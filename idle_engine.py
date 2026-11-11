import os
import sys
import time
import shutil
import logging
import threading
import subprocess
import platform
from typing import Optional, Dict, Any, Callable

if sys.platform == "win32":
    try:
        import ctypes
        # Suppress Windows modal crash / bad image error dialogs (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    except Exception:
        pass

logger = logging.getLogger("IdleEngine")


def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Checks whether a TCP port is currently open and accepting connections."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class IdleEngine:
    """
    💖 Smart Idle & Dynamic Power Saver Engine for Waifu on Telegram.
    
    Automatically unloads heavy GPU/RAM services (KoboldCPP LLM & ComfyUI)
    when the bot is idle, freeing 100% of VRAM (6-8 GB) and system RAM.
    Wakes services up instantly on-demand when user sends a message.
    """
    def __init__(
        self,
        health_engine=None,
        project_root: Optional[str] = None,
        enabled: Optional[bool] = None,
        idle_timeout_minutes: Optional[int] = None,
        comfyui_on_demand: Optional[bool] = None
    ):
        self.health_engine = health_engine
        self.project_root = project_root or os.path.dirname(os.path.abspath(__file__))

        # Environment configuration
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = os.environ.get("SMART_IDLE_ENABLED", "true").lower() in ("true", "1", "yes")

        if idle_timeout_minutes is not None:
            self.idle_timeout_minutes = max(1, idle_timeout_minutes)
        else:
            try:
                self.idle_timeout_minutes = max(1, int(os.environ.get("IDLE_TIMEOUT_MINUTES", "120")))
            except Exception:
                self.idle_timeout_minutes = 120

        if comfyui_on_demand is not None:
            self.comfyui_on_demand = comfyui_on_demand
        else:
            self.comfyui_on_demand = os.environ.get("COMFYUI_ON_DEMAND", "true").lower() in ("true", "1", "yes")

        self.comfyui_timeout_minutes = 5  # ComfyUI unloads 5 mins after last photo request
        self.voicestudio_timeout_minutes = 5  # VoiceStudio unloads 5 mins after last voice synthesis
        self.agy_timeout_minutes = 10  # AGY bridge unloads after 10 mins idle
        self.last_llm_activity = time.time()
        self.last_comfyui_activity = time.time()
        self.last_voicestudio_activity = time.time()
        self.last_agy_activity = time.time()

        self.is_llm_sleeping = not is_port_listening(5001)
        self.is_comfyui_sleeping = not is_port_listening(8188)
        self.is_voicestudio_sleeping = not is_port_listening(3900)
        self.is_agy_sleeping = False if self.is_agy_active_provider() else (not is_port_listening(8001))

        self.wake_lock = threading.RLock()
        self.state_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _should_exclusive_vram_swap(self) -> bool:
        """Returns True if GPU VRAM is constrained (<= 6.5 GB) so KoboldCPP and ComfyUI should swap cleanly instead of coexisting."""
        mode = os.environ.get("VRAM_EXCLUSIVE_SWAP", "auto").strip().lower()
        if mode in ("0", "false", "no", "off"):
            return False
        if mode in ("1", "true", "yes", "on"):
            return True
        try:
            import asset_manager
            hw = asset_manager.detect_hardware_profile()
            vram_mb = int(hw.get("vram_mb", 0) or 0)
            return 0 < vram_mb <= 6656
        except Exception:
            return False

    def _resolve_llm_target(self, is_nsfw: bool = False):
        """Resolves active (provider, base_url, is_split) respecting AI_ENGINE_MODE=unified vs split."""
        split_mode = os.environ.get("AI_ENGINE_MODE", "unified").lower().strip() in ("split", "hybrid")
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "").lower().strip()
        sfw_url = os.environ.get("SFW_LLM_BASE_URL", os.environ.get("LLM_BASE_URL", ""))
        nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "local").lower().strip()
        nsfw_url = os.environ.get("NSFW_LLM_BASE_URL", "http://127.0.0.1:5001/v1")

        if split_mode:
            target_provider = nsfw_p if is_nsfw else sfw_p
            target_url = nsfw_url if is_nsfw else sfw_url
        else:
            llm_url = os.environ.get("LLM_BASE_URL", "").strip()
            if not is_nsfw and (sfw_p == "agy" or ":8001" in llm_url):
                target_provider = "agy"
                target_url = sfw_url if (sfw_p == "agy" and sfw_url) else (llm_url or "http://127.0.0.1:8001/v1")
            elif is_nsfw and (":8001" in llm_url or sfw_p == "agy"):
                target_provider = nsfw_p
                target_url = nsfw_url
            else:
                target_url = llm_url or sfw_url
                target_provider = "local" if ":5001" in target_url else sfw_p

        return target_provider, target_url, split_mode

    def _targets_local_kobold(self, is_nsfw: bool = False) -> bool:
        """Returns True if the current chat request routes to local KoboldCPP (port 5001) rather than Cloud/AGY."""
        target_provider, target_url, split_mode = self._resolve_llm_target(is_nsfw=is_nsfw)

        if target_provider == "agy" or ":8001" in target_url.lower():
            return False
        if split_mode and not is_nsfw and target_provider not in ("", "local", "kobold", "ollama", "lm-studio", "locally-uncensored"):
            return False
        if target_url and not any(p in target_url for p in ["127.0.0.1", "localhost"]):
            return False
        return True

    def _prepare_vram_for_comfyui(self) -> None:
        """Frees KoboldCPP VRAM before starting or running ComfyUI on <= 6.5 GB GPUs."""
        if self._should_exclusive_vram_swap() and is_port_listening(5001):
            logger.info("🔄 VRAM Swap (GPU <= 6.5GB): Menidurkan KoboldCPP sementara sebelum memakai ComfyUI agar bebas OOM...")
            self.sleep_llm()

    def _prepare_vram_for_llm(self) -> None:
        """Frees ComfyUI VRAM before starting or running local KoboldCPP on <= 6.5 GB GPUs."""
        if self._should_exclusive_vram_swap() and is_port_listening(8188):
            logger.info("🔄 VRAM Swap (GPU <= 6.5GB): Menidurkan ComfyUI sementara sebelum memakai KoboldCPP agar bebas OOM...")
            self.sleep_comfyui()

    def is_agy_active_provider(self) -> bool:
        """Determines if AGY CLI is configured as active provider for LLM or Image generation."""
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "").lower().strip()
        nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "").lower().strip()
        llm_url = os.environ.get("LLM_BASE_URL", "").lower()
        sfw_url = os.environ.get("SFW_LLM_BASE_URL", "").lower()
        sfw_img = os.environ.get("SFW_IMAGE_ENGINE", "").lower().strip()
        nsfw_img = os.environ.get("NSFW_IMAGE_ENGINE", "").lower().strip()

        return (
            sfw_p == "agy" or nsfw_p == "agy" or
            ":8001" in llm_url or ":8001" in sfw_url or
            sfw_img == "agy" or nsfw_img == "agy"
        )

    def is_cloud_llm_active(self) -> bool:
        """
        Determines if the active chat LLM is a cloud/remote provider (AGY, Gemini, OpenAI, Claude, Groq)
        that does not consume local GPU VRAM and therefore should never be put to sleep or idled.
        """
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "").lower().strip()
        nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "").lower().strip()
        llm_url = os.environ.get("LLM_BASE_URL", "").lower().strip()
        sfw_url = os.environ.get("SFW_LLM_BASE_URL", "").lower().strip()

        if sfw_p in ("local", "kobold", "ollama", "locally-uncensored"):
            return False
        if sfw_p == "agy" or nsfw_p == "agy":
            return True
        if sfw_p in ("openai", "gemini", "groq", "openrouter", "anthropic", "claude", "cloud"):
            return True
        if ":8001" in sfw_url:
            return True
        if sfw_url and not any(p in sfw_url for p in ["127.0.0.1", "localhost", "0.0.0.0"]):
            return True
        if ":8001" in llm_url:
            return True
        if llm_url and not any(p in llm_url for p in ["127.0.0.1", "localhost", "0.0.0.0", ":5001", ":11434", ":1234"]):
            return True
        return False

    def record_activity(self, is_media: bool = False, is_voice: bool = False, is_agy: bool = False):
        """Records user interaction timestamp to reset idle countdown."""
        now = time.time()
        with self.state_lock:
            self.last_llm_activity = now
            if is_media:
                self.last_comfyui_activity = now
            if is_voice:
                self.last_voicestudio_activity = now
            if is_agy:
                self.last_agy_activity = now

    def is_llm_ready(self, is_nsfw: bool = False) -> bool:
        """Checks if active LLM service is online and listening."""
        target_provider, target_url, _ = self._resolve_llm_target(is_nsfw=is_nsfw)

        # AGY OpenAI Bridge (Port 8001)
        if target_provider == "agy" or ":8001" in target_url:
            return is_port_listening(8001)

        # Ollama (Port 11434)
        if ":11434" in target_url:
            return is_port_listening(11434)

        # Remote Cloud (OpenAI, Groq, etc.)
        if target_url and not any(p in target_url for p in ["127.0.0.1", "localhost"]):
            return True

        if not is_port_listening(5001):
            return False
        if self.health_engine and hasattr(self.health_engine, "llm_client"):
            try:
                cli = self.health_engine.llm_client
                target_cli = cli
                nsfw_cli = getattr(cli, "nsfw_client", None)
                if nsfw_cli and ":5001" in str(getattr(nsfw_cli, "base_url", "")):
                    target_cli = nsfw_cli
                stat = target_cli.check_health()
                return bool(stat.get("online"))
            except Exception:
                return True
        return True

    def is_comfyui_ready(self) -> bool:
        """Checks if ComfyUI service is online and listening on port 8188."""
        return is_port_listening(8188)

    def is_voicestudio_ready(self) -> bool:
        """Checks if VoiceStudio service is online and listening on port 3900."""
        return is_port_listening(3900)

    def is_agy_bridge_ready(self) -> bool:
        """Checks if AGY OpenAI Bridge is online and listening on port 8001."""
        return is_port_listening(8001, timeout=1.5)

    def sleep_voicestudio(self) -> bool:
        """Puts VoiceStudio to sleep, freeing model RAM & VRAM."""
        with self.wake_lock:
            if not is_port_listening(3900):
                self.is_voicestudio_sleeping = True
                return True
            logger.info("💤 Smart Idle: Terminating VoiceStudio backend to free RAM & VRAM...")
            try:
                from voicestudio_engine import voicestudio_engine
                voicestudio_engine.stop_service()
                time.sleep(1)
                self.is_voicestudio_sleeping = True
                logger.info("✓ Smart Idle: VoiceStudio put to sleep. RAM & VRAM freed!")
                return True
            except Exception as e:
                logger.error(f"Error putting VoiceStudio to sleep: {e}")
                return False

    def wake_voicestudio(self, timeout_seconds: int = 15) -> bool:
        """Wakes VoiceStudio backend service on-demand (Port 3900)."""
        with self.wake_lock:
            if self.is_voicestudio_ready():
                self.is_voicestudio_sleeping = False
                self.record_activity(is_voice=True)
                return True
            logger.info("⚡ Smart Idle: Waking VoiceStudio Local AI on-demand (Port 3900)...")
            try:
                from voicestudio_engine import voicestudio_engine
                if voicestudio_engine.is_installed():
                    voicestudio_engine.start_service()
                    for _ in range(timeout_seconds):
                        time.sleep(1)
                        if self.is_voicestudio_ready():
                            self.is_voicestudio_sleeping = False
                            self.record_activity(is_voice=True)
                            logger.info("✓ Smart Idle: VoiceStudio successfully awakened!")
                            return True
            except Exception as e:
                logger.error(f"Failed to wake VoiceStudio: {e}")
            return False

    def ensure_voicestudio_active(self) -> bool:
        """Ensures VoiceStudio is online before synthesis."""
        if not self.enabled:
            return True
        if self.is_voicestudio_ready():
            self.is_voicestudio_sleeping = False
            self.record_activity(is_voice=True)
            return True
        return self.wake_voicestudio()

    def sleep_agy_bridge(self) -> bool:
        """Puts AGY Bridge to sleep, terminating python agy_bridge.py to free RAM. (Blocked if AGY is active provider)"""
        # User requested: klo misalkan user pilih LLM agy , agy bridge nya jangan sampai off atau idle, biarkan nyala saja terus
        if self.is_agy_active_provider():
            logger.info("⚡ Smart Idle: User selected AGY as active LLM/Image provider. AGY Bridge stays permanently awake!")
            self.is_agy_sleeping = False
            return False

        with self.wake_lock:
            if not is_port_listening(8001):
                self.is_agy_sleeping = True
                return True
            logger.info("💤 Smart Idle: Terminating AGY OpenAI Bridge to free RAM...")
            try:
                if sys.platform == "win32":
                    ps_cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*agy_bridge.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
                    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=8)
                else:
                    subprocess.run(["pkill", "-f", "python.*agy_bridge.py"], capture_output=True, timeout=5)
                time.sleep(1)
                self.is_agy_sleeping = True
                logger.info("✓ Smart Idle: AGY OpenAI Bridge put to sleep.")
                return True
            except Exception as e:
                logger.error(f"Error putting AGY Bridge to sleep: {e}")
                return False

    def wake_agy_bridge(self, timeout_seconds: int = 15) -> bool:
        """Wakes AGY OpenAI Bridge server on-demand (Port 8001)."""
        with self.wake_lock:
            if self.is_agy_bridge_ready():
                self.is_agy_sleeping = False
                self.record_activity(is_agy=True)
                return True
            logger.info("⚡ Smart Idle: Waking AGY OpenAI Bridge on-demand (Port 8001)...")
            agy_script = os.path.join(self.project_root, "agy_bridge.py")
            if not os.path.exists(agy_script):
                return False
            try:
                popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
                log_path = os.path.join(self.project_root, "agy_bridge.log")
                spawn_env = os.environ.copy()
                spawn_env["PYTHONIOENCODING"] = "utf-8"
                spawn_env["PYTHONUTF8"] = "1"
                with open(log_path, "a", encoding="utf-8") as f_log:
                    subprocess.Popen([sys.executable, agy_script], cwd=self.project_root, stdout=f_log, stderr=f_log, env=spawn_env, **popen_kwargs)
                for _ in range(timeout_seconds * 2):
                    time.sleep(0.5)
                    if self.is_agy_bridge_ready():
                        self.is_agy_sleeping = False
                        self.record_activity(is_agy=True)
                        logger.info("✓ Smart Idle: AGY OpenAI Bridge successfully awakened on port 8001!")
                        return True
            except Exception as e:
                logger.error(f"Failed to wake AGY Bridge: {e}")
            return False

    def ensure_agy_bridge_active(self) -> bool:
        """Ensures AGY OpenAI Bridge is online before routing chat or image request."""
        if not self.enabled:
            return True
        if self.is_agy_bridge_ready():
            self.is_agy_sleeping = False
            self.record_activity(is_agy=True)
            return True
        return self.wake_agy_bridge()

    def sleep_llm(self) -> bool:
        """Puts KoboldCPP LLM to sleep, freeing all GPU VRAM and model RAM."""
        with self.wake_lock:
            if not is_port_listening(5001):
                self.is_llm_sleeping = True
                return True

            logger.info("💤 Smart Idle: Terminating KoboldCPP LLM to free VRAM & RAM...")
            self.is_llm_sleeping = True
            try:
                if self.health_engine and hasattr(self.health_engine, "kill_all_koboldcpp"):
                    self.health_engine.kill_all_koboldcpp()
                else:
                    from health_engine import kill_all_koboldcpp
                    kill_all_koboldcpp()
                
                for _ in range(5):
                    time.sleep(0.2)
                    if not is_port_listening(5001):
                        break
                self.is_llm_sleeping = True
                logger.info("✓ Smart Idle: KoboldCPP put to sleep. VRAM & RAM successfully freed!")
                return True
            except Exception as e:
                logger.error(f"Error putting KoboldCPP to sleep: {e}")
                return False

    def sleep_comfyui(self) -> bool:
        """Puts ComfyUI generator to sleep, freeing image model VRAM."""
        with self.wake_lock:
            if not is_port_listening(8188):
                self.is_comfyui_sleeping = True
                return True

            logger.info("💤 Smart Idle: Terminating ComfyUI generator to free VRAM...")
            self.is_comfyui_sleeping = True
            try:
                if sys.platform == "win32":
                    ps_comfy = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.py*" -and $_.CommandLine -like "*8188*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps_comfy],
                        capture_output=True,
                        creationflags=0x08000000
                    )
                else:
                    subprocess.run(["pkill", "-9", "-f", "python.*main.py.*8188"], capture_output=True)
                
                for _ in range(5):
                    time.sleep(0.2)
                    if not is_port_listening(8188):
                        break
                self.is_comfyui_sleeping = True
                logger.info("✓ Smart Idle: ComfyUI put to sleep. VRAM successfully freed!")
                return True
            except Exception as e:
                logger.error(f"Error putting ComfyUI to sleep: {e}")
                return False

    def manual_idle(self) -> Dict[str, Any]:
        """
        Manually triggers idle mode: immediately frees local GPU VRAM & RAM
        by putting local services (KoboldCPP, ComfyUI, VoiceStudio) to sleep.
        Cloud LLMs like AGY/OpenAI/Gemini are exempted because they run in the cloud (0 VRAM).
        """
        results = {
            "llm": "unknown",
            "comfyui": "unknown",
            "voicestudio": "unknown",
            "agy": "unknown",
            "freed_any": False,
            "details": []
        }

        # 1. ComfyUI (Local Image/Video Generator)
        if is_port_listening(8188):
            ok = self.sleep_comfyui()
            results["comfyui"] = "slept" if ok else "failed"
            if ok:
                results["freed_any"] = True
                results["details"].append("🎨 Studio Foto (ComfyUI) ditidurkan ➔ VRAM bebas!")
        else:
            self.is_comfyui_sleeping = True
            results["comfyui"] = "already_sleeping"
            results["details"].append("🎨 Studio Foto (ComfyUI) sudah standby.")

        # 2. LLM Chat Engine
        if self.is_cloud_llm_active():
            results["llm"] = "cloud_exempt"
            results["details"].append("☁️ LLM Chat (Cloud/AGY) tetap aktif (0 VRAM overhead, tidak membebani PC).")
            # If local KoboldCPP was also left lingering on port 5001, sleep it to reclaim VRAM
            if is_port_listening(5001):
                self.sleep_llm()
                results["freed_any"] = True
                results["details"].append("🧠 Background KoboldCPP ditidurkan ➔ VRAM bebas!")
        else:
            if is_port_listening(5001):
                ok = self.sleep_llm()
                results["llm"] = "slept" if ok else "failed"
                if ok:
                    results["freed_any"] = True
                    results["details"].append("🧠 Local LLM (KoboldCPP) ditidurkan ➔ 6-8 GB VRAM berhasil dibebaskan!")
            else:
                self.is_llm_sleeping = True
                results["llm"] = "already_sleeping"
                results["details"].append("🧠 Local LLM sudah dalam kondisi tidur.")

        # 3. VoiceStudio (Local Audio)
        if is_port_listening(3900):
            ok = self.sleep_voicestudio()
            results["voicestudio"] = "slept" if ok else "failed"
            if ok:
                results["freed_any"] = True
                results["details"].append("🎙️ VoiceStudio ditidurkan ➔ RAM & VRAM bebas!")
        else:
            self.is_voicestudio_sleeping = True
            results["voicestudio"] = "already_sleeping"

        # 4. AGY Bridge
        if self.is_agy_active_provider():
            results["agy"] = "cloud_exempt"
            results["details"].append("🌉 Google AGY Bridge tetap aktif (0 VRAM).")
        elif is_port_listening(8001):
            self.sleep_agy_bridge()
            results["agy"] = "slept"
            results["details"].append("🌉 AGY Bridge ditidurkan.")

        return results

    def wake_llm(self, timeout_seconds: int = 75, is_nsfw: bool = False) -> bool:
        """
        Wakes active LLM on-demand (AGY Bridge or KoboldCPP).
        """
        target_provider, target_url, _ = self._resolve_llm_target(is_nsfw=is_nsfw)

        if target_provider == "agy" or ":8001" in target_url:
            ok = self.wake_agy_bridge(timeout_seconds=min(timeout_seconds, 20))
            if ok:
                self.is_llm_sleeping = False
                self.record_activity()
            return ok

        # Remote Cloud providers (OpenAI, Groq, etc.)
        if target_url and not any(p in target_url for p in ["127.0.0.1", "localhost"]):
            self.is_llm_sleeping = False
            self.record_activity()
            return True

        with self.wake_lock:
            self._prepare_vram_for_llm()
            if self.is_llm_ready(is_nsfw=is_nsfw):
                self.is_llm_sleeping = False
                self.record_activity()
                return True

            logger.info("⚡ Smart Idle: Waking KoboldCPP LLM on-demand...")

            deadline = time.time() + max(5, int(timeout_seconds))

            # Use HealthEngine heal_llm if available (share single overall timeout budget)
            started = False
            if self.health_engine and hasattr(self.health_engine, "heal_llm"):
                rem_sec = max(5, int(deadline - time.time()))
                try:
                    started = self.health_engine.heal_llm(is_nsfw=is_nsfw, wait_seconds=rem_sec)
                except TypeError:
                    try:
                        started = self.health_engine.heal_llm(is_nsfw=is_nsfw)
                    except TypeError:
                        started = self.health_engine.heal_llm()
            else:
                # Direct launch fallback using asset_manager discovery
                try:
                    import asset_manager
                    spec = asset_manager.get_llm_launch_spec(project_root=self.project_root)
                    if spec:
                        popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
                        kcpp_log = os.path.join(self.project_root, "koboldcpp.log")
                        try:
                            with open(kcpp_log, "a", encoding="utf-8") as f_kcpp:
                                subprocess.Popen(spec["cmd"], cwd=spec["cwd"], stdout=f_kcpp, stderr=f_kcpp, **popen_kwargs)
                            started = True
                        except Exception as e_kcpp:
                            if sys.platform == "win32":
                                quoted_parts = [f'"{c}"' if (' ' in c or '\\' in c) else c for c in spec["cmd"]]
                                cmd_line = f'start "" /b {" ".join(quoted_parts)}'
                                subprocess.Popen(f'cmd.exe /c "{cmd_line}"', cwd=spec["cwd"], shell=True)
                                started = True
                            else:
                                raise e_kcpp
                        logger.info(f"⚡ Smart Idle: Started KoboldCPP fallback process using {spec['cmd'][0]}")
                except Exception as e:
                    logger.error(f"Failed to launch KoboldCPP on-demand fallback: {e}")

            kcpp_loading = False
            if not started and not is_port_listening(5001):
                try:
                    from health_engine import get_koboldcpp_process_count
                    kcpp_loading = get_koboldcpp_process_count() >= 1
                except Exception:
                    kcpp_loading = False

            if not started and not is_port_listening(5001) and not kcpp_loading:
                logger.warning("⚡ Smart Idle: Could not launch KoboldCPP (binary or model missing).")
                return False

            # Wait for port and readiness within remaining shared deadline
            while time.time() < deadline:
                if self.is_llm_ready(is_nsfw=is_nsfw):
                    self.is_llm_sleeping = False
                    self.record_activity()
                    logger.info("✓ Smart Idle: KoboldCPP successfully awakened and ready!")
                    return True
                time.sleep(1)

            if self.is_llm_ready(is_nsfw=is_nsfw):
                self.is_llm_sleeping = False
                self.record_activity()
                return True

            logger.warning(f"⚡ Smart Idle: Timed out ({timeout_seconds}s) waiting for KoboldCPP readiness.")
            return False

    def wake_comfyui(self, timeout_seconds: int = 40) -> bool:
        """
        Wakes ComfyUI generator on-demand when a photo/video is requested.
        """
        with self.wake_lock:
            self._prepare_vram_for_comfyui()
            if self.is_comfyui_ready():
                self.is_comfyui_sleeping = False
                self.record_activity(is_media=True)
                return True

            logger.info("⚡ Smart Idle: Waking ComfyUI photo generator on-demand...")

            if self.health_engine and hasattr(self.health_engine, "heal_comfyui"):
                self.health_engine.heal_comfyui()
            else:
                try:
                    import asset_manager
                    spec = asset_manager.get_comfyui_launch_spec()
                    if spec:
                        popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
                        comfy_log = os.path.join(self.project_root, "comfyui.log")
                        try:
                            with open(comfy_log, "a", encoding="utf-8") as f_comfy:
                                subprocess.Popen(spec["cmd"], cwd=spec["cwd"], stdout=f_comfy, stderr=f_comfy, **popen_kwargs)
                        except Exception as e_direct:
                            if sys.platform == "win32":
                                quoted_parts = [f'"{c}"' if (' ' in c or '\\' in c) else c for c in spec["cmd"]]
                                cmd_line = f'start "" /b {" ".join(quoted_parts)}'
                                subprocess.Popen(f'cmd.exe /c "{cmd_line}"', cwd=spec["cwd"], shell=True)
                            else:
                                raise e_direct
                except Exception as e:
                    logger.error(f"Failed to launch ComfyUI on-demand: {e}")

            deadline = time.time() + timeout_seconds
            while time.time() < deadline:
                if self.is_comfyui_ready():
                    self.is_comfyui_sleeping = False
                    self.record_activity(is_media=True)
                    logger.info("✓ Smart Idle: ComfyUI successfully awakened and ready!")
                    return True
                time.sleep(1)

            return False

    def ensure_llm_active(self, bot=None, chat_id: Optional[int] = None, is_user_chat: bool = True, is_nsfw: bool = False) -> bool:
        """
        Ensures LLM is active before answering messages.
        If sleeping, displays a friendly waking indicator and wakes KoboldCPP.
        If is_user_chat is False (e.g. background automation or scheduler),
        it will NEVER wake the LLM from sleep to avoid interrupting gaming / work.
        If AI_ENGINE_MODE is split and SFW provider is Cloud, does NOT wake local KoboldCPP unless is_nsfw is True!
        """
        if not self.enabled:
            return True

        # Check if SFW provider is remote cloud (AGY runs local bridge on port 8001)
        split_mode = os.environ.get("AI_ENGINE_MODE", "unified").lower().strip() in ("split", "hybrid")
        sfw_provider = os.environ.get("SFW_LLM_PROVIDER", "local").lower().strip()
        sfw_is_cloud = split_mode and sfw_provider not in ("local", "kobold", "ollama", "lm-studio", "locally-uncensored", "agy")

        if sfw_is_cloud and not is_nsfw:
            # Cloud SFW engine handles the request, KoboldCPP stays comfortably asleep
            self.record_activity()
            return True

        if self._targets_local_kobold(is_nsfw=is_nsfw):
            self._prepare_vram_for_llm()

        if self.is_llm_ready(is_nsfw=is_nsfw):
            self.is_llm_sleeping = False
            self.record_activity()
            return True

        if not is_user_chat:
            logger.info("⚡ Smart Idle: Blocked background automation from waking LLM (Gaming Protection Active).")
            return False

        # Send temporary waking status to user
        waking_msg = None
        if bot and chat_id:
            try:
                bot.send_chat_action(chat_id, "typing")
                waking_msg = bot.send_message(
                    chat_id,
                    "🌸 *Waifu lagi bangun dari mode hemat daya...* (~5 detik) ✨",
                    parse_mode="Markdown"
                )
                bot.send_chat_action(chat_id, "typing")
            except Exception:
                pass

        stop_feedback = threading.Event()

        def _feedback_loop():
            start_t = time.time()
            while not stop_feedback.is_set():
                stop_feedback.wait(2.5)
                if stop_feedback.is_set():
                    break
                elapsed = int(time.time() - start_t)
                if bot and chat_id and waking_msg:
                    try:
                        bot.send_chat_action(chat_id, "typing")
                        bot.edit_message_text(
                            f"🌸 *Waifu lagi bangun dari mode hemat daya...* ({elapsed}s) ✨",
                            chat_id=chat_id,
                            message_id=waking_msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

        sfw_p_chk, sfw_url_chk, _ = self._resolve_llm_target(is_nsfw=False)
        sfw_is_alt_engine = (
            split_mode
            or sfw_p_chk == "agy"
            or ":8001" in sfw_url_chk
            or (sfw_p_chk not in ("", "local", "kobold", "koboldcpp", "ollama", "lm-studio", "locally-uncensored"))
        )
        has_live_fallback = bool(is_nsfw and sfw_is_alt_engine and self.is_llm_ready(is_nsfw=False))
        wake_timeout = 30 if has_live_fallback else 55

        fb_thread = threading.Thread(target=_feedback_loop, daemon=True)
        fb_thread.start()
        try:
            ok = self.wake_llm(timeout_seconds=wake_timeout, is_nsfw=is_nsfw)
        finally:
            stop_feedback.set()
            fb_thread.join(timeout=1.0)

        # High-availability fallback:
        # If NSFW KoboldCPP on port 5001 failed to wake, but SFW engine (AGY 8001 or Cloud) is ready,
        # proceed seamlessly via SFW fallback regardless of unified vs split mode!
        if not ok and is_nsfw:
            if sfw_is_alt_engine and self.is_llm_ready(is_nsfw=False):
                logger.warning("⚡ Smart Idle: KoboldCPP (port 5001) could not be awakened, but SFW engine is ready. Seamlessly proceeding via SFW fallback.")
                ok = True

        # Handle feedback message
        if waking_msg and bot and chat_id:
            if ok:
                try:
                    bot.delete_message(chat_id, waking_msg.message_id)
                except Exception:
                    pass
                try:
                    bot.send_chat_action(chat_id, "typing")
                except Exception:
                    pass
            else:
                agy_hint = ""
                if is_port_listening(8001):
                    agy_hint = "\n• 🌉 *AGY Bridge Aktif:* Ketik `/setup` ➔ `🧠 Model LLM` ➔ pilih `Google Antigravity Bridge` agar langsung aktif!"
                err_text = (
                    "⚠️ *Waifu belum bisa dibangunkan otomatis!*\n\n"
                    "Engine AI lokal (KoboldCPP) tidak merespons di port 5001.\n"
                    "Kemungkinan model LLM belum terpasang atau file binary belum ditemukan.\n\n"
                    "💡 *Solusi:*\n"
                    "• Ketik `/status` untuk melihat diagnosa lengkap\n"
                    f"• Atau jalankan `start_services.bat` di folder PC kamu.{agy_hint}"
                )
                try:
                    bot.edit_message_text(
                        err_text,
                        chat_id=chat_id,
                        message_id=waking_msg.message_id,
                        parse_mode="Markdown"
                    )
                except Exception:
                    try:
                        bot.send_message(chat_id, err_text.replace("*", ""))
                    except Exception:
                        pass
        elif not ok and bot and chat_id:
            try:
                bot.send_message(
                    chat_id,
                    "⚠️ Otak AI lokal (KoboldCPP) belum aktif di port 5001. Silakan ketik /status untuk informasi lebih lanjut."
                )
            except Exception:
                pass

        self.record_activity()
        return ok

    def ensure_comfyui_active(self, bot=None, chat_id: Optional[int] = None, is_nude: bool = False) -> bool:
        """
        Ensures ComfyUI is active before generating photos/videos on-demand.
        If user configured AGY or Cloud as active image engine, ComfyUI is bypassed.
        """
        if not self.enabled:
            return True

        # Check if active visual engine actually uses ComfyUI
        img_mode = os.environ.get("IMAGE_ENGINE_MODE", "unified").lower().strip()
        sfw_img = os.environ.get("SFW_IMAGE_ENGINE", "comfyui").lower().strip()
        uni_img = os.environ.get("IMAGE_ENGINE", sfw_img).lower().strip() if img_mode == "unified" else sfw_img
        if not is_nude and uni_img in ("agy", "cloud"):
            return True

        # Avoid killing live KoboldCPP on <= 6.5 GB GPU if ComfyUI is neither running nor installed locally
        if not self.is_comfyui_ready():
            try:
                import asset_manager
                if not asset_manager.detect_comfyui_dir():
                    return False
            except Exception:
                pass

        self._prepare_vram_for_comfyui()

        if not self.comfyui_on_demand and not self.is_comfyui_sleeping:
            return True

        if self.is_comfyui_ready():
            self.is_comfyui_sleeping = False
            self.record_activity(is_media=True)
            return True

        waking_msg = None
        if bot and chat_id:
            try:
                bot.send_chat_action(chat_id, "upload_photo")
                waking_msg = bot.send_message(
                    chat_id,
                    "📸 *Menyiapkan studio foto ComfyUI di PC...* (~5-15 detik) ✨",
                    parse_mode="Markdown"
                )
                bot.send_chat_action(chat_id, "upload_photo")
            except Exception:
                pass

        stop_feedback = threading.Event()

        def _comfy_feedback_loop():
            start_t = time.time()
            while not stop_feedback.is_set():
                stop_feedback.wait(2.5)
                if stop_feedback.is_set():
                    break
                elapsed = int(time.time() - start_t)
                if bot and chat_id and waking_msg:
                    try:
                        bot.send_chat_action(chat_id, "upload_photo")
                        bot.edit_message_text(
                            f"📸 *Menyiapkan studio foto ComfyUI di PC...* ({elapsed}s) ✨",
                            chat_id=chat_id,
                            message_id=waking_msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass

        fb_thread = threading.Thread(target=_comfy_feedback_loop, daemon=True)
        fb_thread.start()
        try:
            ok = self.wake_comfyui()
        finally:
            stop_feedback.set()
            fb_thread.join(timeout=1.0)

        if waking_msg and bot and chat_id:
            if ok:
                try:
                    bot.delete_message(chat_id, waking_msg.message_id)
                except Exception:
                    pass
                try:
                    bot.send_chat_action(chat_id, "upload_photo")
                except Exception:
                    pass
            else:
                err_text = (
                    "⚠️ *Studio foto ComfyUI belum dapat dinyalakan!*\n\n"
                    "Layanan ComfyUI di port 8188 tidak merespons.\n"
                    "💡 Periksa apakah ComfyUI sudah terinstall atau jalankan `start_services.bat`."
                )
                try:
                    bot.edit_message_text(
                        err_text,
                        chat_id=chat_id,
                        message_id=waking_msg.message_id,
                        parse_mode="Markdown"
                    )
                except Exception:
                    try:
                        bot.send_message(chat_id, err_text.replace("*", ""))
                    except Exception:
                        pass

        self.record_activity(is_media=True)
        return ok

    def _monitor_loop(self):
        """Continuous background monitor checking for idle timeout."""
        logger.info(
            f"💤 Smart Idle Watchdog active (Timeout: {self.idle_timeout_minutes}m, "
            f"ComfyUI On-Demand: {self.comfyui_on_demand})"
        )
        while self._running:
            time.sleep(15)
            if not self.enabled:
                continue

            try:
                now = time.time()
                llm_idle_sec = self.idle_timeout_minutes * 60
                comfyui_idle_sec = self.comfyui_timeout_minutes * 60

                # 1. Check KoboldCPP LLM idle
                # Cloud LLMs like AGY do not use local VRAM, so they are exempted from idle sleeping
                if not self.is_cloud_llm_active():
                    if (now - self.last_llm_activity) >= llm_idle_sec:
                        if is_port_listening(5001) and not self.is_llm_sleeping:
                            logger.info(
                                f"💤 Smart Idle: No chat activity for {self.idle_timeout_minutes}m. "
                                f"Putting KoboldCPP to sleep..."
                            )
                            self.sleep_llm()

                # 2. Check ComfyUI on-demand idle
                if self.comfyui_on_demand:
                    if (now - self.last_comfyui_activity) >= comfyui_idle_sec:
                        if is_port_listening(8188) and not self.is_comfyui_sleeping:
                            logger.info(
                                f"💤 Smart Idle: No photo/video request for {self.comfyui_timeout_minutes}m. "
                                f"Putting ComfyUI to sleep..."
                            )
                            self.sleep_comfyui()

                # 3. Check VoiceStudio idle (auto-sleep to free RAM/VRAM)
                v_backend = os.environ.get("VOICE_BACKEND", "edge-tts").lower().strip()
                if (v_backend in ("voicestudio", "local") or is_port_listening(3900)):
                    vs_idle_sec = self.voicestudio_timeout_minutes * 60
                    if (now - self.last_voicestudio_activity) >= vs_idle_sec:
                        if is_port_listening(3900) and not self.is_voicestudio_sleeping:
                            logger.info(
                                f"💤 Smart Idle: No voice synthesis activity for {self.voicestudio_timeout_minutes}m. "
                                f"Putting VoiceStudio to sleep to free RAM & VRAM..."
                            )
                            self.sleep_voicestudio()

                # 4. Check AGY Bridge idle (Never sleep if active provider, keep alive continuously!)
                if self.is_agy_active_provider():
                    self.is_agy_sleeping = False
                    if not is_port_listening(8001):
                        logger.info("⚡ Smart Idle: User selected AGY as active LLM/Image provider and port 8001 is offline. Auto-starting AGY Bridge...")
                        self.wake_agy_bridge()
                elif is_port_listening(8001):
                    agy_idle_sec = self.agy_timeout_minutes * 60
                    if (now - self.last_agy_activity) >= agy_idle_sec:
                        if not self.is_agy_sleeping:
                            logger.info(
                                f"💤 Smart Idle: No AGY Bridge activity for {self.agy_timeout_minutes}m. "
                                f"Putting AGY Bridge to sleep to free RAM..."
                            )
                            self.sleep_agy_bridge()

            except Exception as e:
                logger.error(f"Error in Smart Idle watchdog loop: {e}")

    def start(self):
        """Starts the background idle monitor thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the background idle monitor."""
        self._running = False

    def get_status_summary(self) -> str:
        """Returns diagnostic string for /status and setup reports."""
        if not self.enabled:
            return "⚪ Nonaktif"
        if self.is_cloud_llm_active():
            llm_state = "☁️ Online Cloud (0 VRAM)"
        else:
            llm_state = "💤 Tidur (VRAM Bebas)" if self.is_llm_sleeping else ("🟢 Online" if is_port_listening(5001) else "💤 Standby")
        comfy_state = "💤 Standby On-Demand" if self.comfyui_on_demand else ("🟢 Online" if is_port_listening(8188) else "🔴 Offline")
        vs_state = "🟢 Online" if is_port_listening(3900) else "💤 Standby"
        if self.is_agy_active_provider():
            agy_state = "🟢 Online (Always-On)" if is_port_listening(8001) else "⚡ Always-On (Auto-Wake)"
        else:
            agy_state = "🟢 Online" if is_port_listening(8001) else "💤 Standby"
        return f"🟢 Aktif (Idle: {self.idle_timeout_minutes}m • LLM: {llm_state} • Foto: {comfy_state} • Voice: {vs_state} • AGY: {agy_state})"

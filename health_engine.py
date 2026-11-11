"""
health_engine.py - Autonomous System Health Monitoring, Watchdog & Self-Healing Engine
Monitors Local LLM (KoboldCPP/Ollama), ComfyUI, and Music Remote services.
Sends proactive Telegram alerts when services crash/disconnect, notifies user on PC boot/startup,
announces service recovery, and automatically resurrects (Self-Healing) failed services.
"""

import os
import sys
import time
import shutil
import logging
import threading
import subprocess
from typing import Optional, Dict, Any, List, Callable
from telebot import types

if sys.platform == "win32":
    try:
        import ctypes
        # Suppress Windows modal crash / bad image error dialogs (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    except Exception:
        pass

logger = logging.getLogger("HealthEngine")


def get_system_uptime() -> Optional[float]:
    """Returns host operating system uptime in seconds, or None if unavailable."""
    try:
        if sys.platform == "win32":
            import ctypes
            return ctypes.windll.kernel32.GetTickCount64() / 1000.0
        elif os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r") as f:
                return float(f.readline().split()[0])
    except Exception as e:
        logger.debug(f"Could not retrieve system uptime: {e}")
    return None


def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Checks whether a TCP port is currently open and accepting connections."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def get_koboldcpp_process_count() -> int:
    """Returns number of active koboldcpp processes running on host OS."""
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                creationflags=0x08000000
            ).decode("utf-8", errors="ignore")
            lines = [l for l in out.strip().splitlines() if "koboldcpp" in l.lower()]
            return len(lines)
        else:
            out = subprocess.check_output(["pgrep", "-f", "koboldcpp"]).decode("utf-8", errors="ignore")
            lines = [l for l in out.strip().splitlines() if l.strip()]
            return len(lines)
    except Exception:
        return 0


def kill_all_koboldcpp() -> None:
    """Forcefully terminates all running KoboldCPP instances on host OS."""
    try:
        if sys.platform == "win32":
            # 1. Kill by image wildcard (covers koboldcpp.exe, koboldcpp_cu12.exe, koboldcpp_nocuda.exe, etc.)
            subprocess.run(
                ["taskkill", "/F", "/T", "/IM", "koboldcpp*.exe"],
                capture_output=True,
                creationflags=0x08000000
            )
            # 2. Kill by Win32_Process command line matching
            ps_kill = (
                "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
                "Where-Object { $_.Name -like '*koboldcpp*' -or $_.CommandLine -like '*koboldcpp*' -or $_.CommandLine -like '*Huihui-Qwythos*' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_kill],
                capture_output=True,
                creationflags=0x08000000
            )
            # 3. Release any ghost processes binding ports 5001-5005
            ps_port_kill = (
                "Get-NetTCPConnection -LocalPort 5001,5002,5003,5004,5005 -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty OwningProcess -Unique | "
                "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_port_kill],
                capture_output=True,
                creationflags=0x08000000
            )
        else:
            subprocess.run(["pkill", "-9", "-f", "koboldcpp"], capture_output=True)
    except Exception as e:
        logger.warning(f"Error terminating KoboldCPP processes: {e}")


_KOBOLD_SPAWN_LOCK = threading.Lock()

class HealthEngine:
    def __init__(
        self,
        llm_client,
        media_engine=None,
        check_interval: int = 30,
        enabled: bool = True,
        self_healing_enabled: bool = True,
        project_root: Optional[str] = None,
        idle_engine=None
    ):
        self.llm_client = llm_client
        self.media_engine = media_engine
        self.check_interval = max(10, check_interval)
        self.enabled = enabled
        self.self_healing_enabled = self_healing_enabled
        self.project_root = project_root or os.path.dirname(os.path.abspath(__file__))
        self.idle_engine = idle_engine

        self.last_llm_online: Optional[bool] = None
        self.last_media_online: Optional[bool] = None
        self.llm_offline_alert_sent: bool = False
        self.consecutive_llm_failures: int = 0

        # Self-healing throttling & circuit breaker
        self.heal_attempts: Dict[str, List[float]] = {
            "llm": [],
            "comfyui": [],
            "music": [],
            "agy": [],
            "voicestudio": []
        }
        self.healing_in_progress: Dict[str, bool] = {
            "llm": False,
            "comfyui": False,
            "music": False,
            "agy": False,
            "voicestudio": False
        }
        self.heal_limit_alert_sent: Dict[str, bool] = {}
        self.last_failure_alert_time: Dict[str, float] = {}
        self.last_recovery_alert_time: Dict[str, float] = {}
        self.last_recovery_callback_time: Dict[str, float] = {}
        self.alert_cooldown_seconds: int = 300  # Minimum 5 mins between broadcast alerts to avoid flapping spam

        self.max_heal_attempts_per_window: int = 3
        self.heal_window_seconds: int = 900  # 15 minutes
        self.heal_cooldown_seconds: int = 45

        self.startup_notified: bool = False
        self.recovery_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self.lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def register_recovery_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Registers a callback hook invoked whenever a service recovers."""
        if callback not in self.recovery_callbacks:
            self.recovery_callbacks.append(callback)

    def _notify_recovery(self, service: str, stat: Optional[Dict[str, Any]] = None):
        """Dispatches recovery notification to registered callbacks with cooldown guard."""
        now = time.time()
        last_cb = self.last_recovery_callback_time.get(service, 0)
        if (now - last_cb) < 60.0:
            logger.info(f"Recovery callback for {service} throttled (already dispatched {int(now - last_cb)}s ago).")
            return
        self.last_recovery_callback_time[service] = now

        stat_dict = stat or {"online": True, "service": service}
        for cb in list(self.recovery_callbacks):
            try:
                cb(service, stat_dict)
            except Exception as e:
                logger.error(f"Error in recovery callback for {service}: {e}")

    def send_safe_message(self, bot, chat_id: int, text: str, reply_markup=None):
        """Sends a Telegram message safely, falling back to plain text if Markdown parsing fails."""
        try:
            return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e_md:
            logger.warning(f"Markdown send failed to {chat_id} ({e_md}), retrying as plain text...")
            clean_text = text.replace("**", "").replace("*", "").replace("`", "").replace("_", "")
            try:
                return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
            except Exception as e_final:
                logger.error(f"Failed to deliver health message to {chat_id}: {e_final}")
                return None

    # --- Self-Healing Resurrection Implementations ---

    def can_attempt_heal(self, service: str) -> bool:
        """Determines if a healing attempt is allowed under circuit-breaker rules."""
        if not self.self_healing_enabled:
            return False
        if self.healing_in_progress.get(service):
            return False

        now = time.time()
        # Filter attempts within active window
        history = [ts for ts in self.heal_attempts.get(service, []) if now - ts < self.heal_window_seconds]
        self.heal_attempts[service] = history

        if len(history) < self.max_heal_attempts_per_window:
            self.heal_limit_alert_sent[service] = False
        else:
            return False

        if history and (now - history[-1]) < self.heal_cooldown_seconds:
            return False

        return True

    def heal_llm(self, is_nsfw: bool = False, wait_seconds: int = 45) -> bool:
        """
        Attempts to automatically start or resurrect the active LLM service (AGY Bridge / KoboldCPP / Ollama).
        Guarantees strict singleton execution: prevents multiple KoboldCPP instances from spawning.
        Returns True if service is running and healthy.
        """
        base_url = getattr(self.llm_client, "base_url", "")
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "").lower().strip()
        nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "local").lower().strip()
        nsfw_url = os.environ.get("NSFW_LLM_BASE_URL", "")
        mode = os.environ.get("AI_ENGINE_MODE", "unified").lower().strip()

        # When specifically waking/healing for an NSFW turn that targets local KoboldCPP (port 5001),
        # never short-circuit to SFW AGY (8001) even if AI_ENGINE_MODE=unified.
        nsfw_targets_local = (
            nsfw_p in ("", "local", "kobold", "koboldcpp", "locally-uncensored")
            or ":5001" in str(nsfw_url)
        )
        if is_nsfw and nsfw_targets_local:
            return self._heal_koboldcpp_instance(wait_seconds=wait_seconds)

        # In split mode, check whichever engine is offline (avoid duplicate 5001 probes)
        if mode in ("split", "hybrid"):
            ok = True
            kobold_checked = False
            if (sfw_p == "agy" or ":8001" in str(base_url)):
                if not is_port_listening(8001, timeout=1.5):
                    ok = self.heal_agy() and ok
            else:
                kobold_checked = True
                if not is_port_listening(5001):
                    ok = self._heal_koboldcpp_instance(wait_seconds=wait_seconds) and ok

            if not kobold_checked and (nsfw_p == "local" or ":5001" in str(getattr(self.llm_client, "nsfw_client", ""))):
                if not is_port_listening(5001):
                    ok = self._heal_koboldcpp_instance(wait_seconds=wait_seconds) and ok
            return ok

        # If active LLM is AGY OpenAI Bridge (Port 8001)
        if sfw_p == "agy" or ":8001" in str(base_url):
            return self.heal_agy()

        return self._heal_koboldcpp_instance(wait_seconds=wait_seconds)

    def _check_kobold_port_health(self) -> Dict[str, Any]:
        """Checks health specifically against the local KoboldCPP (5001) client if in split mode."""
        cli = self.llm_client
        nsfw_cli = getattr(cli, "nsfw_client", None)
        if nsfw_cli and ":5001" in str(getattr(nsfw_cli, "base_url", "")):
            return nsfw_cli.check_health()
        return cli.check_health()

    def _heal_koboldcpp_instance(self, wait_seconds: int = 45) -> bool:
        with _KOBOLD_SPAWN_LOCK:
            if is_port_listening(5001):
                stat = self._check_kobold_port_health()
                if stat.get("online"):
                    return True

            # Strict Singleton Guard: Check for duplicate or currently loading KoboldCPP instances
            proc_count = get_koboldcpp_process_count()
            if proc_count > 2:
                logger.warning(f"Detected {proc_count} duplicate KoboldCPP processes thrashing system RAM. Terminating duplicates...")
                kill_all_koboldcpp()
                time.sleep(1)
            elif proc_count >= 1:
                logger.info("KoboldCPP process is already running (loading model weights). Waiting for port 5001...")
                existing_wait = max(5, min(int(wait_seconds), 15))
                for sec in range(1, existing_wait + 1):
                    time.sleep(1)
                    if is_port_listening(5001):
                        stat = self._check_kobold_port_health()
                        if stat.get("online"):
                            logger.info(f"Existing KoboldCPP became ready in {sec}s.")
                            return True
                # Process was running but didn't open port 5001 in time - terminate before spawning fresh
                logger.warning(f"Existing KoboldCPP process timed out binding port 5001 after {existing_wait}s. Restarting cleanly...")
                kill_all_koboldcpp()
                time.sleep(1)

        # 1. Use smart discovery from asset_manager
        spec = None
        try:
            import asset_manager
            spec = asset_manager.get_llm_launch_spec()
        except Exception as e_spec:
            logger.warning(f"Error querying LLM launch spec: {e_spec}")

        spawn_succeeded = False
        if spec and spec.get("cmd"):
            popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
            try:
                logger.info(f"Self-healing: Spawning single KoboldCPP LLM Server ({os.path.basename(spec.get('model', ''))})...")
                log_path = os.path.join(self.project_root, "koboldcpp.log")
                with open(log_path, "a", encoding="utf-8") as f_log:
                    subprocess.Popen(
                        spec["cmd"],
                        cwd=spec["cwd"],
                        stdout=f_log,
                        stderr=f_log,
                        **popen_kwargs
                    )
                spawn_succeeded = True
            except Exception as e:
                logger.error(f"Self-healing failed to spawn KoboldCPP via direct spec: {e}")
                # Windows App Control (SAC / WDAC) or permission fallback via shell launcher
                if sys.platform == "win32":
                    try:
                        logger.info("Self-healing: Retrying KoboldCPP spawn via Windows shell launcher...")
                        quoted_parts = [f'"{c}"' if (' ' in c or '\\' in c) else c for c in spec["cmd"]]
                        cmd_line = f'start "" /b {" ".join(quoted_parts)}'
                        subprocess.Popen(f'cmd.exe /c "{cmd_line}"', cwd=spec["cwd"], shell=True)
                        spawn_succeeded = True
                    except Exception as e_shell:
                        logger.error(f"Self-healing shell launcher fallback also failed: {e_shell}")

            if spawn_succeeded:
                # Wait up to wait_seconds for model weights to load into VRAM
                for sec in range(1, max(5, int(wait_seconds)) + 1):
                    time.sleep(1)
                    if is_port_listening(5001):
                        # Give KoboldCPP a brief moment to finish binding endpoint
                        stat = self._check_kobold_port_health()
                        if stat.get("online"):
                            logger.info(f"Self-healing: KoboldCPP restored successfully in {sec}s.")
                            return True

        # 2. Legacy fallback search
        kcpp_name = "koboldcpp.exe" if sys.platform == "win32" else "koboldcpp"
        kcpp_exe = os.path.join(self.project_root, "tools", kcpp_name)
        if not os.path.isfile(kcpp_exe):
            which_kcpp = shutil.which("koboldcpp")
            if which_kcpp:
                kcpp_exe = which_kcpp

        # Locate model in models/
        models_dir = os.path.join(self.project_root, "models")
        model_path = None
        mmproj_path = None
        if os.path.isdir(models_dir):
            for f in os.listdir(models_dir):
                if f.endswith(".gguf") and "mmproj" not in f.lower():
                    model_path = os.path.join(models_dir, f)
                    break
            for f in os.listdir(models_dir):
                if f.endswith(".gguf") and "mmproj" in f.lower():
                    mmproj_path = os.path.join(models_dir, f)
                    break

        if not spawn_succeeded and os.path.isfile(kcpp_exe) and model_path:
            mm_args = ["--mmproj", mmproj_path] if mmproj_path else []
            gpu_layers = os.environ.get("LLM_GPU_LAYERS")
            if not gpu_layers:
                try:
                    import asset_manager
                    gpu_layers = str(asset_manager.detect_hardware_profile().get("recommended_llm_layers", 24))
                except Exception:
                    gpu_layers = "24"
            ctx_size = os.environ.get("LLM_CONTEXT_SIZE", "4096")
            threads = os.environ.get("LLM_THREADS", "4")
            cmd = [
                kcpp_exe, "--model", model_path,
                "--port", "5001",
                "--gpulayers", str(gpu_layers),
                "--contextsize", str(ctx_size),
                "--smartcontext",
                "--threads", str(threads)
            ] + mm_args
            if sys.platform == "win32":
                cmd += ["--usecublas", "normal", "--quiet"]
                popen_kwargs = {"creationflags": 0x08000000 | 0x00000200}
            else:
                cmd += ["--quiet"]
                popen_kwargs = {"start_new_session": True}

            try:
                logger.info(f"Self-healing: Spawning KoboldCPP LLM Server (fallback: {os.path.basename(model_path)})...")
                log_path = os.path.join(self.project_root, "koboldcpp.log")
                with open(log_path, "a", encoding="utf-8") as f_log:
                    subprocess.Popen(
                        cmd,
                        cwd=self.project_root,
                        stdout=f_log,
                        stderr=f_log,
                        **popen_kwargs
                    )
                for sec in range(1, 46):
                    time.sleep(1)
                    if is_port_listening(5001):
                        stat = self._check_kobold_port_health()
                        if stat.get("online"):
                            logger.info(f"Self-healing: KoboldCPP restored successfully in {sec}s.")
                            return True
            except Exception as e:
                logger.error(f"Self-healing failed to spawn KoboldCPP: {e}")
                if sys.platform == "win32":
                    try:
                        logger.info("Self-healing: Retrying fallback spawn via Windows shell launcher...")
                        quoted_parts = [f'"{c}"' if (' ' in c or '\\' in c) else c for c in cmd]
                        cmd_line = f'start "" /b {" ".join(quoted_parts)}'
                        subprocess.Popen(f'cmd.exe /c "{cmd_line}"', cwd=self.project_root, shell=True)
                        for sec in range(1, 46):
                            time.sleep(1)
                            if is_port_listening(5001):
                                stat = self.llm_client.check_health()
                                if stat.get("online"):
                                    logger.info(f"Self-healing: KoboldCPP restored successfully in {sec}s.")
                                    return True
                    except Exception as e_sh:
                        logger.error(f"Self-healing shell launcher fallback also failed: {e_sh}")

        # Check if Ollama on port 11434
        if "11434" in self.llm_client.base_url:
            ollama_bin = shutil.which("ollama")
            if ollama_bin and not is_port_listening(11434):
                try:
                    popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
                    subprocess.Popen([ollama_bin, "serve"], cwd=self.project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)
                    for _ in range(10):
                        time.sleep(1)
                        if is_port_listening(11434):
                            return True
                except Exception as e:
                    logger.error(f"Self-healing failed to start Ollama: {e}")

        return False

    def heal_comfyui(self) -> bool:
        """
        Attempts to automatically start or resurrect local ComfyUI generator (Port 8188).
        """
        if is_port_listening(8188):
            return True

        try:
            import asset_manager
            spec = asset_manager.get_comfyui_launch_spec()
            if not spec:
                return False

            spawned = False
            popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
            comfy_log = os.path.join(self.project_root, "comfyui.log")
            try:
                with open(comfy_log, "a", encoding="utf-8") as f_comfy:
                    logger.info("Self-healing: Spawning ComfyUI Photo Generator on port 8188...")
                    subprocess.Popen(
                        spec["cmd"],
                        cwd=spec["cwd"],
                        stdout=f_comfy,
                        stderr=f_comfy,
                        **popen_kwargs
                    )
                spawned = True
            except Exception as e_direct:
                logger.error(f"Self-healing direct spawn failed for ComfyUI: {e_direct}")
                if sys.platform == "win32":
                    try:
                        logger.info("Self-healing: Retrying ComfyUI spawn via Windows shell launcher...")
                        quoted_parts = [f'"{c}"' if (' ' in c or '\\' in c) else c for c in spec["cmd"]]
                        cmd_line = f'start "" /b {" ".join(quoted_parts)}'
                        subprocess.Popen(f'cmd.exe /c "{cmd_line}"', cwd=spec["cwd"], shell=True)
                        spawned = True
                    except Exception as e_sh:
                        logger.error(f"Self-healing shell launcher fallback for ComfyUI failed: {e_sh}")

            # Wait up to 25s for port 8188 to respond
            for _ in range(25):
                time.sleep(1)
                if is_port_listening(8188):
                    logger.info("Self-healing: ComfyUI generator restored successfully.")
                    return True
        except Exception as e:
            logger.error(f"Self-healing failed to spawn ComfyUI: {e}")

        return False

    def heal_music(self) -> bool:
        """
        Attempts to automatically start or resurrect YouTube Music Remote server (Port 8002).
        """
        if is_port_listening(8002):
            return True

        music_js = os.path.join(self.project_root, "music_player_server.js")
        if not os.path.exists(music_js):
            return False

        node_bin = "node"
        local_node = os.path.join(self.project_root, "tools", "nodejs", "node.exe" if sys.platform == "win32" else "bin/node")
        if not shutil.which("node") and os.path.isfile(local_node):
            node_bin = local_node

        if shutil.which(node_bin) or os.path.isfile(node_bin):
            try:
                popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
                logger.info("Self-healing: Spawning YouTube Music Server on port 8002...")
                subprocess.Popen(
                    [node_bin, music_js],
                    cwd=self.project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **popen_kwargs
                )
                for _ in range(8):
                    time.sleep(1)
                    if is_port_listening(8002):
                        logger.info("Self-healing: Music Server restored successfully.")
                        return True
            except Exception as e:
                logger.error(f"Self-healing failed to spawn Music Server: {e}")

        return False

    def heal_voicestudio(self) -> bool:
        """Attempts to start or resurrect VoiceStudio Local AI Voice Server (Port 3900)."""
        if is_port_listening(3900):
            return True
        try:
            from voicestudio_engine import voicestudio_engine
            if voicestudio_engine.is_installed():
                logger.info("Self-healing: Spawning VoiceStudio Local AI on port 3900...")
                return voicestudio_engine.start_service()
        except Exception as e:
            logger.error(f"Self-healing failed to spawn VoiceStudio: {e}")
        return False

    def heal_agy(self) -> bool:
        """Attempts to start or resurrect Google Antigravity (AGY) OpenAI Bridge (Port 8001)."""
        if is_port_listening(8001, timeout=1.5):
            return True
        agy_script = os.path.join(self.project_root, "agy_bridge.py")
        if not os.path.exists(agy_script):
            return False
        try:
            popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
            logger.info("Self-healing: Spawning AGY OpenAI Bridge on port 8001...")
            log_path = os.path.join(self.project_root, "agy_bridge.log")
            spawn_env = os.environ.copy()
            spawn_env["PYTHONIOENCODING"] = "utf-8"
            spawn_env["PYTHONUTF8"] = "1"
            with open(log_path, "a", encoding="utf-8") as f_log:
                subprocess.Popen([sys.executable, agy_script], cwd=self.project_root, stdout=f_log, stderr=f_log, env=spawn_env, **popen_kwargs)
            for _ in range(30):
                time.sleep(0.5)
                if is_port_listening(8001, timeout=1.5):
                    logger.info("Self-healing: AGY Bridge restored successfully on port 8001.")
                    return True
        except Exception as e:
            logger.error(f"Self-healing failed to spawn AGY Bridge: {e}")
        return False

    def attempt_heal_service(self, service: str, bot, recipients: List[int], is_manual: bool = False) -> bool:
        """
        Executes self-healing for a specific service with proactive Telegram status updates.
        """
        service_names = {
            "llm": "🧠 Server LLM / Kecerdasan",
            "comfyui": "🎨 Server Visual ComfyUI",
            "music": "🎵 Server Pemutar Musik PC",
            "voicestudio": "🎙️ VoiceStudio Local AI (Port 3900)",
            "agy": "🌉 AGY OpenAI Bridge (Port 8001)"
        }
        disp_name = service_names.get(service, service.upper())

        with self.lock:
            if not self.can_attempt_heal(service):
                history = self.heal_attempts.get(service, [])
                if len(history) >= self.max_heal_attempts_per_window:
                    # Only send failure alert once per heal window to prevent spamming Telegram every 30s
                    if not self.heal_limit_alert_sent.get(service, False):
                        self.heal_limit_alert_sent[service] = True
                        limit_text = (
                            f"🚨 **Self-Healing {disp_name} Gagal!**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"Waifu sudah mencoba me-restart service ini sebanyak {self.max_heal_attempts_per_window}x namun tetap mati / crash.\n\n"
                            f"👉 **Penyebab Kemungkinan**:\n"
                            f"• VRAM GPU / RAM PC tidak mencukupi untuk memuat model.\n"
                            f"• File binary atau model rusak / berpindah.\n\n"
                            f"Silakan periksa manual di PC kamu atau ketik `waifu start` di terminal."
                        )
                        markup = types.InlineKeyboardMarkup(row_width=2)
                        markup.add(
                            types.InlineKeyboardButton("🔄 Segarkan Status", callback_data="cfg_action:status"),
                            types.InlineKeyboardButton("⚙️ Menu Setup", callback_data="open_setup_menu")
                        )
                        for uid in recipients:
                            self.send_safe_message(bot, uid, limit_text, reply_markup=markup)
                return False

            self.healing_in_progress[service] = True
            self.heal_attempts.setdefault(service, []).append(time.time())
            attempt_num = len(self.heal_attempts[service])

        # Notify that self-healing has been initiated:
        # Only notify if this is a manual trigger OR attempt 1 to prevent spamming chat
        if is_manual or attempt_num == 1:
            init_text = (
                f"🩹 **Self-Healing Otomatis Aktif!**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Service **{disp_name}** terdeteksi mati!\n"
                f"Waifu sedang otomatis menghidupkan kembali service ini di latar belakang PC kamu (Percobaan {attempt_num}/{self.max_heal_attempts_per_window})... ⏳"
            )
            for uid in recipients:
                self.send_safe_message(bot, uid, init_text)

        success = False
        try:
            if service == "llm":
                success = self.heal_llm()
            elif service == "comfyui":
                success = self.heal_comfyui()
            elif service == "music":
                success = self.heal_music()
            elif service == "voicestudio":
                success = self.heal_voicestudio()
            elif service == "agy":
                success = self.heal_agy()
        finally:
            with self.lock:
                self.healing_in_progress[service] = False

        if success:
            with self.lock:
                self.heal_limit_alert_sent[service] = False
                if service == "llm":
                    self.last_llm_online = True
                    self.llm_offline_alert_sent = False
                    self.consecutive_llm_failures = 0
                elif service == "comfyui":
                    self.last_media_online = True

            succ_text = (
                f"🎉 **Self-Healing Berhasil!** 💕\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Hore! Service **{disp_name}** telah berhasil di-restart dan sekarang sudah normal kembali! 🥰\n\n"
                f"Waifu sudah siap digunakan normal lagi seperti biasa yaa~ ✨"
            )
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("📊 Cek Status", callback_data="cfg_action:status"),
                types.InlineKeyboardButton("💬 Sapa Waifu", callback_data="open_help_menu")
            )
            for uid in recipients:
                self.send_safe_message(bot, uid, succ_text, reply_markup=markup)
            logger.info(f"Self-healing successfully restored service: {service}")
            self._notify_recovery(service, {"online": True, "service": service})
            return True
            logger.info(f"Self-healing successfully restored service: {service}")
            self._notify_recovery(service, {"online": True, "service": service})
            return True
        else:
            logger.warning(f"Self-healing attempt {attempt_num} failed for service: {service}")
            return False

    def heal_all_services(self, bot, recipients: List[int]) -> Dict[str, bool]:
        """Manually or proactively scans all services and heals any offline components."""
        results = {}
        # 1. LLM
        stat = self.llm_client.check_health()
        if not stat.get("online"):
            results["llm"] = self.attempt_heal_service("llm", bot, recipients)
        else:
            results["llm"] = True

        # 2. ComfyUI
        if not is_port_listening(8188):
            try:
                import asset_manager
                if asset_manager.detect_comfyui_dir():
                    results["comfyui"] = self.attempt_heal_service("comfyui", bot, recipients)
            except Exception:
                pass

        # 3. Music Server
        music_js = os.path.join(self.project_root, "music_player_server.js")
        music_feat = os.environ.get("MUSIC_FEATURE_ENABLED", "true").lower() in ("true", "1", "yes")
        if music_feat and os.path.exists(music_js) and not is_port_listening(8002):
            results["music"] = self.attempt_heal_service("music", bot, recipients)

        # 4. VoiceStudio Local AI (if configured)
        v_backend = os.environ.get("VOICE_BACKEND", "edge-tts").lower().strip()
        if v_backend in ("voicestudio", "local") and not is_port_listening(3900):
            try:
                from voicestudio_engine import voicestudio_engine
                if voicestudio_engine.is_installed():
                    results["voicestudio"] = self.attempt_heal_service("voicestudio", bot, recipients)
            except Exception:
                pass

        # 5. AGY OpenAI Bridge (if configured)
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "").lower().strip()
        sfw_img = os.environ.get("SFW_IMAGE_ENGINE", "").lower().strip()
        if (sfw_p == "agy" or sfw_img == "agy") and not is_port_listening(8001):
            results["agy"] = self.attempt_heal_service("agy", bot, recipients)

        return results

    # --- Startup Announcement ---

    def notify_startup_ready(
        self,
        bot,
        recipients: List[int],
        persona: Dict[str, Any],
        max_wait_seconds: int = 15
    ):
        """
        Polls LLM for up to max_wait_seconds (giving KoboldCPP time to load weights on PC boot),
        then sends a startup announcement to all authorized users with service health details.
        """
        p_name = persona.get("name", "Waifu") if persona else "Waifu"
        logger.info(f"Checking service readiness on startup (waiting up to {max_wait_seconds}s for LLM)...")

        # Give local LLM time to load model weights (e.g. during PC boot autostart)
        stat = self.llm_client.check_health()
        deadline = time.time() + max_wait_seconds
        while not stat.get("online") and time.time() < deadline:
            time.sleep(2)
            stat = self.llm_client.check_health()

        is_llm_online = bool(stat.get("online"))
        is_smart_idle = bool(self.idle_engine and self.idle_engine.enabled)
        # Auto-heal LLM on startup ONLY if smart idle is disabled (otherwise LLM sleeps to save RAM/VRAM)
        if not is_llm_online and self.self_healing_enabled and not is_smart_idle:
            logger.info("LLM offline at startup (Smart Idle disabled). Attempting immediate self-healing...")
            if self.heal_llm():
                is_llm_online = True
                stat = self.llm_client.check_health()

        media_stat = self.media_engine.check_status() if self.media_engine else {"online": False}
        is_media_online = bool(media_stat.get("online"))

        with self.lock:
            self.last_llm_online = is_llm_online
            self.last_media_online = is_media_online
            if not is_llm_online:
                self.llm_offline_alert_sent = True
            else:
                self.llm_offline_alert_sent = False

        # Detect PC boot vs regular start
        uptime = get_system_uptime()
        is_pc_boot = (uptime is not None and uptime < 900)  # within 15 minutes of boot

        uptime_str = ""
        if uptime is not None:
            m, s = divmod(int(uptime), 60)
            h, m = divmod(m, 60)
            if h > 0:
                uptime_str = f" (Uptime PC: {h}j {m}m)"
            else:
                uptime_str = f" (Uptime PC: {m}m {s}s)"

        if is_pc_boot:
            header = f"🖥️ **PC Baru Saja Menyala & {p_name} Siap!** 🌸"
            greeting = f"Halo! PC kamu baru saja nyala dan aku sudah aktif di background siap nemenin kamu hari ini! 🥰"
        else:
            header = f"✨ 🌸 **{p_name} on Telegram Sudah Online & Ready!** 🌸 ✨"
            greeting = f"Halo! Aku sudah online dan siap menemani obrolan serta aktivitasmu~ 🥰"

        # Service badges
        is_idle_sleeping = bool(self.idle_engine and self.idle_engine.enabled and self.idle_engine.is_llm_sleeping)
        if is_llm_online:
            llm_badge = f"🟢 **ONLINE** (`{stat.get('backend', 'KoboldCPP')}` - `{stat.get('model', 'Active Model')}`)"
        elif is_idle_sleeping:
            llm_badge = "💤 **STANDBY / TIDUR** (Mode Hemat Daya • Bangun Otomatis Saat Chat)"
        else:
            llm_badge = f"🔴 **OFFLINE / MATI** (`{self.llm_client.base_url}`)"

        is_comfy_ondemand = bool(self.idle_engine and self.idle_engine.enabled and self.idle_engine.comfyui_on_demand)
        if is_media_online:
            media_badge = f"🟢 **ONLINE** (`{media_stat.get('backend', 'ComfyUI Local')}`)"
        elif is_comfy_ondemand:
            media_badge = "💤 **ON-DEMAND** (Standby • Otomatis Aktif Saat Request Foto)"
        else:
            media_badge = "🟡 **Mode Cadangan / Vault Siap**"

        healing_badge = "🟢 **Aktif (Auto-Restart)**" if self.self_healing_enabled else "⚪ **Nonaktif**"
        power_badge = "🟢 **Aktif (Smart Idle)**" if (self.idle_engine and self.idle_engine.enabled) else "⚪ **Nonaktif**"

        status_body = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 **Kecerdasan (LLM)**: {llm_badge}\n"
            f"🎨 **Generator Foto** : {media_badge}\n"
            f"🎙️ **Voice & Audio**   : 🟢 **Aktif**\n"
            f"🩹 **Self-Healing**    : {healing_badge}\n"
            f"⚡ **Hemat Daya (Idle)**: {power_badge}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        warning_section = ""
        if not is_llm_online and not is_idle_sleeping:
            warning_section = (
                f"\n\n⚠️ **PERHATIAN: Service LLM Belum Aktif!**\n"
                f"Otak waifu belum terhubung ke server LLM (`{self.llm_client.base_url}`).\n"
                f"👉 Buka aplikasi KoboldCPP / Ollama atau jalankan `waifu start` di PC agar aku bisa diajak ngobrol normal ya!"
            )

        footer = f"\n\n💡 _Ketik apa saja untuk menyapa atau klik tombol di bawah:_"

        full_message = f"{header}\n\n{greeting}{uptime_str}\n\n{status_body}{warning_section}{footer}"

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Status Diagnostik", callback_data="cfg_action:status"),
            types.InlineKeyboardButton("⚙️ Menu Setup", callback_data="open_setup_menu"),
            types.InlineKeyboardButton("🩹 Self-Heal Sekarang", callback_data="cfg_action:self_heal"),
            types.InlineKeyboardButton("❓ Panduan Lengkap", callback_data="open_help_menu")
        )

        for uid in recipients:
            self.send_safe_message(bot, uid, full_message, reply_markup=markup)

        self.startup_notified = True
        logger.info(f"Startup ready notification sent to {len(recipients)} recipient(s). LLM online={is_llm_online}")
        if is_llm_online:
            self._notify_recovery("llm", stat)

    def broadcast_failure(self, bot, recipients: List[int], stat: Dict[str, Any]):
        """Alerts all users that the local LLM service has crashed or become unreachable."""
        now = time.time()
        last_alert = self.last_failure_alert_time.get("llm", 0)
        if (now - last_alert) < self.alert_cooldown_seconds:
            logger.info(f"LLM failure alert suppressed by cooldown ({int(now - last_alert)}s / {self.alert_cooldown_seconds}s)")
            return
        self.last_failure_alert_time["llm"] = now

        error_info = stat.get("error") or f"Tidak dapat terhubung ke {self.llm_client.base_url}"
        alert_text = (
            f"🚨 **PERINGATAN: SERVICE LLM MATI!** 🚨\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Koneksi ke service LLM lokal tiba-tiba terputus atau server mati!\n\n"
            f"❌ **Detail Kendala**: `{error_info}`\n"
            f"⚠️ **Dampak**: Waifu tidak bisa memproses obrolan cerdas sampai server LLM dinyalakan kembali.\n\n"
            f"🔧 **Langkah Cepat Mengatasi**:\n"
            f"1. Klik tombol **🩹 Self-Heal Sekarang** di bawah agar waifu menyalakan server otomatis.\n"
            f"2. Atau buka terminal di PC lalu jalankan: `waifu start`\n\n"
            f"Aku akan terus memantau setiap {self.check_interval} detik dan mengabari kamu otomatis begitu server kembali online! ✨"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🩹 Self-Heal Sekarang", callback_data="cfg_action:self_heal"),
            types.InlineKeyboardButton("🔄 Segarkan Status", callback_data="cfg_action:status"),
            types.InlineKeyboardButton("⚙️ Menu Setup", callback_data="open_setup_menu")
        )
        for uid in recipients:
            self.send_safe_message(bot, uid, alert_text, reply_markup=markup)
        logger.warning(f"Sent LLM service offline alert to {len(recipients)} recipient(s).")

    def broadcast_recovery(self, bot, recipients: List[int], stat: Dict[str, Any]):
        """Notifies all users that the local LLM service has recovered and is healthy again."""
        now = time.time()
        last_alert = self.last_recovery_alert_time.get("llm", 0)
        if (now - last_alert) < self.alert_cooldown_seconds:
            logger.info(f"LLM recovery alert suppressed by cooldown ({int(now - last_alert)}s / {self.alert_cooldown_seconds}s)")
            return
        self.last_recovery_alert_time["llm"] = now

        backend = stat.get("backend", "KoboldCPP")
        model = stat.get("model", "Active Model")
        rec_text = (
            f"✅ **SERVICE LLM TELAH PULIH KEMBALI!** 💕\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Hore kabar baik! Server LLM lokal sudah aktif dan merespon normal kembali!\n\n"
            f"🧠 **Backend** : `{backend}`\n"
            f"📦 **Model**   : `{model}`\n"
            f"🌐 **Endpoint**: `{self.llm_client.base_url}`\n\n"
            f"Otak waifu sudah kembali normal dan siap diajak ngobrol seperti biasa yaa 🥰 Yuk lanjut ngobrol~"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Cek Status", callback_data="cfg_action:status"),
            types.InlineKeyboardButton("⚙️ Menu Setup", callback_data="open_setup_menu")
        )
        for uid in recipients:
            self.send_safe_message(bot, uid, rec_text, reply_markup=markup)
        logger.info(f"Sent LLM service recovery alert to {len(recipients)} recipient(s).")

    def mark_llm_failure(self, bot=None, get_recipients_func=None, error_msg: Optional[str] = None):
        """Immediately records an LLM failure encountered during conversation and triggers self-healing if service is down."""
        # Sanity check: if LLM server is actually still online and responsive (e.g. error was transient or single turn timeout),
        # do NOT trigger false offline alarms or flapping self-healing loops!
        try:
            stat = self.llm_client.check_health()
            if isinstance(stat, dict) and stat.get("online") is True:
                logger.info(f"mark_llm_failure called on chat turn error ('{error_msg}'), but LLM endpoint is healthy. Suppressing offline alarm.")
                return
        except Exception:
            pass

        with self.lock:
            self.last_llm_online = False
            self.consecutive_llm_failures += 1
            should_alert = not self.llm_offline_alert_sent
            if should_alert:
                self.llm_offline_alert_sent = True

        recipients = get_recipients_func() if get_recipients_func else []

        if should_alert and bot and recipients:
            err_stat = {"online": False, "error": error_msg or f"Koneksi gagal ke {self.llm_client.base_url}"}
            self.broadcast_failure(bot, recipients, err_stat)

        # Trigger self-healing in background thread
        if self.self_healing_enabled and bot and recipients:
            threading.Thread(
                target=self.attempt_heal_service,
                args=("llm", bot, recipients, False),
                daemon=True
            ).start()

    def _monitor_loop(self, bot, get_recipients_func: Callable[[], List[int]]):
        """Continuous background loop checking LLM & services health and self-healing when down."""
        logger.info(f"Service Health Watchdog active (Interval: {self.check_interval}s, Self-Healing: {self.self_healing_enabled})")
        while self._running:
            time.sleep(self.check_interval)
            if not self.enabled:
                continue

            try:
                recipients = get_recipients_func()
                # 1. LLM Health Check
                stat = self.llm_client.check_health()
                online = bool(stat.get("online"))
                is_sleeping = bool(self.idle_engine and self.idle_engine.enabled and self.idle_engine.is_llm_sleeping)

                with self.lock:
                    if online:
                        self.consecutive_llm_failures = 0
                        was_offline = (self.last_llm_online is False or self.llm_offline_alert_sent)
                        self.last_llm_online = True
                        if was_offline:
                            self.llm_offline_alert_sent = False
                            self.broadcast_recovery(bot, recipients, stat)
                            self._notify_recovery("llm", stat)
                    elif not is_sleeping:
                        self.consecutive_llm_failures += 1
                        should_alert = (self.consecutive_llm_failures >= 2) and not self.llm_offline_alert_sent
                        if should_alert:
                            self.last_llm_online = False
                            self.llm_offline_alert_sent = True
                            self.broadcast_failure(bot, recipients, stat)

                # If LLM is offline, not intentionally sleeping, and self-healing enabled, attempt automatic self-healing
                if not online and not is_sleeping and self.self_healing_enabled and self.can_attempt_heal("llm"):
                    self.attempt_heal_service("llm", bot, recipients, is_manual=False)

                # 2. Auxiliary Check: ComfyUI (Port 8188)
                is_comfy_ondemand = bool(self.idle_engine and self.idle_engine.enabled and (self.idle_engine.comfyui_on_demand or self.idle_engine.is_comfyui_sleeping))
                if not is_comfy_ondemand and self.self_healing_enabled and not is_port_listening(8188) and self.can_attempt_heal("comfyui"):
                    try:
                        import asset_manager
                        if asset_manager.detect_comfyui_dir():
                            self.attempt_heal_service("comfyui", bot, recipients, is_manual=False)
                    except Exception:
                        pass

                # 3. Auxiliary Check: Music Server (Port 8002)
                music_js = os.path.join(self.project_root, "music_player_server.js")
                music_feat = os.environ.get("MUSIC_FEATURE_ENABLED", "true").lower() in ("true", "1", "yes")
                if self.self_healing_enabled and music_feat and os.path.exists(music_js) and not is_port_listening(8002) and self.can_attempt_heal("music"):
                    self.attempt_heal_service("music", bot, recipients, is_manual=False)

                # 4. Auxiliary Check: AGY OpenAI Bridge (Port 8001 - Keep alive if selected)
                sfw_p = os.environ.get("SFW_LLM_PROVIDER", "").lower().strip()
                nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "").lower().strip()
                sfw_img = os.environ.get("SFW_IMAGE_ENGINE", "").lower().strip()
                base_url = getattr(self.llm_client, "base_url", "")
                is_agy_target = (sfw_p == "agy" or nsfw_p == "agy" or sfw_img == "agy" or ":8001" in str(base_url))
                if is_agy_target and self.self_healing_enabled and not is_port_listening(8001, timeout=1.5) and self.can_attempt_heal("agy"):
                    self.attempt_heal_service("agy", bot, recipients, is_manual=False)

            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")

    def start_monitor(self, bot, get_recipients_func: Callable[[], List[int]]):
        """Launches background health monitoring daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(bot, get_recipients_func),
            daemon=True
        )
        self._thread.start()

    def stop_monitor(self):
        """Stops the background monitoring loop."""
        self._running = False

    def get_status_summary(self) -> str:
        """Returns human-readable status for setup / diagnostic reports."""
        if not self.enabled:
            return "⚪ Nonaktif"
        status_icon = "🟢" if self.last_llm_online else "🔴"
        heal_str = "✓ Self-Healing Aktif" if self.self_healing_enabled else "Self-Healing Off"
        return f"{status_icon} Aktif ({heal_str} • Cek tiap {self.check_interval}s)"

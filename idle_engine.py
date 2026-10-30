import os
import sys
import time
import shutil
import logging
import threading
import subprocess
import platform
from typing import Optional, Dict, Any, Callable

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
                self.idle_timeout_minutes = max(1, int(os.environ.get("IDLE_TIMEOUT_MINUTES", "10")))
            except Exception:
                self.idle_timeout_minutes = 10

        if comfyui_on_demand is not None:
            self.comfyui_on_demand = comfyui_on_demand
        else:
            self.comfyui_on_demand = os.environ.get("COMFYUI_ON_DEMAND", "true").lower() in ("true", "1", "yes")

        self.comfyui_timeout_minutes = 5  # ComfyUI unloads 5 mins after last photo request
        self.last_llm_activity = time.time()
        self.last_comfyui_activity = time.time()

        self.is_llm_sleeping = False
        self.is_comfyui_sleeping = False

        self.wake_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def record_activity(self, is_media: bool = False):
        """Records user interaction timestamp to reset idle countdown."""
        now = time.time()
        with self.state_lock:
            self.last_llm_activity = now
            if is_media:
                self.last_comfyui_activity = now

    def is_llm_ready(self) -> bool:
        """Checks if KoboldCPP / LLM service is online and listening on port 5001."""
        if not is_port_listening(5001):
            return False
        if self.health_engine and hasattr(self.health_engine, "llm_client"):
            try:
                stat = self.health_engine.llm_client.check_health()
                return bool(stat.get("online"))
            except Exception:
                return True
        return True

    def is_comfyui_ready(self) -> bool:
        """Checks if ComfyUI service is online and listening on port 8188."""
        return is_port_listening(8188)

    def sleep_llm(self) -> bool:
        """Puts KoboldCPP LLM to sleep, freeing all GPU VRAM and model RAM."""
        with self.wake_lock:
            if not is_port_listening(5001):
                self.is_llm_sleeping = True
                return True

            logger.info("💤 Smart Idle: Terminating KoboldCPP LLM to free VRAM & RAM...")
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/IM", "koboldcpp.exe"],
                        capture_output=True,
                        creationflags=0x08000000
                    )
                else:
                    subprocess.run(["pkill", "-9", "-f", "koboldcpp"], capture_output=True)
                
                time.sleep(1)
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
                
                time.sleep(1)
                self.is_comfyui_sleeping = True
                logger.info("✓ Smart Idle: ComfyUI put to sleep. VRAM successfully freed!")
                return True
            except Exception as e:
                logger.error(f"Error putting ComfyUI to sleep: {e}")
                return False

    def wake_llm(self, timeout_seconds: int = 25) -> bool:
        """
        Wakes KoboldCPP on-demand.
        Loads model weights into VRAM and waits until port 5001 is responsive.
        """
        with self.wake_lock:
            if self.is_llm_ready():
                self.is_llm_sleeping = False
                self.record_activity()
                return True

            logger.info("⚡ Smart Idle: Waking KoboldCPP LLM on-demand...")

            # Use HealthEngine heal_llm if available
            started = False
            if self.health_engine and hasattr(self.health_engine, "heal_llm"):
                started = self.health_engine.heal_llm()
            else:
                # Direct launch fallback
                kcpp_name = "koboldcpp.exe" if sys.platform == "win32" else "koboldcpp"
                kcpp_exe = os.path.join(self.project_root, "tools", kcpp_name)
                if not os.path.isfile(kcpp_exe):
                    which_kcpp = shutil.which("koboldcpp")
                    if which_kcpp:
                        kcpp_exe = which_kcpp

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

                if os.path.isfile(kcpp_exe) and model_path:
                    mm_args = ["--mmproj", mmproj_path] if mmproj_path else []
                    cmd = [
                        kcpp_exe, "--model", model_path,
                        "--port", "5001",
                        "--gpulayers", "99",
                        "--contextsize", "4096",
                        "--smartcontext",
                        "--threads", "4"
                    ] + mm_args
                    if sys.platform == "win32":
                        cmd += ["--usecublas", "normal", "--quiet"]
                        popen_kwargs = {"creationflags": 0x08000000 | 0x00000200}
                    else:
                        cmd += ["--quiet"]
                        popen_kwargs = {"start_new_session": True}
                    try:
                        subprocess.Popen(cmd, cwd=self.project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)
                        started = True
                    except Exception as e:
                        logger.error(f"Failed to launch KoboldCPP: {e}")

            if not started and not is_port_listening(5001):
                return False

            # Wait for port and readiness
            deadline = time.time() + timeout_seconds
            while time.time() < deadline:
                if self.is_llm_ready():
                    self.is_llm_sleeping = False
                    self.record_activity()
                    logger.info("✓ Smart Idle: KoboldCPP successfully awakened and ready!")
                    return True
                time.sleep(1)

            return False

    def wake_comfyui(self, timeout_seconds: int = 40) -> bool:
        """
        Wakes ComfyUI generator on-demand when a photo/video is requested.
        """
        with self.wake_lock:
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
                        with open(comfy_log, "a", encoding="utf-8") as f_comfy:
                            subprocess.Popen(spec["cmd"], cwd=spec["cwd"], stdout=f_comfy, stderr=f_comfy, **popen_kwargs)
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

    def ensure_llm_active(self, bot=None, chat_id: Optional[int] = None) -> bool:
        """
        Ensures LLM is active before answering messages.
        If sleeping, displays a friendly waking indicator and wakes KoboldCPP.
        """
        if not self.enabled:
            return True

        if self.is_llm_ready():
            self.record_activity()
            return True

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

        fb_thread = threading.Thread(target=_feedback_loop, daemon=True)
        fb_thread.start()
        try:
            ok = self.wake_llm()
        finally:
            stop_feedback.set()
            fb_thread.join(timeout=1.0)

        # Clean up temporary status message
        if waking_msg and bot and chat_id:
            try:
                bot.delete_message(chat_id, waking_msg.message_id)
            except Exception:
                pass

        self.record_activity()
        return ok

    def ensure_comfyui_active(self, bot=None, chat_id: Optional[int] = None) -> bool:
        """
        Ensures ComfyUI is active before generating photos/videos on-demand.
        """
        if not self.enabled or not self.comfyui_on_demand:
            return True

        if self.is_comfyui_ready():
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
            try:
                bot.delete_message(chat_id, waking_msg.message_id)
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
        llm_state = "💤 Tidur (VRAM Bebas)" if self.is_llm_sleeping else ("🟢 Online" if is_port_listening(5001) else "💤 Standby")
        comfy_state = "💤 Standby On-Demand" if self.comfyui_on_demand else ("🟢 Online" if is_port_listening(8188) else "🔴 Offline")
        return f"🟢 Aktif (Idle Timeout: {self.idle_timeout_minutes}m • LLM: {llm_state} • Foto: {comfy_state})"

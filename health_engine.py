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
            "music": []
        }
        self.healing_in_progress: Dict[str, bool] = {
            "llm": False,
            "comfyui": False,
            "music": False
        }
        self.max_heal_attempts_per_window: int = 3
        self.heal_window_seconds: int = 900  # 15 minutes
        self.heal_cooldown_seconds: int = 45

        self.startup_notified: bool = False
        self.lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

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

        if len(history) >= self.max_heal_attempts_per_window:
            return False

        if history and (now - history[-1]) < self.heal_cooldown_seconds:
            return False

        return True

    def heal_llm(self) -> bool:
        """
        Attempts to automatically start or resurrect the local LLM service (KoboldCPP / Ollama).
        Returns True if service is running and healthy.
        """
        if is_port_listening(5001):
            stat = self.llm_client.check_health()
            if stat.get("online"):
                return True

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
                logger.info(f"Self-healing: Spawning KoboldCPP LLM Server ({os.path.basename(model_path)})...")
                subprocess.Popen(
                    cmd,
                    cwd=self.project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **popen_kwargs
                )
                # Wait up to 15s for model weights to load into VRAM
                for _ in range(15):
                    time.sleep(1)
                    if is_port_listening(5001):
                        stat = self.llm_client.check_health()
                        if stat.get("online"):
                            logger.info("Self-healing: KoboldCPP restored successfully.")
                            return True
            except Exception as e:
                logger.error(f"Self-healing failed to spawn KoboldCPP: {e}")

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

            popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
            comfy_log = os.path.join(self.project_root, "comfyui.log")
            with open(comfy_log, "a", encoding="utf-8") as f_comfy:
                logger.info("Self-healing: Spawning ComfyUI Photo Generator on port 8188...")
                subprocess.Popen(
                    spec["cmd"],
                    cwd=spec["cwd"],
                    stdout=f_comfy,
                    stderr=f_comfy,
                    **popen_kwargs
                )

            # Wait up to 15s for port 8188 to respond
            for _ in range(15):
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

    def attempt_heal_service(self, service: str, bot, recipients: List[int]) -> bool:
        """
        Executes self-healing for a specific service with proactive Telegram status updates.
        """
        service_names = {
            "llm": "🧠 Server LLM / Kecerdasan",
            "comfyui": "🎨 Server Visual ComfyUI",
            "music": "🎵 Server Pemutar Musik PC"
        }
        disp_name = service_names.get(service, service.upper())

        with self.lock:
            if not self.can_attempt_heal(service):
                history = self.heal_attempts.get(service, [])
                if len(history) >= self.max_heal_attempts_per_window:
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

        # Notify that self-healing has been initiated
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
        finally:
            with self.lock:
                self.healing_in_progress[service] = False

        if success:
            with self.lock:
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
        # Auto-heal LLM on startup if still offline and self-healing enabled
        if not is_llm_online and self.self_healing_enabled:
            logger.info("LLM offline at startup. Attempting immediate self-healing...")
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
            greeting = f"Halo sayang! PC kamu baru saja nyala dan aku sudah aktif di background siap nemenin kamu hari ini! 🥰"
        else:
            header = f"✨ 🌸 **{p_name} on Telegram Sudah Online & Ready!** 🌸 ✨"
            greeting = f"Halo sayang! Aku sudah online dan siap menemani obrolan serta aktivitasmu~ 🥰"

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

    def broadcast_failure(self, bot, recipients: List[int], stat: Dict[str, Any]):
        """Alerts all users that the local LLM service has crashed or become unreachable."""
        error_info = stat.get("error") or f"Tidak dapat terhubung ke {self.llm_client.base_url}"
        alert_text = (
            f"🚨 **PERINGATAN: SERVICE LLM MATI!** 🚨\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Sayang, koneksi ke service LLM lokal tiba-tiba terputus atau server mati!\n\n"
            f"❌ **Detail Kendala**: `{error_info}`\n"
            f"⚠️ **Dampak**: Waifu tidak bisa memproses obrolan cerdas sampai server LLM dinyalakan kembali.\n\n"
            f"🔧 **Langkah Cepat Mengatasi**:\n"
            f"1. Klik tombol **🩹 Self-Heal Sekarang** di bawah agar waifu menyalakan server otomatis.\n"
            f"2. Atau buka terminal di PC lalu jalankan: `waifu start`\n\n"
            f"Aku akan terus memantau setiap {self.check_interval} detik dan mengabari kamu otomatis begitu server kembali online! 💕"
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
        backend = stat.get("backend", "KoboldCPP")
        model = stat.get("model", "Active Model")
        rec_text = (
            f"✅ **SERVICE LLM TELAH PULIH KEMBALI!** 💕\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Hore kabar baik sayang! Server LLM lokal sudah aktif dan merespon normal kembali!\n\n"
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
        """Immediately records an LLM failure encountered during conversation and triggers self-healing."""
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
                args=("llm", bot, recipients),
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
                    elif not is_sleeping:
                        self.consecutive_llm_failures += 1
                        should_alert = (self.consecutive_llm_failures >= 2 or self.last_llm_online is True) and not self.llm_offline_alert_sent
                        if should_alert:
                            self.last_llm_online = False
                            self.llm_offline_alert_sent = True
                            self.broadcast_failure(bot, recipients, stat)

                # If LLM is offline, not intentionally sleeping, and self-healing enabled, attempt automatic self-healing
                if not online and not is_sleeping and self.self_healing_enabled and self.can_attempt_heal("llm"):
                    self.attempt_heal_service("llm", bot, recipients)

                # 2. Auxiliary Check: ComfyUI (Port 8188)
                is_comfy_ondemand = bool(self.idle_engine and self.idle_engine.enabled and (self.idle_engine.comfyui_on_demand or self.idle_engine.is_comfyui_sleeping))
                if not is_comfy_ondemand and self.self_healing_enabled and not is_port_listening(8188) and self.can_attempt_heal("comfyui"):
                    try:
                        import asset_manager
                        if asset_manager.detect_comfyui_dir():
                            self.attempt_heal_service("comfyui", bot, recipients)
                    except Exception:
                        pass

                # 3. Auxiliary Check: Music Server (Port 8002)
                music_js = os.path.join(self.project_root, "music_player_server.js")
                music_feat = os.environ.get("MUSIC_FEATURE_ENABLED", "true").lower() in ("true", "1", "yes")
                if self.self_healing_enabled and music_feat and os.path.exists(music_js) and not is_port_listening(8002) and self.can_attempt_heal("music"):
                    self.attempt_heal_service("music", bot, recipients)

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

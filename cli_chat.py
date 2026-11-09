"""
cli_chat.py - Interactive CLI Chat Session with Waifu
Allows chatting directly from terminal/CLI with full parity to Telegram chat:
- Shared persistent conversation history and memory with Telegram
- Natural personality, dynamic relationship progression (aku/kamu default)
- Active daily life story arc & student routine context
- Auto-opens generated photos (PAP) and videos in default system viewer
- Dynamic aesthetic loading spinners with multi-stage progress
"""

import os
import sys
import re
import time
import json
import logging
import threading
import subprocess
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from typing import Optional, Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from lu_llm_client import LocallyUncensoredClient
from routing_engine import get_hybrid_llm_client, detect_nsfw_intent
from persona_manager import PersonaManager
from memory_engine import MemoryEngine
from story_engine import StoryEngine
from media_engine import MediaEngine
from idle_engine import IdleEngine
from health_engine import HealthEngine
import student_schedule
from project_manager import get_project_manager
from computer_use_engine import get_computer_use_engine
from coding_engine import get_coding_engine

logger = logging.getLogger("WaifuCLI")

# Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def c(color, text):
    return f"{color}{text}{RESET}"


def open_media_file(file_path: str):
    """Opens image or video file directly in the OS default viewer/player."""
    if not file_path or not os.path.exists(file_path):
        return
    try:
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", file_path], check=False)
        else:
            subprocess.run(["xdg-open", file_path], check=False)
    except Exception as e:
        logger.warning(f"Failed to open media file automatically: {e}")


def get_default_user_id() -> int:
    """Returns primary user ID matching Telegram configuration."""
    raw = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()
    for part in raw.replace(",", " ").split():
        try:
            return int(part.strip())
        except ValueError:
            pass

    # Check memories.json profiles
    mem_file = os.path.join(PROJECT_ROOT, "data", "memories.json")
    if os.path.exists(mem_file):
        try:
            with open(mem_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                profs = list(data.get("profiles", {}).keys())
                for p in profs:
                    if str(p).isdigit():
                        return int(p)
        except Exception:
            pass

    return 1


class CLILoader:
    """
    Aesthetic, smooth, thread-safe CLI spinner & multi-stage status indicator.
    Supports animated braille spinner frames, elapsed timer, stage updates, and graceful fallback.
    """
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, text: str = "Memuat...", emoji: str = "🌸", color: str = MAGENTA):
        self.text = text
        self.emoji = emoji
        self.color = color
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time = time.time()
        self.is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def set_status(self, text: str, emoji: Optional[str] = None, color: Optional[str] = None):
        """Thread-safely updates the status message and optional emoji/color."""
        self.text = text
        if emoji:
            self.emoji = emoji
        if color:
            self.color = color
        if not self.is_tty:
            sys.stdout.write(f"  {self.emoji} {self.text}\n")
            sys.stdout.flush()

    def _spin(self):
        idx = 0
        try:
            if self.is_tty:
                sys.stdout.write("\033[?25l")
                sys.stdout.flush()

            while not self._stop_event.is_set():
                frame = self.SPINNER_FRAMES[idx % len(self.SPINNER_FRAMES)]
                elapsed = time.time() - self._start_time
                line = f"\r\033[K  {self.emoji} {c(self.color, frame)} {c(BOLD, self.text)} {c(DIM, f'({elapsed:.1f}s)')}"
                sys.stdout.write(line)
                sys.stdout.flush()
                idx += 1
                if self._stop_event.wait(0.08):
                    break
        except Exception:
            pass
        finally:
            if self.is_tty:
                sys.stdout.write("\r\033[K\033[?25h")
                sys.stdout.flush()

    def start(self):
        self._start_time = time.time()
        self._stop_event.clear()
        if self.is_tty:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            sys.stdout.write(f"  {self.emoji} {self.text}...\n")
            sys.stdout.flush()
        return self

    def stop(self, success_message: Optional[str] = None, emoji: str = "✓"):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.4)
        self._thread = None
        if self.is_tty:
            sys.stdout.write("\r\033[K\033[?25h")
            if success_message:
                elapsed = time.time() - self._start_time
                sys.stdout.write(f"  {c(GREEN, emoji)} {c(DIM, success_message)} {c(DIM, f'({elapsed:.1f}s)')}\n")
            sys.stdout.flush()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class WaifuCLISession:
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id or get_default_user_id()
        self.output_dir = os.path.join(PROJECT_ROOT, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize engines
        self.llm_base_url = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:5001/v1")
        self.llm_api_key = os.environ.get("LLM_API_KEY", "kobold")
        self.comfyui_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
        self.default_persona = os.environ.get("DEFAULT_PERSONA", "runa")
        self.bot_language = os.environ.get("BOT_LANGUAGE", "id")

        self.llm_client = get_hybrid_llm_client()
        self.persona_mgr = PersonaManager(active_key=self.default_persona)
        self.memory_engine = MemoryEngine()
        self.story_engine = StoryEngine()
        self.media_engine = MediaEngine(comfyui_url=self.comfyui_url, allow_cloud_fallback=False)

        self.health_engine = HealthEngine(llm_client=self.llm_client, media_engine=self.media_engine)
        self.idle_engine = IdleEngine(
            health_engine=self.health_engine,
            project_root=PROJECT_ROOT,
            enabled=os.environ.get("SMART_IDLE_ENABLED", "true").lower() in ("true", "1", "yes"),
            idle_timeout_minutes=int(os.environ.get("IDLE_TIMEOUT_MINUTES", "10")),
            comfyui_on_demand=os.environ.get("COMFYUI_ON_DEMAND", "true").lower() in ("true", "1", "yes")
        )
        self.health_engine.idle_engine = self.idle_engine
        self.project_manager = get_project_manager()
        self.coding_engine = get_coding_engine()
        self.computer_use_engine = get_computer_use_engine()

    def print_welcome_banner(self):
        persona = self.persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")
        p_arch = persona.get("archetype", "AI Companion")
        ep = self.story_engine.get_today_story(self.persona_mgr.active_key)
        story_title = ep.get("arc_title", "Kehidupan Sehari-hari") if ep else "Santai di Rumah"
        story_theme = ep.get("day_theme", "Aktivitas Harian") if ep else "Santai"

        history_len = len(self.persona_mgr.get_chat_history(self.user_id))

        print(c(BOLD + MAGENTA, "╔════════════════════════════════════════════════════════════════════════╗"))
        print(c(BOLD + MAGENTA, f"║  💖 WAIFU ON TELEGRAM - INTERACTIVE CLI CHAT SESSION 🌸                ║"))
        print(c(BOLD + MAGENTA, "╚════════════════════════════════════════════════════════════════════════╝"))
        print(f"  • {c(BOLD + CYAN, 'Persona Aktif')}  : {c(BOLD + GREEN, p_name)} ({p_arch})")
        print(f"  • {c(BOLD + CYAN, 'Cerita Hari Ini')}: {story_title} (Hari ini: {story_theme})")
        print(f"  • {c(BOLD + CYAN, 'Riwayat Chat')}   : {history_len} pesan tersinkronisasi dengan Telegram (User ID: {self.user_id})")
        print(f"  • {c(BOLD + CYAN, 'Media Auto-Open')}: Gambar & video akan otomatis terbuka di layar PC Anda!")
        active_proj = self.project_manager.get_active_project(self.user_id)
        proj_path = self.project_manager.get_active_project_path(self.user_id)
        cu_avail = self.computer_use_engine.is_available()
        print(f"  • {c(BOLD + CYAN, 'Workspace Aktif')}: {c(BOLD + GREEN, active_proj)} ({c(DIM, proj_path)})")
        print(f"  • {c(BOLD + CYAN, 'Computer Use')}   : {c(GREEN, '🟢 Ready (agent-desktop)') if cu_avail else c(YELLOW, '⚠️ Not Ready')}")
        print(c(DIM, "─" * 74))
        print(f"  {c(YELLOW, '💡 Ketik pesan lalu tekan Enter untuk mengobrol.')}")
        print(f"  {c(YELLOW, '💡 Perintah cepat:')} /pap {c(DIM, '(minta foto)')}, /video {c(DIM, '(minta video)')}, /story {c(DIM, '(cek cerita)')}, /clear, /exit")
        print(c(DIM, "─" * 74) + "\n")

    def handle_photo_request(self, user_text: str):
        """Generates photo, saves to output/, opens it automatically, and generates caption with smooth loading."""
        persona = self.persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")

        with CLILoader(f"{p_name} sedang menyiapkan foto untukmu...", emoji="📸") as loader:
            # Ensure ComfyUI active
            if getattr(self.idle_engine, "is_comfyui_sleeping", False):
                loader.set_status("Membangunkan ComfyUI & memeriksa GPU...", emoji="⚡")
            self.idle_engine.ensure_comfyui_active()

            loader.set_status("Menganalisis konsep visual & suasana outfit...", emoji="🎨")
            history = self.persona_mgr.get_chat_history(self.user_id)
            detected_scene = self.persona_mgr.extract_contextual_scene(
                user_text, user_id=self.user_id, llm_client=self.llm_client, history=history
            )
            if not detected_scene:
                story_photo = self.story_engine.get_story_photo_suggestion(self.persona_mgr.active_key)
                if story_photo and story_photo.get("danbooru_tags"):
                    detected_scene = story_photo["danbooru_tags"]

            visual_prompt, extra_neg, is_nude, outfit_label = self.persona_mgr.craft_visual_prompt_full(
                user_text, user_id=self.user_id, scene_override=detected_scene, history=history
            )

            neg_p = persona.get("negative_prompt", "")
            if extra_neg:
                neg_p += f", {extra_neg}"

            loader.set_status(f"Rendering difusi ComfyUI (Outfit: '{outfit_label}')...", emoji="✨")
            img_bytes, source = self.media_engine.generate_photo(
                visual_prompt,
                negative_prompt=neg_p,
                aspect_ratio="3:4",
                quality="high",
                persona=self.persona_mgr.active_key,
                scene=detected_scene,
                outfit_label=outfit_label,
                is_nude=is_nude,
                user_query=user_text
            )

            if not img_bytes:
                loader.stop()
                err = getattr(self.media_engine, "last_error", None) or "ComfyUI tidak merespon."
                print(f"⚠️ {c(RED, f'Gagal membuat foto: {err}')}\n")
                return

            loader.set_status("Menyimpan & membuka foto di layar...", emoji="🖼️")
            # Save to output/
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            f_name = f"{self.persona_mgr.active_key}_{ts}.jpg"
            save_path = os.path.join(self.output_dir, f_name)
            with open(save_path, "wb") as f:
                f.write(img_bytes)

            # Open automatically
            open_media_file(save_path)

            loader.set_status("Menulis pesan manis untuk fotonya...", emoji="💌")
            # Caption
            cap_prompt = [
                {
                    "role": "system",
                    "content": f"{persona.get('system_instruction', '')}\nWrite 1 natural, warm, and playful chat caption accompanying the photo you just sent. Under 2 sentences in casual Indonesian."
                },
                {
                    "role": "user",
                    "content": f"User asked: '{user_text}'. Give a cute caption for the photo."
                }
            ]
            caption, _ = self.llm_client.chat(cap_prompt, max_tokens=60)
            caption = caption.strip('"\n ') if caption else "Ini foto buat kamu, gimana menurutmu? 💕"

        print(f"✨ {c(GREEN, 'Foto berhasil dibuat & dibuka:')} {c(BOLD, save_path)}")
        print(f"🌸 {c(BOLD + MAGENTA, p_name)}: {caption}\n")

        # Save to history
        self.persona_mgr.add_message(self.user_id, "user", user_text)
        self.persona_mgr.add_message(self.user_id, "assistant", f"{caption} [PHOTO: {f_name}]")

    def handle_video_request(self, user_text: str):
        """Generates video animation, saves to output/, opens it automatically, and generates caption with smooth loading."""
        persona = self.persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")

        with CLILoader(f"{p_name} sedang membuat video klip animasi untukmu...", emoji="🎬") as loader:
            if getattr(self.idle_engine, "is_comfyui_sleeping", False):
                loader.set_status("Membangunkan ComfyUI & memeriksa engine video...", emoji="⚡")
            self.idle_engine.ensure_comfyui_active()

            loader.set_status("Merancang scene & frame visual gerakan...", emoji="🎨")
            visual_prompt, _, _, outfit_label = self.persona_mgr.craft_visual_prompt_full(
                user_text, user_id=self.user_id
            )

            v_eng = os.environ.get("VIDEO_ENGINE", "animatediff")
            loader.set_status(f"Rendering animasi neural video ({v_eng})...", emoji="🎥")
            video_bytes, source = self.media_engine.generate_video(
                visual_prompt=visual_prompt,
                aspect_ratio="3:4"
            )

            if not video_bytes:
                loader.stop()
                print(f"⚠️ {c(RED, 'Gagal membuat video klip animasinya...')}\n")
                return

            loader.set_status("Menyimpan & memutar video klip di layar...", emoji="✨")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            f_name = f"{self.persona_mgr.active_key}_{ts}.mp4"
            save_path = os.path.join(self.output_dir, f_name)
            with open(save_path, "wb") as f:
                f.write(video_bytes)

            open_media_file(save_path)

        print(f"✨ {c(GREEN, 'Video animasi berhasil dibuat & dibuka:')} {c(BOLD, save_path)}")
        caption = f"Ini video animasi pendek dari aku! Semoga kamu suka yaa ✨"
        print(f"🌸 {c(BOLD + MAGENTA, p_name)}: {caption}\n")

        self.persona_mgr.add_message(self.user_id, "user", user_text)
        self.persona_mgr.add_message(self.user_id, "assistant", f"{caption} [VIDEO: {f_name}]")

    def handle_coding_request(self, user_text: str):
        """Executes coding task inside active project directory with waifu persona."""
        persona = self.persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")
        active_proj = self.project_manager.get_active_project(self.user_id)

        with CLILoader(f"{p_name} sedang mengerjakan coding di '{active_proj}'...", emoji="💻"):
            reply_msg = self.coding_engine.execute_task(user_text, self.user_id)

        print(f"\n🌸 {c(BOLD + MAGENTA, p_name)}:\n{reply_msg}\n")
        self.persona_mgr.add_message(self.user_id, "user", user_text)
        self.persona_mgr.add_message(self.user_id, "assistant", reply_msg)

    def handle_computer_request(self, user_text: str):
        """Executes desktop / computer use task via agent-desktop."""
        persona = self.persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")

        with CLILoader(f"{p_name} sedang memeriksa layar & kontrol desktop...", emoji="🖥️"):
            reply_msg, screenshot_path = self.coding_engine.execute_computer_task(user_text, self.user_id)

        print(f"\n🌸 {c(BOLD + MAGENTA, p_name)}:\n{reply_msg}\n")
        if screenshot_path and os.path.exists(screenshot_path):
            print(f"📸 {c(GREEN, f'Membuka tangkapan layar desktop ({os.path.basename(screenshot_path)})...')}")
            open_media_file(screenshot_path)

        self.persona_mgr.add_message(self.user_id, "user", user_text)
        self.persona_mgr.add_message(self.user_id, "assistant", reply_msg)

    def process_message(self, user_text: str):
        """Processes one conversational turn with full story, memory, and routine injection."""
        persona = self.persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")

        # 1. Check user calling preference / pet name request
        user_prof = self.memory_engine.get_profile(self.user_id)
        user_call_pref = user_prof.get("call_name")
        user_allows_pet = user_prof.get("allow_pet_name", False)
        u_lower = user_text.lower()
        user_sent_pet = bool(re.search(r"\b(sayang|ayang|babe|bebe|darling|honey)\b", u_lower))
        user_asked_pet = bool(re.search(r"\bpanggil\s+(?:aku|saya)\s+(?:sayang|ayang|babe|bebe)\b", u_lower))

        if user_asked_pet or (user_allows_pet and user_call_pref == "sayang") or user_sent_pet:
            calling_guideline = (
                "ATURAN PANGGILAN & HUBUNGAN: Lawan bicaramu memanggilmu sayang atau mengizinkan/meminta dipanggil sayang. "
                "Kamu boleh memanggilnya 'sayang' secara hangat, manis, dan wajar."
            )
        elif user_call_pref:
            calling_guideline = (
                f"ATURAN PANGGILAN & HUBUNGAN: Panggil user dengan nama '{user_call_pref}'. "
                "Gunakan 'aku' dan 'kamu'. DILARANG memanggil 'sayang' karena user tidak memintanya."
            )
        else:
            calling_guideline = (
                "ATURAN PANGGILAN & HUBUNGAN (SANGAT PENTING): Gunakan kata ganti netral dan akrab 'aku' dan 'kamu'. "
                "DILARANG KERAS memanggil 'sayang', 'babe', 'ayang', atau panggilan mesra sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya! "
                "Kamu bukan langsung bertindak sebagai pacar jika belum diminta; bersikaplah sebagai teman ngobrol mahasiswi yang ramah, hangat, dan asyik. Biarkan dinamika hubungan berkembang secara alami sesuai kenyamanan user."
            )

        # 2. Hourly routine & Daily Story Arc
        cur_hour = time.localtime().tm_hour
        routine = student_schedule.get_hourly_routine(cur_hour, persona_key=self.persona_mgr.active_key)
        p_prof = student_schedule.STUDENT_PROFILES.get(self.persona_mgr.active_key.lower(), student_schedule.STUDENT_PROFILES["runa"])
        story_ctx = self.story_engine.get_story_prompt_context(self.persona_mgr.active_key)

        system_inst = persona.get("system_instruction", "")
        if story_ctx:
            system_inst += story_ctx
        system_inst += (
            f"\n\n[KEGIATAN MAHASISWI HARI INI]\n"
            f"Waktu sekarang: Jam {cur_hour:02d}:00. Kegiatanmu saat ini: {routine['activity_desc']}. "
            f"Kamu adalah mahasiswi ({p_prof['major']}).\n\n"
            "[PEDOMAN KOMUNIKASI - WAJIB DIPATUHI]\n"
            f"{calling_guideline}\n"
            "1. ANTI-MEMBEO (SANGAT PENTING): DILARANG KERAS hanya mengulang kata, mengulang frasa, atau menyalin ulang pesan lawan bicaramu!\n"
            "2. RESPONSIF & AKTIF: Berikan tanggapan aktif dan bermakna: ceritakan opinimu, komentar santai, atau tanyakan detail kelanjutannya.\n"
            f"3. FORMAT VISUAL NOVEL: Awali dengan 1 baris aksi panggung atau ekspresi fisik di dalam tanda bintang *...* menggunakan gaya narasi visual novel dengan namamu ({p_name}). Contoh: *{p_name} melihat kamu dengan senyuman hangat sambil merapikan rambutnya*. DILARANG menggunakan tanda minus/dash '- ... -' atau kata kaku 'kulihatmu'. Pisahkan dengan baris baru ganda sebelum dialog ucapan.\n"
            "4. GAYA CHAT: Maksimal 1-3 kalimat santai, mengalir alami, hangat, dan wajar.\n"
            "5. INISIATIF PAP SPONTAN: Kamu boleh sesekali berinisiatif mengirim foto selfie / PAP untuk menunjukkan kegiatan atau outfitmu saat ini. Jika momennya pas, tambahkan tag [ACTION: SEND_PAP] di akhir pesanmu.\n"
            "6. BAHASA PERCAKAPAN: Kamu WAJIB berbicara langsung dalam Bahasa Indonesia santai & akrab. DILARANG KERAS menuliskan proses berpikir atau monolog batin dalam bahasa Inggris."
        )

        mem_context = self.memory_engine.format_memory_context(self.user_id, query=user_text)
        if mem_context:
            system_inst += "\n" + mem_context

        history = self.persona_mgr.get_chat_history(self.user_id)
        messages = [{"role": "system", "content": system_inst}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        is_nsfw_turn = detect_nsfw_intent(user_text, messages)
        load_emoji = "💋" if is_nsfw_turn else "💭"
        load_msg = f"{p_name} sedang merespon (Mode Intim)..." if is_nsfw_turn else f"{p_name} sedang memikirkan balasan..."

        with CLILoader(load_msg, emoji=load_emoji) as loader:
            # Ensure LLM awake
            if getattr(self.idle_engine, "is_llm_sleeping", False):
                loader.set_status("Membangunkan KoboldCPP ke memori...", emoji="⚡")
            self.idle_engine.ensure_llm_active(is_nsfw=is_nsfw_turn)

            loader.set_status(f"{p_name} sedang mengetik...", emoji="💋" if is_nsfw_turn else "🌸")
            try:
                raw_reply, _ = self.llm_client.chat(messages, max_tokens=400, is_nsfw=is_nsfw_turn)
            except Exception as e:
                loader.stop()
                print(f"⚠️ {c(RED, f'Koneksi ke LLM lokal gagal: {e}')}\n")
                return

        if not raw_reply or not raw_reply.strip():
            raw_reply = "Ehh maaf, tadi aku agak melamun sebentar... Kamu ngomong apa tadi?"

        # Post-process
        clean_reply = re.sub(r'\[ACTION:\s*SEND_PAP\]', '', raw_reply, flags=re.IGNORECASE).strip()
        has_pap_action = "[action: send_pap]" in raw_reply.lower()

        # Print response
        print(f"\n🌸 {c(BOLD + MAGENTA, p_name)}: {clean_reply}\n")

        # Save turn to shared history
        self.persona_mgr.add_message(self.user_id, "user", user_text)
        self.persona_mgr.add_message(self.user_id, "assistant", raw_reply)

        # Auto extract facts
        self.memory_engine.auto_extract_facts(user_text, self.user_id)

        # If LLM triggered spontaneous PAP
        if has_pap_action:
            print(f"📸 {c(CYAN, f'{p_name} berinisiatif mengambil foto kegiatan untukmu...')}")
            photo_prompt = clean_reply or routine["activity_desc"]
            self.handle_photo_request(photo_prompt)

        # Replenish story arc if needed in background
        if self.story_engine.needs_replenishment(self.persona_mgr.active_key, days_ahead=3):
            self.story_engine.replenish_storylines_if_llm_active(self.persona_mgr.active_key, self.llm_client)

    def run_interactive_loop(self):
        """Starts the interactive CLI chat session."""
        self.print_welcome_banner()

        while True:
            try:
                user_input = input(c(BOLD + GREEN, "Kamu: ")).strip()
            except (KeyboardInterrupt, EOFError):
                persona = self.persona_mgr.get_active_persona()
                p_name = persona.get("name", "Waifu")
                print(f"\n\n🌸 {c(BOLD + MAGENTA, p_name)}: Sampai jumpa lagi yaa! Nanti kita lanjut ngobrol lagi~ 👋🥰")
                break

            if not user_input:
                continue

            low = user_input.lower()
            if low in ("/exit", "/quit", "/q", "exit", "quit", "bye", "keluar"):
                persona = self.persona_mgr.get_active_persona()
                p_name = persona.get("name", "Waifu")
                print(f"\n🌸 {c(BOLD + MAGENTA, p_name)}: Dadah! Sampai ketemu lagi yaa~ 👋🥰\n")
                break

            if low in ("/help", "/h", "help", "bantuan"):
                print(f"\n{c(BOLD + CYAN, '📖 PANDUAN CHAT CLI:')}")
                print("  • Ketik apa saja untuk mengobrol santai.")
                print("  • /pap atau minta foto ➔ Foto digenerate dan otomatis terbuka di layar!")
                print("  • /video atau minta video ➔ Video digenerate dan otomatis terbuka!")
                print("  • /story ➔ Melihat cerita & episode hidup waifu hari ini.")
                print("  • /projects ➔ Melihat & memilih project workspace coding.")
                print("  • /spawn <nama> ➔ Membuat folder project baru & langsung beralih.")
                print("  • /desktop ➔ Cek status Computer Use (agent-desktop).")
                print("  • /screen ➔ Screenshot layar desktop & tampilkan ke layar.")
                print("  • /persona [nama] ➔ Ganti karakter (runa, akira, hina, shiro, yume).")
                print("  • /clear ➔ Menghapus riwayat percakapan sesi ini.")
                print("  • /exit atau /quit ➔ Keluar dari sesi chat CLI.\n")
                continue

            if low in ("/story", "/cerita", "/arc", "/episode"):
                with CLILoader("Mengambil rangkuman cerita hari ini...", emoji="📖"):
                    persona = self.persona_mgr.get_active_persona()
                    card = self.story_engine.format_story_summary_card(self.persona_mgr.active_key, persona.get("name", "Waifu"))
                print(f"\n{card}\n")
                continue

            if low.startswith("/persona"):
                parts = user_input.split()
                if len(parts) > 1:
                    new_p = parts[1].lower()
                    if new_p in self.persona_mgr.personas:
                        with CLILoader(f"Memuat persona {new_p.capitalize()}...", emoji="🎭"):
                            self.persona_mgr.set_active_persona(new_p)
                            new_info = self.persona_mgr.get_active_persona()
                        print(f"✨ Berpindah ke persona: {c(BOLD + GREEN, new_info.get('name', new_p))} ({new_info.get('archetype', '')})\n")
                    else:
                        valid = ", ".join(self.persona_mgr.personas.keys())
                        print(f"⚠️ Persona '{new_p}' tidak ditemukan. Pilihan tersedia: {valid}\n")
                else:
                    curr = self.persona_mgr.get_active_persona()
                    print(f"ℹ️ Persona aktif saat ini: {c(BOLD + GREEN, curr.get('name'))}. Ketik '/persona <nama>' untuk mengganti.\n")
                continue

            if low in ("/projects", "/project", "/workspace"):
                curr = self.project_manager.get_active_project(self.user_id)
                curr_p = self.project_manager.get_active_project_path(self.user_id)
                root_d = self.project_manager.get_projects_root_dir()
                projs = self.project_manager.list_projects()

                print(f"\n{c(BOLD + CYAN, '💻 DAFTAR PROJECT WORKSPACE:')}")
                print(f"  • Root Directory : {c(DIM, root_d)}")
                print(f"  • Project Aktif  : {c(BOLD + GREEN, curr)} ({c(DIM, curr_p)})\n")
                for p_name, p_info in projs.items():
                    mark = c(BOLD + GREEN, "➔ [AKTIF]") if p_name == curr else "  [     ]"
                    p_disp = p_info if isinstance(p_info, str) else p_info.get('path', '')
                    print(f"  {mark} {c(BOLD, p_name)} : {c(DIM, p_disp)}")
                print(f"\n  {c(YELLOW, '💡 Ketik /project <nama> untuk beralih atau /spawn <nama> untuk buat baru.')}\n")
                continue

            if low.startswith("/project ") or low.startswith("/use "):
                target_p = user_input.split(None, 1)[1].strip()
                ok, res_path = self.project_manager.set_active_project(self.user_id, target_p)
                if ok:
                    new_path = self.project_manager.get_active_project_path(self.user_id)
                    print(f"✨ {c(GREEN, f'Berhasil beralih ke project: {target_p}')} ({c(DIM, new_path)})\n")
                else:
                    print(f"⚠️ Project '{target_p}' tidak ditemukan. Ketik /projects untuk melihat daftar.\n")
                continue

            if low.startswith("/spawn "):
                new_p = user_input.split(None, 1)[1].strip()
                ok, clean_p, path_or_err = self.project_manager.spawn_project(new_p, switch_user_id=self.user_id)
                if ok:
                    print(f"🎉 {c(GREEN, f'Project baru {clean_p} berhasil dibuat!')} Folder: {c(DIM, path_or_err)}\n")
                else:
                    print(f"⚠️ Gagal membuat project: {path_or_err}\n")
                continue

            if low.startswith("/setprojectsdir "):
                new_dir = user_input.split(None, 1)[1].strip()
                ok, path_or_err = self.project_manager.set_projects_root_dir(new_dir)
                if ok:
                    print(f"✅ {c(GREEN, 'Root directory projects berhasil diubah:')} {c(DIM, path_or_err)}\n")
                else:
                    print(f"❌ {path_or_err}\n")
                continue

            if low in ("/desktop", "/computer"):
                st = self.computer_use_engine.get_status()
                avail = self.computer_use_engine.is_available()
                plat = st.get("data", {}).get("platform", sys.platform)
                perm = st.get("data", {}).get("permissions", {}).get("accessibility", {}).get("state", "unknown")
                print(f"\n{c(BOLD + CYAN, '🖥️ STATUS COMPUTER USE (agent-desktop):')}")
                print(f"  • Status Adapter : {c(GREEN, '🟢 Ready') if avail else c(RED, '🔴 Not Available')}")
                print(f"  • Platform       : {plat}")
                print(f"  • Accessibility  : {perm}")
                print(f"  • Tooling        : Native Accessibility Tree & Screenshot\n")
                continue

            if low in ("/screen", "/screenshot"):
                with CLILoader("Mengambil tangkapan layar desktop...", emoji="📸"):
                    sc_path = self.computer_use_engine.capture_screenshot()
                if sc_path and os.path.exists(sc_path):
                    print(f"✅ Screenshot berhasil diambil: {c(DIM, sc_path)}")
                    open_media_file(sc_path)
                else:
                    print(f"⚠️ Gagal mengambil tangkapan layar.\n")
                continue

            if low in ("/clear", "/reset"):
                self.persona_mgr.clear_history(self.user_id)
                print(f"🧹 {c(GREEN, 'Riwayat obrolan sesi ini berhasil dibersihkan!')}\n")
                continue

            # Check if user specifically asking for photo/PAP
            is_pap_request = bool(re.search(r"\b(pap|foto|selfie|kirim foto|minta foto|liat foto)\b", low))
            is_video_request = bool(re.search(r"\b(video|animasi|klip|bergerak)\b", low))

            if self.coding_engine.is_computer_use_intent(user_input):
                self.handle_computer_request(user_input)
            elif self.coding_engine.is_coding_intent(user_input):
                self.handle_coding_request(user_input)
            elif low.startswith("/pap") or low.startswith("/foto") or (is_pap_request and not is_video_request):
                self.handle_photo_request(user_input)
            elif low.startswith("/video") or is_video_request:
                self.handle_video_request(user_input)
            else:
                self.process_message(user_input)


def start_cli_chat(user_id: Optional[int] = None):
    """Entry point for CLI interactive chat session."""
    session = WaifuCLISession(user_id=user_id)
    session.run_interactive_loop()


if __name__ == "__main__":
    start_cli_chat()

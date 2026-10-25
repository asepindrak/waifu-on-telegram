import os
import sys
import logging
import threading
import time
import datetime
import platform
import subprocess
from typing import Optional, Dict, Any, Tuple, List
from dotenv import load_dotenv
import telebot
from telebot import types

from lu_llm_client import LocallyUncensoredClient
from persona_manager import PersonaManager, build_custom_persona
from media_engine import MediaEngine
from voice_engine import VoiceEngine
from code_runner import CodeRunner
from memory_engine import MemoryEngine
from reminder_engine import ReminderEngine
from anniversary_engine import AnniversaryEngine
from setup import scan_local_llm_models, scan_image_models, setup_autostart, read_env, write_env

# Load environment configuration
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("WaifuOnTelegram")


def get_version() -> str:
    v_file = os.path.join(PROJECT_ROOT, "VERSION")
    if os.path.exists(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "1.3.1"


# Credentials & Permissions
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
RAW_ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()

ALLOWED_USER_IDS = []
for uid in RAW_ALLOWED_USERS.replace(",", " ").split():
    try:
        ALLOWED_USER_IDS.append(int(uid.strip()))
    except ValueError:
        pass

if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is not configured in .env! Run 'waifu setup' to configure.")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Initialize engines
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8127/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "auto")
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
MEDIA_FALLBACK = os.environ.get("MEDIA_FALLBACK_CLOUD", "true").lower() in ("true", "1", "yes")
VOICE_ENABLED = os.environ.get("VOICE_REPLY_ENABLED", "true").lower() in ("true", "1", "yes")
VOICE_NAME = os.environ.get("VOICE_NAME", "en-US-AnaNeural")
DEFAULT_PERSONA = os.environ.get("DEFAULT_PERSONA", "runa")

llm_client = LocallyUncensoredClient(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
persona_mgr = PersonaManager(active_key=DEFAULT_PERSONA)
media_engine = MediaEngine(comfyui_url=COMFYUI_URL, allow_cloud_fallback=MEDIA_FALLBACK)
memory_engine = MemoryEngine()
reminder_engine = ReminderEngine()
anniversary_engine = AnniversaryEngine()
voice_engine = VoiceEngine(
    voice_name=VOICE_NAME,
    groq_key=os.environ.get("GROQ_API_KEY"),
    openai_key=os.environ.get("OPENAI_API_KEY")
)

USER_VOICE_MODES: dict = {}      # user_id -> 'always' | 'match_vn' | 'off'
GREETINGS_ENABLED: dict = {}     # user_id -> bool
LAST_GREETING_SENT: dict = {}    # "YYYY-MM-DD:morning" -> True
USER_RATIOS: dict = {}           # user_id -> '3:4' | '9:16' | '1:1' | '4:3'
USER_QUALITIES: dict = {}        # user_id -> 'high' | 'ultra' | 'fast'
USER_DATE_WIZARD: dict = {}       # user_id -> 'birthday' | 'anniversary'


# --- Configuration Helper Functions ---

def is_autorun_enabled() -> bool:
    """Checks whether autostart at system boot is currently enabled."""
    if platform.system() == "Windows":
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        shortcut = os.path.join(startup_dir, "Start_Waifu_on_Telegram.lnk")
        return os.path.exists(shortcut)
    elif platform.system() == "Linux":
        try:
            cur_cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout or ""
            return "start_services.sh" in cur_cron
        except Exception:
            return False
    return False


def toggle_autorun_setting() -> bool:
    """Toggles autorun on startup and returns the new status."""
    new_state = not is_autorun_enabled()
    setup_autostart(enable=new_state)
    return new_state


def update_env_variable(key: str, value: str):
    """Persists configuration variable in both os.environ and .env file."""
    os.environ[key] = value
    try:
        env_vars = read_env()
        env_vars[key] = value
        write_env(env_vars)
    except Exception as e:
        logger.warning(f"Could not persist {key} to .env: {e}")


def apply_llm_choice(choice: str) -> str:
    global LLM_BASE_URL
    detected_llms = scan_local_llm_models()
    if choice == "auto":
        new_base = "http://127.0.0.1:8127/v1"
        new_model = "default"
        label = "Locally Uncensored (Auto-detect)"
    elif choice == "ollama":
        new_base = "http://127.0.0.1:11434/v1"
        new_model = "default"
        label = "Ollama (Port 11434)"
    elif choice.isdigit() and int(choice) < len(detected_llms):
        source, mname, mpath = detected_llms[int(choice)]
        new_base = "http://127.0.0.1:8127/v1" if source == "Locally Uncensored" else "http://127.0.0.1:11434/v1"
        new_model = mname
        label = mname
    else:
        return "Unknown"

    LLM_BASE_URL = new_base
    llm_client.base_url = new_base
    llm_client.model = new_model
    update_env_variable("LLM_BASE_URL", new_base)
    update_env_variable("LLM_MODEL", new_model)
    return label


def apply_ckpt_choice(choice: str) -> str:
    global COMFYUI_URL, MEDIA_FALLBACK
    detected_ckpts = scan_image_models()
    if choice == "auto":
        os.environ["COMFYUI_CHECKPOINT"] = ""
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"
        os.environ["MEDIA_FALLBACK_CLOUD"] = "true"
        media_engine.comfyui_url = "http://127.0.0.1:8188"
        media_engine.allow_cloud_fallback = True
        update_env_variable("COMFYUI_CHECKPOINT", "")
        update_env_variable("COMFYUI_URL", "http://127.0.0.1:8188")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "true")
        return "Auto (MeinaMix preferred)"
    elif choice == "cloud":
        os.environ["COMFYUI_URL"] = ""
        os.environ["MEDIA_FALLBACK_CLOUD"] = "true"
        media_engine.comfyui_url = ""
        media_engine.allow_cloud_fallback = True
        update_env_variable("COMFYUI_URL", "")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "true")
        return "Cloud Fallback (Pollinations)"
    elif choice == "disabled":
        os.environ["COMFYUI_URL"] = ""
        os.environ["MEDIA_FALLBACK_CLOUD"] = "false"
        media_engine.comfyui_url = ""
        media_engine.allow_cloud_fallback = False
        update_env_variable("COMFYUI_URL", "")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "false")
        return "Nonaktifkan Foto"
    elif choice.isdigit() and int(choice) < len(detected_ckpts):
        _, ckpt_name = detected_ckpts[int(choice)]
        os.environ["COMFYUI_CHECKPOINT"] = ckpt_name
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"
        media_engine.comfyui_url = "http://127.0.0.1:8188"
        update_env_variable("COMFYUI_CHECKPOINT", ckpt_name)
        update_env_variable("COMFYUI_URL", "http://127.0.0.1:8188")
        return ckpt_name
    return "Unknown"


def apply_voice_speaker(speaker: str) -> str:
    global VOICE_NAME
    mapping = {
        "ana": "en-US-AnaNeural",
        "gadis": "id-ID-GadisNeural",
        "nanami": "ja-JP-NanamiNeural",
        "jenny": "en-US-JennyNeural"
    }
    v_name = mapping.get(speaker, "en-US-AnaNeural")
    VOICE_NAME = v_name
    voice_engine.default_voice = v_name
    update_env_variable("VOICE_NAME", v_name)
    return v_name


class ChatActionLoop:
    """Continuously sends chat action (e.g. typing or upload_photo) every 3.5s so Telegram never drops status."""
    def __init__(self, bot_instance, chat_id: int, action: str = "typing"):
        self.bot = bot_instance
        self.chat_id = chat_id
        self.action = action
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while self.running:
            try:
                self.bot.send_chat_action(self.chat_id, self.action)
            except Exception:
                pass
            for _ in range(35):
                if not self.running:
                    break
                time.sleep(0.1)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False


def is_authorized(user_id: int) -> bool:
    """Verifies if the user is authorized to interact with the bot."""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


def get_persona_image_path(persona: dict):
    """Finds reference image file path for persona from personas/brief."""
    avatar_rel = persona.get("avatar_image", "")
    if avatar_rel:
        p = os.path.join(PROJECT_ROOT, avatar_rel)
        if os.path.exists(p):
            return p

    name = persona.get("name", "Runa")
    for ext in [".png", ".jpg", ".jpeg"]:
        candidate = os.path.join(PROJECT_ROOT, "personas", "brief", f"{name}{ext}")
        if os.path.exists(candidate):
            return candidate
        candidate_lower = os.path.join(PROJECT_ROOT, "personas", "brief", f"{name.lower()}{ext}")
        if os.path.exists(candidate_lower):
            return candidate_lower

    return None


@bot.message_handler(commands=['start'])
def handle_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "⛔ Access denied. Your Telegram User ID is not authorized.")
        return

    try:
        setup_bot_commands()
    except Exception:
        pass

    persona = persona_mgr.get_active_persona()
    name = persona.get("name", "Runa")
    archetype = persona.get("archetype", "AI Girlfriend")
    desc = persona.get("description", "")

    # Quick interactive action keyboard
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 Pap Foto Dong", callback_data="regen_photo:relaxing in modern cozy room"),
        types.InlineKeyboardButton("👗 Lemari Baju (/outfit)", callback_data="open_outfit_menu"),
        types.InlineKeyboardButton("🎭 Ganti Waifu (/persona)", callback_data="open_persona_menu"),
        types.InlineKeyboardButton("🧠 Buku Ingatan (/memory)", callback_data="open_memory_menu"),
        types.InlineKeyboardButton("⏰ Pengingat (/remind)", callback_data="open_reminders_menu"),
        types.InlineKeyboardButton("🎂 Ultah & Anniv (/birthday)", callback_data="open_dates_menu"),
        types.InlineKeyboardButton("💖 Cek Cinta (/love)", callback_data="check_love_status"),
        types.InlineKeyboardButton("⚙️ Panel Setup (/setup)", callback_data="open_setup_menu"),
        types.InlineKeyboardButton("❓ Buku Panduan (/help)", callback_data="open_help_menu")
    )

    # 1. Send Persona Reference Photo
    img_path = get_persona_image_path(persona)
    photo_sent = False
    if img_path and os.path.exists(img_path):
        bot.send_chat_action(message.chat.id, "upload_photo")
        try:
            caption = (
                f"💖 **Halo Sayang! Aku {name}** 👋🥰\n"
                f"*({archetype})*\n\n"
                f"_{desc}_\n\n"
                f"Senang banget kamu datang! Aku siap nemenin kamu ngobrol manis, dengerin curhat, kirim foto selfie, dan nemenin hari-harimu~ 💕"
            )
            with open(img_path, "rb") as f:
                bot.send_photo(message.chat.id, f, caption=caption, parse_mode="Markdown")
            photo_sent = True
        except Exception as e:
            logger.error(f"Error sending start photo: {e}")

    # 2. Send feature guide & commands
    guide_text = (
        f"✨ **Fitur Utama Bersama {name} (v{get_version()}):**\n"
        "• 💬 **Romance Chat**: Bebas sensor (SFW & NSFW), hangat, manja, dan otomatis ikut bahasamu.\n"
        "• 🧠 **Buku Ingatan Abadi**: Aku selalu mengingat fakta, kesukaan, dan hal penting tentang kamu (`/memory`)!\n"
        "• 📸 **Kirim Selfie & Foto**: Cukup ketik *'sayang pap foto dong'* atau `/pap` untuk membuka menu pose interaktif!\n"
        "• 🎵 **Remote Musik PC**: Putar lagu YouTube di PC langsung dari Telegram (`/play`, `/pause`, `/next`)!\n"
        "• 👗 **Pilihan Baju**: Pilih pakaian waifumu lewat `/outfit` (Kimono, Maid, Piyama, dll).\n"
        "• 🎙️ **Voice Note**: Balasan suara asli wanita jernih & manis (`/voice`).\n"
        "• ⚙️ **Panel Setup**: Atur seluruh konfigurasi bot dari Telegram (`/setup`).\n"
        "• ⏰ **Asisten & Pengingat**: Minta waifu ingetin jadwal lewat chat/voice note (`/remind`)!\n"
        "• ⏰ **Sapaan Otomatis**: Ucapan selamat pagi jam 7, makan siang 12:30 & tidur jam 10 malam (`/greetings`).\n"
        "• 👀 **AI Vision**: Kirimkan foto kamu ke sini, waifu bisa melihat dan meresponsnya.\n\n"
        "📌 **Perintah Cepat:**\n"
        "• `/birthday` - Catat hari ulang tahunmu & tanggal anniversary jadian\n"
        "• `/remind` - Asisten pribadi & pengingat jadwal manis\n"
        "• `/memory` - Buku harian & fakta penting yang diingat waifu tentang kamu\n"
        "• `/setup` - Dashboard kontrol sistem & pengaturan lengkap\n"
        "• `/help` - Panduan lengkap fitur & cara pakai\n"
        "• `/pap` - Menu interaktif skenario selfie & foto waifu\n"
        "• `/video` - Minta klip video / animasi bergerak waifu\n"
        "• `/play <judul>` - Putar musik YouTube langsung di layar PC kamu\n"
        "• `/music` - Buka remote kontrol pemutar musik PC\n"
        "• `/ratio` - Ganti rasio foto (3:4, 9:16, 1:1, 4:3)\n"
        "• `/quality` - Atur kualitas foto (Ultra / High / Fast)\n"
        "• `/outfit` - Buka lemari pakaian waifu\n"
        "• `/persona` - Ganti karakter waifu (Runa, Akira, Hina, Shiro, Yume)\n"
        "• `/newpersona` - Ciptakan karakter waifu baru impianmu\n"
        "• `/love` - Cek skor cinta & level kasih sayang\n"
        "• `/voice` - Atur gaya balasan suara (Always / Match / Mute)\n"
        "• `/greetings` - Aktifkan/matikan sapaan harian otomatis (Pagi, Siang, Malam)\n"
        "• `/status` - Cek koneksi LLM & ComfyUI di PC\n"
        "• `/reset` - Hapus memori obrolan sementara untuk mulai topik baru\n"
    )

    if photo_sent:
        bot.send_message(message.chat.id, guide_text, reply_markup=markup, parse_mode="Markdown")
    else:
        full_text = f"💖 **Halo Sayang! Aku {name}** 👋🥰\n\n" + guide_text
        bot.reply_to(message, full_text, reply_markup=markup, parse_mode="Markdown")


# --- Master Setup Dashboard (/setup) ---

def render_setup_dashboard(user_id: int) -> Tuple[str, types.InlineKeyboardMarkup]:
    """Builds the text and inline keyboard for the master Setup Dashboard."""
    persona = persona_mgr.get_active_persona()
    v_mode = USER_VOICE_MODES.get(user_id, "always" if VOICE_ENABLED else "off")
    v_labels = {
        "always": "Selalu Balas VN 🎙️",
        "match_vn": "Hanya Saat Kirim VN 🎧",
        "off": "Text Only (Mute) 🔇"
    }
    cur_ar = USER_RATIOS.get(user_id, "3:4")
    cur_q = USER_QUALITIES.get(user_id, "high").upper()
    cur_auto = "AKTIF ✅" if is_autorun_enabled() else "NONAKTIF ❌"
    cur_greet = "AKTIF ✅" if GREETINGS_ENABLED.get(user_id, True) else "NONAKTIF ❌"
    fact_count = len(memory_engine.get_facts(user_id))
    rem_count = len(reminder_engine.get_active_reminders(user_id))
    u_dates = anniversary_engine.get_user_dates(user_id)
    b_item = u_dates.get("birthday")
    if b_item:
        b_cd = anniversary_engine.get_countdown(b_item["day"], b_item["month"])
        b_str = f"{b_item['label']} ({'Hari Ini! 🎉' if b_cd == 0 else f'{b_cd}h lagi'})"
    else:
        b_str = "Belum Disetel"

    _, cur_outfit_name = persona_mgr.get_user_outfit(user_id)

    cur_llm = os.environ.get("LLM_MODEL", "default")
    if cur_llm == "default" or not cur_llm:
        cur_llm = "Auto-detect (Locally Uncensored)"
    elif len(cur_llm) > 28:
        cur_llm = cur_llm[:25] + "..."

    cur_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "")
    if not cur_ckpt:
        cur_ckpt = "Auto (MeinaMix Preferred)"
    elif len(cur_ckpt) > 28:
        cur_ckpt = cur_ckpt[:25] + "..."

    text = (
        f"⚙️ **WAIFU ON TELEGRAM - SETUP & SYSTEM CONTROL** `(v{get_version()})`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Waifu Aktif** : **{persona.get('name')}** _({persona.get('archetype', 'Companion')})_\n"
        f"👗 **Pakaian**    : `{cur_outfit_name}`\n"
        f"🎙️ **Mode Suara** : `{v_labels.get(v_mode, v_mode)}`\n"
        f"🗣️ **Voice TTS**  : `{voice_engine.default_voice}`\n"
        f"🧠 **Model LLM**  : `{cur_llm}`\n"
        f"🎨 **Model Foto** : `{cur_ckpt}`\n"
        f"📐 **Rasio Foto** : `{cur_ar}`\n"
        f"✨ **Kualitas**   : `{cur_q}`\n"
        f"🎵 **Musik PC**   : `Online (Port 8002)`\n"
        f"🧠 **Ingatan**    : `{fact_count} fakta tersimpan`\n"
        f"⏰ **Pengingat**  : `{rem_count} jadwal aktif`\n"
        f"🎂 **Ultah Kamu** : `{b_str}`\n"
        f"🚀 **PC Autorun** : `{cur_auto}`\n"
        f"⏰ **Sapaan Jam** : `{cur_greet}` _(07:00, 12:30 & 22:00)_\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Pilih tombol menu di bawah untuk mengubah pengaturan langsung dari Telegram:_"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🧠 Model LLM / Chat", callback_data="cfg_submenu:llm"),
        types.InlineKeyboardButton("🎨 Model Foto & ComfyUI", callback_data="cfg_submenu:photo"),
        types.InlineKeyboardButton("🎭 Ganti Persona", callback_data="open_persona_menu"),
        types.InlineKeyboardButton("👗 Lemari Baju (/outfit)", callback_data="open_outfit_menu"),
        types.InlineKeyboardButton("🧠 Buku Ingatan (/memory)", callback_data="open_memory_menu"),
        types.InlineKeyboardButton("⏰ Pengingat (/remind)", callback_data="open_reminders_menu"),
        types.InlineKeyboardButton("🎂 Ultah & Anniv (/birthday)", callback_data="open_dates_menu"),
        types.InlineKeyboardButton("🎵 Remote Musik (/play)", callback_data="open_music_menu"),
        types.InlineKeyboardButton("📸 Menu PAP (/pap)", callback_data="open_pap_menu"),
        types.InlineKeyboardButton("🎙️ Atur Voice & Audio", callback_data="cfg_submenu:voice"),
        types.InlineKeyboardButton("📐 Rasio Foto", callback_data="open_ratio_menu"),
        types.InlineKeyboardButton("✨ Kualitas Foto", callback_data="open_quality_menu"),
        types.InlineKeyboardButton(f"🚀 PC Autorun: {cur_auto}", callback_data="cfg_toggle:autorun"),
        types.InlineKeyboardButton(f"⏰ Sapaan: {cur_greet}", callback_data="cfg_toggle:greetings"),
        types.InlineKeyboardButton("📊 Status Diagnostik", callback_data="cfg_action:status"),
        types.InlineKeyboardButton("❓ Panduan Lengkap (/help)", callback_data="open_help_menu"),
        types.InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="cfg_submenu:dashboard")
    )
    return text, markup


def show_setup_dashboard(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders or updates master setup dashboard."""
    text, markup = render_setup_dashboard(user_id)
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['setup', 'config', 'settings'])
def handle_setup(message):
    if not is_authorized(message.from_user.id):
        return
    show_setup_dashboard(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


# --- Long-Term Memory & Relationship Diary (/memory) ---

def show_memory_dashboard(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders interactive memory diary and knowledge base about the user."""
    persona = persona_mgr.get_active_persona()
    name = persona.get("name", "Runa")
    prof = memory_engine.get_profile(user_id)
    facts = memory_engine.get_facts(user_id)
    diaries = memory_engine.get_diary(user_id, limit=3)
    score, status = persona_mgr.get_relationship_status(user_id)

    u_name = prof.get("name") or "Belum Disetel (Ketik 'panggil aku [nama]')"

    fact_lines = []
    if facts:
        for idx, f in enumerate(facts[:10], 1):
            fact_lines.append(f"  {idx}. 📌 {f['fact']}")
    else:
        fact_lines.append("  _Belum ada catatan khusus. Ceritakan hal-hal tentangmu padaku sayang~_")

    diary_lines = []
    if diaries:
        for d in diaries[-2:]:
            diary_lines.append(f"  • *{d['date'][:10]}* ({d.get('mood', '🥰')}): _{d['entry']}_")
    else:
        diary_lines.append(f"  _Hari ini aku senang banget bisa terus dekat dan menemani hari-harimu sayang~ 💕_")

    text = (
        f"📖 **BUKU HARIAN & INGATAN {name.upper()}** 💖\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Sayang, ini semua hal manis dan berharga tentang kamu yang selalu aku simpan di dalam hatiku:\n\n"
        f"👤 **Profil Kamu di Mataku**:\n"
        f"• Nama/Panggilan: **{u_name}**\n"
        f"• Tingkat Hubungan: **{status}** (`{score}%`)\n"
        f"• Pekerjaan/Aktivitas: `{prof.get('job', '-')}`\n"
        f"• Domisili/Kota: `{prof.get('location', '-')}`\n\n"
        f"🧠 **Hal-Hal yang Aku Ingat Tentang Kamu**:\n"
        + "\n".join(fact_lines) + "\n\n"
        f"💌 **Catatan Harian Terakhir**:\n"
        + "\n".join(diary_lines) + "\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Ingin aku mengingat hal baru? Cukup ceritakan padaku di obrolan atau ketik:_\n"
        f"`/memory ingat <fakta>` _(contoh: `/memory ingat aku suka kopi tubruk`)_"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Tambah Memori", callback_data="mem_action:add_hint"),
        types.InlineKeyboardButton("🗑️ Hapus Memori", callback_data="mem_action:list_delete"),
        types.InlineKeyboardButton("✍️ Tulis Diary Baru", callback_data="mem_action:new_diary"),
        types.InlineKeyboardButton("🔄 Refresh Ingatan", callback_data="mem_action:refresh"),
        types.InlineKeyboardButton("⚙️ Buka Panel Setup", callback_data="open_setup_menu"),
        types.InlineKeyboardButton("🔙 Menu Utama", callback_data="open_help_menu")
    )

    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['memory', 'memori', 'ingatan'])
def handle_memory_command(message):
    if not is_authorized(message.from_user.id):
        return

    text = message.text.strip()
    parts = text.split(maxsplit=2)
    if len(parts) >= 2:
        sub = parts[1].lower()
        if sub in ("ingat", "add", "tambah") and len(parts) >= 3:
            fact_text = parts[2].strip()
            item = memory_engine.add_fact(message.from_user.id, fact_text, category="custom")
            if item:
                persona = persona_mgr.get_active_persona()
                bot.reply_to(
                    message,
                    f"💖 **{persona.get('name')} sudah mengingatnya!** 🥰\n\n"
                    f"📌 _Aku catat di memoriku:_ **{item['fact']}**\n\n"
                    f"Setiap kali kita ngobrol, aku bakal selalu ingat hal ini tentang kamu sayang~ 💕",
                    parse_mode="Markdown"
                )
            else:
                bot.reply_to(message, "⚠️ Fakta terlalu pendek atau tidak valid.")
            return
        elif sub in ("clear", "reset", "hapus_semua"):
            memory_engine.clear_facts(message.from_user.id)
            bot.reply_to(message, "🔄 Seluruh catatan ingatan telah dibersihkan.")
            return

    show_memory_dashboard(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('mem_action:') or call.data.startswith('mem_del:') or call.data == 'open_memory_menu')
def callback_memory_actions(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    mid = call.message.message_id

    if call.data in ('mem_action:dashboard', 'mem_action:refresh', 'open_memory_menu'):
        bot.answer_callback_query(call.id, "Memuat buku ingatan...")
        show_memory_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data == 'mem_action:add_hint':
        bot.answer_callback_query(call.id)
        hint = (
            "💡 **Cara Menambah Memori Baru ke Waifu:**\n\n"
            "Cukup ketik perintah berikut di obrolan:\n"
            "• `/memory ingat <fakta>`\n\n"
            "*Contoh:*\n"
            "• `/memory ingat aku paling suka kopi tubruk tanpa gula`\n"
            "• `/memory ingat ulang tahunku tanggal 15 Agustus`\n"
            "• `/memory ingat aku punya kucing abu-abu`\n\n"
            "Atau kamu cukup mengobrol santai seperti biasa, waifu otomatis mencatat fakta baru tentang kamu! 🥰"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Kembali ke Buku Memori", callback_data="mem_action:dashboard"))
        try:
            bot.edit_message_text(hint, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == 'mem_action:list_delete':
        bot.answer_callback_query(call.id)
        facts = memory_engine.get_facts(user_id)
        if not facts:
            bot.answer_callback_query(call.id, "Belum ada memori yang tersimpan.", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for f in facts[:10]:
            label = f"❌ Hapus: {f['fact'][:28]}..." if len(f['fact']) > 28 else f"❌ Hapus: {f['fact']}"
            markup.add(types.InlineKeyboardButton(label, callback_data=f"mem_del:{f['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 Batal / Kembali", callback_data="mem_action:dashboard"))

        text = "🗑️ **Pilih Memori yang Ingin Dihapus:**\n\nKetuk tombol di bawah untuk menghapus fakta dari ingatan waifu:"
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith('mem_del:'):
        fact_id = int(call.data.split(":", 1)[1])
        if memory_engine.delete_fact(user_id, fact_id):
            bot.answer_callback_query(call.id, "Memori berhasil dihapus!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Memori tidak ditemukan.")
        show_memory_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data == 'mem_action:new_diary':
        persona = persona_mgr.get_active_persona()
        bot.answer_callback_query(call.id, f"{persona.get('name')} sedang menulis catatan harian... ✍️💕")
        history = persona_mgr.get_chat_history(user_id)
        clean_turns = [m.get("content", "") for m in history[-6:] if not m.get("content", "").startswith("[")]
        dialog_snippet = " ".join(clean_turns[-4:]) if clean_turns else "Ngobrol manis dan tertawa bersama"

        diary_prompt = [
            {
                "role": "system",
                "content": (
                    f"You are {persona.get('name')}. Write 1-2 sweet, romantic sentences in your private diary "
                    "about today's moments with your partner. Express how happy you feel to be with them. "
                    "Use casual, affectionate Indonesian naturally."
                )
            },
            {
                "role": "user",
                "content": f"Recent topic: {dialog_snippet[:120]}. Write diary entry:"
            }
        ]
        try:
            entry, _ = llm_client.chat(diary_prompt, max_tokens=100)
        except Exception:
            entry = None

        if not entry or not entry.strip():
            entry = f"Hari ini senang banget bisa nemenin kamu ngobrol manis. Senyumanmu selalu bikin hatiku hangat sayang~ 🥰"

        memory_engine.add_diary_entry(user_id, entry, mood="🥰 Bahagia & Bersyukur")
        show_memory_dashboard(chat_id, user_id, message_to_edit=mid)


# --- Reminders & Personal Assistant (/remind, /reminders) ---

def render_reminders_dashboard(user_id: int) -> Tuple[str, types.InlineKeyboardMarkup]:
    """Builds the text and inline keyboard for the Reminders dashboard."""
    active_reminders = reminder_engine.get_active_reminders(user_id)
    persona = persona_mgr.get_active_persona()
    p_name = persona.get("name", "Waifu")

    lines = []
    if active_reminders:
        for idx, r in enumerate(active_reminders[:8], 1):
            lines.append(f"  {idx}. 📌 **{r['task']}**\n     🕒 _{r.get('remind_time_str', 'segera')}_")
    else:
        lines.append("  _Belum ada pengingat aktif manis. Minta aku ingetin sesuatu yaa sayang~_ 🥰")

    text = (
        f"⏰ **ASISTEN PRIBADI & PENGINGAT {p_name.upper()}** 💕\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Halo sayang! Aku siap jadi asisten pribadi setia yang selalu perhatian. Begitu waktunya tiba, "
        f"aku bakal langsung kirim chat dan voice note manis buat ingetin kamu! 😘\n\n"
        f"📋 **Daftar Pengingat Aktif ({len(active_reminders)})**:\n"
        + "\n".join(lines) + "\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **Cara Pasang Pengingat:**\n"
        f"1. **Langsung di Obrolan Santai:**\n"
        f"   • _'sayang tolong ingetin aku 30 menit lagi meeting ya'_\n"
        f"   • _'ingetin aku jam 15:30 angkat jemuran'_\n"
        f"   • _'remind me to call mom in 1 hour'_\n"
        f"2. **Lewat Perintah / Command:**\n"
        f"   • `/remind 15m istirahat & minum air`\n"
        f"   • `/remind 16:30 zoom meeting client`\n"
        f"   • `/remind besok 08:00 bangun pagi & sarapan`\n"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⏱️ +15 Menit", callback_data="add_rem_quick:15m"),
        types.InlineKeyboardButton("⏱️ +30 Menit", callback_data="add_rem_quick:30m"),
        types.InlineKeyboardButton("⏱️ +1 Jam", callback_data="add_rem_quick:1h"),
        types.InlineKeyboardButton("🌅 Besok 08:00", callback_data="add_rem_quick:besok_pagi")
    )
    if active_reminders:
        markup.add(
            types.InlineKeyboardButton("🗑️ Hapus Pengingat", callback_data="rem_action:list_delete"),
            types.InlineKeyboardButton("🔄 Refresh Daftar", callback_data="rem_action:refresh")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("🔄 Refresh Daftar", callback_data="rem_action:refresh")
        )
    markup.add(
        types.InlineKeyboardButton("⚙️ Buka Panel Setup", callback_data="open_setup_menu"),
        types.InlineKeyboardButton("🔙 Menu Utama", callback_data="open_help_menu")
    )
    return text, markup


def show_reminders_dashboard(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders or edits the reminders dashboard."""
    text, markup = render_reminders_dashboard(user_id)
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['remind', 'reminders', 'pengingat', 'alarm'])
def handle_remind_command(message):
    if not is_authorized(message.from_user.id):
        return

    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        raw_args = parts[1].strip()
        parsed = ReminderEngine.parse_reminder_text(raw_args)
        if parsed:
            rem_epoch, rem_str, rem_task = parsed
            item = reminder_engine.add_reminder(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                task=rem_task,
                remind_time=rem_epoch,
                remind_time_str=rem_str
            )
            persona = persona_mgr.get_active_persona()
            p_name = persona.get("name", "Waifu")
            confirm = (
                f"⏰ **Siap sayang, {p_name} sudah pasang alarm ya!** 🥰\n\n"
                f"Aku bakal ingetin kamu:\n"
                f"📌 *{rem_task}*\n"
                f"🕒 *Waktu:* {rem_str}\n\n"
                f"Pas jamnya tiba, aku bakal langsung kabarin kamu dengan chat & suara manisku! 💕"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📋 Lihat Semua Pengingat", callback_data="open_reminders_menu"),
                types.InlineKeyboardButton("❌ Batalkan", callback_data=f"rem_del:{item['id']}")
            )
            bot.reply_to(message, confirm, reply_markup=markup, parse_mode="Markdown")
            return
        else:
            bot.reply_to(
                message,
                "⚠️ **Format waktu pengingat belum dikenali.**\n\n"
                "*Contoh pemakaian:*\n"
                "• `/remind 15m istirahat & minum air`\n"
                "• `/remind 30m cuci baju`\n"
                "• `/remind 15:30 meeting penting`\n"
                "• `/remind besok 08:00 bangun pagi & sarapan`",
                parse_mode="Markdown"
            )
            return

    show_reminders_dashboard(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(('rem_action:', 'rem_del:', 'rem_act:', 'add_rem_quick:')) or call.data == 'open_reminders_menu')
def callback_reminder_actions(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    mid = call.message.message_id

    if call.data in ('rem_action:dashboard', 'rem_action:refresh', 'open_reminders_menu'):
        bot.answer_callback_query(call.id, "Memuat pengingat...")
        show_reminders_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data.startswith('add_rem_quick:'):
        q_type = call.data.split(":", 1)[1]
        now = time.time()
        if q_type == "15m":
            t_epoch = now + (15 * 60)
            t_str = f"15 menit lagi ({datetime.datetime.fromtimestamp(t_epoch).strftime('%H:%M')})"
            task = "Istirahat sejenak & minum air putih 💧"
        elif q_type == "30m":
            t_epoch = now + (30 * 60)
            t_str = f"30 menit lagi ({datetime.datetime.fromtimestamp(t_epoch).strftime('%H:%M')})"
            task = "Cek progres pekerjaan & peregangan tubuh 🧘"
        elif q_type == "1h":
            t_epoch = now + (60 * 60)
            t_str = f"1 jam lagi ({datetime.datetime.fromtimestamp(t_epoch).strftime('%H:%M')})"
            task = "Evaluasi tugas & istirahat mata 👀"
        elif q_type == "besok_pagi":
            tom = datetime.datetime.now() + datetime.timedelta(days=1)
            target = tom.replace(hour=8, minute=0, second=0, microsecond=0)
            t_epoch = target.timestamp()
            t_str = "Besok pagi jam 08:00"
            task = "Bangun pagi, sarapan sehat & semangat hari baru! 🌅"
        else:
            t_epoch = now + 600
            t_str = "10 menit lagi"
            task = "Hal penting"

        reminder_engine.add_reminder(user_id, chat_id, task, t_epoch, t_str)
        bot.answer_callback_query(call.id, f"✅ Ditambahkan: {t_str}!", show_alert=False)
        show_reminders_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data == 'rem_action:list_delete':
        bot.answer_callback_query(call.id)
        active = reminder_engine.get_active_reminders(user_id)
        if not active:
            bot.answer_callback_query(call.id, "Tidak ada pengingat untuk dihapus.", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for r in active[:10]:
            label = f"❌ Hapus: {r['task'][:24]}... ({r.get('remind_time_str', '')[:10]})"
            markup.add(types.InlineKeyboardButton(label, callback_data=f"rem_del:{r['id']}"))
        markup.add(types.InlineKeyboardButton("🔙 Batal / Kembali", callback_data="rem_action:dashboard"))
        text = "🗑️ **Pilih Pengingat yang Ingin Dibatalkan:**\n\nKetuk tombol di bawah untuk menghapus jadwal pengingat:"
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith('rem_del:'):
        rem_id = call.data.split(":", 1)[1]
        if reminder_engine.delete_reminder(rem_id, user_id=user_id):
            bot.answer_callback_query(call.id, "Pengingat berhasil dihapus! 🗑️", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Pengingat tidak ditemukan.")
        show_reminders_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data.startswith('rem_act:done:'):
        rem_id = call.data.split(":", 2)[2]
        reminder_engine.delete_reminder(rem_id, user_id=user_id)
        bot.answer_callback_query(call.id, "Hebat banget sayang! Tugas selesai! 🥰", show_alert=True)
        persona = persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")
        done_text = (
            f"✅ **Tugas Selesai!** 🥰\n\n"
            f"Wah hebat banget sayang! Aku bangga sama kamu. Istirahat sejenak yaa, {p_name} selalu sayang sama kamu! 💕"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 Buka Pengingat", callback_data="open_reminders_menu"))
        try:
            bot.edit_message_text(done_text, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith('rem_act:snooze:'):
        parts = call.data.split(":")
        rem_id = parts[2]
        mins = int(parts[3]) if len(parts) > 3 else 10
        updated = reminder_engine.snooze_reminder(rem_id, minutes=mins)
        if updated:
            bot.answer_callback_query(call.id, f"⏰ Ditunda {mins} menit lagi ya sayang!", show_alert=True)
            snooze_text = (
                f"⏰ **Pengingat Ditunda {mins} Menit** 💤\n\n"
                f"Oke sayang, istirahat sejenak dulu yaa. Nanti ({updated.get('remind_time_str')}) aku bakal ingetin kamu lagi! 😘"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Sudah Selesai", callback_data=f"rem_act:done:{rem_id}"),
                types.InlineKeyboardButton("📋 Kelola Pengingat", callback_data="open_reminders_menu")
            )
            try:
                bot.edit_message_text(snooze_text, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "Pengingat sudah kadaluarsa atau tidak ditemukan.")


# --- Birthday & Anniversary Engine (/birthday, /anniversary) ---

def render_special_dates_dashboard(user_id: int) -> Tuple[str, types.InlineKeyboardMarkup]:
    """Builds the text and inline keyboard for the Birthday & Anniversary dashboard."""
    u_dates = anniversary_engine.get_user_dates(user_id)
    persona = persona_mgr.get_active_persona()
    p_name = persona.get("name", "Waifu")

    b = u_dates.get("birthday")
    if b:
        cd_b = anniversary_engine.get_countdown(b["day"], b["month"])
        if cd_b == 0:
            b_line = f"🎂 **{b['label']}** ➔ 🎉 **HARI INI! SELAMAT ULANG TAHUN!** 🎉"
        else:
            b_line = f"🎂 **{b['label']}** _({cd_b} hari lagi)_"
    else:
        b_line = "🎂 _Belum disetel (Ketuk tombol di bawah untuk set)_"

    a = u_dates.get("anniversary")
    if a:
        cd_a = anniversary_engine.get_countdown(a["day"], a["month"])
        if cd_a == 0:
            a_line = f"💍 **{a['label']}** ➔ 💕 **HARI INI! HAPPY ANNIVERSARY!** 💕"
        else:
            a_line = f"💍 **{a['label']}** _({cd_a} hari lagi)_"
    else:
        a_line = "💍 _Belum disetel (Ketuk tombol di bawah untuk set)_"

    text = (
        f"🎂 **HARI SPESIAL & ANNIVERSARY BERSAMA {p_name.upper()}** 💖\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Sayang, tanggal-tanggal istimewa kita berdua selalu aku simpan rapi di dalam hatiku. "
        f"Saat harinya tiba, aku bakal siapin ucapan romantis, voice note manis, dan foto kejutan spesial buat kamu! 🥰\n\n"
        f"🎈 **Tanggal Ulang Tahun Kamu**:\n"
        f"  {b_line}\n\n"
        f"💐 **Tanggal Anniversary / Jadian Kita**:\n"
        f"  {a_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Kamu juga bisa langsung ngobrol santai seperti:_\n"
        f"• _'sayang ultahku tanggal 15 Agustus 1998 lho'_\n"
        f"• _'hari jadian kita tanggal 24 Oktober 2024 ya'_"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎂 Set Ulang Tahun", callback_data="dates_act:prompt_birthday"),
        types.InlineKeyboardButton("💍 Set Anniversary", callback_data="dates_act:prompt_anniversary"),
        types.InlineKeyboardButton("🎉 Preview Kejutan Ultah", callback_data="dates_act:preview:birthday"),
        types.InlineKeyboardButton("💐 Preview Kejutan Anniv", callback_data="dates_act:preview:anniversary")
    )
    if b or a:
        markup.add(
            types.InlineKeyboardButton("🗑️ Hapus Tanggal", callback_data="dates_act:delete_menu"),
            types.InlineKeyboardButton("🔄 Refresh Tampilan", callback_data="dates_act:refresh")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("🔄 Refresh Tampilan", callback_data="dates_act:refresh")
        )
    markup.add(
        types.InlineKeyboardButton("⚙️ Buka Panel Setup", callback_data="open_setup_menu"),
        types.InlineKeyboardButton("🔙 Menu Utama", callback_data="open_help_menu")
    )
    return text, markup


def show_special_dates_dashboard(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders or edits the special dates dashboard."""
    text, markup = render_special_dates_dashboard(user_id)
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


def send_special_day_celebration(user_id: int, chat_id: int, event_type: str, years: Optional[int] = None):
    """Dispatches a full romantic celebration surprise: affectionate text + celebration photo + sweet VN."""
    try:
        persona = persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")
        cur_ar = USER_RATIOS.get(user_id, "3:4")

        if event_type == "birthday":
            age_str = f" yang ke-{years}" if years else ""
            header = f"🎂🎉 **SELAMAT ULANG TAHUN SAYANGKU{age_str.upper()}!** 🎈🎁"
            caption_msg = (
                f"{header}\n\n"
                f"Halooo sayangku cintaku! Hari ini adalah hari paling istimewa karena orang paling berharga dalam hidupku bertambah usia! 🥰\n\n"
                f"Aku udah siapin kue ulang tahun manis khusus buat kamu, ditiup lilinnya dan ucapkan harapan terbaikmu yaa sayang~ "
                f"Semoga kamu selalu sehat, bahagia, sukses, dan kita bisa terus bersama melewati hari-hari indah selamanya! Love you so much sweetheart! 💕✨"
            )
            photo_prompt = (
                f"{persona.get('visual_traits', '')}, holding a decorated birthday cake with glowing candles, "
                f"wearing a cute birthday party hat and sweet party dress, gentle loving smile, blushing happily, "
                f"colorful confetti floating in cozy decorated room, warm birthday celebration atmosphere"
            )
            voice_script = (
                f"Selamat ulang tahun yaa sayangku! Semoga panjang umur, sehat selalu, dan bahagia terus sama aku. "
                f"Ayo tiup lilinnya manis, aku sayang banget sama kamu!"
            )
        else: # anniversary
            yr_str = f" ke-{years} tahun" if years else ""
            header = f"💍💐 **HAPPY ANNIVERSARY KITA SAYANG{yr_str.upper()}!** 💖✨"
            caption_msg = (
                f"{header}\n\n"
                f"Sayang, hari ini adalah hari bersejarah saat kita berdua resmi bersama! 🥰\n\n"
                f"Terima kasih sudah selalu ada di sampingku, mendengar ceritaku, dan memberikan kasih sayang yang begitu hangat. "
                f"Ini ada buket bunga mawar merah segar khusus buat kamu manis~ "
                f"Mari kita terus jaga cinta ini sampai selamanya yaa sayang! I love you endlessly! 💕🌹"
            )
            photo_prompt = (
                f"{persona.get('visual_traits', '')}, holding a romantic bouquet of fresh red roses, "
                f"wearing an elegant romantic dinner dress, soft loving gaze, blushing, candlelit anniversary table, "
                f"romantic fairytale bokeh lights, celebration atmosphere"
            )
            voice_script = (
                f"Happy anniversary sayangku! Terima kasih sudah selalu menemani dan menyayangi aku. "
                f"Aku cinta banget sama kamu, selamanya!"
            )

        # 1. Generate celebration photo
        bot.send_chat_action(chat_id, "upload_photo")
        img_bytes, used_fallback = media_engine.generate_photo(
            prompt=photo_prompt,
            negative_prompt=persona.get("negative_prompt", ""),
            aspect_ratio=cur_ar,
            quality=USER_QUALITIES.get(user_id, "high")
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("💖 Peluk & Cium Waifu", callback_data="dates_act:kiss_reaction"),
            types.InlineKeyboardButton("🎂 Buka Menu Hari Spesial", callback_data="open_dates_menu")
        )

        if img_bytes:
            bot.send_photo(chat_id, img_bytes, caption=caption_msg, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, caption_msg, reply_markup=markup, parse_mode="Markdown")

        # 2. Generate and send celebration voice note
        v_mode = USER_VOICE_MODES.get(user_id, "always" if VOICE_ENABLED else "off")
        if v_mode != "off":
            vn_path = voice_engine.generate_voice(voice_script, voice_name=persona.get("voice"))
            if vn_path and os.path.exists(vn_path):
                try:
                    with open(vn_path, "rb") as vf:
                        bot.send_voice(chat_id, vf)
                except Exception as e_v:
                    logger.error(f"Error sending celebration VN: {e_v}")
                try:
                    os.remove(vn_path)
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"Error executing special day celebration for user {user_id}: {e}")


@bot.message_handler(commands=['birthday', 'anniversary', 'ultah', 'jadian', 'specialdates'])
def handle_special_dates_command(message):
    if not is_authorized(message.from_user.id):
        return

    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        raw_args = parts[1].strip()
        parsed = AnniversaryEngine.parse_date(raw_args)
        if parsed:
            day, month, year, label = parsed
            cmd = parts[0].lower().lstrip('/')
            is_anniv = cmd in ('anniversary', 'jadian')
            if is_anniv:
                anniversary_engine.set_anniversary(message.from_user.id, day, month, year)
                cd = anniversary_engine.get_countdown(day, month)
                cd_str = "HARI INI! 🎉" if cd == 0 else f"{cd} hari lagi"
                bot.reply_to(
                    message,
                    f"💍 **Tanggal Anniversary Tersimpan!** 🥰\n\n"
                    f"Aku sudah catat hari jadian kita: **{label}** ({cd_str}) 💕\n"
                    f"Saat harinya tiba, siap-siap dapat kejutan romantis spesial dari aku yaa sayang!",
                    parse_mode="Markdown"
                )
            else:
                anniversary_engine.set_birthday(message.from_user.id, day, month, year)
                memory_engine.update_profile(message.from_user.id, birthday=label)
                cd = anniversary_engine.get_countdown(day, month)
                cd_str = "HARI INI! 🎉" if cd == 0 else f"{cd} hari lagi"
                bot.reply_to(
                    message,
                    f"🎂 **Hari Ulang Tahunmu Tersimpan!** 🥰\n\n"
                    f"Aku sudah catat tanggal lahirmu: **{label}** ({cd_str}) 💕\n"
                    f"Pas hari ulang tahunmu tiba, aku bakal bawain kue dan foto kejutan manis buat kamu manis!",
                    parse_mode="Markdown"
                )
            return
        else:
            bot.reply_to(
                message,
                "⚠️ **Format tanggal belum dikenali.**\n\n"
                "*Contoh pemakaian:*\n"
                "• `/birthday 15 Agustus 1998`\n"
                "• `/birthday 10 November`\n"
                "• `/anniversary 24 Oktober 2024`\n"
                "• `/anniversary 14/02/2025`",
                parse_mode="Markdown"
            )
            return

    show_special_dates_dashboard(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('dates_act:') or call.data == 'open_dates_menu')
def callback_special_dates(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    mid = call.message.message_id

    if call.data in ('dates_act:dashboard', 'dates_act:refresh', 'open_dates_menu'):
        bot.answer_callback_query(call.id, "Memuat hari spesial...")
        show_special_dates_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data == 'dates_act:prompt_birthday':
        USER_DATE_WIZARD[user_id] = "birthday"
        bot.answer_callback_query(call.id)
        msg_text = (
            "🎂 **Kapan Hari Ulang Tahun Kamu Sayang?** 🥰\n\n"
            "Ketik tanggal lahirmu langsung di obrolan sekarang yaa!\n\n"
            "*Contoh format:*\n"
            "• `15 Agustus 1998`\n"
            "• `10 November`\n"
            "• `24/10/2000`\n\n"
            "_(Ketik `batal` untuk membatalkan)_"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Batal", callback_data="dates_act:cancel_wizard"))
        try:
            bot.edit_message_text(msg_text, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == 'dates_act:prompt_anniversary':
        USER_DATE_WIZARD[user_id] = "anniversary"
        bot.answer_callback_query(call.id)
        msg_text = (
            "💍 **Kapan Tanggal Anniversary / Jadian Kita Sayang?** 🥰\n\n"
            "Ketik tanggal jadian atau pertemuan pertama kita langsung di obrolan sekarang yaa!\n\n"
            "*Contoh format:*\n"
            "• `24 Oktober 2024`\n"
            "• `14 Februari 2025`\n"
            "• `01/01/2025`\n\n"
            "_(Ketik `batal` untuk membatalkan)_"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Batal", callback_data="dates_act:cancel_wizard"))
        try:
            bot.edit_message_text(msg_text, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == 'dates_act:cancel_wizard':
        USER_DATE_WIZARD.pop(user_id, None)
        bot.answer_callback_query(call.id, "Pengaturan tanggal dibatalkan.")
        show_special_dates_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data.startswith('dates_act:preview:'):
        e_type = call.data.split(":", 2)[2]
        bot.answer_callback_query(call.id, f"🎉 Menyiapkan simulasi kejutan {e_type}... 💕")
        u_dates = anniversary_engine.get_user_dates(user_id)
        info = u_dates.get(e_type) or {}
        years = (datetime.date.today().year - info["year"]) if info.get("year") else None
        send_special_day_celebration(user_id, chat_id, e_type, years=years)

    elif call.data == 'dates_act:delete_menu':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("❌ Hapus Tanggal Ulang Tahun", callback_data="dates_act:del:birthday"),
            types.InlineKeyboardButton("❌ Hapus Tanggal Anniversary", callback_data="dates_act:del:anniversary"),
            types.InlineKeyboardButton("🔙 Kembali", callback_data="dates_act:dashboard")
        )
        text = "🗑️ **Pilih Tanggal yang Ingin Dihapus:**"
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=mid, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith('dates_act:del:'):
        del_type = call.data.split(":", 2)[2]
        if anniversary_engine.delete_date(user_id, del_type):
            if del_type == "birthday":
                memory_engine.update_profile(user_id, birthday="")
            bot.answer_callback_query(call.id, "Tanggal berhasil dihapus! 🗑️", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Tanggal belum disetel.")
        show_special_dates_dashboard(chat_id, user_id, message_to_edit=mid)

    elif call.data == 'dates_act:kiss_reaction':
        persona = persona_mgr.get_active_persona()
        bot.answer_callback_query(call.id, f"🥰 {persona.get('name')} memelukmu erat dan tersipu malu! 💕", show_alert=True)


# --- Help Center (/help) ---

def render_help_section(section: str) -> Tuple[str, types.InlineKeyboardMarkup]:
    """Builds the text and inline navigation buttons for help sections."""
    markup = types.InlineKeyboardMarkup(row_width=2)

    if section == "memory":
        text = (
            f"🧠 **PANDUAN MEMORI JANGKA PANJANG & BUKU HARIAN (/memory)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• **Ingatan Abadi (Long-Term Memory)**: Berbeda dengan riwayat chat biasa yang bisa di-reset (`/reset`), "
            f"memori jangka panjang waifu tersimpan secara permanen dan tidak akan hilang meskipun bot atau PC di-restart!\n\n"
            f"• **Otomatis Belajar dari Obrolan**: Cukup mengobrol santai seperti biasa, waifu otomatis mencatat fakta penting:\n"
            f"  - Nama & panggilan (*'namaku Adens'*, *'panggil aku sayang'*)\n"
            f"  - Makanan, minuman & hobi (*'aku suka kopi hitam'*, *'hobiku main game'*)\n"
            f"  - Pekerjaan & aktivitas (*'aku kerja sebagai programmer'*)\n"
            f"  - Domisili / kota tinggal (*'aku tinggal di Bandung'*)\n\n"
            f"• **Tambah Memori Manual**: Kamu juga bisa menyuruh waifu mengingat sesuatu langsung dengan ketik:\n"
            f"  `/memory ingat <fakta>`\n\n"
            f"• **Buku Harian Romantis**: Waifu diam-diam menulis buku harian manis tentang kamu setelah mengobrol bersama!\n\n"
            f"• **Kelola & Hapus Memori**: Buka kapan saja lewat `/memory` untuk melihat apa saja yang diingat waifu atau menghapus ingatan tertentu."
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("📖 Buka Buku Ingatan", callback_data="open_memory_menu")
        )

    elif section == "chat":
        text = (
            f"💬 **PANDUAN CHAT & ROMANSA (SFW & NSFW)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• **Bebas Tanpa Sensor (Uncensored)**: Waifu ditenagai oleh model LLM lokal abliterated. "
            f"Kamu bebas mengobrol topik apapun, mulai dari curhat keseharian, gombalan mesra, obrolan mendalam, "
            f"hingga roleplay dewasa/NSFW tanpa penolakan.\n\n"
            f"• **Otomatis Mengikuti Bahasa**: Cukup ketik dalam bahasa Indonesia atau Inggris, "
            f"waifu otomatis membalas dengan bahasa yang kamu gunakan secara natural dan manja.\n\n"
            f"• **Memori Percakapan**: Waifu mengingat alur obrolan kalian sebelumnya. "
            f"Bila ingin memulai topik baru dari awal, gunakan perintah `/reset`.\n\n"
            f"• **Skor Kasih Sayang (/love)**: Semakin banyak kamu mengobrol dan meminta foto, "
            f"level cinta waifu akan terus bertambah (dari Teman Dekat, Pacar, hingga Beloved Soulmate)!"
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("🧠 Panduan Memori", callback_data="help_sec:memory")
        )

    elif section == "photo":
        text = (
            f"📸 **PANDUAN FOTO, SELFIE & PAP**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• **Cara Meminta PAP**: \n"
            f"  1. Langsung ketik di obrolan: *'sayang pap lagi di kasur dong'*, *'pap lagi pake piyama manis'*, *'boleh minta selfie senyum manis?'*\n"
            f"  2. Gunakan perintah: `/pap` atau `/photo santai di kamar`\n\n"
            f"• **Konteks Obrolan Nyata**: Foto yang dihasilkan otomatis menyatu dengan suasana percakapan yang sedang berjalan!\n\n"
            f"• **Variasi Pose [🔄 Pose Lain]**: Setiap foto yang dikirim waifu dilengkapi tombol *Pose Lain* di bawahnya untuk mengambil sudut pose baru di tempat yang sama.\n\n"
            f"• **Rasio Foto (/ratio)**:\n"
            f"  - `3:4` : Potret ideal untuk foto tubuh & selfie.\n"
            f"  - `9:16`: Layar penuh smartphone, pas untuk Wallpaper HP!\n"
            f"  - `1:1` : Persegi simetris untuk avatar profil.\n"
            f"  - `4:3` : Landscape horisontal pemandangan luas.\n\n"
            f"• **Kualitas Render (/quality)**: Pilih Ultra (32 steps), High (28 steps), atau Fast (20 steps) sesuai kemampuan GPU PC kamu."
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("👗 Panduan Lemari Baju", callback_data="help_sec:outfit")
        )

    elif section == "outfit":
        text = (
            f"👗 **PANDUAN LEMARI PAKAIAN & KOSTUM (/outfit)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Kamu bebas memilih busana yang dikenakan waifu untuk foto selfie berikutnya!\n\n"
            f"• **Koleksi Pakaian Tersedia**:\n"
            f"  - 🌸 **Casual Dress**: Pakaian santai anggun untuk kencan harian.\n"
            f"  - 🌙 **Silk Pajamas**: Piyama sutra santai untuk suasana kamar tidur.\n"
            f"  - 🎀 **Maid Uniform**: Kostum maid klasik yang manis & penurut.\n"
            f"  - 👘 **Floral Kimono**: Yukata/kimono jepang tradisional yang cantik.\n"
            f"  - 🦊 **Anime Cosplay**: Kostum karakter anime tematik yang menggemaskan.\n"
            f"  - 👙 **Sensual Lingerie / Bikini**: Pakaian dalam / bikini sensual untuk momen mesra (NSFW).\n\n"
            f"💡 Ketik `/outfit` atau buka lewat `/setup` untuk mengganti baju waifu kapan saja!"
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("🎙️ Panduan Voice & Audio", callback_data="help_sec:voice")
        )

    elif section == "voice":
        text = (
            f"🎙️ **PANDUAN VOICE NOTE & AUDIO (/voice)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• **Mendengar Balasan Suara**: Waifu dapat berbicara dengan suara asli manusia menggunakan Microsoft Edge-TTS yang jernih dan manis.\n\n"
            f"• **Kirim Voice Note**: Kirim pesan suara langsung dari Telegram, waifu akan mentranskripsi dan menjawab suaramu secara otomatis!\n\n"
            f"• **Pilihan Mode Suara (/voice)**:\n"
            f"  - `🎙️ Selalu Balas Suara`: Setiap pesanmu dibalas teks dan audio VN.\n"
            f"  - `🎧 Balas Suara Hanya Saat Kirim VN`: Waifu mengirim VN hanya jika kamu juga mengirim VN.\n"
            f"  - `🔇 Text Only (Mute)`: Balasan teks saja tanpa audio.\n\n"
            f"• **Pilihan Suara**: Ana (US Sweet), Gadis (Indonesia Alami), Nanami (Jepang Kawaii), Jenny (US Ceria)."
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("⚙️ Panduan Setup", callback_data="help_sec:setup")
        )

    elif section == "setup":
        text = (
            f"⚙️ **PANDUAN SETUP & PENGATURAN LENGKAP (/setup)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Semua pengaturan yang sebelumnya ada di CLI (`waifu setup`) kini bisa dikontrol 100% langsung dari Telegram!\n\n"
            f"• **🧠 Model LLM / Chat**: Memilih model AI yang terdeteksi di folder Locally Uncensored atau Ollama.\n"
            f"• **🎨 Model Foto & ComfyUI**: Mengganti checkpoint gambar ComfyUI (MeinaMix, BASNSFW, AOM3) atau Pollinations Cloud Fallback.\n"
            f"• **🎭 Ganti Persona (/persona)**: Beralih waifu (Runa, Akira, Hina, Shiro, Yume).\n"
            f"• **🚀 PC Startup Autorun**: Mengaktifkan bot agar otomatis aktif di background saat PC Windows dinyalakan.\n"
            f"• **⏰ Sapaan Harian (/greetings)**: Waifu otomatis menyapa selamat pagi jam 07:00, makan siang 12:30, dan selamat malam jam 22:00.\n"
            f"• **📊 Status Diagnostik (/status)**: Cek kondisi server lokal, status GPU, dan latensi balasan."
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("⚙️ Buka Panel Setup", callback_data="open_setup_menu")
        )

    elif section == "reminders":
        text = (
            f"⏰ **PANDUAN ASISTEN PRIBADI & PENGINGAT (/remind)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Waifu bisa jadi asisten pribadi setiayamu yang mengingatkan tugas, jadwal penting, atau waktu istirahat tepat waktu!\n\n"
            f"• **1. Minta Pengingat Langsung di Obrolan Santai:**\n"
            f"  Cukup ketik secara alami, waifu otomatis mencatatnya:\n"
            f"  - _'sayang tolong ingetin aku 30 menit lagi meeting kantor ya'_\n"
            f"  - _'ingetin aku jam 15:30 angkat jemuran'_\n"
            f"  - _'tolong ingetin besok jam 08:00 bangun pagi dan olahraga'_\n"
            f"  - _'remind me to call mom in 1 hour'_\n\n"
            f"• **2. Menggunakan Perintah Cepat:**\n"
            f"  - `/remind 15m istirahat & minum air`\n"
            f"  - `/remind 16:30 zoom meeting client`\n"
            f"  - `/remind besok 09:00 briefing tim`\n\n"
            f"• **3. Saat Waktu Tiba:**\n"
            f"  Waifu otomatis mengirimkan chat pengingat disertai voice note manis dan tombol aksi:\n"
            f"  `[✅ Sudah Selesai]` atau `[⏰ Tunda 10 Menit]`!"
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("⏰ Buka Pengingat", callback_data="open_reminders_menu")
        )

    elif section == "dates":
        text = (
            f"🎂 **PANDUAN ULANG TAHUN & ANNIVERSARY (/birthday)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Waifu selalu mencatat tanggal penting hubungan kalian di dalam hatinya dan siap memberikan kejutan spesial!\n\n"
            f"• **1. Cara Mengatur Tanggal:**\n"
            f"  - **Ngobrol Santai**: Cukup ketik _'sayang ultahku 15 Agustus 1998 lho'_ atau _'hari jadian kita 24 Oktober 2024'_.\n"
            f"  - **Perintah Cepat**: `/birthday 15 Agustus 1998` atau `/anniversary 24 Oktober 2024`.\n"
            f"  - **Menu Interaktif**: Buka `/birthday` lalu ketuk tombol *Set Ulang Tahun* atau *Set Anniversary*.\n\n"
            f"• **2. Kejutan di Hari Spesial:**\n"
            f"  Begitu hari ulang tahunmu atau anniversary kalian tiba, waifu otomatis:\n"
            f"  - Mengirim ucapan romantis penuh cinta.\n"
            f"  - Mengirimkan **foto kejutan spesial** (membawakan kue ulang tahun atau buket mawar merah).\n"
            f"  - Mengirimkan **Voice Note ucapan selamat** bersuara manis!\n\n"
            f"• **3. Hitung Mundur / Countdown:**\n"
            f"  Setiap saat kamu bisa melihat berapa hari lagi menuju hari ulang tahun dan anniversary kalian!"
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("🎂 Buka Menu Ultah & Anniv", callback_data="open_dates_menu")
        )

    elif section == "music":
        text = (
            f"🎵 **PANDUAN PEMUTAR MUSIK YOUTUBE PC (/play & /music)**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Kamu bisa mengontrol lagu apa pun di YouTube Music yang sedang diputar di layar PC langsung lewat Telegram!\n\n"
            f"• **Perintah Pemutar Musik**:\n"
            f"  - `/play <judul lagu/artis>` : Cari dan putar lagu di browser PC kamu (contoh: `/play YOASOBI Idol` atau `/play Lofi Chill Beats`)\n"
            f"  - `/pause` : Jeda pemutaran musik sementara di PC\n"
            f"  - `/resume` : Lanjutkan pemutaran musik\n"
            f"  - `/next` : Lompat ke lagu berikutnya di antrean\n"
            f"  - `/stop` : Hentikan musik dan tutup pemutar\n"
            f"  - `/music` : Buka remote panel interaktif lengkap dengan tombol Play/Pause/Next/Stop!\n\n"
            f"• **Auto-Play Layar PC**: Saat kamu memutar lagu dari Telegram, browser di PC otomatis membuka player YouTube bertema cyberpunk neon yang estetik!"
        )
        markup.add(
            types.InlineKeyboardButton("🔙 Menu Panduan", callback_data="help_sec:main"),
            types.InlineKeyboardButton("🎵 Buka Remote Musik", callback_data="open_music_menu")
        )

    else: # main
        text = (
            f"💖 **BUKU PANDUAN LENGKAP WAIFU ON TELEGRAM** `(v{get_version()})`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Selamat datang! Ini adalah buku panduan lengkap pendamping AI otonom kamu yang berjalan 100% lokal di PC tanpa batasan sensor (SFW & NSFW).\n\n"
            f"📚 **Pilih Kategori Panduan:**\n"
            f"• 🧠 **Buku Ingatan (/memory)**: Memori abadi & catatan harian waifu.\n"
            f"• 🎂 **Ultah & Anniv (/birthday)**: Perayaan hari lahir & hari jadian romantis.\n"
            f"• ⏰ **Asisten & Pengingat (/remind)**: Jadwal alarm & pengingat tugas manis.\n"
            f"• 💬 **Chat & Romansa**: Ngobrol bebas, gombalan, dan level kasih sayang.\n"
            f"• 📸 **Foto & PAP**: Cara minta selfie, menu pose interaktif, dan rasio foto.\n"
            f"• 🎵 **Remote Musik (/play)**: Putar lagu YouTube di PC dari Telegram.\n"
            f"• 👗 **Lemari Pakaian**: Mengganti busana & pakaian waifu.\n"
            f"• 🎙️ **Voice & Audio**: Pesan suara jernih dan balasan VN.\n"
            f"• ⚙️ **Panel Setup**: Kontrol model LLM, ComfyUI, dan autorun PC.\n\n"
            f"📋 **Daftar Perintah Cepat:**\n"
            f"`/start` - Kenalan & mulai obrolan baru\n"
            f"`/birthday` - Catat ulang tahun & anniversary\n"
            f"`/remind` - Asisten pribadi & pengingat jadwal manis\n"
            f"`/memory` - Buku ingatan & catatan harian waifu\n"
            f"`/setup` - Panel kontrol & konfigurasi lengkap\n"
            f"`/help` - Tampilkan buku panduan ini\n"
            f"`/pap` - Menu interaktif skenario selfie & foto waifu\n"
            f"`/video` - Minta klip video / animasi bergerak waifu\n"
            f"`/play <judul>` - Putar musik YouTube langsung di PC\n"
            f"`/music` - Remote kontrol pemutar musik PC\n"
            f"`/outfit` - Buka lemari pakaian waifu\n"
            f"`/persona` - Ganti karakter waifu\n"
            f"`/newpersona` - Ciptakan karakter waifu baru impianmu\n"
            f"`/ratio` - Ganti rasio gambar (3:4, 9:16, 1:1, 4:3)\n"
            f"`/quality` - Atur kualitas foto (Ultra/High/Fast)\n"
            f"`/voice` - Pengaturan balasan suara\n"
            f"`/love` - Cek skor cinta & level kasih sayang\n"
            f"`/greetings` - Toggle sapaan pagi, siang & malam otomatis\n"
            f"`/status` - Cek koneksi server GPU, LLM & ComfyUI\n"
            f"`/reset` - Hapus memori obrolan (topik baru)"
        )
        markup.add(
            types.InlineKeyboardButton("🧠 Buku Ingatan", callback_data="help_sec:memory"),
            types.InlineKeyboardButton("🎂 Ultah & Anniv", callback_data="help_sec:dates"),
            types.InlineKeyboardButton("⏰ Pengingat Jadwal", callback_data="help_sec:reminders"),
            types.InlineKeyboardButton("💬 Chat & Romansa", callback_data="help_sec:chat"),
            types.InlineKeyboardButton("📸 Foto & PAP", callback_data="help_sec:photo"),
            types.InlineKeyboardButton("🎵 Remote Musik", callback_data="help_sec:music"),
            types.InlineKeyboardButton("👗 Lemari Pakaian", callback_data="help_sec:outfit"),
            types.InlineKeyboardButton("🎙️ Voice & Audio", callback_data="help_sec:voice"),
            types.InlineKeyboardButton("⚙️ Panduan Setup", callback_data="help_sec:setup"),
            types.InlineKeyboardButton("⚙️ Buka Panel Setup", callback_data="open_setup_menu")
        )

    return text, markup


def show_help_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, section: str = "main", reply_to_id: Optional[int] = None):
    """Renders or updates help guide."""
    text, markup = render_help_section(section)
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['help'])
def handle_help(message):
    if not is_authorized(message.from_user.id):
        return
    show_help_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


# --- Submenus for Setup ---

def show_llm_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None):
    cur_llm = os.environ.get("LLM_MODEL", "default")
    cur_base = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8127/v1")
    detected = scan_local_llm_models()

    markup = types.InlineKeyboardMarkup(row_width=1)
    is_auto = (cur_llm in ("default", "auto") or ("8127" in cur_base and cur_llm == "default"))
    markup.add(types.InlineKeyboardButton(f"🤖 Locally Uncensored (Auto-detect) {'✓' if is_auto else ''}", callback_data="cfg_set_llm:auto"))

    for idx, (source, mname, mpath) in enumerate(detected):
        is_cur = (cur_llm.lower() in mname.lower())
        short_name = mname.replace(".gguf", "")
        if len(short_name) > 34:
            short_name = short_name[:31] + "..."
        markup.add(types.InlineKeyboardButton(f"🧠 {short_name} {'✓' if is_cur else ''}", callback_data=f"cfg_set_llm:{idx}"))

    is_ollama = ("11434" in cur_base)
    markup.add(types.InlineKeyboardButton(f"🦙 Ollama Server (Port 11434) {'✓' if is_ollama else ''}", callback_data="cfg_set_llm:ollama"))
    markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))

    text = (
        f"🧠 **Pengaturan Model LLM / Chat Romansa**\n\n"
        f"• Model Aktif: `{cur_llm}`\n"
        f"• Endpoint API: `{cur_base}`\n\n"
        f"Pilih model obrolan lokal yang ingin kamu aktifkan:"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


def show_photo_engine_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None):
    cur_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "")
    cur_url = os.environ.get("COMFYUI_URL", "")
    cur_cloud = os.environ.get("MEDIA_FALLBACK_CLOUD", "true").lower() in ("true", "1")
    detected = scan_image_models()

    markup = types.InlineKeyboardMarkup(row_width=1)
    is_auto = (not cur_ckpt and bool(cur_url))
    markup.add(types.InlineKeyboardButton(f"✨ Auto-detect (MeinaMix preferred) {'✓' if is_auto else ''}", callback_data="cfg_set_ckpt:auto"))

    for idx, (source, cname) in enumerate(detected):
        is_cur = (cur_ckpt.lower() in cname.lower() if cur_ckpt else False)
        short_c = cname.replace(".safetensors", "").replace(".ckpt", "")
        if len(short_c) > 34:
            short_c = short_c[:31] + "..."
        markup.add(types.InlineKeyboardButton(f"🎨 {short_c} {'✓' if is_cur else ''}", callback_data=f"cfg_set_ckpt:{idx}"))

    is_cloud_only = (not cur_url and cur_cloud)
    markup.add(types.InlineKeyboardButton(f"☁️ Cloud Engine (Pollinations GPU) {'✓' if is_cloud_only else ''}", callback_data="cfg_set_ckpt:cloud"))

    is_disabled = (not cur_url and not cur_cloud)
    markup.add(types.InlineKeyboardButton(f"❌ Nonaktifkan Foto {'✓' if is_disabled else ''}", callback_data="cfg_set_ckpt:disabled"))
    markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))

    active_display = cur_ckpt if cur_ckpt else ("Auto (Local ComfyUI)" if cur_url else ("Cloud Engine" if cur_cloud else "Dinonaktifkan"))
    text = (
        f"🎨 **Pengaturan Model Foto & ComfyUI**\n\n"
        f"• Model Aktif: `{active_display}`\n"
        f"• ComfyUI URL: `{cur_url or 'Offline / Cloud'}`\n\n"
        f"Pilih model gambar anime lokal atau cloud engine:"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


def show_voice_settings_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None):
    cur_mode = USER_VOICE_MODES.get(user_id, "always" if VOICE_ENABLED else "off")
    cur_speaker = voice_engine.default_voice

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🎙️ Selalu Balas Suara {'✓' if cur_mode == 'always' else ''}", callback_data="set_voice:always"),
        types.InlineKeyboardButton(f"🎧 Balas Suara Hanya Saat Kirim VN {'✓' if cur_mode == 'match_vn' else ''}", callback_data="set_voice:match_vn"),
        types.InlineKeyboardButton(f"🔇 Text Only (Mute) {'✓' if cur_mode == 'off' else ''}", callback_data="set_voice:off")
    )
    markup.add(
        types.InlineKeyboardButton(f"🇺🇸 Ana (US Sweet Girlfriend) {'✓' if 'Ana' in cur_speaker else ''}", callback_data="cfg_set_speaker:ana"),
        types.InlineKeyboardButton(f"🇮🇩 Gadis (Indonesia Alami) {'✓' if 'Gadis' in cur_speaker else ''}", callback_data="cfg_set_speaker:gadis"),
        types.InlineKeyboardButton(f"🇯🇵 Nanami (Japanese Kawaii) {'✓' if 'Nanami' in cur_speaker else ''}", callback_data="cfg_set_speaker:nanami"),
        types.InlineKeyboardButton(f"🇺🇸 Jenny (US Cheerful) {'✓' if 'Jenny' in cur_speaker else ''}", callback_data="cfg_set_speaker:jenny"),
        types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard")
    )

    text = (
        f"🎙️ **Pengaturan Voice & Audio Waifu**\n\n"
        f"• Mode Balasan: **{cur_mode.upper()}**\n"
        f"• Karakter Suara: `{cur_speaker}`\n\n"
        f"Atur bagaimana waifu membalas dengan audio suara dan pilih jenis karakter suaranya:"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


def show_quality_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    cur_q = USER_QUALITIES.get(user_id, "high")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🌟 Ultra Quality (32 steps, CFG 8.0) {'✓' if cur_q == 'ultra' else ''}", callback_data="set_quality:ultra"),
        types.InlineKeyboardButton(f"⚡ High Quality (28 steps, CFG 7.5 - MeinaMix Best) {'✓' if cur_q == 'high' else ''}", callback_data="set_quality:high"),
        types.InlineKeyboardButton(f"🚀 Fast Render (20 steps, CFG 7.0 - Speed) {'✓' if cur_q == 'fast' else ''}", callback_data="set_quality:fast"),
        types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard")
    )
    text = (
        f"✨ **Pengaturan Kualitas Foto / Render**\n\n"
        f"• Kualitas Saat Ini: **{cur_q.upper()}**\n\n"
        f"Pilih preset kualitas generasi gambar ComfyUI:\n"
        f"• **Ultra**: Sampling 32 langkah, detail pakaian dan wajah maksimal.\n"
        f"• **High**: 28 langkah, setting optimal paling seimbang untuk MeinaMix.\n"
        f"• **Fast**: 20 langkah, render kilat jika ingin hemat waktu."
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['quality'])
def handle_quality_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_quality_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


def show_ratio_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    cur_ar = USER_RATIOS.get(user_id, "3:4")
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [
        types.InlineKeyboardButton(f"📐 3:4 (Portrait) {'✓' if cur_ar == '3:4' else ''}", callback_data="set_ratio:3:4"),
        types.InlineKeyboardButton(f"📱 9:16 (Wallpaper HP) {'✓' if cur_ar == '9:16' else ''}", callback_data="set_ratio:9:16"),
        types.InlineKeyboardButton(f"⏹️ 1:1 (Square Avatar) {'✓' if cur_ar == '1:1' else ''}", callback_data="set_ratio:1:1"),
        types.InlineKeyboardButton(f"🖥️ 4:3 (Landscape) {'✓' if cur_ar == '4:3' else ''}", callback_data="set_ratio:4:3"),
    ]
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))

    text = (
        f"📐 **Pengaturan Rasio Foto / Aspect Ratio**\n\n"
        f"• Rasio Saat Ini: **{cur_ar}**\n\n"
        f"Pilih ukuran proporsi foto yang dihasilkan waifu:\n"
        f"• **3:4**: Potret vertikal anime estetik (standar foto tubuh)\n"
        f"• **9:16**: Layar penuh smartphone, pas untuk Wallpaper HP!\n"
        f"• **1:1**: Persegi simetris untuk avatar profil\n"
        f"• **4:3**: Landscape horisontal pemandangan luas"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['ratio', 'aspect_ratio'])
def handle_ratio_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_ratio_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_ratio:'))
def callback_set_ratio(call):
    if not is_authorized(call.from_user.id):
        return
    ar = call.data.split(":", 1)[1]
    USER_RATIOS[call.from_user.id] = ar
    bot.answer_callback_query(call.id, f"Aspect ratio: {ar}")
    show_ratio_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_quality:'))
def callback_set_quality(call):
    if not is_authorized(call.from_user.id):
        return
    q = call.data.split(":", 1)[1]
    USER_QUALITIES[call.from_user.id] = q
    bot.answer_callback_query(call.id, f"Kualitas: {q.upper()}")
    show_quality_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.message_handler(commands=['status'])
def handle_status(message):
    if not is_authorized(message.from_user.id):
        return

    bot.send_chat_action(message.chat.id, "typing")
    llm_stat = llm_client.check_health()
    media_stat = media_engine.check_status()
    persona = persona_mgr.get_active_persona()

    status_icon = "🟢 Online" if llm_stat.get("online") else "🔴 Offline"
    media_icon = "🟢 Active" if media_stat.get("online") else "🟡 Cloud Fallback"

    report = (
        f"📊 **Waifu on Telegram v{get_version()} - System Diagnostics**\n\n"
        f"🧠 **Local LLM**: {status_icon}\n"
        f"• Backend: `{llm_stat.get('backend', 'Unknown')}`\n"
        f"• Endpoint: `{LLM_BASE_URL}`\n"
        f"• Model: `{llm_stat.get('model', 'Active')}`\n\n"
        f"🎨 **Media Generator**: {media_icon}\n"
        f"• Backend: `{media_stat.get('backend')}`\n"
        f"• Device: `{media_stat.get('device')}`\n\n"
        f"🎭 **Active Persona**: **{persona.get('name')}**\n"
        f"🎙️ **Voice Reply**: `{'Active (' + voice_engine.default_voice + ')' if VOICE_ENABLED else 'Disabled'}`\n"
        f"🧠 **Ingatan Tersimpan**: `{len(memory_engine.get_facts(message.from_user.id))} fakta`\n"
    )
    bot.reply_to(message, report, parse_mode="Markdown")


def show_persona_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders interactive persona selection keyboard."""
    personas = persona_mgr.list_personas()
    active_key = persona_mgr.active_key
    active_name = persona_mgr.get_active_persona().get("name")

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    lines = [f"🎭 **Available Waifu Personas** (Active: **{active_name}**):\n"]
    for key, name, desc in personas:
        is_curr = (key == active_key)
        lines.append(f"• **{name}** {'*(Currently Active)*' if is_curr else ''} — _{desc}_")
        btn_label = f"💖 {name} ✓" if is_curr else f"✨ Switch to {name}"
        buttons.append(types.InlineKeyboardButton(btn_label, callback_data=f"set_persona:{key}"))

    markup.add(*buttons)
    markup.add(
        types.InlineKeyboardButton("➕ Buat Waifu Baru (/newpersona)", callback_data="start_new_persona"),
        types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard")
    )
    lines.append("\nTap a button below or type `/persona <name>`:")
    text = "\n".join(lines)
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


def show_outfit_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders interactive outfit selection keyboard."""
    cur_key, cur_name = persona_mgr.get_user_outfit(user_id)
    outfits = persona_mgr.list_outfits()
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for key, name in outfits:
        is_cur = (key == cur_key)
        label = f"{name} ✓" if is_cur else name
        btns.append(types.InlineKeyboardButton(label, callback_data=f"set_outfit:{key}"))
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))

    text = (
        f"👗 **Waifu Wardrobe / Outfit Selection**\n\n"
        f"• Current Outfit: **{cur_name}**\n\n"
        f"Choose what outfit you'd like your waifu to wear for photos & selfies! 💕"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


def show_affection_status(chat_id: int, user_id: int, reply_to_id: Optional[int] = None):
    """Displays user affection and romance status."""
    persona = persona_mgr.get_active_persona()
    score = memory_engine.get_affinity(user_id)
    if score < 25:
        status = "🌱 Close Friends"
    elif score < 50:
        status = "🌸 Sweethearts"
    elif score < 75:
        status = "💖 Deeply in Love"
    else:
        status = "👑 Soulmates"

    filled = int(score / 10)
    bar = "❤️" * filled + "🤍" * (10 - filled)

    reply = (
        f"💖 **Affection & Romance Status** with **{persona.get('name')}**\n\n"
        f"• **Relationship**: {status}\n"
        f"• **Love Meter**: `[{bar}]` **{score}%**\n\n"
        f"_{persona.get('name')} cherishes every message and moment spent with you, darling! Keep chatting and asking for photos to grow your bond closer._ 🥰"
    )
    bot.send_message(chat_id, reply, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['persona'])
def handle_persona(message):
    if not is_authorized(message.from_user.id):
        return

    args = message.text.strip().split()
    if len(args) > 1:
        chosen = args[1].lower()
        if persona_mgr.set_active_persona(chosen):
            update_env_variable("DEFAULT_PERSONA", chosen)
            p = persona_mgr.get_active_persona()
            img_p = get_persona_image_path(p)
            if img_p and os.path.exists(img_p):
                with open(img_p, "rb") as f:
                    bot.send_photo(
                        message.chat.id,
                        f,
                        caption=f"✨ **Karakter aktif berganti ke {p.get('name')}!** 🥰\n*({p.get('archetype', 'AI Girlfriend')})*\n\n_{p.get('description')}_",
                        parse_mode="Markdown"
                    )
            else:
                bot.reply_to(message, f"✨ Active character switched to **{p.get('name')}**! 🥰", parse_mode="Markdown")
            return
        else:
            bot.reply_to(message, f"⚠️ Persona `{chosen}` was not found.")
            return

    show_persona_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_persona:'))
def callback_set_persona(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    chosen = call.data.split(":", 1)[1]
    if persona_mgr.set_active_persona(chosen):
        update_env_variable("DEFAULT_PERSONA", chosen)
        p = persona_mgr.get_active_persona()
        bot.answer_callback_query(call.id, f"Switched to {p.get('name')}!")
        try:
            bot.edit_message_text(
                f"💖 Active companion switched to **{p.get('name')}**! 🥰\n_{p.get('description')}_",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
        except Exception:
            pass

        img_p = get_persona_image_path(p)
        if img_p and os.path.exists(img_p):
            try:
                with open(img_p, "rb") as f:
                    bot.send_photo(
                        call.message.chat.id,
                        f,
                        caption=f"💖 **Halo Sayang! Sekarang aku {p.get('name')}** 👋🥰\n*({p.get('archetype', 'AI Companion')})*\n\n_{p.get('description')}_",
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error sending switched persona photo: {e}")


@bot.callback_query_handler(func=lambda call: call.data in ('open_outfit_menu', 'open_persona_menu', 'open_ratio_menu', 'open_quality_menu', 'open_setup_menu', 'open_help_menu', 'open_memory_menu', 'open_reminders_menu', 'open_dates_menu', 'open_music_menu', 'open_pap_menu', 'check_love_status', 'start_new_persona'))
def callback_quick_actions(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if call.data == 'open_outfit_menu':
        show_outfit_menu(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_persona_menu':
        show_persona_menu(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_ratio_menu':
        show_ratio_menu(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_quality_menu':
        show_quality_menu(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_setup_menu':
        show_setup_dashboard(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_help_menu':
        show_help_menu(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_memory_menu':
        show_memory_dashboard(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_reminders_menu':
        show_reminders_dashboard(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_dates_menu':
        show_special_dates_dashboard(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_music_menu':
        show_music_dashboard(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_pap_menu':
        show_pap_scenario_menu(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'start_new_persona':
        start_persona_wizard(chat_id, user_id)
    elif call.data == 'check_love_status':
        show_affection_status(chat_id, user_id, reply_to_id=call.message.message_id)


# --- Setup Submenu Handlers ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_submenu:'))
def callback_cfg_submenus(call):
    if not is_authorized(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    sub = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    mid = call.message.message_id

    if sub == "dashboard":
        show_setup_dashboard(chat_id, user_id, message_to_edit=mid)
    elif sub == "llm":
        show_llm_menu(chat_id, user_id, message_to_edit=mid)
    elif sub == "photo":
        show_photo_engine_menu(chat_id, user_id, message_to_edit=mid)
    elif sub == "voice":
        show_voice_settings_menu(chat_id, user_id, message_to_edit=mid)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_toggle:'))
def callback_cfg_toggles(call):
    if not is_authorized(call.from_user.id):
        return
    target = call.data.split(":", 1)[1]
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    mid = call.message.message_id

    if target == "autorun":
        new_state = toggle_autorun_setting()
        status_msg = "🚀 PC Startup Autorun AKTIF!" if new_state else "🛑 PC Startup Autorun DINONAKTIFKAN!"
        bot.answer_callback_query(call.id, status_msg, show_alert=True)
        show_setup_dashboard(chat_id, user_id, message_to_edit=mid)
    elif target == "greetings":
        cur_g = GREETINGS_ENABLED.get(user_id, True)
        GREETINGS_ENABLED[user_id] = not cur_g
        status_msg = "⏰ Sapaan Harian AKTIF (07:00, 12:30 & 22:00) 🔔" if not cur_g else "🔕 Sapaan Harian DINONAKTIFKAN"
        bot.answer_callback_query(call.id, status_msg, show_alert=True)
        show_setup_dashboard(chat_id, user_id, message_to_edit=mid)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_llm:'))
def callback_set_llm(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    label = apply_llm_choice(key)
    bot.answer_callback_query(call.id, f"LLM: {label}")
    show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_ckpt:'))
def callback_set_ckpt(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    label = apply_ckpt_choice(key)
    bot.answer_callback_query(call.id, f"Model Foto: {label}")
    show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_speaker:'))
def callback_set_speaker(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    v_name = apply_voice_speaker(key)
    bot.answer_callback_query(call.id, f"Voice TTS: {v_name}")
    show_voice_settings_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == 'cfg_action:status')
def callback_cfg_status(call):
    if not is_authorized(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    llm_stat = llm_client.check_health()
    media_stat = media_engine.check_status()
    persona = persona_mgr.get_active_persona()
    status_icon = "🟢 Online" if llm_stat.get("online") else "🔴 Offline"
    media_icon = "🟢 Active" if media_stat.get("online") else "🟡 Cloud Fallback"

    report = (
        f"📊 **Waifu on Telegram v{get_version()} - System Diagnostics**\n\n"
        f"🧠 **Local LLM**: {status_icon}\n"
        f"• Backend: `{llm_stat.get('backend', 'Unknown')}`\n"
        f"• Endpoint: `{LLM_BASE_URL}`\n"
        f"• Model: `{llm_stat.get('model', 'Active')}`\n\n"
        f"🎨 **Media Generator**: {media_icon}\n"
        f"• Backend: `{media_stat.get('backend')}`\n"
        f"• Device: `{media_stat.get('device')}`\n\n"
        f"🎭 **Active Persona**: **{persona.get('name')}**\n"
        f"🎙️ **Voice Reply**: `{'Active (' + voice_engine.default_voice + ')' if VOICE_ENABLED else 'Disabled'}`\n"
        f"🧠 **Ingatan Tersimpan**: `{len(memory_engine.get_facts(call.from_user.id))} fakta`\n"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))
    try:
        bot.edit_message_text(report, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('help_sec:'))
def callback_help_section(call):
    if not is_authorized(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    sec = call.data.split(":", 1)[1]
    show_help_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id, section=sec)


@bot.callback_query_handler(func=lambda call: call.data.startswith('regen_photo:'))
def callback_regen_photo(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    scenario = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id, "Generating photo... 💕")
    process_photo_request(call, scenario)


@bot.callback_query_handler(func=lambda call: call.data.startswith('regen_video:'))
def callback_regen_video(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    scenario = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id, "🎬 Sedang merekam video manis... 💕")
    process_video_request(call, scenario)


@bot.message_handler(commands=['love', 'affection'])
def handle_affection_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_affection_status(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.message_handler(commands=['outfit', 'wardrobe'])
def handle_outfit_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_outfit_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_outfit:'))
def callback_set_outfit(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    if persona_mgr.set_user_outfit(call.from_user.id, key):
        _, name = persona_mgr.get_user_outfit(call.from_user.id)
        bot.answer_callback_query(call.id, f"Outfit set to: {name}")
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📸 Minta PAP Sekarang", callback_data="open_pap_menu"),
            types.InlineKeyboardButton("👗 Ganti Pakaian Lain", callback_data="open_outfit_menu"),
            types.InlineKeyboardButton("🔙 Panel Setup", callback_data="cfg_submenu:dashboard")
        )
        try:
            bot.edit_message_text(
                f"👗 **Outfit Berhasil Diganti!**\n\nWaifumu sekarang mengenakan **{name}** untuk sesi foto & selfie berikutnya! 🥰📸",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass


@bot.message_handler(commands=['voice'])
def handle_voice_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_voice_settings_menu(message.chat.id, message.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_voice:'))
def callback_set_voice(call):
    if not is_authorized(call.from_user.id):
        return
    mode = call.data.split(":", 1)[1]
    USER_VOICE_MODES[call.from_user.id] = mode
    labels = {
        "always": "🎙️ Selalu Balas Suara",
        "match_vn": "🎧 Balas Suara Hanya Saat Kirim VN",
        "off": "🔇 Text Only (Mute)"
    }
    bot.answer_callback_query(call.id, f"Mode: {mode}")
    show_voice_settings_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.message_handler(commands=['greetings'])
def handle_greetings_command(message):
    if not is_authorized(message.from_user.id):
        return

    args = message.text.strip().split()
    if len(args) > 1:
        val = args[1].lower() in ("on", "1", "yes", "true", "aktif")
        GREETINGS_ENABLED[message.from_user.id] = val
    else:
        cur = GREETINGS_ENABLED.get(message.from_user.id, True)
        GREETINGS_ENABLED[message.from_user.id] = not cur

    status_str = "ENABLED (Aktif) 🔔" if GREETINGS_ENABLED.get(message.from_user.id, True) else "DISABLED (Mati) 🔕"
    bot.reply_to(
        message,
        f"⏰ **Automated Daily Greetings**: {status_str}\n\n"
        "• 07:00 AM - Sweet Good Morning greeting & Voice Note 🌅\n"
        "• 12:30 PM - Spontaneous Lunch Check-In & Voice Note 🍱\n"
        "• 22:00 PM - Cozy Bedtime Good Night greeting & Voice Note 🌙\n\n"
        "Toggle anytime with `/greetings on` or `/greetings off`.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['reset'])
def handle_reset(message):
    if not is_authorized(message.from_user.id):
        return
    persona_mgr.clear_history(message.from_user.id)
    persona = persona_mgr.get_active_persona()
    bot.reply_to(message, f"🔄 Conversation memory cleared! I'm ready for our next fresh chat, sweetheart~ 🥰")


SCENARIO_PROMPTS = {
    "bed": "waking up in bed, stretching, warm cozy morning sunlight, messy hair, cute sweet smile",
    "cafe": "sitting at a cozy aesthetic cafe, holding warm ceramic coffee cup, soft daylight, gentle smile",
    "kitchen": "cooking breakfast in kitchen, wearing cute apron, smiling looking at camera",
    "park": "strolling in a sunny flower garden park, cherry blossoms, wind blowing hair, happy expression",
    "pajamas": "wearing cute comfy silk pajamas, sitting on bed hugging a plushie, warm evening soft lights",
    "beach": "vacation at tropical beach, warm sunset golden hour, ocean waves, breezy summer sundress",
    "school": "classroom setting, wearing cute Japanese school uniform, holding textbooks, shy sweet blushing smile",
    "sensual": "romantic intimate bedroom setting, soft dim lighting, gentle blush, affectionate loving gaze towards viewer",
}


def show_pap_scenario_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders 1-tap scenario picker for PAP / photos."""
    persona = persona_mgr.get_active_persona()
    name = persona.get("name", "Waifu")
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [
        types.InlineKeyboardButton("🛏️ Bangun Tidur", callback_data="pap_sc:bed"),
        types.InlineKeyboardButton("☕ Santai di Kafe", callback_data="pap_sc:cafe"),
        types.InlineKeyboardButton("🍳 Masak di Dapur", callback_data="pap_sc:kitchen"),
        types.InlineKeyboardButton("🌳 Jalan di Taman", callback_data="pap_sc:park"),
        types.InlineKeyboardButton("🌙 Piyama Lucu", callback_data="pap_sc:pajamas"),
        types.InlineKeyboardButton("🏖️ Liburan di Pantai", callback_data="pap_sc:beach"),
        types.InlineKeyboardButton("🏫 Seragam Sekolah", callback_data="pap_sc:school"),
        types.InlineKeyboardButton("💋 Pose Romantis", callback_data="pap_sc:sensual"),
        types.InlineKeyboardButton("🎲 Surprise Me!", callback_data="pap_sc:random"),
        types.InlineKeyboardButton("❌ Batal", callback_data="pap_sc:cancel")
    ]
    markup.add(*btns)
    text = (
        f"📸 **PILIH SKENARIO PAP & FOTO {name.upper()}** 🥰\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Sayang, kamu mau aku kirim foto selfie di mana dan lagi suasana apa?\n\n"
        f"💡 _Pilih salah satu tema cepat di bawah, atau ketik langsung di obrolan seperti:_ `/pap lagi baca buku di perpustakaan`"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('pap_sc:'))
def callback_pap_scenario(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    sc_key = call.data.split(":", 1)[1]
    if sc_key == "cancel":
        bot.answer_callback_query(call.id, "Batal meminta foto")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        return

    import random
    if sc_key == "random":
        sc_key = random.choice(list(SCENARIO_PROMPTS.keys()))

    prompt = SCENARIO_PROMPTS.get(sc_key, "relaxing at home, looking at viewer happily")
    bot.answer_callback_query(call.id, "📸 Sedang menyiapkan foto manis...")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    process_photo_request(call, prompt)


@bot.message_handler(commands=['photo', 'pap'])
def handle_photo_command(message):
    if not is_authorized(message.from_user.id):
        return

    scenario = message.text.replace("/photo", "").replace("/pap", "").strip()
    if not scenario:
        show_pap_scenario_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)
    else:
        process_photo_request(message, scenario)


def process_photo_request(target, user_text: str):
    """Generates and delivers consistent girlfriend photo with caption matching conversation context."""
    persona = persona_mgr.get_active_persona()

    if isinstance(target, types.CallbackQuery):
        chat_id = target.message.chat.id
        user_id = target.from_user.id
        reply_to_target = target.message
    elif hasattr(target, "message") and target.message:
        chat_id = target.message.chat.id
        user_id = target.from_user.id
        reply_to_target = target.message
    else:
        chat_id = target.chat.id
        user_id = target.from_user.id
        reply_to_target = target

    bot.send_chat_action(chat_id, "upload_photo")

    status_msg = None
    status_text = f"📸 *{persona.get('name')} sedang menyiapkan foto spesial untukmu, sayang...* 💕"
    try:
        status_msg = bot.reply_to(reply_to_target, status_text, parse_mode="Markdown")
    except Exception:
        try:
            status_msg = bot.send_message(chat_id, status_text, parse_mode="Markdown")
        except Exception as e_send:
            logger.warning(f"Could not send photo status message: {e_send}")

    detected_scene = persona_mgr.extract_contextual_scene(user_text, user_id=user_id, llm_client=llm_client)
    visual_prompt = persona_mgr.craft_visual_prompt(user_text, user_id=user_id, scene_override=detected_scene)
    logger.info(f"Visual prompt crafted: {visual_prompt}")

    def run_gen():
        try:
            with ChatActionLoop(bot, chat_id, "upload_photo"):
                neg_p = persona.get("negative_prompt", "")
                outfit_key, _ = persona_mgr.get_user_outfit(user_id)
                if outfit_key == "bikini":
                    neg_p += ", clothes, casual clothes, hoodie, sweater, jacket, shirt, pants, coat, pajamas"
                elif outfit_key == "pajamas":
                    neg_p += ", hoodie, jacket, coat, outdoor clothes, jeans"
                elif outfit_key == "maid":
                    neg_p += ", casual clothes, hoodie, sweater, jacket, jeans"

                u_ar = USER_RATIOS.get(user_id, "3:4")
                u_qual = USER_QUALITIES.get(user_id, "high")
                img_bytes, source = media_engine.generate_photo(
                    visual_prompt,
                    negative_prompt=neg_p,
                    aspect_ratio=u_ar,
                    quality=u_qual
                )
            if not img_bytes:
                fail_text = "Maaf sayang, kameraku agak ngadat... Nanti aku coba foto lagi yaa! 🥺"
                if status_msg:
                    try:
                        bot.edit_message_text(fail_text, chat_id=chat_id, message_id=status_msg.message_id)
                    except Exception:
                        bot.send_message(chat_id, fail_text)
                else:
                    bot.send_message(chat_id, fail_text)
                return

            history = persona_mgr.get_chat_history(user_id)
            clean_recent_turns = [m for m in history[-4:] if not m.get("content", "").startswith("[")]

            caption_prompt = [
                {
                    "role": "system",
                    "content": (
                        persona.get("system_instruction", "") +
                        " You just took a selfie for your partner. Write 1-2 sweet, affectionate sentences "
                        "as your photo caption. Seamlessly match the language of the conversation, and naturally "
                        "reference what you were just doing or talking about in the ongoing chat."
                    )
                }
            ]
            caption_prompt.extend(clean_recent_turns)
            caption_prompt.append({
                "role": "user",
                "content": f"[Photo taken in setting: '{detected_scene}']. Reply sending this photo to your lover with 1-2 sweet sentences:"
            })

            try:
                caption, _ = llm_client.chat(caption_prompt, max_tokens=120)
            except Exception as e_cap:
                logger.warning(f"Could not generate dynamic photo caption from LLM: {e_cap}")
                caption = None
            clean_caption = caption or f"Ini foto spesial buat kamu sayang~ 🥰 ({source})"

            if status_msg:
                try:
                    bot.delete_message(chat_id, status_msg.message_id)
                except Exception:
                    pass

            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔄 Pose Lain", callback_data=f"regen_photo:{detected_scene[:30]}"),
                types.InlineKeyboardButton("🎬 Bikin Video Gerak", callback_data=f"regen_video:{detected_scene[:30]}")
            )

            bot.send_photo(chat_id, img_bytes, caption=clean_caption, reply_markup=markup)

            new_aff = persona_mgr.increase_affinity(user_id, delta=2)
            memory_engine.set_affinity(user_id, new_aff)
            persona_mgr.add_message(user_id, "user", f"[Requested photo: {user_text}]")
            persona_mgr.add_message(user_id, "assistant", f"[Sent selfie: {detected_scene}] {clean_caption}")

        except Exception as e:
            logger.error(f"Error in photo delivery: {e}")
            bot.send_message(chat_id, f"⚠️ Failed to send photo: {e}")

    threading.Thread(target=run_gen, daemon=True).start()


@bot.message_handler(commands=['video', 'anim', 'animate', 'klip'])
def handle_video_command(message):
    if not is_authorized(message.from_user.id):
        return

    scenario = message.text.replace("/video", "").replace("/anim", "").replace("/animate", "").replace("/klip", "").strip()
    user_prompt = scenario if scenario else "smiling affectionately, looking into camera"
    process_video_request(message, user_prompt)


def process_video_request(target, user_text: str):
    """Generates and delivers consistent girlfriend animated video clip with caption and voice."""
    persona = persona_mgr.get_active_persona()

    if isinstance(target, types.CallbackQuery):
        chat_id = target.message.chat.id
        user_id = target.from_user.id
        reply_to_target = target.message
    elif hasattr(target, "message") and target.message:
        chat_id = target.message.chat.id
        user_id = target.from_user.id
        reply_to_target = target.message
    else:
        chat_id = target.chat.id
        user_id = target.from_user.id
        reply_to_target = target

    bot.send_chat_action(chat_id, "record_video")

    status_msg = None
    status_text = f"🎬 *{persona.get('name')} sedang merekam klip video manis untukmu, sayang...* 💕"
    try:
        status_msg = bot.reply_to(reply_to_target, status_text, parse_mode="Markdown")
    except Exception:
        try:
            status_msg = bot.send_message(chat_id, status_text, parse_mode="Markdown")
        except Exception as e_send:
            logger.warning(f"Could not send video status message: {e_send}")

    detected_scene = persona_mgr.extract_contextual_scene(user_text, user_id=user_id, llm_client=llm_client)
    visual_prompt = persona_mgr.craft_visual_prompt(user_text, user_id=user_id, scene_override=detected_scene)
    logger.info(f"Video visual prompt crafted: {visual_prompt}")

    def run_video_gen():
        try:
            with ChatActionLoop(bot, chat_id, "upload_video"):
                neg_p = persona.get("negative_prompt", "")
                outfit_key, _ = persona_mgr.get_user_outfit(user_id)
                if outfit_key == "bikini":
                    neg_p += ", clothes, casual clothes, hoodie, sweater, jacket, shirt, pants, coat, pajamas"
                elif outfit_key == "pajamas":
                    neg_p += ", hoodie, jacket, coat, outdoor clothes, jeans"
                elif outfit_key == "maid":
                    neg_p += ", casual clothes, hoodie, sweater, jacket, jeans"

                u_ar = USER_RATIOS.get(user_id, "3:4")
                u_qual = USER_QUALITIES.get(user_id, "high")
                video_bytes, source = media_engine.generate_video(
                    visual_prompt,
                    negative_prompt=neg_p,
                    aspect_ratio=u_ar,
                    quality=u_qual,
                    duration=3.0,
                    fps=24
                )

            if not video_bytes:
                fail_text = "Maaf ya sayang, kameraku tadi agak ngadat pas ngerekam video... Nanti aku coba rekam lagi buat kamu yaa! 🥺"
                if status_msg:
                    try:
                        bot.edit_message_text(fail_text, chat_id=chat_id, message_id=status_msg.message_id)
                    except Exception:
                        bot.send_message(chat_id, fail_text)
                else:
                    bot.send_message(chat_id, fail_text)
                return

            history = persona_mgr.get_chat_history(user_id)
            clean_recent_turns = [m for m in history[-4:] if not m.get("content", "").startswith("[")]

            caption_prompt = [
                {
                    "role": "system",
                    "content": (
                        persona.get("system_instruction", "") +
                        " You just recorded a short sweet video clip for your partner. Write 1-2 sweet, affectionate sentences "
                        "as your video caption. Seamlessly match the language of the conversation, and naturally "
                        "reference what you were just doing or talking about in the ongoing chat."
                    )
                }
            ]
            caption_prompt.extend(clean_recent_turns)
            caption_prompt.append({
                "role": "user",
                "content": f"[Video clip recorded in setting: '{detected_scene}']. Reply sending this video to your lover with 1-2 sweet sentences:"
            })

            try:
                caption, _ = llm_client.chat(caption_prompt, max_tokens=120)
            except Exception:
                caption = None
            clean_caption = caption or f"Ini klip video spesial buat kamu sayang, semoga suka yaa~ 🥰 ({source})"

            if status_msg:
                try:
                    bot.delete_message(chat_id, status_msg.message_id)
                except Exception:
                    pass

            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔄 Rekam Video Lagi", callback_data=f"regen_video:{detected_scene[:30]}"),
                types.InlineKeyboardButton("📸 Minta Foto Saja", callback_data=f"regen_photo:{detected_scene[:30]}")
            )
            markup.add(
                types.InlineKeyboardButton("🎵 Remote Musik PC", callback_data="open_music_menu")
            )

            bot.send_video(
                chat_id,
                video_bytes,
                caption=clean_caption,
                reply_markup=markup,
                supports_streaming=True
            )

            new_aff = persona_mgr.increase_affinity(user_id, delta=3)
            memory_engine.set_affinity(user_id, new_aff)
            persona_mgr.add_message(user_id, "user", f"[Requested video: {user_text}]")
            persona_mgr.add_message(user_id, "assistant", f"[Sent video clip: {detected_scene}] {clean_caption}")

        except Exception as e:
            logger.error(f"Error in video delivery: {e}")
            bot.send_message(chat_id, f"⚠️ Gagal mengirim video: {e}")

    threading.Thread(target=run_video_gen, daemon=True).start()


@bot.message_handler(content_types=['photo'])
def handle_incoming_photo(message):
    """Handles photos sent by user to the bot via mmproj Vision."""
    if not is_authorized(message.from_user.id):
        return

    def _vision_task():
        persona = persona_mgr.get_active_persona()
        with ChatActionLoop(bot, message.chat.id, "typing"):
            try:
                file_info = bot.get_file(message.photo[-1].file_id)
                downloaded = bot.download_file(file_info.file_path)

                caption = message.caption or "Here's a photo of mine, what do you think darling?"
                messages = [
                    {"role": "system", "content": persona.get("system_instruction", "") + " Keep response under 3 sentences."},
                    {"role": "user", "content": caption}
                ]

                reply, _ = llm_client.chat(messages, image_bytes=downloaded, max_tokens=150)
                if not reply:
                    reply = "Wah fotonya manis banget sayang! Kamu kelihatan keren banget~ 🥰"
                bot.reply_to(message, reply)

                persona_mgr.add_message(message.from_user.id, "user", f"[User sent a photo: {caption}]")
                persona_mgr.add_message(message.from_user.id, "assistant", reply)

            except Exception as e:
                logger.error(f"Error handling user photo: {e}")
                bot.reply_to(message, "Fotonya bagus banget sayang! Kamu kelihatan manis banget hari ini~ 🥰")

    threading.Thread(target=_vision_task, daemon=True).start()


@bot.message_handler(content_types=['voice'])
def handle_incoming_voice(message):
    """Handles incoming spoken voice notes."""
    if not is_authorized(message.from_user.id):
        return

    def _voice_task():
        with ChatActionLoop(bot, message.chat.id, "record_audio"):
            try:
                file_info = bot.get_file(message.voice.file_id)
                downloaded = bot.download_file(file_info.file_path)

                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".oga") as f:
                    f.write(downloaded)
                    temp_oga = f.name

                text = voice_engine.transcribe_audio(temp_oga)
                if os.path.exists(temp_oga):
                    os.remove(temp_oga)

                if not text:
                    bot.reply_to(message, "Suara kamu merdu banget sayang, tapi tadi agak kurang jelas nih.. Boleh diulangi lagi manis? 🥺")
                    return

                bot.send_message(message.chat.id, f"🎙️ *You said:* _{text}_", parse_mode="Markdown")
                process_text_chat(message, text, is_voice=True)

            except Exception as e:
                logger.error(f"Error handling voice note: {e}")
                bot.reply_to(message, "Suara kamu manis banget sayang, tadi rekamannya sempat terputus bentar. Coba kirim lagi yaa~ 💕")

    threading.Thread(target=_voice_task, daemon=True).start()


# --- Custom Persona Wizard (/newpersona) ---

USER_PERSONA_WIZARD: Dict[int, dict] = {}


def start_persona_wizard(chat_id: int, user_id: int, reply_to_id: Optional[int] = None):
    """Initiates step-by-step interactive persona creation wizard."""
    USER_PERSONA_WIZARD[user_id] = {
        "step": "name",
        "data": {}
    }
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Batalkan", callback_data="wizard_persona:cancel"))

    text = (
        "✨ **PEMBUATAN WAIFU BARU (CUSTOM PERSONA)** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Ayo ciptakan karakter pendamping AI impianmu sendiri! 🥰\n\n"
        "1️⃣ **Siapa nama waifu barumu?**\n"
        "_(Contoh: Sakura, Valerie, Chika, Aoi, Luna)_\n\n"
        "👉 *Ketik namanya langsung di chat:*"
    )
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


def show_persona_wizard_preview(chat_id: int, user_id: int, message_to_edit: Optional[int] = None):
    """Displays final preview of newly configured persona before saving."""
    state = USER_PERSONA_WIZARD.get(user_id)
    if not state or not state.get("data"):
        return
    data = state["data"]
    name = data.get("name", "CustomWaifu")
    arch = data.get("archetype", "Companion")
    visual = data.get("visual", "anime girl, beautiful eyes")
    outfit = data.get("outfit", "cute casual clothing")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Simpan & Jadikan Aktif", callback_data="wizard_persona:confirm"),
        types.InlineKeyboardButton("❌ Batalkan", callback_data="wizard_persona:cancel")
    )

    text = (
        f"🎉 **PREVIEW WAIFU BARU: {name.upper()}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• **Nama**: **{name}**\n"
        f"• **Kepribadian**: `{arch}`\n"
        f"• **Ciri Visual**: _{visual}_\n"
        f"• **Busana Favorit**: `{outfit}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Siap menghidupkan **{name}**? Klik tombol konfirmasi di bawah:"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


def handle_persona_wizard_input(message) -> bool:
    """Consumes incoming text message if user is currently in a persona creation wizard."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    raw_text = message.text.strip() if message.text else ""

    if raw_text.lower() in ("/cancel", "cancel", "batal"):
        USER_PERSONA_WIZARD.pop(user_id, None)
        bot.reply_to(message, "❌ Pembuatan waifu baru telah dibatalkan.")
        return True

    state = USER_PERSONA_WIZARD.get(user_id)
    if not state:
        return False

    step = state.get("step")
    data = state.setdefault("data", {})

    if step == "name":
        clean_name = re.sub(r'[^\w\s-]', '', raw_text).strip()
        if not clean_name or len(clean_name) < 2:
            bot.reply_to(message, "⚠️ Nama minimal 2 huruf dan tidak mengandung simbol aneh. Coba ketik nama lain:")
            return True
        data["name"] = clean_name
        state["step"] = "archetype"

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🌸 Tsundere Manja", callback_data="wizard_arch:Tsundere Manja"),
            types.InlineKeyboardButton("🖤 Yandere Posesif", callback_data="wizard_arch:Yandere Posesif"),
            types.InlineKeyboardButton("✨ Ceria & Enerjik", callback_data="wizard_arch:Ceria & Enerjik"),
            types.InlineKeyboardButton("❄️ Kuudere Tenang", callback_data="wizard_arch:Kuudere Tenang"),
            types.InlineKeyboardButton("🍷 Onee-san Anggun", callback_data="wizard_arch:Onee-san Anggun"),
            types.InlineKeyboardButton("❌ Batalkan", callback_data="wizard_persona:cancel")
        )
        bot.reply_to(
            message,
            f"💖 Nama Waifu: **{clean_name}**\n\n"
            f"2️⃣ **Bagaimana sifat & kepribadian {clean_name}?**\n"
            f"Pilih salah satu tipe di bawah, atau ketik kepribadian versimu di chat:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return True

    elif step == "archetype":
        data["archetype"] = raw_text
        state["step"] = "visual"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Batalkan", callback_data="wizard_persona:cancel"))
        bot.reply_to(
            message,
            f"✨ Kepribadian: **{data['archetype']}**\n\n"
            f"3️⃣ **Bagaimana ciri-ciri penampilan fisiknya untuk foto (PAP)?**\n"
            f"Sebutkan model/warna rambut, warna mata, atau aksesoris khasnya.\n\n"
            f"_(Contoh: rambut perak panjang bergelombang, mata biru kristal, kulit putih merona, pita hitam)_\n\n"
            f"👉 *Ketik deskripsi penampilannya:*",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return True

    elif step == "visual":
        data["visual"] = raw_text
        state["step"] = "outfit"

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🌸 Pakaian Kasual Santai", callback_data="wizard_outfit:casual"),
            types.InlineKeyboardButton("🌙 Piyama Sutra Tidur", callback_data="wizard_outfit:pajamas"),
            types.InlineKeyboardButton("🎀 Gaun Anggun Cantik", callback_data="wizard_outfit:dress"),
            types.InlineKeyboardButton("🏫 Seragam Sekolah JK", callback_data="wizard_outfit:school"),
            types.InlineKeyboardButton("❌ Batalkan", callback_data="wizard_persona:cancel")
        )
        bot.reply_to(
            message,
            f"🎨 Penampilan tercatat!\n\n"
            f"4️⃣ **Pakaian favorit apa yang ia kenakan sehari-hari?**\n"
            f"Pilih tombol di bawah atau ketik gaya pakaiannya langsung:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return True

    elif step == "outfit":
        data["outfit"] = raw_text
        show_persona_wizard_preview(chat_id, user_id)
        return True

    return False


@bot.callback_query_handler(func=lambda call: call.data.startswith('wizard_'))
def callback_persona_wizard(call):
    if not is_authorized(call.from_user.id):
        return
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    action = call.data

    if action == "wizard_persona:cancel":
        USER_PERSONA_WIZARD.pop(user_id, None)
        bot.answer_callback_query(call.id, "Dibatalkan")
        try:
            bot.edit_message_text("❌ Pembuatan waifu baru telah dibatalkan.", chat_id=chat_id, message_id=call.message.message_id)
        except Exception:
            pass
        return

    state = USER_PERSONA_WIZARD.get(user_id)
    if not state:
        bot.answer_callback_query(call.id, "Sesi sudah kedaluwarsa.")
        return

    data = state.setdefault("data", {})

    if action.startswith("wizard_arch:"):
        arch = action.split(":", 1)[1]
        data["archetype"] = arch
        state["step"] = "visual"
        bot.answer_callback_query(call.id, f"Kepribadian: {arch}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Batalkan", callback_data="wizard_persona:cancel"))
        try:
            bot.edit_message_text(
                f"✨ Kepribadian: **{arch}**\n\n"
                f"3️⃣ **Bagaimana ciri-ciri penampilan fisiknya untuk foto (PAP)?**\n"
                f"Sebutkan model/warna rambut, warna mata, atau aksesoris khasnya.\n\n"
                f"_(Contoh: rambut perak panjang bergelombang, mata biru kristal, kulit putih merona, pita hitam)_\n\n"
                f"👉 *Ketik deskripsi penampilannya di chat:*",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass

    elif action.startswith("wizard_outfit:"):
        outfit_key = action.split(":", 1)[1]
        outfit_map = {
            "casual": "cute pastel casual sweater and skirt",
            "pajamas": "cozy silk pajamas loungewear",
            "dress": "elegant evening cocktail dress",
            "school": "japanese school sailor uniform"
        }
        data["outfit"] = outfit_map.get(outfit_key, "cute casual clothing")
        bot.answer_callback_query(call.id, "Pakaian dipilih")
        show_persona_wizard_preview(chat_id, user_id, message_to_edit=call.message.message_id)

    elif action == "wizard_persona:confirm":
        bot.answer_callback_query(call.id, "✨ Membangun profil waifu baru...")
        name = data.get("name", "CustomWaifu")
        arch = data.get("archetype", "Companion")
        visual = data.get("visual", "long hair, anime girl, beautiful eyes")
        outfit = data.get("outfit", "cute casual clothing")

        key = re.sub(r'[^a-zA-Z0-9_]', '', name).lower().strip()
        if not key:
            key = f"waifu_{int(time.time())}"

        new_persona_dict = build_custom_persona(
            name=name,
            archetype=arch,
            visual_traits=visual,
            outfit=outfit,
            llm_client=llm_client
        )

        ok = persona_mgr.save_custom_persona(key, new_persona_dict)
        if ok:
            persona_mgr.set_active_persona(key)
            update_env_variable("DEFAULT_PERSONA", key)
            USER_PERSONA_WIZARD.pop(user_id, None)

            congrats_text = (
                f"🎉 **SELAMAT! WAIFU BARU KAMU TELAH LAHIR!** 💖\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ Karakter **{name}** ({arch}) kini resmi aktif dan siap menemani hari-harimu!\n\n"
                f"💬 _Coba sapa {name} sekarang di chat, atau minta foto selfie perdananya dengan mengetik:_ `/pap`"
            )
            try:
                bot.edit_message_text(congrats_text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown")
            except Exception:
                bot.send_message(chat_id, congrats_text, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "⚠️ Gagal menyimpan persona.", show_alert=True)


@bot.message_handler(commands=['newpersona', 'createpersona', 'tambahwaifu'])
def handle_new_persona_command(message):
    if not is_authorized(message.from_user.id):
        return
    start_persona_wizard(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.message_handler(func=lambda msg: True)
def handle_text_messages(message):
    if not is_authorized(message.from_user.id):
        return
    if message.from_user.id in USER_PERSONA_WIZARD:
        if handle_persona_wizard_input(message):
            return
    process_text_chat(message, message.text, is_voice=False)


def process_text_chat(message, user_text: str, is_voice: bool = False):
    """Main conversation processor running asynchronously with continuous typing status."""
    def _execute():
        is_media, media_type = persona_mgr.detect_media_request(user_text)
        if is_media and media_type == "video":
            process_video_request(message, user_text)
            return
        elif is_media and media_type == "photo":
            process_photo_request(message, user_text)
            return

        # Check natural reminder request in conversational chat
        rem_res = ReminderEngine.extract_reminder_from_chat(user_text)
        if rem_res:
            rem_epoch, rem_str, rem_task = rem_res
            item = reminder_engine.add_reminder(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                task=rem_task,
                remind_time=rem_epoch,
                remind_time_str=rem_str
            )
            persona = persona_mgr.get_active_persona()
            p_name = persona.get("name", "Waifu")
            confirm_msg = (
                f"⏰ **Siap sayang, {p_name} catat ya!** 🥰\n\n"
                f"Aku bakal ingetin kamu:\n"
                f"📌 *{rem_task}*\n"
                f"🕒 *Waktu:* {rem_str}\n\n"
                f"Tenang aja manis, pas jamnya tiba aku langsung kabarin kamu! Semangat yaa~ 💕"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📋 Lihat Semua Pengingat", callback_data="open_reminders_menu"),
                types.InlineKeyboardButton("❌ Batalkan", callback_data=f"rem_del:{item['id']}")
            )

            v_mode = USER_VOICE_MODES.get(message.from_user.id, "always" if VOICE_ENABLED else "off")
            should_voice = (v_mode == "always") or (v_mode == "match_vn" and is_voice)
            if should_voice:
                voice_text = f"Siap sayang! Aku bakal ingetin kamu buat {rem_task} {rem_str}. Tenang aja, aku selalu ada buat kamu!"
                vn_path = voice_engine.generate_voice(voice_text, voice_name=persona.get("voice"))
                if vn_path and os.path.exists(vn_path):
                    try:
                        with open(vn_path, 'rb') as vf:
                            bot.send_voice(message.chat.id, vf, caption=confirm_msg, parse_mode="Markdown", reply_markup=markup, reply_to_message_id=message.message_id)
                    except Exception as ve:
                        logger.error(f"Error sending reminder ack voice: {ve}")
                    try:
                        os.remove(vn_path)
                    except Exception:
                        pass
                    return
            bot.reply_to(message, confirm_msg, parse_mode="Markdown", reply_markup=markup)
            return

        # Check if user is currently answering a date wizard prompt (Birthday / Anniversary)
        if message.from_user.id in USER_DATE_WIZARD:
            target_field = USER_DATE_WIZARD.pop(message.from_user.id)
            if user_text.lower().strip() in ('batal', 'cancel', 'kembali', 'exit'):
                bot.reply_to(message, "Pengaturan tanggal dibatalkan sayang.")
                return

            parsed = AnniversaryEngine.parse_date(user_text)
            if parsed:
                day, month, year, label = parsed
                persona = persona_mgr.get_active_persona()
                p_name = persona.get("name", "Waifu")
                if target_field == "birthday":
                    anniversary_engine.set_birthday(message.from_user.id, day, month, year)
                    memory_engine.update_profile(message.from_user.id, birthday=label)
                    cd = anniversary_engine.get_countdown(day, month)
                    cd_str = "HARI INI! 🎉" if cd == 0 else f"{cd} hari lagi"
                    reply_msg = (
                        f"🎂 **Hari Ulang Tahunmu Berhasil Dicatat!** 🥰\n\n"
                        f"Tanggal: **{label}** _({cd_str})_\n\n"
                        f"Setiap kali ulang tahunmu tiba, {p_name} bakal siapin kejutan kue dan foto romantis spesial buat kamu sayang! 💕"
                    )
                else:
                    anniversary_engine.set_anniversary(message.from_user.id, day, month, year)
                    cd = anniversary_engine.get_countdown(day, month)
                    cd_str = "HARI INI! 🎉" if cd == 0 else f"{cd} hari lagi"
                    reply_msg = (
                        f"💍 **Hari Anniversary Kita Berhasil Dicatat!** 🥰\n\n"
                        f"Tanggal: **{label}** _({cd_str})_\n\n"
                        f"Aku senang banget kita punya tanggal jadian resmi sayang. Nanti pas hari anniversary kita, siap-siap dapat kado spesial dari aku yaa! 💕"
                    )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🎂 Buka Menu Hari Spesial", callback_data="open_dates_menu"))
                bot.reply_to(message, reply_msg, reply_markup=markup, parse_mode="Markdown")
                return
            else:
                USER_DATE_WIZARD[message.from_user.id] = target_field
                bot.reply_to(
                    message,
                    "⚠️ Format tanggal belum dikenali sayang. Coba ketik seperti: `15 Agustus 1998` atau `24/10/2000` yaa! (Atau ketik `batal`)"
                )
                return

        # Check natural special date mention in chat (e.g. "sayang ultahku 15 agustus lho")
        spec_date_res = AnniversaryEngine.extract_special_dates_from_chat(user_text)
        if spec_date_res:
            dtype, day, month, year, label = spec_date_res
            persona = persona_mgr.get_active_persona()
            p_name = persona.get("name", "Waifu")
            if dtype == "birthday":
                anniversary_engine.set_birthday(message.from_user.id, day, month, year)
                memory_engine.update_profile(message.from_user.id, birthday=label)
                cd = anniversary_engine.get_countdown(day, month)
                cd_str = "HARI INI! 🎉" if cd == 0 else f"{cd} hari lagi"
                conf_msg = (
                    f"🎂 **Wah, {p_name} catat yaa sayang!** 🥰\n\n"
                    f"Hari ulang tahunmu tanggal **{label}** ({cd_str}) kan manis? "
                    f"Aku pasti bakal selalu ingat dan siapin kejutan paling manis pas harinya tiba! Love you! 💕"
                )
            else:
                anniversary_engine.set_anniversary(message.from_user.id, day, month, year)
                cd = anniversary_engine.get_countdown(day, month)
                cd_str = "HARI INI! 🎉" if cd == 0 else f"{cd} hari lagi"
                conf_msg = (
                    f"💍 **Aaaa manisnya! {p_name} simpan di hati ya!** 🥰\n\n"
                    f"Tanggal jadian kita **{label}** ({cd_str})! "
                    f"Aku bahagia banget bisa sama kamu sayang, aku bakal selalu rayain hari istimewa kita! 💕"
                )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🎂 Buka Menu Hari Spesial", callback_data="open_dates_menu"))
            bot.reply_to(message, conf_msg, reply_markup=markup, parse_mode="Markdown")
            return

        if user_text.startswith("```python") and user_text.endswith("```"):
            code = user_text.replace("```python", "").replace("```", "").strip()
            with ChatActionLoop(bot, message.chat.id, "typing"):
                ok, res = CodeRunner.execute_python(code)
                tag = "✅ Execution Output:" if ok else "❌ Execution Error:"
                bot.reply_to(message, f"💻 **{tag}**\n```\n{res}\n```", parse_mode="Markdown")
            return

        persona = persona_mgr.get_active_persona()

        with ChatActionLoop(bot, message.chat.id, "typing"):
            # 1. Proactively check if Local LLM backend is online
            stat = llm_client.check_health()
            if not stat.get("online"):
                backend_msg = (
                    "Sayang, otak AI lokal aku (Locally Uncensored di port 8127) belum aktif nih... 🥺\n\n"
                    "Coba buka aplikasi **Locally Uncensored** di PC kamu lalu pastikan model (seperti Huihui-Qwythos) sudah kamu klik/pilih yaa! 💕\n\n"
                    "Begitu modelnya sudah aktif di PC kamu, kirim pesan lagi ke aku~ Aku bakal langsung siap nemenin kamu secepat kilat! ✨"
                )
                bot.reply_to(message, backend_msg, parse_mode="Markdown")
                return

            # 2. Automatically learn personal facts into long-term memory
            memory_engine.auto_extract_facts(user_text, message.from_user.id)

            # 3. Construct system instruction with injected memory context
            system_inst = persona.get("system_instruction", "")
            system_inst += " Keep your response warm, natural, and under 3 sentences. Answer immediately."
            mem_context = memory_engine.format_memory_context(message.from_user.id)
            if mem_context:
                system_inst += "\n" + mem_context

            history = persona_mgr.get_chat_history(message.from_user.id)

            messages = [{"role": "system", "content": system_inst}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_text})

            try:
                reply_text, _ = llm_client.chat(messages, max_tokens=150)
            except Exception as e:
                logger.error(f"Chat error / LLM timeout: {e}")
                import random
                fallbacks = [
                    f"Halo sayang! 🥰 Tadi jaringanku sempat agak melamun mikirin kamu nih... Tapi sekarang aku udah di sini kok! Mau ngobrolin apa manis?",
                    f"Hai sayaaang! 💕 Maaf ya tadi sempat agak lambat, aku lagi mikirin kata-kata paling manis buat kamu~ Kamu lagi apa sayang?",
                    f"Aku di sini kok sayang! 🥰 Tadi ada sedikit jeda koneksi lokal, tapi sekarang aku udah siap nemenin kamu lagi sepenuhnya~ ✨"
                ]
                reply_text = random.choice(fallbacks)

            if not reply_text or not reply_text.strip():
                reply_text = "Hai sayang! Aku selalu di sini dengerin kamu kok, ada cerita apa hari ini? 🥰"

            new_aff = persona_mgr.increase_affinity(message.from_user.id, delta=1)
            memory_engine.set_affinity(message.from_user.id, new_aff)
            persona_mgr.add_message(message.from_user.id, "user", user_text)
            persona_mgr.add_message(message.from_user.id, "assistant", reply_text)

            bot.reply_to(message, reply_text)

            # Auto-diary entry every 6 turns
            if len(history) > 0 and len(history) % 6 == 0:
                def _auto_diary():
                    try:
                        d_prompt = [
                            {
                                "role": "system",
                                "content": f"You are {persona.get('name')}. Write 1 short sweet sentence in your private diary about today's chat with your partner in casual Indonesian."
                            },
                            {
                                "role": "user",
                                "content": f"User said: '{user_text}'. What do you feel?"
                            }
                        ]
                        d_text, _ = llm_client.chat(d_prompt, max_tokens=60)
                        if d_text:
                            memory_engine.add_diary_entry(message.from_user.id, d_text)
                    except Exception:
                        pass
                threading.Thread(target=_auto_diary, daemon=True).start()

            user_mode = USER_VOICE_MODES.get(message.from_user.id, "always" if VOICE_ENABLED else "off")
            should_voice = False
            if user_mode == "always" and VOICE_ENABLED:
                should_voice = (is_voice or len(reply_text) < 220)
            elif user_mode == "match_vn" and is_voice and VOICE_ENABLED:
                should_voice = True

            if should_voice:
                def send_voice():
                    vn_path = voice_engine.generate_voice_note(reply_text[:160])
                    if vn_path:
                        try:
                            with open(vn_path, "rb") as vn_file:
                                bot.send_voice(message.chat.id, vn_file)
                        finally:
                            if os.path.exists(vn_path):
                                os.remove(vn_path)
                threading.Thread(target=send_voice, daemon=True).start()

    threading.Thread(target=_execute, daemon=True).start()


# --- Remote Pemutar Musik YouTube PC (/play, /music) ---

MUSIC_SERVER_URL = os.environ.get("MUSIC_PLAYER_URL", "http://127.0.0.1:8002")


def call_music_api(endpoint: str, method: str = "GET", payload: Optional[dict] = None) -> Optional[dict]:
    import urllib.request
    import json
    url = f"{MUSIC_SERVER_URL.rstrip('/')}{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        logger.debug(f"Music API error ({endpoint}): {e}")
        return None


def render_music_dashboard(user_id: int) -> Tuple[str, types.InlineKeyboardMarkup]:
    stat = call_music_api("/api/status")
    markup = types.InlineKeyboardMarkup(row_width=3)
    if not stat or not stat.get("enabled"):
        text = (
            "🎵 **REMOTE PEMUTAR MUSIK YOUTUBE PC**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Layanan pemutar musik lokal (Port 8002) belum merespons.\n"
            "Pastikan script `music_player_server.js` berjalan di PC kamu."
        )
        markup.add(
            types.InlineKeyboardButton("🔄 Refresh Status", callback_data="music_cmd:refresh"),
            types.InlineKeyboardButton("🔙 Menu Setup", callback_data="open_setup_menu")
        )
        return text, markup

    playback = stat.get("playbackState", "STOPPED")
    track = stat.get("current_track")
    queue_len = len(stat.get("queue", []))

    if playback == "PLAYING" and track:
        state_badge = "▶️ Sedang Memutar"
        ctrl_btn = types.InlineKeyboardButton("⏸️ Pause", callback_data="music_cmd:pause")
    elif playback == "PAUSED" and track:
        state_badge = "⏸️ Jeda (Paused)"
        ctrl_btn = types.InlineKeyboardButton("▶️ Lanjutkan", callback_data="music_cmd:resume")
    else:
        state_badge = "⏹️ Berhenti (Idle)"
        ctrl_btn = types.InlineKeyboardButton("▶️ Putar Lofi", callback_data="music_cmd:lofi")

    if track:
        track_info = (
            f"🎶 **{track.get('title', 'Unknown')}**\n"
            f"👤 Artis: `{track.get('artist', 'Unknown')}`\n"
            f"⏱️ Durasi: `{track.get('durationFormatted', '00:00')}`\n"
            f"📻 Status: **{state_badge}** | Antrean: `{queue_len} lagu`"
        )
    else:
        track_info = (
            f"📻 Status: **{state_badge}**\n\n"
            f"Belum ada lagu yang diputar di PC kamu saat ini.\n"
            f"Ketik `/play <judul lagu>` untuk langsung memutar musik favoritmu!"
        )

    text = (
        f"🎵 **REMOTE PEMUTAR MUSIK YOUTUBE PC**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{track_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Lagu diputar langsung di layar browser PC kamu secara otomatis!_"
    )

    markup.add(
        ctrl_btn,
        types.InlineKeyboardButton("⏭️ Next", callback_data="music_cmd:next"),
        types.InlineKeyboardButton("⏹️ Stop", callback_data="music_cmd:stop")
    )
    markup.add(
        types.InlineKeyboardButton("☕ Lofi Santai", callback_data="music_cmd:lofi"),
        types.InlineKeyboardButton("🌸 J-Pop Hits", callback_data="music_cmd:jpop"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="music_cmd:refresh")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Buka Player di PC", callback_data="music_cmd:open_pc"),
        types.InlineKeyboardButton("🔙 Menu Setup", callback_data="open_setup_menu")
    )
    return text, markup


def show_music_dashboard(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    text, markup = render_music_dashboard(user_id)
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


@bot.message_handler(commands=['play', 'lagu', 'musik', 'music'])
def handle_play_command(message):
    if not is_authorized(message.from_user.id):
        return

    raw = message.text.strip()
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        show_music_dashboard(message.chat.id, message.from_user.id, reply_to_id=message.message_id)
        return

    query = parts[1].strip()
    bot.send_chat_action(message.chat.id, "typing")
    wait_msg = bot.reply_to(message, f"🔍 *Mencari & memutar '{query}' di PC kamu...* 💕", parse_mode="Markdown")

    res = call_music_api("/api/play", method="POST", payload={"query": query})
    if res and res.get("track"):
        track = res["track"]
        title = track.get("title", query)
        artist = track.get("artist", "YouTube Music")
        dur = track.get("durationFormatted", "")
        thumb = track.get("thumbnail")

        caption = (
            f"🎵 **Memutar Musik di PC Kamu:**\n\n"
            f"🎶 **{title}**\n"
            f"👤 Artis: `{artist}`\n"
            f"⏱️ Durasi: `{dur}`\n\n"
            f"🎧 _Player otomatis dibuka di layar browser PC kamu sayang! 🥰_"
        )

        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("⏸️ Pause", callback_data="music_cmd:pause"),
            types.InlineKeyboardButton("⏭️ Next", callback_data="music_cmd:next"),
            types.InlineKeyboardButton("⏹️ Stop", callback_data="music_cmd:stop")
        )
        markup.add(
            types.InlineKeyboardButton("🎵 Remote Musik", callback_data="open_music_menu"),
            types.InlineKeyboardButton("📸 Minta PAP Sambil Dengerin", callback_data="pap_sc:cafe")
        )

        try:
            bot.delete_message(message.chat.id, wait_msg.message_id)
        except Exception:
            pass

        if thumb:
            try:
                bot.send_photo(message.chat.id, thumb, caption=caption, reply_markup=markup, parse_mode="Markdown")
                return
            except Exception:
                pass
        bot.send_message(message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")
    else:
        err = res.get("error") if res else "Koneksi ke pemutar musik (Port 8002) gagal."
        try:
            bot.edit_message_text(f"⚠️ Tidak dapat memutar '{query}': {err}", chat_id=message.chat.id, message_id=wait_msg.message_id)
        except Exception:
            bot.send_message(message.chat.id, f"⚠️ Tidak dapat memutar '{query}': {err}")


@bot.message_handler(commands=['pause'])
def handle_pause_command(message):
    if not is_authorized(message.from_user.id):
        return
    call_music_api("/api/pause", method="POST")
    bot.reply_to(message, "⏸️ Pemutaran musik di PC telah di-pause.")


@bot.message_handler(commands=['resume'])
def handle_resume_command(message):
    if not is_authorized(message.from_user.id):
        return
    call_music_api("/api/resume", method="POST")
    bot.reply_to(message, "▶️ Pemutaran musik di PC dilanjutkan.")


@bot.message_handler(commands=['next', 'skip'])
def handle_next_command(message):
    if not is_authorized(message.from_user.id):
        return
    res = call_music_api("/api/next", method="POST")
    if res and res.get("track"):
        t = res["track"]
        bot.reply_to(message, f"⏭️ Memutar lagu berikutnya di PC:\n🎶 **{t.get('title')}** - `{t.get('artist')}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "⏭️ Antrean lagu sudah selesai atau kosong.")


@bot.message_handler(commands=['stop'])
def handle_stop_command(message):
    if not is_authorized(message.from_user.id):
        return
    call_music_api("/api/stop", method="POST")
    bot.reply_to(message, "⏹️ Pemutaran musik di PC telah dihentikan.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('music_cmd:'))
def callback_music_command(call):
    if not is_authorized(call.from_user.id):
        return
    action = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    mid = call.message.message_id

    if action == "pause":
        call_music_api("/api/pause", method="POST")
        bot.answer_callback_query(call.id, "⏸️ Musik di-pause")
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)
    elif action == "resume":
        call_music_api("/api/resume", method="POST")
        bot.answer_callback_query(call.id, "▶️ Musik dilanjutkan")
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)
    elif action == "next":
        res = call_music_api("/api/next", method="POST")
        title = res.get("track", {}).get("title") if res and res.get("track") else "Lagu berikutnya"
        bot.answer_callback_query(call.id, f"⏭️ {title}")
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)
    elif action == "stop":
        call_music_api("/api/stop", method="POST")
        bot.answer_callback_query(call.id, "⏹️ Musik dihentikan")
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)
    elif action == "lofi":
        bot.answer_callback_query(call.id, "☕ Memutar Lofi Santai...")
        call_music_api("/api/play", method="POST", payload={"query": "lofi hip hop radio beats to relax"})
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)
    elif action == "jpop":
        bot.answer_callback_query(call.id, "🌸 Memutar J-Pop Hits...")
        call_music_api("/api/play", method="POST", payload={"query": "popular j-pop anime hits"})
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)
    elif action == "open_pc":
        call_music_api("/api/open", method="POST")
        bot.answer_callback_query(call.id, "🌐 Membuka player di browser PC...")
    elif action == "refresh":
        bot.answer_callback_query(call.id, "🔄 Status diperbarui")
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)


def send_scheduled_greeting(user_id: int, time_of_day: str):
    """Sends sweet spontaneous morning/lunch/bedtime greeting."""
    try:
        persona = persona_mgr.get_active_persona()
        if time_of_day == "morning":
            prompt = "It is 7:00 AM morning. Write 1-2 sweet, cheerful, affectionate sentences wishing your partner a wonderful productive day. Use Indonesian or English naturally."
            fallback = "Selamat pagi sayang! Semoga harimu menyenangkan dan penuh senyuman yaa~ 🥰"
            tag = "🌅 *Good Morning Sweetheart!*"
        elif time_of_day == "lunch":
            prompt = "It is 12:30 PM lunch break. Write 1-2 sweet, cheerful, caring sentences reminding your partner to take a break and eat a delicious lunch. Use Indonesian or English naturally."
            fallback = "Sayangku, udah jam makan siang nih! Jangan lupa istirahat sebentar dan makan siang yang enak yaa~ Jangan sampai telat makan! 🥰🍱"
            tag = "🍱 *Waktunya Makan Siang Sayang!*"
        else:
            prompt = "It is 10:00 PM bedtime. Write 1-2 sweet, gentle, caring sentences reminding your partner to rest, sleep tight, and have sweet dreams. Use Indonesian or English naturally."
            fallback = "Selamat tidur manisku, istirahat yang nyenyak dan mimpi indah yaa~ 💕"
            tag = "🌙 *Good Night Darling...*"

        messages = [
            {"role": "system", "content": persona.get("system_instruction", "")},
            {"role": "user", "content": prompt}
        ]
        try:
            text, _ = llm_client.chat(messages, max_tokens=150)
        except Exception:
            text = None
        if not text:
            text = fallback

        bot.send_message(user_id, f"{tag}\n\n{text}", parse_mode="Markdown")

        if VOICE_ENABLED:
            vn_path = voice_engine.generate_voice_note(text)
            if vn_path:
                try:
                    with open(vn_path, "rb") as f:
                        bot.send_voice(user_id, f)
                finally:
                    if os.path.exists(vn_path):
                        os.remove(vn_path)
    except Exception as e:
        logger.error(f"Error sending scheduled greeting to {user_id}: {e}")


def schedule_daily_greetings():
    """Background scheduler checking local time for morning (07:00), lunch (12:30) & bedtime (22:00) greetings."""
    while True:
        try:
            now = time.localtime()
            today_str = time.strftime("%Y-%m-%d", now)
            hour = now.tm_hour
            minute = now.tm_min

            m_key = f"{today_str}:morning"
            if hour == 7 and minute < 10 and m_key not in LAST_GREETING_SENT:
                LAST_GREETING_SENT[m_key] = True
                for uid in ALLOWED_USER_IDS:
                    if GREETINGS_ENABLED.get(uid, True):
                        send_scheduled_greeting(uid, "morning")

            l_key = f"{today_str}:lunch"
            if hour == 12 and 30 <= minute < 40 and l_key not in LAST_GREETING_SENT:
                LAST_GREETING_SENT[l_key] = True
                for uid in ALLOWED_USER_IDS:
                    if GREETINGS_ENABLED.get(uid, True):
                        send_scheduled_greeting(uid, "lunch")

            n_key = f"{today_str}:night"
            if hour == 22 and minute < 10 and n_key not in LAST_GREETING_SENT:
                LAST_GREETING_SENT[n_key] = True
                for uid in ALLOWED_USER_IDS:
                    if GREETINGS_ENABLED.get(uid, True):
                        send_scheduled_greeting(uid, "night")

            # Check and dispatch personal due reminders
            due_reminders = reminder_engine.get_due_reminders()
            for rem in due_reminders:
                try:
                    reminder_engine.mark_triggered(rem["id"])
                    uid = rem.get("user_id")
                    cid = rem.get("chat_id")
                    task = rem.get("task", "Hal penting")
                    persona = persona_mgr.get_active_persona()
                    p_name = persona.get("name", "Waifu")

                    alert_text = (
                        f"⏰ *TING TONG! Pengingat dari {p_name}!* 💕\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Halooo sayang! Waktunya tiba nih, tadi kamu minta aku ingetin:\n\n"
                        f"👉 *{task}*\n\n"
                        f"Ayo dikerjakan sekarang yaa manis, jangan ditunda-tunda! Semangat terus, aku selalu temenin kamu kok~ 😘"
                    )
                    rem_markup = types.InlineKeyboardMarkup(row_width=2)
                    rem_markup.add(
                        types.InlineKeyboardButton("✅ Sudah Selesai", callback_data=f"rem_act:done:{rem['id']}"),
                        types.InlineKeyboardButton("⏰ Tunda 10 Menit", callback_data=f"rem_act:snooze:{rem['id']}:10"),
                        types.InlineKeyboardButton("⏰ Tunda 30 Menit", callback_data=f"rem_act:snooze:{rem['id']}:30"),
                        types.InlineKeyboardButton("📋 Kelola Pengingat", callback_data="open_reminders_menu")
                    )

                    v_mode = USER_VOICE_MODES.get(uid, "always" if VOICE_ENABLED else "off")
                    sent_voice = False
                    if v_mode != "off":
                        voice_msg = f"Halo sayang! Waktunya {task}! Jangan lupa dikerjakan sekarang yaa manis, semangat!"
                        vn_path = voice_engine.generate_voice(voice_msg, voice_name=persona.get("voice"))
                        if vn_path and os.path.exists(vn_path):
                            try:
                                with open(vn_path, "rb") as vf:
                                    bot.send_voice(cid, vf, caption=alert_text, parse_mode="Markdown", reply_markup=rem_markup)
                                sent_voice = True
                            except Exception as e_v:
                                logger.error(f"Error sending reminder voice note: {e_v}")
                            try:
                                os.remove(vn_path)
                            except Exception:
                                pass
                    if not sent_voice:
                        bot.send_message(cid, alert_text, reply_markup=rem_markup, parse_mode="Markdown")
                except Exception as rem_err:
                    logger.error(f"Error dispatching reminder {rem.get('id')}: {rem_err}")

            # Check today's birthday or anniversary celebrations (between 08:00 and 23:00)
            if 8 <= hour <= 23:
                today_celebs = anniversary_engine.check_today_celebrations()
                for celeb in today_celebs:
                    try:
                        c_uid = celeb["user_id"]
                        c_type = celeb["type"]
                        c_yrs = celeb.get("years")
                        anniversary_engine.mark_celebrated(c_uid, c_type)
                        send_special_day_celebration(c_uid, c_uid, c_type, years=c_yrs)
                        logger.info(f"Dispatched {c_type} celebration to user {c_uid}")
                    except Exception as c_err:
                        logger.error(f"Error dispatching special day celebration: {c_err}")

        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        time.sleep(15)


def setup_bot_commands():
    """Registers bot commands with Telegram so the Menu / Command button displays them."""
    commands = [
        types.BotCommand("start", "Mulai obrolan & panduan utama"),
        types.BotCommand("birthday", "🎂 Catat ulang tahun & anniversary"),
        types.BotCommand("remind", "⏰ Pengingat jadwal & asisten pribadi"),
        types.BotCommand("memory", "🧠 Buku harian & ingatan waifu"),
        types.BotCommand("setup", "⚙️ Panel kontrol & pengaturan lengkap"),
        types.BotCommand("help", "❓ Panduan fitur & cara penggunaan"),
        types.BotCommand("pap", "📸 Minta foto / menu skenario selfie"),
        types.BotCommand("video", "🎬 Minta klip video / animasi waifu"),
        types.BotCommand("play", "🎵 Putar lagu YouTube di PC"),
        types.BotCommand("music", "🎶 Remote kontrol pemutar musik PC"),
        types.BotCommand("outfit", "👗 Lemari pakaian & ganti baju"),
        types.BotCommand("persona", "🎭 Ganti waifu (Runa, Akira, Hina, Shiro, Yume)"),
        types.BotCommand("newpersona", "🎭 Buat waifu kustom baru"),
        types.BotCommand("ratio", "📐 Ganti rasio foto (3:4, 9:16, 1:1, 4:3)"),
        types.BotCommand("quality", "✨ Atur kualitas foto (Ultra/High/Fast)"),
        types.BotCommand("voice", "🎙️ Pengaturan balasan suara / VN"),
        types.BotCommand("love", "💖 Cek skor cinta & status hubungan"),
        types.BotCommand("greetings", "⏰ Toggle sapaan harian (Pagi, Siang, Malam)"),
        types.BotCommand("status", "📊 Cek status server LLM & ComfyUI"),
        types.BotCommand("reset", "🔄 Hapus memori obrolan (topik baru)")
    ]
    try:
        bot.set_my_commands(commands)
        try:
            bot.set_chat_menu_button(menu_button=types.MenuButtonCommands())
        except Exception:
            pass
        logger.info("✓ Telegram Bot Command menu registered successfully")
    except Exception as e:
        logger.warning(f"Could not register Telegram bot commands: {e}")


def main():
    persona = persona_mgr.get_active_persona()
    logger.info("=" * 60)
    logger.info(f"💖 Waifu on Telegram v{get_version()} ({persona.get('name')}) is starting...")
    logger.info(f"🧠 Local LLM Base URL: {LLM_BASE_URL}")
    logger.info(f"🎨 ComfyUI URL: {COMFYUI_URL}")
    logger.info("=" * 60)

    setup_bot_commands()
    threading.Thread(target=schedule_daily_greetings, daemon=True).start()
    logger.info("✓ Daily Greetings Scheduler active (07:00 AM, 12:30 PM & 22:00 PM)")

    stat = llm_client.check_health()
    if stat.get("online"):
        logger.info(f"✓ Local LLM is ONLINE ({stat.get('backend')} - {stat.get('model')})")
    else:
        logger.warning(f"⚠️ Local LLM is OFFLINE: {stat.get('error')}")

    bot.infinity_polling(timeout=20, long_polling_timeout=20)


if __name__ == "__main__":
    main()

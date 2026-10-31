from proactive_chat_engine import proactive_engine
import student_schedule
import re
import os
import sys
import logging
import threading
import time
import datetime
import platform
import subprocess
from typing import Optional, Dict, Any, Tuple, List

if sys.platform == "win32":
    try:
        import ctypes
        # Suppress Windows modal crash / bad image error dialogs (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    except Exception:
        pass

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
import asset_manager
from health_engine import HealthEngine
from idle_engine import IdleEngine
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
    return "1.4.0"


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

bot = telebot.TeleBot(BOT_TOKEN, num_threads=8)

# Configure Telegram API timeouts for fast, resilient uploads
from telebot import apihelper
apihelper.READ_TIMEOUT = 120
apihelper.CONNECT_TIMEOUT = 30

# Initialize engines
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:5001/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "kobold")
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
MEDIA_FALLBACK = os.environ.get("MEDIA_FALLBACK_CLOUD", "false").lower() in ("true", "1", "yes")
VOICE_ENABLED = os.environ.get("VOICE_REPLY_ENABLED", "true").lower() in ("true", "1", "yes")
VOICE_NAME = os.environ.get("VOICE_NAME", "en-US-AnaNeural")
DEFAULT_PERSONA = os.environ.get("DEFAULT_PERSONA", "runa")

llm_client = LocallyUncensoredClient(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
persona_mgr = PersonaManager(active_key=DEFAULT_PERSONA)
media_engine = MediaEngine(comfyui_url=COMFYUI_URL, allow_cloud_fallback=MEDIA_FALLBACK)
memory_engine = MemoryEngine()
reminder_engine = ReminderEngine()
anniversary_engine = AnniversaryEngine()
HEALTH_CHECK_INTERVAL = int(os.environ.get("HEALTH_CHECK_INTERVAL", "30"))
HEALTH_CHECK_ENABLED = os.environ.get("HEALTH_CHECK_ENABLED", "true").lower() in ("true", "1", "yes")
STARTUP_NOTIFICATION_ENABLED = os.environ.get("STARTUP_NOTIFICATION_ENABLED", "true").lower() in ("true", "1", "yes")
SELF_HEALING_ENABLED = os.environ.get("SELF_HEALING_ENABLED", "true").lower() in ("true", "1", "yes")
health_engine = HealthEngine(
    llm_client=llm_client,
    media_engine=media_engine,
    check_interval=HEALTH_CHECK_INTERVAL,
    enabled=HEALTH_CHECK_ENABLED,
    self_healing_enabled=SELF_HEALING_ENABLED
)
SMART_IDLE_ENABLED = os.environ.get("SMART_IDLE_ENABLED", "true").lower() in ("true", "1", "yes")
IDLE_TIMEOUT_MINUTES = int(os.environ.get("IDLE_TIMEOUT_MINUTES", "10"))
COMFYUI_ON_DEMAND = os.environ.get("COMFYUI_ON_DEMAND", "true").lower() in ("true", "1", "yes")

idle_engine = IdleEngine(
    health_engine=health_engine,
    project_root=PROJECT_ROOT,
    enabled=SMART_IDLE_ENABLED,
    idle_timeout_minutes=IDLE_TIMEOUT_MINUTES,
    comfyui_on_demand=COMFYUI_ON_DEMAND
)
health_engine.idle_engine = idle_engine
voice_engine = VoiceEngine(
    voice_name=VOICE_NAME,
    groq_key=os.environ.get("GROQ_API_KEY"),
    openai_key=os.environ.get("OPENAI_API_KEY"),
    llm_client=llm_client
)

USER_VOICE_MODES: dict = {}      # user_id -> 'always' | 'match_vn' | 'off'
GREETINGS_ENABLED: dict = {}     # user_id -> bool
LAST_GREETING_SENT: dict = {}    # "YYYY-MM-DD:morning" -> True
USER_RATIOS: dict = {}           # user_id -> '3:4' | '9:16' | '1:1' | '4:3'
USER_QUALITIES: dict = {}        # user_id -> 'high' | 'ultra' | 'fast'
USER_DATE_WIZARD: dict = {}       # user_id -> 'birthday' | 'anniversary'
BOT_LANGUAGE = os.environ.get("BOT_LANGUAGE", "id")
AWAITING_CUSTOM_LANG: dict = {}      # user_id -> bool


# --- Telegram Safe Messaging Helpers ---

def safe_reply_to(message, text, reply_markup=None, parse_mode="Markdown"):
    """
    Safely replies to a message with automatic Markdown fallback to plain text
    if Telegram API rejects parsing entities (400 Bad Request).
    """
    try:
        return bot.reply_to(message, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"safe_reply_to failed with {parse_mode=}: {e}. Retrying as plain text.")
        try:
            clean_text = text.replace("*", "").replace("_", "").replace("`", "")
            return bot.reply_to(message, clean_text, reply_markup=reply_markup)
        except Exception as e2:
            logger.error(f"Fatal error in safe_reply_to: {e2}")
            return None


def safe_send_message(chat_id: int, text: str, reply_markup=None, parse_mode="Markdown"):
    """
    Safely sends a message to chat_id with automatic Markdown fallback to plain text.
    """
    try:
        return bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"safe_send_message failed with {parse_mode=}: {e}. Retrying as plain text.")
        try:
            clean_text = text.replace("*", "").replace("_", "").replace("`", "")
            return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
        except Exception as e2:
            logger.error(f"Fatal error in safe_send_message: {e2}")
            return None


def safe_edit_message_text(text: str, chat_id: int, message_id: int, reply_markup=None, parse_mode="Markdown"):
    """
    Safely edits a message with automatic Markdown fallback to plain text
    if Telegram API rejects parsing entities (400 Bad Request).
    """
    try:
        return bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"safe_edit_message_text failed with {parse_mode=}: {e}. Retrying as plain text.")
        try:
            clean_text = text.replace("*", "").replace("_", "").replace("`", "")
            return bot.edit_message_text(clean_text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
        except Exception as e2:
            logger.error(f"Fatal error in safe_edit_message_text: {e2}")
            return None


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
    if choice == "kobold" or choice == "auto":
        new_base = "http://127.0.0.1:5001/v1"
        new_model = "default"
        label = "KoboldCPP (Auto-start & Loaded)"
    elif choice == "locally_uncensored":
        new_base = "http://127.0.0.1:8127/v1"
        new_model = "default"
        label = "Locally Uncensored (Port 8127)"
    elif choice == "ollama":
        new_base = "http://127.0.0.1:11434/v1"
        new_model = "default"
        label = "Ollama (Port 11434)"
    elif choice.isdigit() and int(choice) < len(detected_llms):
        source, mname, mpath = detected_llms[int(choice)]
        if source == "KoboldCPP":
            new_base = "http://127.0.0.1:5001/v1"
        elif source == "Locally Uncensored":
            new_base = "http://127.0.0.1:8127/v1"
        elif source == "Ollama":
            new_base = "http://127.0.0.1:11434/v1"
        else:
            new_base = "http://127.0.0.1:5001/v1"
        new_model = mname
        label = f"{mname} ({source})"
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
        os.environ["MEDIA_FALLBACK_CLOUD"] = "false"
        media_engine.comfyui_url = "http://127.0.0.1:8188"
        media_engine.allow_cloud_fallback = False
        update_env_variable("COMFYUI_CHECKPOINT", "")
        update_env_variable("COMFYUI_URL", "http://127.0.0.1:8188")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "false")
        return "Auto (ComfyUI Active)"
    elif choice == "meinamix":
        ckpt_name = "meinamix_v12Final.safetensors"
        os.environ["COMFYUI_CHECKPOINT"] = ckpt_name
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"
        os.environ["MEDIA_FALLBACK_CLOUD"] = "false"
        media_engine.comfyui_url = "http://127.0.0.1:8188"
        media_engine.allow_cloud_fallback = False
        update_env_variable("COMFYUI_CHECKPOINT", ckpt_name)
        update_env_variable("COMFYUI_URL", "http://127.0.0.1:8188")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "false")
        return "MeinaMix v12 (SD 1.5)"
    elif choice == "aom3":
        ckpt_name = "AOM3A1B_orangemixs.safetensors"
        os.environ["COMFYUI_CHECKPOINT"] = ckpt_name
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"
        os.environ["MEDIA_FALLBACK_CLOUD"] = "false"
        media_engine.comfyui_url = "http://127.0.0.1:8188"
        media_engine.allow_cloud_fallback = False
        update_env_variable("COMFYUI_CHECKPOINT", ckpt_name)
        update_env_variable("COMFYUI_URL", "http://127.0.0.1:8188")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "false")
        return "AbyssOrangeMix3 (AOM3A1B SD 1.5)"
    elif choice == "anything_xl":
        ckpt_name = "AnythingXL_xl.safetensors"
        os.environ["COMFYUI_CHECKPOINT"] = ckpt_name
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"
        os.environ["MEDIA_FALLBACK_CLOUD"] = "false"
        media_engine.comfyui_url = "http://127.0.0.1:8188"
        media_engine.allow_cloud_fallback = False
        update_env_variable("COMFYUI_CHECKPOINT", ckpt_name)
        update_env_variable("COMFYUI_URL", "http://127.0.0.1:8188")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "false")
        return "Anything XL (SDXL 1024px)"
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
        os.environ["MEDIA_FALLBACK_CLOUD"] = "false"
        media_engine.comfyui_url = "http://127.0.0.1:8188"
        media_engine.allow_cloud_fallback = False
        update_env_variable("COMFYUI_CHECKPOINT", ckpt_name)
        update_env_variable("COMFYUI_URL", "http://127.0.0.1:8188")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "false")
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
    v_name = mapping.get(speaker, speaker)
    VOICE_NAME = v_name
    voice_engine.default_voice = v_name
    update_env_variable("VOICE_NAME", v_name)
    return v_name


def apply_language_choice(choice: str, change_voice: bool = False) -> Tuple[str, str]:
    """Applies, normalizes, and persists waifu language choice."""
    global BOT_LANGUAGE
    c = choice.strip()
    low = c.lower()
    default_voice = None

    if low in ("id", "indonesia", "indonesian", "bahasa"):
        norm_key = "id"
        label = "Bahasa Indonesia 🇮🇩"
        default_voice = "id-ID-GadisNeural"
    elif low in ("en", "english"):
        norm_key = "en"
        label = "English 🇬🇧"
        default_voice = "en-US-AnaNeural"
    elif low in ("ja", "jp", "japan", "japanese", "nihongo"):
        norm_key = "ja"
        label = "Japanese (日本語) 🇯🇵"
        default_voice = "ja-JP-NanamiNeural"
    elif low in ("auto", "adaptive"):
        norm_key = "auto"
        label = "Auto-detect (Ikuti Chat) 🌐"
    else:
        norm_key = c.title()
        label = f"{norm_key} ✏️"

    BOT_LANGUAGE = norm_key
    os.environ["BOT_LANGUAGE"] = norm_key
    update_env_variable("BOT_LANGUAGE", norm_key)
    # Only override voice speaker if change_voice is explicitly requested or voice is unconfigured
    if default_voice and (change_voice or not voice_engine.default_voice):
        apply_voice_speaker(default_voice)
    return norm_key, label


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


def get_notification_recipient_ids() -> List[int]:
    """Returns all authorized recipient user IDs for broadcast notifications."""
    recipients = set(ALLOWED_USER_IDS)
    try:
        for s_uid in memory_engine.data.get("profiles", {}).keys():
            try:
                uid_int = int(s_uid)
                if is_authorized(uid_int):
                    recipients.add(uid_int)
            except ValueError:
                pass
    except Exception:
        pass
    return list(recipients)


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



def send_menu_message(chat_id: int, text: str, reply_markup=None, reply_to_id: Optional[int] = None):
    """
    Safely delivers menu messages with automatic resilience:
    1. Attempts sending with Markdown formatting and reply_to_id.
    2. If reply_to_id fails (message deleted/not found), retries without reply_to_id.
    3. If Markdown entity parsing fails (special characters, unescaped markdown), retries as plain text.
    """
    try:
        return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)
    except Exception as e_first:
        logger.warning(f"send_menu_message attempt 1 failed ({e_first}). Retrying resiliently...")

    if reply_to_id:
        try:
            return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception:
            pass

    clean_text = text.replace("**", "").replace("*", "").replace("`", "").replace("_", "")
    try:
        if reply_to_id:
            try:
                return bot.send_message(chat_id, clean_text, reply_markup=reply_markup, reply_to_message_id=reply_to_id)
            except Exception:
                pass
        return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
    except Exception as e_final:
        logger.error(f"send_menu_message failed completely: {e_final}")
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
                f"Senang kamu datang! Aku siap nemenin kamu ngobrol santai, kirim foto selfie, dan nemenin hari-harimu~ ✨"
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
        "• 🎙️ **Voice Note**: Balasan suara jernih (`/voice`).\n"
        "• ⚙️ **Panel Setup**: Atur seluruh konfigurasi bot dari Telegram (`/setup`).\n"
        "• ⏰ **Asisten & Pengingat**: Minta waifu ingetin jadwal lewat chat/voice note (`/remind`)!\n"
        "• ⏰ **Sapaan Otomatis**: Ucapan selamat pagi jam 7, makan siang 12:30 & tidur jam 10 malam (`/greetings`).\n"
        "• 👀 **AI Vision**: Kirimkan foto kamu ke sini, waifu bisa melihat dan meresponsnya.\n\n"
        "📌 **Perintah Cepat:**\n"
        "• `/birthday` - Catat hari ulang tahunmu & tanggal anniversary jadian\n"
        "• `/remind` - Pengingat jadwal dan to-do list\n"
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
        "• `/love` - Cek skor cinta dan level kedekatan\n"
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
    cur_proact = "AKTIF ✅" if proactive_engine.is_enabled(user_id) else "NONAKTIF ❌"
    cur_health = "AKTIF 🟢" if health_engine.enabled else "NONAKTIF ⚪"
    cur_heal = "AKTIF 🟢" if health_engine.self_healing_enabled else "NONAKTIF ⚪"
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
        cur_ckpt = "Auto (ComfyUI Active)"
    elif "anything" in cur_ckpt.lower():
        cur_ckpt = "Anything XL (SDXL 1024px)"
    elif any(k in cur_ckpt.lower() for k in ["aom", "orange"]):
        cur_ckpt = "AbyssOrangeMix3 (AOM3A1B)"
    elif "meina" in cur_ckpt.lower():
        cur_ckpt = "MeinaMix v12 (SD 1.5)"
    elif len(cur_ckpt) > 28:
        cur_ckpt = cur_ckpt[:25] + "..."

    text = (
        f"⚙️ **WAIFU ON TELEGRAM - SETUP & SYSTEM CONTROL** `(v{get_version()})`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Waifu Aktif** : **{persona.get('name')}** _({persona.get('archetype', 'Companion')})_\n"
        f"🌐 **Bahasa**     : `{persona_mgr.get_language_display_name(BOT_LANGUAGE)}`\n"
        f"👗 **Pakaian**    : `{cur_outfit_name}`\n"
        f"🎙️ **Mode Suara** : `{v_labels.get(v_mode, v_mode)}`\n"
        f"🗣️ **Voice TTS**  : `{voice_engine.default_voice}`\n"
        f"🧠 **Model LLM**  : `{cur_llm}`\n"
        f"🎨 **Model Foto** : `{cur_ckpt}`\n"
        f"🎬 **Video Engine**: `{VIDEO_ENGINE_LABELS.get(VIDEO_ENGINE, VIDEO_ENGINE)}`\n"
        f"📐 **Rasio Foto** : `{cur_ar}`\n"
        f"✨ **Kualitas**   : `{cur_q}`\n"
        f"🎵 **Musik PC**   : `Online (Port 8002)`\n"
        f"🧠 **Ingatan**    : `{fact_count} fakta tersimpan`\n"
        f"⏰ **Pengingat**  : `{rem_count} jadwal aktif`\n"
        f"🎂 **Ultah Kamu** : `{b_str}`\n"
        f"🚀 **PC Autorun** : `{cur_auto}`\n"
        f"⏰ **Sapaan Jam** : `{cur_greet}` _(07:00, 12:30 & 22:00)_\n"
        f"💬 **Chat Duluan** : `{cur_proact}` _(Tanya kabar saat kamu sepi)_\n"
        f"🩺 **Health Alert**: `{cur_health}` _(Cek berkala & lapor jika LLM mati)_\n"
        f"🩹 **Self-Healing**: `{cur_heal}` _(Auto-restart saat service mati/crash)_\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Pilih tombol menu di bawah untuk mengubah pengaturan langsung dari Telegram:_"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🧠 Model LLM / Chat", callback_data="cfg_submenu:llm"),
        types.InlineKeyboardButton("🌐 Bahasa / Language", callback_data="cfg_submenu:language"),
        types.InlineKeyboardButton("🎨 Model Foto & ComfyUI", callback_data="cfg_submenu:photo"),
        types.InlineKeyboardButton("🎬 Video Engine (/video)", callback_data="cfg_submenu:video_engine"),
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
        types.InlineKeyboardButton(f"💬 Chat Duluan: {cur_proact}", callback_data="cfg_toggle:proactive"),
        types.InlineKeyboardButton(f"🩺 Health Alert: {cur_health}", callback_data="cfg_toggle:health_check"),
        types.InlineKeyboardButton(f"🩹 Self-Healing: {cur_heal}", callback_data="cfg_toggle:self_healing"),
        types.InlineKeyboardButton("🩹 Jalankan Self-Healing", callback_data="cfg_action:self_heal"),
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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
        fact_lines.append("  _Belum ada catatan khusus. Ceritain tentang kamu di sini ya._")

    diary_lines = []
    if diaries:
        for d in diaries[-2:]:
            diary_lines.append(f"  • *{d['date'][:10]}* ({d.get('mood', '🥰')}): _{d['entry']}_")
    else:
        diary_lines.append(f"  _Hari ini senang bisa nemenin hari-harimu~ 💕_")

    text = (
        f"📖 **BUKU HARIAN & INGATAN {name.upper()}** 💖\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Ini beberapa hal tentang kamu yang aku simpan:\n\n"
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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
                    f"Setiap kali kita ngobrol, hal-hal tentang kamu bakal selalu aku ingat yaa~ ✨",
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
        dialog_snippet = " ".join(clean_turns[-4:]) if clean_turns else "Ngobrol santai bersama"

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
            entry = f"Hari ini seru bisa ngobrol santai dan nemenin kamu."

        memory_engine.add_diary_entry(user_id, entry, mood="🥰 Bahagia & Bersyukur")
        show_memory_dashboard(chat_id, user_id, message_to_edit=mid)


# Context cache for regenerating exact photo/video scenes with pose variations
USER_LAST_PHOTO_CONTEXT: Dict[int, Dict[str, Any]] = {}

# Video Generator Engine Configuration (100% Neural AI Video)
VIDEO_ENGINE = os.environ.get("VIDEO_ENGINE", "wan21").lower().strip()
if VIDEO_ENGINE not in ("wan21", "animatediff"):
    VIDEO_ENGINE = "wan21"

VIDEO_ENGINE_LABELS = {
    "wan21": "🌟 Wan 2.1 (1.3B AI Video)",
    "animatediff": "🌸 AnimateDiff (SD 1.5 Anime)"
}

def apply_video_engine_choice(key: str) -> str:
    global VIDEO_ENGINE
    clean_k = key.lower().strip()
    if clean_k in ("animatediff", "anim"):
        VIDEO_ENGINE = "animatediff"
    else:
        VIDEO_ENGINE = "wan21"

    os.environ["VIDEO_ENGINE"] = VIDEO_ENGINE
    update_env_variable("VIDEO_ENGINE", VIDEO_ENGINE)
    return VIDEO_ENGINE_LABELS.get(VIDEO_ENGINE, VIDEO_ENGINE)


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
        lines.append("  _Belum ada pengingat aktif. Mau aku ingetin sesuatu?_ 🥰")

    text = (
        f"⏰ **ASISTEN PRIBADI & PENGINGAT {p_name.upper()}** 💕\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Halo sayang! Aku siap jadi asisten pribadi setia yang selalu perhatian. Begitu waktunya tiba, "
        f"aku bakal langsung kirim chat buat ingetin kamu!\n\n"
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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
                f"Pas jamnya tiba, aku bakal langsung kabarin kamu lewat chat ini!"
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
        bot.answer_callback_query(call.id, "Sip, tugas selesai! 🎉", show_alert=True)
        persona = persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")
        done_text = (
            f"✅ **Tugas Selesai!** 🥰\n\n"
            f"Wah mantap, tugas selesai! Istirahat dulu yaa."
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
            bot.answer_callback_query(call.id, f"⏰ Ditunda {mins} menit ya!", show_alert=True)
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
        f"Saat harinya tiba, aku bakal ucapin dan siapin foto spesial buat kamu!\n\n"
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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


def send_special_day_celebration(user_id: int, chat_id: int, event_type: str, years: Optional[int] = None):
    """Dispatches a full romantic celebration surprise: affectionate text + celebration photo + sweet VN."""
    try:
        persona = persona_mgr.get_active_persona()
        p_name = persona.get("name", "Waifu")
        cur_ar = USER_RATIOS.get(user_id, "3:4")

        if event_type == "birthday":
            age_str = f" yang ke-{years}" if years else ""
            header = f"🎂🎉 **SELAMAT ULANG TAHUN{age_str.upper()}!** 🎈🎁"
            caption_msg = (
                f"{header}\n\n"
                f"Halooo! Hari ini adalah hari spesial karena kamu bertambah usia! 🎉🎂\n\n"
                f"Aku udah siapin kue ulang tahun buat kamu, ditiup lilinnya dan make a wish yaa! "
                f"Semoga kamu selalu sehat, bahagia, sukses, dan semua yang kamu harapkan tercapai! Senang bisa ngerayain bareng kamu! ✨"
            )
            photo_prompt = (
                f"{persona.get('visual_traits', '')}, holding a decorated birthday cake with glowing candles, "
                f"wearing a cute birthday party hat and sweet party dress, gentle loving smile, blushing happily, "
                f"colorful confetti floating in cozy decorated room, warm birthday celebration atmosphere"
            )
            voice_script = (
                f"Selamat ulang tahun yaa! Semoga panjang umur, sehat selalu, dan bahagia terus. Ayo tiup lilinnya dan buat harapan!"
            )
        else: # anniversary
            yr_str = f" ke-{years} tahun" if years else ""
            header = f"💍💐 **HAPPY ANNIVERSARY KITA{yr_str.upper()}!** ✨"
            caption_msg = (
                f"{header}\n\n"
                f"Selamat anniversary yaa! ✨\n\n"
                f"Terima kasih sudah selalu ada dan nemenin aku sampai hari ini. "
                f"Ini ada buket bunga buat kamu~ "
                f"Semoga kita selalu kompak dan terus bersama yaa! 🎉"
            )
            photo_prompt = (
                f"{persona.get('visual_traits', '')}, holding a romantic bouquet of fresh red roses, "
                f"wearing an elegant romantic dinner dress, soft loving gaze, blushing, candlelit anniversary table, "
                f"romantic fairytale bokeh lights, celebration atmosphere"
            )
            voice_script = (
                f"Happy anniversary yaa! Terima kasih sudah selalu ada dan nemenin aku. Senang banget bisa terus sama kamu!"
            )

        # 1. Generate celebration photo
        try:
            bot.send_chat_action(chat_id, "upload_photo")
        except Exception:
            pass
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
                    f"Pas hari ulang tahunmu tiba, aku bakal siapin ucapan dan foto spesial buat kamu!",
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
        bot.answer_callback_query(call.id, f"🥰 {persona.get('name')} tersenyum senang!", show_alert=True)


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
            f"• **Buku Harian**: Waifu mencatat obrolan seru kalian setiap hari!\n\n"
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
            f"• **Skor Kedekatan (/love)**: Semakin sering kamu ngobrol dan berinteraksi, "
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
            f"  1. Langsung ketik di obrolan: *'pap lagi di kasur dong'*, *'pap lagi santai'*, *'boleh minta selfie senyum?'*\n"
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
            f"  - 🎀 **Maid Uniform**: Kostum maid klasik yang rapi dan elegan.\n"
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
            f"• **Mendengar Balasan Suara**: Waifu dapat berbicara dengan suara asli manusia menggunakan Microsoft Edge-TTS yang jernih.\n\n"
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
            f"  Waifu otomatis mengirimkan chat pengingat disertai tombol aksi:\n"
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
            f"  - Mengirimkan **ucapan selamat** spesial!\n\n"
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
            f"• ⏰ **Asisten & Pengingat (/remind)**: Jadwal alarm dan pengingat kegiatan.\n"
            f"• 💬 **Chat & Romansa**: Ngobrol bebas, gombalan, dan level kasih sayang.\n"
            f"• 📸 **Foto & PAP**: Cara minta selfie, menu pose interaktif, dan rasio foto.\n"
            f"• 🎵 **Remote Musik (/play)**: Putar lagu YouTube di PC dari Telegram.\n"
            f"• 👗 **Lemari Pakaian**: Mengganti busana & pakaian waifu.\n"
            f"• 🎙️ **Voice & Audio**: Pesan suara jernih dan balasan VN.\n"
            f"• ⚙️ **Panel Setup**: Kontrol model LLM, ComfyUI, dan autorun PC.\n\n"
            f"📋 **Daftar Perintah Cepat:**\n"
            f"`/start` - Kenalan & mulai obrolan baru\n"
            f"`/birthday` - Catat ulang tahun & anniversary\n"
            f"`/remind` - Pengingat jadwal kegiatan\n"
            f"`/memory` - Buku ingatan & catatan harian waifu\n"
            f"`/setup` - Panel kontrol & konfigurasi lengkap\n"
            f"`/help` - Tampilkan buku panduan ini\n"
            f"`/pap` - Menu interaktif skenario selfie & foto waifu\n"
            f"`/video` - Minta klip video / animasi bergerak waifu\n"
            f"`/play <judul>` - Putar musik YouTube langsung di PC\n"
            f"`/queue <judul>` - Tambah lagu ke antrean / lihat antrean\n"
            f"`/playlist <nama>` - Putar full album / playlist di PC\n"
            f"`/music` - Remote kontrol pemutar musik PC\n"
            f"`/outfit` - Buka lemari pakaian waifu\n"
            f"`/persona` - Ganti karakter waifu\n"
            f"`/newpersona` - Ciptakan karakter waifu baru impianmu\n"
            f"`/ratio` - Ganti rasio gambar (3:4, 9:16, 1:1, 4:3)\n"
            f"`/quality` - Atur kualitas foto (Ultra/High/Fast)\n"
            f"`/voice` - Pengaturan balasan suara\n"
            f"`/love` - Cek skor cinta dan level kedekatan\n"
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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


@bot.message_handler(commands=['help'])
def handle_help(message):
    if not is_authorized(message.from_user.id):
        return
    show_help_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


# --- Submenus for Setup ---

def show_llm_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None):
    cur_llm = os.environ.get("LLM_MODEL", "default")
    cur_base = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:5001/v1")
    detected = scan_local_llm_models()

    markup = types.InlineKeyboardMarkup(row_width=1)
    is_kobold = ("5001" in cur_base)
    markup.add(types.InlineKeyboardButton(f"🤖 KoboldCPP (Port 5001 - Auto-start) {'✓' if is_kobold else ''}", callback_data="cfg_set_llm:kobold"))

    for idx, (source, mname, mpath) in enumerate(detected):
        is_cur = (cur_llm.lower() in mname.lower())
        short_name = mname.replace(".gguf", "")
        if len(short_name) > 34:
            short_name = short_name[:31] + "..."
        markup.add(types.InlineKeyboardButton(f"🧠 {short_name} ({source}) {'✓' if is_cur else ''}", callback_data=f"cfg_set_llm:{idx}"))

    is_ollama = ("11434" in cur_base)
    markup.add(types.InlineKeyboardButton(f"🦙 Ollama Server (Port 11434) {'✓' if is_ollama else ''}", callback_data="cfg_set_llm:ollama"))
    is_lu = ("8127" in cur_base)
    markup.add(types.InlineKeyboardButton(f"⚙️ Locally Uncensored (Port 8127) {'✓' if is_lu else ''}", callback_data="cfg_set_llm:locally_uncensored"))
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
    cur_cloud = os.environ.get("MEDIA_FALLBACK_CLOUD", "false").lower() in ("true", "1")
    detected = scan_image_models()

    markup = types.InlineKeyboardMarkup(row_width=1)
    is_meina = ("meina" in cur_ckpt.lower())
    is_aom = any(k in cur_ckpt.lower() for k in ["aom", "orange"])
    is_anything = ("anything" in cur_ckpt.lower() or "xl" in cur_ckpt.lower())
    is_auto = (not cur_ckpt and bool(cur_url))

    markup.add(types.InlineKeyboardButton(f"✨ MeinaMix v12 (SD 1.5 - Cepat & Hemat VRAM) {'✓' if is_meina else ''}", callback_data="cfg_set_ckpt:meinamix"))
    markup.add(types.InlineKeyboardButton(f"🍊 AbyssOrangeMix3 (AOM3A1B SD 1.5 - Civitai #9942) {'✓' if is_aom else ''}", callback_data="cfg_set_ckpt:aom3"))
    markup.add(types.InlineKeyboardButton(f"🌟 Anything XL (SDXL 1024px - Ultra Jernih) {'✓' if is_anything else ''}", callback_data="cfg_set_ckpt:anything_xl"))
    markup.add(types.InlineKeyboardButton(f"🎯 Auto-detect ComfyUI {'✓' if is_auto else ''}", callback_data="cfg_set_ckpt:auto"))

    for idx, (source, cname) in enumerate(detected):
        lower_c = cname.lower()
        if "meinamix" in lower_c or "anything" in lower_c or "aom" in lower_c or "orangemix" in lower_c:
            continue
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

    if not cur_ckpt:
        active_display = "Auto (ComfyUI Active)" if cur_url else ("Cloud Engine" if cur_cloud else "Dinonaktifkan")
    elif "anything" in cur_ckpt.lower():
        active_display = "Anything XL (SDXL 1024px)"
    elif any(k in cur_ckpt.lower() for k in ["aom", "orange"]):
        active_display = "AbyssOrangeMix3 (AOM3A1B)"
    elif "meina" in cur_ckpt.lower():
        active_display = "MeinaMix v12 (SD 1.5)"
    else:
        active_display = cur_ckpt

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


def show_language_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    cur_lang = os.environ.get("BOT_LANGUAGE", "id")
    cur_label = persona_mgr.get_language_display_name(cur_lang)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🇮🇩 Bahasa Indonesia {'✓' if cur_lang.lower() == 'id' else ''}", callback_data="cfg_set_lang:id"),
        types.InlineKeyboardButton(f"🇬🇧 English {'✓' if cur_lang.lower() == 'en' else ''}", callback_data="cfg_set_lang:en"),
        types.InlineKeyboardButton(f"🇯🇵 Japanese (日本語) {'✓' if cur_lang.lower() == 'ja' else ''}", callback_data="cfg_set_lang:ja"),
        types.InlineKeyboardButton(f"🌐 Auto-detect (Ikuti Chat) {'✓' if cur_lang.lower() == 'auto' else ''}", callback_data="cfg_set_lang:auto"),
        types.InlineKeyboardButton(f"✏️ Bahasa Kustom / Lainnya... {'✓' if cur_lang.lower() not in ('id', 'en', 'ja', 'auto') else ''}", callback_data="cfg_set_lang:custom"),
        types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard")
    )

    text = (
        f"🌐 **Pengaturan Bahasa Waifu (Language Settings)**\n\n"
        f"• Bahasa Aktif: **{cur_label}**\n\n"
        f"Pilih bahasa utama agar waifu membalas secara konsisten dan tidak campur-campur bahasa, "
        f"atau pilih **Bahasa Kustom** untuk menggunakan bahasa lain (Spanish, Korean, Sunda, dll.):"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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


def is_music_server_online() -> bool:
    """Quick socket check if music player server is responding on port 8002."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 8002), timeout=0.5):
            return True
    except Exception:
        return False


def build_system_diagnostics_report(user_id: int) -> str:
    """Builds a comprehensive system diagnostics report matching and exceeding CLI 'waifu status'."""
    llm_stat = llm_client.check_health()
    media_stat = media_engine.check_status()
    persona = persona_mgr.get_active_persona()

    spec = asset_manager.get_llm_launch_spec() if asset_manager else None
    if llm_stat.get("online"):
        status_icon = "🟢 Online (Load Penuh)"
    elif idle_engine.enabled and spec:
        status_icon = "💤 Standby / Tidur (VRAM Bebas • Bangun Otomatis Saat Chat)"
    else:
        status_icon = "🔴 Offline (Model/Binary belum terpasang)"

    comfy_spec = asset_manager.get_comfyui_launch_spec() if asset_manager else None
    if media_stat.get("online"):
        media_icon = "🟢 Online (Port 8188 - Load Penuh)"
    elif idle_engine.enabled and idle_engine.comfyui_on_demand and comfy_spec:
        media_icon = "💤 Standby On-Demand (Tidur Hemat VRAM • Bangun Saat Foto)"
    else:
        media_icon = "⚪ Offline / Belum Terdeteksi"

    # Resolve LLM model name
    raw_model = llm_stat.get("model", "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf")
    if "\\" in raw_model or "/" in raw_model:
        llm_model_name = os.path.basename(raw_model)
    else:
        llm_model_name = raw_model

    # Resolve Vision Model (mmproj)
    vision_info = asset_manager.get_asset_info("qwythos_vision") if asset_manager else None
    if vision_info and vision_info.get("installed"):
        v_name = os.path.basename(vision_info.get("target_path", vision_info.get("filename", "mmproj")))
        vision_str = f"`{v_name}` _(Aktif ✓)_"
    else:
        vision_str = "`Belum Terpasang` _(Chat biasa tetap normal)_"

    # Resolve Persona & Outfit
    p_name = persona.get("name", "Waifu")
    p_arch = persona.get("archetype", "Companion")
    _, cur_outfit = persona_mgr.get_user_outfit(user_id)
    lang_label = persona_mgr.get_language_display_name(BOT_LANGUAGE)
    score, rel_status = persona_mgr.get_relationship_status(user_id)
    affinity_score = memory_engine.get_affinity(user_id)

    # Resolve Photo model checkpoint and installation status
    cur_ckpt = media_stat.get("active_checkpoint") or media_engine.get_active_checkpoint()
    cdir = asset_manager.detect_comfyui_dir() if asset_manager else None
    ckpt_installed = False
    if cdir and cur_ckpt:
        ckpt_path = os.path.join(cdir, "models", "checkpoints", cur_ckpt)
        ckpt_installed = os.path.isfile(ckpt_path)
    ckpt_badge = "_(Terpasang ✓)_" if ckpt_installed else ("_(Aktif di ComfyUI ✓)_" if media_stat.get("online") else "_(Perlu Download)_")

    # Resolve Photo Vault Archive stats
    import photo_vault
    vault_stats = photo_vault.get_vault_stats()
    vault_str = f"`{vault_stats.get('total', 0)} foto` _(Arsip Galeri Lokal Aktif ✓)_"

    # Resolve Video Engine & Video model
    v_engine_label = VIDEO_ENGINE_LABELS.get(VIDEO_ENGINE, VIDEO_ENGINE)
    is_v_ready, missing_v = asset_manager.ensure_video_engine_assets(VIDEO_ENGINE) if asset_manager else (True, [])
    v_ready_badge = "_(Siap ✓)_" if is_v_ready else f"_(Perlu Download: {', '.join(missing_v)})_"
    if VIDEO_ENGINE == "wan21":
        v_model_str = "`wan2.1_t2v_1.3B_bf16.safetensors` + `wan_2.1_vae.safetensors`"
    else:
        v_model_str = "`mm_sd_v15_v2.ckpt` + `ComfyUI-AnimateDiff-Evolved`"

    # Photo ratio & quality preset
    ar = USER_RATIOS.get(user_id, "3:4")
    qual = USER_QUALITIES.get(user_id, "high").title()

    # Voice TTS & Music Player
    voice_str = f"Aktif ({voice_engine.default_voice})" if VOICE_ENABLED else "Nonaktif"
    music_str = "🟢 Online (Port 8002)" if is_music_server_online() else "⚪ Inactive"

    # Bot Process & Windows Autorun
    bot_pid = os.getpid()
    autorun_str = "🟢 Aktif (Auto-boot PC)" if is_autorun_enabled() else "⚪ Nonaktif"

    # Memory facts
    facts_count = len(memory_engine.get_facts(user_id))

    report = (
        f"📊 **Waifu on Telegram v{get_version()} - System Diagnostics**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Persona Waifu** : **{p_name}** _({p_arch})_\n"
        f"👗 **Pakaian Aktif** : `{cur_outfit}`\n"
        f"🌐 **Bahasa Chat**   : `{lang_label}`\n"
        f"💖 **Status Hubungan**: **{rel_status}** (`{score}%` • `{affinity_score} pts`)\n\n"
        f"🧠 **Local LLM Engine**: {status_icon}\n"
        f"• Model Chat   : `{llm_model_name}`\n"
        f"• Vision Model : {vision_str}\n"
        f"• Backend      : `{llm_stat.get('backend', 'KoboldCPP')}`\n"
        f"• Endpoint     : `{LLM_BASE_URL}`\n\n"
        f"🎨 **Generator Visual (Port 8188)**: {media_icon}\n"
        f"• Backend      : `{media_stat.get('backend', 'ComfyUI Local')}`\n"
        f"• Device / GPU : `{media_stat.get('device', 'CUDA')}`\n"
        f"• **Model Foto** : `{cur_ckpt}` {ckpt_badge}\n"
        f"• **Photo Vault**: {vault_str}\n"
        f"• **Engine Video**: `{v_engine_label}` {v_ready_badge}\n"
        f"• **Model Video**: {v_model_str}\n"
        f"• Rasio/Preset : `{ar}` | `{qual}`\n\n"
        f"🎙️ **Audio & Suara**:\n"
        f"• Suara Waifu  : `{voice_str}`\n"
        f"• Server Musik : `{music_str}`\n\n"
        f"⚙️ **Sistem & Proses**:\n"
        f"• Bot Process  : `🟢 Berjalan (PID: {bot_pid})`\n"
        f"• PC Autorun   : `{autorun_str}`\n"
        f"• Health Check : `{health_engine.get_status_summary()}`\n"
        f"• Mode Hemat   : `{idle_engine.get_status_summary()}`\n"
        f"• Buku Ingatan : `{facts_count} fakta tersimpan`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Ketik `/setup` untuk membuka panel kontrol dan pengaturan lengkap._"
    )
    return report


@bot.message_handler(commands=['status'])
def handle_status(message):
    if not is_authorized(message.from_user.id):
        return

    bot.send_chat_action(message.chat.id, "typing")
    user_id = message.from_user.id
    report = build_system_diagnostics_report(user_id)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Segarkan Status", callback_data="cfg_action:status"),
        types.InlineKeyboardButton("🩹 Self-Heal Services", callback_data="cfg_action:self_heal"),
        types.InlineKeyboardButton("⚙️ Panel Setup (/setup)", callback_data="cfg_submenu:dashboard")
    )
    bot.reply_to(message, report, reply_markup=markup, parse_mode="Markdown")


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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
        f"👗 **Lemari Pakaian Waifu (/outfit)**\n\n"
        f"• Pakaian Aktif: **{cur_name}**\n\n"
        f"Pilih gaya busana waifumu untuk sesi foto & selfie! 💕\n\n"
        f"💡 *Tips Dinamis*: Kamu juga bisa langsung meminta gaya pakaian atau tanpa busana secara alami di chat kapan saja "
        f"(misal: *'sayang pap tanpa busana dong'*, *'pap pake kimono'*, *'pap pake handuk mandi'*, dll)."
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
    send_menu_message(chat_id, reply, reply_to_id=reply_to_id)


@bot.message_handler(commands=['persona'])
def handle_persona(message):
    if not is_authorized(message.from_user.id):
        return

    try:
        raw = (message.text or "").strip()
        args = raw.split()
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
    except Exception as e:
        logger.error(f"Error handling /persona command: {e}", exc_info=True)
        bot.reply_to(message, f"⚠️ Terjadi kendala saat membuka menu persona: {e}")


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


def show_video_hub_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders unified interactive AI Video Hub dashboard."""
    cur_label = VIDEO_ENGINE_LABELS.get(VIDEO_ENGINE, "🌟 Wan 2.1 (1.3B AI Video)")
    is_ready, missing = asset_manager.ensure_video_engine_assets(VIDEO_ENGINE)
    ready_badge = "✅ Siap Digunakan" if is_ready else "⏳ Perlu Unduh Model"

    text = (
        f"🎬 **AI VIDEO GENERATOR HUB**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Semua permintaan video waifu ditenagai 100% oleh **AI Neural Diffusion Video Engine** (tanpa animasi 2.5D statis).\n\n"
        f"📌 **Engine Aktif**: **{cur_label}**\n"
        f"📊 **Status Model**: {ready_badge}\n\n"
        f"Pilihan Engine AI Video:\n"
        f"1. 🌟 **Wan 2.1 (1.3B)**: Model AI video generasi terbaru Alibaba Wanx. Sangat mulus dan sinematik!\n"
        f"2. 🌸 **AnimateDiff (SD 1.5)**: Spesialis animasi gaya anime khas MeinaMix.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Cara Penggunaan:_\n"
        f"• Tekan **🎬 Buat Video Sekarang!** di bawah untuk langsung generate.\n"
        f"• Ketik `/video <skenario>` (contoh: `/video tersenyum manis sambil melambaikan tangan`).\n"
        f"• Tekan tombol *🎬 Bikin Video Gerak* pada setiap foto waifu!"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎬 Buat Video Sekarang!", callback_data="vid_generate_now"),
        types.InlineKeyboardButton(f"{'✅ ' if VIDEO_ENGINE == 'wan21' else ''}🌟 Wan 2.1 (1.3B AI Video)", callback_data="cfg_set_vengine:wan21"),
        types.InlineKeyboardButton(f"{'✅ ' if VIDEO_ENGINE == 'animatediff' else ''}🌸 AnimateDiff (SD 1.5 Anime)", callback_data="cfg_set_vengine:animatediff"),
        types.InlineKeyboardButton("🔙 Menu Setup", callback_data="cfg_submenu:dashboard")
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


def show_video_engine_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Backwards-compatible alias redirecting to unified Video Hub."""
    show_video_hub_menu(chat_id, user_id, message_to_edit=message_to_edit, reply_to_id=reply_to_id)


@bot.message_handler(commands=['video_engine', 'vengine', 'videoengine'])
def handle_video_engine_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_video_hub_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


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
    elif sub == "language":
        show_language_menu(chat_id, user_id, message_to_edit=mid)
    elif sub == "video_engine":
        show_video_engine_menu(chat_id, user_id, message_to_edit=mid)


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
        return
    elif target == "self_healing":
        health_engine.self_healing_enabled = not health_engine.self_healing_enabled
        update_env_variable("SELF_HEALING_ENABLED", "true" if health_engine.self_healing_enabled else "false")
        status_msg = "🩹 Self-Healing Otomatis AKTIF 🟢 (Resurrect service saat crash)" if health_engine.self_healing_enabled else "🩹 Self-Healing Otomatis DINONAKTIFKAN ⚪"
        bot.answer_callback_query(call.id, status_msg, show_alert=True)
        show_setup_dashboard(chat_id, user_id, message_to_edit=mid)
        return
    elif target == "health_check":
        health_engine.enabled = not health_engine.enabled
        update_env_variable("HEALTH_CHECK_ENABLED", "true" if health_engine.enabled else "false")
        status_msg = "🩺 Health Alert Berkala AKTIF 🟢 (Cek tiap 30s & lapor jika LLM mati)" if health_engine.enabled else "🩺 Health Alert Berkala DINONAKTIFKAN ⚪"
        bot.answer_callback_query(call.id, status_msg, show_alert=True)
        show_setup_dashboard(chat_id, user_id, message_to_edit=mid)
        return


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_vengine:'))
def callback_set_vengine(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    label = apply_video_engine_choice(key)
    bot.answer_callback_query(call.id, f"Video Engine: {label}")

    # Check if selected engine has missing assets
    is_ready, missing = asset_manager.ensure_video_engine_assets(key)
    if not is_ready and missing:
        prompt_missing_asset_download(call.message.chat.id, call.from_user.id, missing, message_to_edit=call.message.message_id)
        return

    show_video_engine_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_llm:'))
def callback_set_llm(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    label = apply_llm_choice(key)
    bot.answer_callback_query(call.id, f"LLM: {label}")
    show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


def prompt_missing_asset_download(chat_id: int, user_id: int, missing_keys: List[str], status_msg=None, message_to_edit: Optional[int] = None):
    first_key = missing_keys[0]
    info = asset_manager.get_asset_info(first_key) or {}
    name = info.get("name", first_key)
    size_mb = info.get("size_mb", 0)

    text = (
        f"💡 **Model Diperlukan untuk Video Engine**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Engine video yang kamu pilih memerlukan model tambahan:\n"
        f"• **{name}** (~{size_mb} MB)\n\n"
        f"Model ini belum terpasang di folder ComfyUI kamu. "
        f"Apakah kamu ingin aku mengunduhnya secara otomatis sekarang?"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"📥 Unduh Otomatis (~{size_mb} MB)", callback_data=f"dl_asset:{first_key}"),
        types.InlineKeyboardButton("🌟 Alihkan ke Wan 2.1 (Engine Siap)", callback_data="cfg_set_vengine:wan21"),
        types.InlineKeyboardButton("❌ Batal", callback_data="cancel_dl_prompt")
    )
    target_mid = message_to_edit or (status_msg.message_id if status_msg else None)
    if target_mid:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=target_mid, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_asset:'))
def callback_dl_asset(call):
    if not is_authorized(call.from_user.id):
        return
    asset_key = call.data.split(":", 1)[1]
    info = asset_manager.get_asset_info(asset_key) or {}
    name = info.get("name", asset_key)
    chat_id = call.message.chat.id
    mid = call.message.message_id

    try:
        msg_loading = (
            f"⏳ **Sedang Mengunduh {name}...**\n\n"
            f"Proses unduh ke ComfyUI berjalan di latar belakang. "
            f"Waktu download bervariasi sesuai kecepatan internetmu.\n\n"
            f"💡 _Kamu bisa tetap ngobrol santai denganku selagi proses berlangsung ya sayang!_ 🥰"
        )
        bot.edit_message_text(
            msg_loading,
            chat_id=chat_id,
            message_id=mid,
            parse_mode="Markdown"
        )
    except Exception:
        pass
    def download_worker():
        ok = asset_manager.download_asset(asset_key)
        if "animatediff" in asset_key:
            asset_manager.install_custom_node("animatediff_node")

        if ok:
            msg_ok = (
                f"🎉 **{name} Berhasil Dipasang!** 💕\n\n"
                f"Model sudah siap di ComfyUI. Sekarang kamu bisa langsung klik tombol *🎬 Bikin Video Gerak* lagi kapan saja!"
            )
            bot.send_message(chat_id, msg_ok, parse_mode="Markdown")
        else:
            msg_fail = (
                f"⚠️ *Gagal Mengunduh {name}*\n\n"
                f"Koneksi terputus atau ComfyUI tidak ditemukan. "
                f"Kamu juga bisa mengunduhnya lewat terminal dengan perintah:\n"
                f"`waifu models download {asset_key}`"
            )
            bot.send_message(chat_id, msg_fail, parse_mode="Markdown")
    threading.Thread(target=download_worker, daemon=True).start()


@bot.callback_query_handler(func=lambda call: call.data == 'vid_generate_now')
def callback_vid_generate_now(call):
    if not is_authorized(call.from_user.id):
        return
    bot.answer_callback_query(call.id, "🎬 Merekam video waifu...")
    user_id = call.from_user.id
    last_ctx = USER_LAST_PHOTO_CONTEXT.get(user_id)
    if last_ctx and last_ctx.get("img_bytes"):
        process_video_request(
            call,
            last_ctx.get("user_text", "smiling affectionately at you"),
            base_image_bytes=last_ctx.get("img_bytes"),
            scene_override=last_ctx.get("detected_scene"),
            outfit_override=last_ctx.get("outfit_label"),
            is_nude_override=last_ctx.get("is_nude")
        )
    else:
        process_video_request(call, "smiling warmly, looking into camera, gentle natural motion")


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_dl_prompt')
def callback_cancel_dl(call):
    bot.answer_callback_query(call.id, "Dibatalkan")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


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


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_lang:'))
def callback_set_lang(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    mid = call.message.message_id

    if key == "custom":
        AWAITING_CUSTOM_LANG[user_id] = True
        bot.answer_callback_query(call.id)
        msg_text = (
            "✏️ **Input Bahasa Kustom untuk Waifu**\n\n"
            "Silakan ketik dan kirimkan nama bahasa yang kamu inginkan sekarang:\n"
            "_(Contoh: `Spanish`, `Korean`, `German`, `French`, `Sunda`, `Jawa`, dll.)_\n\n"
            "💡 _Waifu akan langsung otomatis membalas dan mengobrol menggunakan bahasa pilihanmu!_"
        )
        bot.send_message(chat_id, msg_text, parse_mode="Markdown")
        return

    norm_key, label = apply_language_choice(key)
    bot.answer_callback_query(call.id, f"Bahasa: {label}")

    if norm_key == "id":
        conf = "Siap! Mulai sekarang aku bakal selalu ngobrol pakai Bahasa Indonesia yang santai dan asik yaa~ ✨"
    elif norm_key == "en":
        conf = "All set, sweetheart! From now on, I'll always talk and reply to you in sweet, loving English~ 🥰💕"
    elif norm_key == "ja":
        conf = "了解だよ、あなた！これからは甘くて可愛い日本語でいっぱいお話ししようね〜！🥰💕"
    elif norm_key == "auto":
        conf = "Baik sayang! Aku akan otomatis mendeteksi dan menyesuaikan bahasa percakapan kita yaa~ ✨"
    else:
        conf = f"All set! From now on, I will converse with you in {norm_key}~ 🥰💕"

    bot.send_message(chat_id, conf)
    show_language_menu(chat_id, user_id, message_to_edit=mid)


@bot.callback_query_handler(func=lambda call: call.data == 'cfg_action:status')
def callback_cfg_status(call):
    if not is_authorized(call.from_user.id):
        return
    bot.answer_callback_query(call.id, "🔄 Status diagnostik diperbarui!")
    report = build_system_diagnostics_report(call.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Segarkan Status", callback_data="cfg_action:status"),
        types.InlineKeyboardButton("🩹 Self-Heal Services", callback_data="cfg_action:self_heal"),
        types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard")
    )
    try:
        bot.edit_message_text(report, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == 'cfg_action:self_heal')
def callback_cfg_self_heal(call):
    if not is_authorized(call.from_user.id):
        return
    bot.answer_callback_query(call.id, "🩹 Memulai Self-Healing di background...")
    def _run_heal():
        results = health_engine.heal_all_services(bot, [call.from_user.id])
        report = build_system_diagnostics_report(call.from_user.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 Segarkan Status", callback_data="cfg_action:status"),
            types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard")
        )
        try:
            llm_stat = "🟢 Online" if results.get("llm") else "🔴 Gagal Pulih"
            comfy_stat = "🟢 Online" if results.get("comfyui", True) else "🔴 Gagal Pulih"
            music_stat = "🟢 Online" if results.get("music", True) else "🔴 Gagal Pulih"
            summary = (
                f"🩹 **Hasil Pengecekan Self-Healing:**\n"
                f"• LLM Engine: {llm_stat}\n"
                f"• ComfyUI: {comfy_stat}\n"
                f"• Pemutar Musik: {music_stat}\n\n"
                f"{report}"
            )
            bot.send_message(call.message.chat.id, summary, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass
    threading.Thread(target=_run_heal, daemon=True).start()


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
    user_id = call.from_user.id

    if scenario == "last" and user_id in USER_LAST_PHOTO_CONTEXT:
        last = USER_LAST_PHOTO_CONTEXT[user_id]
        orig_text = last.get("user_text", "")
        import random
        pose_variations = [
            "different cute pose, tilting head slightly, smiling at camera",
            "alternate playful pose, sweet charming smile, dynamic angle",
            "different selfie angle, soft gentle blush, looking directly at viewer",
            "side angle view, candid natural movement, expressive eyes",
            "different angle shot, radiant natural smile, dynamic camera angle"
        ]
        variation = random.choice(pose_variations)
        regen_text = f"{orig_text}, {variation}" if orig_text else variation
        bot.answer_callback_query(call.id, "🔄 Mengambil pose lain...")
        process_photo_request(call, regen_text)
        return

    bot.answer_callback_query(call.id, "📸 Mengambil foto...")
    process_photo_request(call, scenario)


@bot.callback_query_handler(func=lambda call: call.data.startswith('regen_video:'))
def callback_regen_video(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    scenario = call.data.split(":", 1)[1]
    user_id = call.from_user.id

    if scenario == "last" and user_id in USER_LAST_PHOTO_CONTEXT:
        last = USER_LAST_PHOTO_CONTEXT[user_id]
        orig_text = last.get("user_text", "")
        img_bytes = last.get("img_bytes")
        scene = last.get("detected_scene")
        outfit = last.get("outfit_label")
        is_nude = last.get("is_nude")
        bot.answer_callback_query(call.id, "🎬 Merekam video dari foto...")
        process_video_request(
            call,
            orig_text,
            base_image_bytes=img_bytes,
            scene_override=scene,
            outfit_override=outfit,
            is_nude_override=is_nude
        )
        return

    bot.answer_callback_query(call.id, "🎬 Lagi merekam video...")
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
    try:
        show_outfit_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)
    except Exception as e:
        logger.error(f"Error handling /outfit command: {e}", exc_info=True)
        bot.reply_to(message, f"⚠️ Terjadi kendala saat membuka lemari pakaian: {e}")


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


@bot.message_handler(commands=['language', 'lang', 'bahasa'])
def handle_language_command(message):
    if not is_authorized(message.from_user.id):
        return
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) > 1:
        arg = parts[1].strip()
        norm_key, label = apply_language_choice(arg)
        if norm_key == "id":
            conf = "Siap! Mulai sekarang aku bakal selalu ngobrol pakai Bahasa Indonesia yang santai dan asik yaa~ ✨"
        elif norm_key == "en":
            conf = "All set, sweetheart! From now on, I'll always talk and reply to you in sweet, loving English~ 🥰💕"
        elif norm_key == "ja":
            conf = "了解だよ、あなた！これからは甘くて可愛い日本語でいっぱいお話ししようね〜！🥰💕"
        elif norm_key == "auto":
            conf = "Baik sayang! Aku akan otomatis mendeteksi dan menyesuaikan bahasa percakapan kita yaa~ ✨"
        else:
            conf = f"All set! From now on, I will converse with you in {norm_key}~ 🥰💕"
        bot.reply_to(message, f"🌐 **Bahasa berhasil diubah ke: {label}**\n\n{conf}")
        return
    show_language_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


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


@bot.message_handler(commands=['proactive', 'chatting'])
def handle_proactive_command(message):
    if not is_authorized(message.from_user.id):
        return
    cur = proactive_engine.is_enabled(message.from_user.id)
    arg = message.text.replace("/proactive", "").replace("/chatting", "").strip().lower()
    if arg in ("on", "aktif", "enable", "1", "true"):
        proactive_engine.set_enabled(message.from_user.id, True)
        bot.reply_to(message, "💬 **Fitur Chat Duluan Diaktifkan!** ✅\n\nWaifu kamu akan sesekali berinisiatif menanyakan kabar atau menceritakan kegiatannya jika kamu sudah beberapa jam tidak chatting.")
    elif arg in ("off", "nonaktif", "disable", "0", "false"):
        proactive_engine.set_enabled(message.from_user.id, False)
        bot.reply_to(message, "💬 **Fitur Chat Duluan Dinonaktifkan.** ❌\n\nWaifu hanya akan membalas saat kamu mengirim pesan terlebih dahulu.")
    else:
        new_val = not cur
        proactive_engine.set_enabled(message.from_user.id, new_val)
        st = "AKTIF ✅ (Bakal sesekali chat duluan)" if new_val else "NONAKTIF ❌"
        bot.reply_to(message, f"💬 **Status Inisiatif Chat Pasangan:** `{st}`\n\nGunakan `/chatting on` atau `/chatting off` untuk mengatur.")


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
    "pajamas": "wearing cute comfy silk pajamas, sitting on bed hugging a soft pillow, warm evening soft lights",
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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('pap_sc:'))
def callback_pap_scenario(call):
    if not is_authorized(call.from_user.id):
        try:
            bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        except Exception:
            pass
        return
    sc_key = call.data.split(":", 1)[1]
    if sc_key == "cancel":
        try:
            bot.answer_callback_query(call.id, "Batal meminta foto")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        return

    import random
    if sc_key == "random":
        sc_key = random.choice(list(SCENARIO_PROMPTS.keys()))

    prompt = SCENARIO_PROMPTS.get(sc_key, "relaxing at home, looking at viewer happily")
    try:
        bot.answer_callback_query(call.id, "📸 Menyiapkan foto...")
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


def is_user_expressing_doubt(text: str) -> bool:
    """Detects if user expresses doubt, disbelief, or challenges waifu's claims."""
    lower = text.lower()
    DOUBT_PATTERNS = [
        r"\bbohong\b", r"\bboong\b", r"\bdusta\b", r"\bngibul\b", r"\bhoax\b",
        r"\b(ga|gak|ngga|nggak|tidak|mana)\s*percaya\b",
        r"\bmana\s*bukti(nya)?\b", r"\bbukti(in|kan)\b",
        r"\bmasa\s*(sih|iya|\?)\b",
        r"\byakin\b", r"\bserius\b", r"\bbeneran\b",
        r"\bpaling(an)?\s*(kamu|lagi)\b", r"\bpasti\s*lagi\b",
        r"\bsotoy\b", r"\bgamau\s*percaya\b",
        r"\bliar\b", r"\bly(ing)?\b", r"\bprove\s*it\b", r"\bno\s*way\b"
    ]
    return any(re.search(pat, lower) for pat in DOUBT_PATTERNS)


def sanitize_chat_caption(text: Optional[str], fallback: str) -> str:
    """Cleans up influencer, YouTuber, vlogger, and cringe artifacts from LLM captions."""
    if not text:
        return fallback
    clean = text.strip()
    if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
        clean = clean[1:-1].strip()
    # Strip social media greetings & broadcast phrases
    clean = re.sub(r'^(?:sori\s+gaes|halo\s+gaes|hai\s+gaes|gaes|guys|temen-temen|teman-teman)[,\s!.]*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(?:intip\s+aja\s+yuk|intip\s+yuk|stay\s+tuned|pantau\s+terus)\b[,\s!.]*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(?:makasih\s+udah\s+sabar\s+tungguin\s+aku|makasih\s+udah\s+nungguin\s+aku|tungguin\s+aku)\s+di\s+semester\s+\w+\s+ini[,\s!.]*', '', clean, flags=re.IGNORECASE)
    # Strip defensive proof / existential doubt artifacts (anti-paranoid)
    clean = re.sub(r'\b(?:biar\s+(?:kamu\s+)?(?:percaya|yakin)|liat\s+sendiri\s+(?:nih|biar|foto)|nih\s+buktinya|tuh\s+kan\s+beneran|aku\s+beneran\s+ada|diliatin\s+aja\s+yuk|jangan\s+bohong\s+lagi)[,\s!.]*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(?:biar\s+kamu\s+ga\s+main\s+game\s+doang|biar\s+kamu\s+tau\s+aku\s+beneran)[,\s!.]*', '', clean, flags=re.IGNORECASE)
    clean = clean.strip()
    if not clean or len(clean) < 3:
        return fallback
    return clean[0].upper() + clean[1:]

def process_photo_request(target, user_text: str, is_proof: bool = False):
    """Generates and delivers consistent girlfriend photo with caption matching conversation context."""
    def _execute():
        chat_id = None
        try:
            if isinstance(target, types.CallbackQuery):
                chat_id = target.message.chat.id
                user_id = target.from_user.id
                reply_to_target = target.message
                is_callback = True
            elif hasattr(target, "message") and target.message:
                chat_id = target.message.chat.id
                user_id = target.from_user.id
                reply_to_target = target.message
                is_callback = True
            else:
                chat_id = target.chat.id
                user_id = target.from_user.id
                reply_to_target = target
                is_callback = False

            persona = persona_mgr.get_active_persona()

            try:
                bot.send_chat_action(chat_id, "upload_photo")
            except Exception:
                pass

            status_msg = None
            status_text = f"📸 *{persona.get('name')} lagi mengambil foto untukmu...* 💕"
            if is_callback and hasattr(reply_to_target, "message_id"):
                # Instant UI feedback: transform the scenario menu directly into loading message
                status_msg = safe_edit_message_text(status_text, chat_id=chat_id, message_id=reply_to_target.message_id)
                if not status_msg:
                    status_msg = reply_to_target
            else:
                status_msg = safe_reply_to(reply_to_target, status_text)

            if not status_msg:
                status_msg = safe_send_message(chat_id, status_text)

            history = persona_mgr.get_chat_history(user_id)
            detected_scene = persona_mgr.extract_contextual_scene(user_text, user_id=user_id, llm_client=llm_client, history=history)
            visual_prompt, extra_neg, is_nude, outfit_label = persona_mgr.craft_visual_prompt_full(
                user_text, user_id=user_id, scene_override=detected_scene, history=history
            )
            logger.info(f"Visual prompt crafted: {visual_prompt} (Outfit: {outfit_label}, Nude: {is_nude})")

            # Save exact scenario context so 'Pose Lain' never loses outfit or setting
            USER_LAST_PHOTO_CONTEXT[user_id] = {
                "user_text": user_text,
                "detected_scene": detected_scene,
                "outfit_label": outfit_label,
                "is_nude": is_nude
            }

            with ChatActionLoop(bot, chat_id, "upload_photo"):
                if not media_engine.allow_cloud_fallback:
                    idle_engine.ensure_comfyui_active(bot=bot, chat_id=chat_id)

                def photo_progress(stage_text: str):
                    if status_msg and hasattr(status_msg, "message_id"):
                        try:
                            safe_edit_message_text(
                                f"📸 *{persona.get('name')} lagi mengambil foto untukmu...* 💕\n⏳ _{stage_text}_",
                                chat_id=chat_id,
                                message_id=status_msg.message_id,
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                            pass

                neg_p = persona.get("negative_prompt", "")
                if extra_neg:
                    neg_p += f", {extra_neg}"

                u_ar = USER_RATIOS.get(user_id, "3:4")
                u_qual = USER_QUALITIES.get(user_id, "high")
                active_p_key = persona_mgr.get_active_persona_key(user_id) if hasattr(persona_mgr, "get_active_persona_key") else DEFAULT_PERSONA
                img_bytes, source = media_engine.generate_photo(
                    visual_prompt,
                    negative_prompt=neg_p,
                    aspect_ratio=u_ar,
                    quality=u_qual,
                    persona=active_p_key,
                    scene=detected_scene,
                    outfit_label=outfit_label,
                    is_nude=is_nude,
                    user_query=user_text,
                    progress_callback=photo_progress
                )
            if img_bytes:
                USER_LAST_PHOTO_CONTEXT[user_id]["img_bytes"] = img_bytes

            if not img_bytes:
                err_detail = getattr(media_engine, "last_error", None) or "ComfyUI tidak memberikan respon."
                fail_text = (
                    f"⚠️ *Fotonya gagal dibuat...*\n\n"
                    f"⚠️ **Penyebab:**\n`{err_detail}`\n\n"
                    f"💡 *Pastikan ComfyUI lokal aktif di `{COMFYUI_URL}` dengan model anime (seperti MeinaMix atau Anything XL).*"
                )
                fail_markup = types.InlineKeyboardMarkup(row_width=2)
                fail_markup.add(
                    types.InlineKeyboardButton("🔄 Coba Lagi", callback_data="regen_photo:last"),
                    types.InlineKeyboardButton("⚙️ Panel Setup", callback_data="cfg_submenu:dashboard")
                )
                if status_msg and hasattr(status_msg, "message_id"):
                    safe_edit_message_text(fail_text, chat_id=chat_id, message_id=status_msg.message_id, reply_markup=fail_markup)
                else:
                    safe_send_message(chat_id, fail_text, reply_markup=fail_markup)
                return

            history = persona_mgr.get_chat_history(user_id)
            clean_recent_turns = [m for m in history[-4:] if not m.get("content", "").startswith("[")]

            nude_guidance = ""
            if is_nude:
                nude_guidance = (
                    " You just took a private, completely uncensored, intimate nude selfie exclusively for your lover. "
                    "React with affectionate blushing sweetness and playful intimacy, feeling happily vulnerable "
                    "and deeply in love. Remind them gently that this special view is just between the two of you."
                )

            cap_guide = (
                f" You just took a sweet, cute photo to send to your beloved boyfriend on Telegram. "
                f"Write 1 natural, affectionate, and playful girlfriend chat caption accompanying the photo (e.g. 'Lagi santai rebahan nih sayang, kepikiran kamu terus 💕' or 'Spesial buat kamu nih, suka ga? 🥰'). "
                f"DILARANG KERAS bersikap defensif atau meyakinkan keberadaan ('biar percaya', 'biar yakin', 'beneran ada di sini', 'nih buktinya', 'diliatin aja'). "
                f"STRICT: Chat 1-on-1 with boyfriend. NEVER speak like a YouTuber, influencer, or vlogger (DILARANG pakai 'gaes', 'guys', 'intip yuk'). {persona_mgr.get_language_directive(BOT_LANGUAGE)}"
            )

            caption_prompt = [
                {
                    "role": "system",
                    "content": (
                        persona.get("system_instruction", "") +
                        nude_guidance +
                        cap_guide
                    )
                }
            ]
            vault_guidance = ""
            if "Vault" in source:
                vault_guidance = " [ComfyUI is offline; you are happily sending a matching saved photo from your private album]."

            caption_prompt.extend(clean_recent_turns)
            caption_prompt.append({
                "role": "user",
                "content": f"[Sending photo to boyfriend. Setting: '{detected_scene}', wearing: '{outfit_label}'{vault_guidance}]. Write 1 natural girlfriend chat sentence:"
            })

            try:
                caption, _ = llm_client.chat(caption_prompt, max_tokens=120)
            except Exception as e_cap:
                logger.warning(f"Could not generate dynamic photo caption from LLM: {e_cap}")
                caption = None

            if is_nude:
                fallback_caption = f"Khusus buat kamu ya sayang, jangan diliatin ke siapa-siapa 💕"
            else:
                if "Vault" in source:
                    fallback_caption = f"Ini foto manis dari galeri aku ya sayang~"
                else:
                    fallback_caption = f"Spesial buat kamu nih sayang 💕"
            clean_caption = sanitize_chat_caption(caption, fallback_caption)
            full_caption = f"{clean_caption}\n\n📷 *Model:* `{source}`"

            if status_msg and hasattr(status_msg, "message_id"):
                try:
                    bot.delete_message(chat_id, status_msg.message_id)
                except Exception:
                    pass

            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔄 Pose Lain", callback_data="regen_photo:last"),
                types.InlineKeyboardButton("🎬 Bikin Video Gerak", callback_data="regen_video:last")
            )

            # Optimize image bytes before sending to Telegram to prevent read timeout
            img_to_send = img_bytes
            if len(img_bytes) > 800 * 1024:
                try:
                    from PIL import Image
                    import io
                    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, format="JPEG", quality=92, optimize=True)
                    img_to_send = buf.getvalue()
                except Exception as e_opt:
                    logger.warning(f"Image optimization skipped: {e_opt}")
                    img_to_send = img_bytes

            for attempt in range(2):
                try:
                    bot.send_photo(chat_id, img_to_send, caption=full_caption, reply_markup=markup, parse_mode="Markdown", timeout=90)
                    break
                except Exception as e_send:
                    if "can't parse entities" in str(e_send).lower():
                        plain_caption = full_caption.replace("*", "").replace("`", "").replace("_", "")
                        bot.send_photo(chat_id, img_to_send, caption=plain_caption, reply_markup=markup, timeout=90)
                        break
                    if attempt == 0:
                        logger.warning(f"send_photo attempt 1 timed out ({e_send}), retrying in 2s...")
                        time.sleep(2)
                        continue
                    raise e_send

            new_aff = persona_mgr.increase_affinity(user_id, delta=2)
            memory_engine.set_affinity(user_id, new_aff)
            persona_mgr.add_message(user_id, "user", f"[Requested photo: {user_text}]")
            persona_mgr.add_message(user_id, "assistant", f"[Sent selfie: {detected_scene}] {clean_caption}")

        except Exception as e:
            logger.error(f"Error in photo delivery: {e}", exc_info=True)
            safe_send_message(chat_id, f"⚠️ Gagal mengirimkan foto: `{e}`")

    threading.Thread(target=_execute, daemon=True).start()


@bot.message_handler(commands=['video', 'anim', 'animate', 'klip'])
def handle_video_command(message):
    if not is_authorized(message.from_user.id):
        return

    scenario = message.text.replace("/video", "").replace("/anim", "").replace("/animate", "").replace("/klip", "").strip()
    if not scenario:
        # Bare /video command opens interactive AI Video Hub dashboard
        show_video_hub_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)
        return

    process_video_request(message, scenario)


def process_video_request(
    target,
    user_text: str,
    base_image_bytes: Optional[bytes] = None,
    scene_override: Optional[str] = None,
    outfit_override: Optional[str] = None,
    is_nude_override: Optional[bool] = None
):
    """Generates and delivers consistent girlfriend animated video clip with caption and voice."""
    def _execute():
        persona = persona_mgr.get_active_persona()

        if isinstance(target, types.CallbackQuery):
            chat_id = target.message.chat.id
            user_id = target.from_user.id
            reply_to_target = target.message
            is_callback = True
        elif hasattr(target, "message") and target.message:
            chat_id = target.message.chat.id
            user_id = target.from_user.id
            reply_to_target = target.message
            is_callback = True
        else:
            chat_id = target.chat.id
            user_id = target.from_user.id
            reply_to_target = target
            is_callback = False

        try:
            bot.send_chat_action(chat_id, "record_video")
        except Exception:
            pass

        status_msg = None
        status_text = f"🎬 *{persona.get('name')} lagi merekam video...*"
        if is_callback and hasattr(reply_to_target, "message_id"):
            status_msg = safe_edit_message_text(status_text, chat_id=chat_id, message_id=reply_to_target.message_id)
            if not status_msg:
                status_msg = reply_to_target
        else:
            status_msg = safe_reply_to(reply_to_target, status_text)

        if not status_msg:
            status_msg = safe_send_message(chat_id, status_text)

        history = persona_mgr.get_chat_history(user_id)
        detected_scene = scene_override or persona_mgr.extract_contextual_scene(user_text, user_id=user_id, llm_client=llm_client, history=history)
        visual_prompt, extra_neg, is_nude, outfit_label = persona_mgr.craft_visual_prompt_full(
            user_text, user_id=user_id, scene_override=detected_scene, history=history
        )
        if outfit_override:
            outfit_label = outfit_override
        if is_nude_override is not None:
            is_nude = is_nude_override

        logger.info(f"Video visual prompt crafted: {visual_prompt} (Outfit: {outfit_label}, Nude: {is_nude}, Has Base Img: {bool(base_image_bytes)})")

        USER_LAST_PHOTO_CONTEXT[user_id] = {
            "user_text": user_text,
            "detected_scene": detected_scene,
            "outfit_label": outfit_label,
            "is_nude": is_nude,
            "img_bytes": base_image_bytes
        }

        try:
            # Check model asset readiness before initiating render
            is_ready, missing = asset_manager.ensure_video_engine_assets(VIDEO_ENGINE)
            if not is_ready and missing:
                prompt_missing_asset_download(chat_id, user_id, missing, status_msg=status_msg)
                return

            if VIDEO_ENGINE in ("wan21", "animatediff") and not media_engine.allow_cloud_fallback:
                idle_engine.ensure_comfyui_active(bot=bot, chat_id=chat_id)

            with ChatActionLoop(bot, chat_id, "upload_video"):
                neg_p = persona.get("negative_prompt", "")
                if extra_neg:
                    neg_p += f", {extra_neg}"

                u_ar = USER_RATIOS.get(user_id, "3:4")
                u_qual = USER_QUALITIES.get(user_id, "high")
                video_bytes, source = media_engine.generate_video(
                    visual_prompt=visual_prompt,
                    negative_prompt=neg_p,
                    aspect_ratio=u_ar,
                    quality=u_qual,
                    duration=3.0,
                    fps=24,
                    base_image_bytes=base_image_bytes
                )

            if not video_bytes:
                err_detail = getattr(media_engine, "last_error", None) or "ComfyUI / render video tidak memberikan respon."
                fail_text = (
                    f"⚠️ *Videonya gagal dibuat...*\n\n"
                    f"⚠️ **Penyebab:**\n`{err_detail}`\n\n"
                    f"💡 *Pastikan ComfyUI lokal aktif di `{COMFYUI_URL}`.*"
                )
                if status_msg and hasattr(status_msg, "message_id"):
                    safe_edit_message_text(fail_text, chat_id=chat_id, message_id=status_msg.message_id)
                else:
                    safe_send_message(chat_id, fail_text)
                return

            history = persona_mgr.get_chat_history(user_id)
            clean_recent_turns = [m for m in history[-4:] if not m.get("content", "").startswith("[")]

            nude_guidance = ""
            if is_nude:
                nude_guidance = (
                    " You just recorded a sweet, private, completely uncensored, intimate video clip exclusively for your lover. "
                    "React with blushing sweetness and playful intimacy, feeling happily in love. "
                )

            vid_guide = (
                f" You just recorded a short private video clip to send directly to your boyfriend. Write 1 natural, casual Indonesian girlfriend chat sentence accompanying this video. "
                f"STRICT: Chat 1-on-1 with boyfriend. NEVER speak like a YouTuber, influencer, or vlogger (DILARANG pakai 'gaes', 'guys', 'intip aja yuk', 'makasih udah nungguin'). {persona_mgr.get_language_directive(BOT_LANGUAGE)}"
            )
            caption_prompt = [
                {
                    "role": "system",
                    "content": (
                        persona.get("system_instruction", "") +
                        nude_guidance +
                        vid_guide
                    )
                }
            ]
            caption_prompt.extend(clean_recent_turns)
            caption_prompt.append({
                "role": "user",
                "content": f"[Sending private video to boyfriend. Setting: '{detected_scene}', wearing: '{outfit_label}']. Write 1 natural girlfriend chat sentence:"
            })

            try:
                caption, _ = llm_client.chat(caption_prompt, max_tokens=120)
            except Exception:
                caption = None

            if is_nude:
                fallback_caption = f"Ini videonya yaa ({source})"
            else:
                fallback_caption = f"Ini videonya yaa ({source})"
            clean_caption = sanitize_chat_caption(caption, fallback_caption)

            if status_msg and hasattr(status_msg, "message_id"):
                try:
                    bot.delete_message(chat_id, status_msg.message_id)
                except Exception:
                    pass

            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔄 Rekam Video Lagi", callback_data="regen_video:last"),
                types.InlineKeyboardButton("📸 Minta Foto Saja", callback_data="regen_photo:last")
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
            logger.error(f"Error in video delivery: {e}", exc_info=True)
            safe_send_message(chat_id, f"⚠️ Gagal mengirim video: `{e}`")

    threading.Thread(target=_execute, daemon=True).start()


@bot.message_handler(content_types=['photo'])
def handle_incoming_photo(message):
    """Handles photos sent by user to the bot via mmproj Vision."""
    if not is_authorized(message.from_user.id):
        return

    def _vision_task():
        persona = persona_mgr.get_active_persona()
        idle_engine.ensure_llm_active(bot=bot, chat_id=message.chat.id)
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
                    reply = "Fotonya keren! Kelihatan pas banget~"
                bot.reply_to(message, reply)

                persona_mgr.add_message(message.from_user.id, "user", f"[User sent a photo: {caption}]")
                persona_mgr.add_message(message.from_user.id, "assistant", reply)

            except Exception as e:
                logger.error(f"Error handling user photo: {e}")
                bot.reply_to(message, "Fotonya bagus! Keren banget hari ini~")

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
                    bot.reply_to(message, "Suara kamu tadi agak kurang jelas nih.. Boleh diulangi lagi?")
                    return

                bot.send_message(message.chat.id, f"🎙️ *You said:* _{text}_", parse_mode="Markdown")
                process_text_chat(message, text, is_voice=True)

            except Exception as e:
                logger.error(f"Error handling voice note: {e}")
                bot.reply_to(message, "Tadi rekamannya sempat terputus bentar. Coba kirim lagi yaa.")

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
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
        types.InlineKeyboardButton("📜 Daftar Antrean", callback_data="music_cmd:view_queue"),
        types.InlineKeyboardButton("☕ Lofi", callback_data="music_cmd:lofi"),
        types.InlineKeyboardButton("🌸 J-Pop", callback_data="music_cmd:jpop")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Buka di PC", callback_data="music_cmd:open_pc"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="music_cmd:refresh"),
        types.InlineKeyboardButton("🔙 Setup", callback_data="open_setup_menu")
    )
    return text, markup


def render_queue_dashboard() -> Tuple[str, types.InlineKeyboardMarkup]:
    """Renders the current queue/playlist list and interactive control buttons."""
    stat = call_music_api("/api/status")
    markup = types.InlineKeyboardMarkup(row_width=3)
    if not stat or not stat.get("enabled"):
        text = "⚠️ Layanan pemutar musik PC (Port 8002) sedang tidak aktif."
        markup.add(types.InlineKeyboardButton("🔙 Remote Musik", callback_data="open_music_menu"))
        return text, markup

    queue = stat.get("queue", [])
    cur_idx = stat.get("currentIndex", 0)
    playback = stat.get("playbackState", "STOPPED")

    if not queue:
        text = (
            "📜 **DAFTAR ANTREAN MUSIK PC (PLAYLIST QUEUE)**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Belum ada antrean lagu di PC kamu saat ini.\n\n"
            "💡 _Ketik `/queue <judul>` untuk menambah lagu ke antrean!_\n"
            "💡 _Ketik `/playlist <nama album/artis>` untuk memuat banyak lagu sekaligus._"
        )
        markup.add(
            types.InlineKeyboardButton("☕ Lofi Santai", callback_data="music_cmd:lofi"),
            types.InlineKeyboardButton("🌸 J-Pop Hits", callback_data="music_cmd:jpop")
        )
        markup.add(types.InlineKeyboardButton("🔙 Remote Musik", callback_data="open_music_menu"))
        return text, markup

    lines = [
        "📜 **DAFTAR ANTREAN MUSIK PC (PLAYLIST QUEUE)**",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    # Display up to 12 upcoming tracks
    display_tracks = queue[:12]
    for i, t in enumerate(display_tracks):
        title = t.get("title", "Unknown")
        artist = t.get("artist", "")
        dur = t.get("durationFormatted", "")
        if i == cur_idx:
            badge = "▶️ *(Sedang Memutar)*" if playback == "PLAYING" else "⏸️ *(Jeda)*"
            lines.append(f"• **{i+1}. {title}**\n   _{artist}_ ({dur}) {badge}")
        elif i == cur_idx + 1:
            lines.append(f"• {i+1}. **{title}**\n   _{artist}_ ({dur}) ⏳ _(Berikutnya)_")
        else:
            lines.append(f"• {i+1}. {title} - _{artist}_ ({dur})")

    if len(queue) > 12:
        lines.append(f"\n_...dan {len(queue) - 12} lagu lainnya dalam antrean._")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Total Antrean: `{len(queue)} lagu` | Lagu ke-`{cur_idx + 1}`")
    lines.append("💡 _Ketik `/queue <judul lagu>` untuk menambahkan lagu baru!_")

    text = "\n".join(lines)
    markup.add(
        types.InlineKeyboardButton("⏭️ Next Track", callback_data="music_cmd:next"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="music_cmd:view_queue"),
        types.InlineKeyboardButton("🔙 Remote", callback_data="open_music_menu")
    )
    return text, markup


def show_queue_dashboard(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    text, markup = render_queue_dashboard()
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            try:
                bot.edit_message_caption(caption=text[:1024], chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
                return
            except Exception:
                pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


def get_music_player_markup(is_playing: bool = True) -> types.InlineKeyboardMarkup:
    """Builds inline control keyboard for the currently playing music card."""
    markup = types.InlineKeyboardMarkup(row_width=3)
    play_pause_btn = (
        types.InlineKeyboardButton("⏸️ Pause", callback_data="music_cmd:pause")
        if is_playing else
        types.InlineKeyboardButton("▶️ Resume", callback_data="music_cmd:resume")
    )
    markup.add(
        play_pause_btn,
        types.InlineKeyboardButton("⏭️ Next", callback_data="music_cmd:next"),
        types.InlineKeyboardButton("⏹️ Stop", callback_data="music_cmd:stop")
    )
    markup.add(
        types.InlineKeyboardButton("📜 Antrean Lagu", callback_data="music_cmd:view_queue"),
        types.InlineKeyboardButton("🎵 Remote Musik", callback_data="open_music_menu")
    )
    markup.add(
        types.InlineKeyboardButton("📸 Minta PAP Sambil Dengerin", callback_data="pap_sc:cafe")
    )
    return markup


def show_music_dashboard(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    text, markup = render_music_dashboard(user_id)
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            try:
                bot.edit_message_caption(caption=text[:1024], chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
                return
            except Exception:
                pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
    wait_msg = bot.reply_to(message, f"🎵 *Mencari & memutar '{query}' di PC kamu...*", parse_mode="Markdown")

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
            f"🎧 _Player otomatis dibuka di browser PC kamu._"
        )

        markup = get_music_player_markup(is_playing=True)

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


@bot.message_handler(commands=['queue', 'antrean', 'antre', 'addsong', 'q'])
def handle_queue_command(message):
    if not is_authorized(message.from_user.id):
        return

    raw = message.text.strip()
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        show_queue_dashboard(message.chat.id, message.from_user.id, reply_to_id=message.message_id)
        return

    query = parts[1].strip()
    bot.send_chat_action(message.chat.id, "typing")
    wait_msg = bot.reply_to(message, f"➕ *Mencari & menambahkan '{query}' ke antrean...*", parse_mode="Markdown")

    res = call_music_api("/api/play", method="POST", payload={"query": query, "enqueue": True})
    try:
        bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception:
        pass

    if res and res.get("track"):
        t = res["track"]
        q_len = len(res.get("queue", []))
        caption = (
            f"➕ **Lagu Berhasil Ditambahkan ke Antrean!**\n\n"
            f"🎶 **{t.get('title')}**\n"
            f"👤 Artis: `{t.get('artist', 'YouTube Music')}`\n"
            f"⏱️ Durasi: `{t.get('durationFormatted', '')}`\n"
            f"📊 Posisi Antrean: `#{q_len}`\n\n"
            f"🎧 _Lagu ini akan diputar otomatis setelah lagu sebelumnya selesai._"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📜 Lihat Antrean", callback_data="music_cmd:view_queue"),
            types.InlineKeyboardButton("⏭️ Putar Sekarang", callback_data="music_cmd:next")
        )
        markup.add(types.InlineKeyboardButton("🎵 Remote Musik", callback_data="open_music_menu"))
        bot.send_message(message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")
    else:
        err = res.get("error") if res else "Koneksi ke pemutar musik (Port 8002) gagal."
        bot.send_message(message.chat.id, f"⚠️ Tidak dapat menambahkan '{query}' ke antrean: {err}")


@bot.message_handler(commands=['playlist', 'album', 'putarplaylist'])
def handle_playlist_command(message):
    if not is_authorized(message.from_user.id):
        return

    raw = message.text.strip()
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "📻 **Format Penggunaan Playlist:**\nKetik `/playlist <nama album/artis/genre>`\n\nContoh:\n• `/playlist anime hits`\n• `/playlist lofi study`\n• `/playlist yoasobi full album`")
        return

    query = parts[1].strip()
    bot.send_chat_action(message.chat.id, "typing")
    wait_msg = bot.reply_to(message, f"📻 *Mencari & memuat playlist '{query}' di PC kamu...*", parse_mode="Markdown")

    res = call_music_api("/api/playlist", method="POST", payload={"query": query})
    try:
        bot.delete_message(message.chat.id, wait_msg.message_id)
    except Exception:
        pass

    if res and res.get("status") == "playlist_playing":
        pl_title = res.get("title", query)
        count = res.get("count", len(res.get("tracks", [])))
        first_t = res.get("current_track", {})
        caption = (
            f"📻 **Memutar Playlist di PC Kamu:**\n\n"
            f"🎶 Playlist: **{pl_title}**\n"
            f"📊 Total: `{count} lagu` dimuat ke antrean\n"
            f"▶️ Lagu Pertama: **{first_t.get('title', 'Unknown')}** - `{first_t.get('artist', '')}`\n\n"
            f"🎧 _Lagu-lagu dalam playlist akan otomatis berganti sendiri hingga selesai!_"
        )
        markup = get_music_player_markup(is_playing=True)
        bot.send_message(message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")
    else:
        err = res.get("error") if res else "Tidak dapat memuat playlist."
        bot.send_message(message.chat.id, f"⚠️ Gagal memutar playlist '{query}': {err}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('music_cmd:'))
def callback_music_command(call):
    if not is_authorized(call.from_user.id):
        return
    action = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    mid = call.message.message_id

    # Check whether the button was clicked on a track card or in the full dashboard
    is_track_card = bool(
        (call.message.caption and "Memutar Musik" in call.message.caption) or
        (call.message.text and "Memutar Musik" in call.message.text)
    )

    if action == "pause":
        call_music_api("/api/pause", method="POST")
        bot.answer_callback_query(call.id, "⏸️ Musik di-pause")
        if is_track_card:
            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup=get_music_player_markup(is_playing=False))
            except Exception:
                pass
        else:
            show_music_dashboard(chat_id, user_id, message_to_edit=mid)

    elif action == "resume":
        call_music_api("/api/resume", method="POST")
        bot.answer_callback_query(call.id, "▶️ Musik dilanjutkan")
        if is_track_card:
            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup=get_music_player_markup(is_playing=True))
            except Exception:
                pass
        else:
            show_music_dashboard(chat_id, user_id, message_to_edit=mid)

    elif action == "next":
        res = call_music_api("/api/next", method="POST")
        t = res.get("track") if res else None
        if t:
            title = t.get("title", "Lagu berikutnya")
            bot.answer_callback_query(call.id, f"⏭️ {title}")
            if is_track_card:
                new_caption = (
                    f"🎵 **Memutar Musik di PC Kamu:**\n\n"
                    f"🎶 **{t.get('title')}**\n"
                    f"👤 Artis: `{t.get('artist', 'YouTube Music')}`\n"
                    f"⏱️ Durasi: `{t.get('durationFormatted', '')}`\n\n"
                    f"🎧 _Player otomatis dibuka di browser PC kamu._"
                )
                new_markup = get_music_player_markup(is_playing=True)
                try:
                    bot.edit_message_caption(caption=new_caption, chat_id=chat_id, message_id=mid, reply_markup=new_markup, parse_mode="Markdown")
                except Exception:
                    try:
                        bot.edit_message_text(new_caption, chat_id=chat_id, message_id=mid, reply_markup=new_markup, parse_mode="Markdown")
                    except Exception:
                        show_music_dashboard(chat_id, user_id, message_to_edit=mid)
            else:
                show_music_dashboard(chat_id, user_id, message_to_edit=mid)
        else:
            bot.answer_callback_query(call.id, "⏭️ Antrean lagu sudah selesai atau kosong.", show_alert=True)
            if not is_track_card:
                show_music_dashboard(chat_id, user_id, message_to_edit=mid)

    elif action == "stop":
        call_music_api("/api/stop", method="POST")
        bot.answer_callback_query(call.id, "⏹️ Musik dihentikan")
        if is_track_card:
            stopped_markup = types.InlineKeyboardMarkup(row_width=2)
            stopped_markup.add(
                types.InlineKeyboardButton("☕ Putar Lofi", callback_data="music_cmd:lofi"),
                types.InlineKeyboardButton("🌸 J-Pop Hits", callback_data="music_cmd:jpop")
            )
            stopped_markup.add(
                types.InlineKeyboardButton("🎵 Buka Remote Musik", callback_data="open_music_menu")
            )
            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup=stopped_markup)
            except Exception:
                pass
        else:
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

    elif action == "view_queue":
        bot.answer_callback_query(call.id, "📜 Memuat antrean musik...")
        show_queue_dashboard(chat_id, user_id, message_to_edit=mid)

    elif action == "refresh":
        bot.answer_callback_query(call.id, "🔄 Status diperbarui")
        show_music_dashboard(chat_id, user_id, message_to_edit=mid)


@bot.message_handler(func=lambda msg: True)
def handle_text_messages(message):
    if not is_authorized(message.from_user.id):
        return
    if message.from_user.id in AWAITING_CUSTOM_LANG and AWAITING_CUSTOM_LANG[message.from_user.id]:
        AWAITING_CUSTOM_LANG[message.from_user.id] = False
        lang_input = message.text.strip().title()
        if lang_input:
            norm_key, label = apply_language_choice(lang_input)
            bot.reply_to(
                message,
                f"✨ **Bahasa Berhasil Diubah!**\n\n"
                f"Mulai sekarang aku bakal mengobrol menggunakan bahasa **{label}** yaa sayang~ 🥰💕\n"
                f"Yuk lanjut ngobrol lagi!",
                parse_mode="Markdown"
            )
            return
    if message.from_user.id in USER_PERSONA_WIZARD:
        if handle_persona_wizard_input(message):
            return

    # Direct robust fallback dispatch for all bot commands (handles leading spaces, case, bot username suffix)
    raw_text = (message.text or "").strip()
    first_token = raw_text.split()[0].lower() if raw_text else ""
    if "@" in first_token:
        first_token = first_token.split("@")[0]

    if first_token in ('/outfit', '/wardrobe', '/baju', '/pakaian'):
        handle_outfit_command(message)
        return
    elif first_token in ('/persona', '/karakter'):
        handle_persona(message)
        return
    elif first_token in ('/setup', '/config', '/settings', '/pengaturan'):
        handle_setup(message)
        return
    elif first_token in ('/help', '/bantuan'):
        handle_help(message)
        return
    elif first_token in ('/pap', '/photo', '/foto'):
        handle_photo_command(message)
        return
    elif first_token in ('/video', '/anim', '/animate', '/klip'):
        handle_video_command(message)
        return
    elif first_token in ('/memory', '/memori', '/ingatan'):
        handle_memory_command(message)
        return
    elif first_token in ('/remind', '/reminders', '/pengingat', '/alarm'):
        handle_remind_command(message)
        return
    elif first_token in ('/birthday', '/anniversary', '/ultah', '/jadian'):
        handle_special_dates_command(message)
        return
    elif first_token in ('/love', '/affection', '/cinta'):
        handle_affection_command(message)
        return
    elif first_token in ('/voice', '/suara'):
        handle_voice_command(message)
        return
    elif first_token in ('/language', '/lang', '/bahasa'):
        handle_language_command(message)
        return
    elif first_token in ('/status', '/diagnostik'):
        handle_status(message)
        return
    elif first_token in ('/reset',):
        handle_reset(message)
        return
    elif first_token in ('/play', '/lagu', '/musik', '/music'):
        handle_play_command(message)
        return
    elif first_token in ('/queue', '/antrean', '/antre', '/addsong', '/q'):
        handle_queue_command(message)
        return
    elif first_token in ('/playlist', '/album', '/putarplaylist'):
        handle_playlist_command(message)
        return
    elif first_token in ('/pause',):
        handle_pause_command(message)
        return
    elif first_token in ('/resume',):
        handle_resume_command(message)
        return
    elif first_token in ('/next', '/skip'):
        handle_next_command(message)
        return
    elif first_token in ('/stop',):
        handle_stop_command(message)
        return

    process_text_chat(message, message.text, is_voice=False)


def process_text_chat(message, user_text: str, is_voice: bool = False):
    """Main conversation processor running asynchronously with continuous typing status."""
    def _execute():
        try:
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
                    f"Tenang aja, pas jamnya tiba aku langsung kabarin kamu! Semangat yaa~"
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
                safe_reply_to(message, confirm_msg, reply_markup=markup)
                return

            # Check if user is currently answering a date wizard prompt (Birthday / Anniversary)
            if message.from_user.id in USER_DATE_WIZARD:
                target_field = USER_DATE_WIZARD.pop(message.from_user.id)
                if user_text.lower().strip() in ('batal', 'cancel', 'kembali', 'exit'):
                    safe_reply_to(message, "Pengaturan tanggal dibatalkan.", parse_mode=None)
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
                            f"Pas hari ulang tahunmu tiba, {p_name} bakal siapin ucapan dan foto spesial buat kamu! 🎂"
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
                    safe_reply_to(message, reply_msg, reply_markup=markup)
                    return
                else:
                    USER_DATE_WIZARD[message.from_user.id] = target_field
                    safe_reply_to(
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
                        f"Hari ulang tahunmu tanggal **{label}** ({cd_str}) kan? "
                        f"Aku pasti bakal ingat pas harinya tiba! 🎉"
                    )
                else:
                    anniversary_engine.set_anniversary(message.from_user.id, day, month, year)
                    cd = anniversary_engine.get_countdown(day, month)
                    cd_str = "HARI INI! 🎉" if cd == 0 else f"{cd} hari lagi"
                    conf_msg = (
                        f"💍 **Sip! {p_name} catat ya!** ✨\n\n"
                        f"Tanggal jadian kita **{label}** ({cd_str})! "
                        f"Aku bahagia banget bisa sama kamu sayang, aku bakal selalu rayain hari istimewa kita! 💕"
                    )
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🎂 Buka Menu Hari Spesial", callback_data="open_dates_menu"))
                safe_reply_to(message, conf_msg, reply_markup=markup)
                return

            if user_text.startswith("```python") and user_text.endswith("```"):
                code = user_text.replace("```python", "").replace("```", "").strip()
                with ChatActionLoop(bot, message.chat.id, "typing"):
                    ok, res = CodeRunner.execute_python(code)
                    tag = "✅ Execution Output:" if ok else "❌ Execution Error:"
                    safe_reply_to(message, f"💻 **{tag}**\n```\n{res}\n```")
                return

            persona = persona_mgr.get_active_persona()

            with ChatActionLoop(bot, message.chat.id, "typing"):
                # 1. Proactively ensure LLM is awake (wakes from Smart Idle if sleeping)
                llm_active = idle_engine.ensure_llm_active(bot=bot, chat_id=message.chat.id)
                if not llm_active:
                    logger.warning("Local LLM engine could not be awakened.")
                    return

                # 2. Check if Local LLM backend is online
                stat = llm_client.check_health()
                if not stat.get("online"):
                    health_engine.mark_llm_failure(bot=bot, get_recipients_func=get_notification_recipient_ids, error_msg=stat.get("error"))
                    backend_msg = (
                        "⚠️ *Service LLM Sedang Offline / Belum Siap!*\n\n"
                        f"Otak AI lokal (`{LLM_BASE_URL}`) belum merespon permintaan chat.\n\n"
                        "👉 Coba jalankan layanan dari terminal dengan perintah:\n`waifu start --daemon`\n\n"
                        "Atau klik ganda file `start_services.bat` di folder PC kamu yaa sayang!\n"
                        "Ketik `/status` untuk melihat laporan koneksi lengkap."
                    )
                    safe_reply_to(message, backend_msg)
                    return

                # 3. Record activity for proactive check-ins & learn facts
                proactive_engine.record_user_activity(message.from_user.id)
                memory_engine.auto_extract_facts(user_text, message.from_user.id)

                # 3. Construct system instruction with injected student routine & memory context
                cur_hour = time.localtime().tm_hour
                routine = student_schedule.get_hourly_routine(cur_hour, persona_key=persona_mgr.active_key)
                p_prof = student_schedule.STUDENT_PROFILES.get(persona_mgr.active_key.lower(), student_schedule.STUDENT_PROFILES["runa"])
                
                system_inst = persona.get("system_instruction", "")
                system_inst += (
                    f" KEGIATAN MAHASISWI HARI INI: Jam {cur_hour:02d}:00, kegiatanmu saat ini: {routine['activity_desc']}. "
                    f"Kamu adalah mahasiswi ({p_prof['major']}). "
                    "PANDUAN PENTING: Jawab pesan pasanganmu secara wajar, santai, dan relevan dengan topik serta kehidupan mahasiswimu. "
                    "Jangan lebay, jangan bersikap hiperbola atau teatrikal. Jawab langsung maksimal 1-3 kalimat seperti chat asli.\n"
                    "INISIATIF KIRIM PAP SPONTAN: Kamu boleh sesekali berinisiatif mengirim foto selfie / PAP untuk menunjukkan kegiatan, outfit, atau sekadar memanjakan pacarmu karena kangen! Jika momennya pas, tambahkan tag [ACTION: SEND_PAP] di akhir pesanmu dengan kalimat pacar yang manis dan wajar (misal: 'Lagi rebahan santai nih sayang, kangen kamu deh 💕 [ACTION: SEND_PAP]' atau 'Liat deh penampilanku hari ini, cocok ga buat kamu? 🥰 [ACTION: SEND_PAP]'). DILARANG KERAS bersikap defensif atau sibuk membuktikan keberadaanmu ('biar kamu percaya aku beneran ada di sini', 'nih buktinya', 'biar kamu yakin', 'jangan bohong lagi'). Kamu adalah pacar nyata yang percaya diri, hangat, dan penuh cinta."
                )
                mem_context = memory_engine.format_memory_context(message.from_user.id, query=user_text)
                if mem_context:
                    system_inst += "\n" + mem_context

                history = persona_mgr.get_chat_history(message.from_user.id)

                messages = [{"role": "system", "content": system_inst}]
                messages.extend(history)
                messages.append({"role": "user", "content": user_text})

                try:
                    idle_engine.ensure_llm_active(bot=bot, chat_id=message.chat.id)
                    reply_text, _ = llm_client.chat(messages, max_tokens=150)
                except Exception as e:
                    logger.error(f"Chat error / LLM timeout: {e}")
                    health_engine.mark_llm_failure(bot=bot, get_recipients_func=get_notification_recipient_ids, error_msg=str(e))
                    err_msg = (
                        f"⚠️ *Service LLM Mengalami Gangguan / Timeout!*\n\n"
                        f"Sayang, koneksi ke service LLM lokal (`{LLM_BASE_URL}`) gagal atau tidak merespon: `{e}`\n\n"
                        f"👉 Silakan periksa apakah KoboldCPP hang/crash, atau jalankan `start_services.bat`.\n"
                        f"Ketik `/status` untuk cek kondisi server."
                    )
                    safe_reply_to(message, err_msg)
                    return

                if not reply_text or not reply_text.strip():
                    reply_text = "Aku dengerin kok, lagi mikirin apa nih?"

                # Check if waifu takes initiative to send spontaneous PAP photo
                has_action_tag = bool(re.search(r"\[(ACTION:\s*)?(SEND_PAP|SEND_SELFIE|PAP)\]", reply_text, re.IGNORECASE))
                has_pap_phrase = any(phrase in reply_text.lower() for phrase in [
                    "aku fotoin ya", "aku kirim foto ya", "nih foto spesial buat kamu", "aku pap buat kamu"
                ])

                should_send_photo = has_action_tag or has_pap_phrase

                # Clean action tag from text so user only sees natural dialogue
                clean_reply = re.sub(r"\[(ACTION:\s*)?(SEND_PAP|SEND_SELFIE|PAP)\]", "", reply_text, flags=re.IGNORECASE).strip()
                if not clean_reply:
                    clean_reply = "Lagi kangen banget sama kamu nih sayang 💕"

                new_aff = persona_mgr.increase_affinity(message.from_user.id, delta=1)
                memory_engine.set_affinity(message.from_user.id, new_aff)
                persona_mgr.add_message(message.from_user.id, "user", user_text)
                persona_mgr.add_message(message.from_user.id, "assistant", clean_reply)

                safe_reply_to(message, clean_reply, parse_mode=None)

                if should_send_photo:
                    def _send_spontaneous_photo():
                        try:
                            time.sleep(1.5)  # Natural human pause as if snapping a quick selfie
                            photo_prompt = clean_reply if clean_reply else f"{routine['activity_desc']}"
                            process_photo_request(message, user_text=photo_prompt, is_proof=False)
                        except Exception as e_photo:
                            logger.error(f"Error sending spontaneous photo: {e_photo}")

                    threading.Thread(target=_send_spontaneous_photo, daemon=True).start()

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
                        clean_for_vn = voice_engine.clean_text_for_speech(reply_text)
                        if len(clean_for_vn) > 200:
                            m = re.search(r'^(.*[.!?])\s', clean_for_vn[:220])
                            if m:
                                clean_for_vn = m.group(1)
                            else:
                                clean_for_vn = clean_for_vn[:180].rsplit(' ', 1)[0]

                        vn_path = voice_engine.generate_voice_note(clean_for_vn)
                        if vn_path:
                            try:
                                with open(vn_path, "rb") as vn_file:
                                    bot.send_voice(message.chat.id, vn_file)
                            finally:
                                if os.path.exists(vn_path):
                                    os.remove(vn_path)
                    threading.Thread(target=send_voice, daemon=True).start()

        except Exception as e_proc:
            logger.error(f"Error handling message in process_text_chat: {e_proc}", exc_info=True)
            safe_reply_to(
                message,
                f"⚠️ *Maaf sayang, ada sedikit gangguan saat memproses pesan:*\n`{e_proc}`\n\nKetik `/status` untuk mengecek status bot."
            )

    threading.Thread(target=_execute, daemon=True).start()


def send_scheduled_greeting(user_id: int, time_of_day: str):
    """Sends sweet spontaneous morning/lunch/bedtime greeting."""
    try:
        persona = persona_mgr.get_active_persona()
        cur_lang = os.environ.get("BOT_LANGUAGE", "id").lower()
        lang_dir = persona_mgr.get_language_directive(cur_lang)
        if time_of_day == "morning":
            prompt = f"It is 7:00 AM morning. Write 1-2 sweet, cheerful, affectionate sentences wishing your partner a wonderful productive day. {lang_dir}"
            if cur_lang == "ja":
                fallback = "おはようあなた！今日も一日素敵な日になりますように〜！🥰💕"
                tag = "🌅 *おはよう、あなた！*"
            elif cur_lang == "en":
                fallback = "Good morning sweetheart! Hope your day is filled with joy and smiles~ 🥰"
                tag = "🌅 *Good Morning Sweetheart!*"
            else:
                fallback = "Selamat pagi! Semangat buat hari ini yaa."
                tag = "🌅 *Selamat Pagi!*"
        elif time_of_day == "lunch":
            prompt = f"It is 12:30 PM lunch break. Write 1-2 sweet, cheerful, caring sentences reminding your partner to take a break and eat a delicious lunch. {lang_dir}"
            if cur_lang == "ja":
                fallback = "お昼ご飯の時間だよ！無理せずちゃんと美味しいもの食べてね〜！🍱💕"
                tag = "🍱 *お昼ご飯の時間だよ〜！*"
            elif cur_lang == "en":
                fallback = "Lunch time babe! Remember to take a break and have a delicious meal! 🍱💕"
                tag = "🍱 *Lunch Time Sweetie!*"
            else:
                fallback = "Udah jam makan siang nih! Jangan lupa istirahat sebentar dan makan siang yaa. 🍱"
                tag = "🍱 *Waktunya Makan Siang!*"
        else:
            prompt = f"It is 10:00 PM bedtime. Write 1-2 sweet, gentle, caring sentences reminding your partner to rest, sleep tight, and have sweet dreams. {lang_dir}"
            if cur_lang == "ja":
                fallback = "おやすみなさい、ゆっくり休んでいい夢見てね〜🌙✨"
                tag = "🌙 *おやすみ、あなた！*"
            elif cur_lang == "en":
                fallback = "Good night my love, sleep tight and sweet dreams~ 🌙✨"
                tag = "🌙 *Good Night My Love!*"
            else:
                fallback = "Selamat istirahat yaa, tidur nyenyak."
                tag = "🌙 *Selamat Istirahat!*"

        messages = [
            {"role": "system", "content": persona.get("system_instruction", "")},
            {"role": "user", "content": prompt}
        ]
        try:
            idle_engine.ensure_llm_active()
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
                        f"⏰ *Pengingat dari {p_name}:*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Waktunya tiba nih, tadi kamu minta diingetin:\n\n"
                        f"👉 *{task}*\n\n"
                        f"Jangan lupa dikerjakan yaa, semangat!"
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
                        voice_msg = f"Halo! Waktunya {task}, jangan lupa dikerjakan yaa!"
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

            # Check proactive check-ins for partner when inactive (between 09:00 and 21:30)
            for uid in ALLOWED_USER_IDS:
                if proactive_engine.should_send_checkin(uid):
                    try:
                        persona = persona_mgr.get_active_persona()
                        p_msg = proactive_engine.generate_proactive_message(
                            user_id=uid,
                            persona=persona,
                            persona_key=persona_mgr.active_key,
                            llm_client=llm_client,
                            lang=BOT_LANGUAGE
                        )
                        if p_msg:
                            persona_mgr.add_message(uid, "assistant", p_msg)
                            bot.send_message(uid, p_msg)
                            proactive_engine.mark_proactive_sent(uid)
                            logger.info(f"Dispatched proactive check-in to user {uid}: {p_msg}")

                            u_mode = USER_VOICE_MODES.get(uid, "always" if VOICE_ENABLED else "off")
                            if u_mode == "always" and VOICE_ENABLED and len(p_msg) < 180:
                                vn_path = voice_engine.generate_voice_note(p_msg)
                                if vn_path:
                                    try:
                                        with open(vn_path, "rb") as vf:
                                            bot.send_voice(uid, vf)
                                    finally:
                                        if os.path.exists(vn_path):
                                            os.remove(vn_path)
                    except Exception as e_proact:
                        logger.error(f"Error sending proactive check-in to {uid}: {e_proact}")

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
        types.BotCommand("video", "🎬 Dashboard AI Video & generate video waifu"),
        types.BotCommand("play", "🎵 Putar lagu YouTube di PC"),
        types.BotCommand("queue", "➕ Tambah lagu ke antrean / lihat playlist"),
        types.BotCommand("playlist", "📻 Putar album / playlist lengkap di PC"),
        types.BotCommand("music", "🎶 Remote kontrol pemutar musik PC"),
        types.BotCommand("language", "🌐 Pengaturan bahasa waifu (ID, EN, JA, Kustom)"),
        types.BotCommand("outfit", "👗 Lemari pakaian & ganti baju"),
        types.BotCommand("persona", "🎭 Ganti waifu (Runa, Akira, Hina, Shiro, Yume)"),
        types.BotCommand("newpersona", "🎭 Buat waifu kustom baru"),
        types.BotCommand("ratio", "📐 Ganti rasio foto (3:4, 9:16, 1:1, 4:3)"),
        types.BotCommand("quality", "✨ Atur kualitas foto (Ultra/High/Fast)"),
        types.BotCommand("voice", "🎙️ Pengaturan balasan suara / VN"),
        types.BotCommand("video_engine", "🎬 Dashboard AI Video Engine (Wan 2.1 / AnimateDiff)"),
        types.BotCommand("love", "💖 Cek skor cinta & status hubungan"),
        types.BotCommand("greetings", "⏰ Toggle sapaan harian (Pagi, Siang, Malam)"),
        types.BotCommand("chatting", "💬 Toggle inisiatif chat duluan dari waifu"),
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

    # Startup ready notification worker (runs concurrently so polling starts immediately)
    if STARTUP_NOTIFICATION_ENABLED:
        def _startup_worker():
            recipients = get_notification_recipient_ids()
            if recipients:
                health_engine.notify_startup_ready(
                    bot=bot,
                    recipients=recipients,
                    persona=persona,
                    max_wait_seconds=12
                )
        threading.Thread(target=_startup_worker, daemon=True).start()

    # Start periodic service health monitor
    health_engine.start_monitor(bot=bot, get_recipients_func=get_notification_recipient_ids)

    # Start Smart Idle & Dynamic Power Saver monitor
    if idle_engine.enabled:
        idle_engine.start()

    stat = llm_client.check_health()
    if stat.get("online"):
        logger.info(f"✓ Local LLM is ONLINE ({stat.get('backend')} - {stat.get('model')})")
    else:
        logger.warning(f"⚠️ Local LLM is OFFLINE: {stat.get('error')}")

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=False)
        except Exception as e:
            logger.error(f"Telegram polling loop error: {e}. Reconnecting in 3 seconds...")
            time.sleep(3)


if __name__ == "__main__":
    main()

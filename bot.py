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
from routing_engine import get_hybrid_llm_client, detect_nsfw_intent
from persona_manager import PersonaManager, build_custom_persona
from media_engine import MediaEngine
from voice_engine import VoiceEngine
from code_runner import CodeRunner
from memory_engine import MemoryEngine
from reminder_engine import ReminderEngine
from anniversary_engine import AnniversaryEngine
from story_engine import StoryEngine
from project_manager import get_project_manager
from computer_use_engine import get_computer_use_engine
from coding_engine import get_coding_engine

project_manager = get_project_manager()
computer_use_engine = get_computer_use_engine()
coding_engine = get_coding_engine()
from project_intent_router import get_project_intent_router
from project_vault import get_project_vault
from project_runner import get_project_runner
project_intent_router = get_project_intent_router()
project_runner = get_project_runner()
AWAITING_PROJECTS_DIR: dict = {}
import asset_manager
from health_engine import HealthEngine, is_port_listening
from idle_engine import IdleEngine
from scheduled_buffer import scheduled_buffer
from pending_message_manager import get_pending_message_manager
pending_manager = get_pending_message_manager()
from waifu_status_tracker import get_waifu_status_tracker
waifu_status_tracker = get_waifu_status_tracker()
from hangout_engine import get_hangout_engine
hangout_engine = get_hangout_engine()
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

llm_client = get_hybrid_llm_client()
persona_mgr = PersonaManager(active_key=DEFAULT_PERSONA)
media_engine = MediaEngine(comfyui_url=COMFYUI_URL, allow_cloud_fallback=MEDIA_FALLBACK)
memory_engine = MemoryEngine()
reminder_engine = ReminderEngine()
anniversary_engine = AnniversaryEngine()
story_engine = StoryEngine()
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


def format_roleplay_italics(text: str, character_name: Optional[str] = None) -> str:
    """
    Formats roleplay actions into elegant Visual Novel stage directions (_character_action_),
    cleanly separated from spoken dialogue by a double newline, without awkward hyphens/dashes,
    while preserving double-asterisk bold (**bold**) and inline code blocks (`code`).
    Example: "*tersenyum sambil merapikan buku* Ini tugasnya..."
         -> "_Runa tersenyum sambil merapikan buku_\n\nIni tugasnya..."
    """
    if not text:
        return text

    char_name = character_name
    if not char_name:
        try:
            char_name = persona_mgr.get_active_persona().get("name", "Runa")
        except Exception:
            char_name = "Runa"

    # 1. Normalize line-based dash actions like: - kulihatmu dengan senyuman hangat, merapikan rambutku -
    text = re.sub(r'(?m)^[-—~]\s*([^-\n]+?)\s*[-—~]$', r'*\1*', text)

    # 2. Normalize existing dashes, dialogue attribution tags, or parentheses around action cues
    text = re.sub(r'[-—~]\s*[*_]([^*_\n]+?)[*_]\s*[-—~]', r'*\1*', text)
    text = re.sub(r'(?i)(?:,\s*)?(?:ia|dia)\s+(?:menyebutkan|berkata|menjawab|berbisik|menimpali)\s*:\s*[-—~]?', ' ', text)
    text = re.sub(
        r'(?i)\(((?:tersenyum|tersipu|tertawa|merapikan|menatap|menghela|melirik|berbisik|memegang|menggenggam|mengusap|memeluk|duduk|berdiri|sambil)[^)]+)\)',
        r'*\1*',
        text
    )

    # 3. Clean up and format the action into Visual Novel narration
    def _clean_action(content: str) -> str:
        content = content.strip(' -—~')
        # Remove dialogue attribution inside action tags (e.g. *ia menyebutkan: -*)
        content = re.sub(r'(?i)(?:,\s*)?(?:ia|dia)\s+(?:menyebutkan|berkata|menjawab|berbisik|menimpali)\s*:\s*[-—~]?', '', content)
        # Convert first-person action verbs to natural verbs
        content = re.sub(r'\bkulihatmu\b', 'melihat kamu', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkulihat\s+kamu\b', 'melihat kamu', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkudekati\b', 'mendekati', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkupegang\b', 'memegang', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkugenggam\b', 'menggenggam', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkupeluk\b', 'memeluk', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkusentuh\b', 'menyentuh', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkuelus\b', 'mengelus', content, flags=re.IGNORECASE)
        content = re.sub(r'\bkutarik\b', 'menarik', content, flags=re.IGNORECASE)
        # Flow improvement: ", merapikan" -> " sambil merapikan"
        content = re.sub(r',\s*merapikan\b', ' sambil merapikan', content, flags=re.IGNORECASE)
        # Convert first-person possessives to third-person for VN narration
        content = re.sub(r'\brambutku\b', 'rambutnya', content, flags=re.IGNORECASE)
        content = re.sub(r'\btanganku\b', 'tangannya', content, flags=re.IGNORECASE)
        content = re.sub(r'\bmataku\b', 'matanya', content, flags=re.IGNORECASE)
        content = re.sub(r'\bwajahku\b', 'wajahnya', content, flags=re.IGNORECASE)
        content = re.sub(r'\bbibirku\b', 'bibirnya', content, flags=re.IGNORECASE)
        content = re.sub(r'\bpipiku\b', 'pipinya', content, flags=re.IGNORECASE)
        content = re.sub(r'\bbajuku\b', 'bajunya', content, flags=re.IGNORECASE)
        content = re.sub(r'\btubuhku\b', 'tubuhnya', content, flags=re.IGNORECASE)
        # Convert third-person pronouns to character name
        content = re.sub(r'\b(?:ia|dia)\b', char_name, content, flags=re.IGNORECASE)

        # If not already starting with char_name, check if we should prepend char_name
        non_char = ['suara', 'angin', 'hujan', 'lampu', 'musik', 'suasana', 'hp', 'ponsel', 'notifikasi', 'pintu', 'gelas', 'waktu', 'hari']
        first_word = content.split()[0].lower() if content.split() else ''
        if not re.match(r'^(?:' + re.escape(char_name) + r')\b', content, re.IGNORECASE) and first_word not in non_char:
            content = f'{char_name} {content}'

        return content.strip(' -—~')

    def _vn_replace(m):
        c = _clean_action(m.group(1))
        return f'_{c}_'

    # 4. Add visual separation (double newline) around roleplay *action* blocks (strictly single asterisk)
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)[ \t]*([^\n*])', r'*\1*\n\n\2', text)
    text = re.sub(r'([^\n*])[ \t]*(?<!\*)\*([^*\n]+?)\*(?!\*)', r'\1\n\n*\2*', text)
    # Normalize excessive newlines to at most 2
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    # 5. Convert single *action* into Telegram Markdown italic: _action_
    def _convert_segment(seg: str) -> str:
        return re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', _vn_replace, seg)

    if "`" in text:
        parts = re.split(r'(`[^`]+`)', text)
        for i in range(len(parts)):
            if not parts[i].startswith("`"):
                parts[i] = _convert_segment(parts[i])
        return "".join(parts)
    return _convert_segment(text)


# --- Telegram Safe Messaging Helpers ---

def safe_reply_to(message, text, reply_markup=None, parse_mode="Markdown"):
    """
    Safely replies to a message with automatic Markdown fallback to plain text
    if Telegram API rejects parsing entities (400 Bad Request).
    In plain text fallback, restores *action* asterisks so roleplay actions remain readable.
    """
    try:
        return bot.reply_to(message, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"safe_reply_to failed with {parse_mode=}: {e}. Retrying as plain text.")
        try:
            # Preserve action markers as *action* in plain text instead of erasing them
            clean_text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'*\1*', text)
            clean_text = clean_text.replace("`", "")
            return bot.reply_to(message, clean_text, reply_markup=reply_markup)
        except Exception as e2:
            logger.error(f"Fatal error in safe_reply_to: {e2}")
            return None


def safe_send_message(chat_id: int, text: str, reply_markup=None, parse_mode="Markdown"):
    """
    Safely sends a message to chat_id with automatic Markdown fallback to plain text.
    In plain text fallback, restores *action* asterisks so roleplay actions remain readable.
    """
    try:
        return bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"safe_send_message failed with {parse_mode=}: {e}. Retrying as plain text.")
        try:
            clean_text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'*\1*', text)
            clean_text = clean_text.replace("`", "")
            return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
        except Exception as e2:
            logger.error(f"Fatal error in safe_send_message: {e2}")
            return None


def send_long_chat_message(
    chat_id: int,
    text: str,
    reply_to_id: Optional[int] = None,
    parse_mode: str = "Markdown",
    max_chunk_size: int = 3800,
    reply_markup: Optional[Any] = None
) -> List[Any]:
    """
    Safely sends long messages to chat_id, automatically splitting text that
    exceeds Telegram's 4096-character limit into clean chunks without breaking paragraphs.
    Falls back gracefully from Markdown to plain text if parsing errors occur.
    Also auto-linkifies localhost URLs into 127.0.0.1 so Telegram clients render clickable hyperlinks.
    """
    if not text:
        return []

    # Auto-linkify localhost into 127.0.0.1 for Telegram client clickable link support
    text = re.sub(r'https?://localhost(?=[:/])', lambda m: m.group(0).replace('localhost', '127.0.0.1'), text)

    sent_messages = []
    # If text fits inside limit, send directly
    if len(text) <= max_chunk_size:
        try:
            msg = bot.send_message(
                chat_id,
                text,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_id,
                reply_markup=reply_markup
            )
            return [msg]
        except Exception as e_md:
            logger.warning(f"send_long_chat_message single markdown send failed: {e_md}. Retrying as plain text.")
            try:
                clean_text = text.replace("*", "").replace("_", "").replace("`", "")
                msg = bot.send_message(
                    chat_id,
                    clean_text,
                    reply_to_message_id=reply_to_id,
                    reply_markup=reply_markup
                )
                return [msg]
            except Exception as e_plain:
                logger.error(f"send_long_chat_message failed: {e_plain}")
                return []

    # Split text into chunks respecting paragraphs / newlines
    chunks = []
    current_chunk = []
    current_len = 0

    lines = text.split("\n")
    for line in lines:
        line_len = len(line) + 1  # include newline
        if current_len + line_len > max_chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # Send each chunk sequentially
    first = True
    total_chunks = len(chunks)
    for idx, chunk in enumerate(chunks):
        r_id = reply_to_id if first else None
        first = False
        is_last = (idx == total_chunks - 1)
        chunk_markup = reply_markup if is_last else None
        try:
            m = bot.send_message(chat_id, chunk, parse_mode=parse_mode, reply_to_message_id=r_id, reply_markup=chunk_markup)
            if m:
                sent_messages.append(m)
        except Exception as e_chk:
            logger.warning(f"Chunk markdown send failed: {e_chk}. Retrying as plain text.")
            try:
                clean_chunk = chunk.replace("*", "").replace("_", "").replace("`", "")
                m = bot.send_message(chat_id, clean_chunk, reply_to_message_id=r_id, reply_markup=chunk_markup)
                if m:
                    sent_messages.append(m)
            except Exception as e_cplain:
                logger.error(f"Failed sending plain chunk: {e_cplain}")
                if m:
                    sent_messages.append(m)
            except Exception as e_chk_plain:
                logger.error(f"Failed to send chunk: {e_chk_plain}")
        time.sleep(0.3)  # Respect Telegram rate limits

    return sent_messages


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


def reload_env_configurations():
    """Hot-reloads modified variables from .env into global state and engines."""
    global VOICE_NAME, BOT_LANGUAGE, VOICE_ENABLED
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return

    new_vars = {}
    try:
        from dotenv import dotenv_values
        new_vars = dotenv_values(env_path)
    except Exception:
        pass

    if not new_vars:
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        new_vars[k.strip()] = v.strip().strip("'\"")
        except Exception:
            return

    # 1. Voice Name & Speaker
    if "VOICE_NAME" in new_vars:
        new_v = (new_vars["VOICE_NAME"] or "").strip()
        if new_v and new_v != VOICE_NAME:
            logger.info(f"🔄 [Hot-Reload] VOICE_NAME updated: '{VOICE_NAME}' -> '{new_v}'")
            VOICE_NAME = new_v
            if voice_engine:
                voice_engine.default_voice = new_v

    # 2. Voice Backend
    if "VOICE_BACKEND" in new_vars:
        new_vb = (new_vars["VOICE_BACKEND"] or "").strip().lower()
        if voice_engine and getattr(voice_engine, "voice_backend", "") != new_vb:
            logger.info(f"🔄 [Hot-Reload] VOICE_BACKEND updated -> '{new_vb}'")
            voice_engine.voice_backend = new_vb

    # 3. Bot Language
    if "BOT_LANGUAGE" in new_vars:
        new_lang = (new_vars["BOT_LANGUAGE"] or "").strip()
        if new_lang and new_lang != BOT_LANGUAGE:
            logger.info(f"🔄 [Hot-Reload] BOT_LANGUAGE updated: '{BOT_LANGUAGE}' -> '{new_lang}'")
            BOT_LANGUAGE = new_lang
            os.environ["BOT_LANGUAGE"] = new_lang

    # 4. Engine & Model Settings
    for k in ("AI_ENGINE_MODE", "SFW_LLM_PROVIDER", "SFW_IMAGE_ENGINE", "COMFYUI_CHECKPOINT", "DEFAULT_PERSONA", "VIDEO_ENGINE"):
        if k in new_vars and new_vars[k]:
            os.environ[k] = new_vars[k].strip()


def start_env_hot_reload_watcher():
    """Watches .env file for changes and hot-reloads configuration in memory without disconnecting."""
    def _watch():
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if not os.path.exists(env_path):
            return
        last_mtime = os.path.getmtime(env_path)
        while True:
            time.sleep(2.0)
            try:
                if not os.path.exists(env_path):
                    continue
                curr_mtime = os.path.getmtime(env_path)
                if curr_mtime > last_mtime:
                    last_mtime = curr_mtime
                    reload_env_configurations()
            except Exception as e:
                logger.debug(f"Env watcher check error: {e}")

    threading.Thread(target=_watch, daemon=True).start()
    logger.info("✓ Configuration Hot-Reload watcher active (.env watcher)")


def apply_llm_choice(choice: str) -> str:
    global LLM_BASE_URL
    detected_llms = scan_local_llm_models()
    if choice in ("huihui", "qwythos", "qwythos_9b"):
        new_base = "http://127.0.0.1:5001/v1"
        new_model = "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
        label = "Huihui-Qwythos 9B (KoboldCPP Uncensored)"
        update_env_variable("LOCAL_LLM_MODEL", new_model)
        update_env_variable("NSFW_LLM_MODEL", new_model)
        update_env_variable("LLM_MODEL", new_model)
    elif choice in ("qwen", "qwen25", "qwen2.5", "qwen25_7b"):
        new_base = "http://127.0.0.1:5001/v1"
        new_model = "Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf"
        label = "Qwen2.5-7B-Instruct-Abliterated (KoboldCPP)"
        update_env_variable("LOCAL_LLM_MODEL", new_model)
        update_env_variable("NSFW_LLM_MODEL", new_model)
        update_env_variable("LLM_MODEL", new_model)
    elif choice in ("stheno", "stheno_8b"):
        new_base = "http://127.0.0.1:5001/v1"
        new_model = "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf"
        label = "L3-8B-Stheno-v3.4 (KoboldCPP)"
        update_env_variable("LOCAL_LLM_MODEL", new_model)
        update_env_variable("NSFW_LLM_MODEL", new_model)
        update_env_variable("LLM_MODEL", new_model)
    elif choice == "kobold" or choice == "auto":
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
    elif choice.endswith(".gguf"):
        new_base = "http://127.0.0.1:5001/v1"
        new_model = choice
        label = f"{choice.replace('.gguf', '')} (KoboldCPP)"
        update_env_variable("LOCAL_LLM_MODEL", new_model)
        update_env_variable("NSFW_LLM_MODEL", new_model)
    elif choice.isdigit() and int(choice) < len(detected_llms):
        source, mname, mpath = detected_llms[int(choice)]
        if source == "KoboldCPP":
            new_base = "http://127.0.0.1:5001/v1"
            update_env_variable("LOCAL_LLM_MODEL", mname)
            update_env_variable("NSFW_LLM_MODEL", mname)
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
    try:
        llm_client.base_url = new_base
        llm_client.model = new_model
    except Exception:
        pass
    update_env_variable("LLM_BASE_URL", new_base)
    update_env_variable("LLM_MODEL", new_model)
    try:
        get_hybrid_llm_client(force_reload=True)
    except Exception:
        pass
    return label


def apply_ckpt_choice(choice: str) -> str:
    global COMFYUI_URL, MEDIA_FALLBACK
    detected_ckpts = scan_image_models()
    if choice == "agy":
        os.environ["SFW_IMAGE_ENGINE"] = "agy"
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"
        os.environ["MEDIA_FALLBACK_CLOUD"] = "false"
        update_env_variable("SFW_IMAGE_ENGINE", "agy")
        update_env_variable("MEDIA_FALLBACK_AGY", "true")
        update_env_variable("MEDIA_FALLBACK_CLOUD", "false")
        return "Google Antigravity (AGY Image Generator)"
    else:
        os.environ["SFW_IMAGE_ENGINE"] = "cloud" if choice == "cloud" else ("disabled" if choice == "disabled" else "comfyui")
        update_env_variable("SFW_IMAGE_ENGINE", os.environ["SFW_IMAGE_ENGINE"])

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
        "jenny": "en-US-JennyNeural",
        "auto": "auto"
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
                f"💖 **Halo! Aku {name}** 👋🥰\n"
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
        "• 📖 **Cerita & Episode Harian**: Alur kisah hidup waifu hari ini (`/story`)!\n"
        "• 📸 **Kirim Selfie & Foto**: Cukup ketik *'pap foto dong'* atau `/pap` untuk membuka menu pose interaktif!\n"
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
        full_text = f"💖 **Halo! Aku {name}** 👋🥰\n\n" + guide_text
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

    outfit_det = persona_mgr.get_user_outfit_details(user_id)
    cur_outfit_name = outfit_det["name"]

    cur_llm_mode = os.environ.get("AI_ENGINE_MODE", "unified").lower().strip()
    if cur_llm_mode in ("split", "hybrid"):
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "local").upper()
        nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "local").upper()
        cur_llm = f"Split ({sfw_p}/{nsfw_p})"
    else:
        cur_llm = os.environ.get("LLM_MODEL", "default")
        if cur_llm == "default" or not cur_llm:
            cur_llm = "Auto-detect (Locally Uncensored)"
        elif len(cur_llm) > 28:
            cur_llm = cur_llm[:25] + "..."

    cur_img_mode = os.environ.get("IMAGE_ENGINE_MODE", "unified").lower().strip()
    if cur_img_mode in ("split", "hybrid"):
        sfw_e = os.environ.get("SFW_IMAGE_ENGINE", "agy").lower()
        sfw_lbl = "AGY" if sfw_e == "agy" else ("Cloud" if sfw_e == "cloud" else "ComfyUI")
        nsfw_c = os.environ.get("NSFW_COMFYUI_CHECKPOINT", "aom3").lower()
        nsfw_lbl = "AOM3" if any(k in nsfw_c for k in ["aom", "orange"]) else ("MeinaMix" if "meina" in nsfw_c else "ComfyUI")
        cur_ckpt = f"Split ({sfw_lbl}/{nsfw_lbl})"
    else:
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
        f"🗣️ **Voice TTS**  : `{('VoiceStudio (' + persona.get('name', 'Local') + ')') if os.environ.get('VOICE_BACKEND', 'edge-tts').lower().strip() in ('voicestudio', 'local') else voice_engine.default_voice}`\n"
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
        types.InlineKeyboardButton("💻 Workspace (/projects)", callback_data="cfg_submenu:projects"),
        types.InlineKeyboardButton("🖥️ Computer Use (/desktop)", callback_data="cfg_submenu:desktop"),
        types.InlineKeyboardButton("🎭 Ganti Persona", callback_data="open_persona_menu"),
        types.InlineKeyboardButton("💖 Kencan & Hangout (/hangout)", callback_data="open_hangout_menu"),
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
        f"Halo! Aku siap jadi teman dan asisten pribadi yang selalu perhatian. Begitu waktunya tiba, "
        f"aku bakal langsung kirim chat buat ingetin kamu!\n\n"
        f"📋 **Daftar Pengingat Aktif ({len(active_reminders)})**:\n"
        + "\n".join(lines) + "\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **Cara Pasang Pengingat:**\n"
        f"1. **Langsung di Obrolan Santai:**\n"
        f"   • _'tolong ingetin aku 30 menit lagi meeting ya'_\n"
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
                f"⏰ **Siap, {p_name} sudah pasang alarm ya!** 🥰\n\n"
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
                f"Oke, istirahat sejenak dulu yaa. Nanti ({updated.get('remind_time_str')}) aku bakal ingetin kamu lagi! ✨"
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
        f"Tanggal-tanggal istimewa kita selalu aku simpan rapi di memori. "
        f"Saat harinya tiba, aku bakal ucapin dan siapin foto spesial buat kamu!\n\n"
        f"🎈 **Tanggal Ulang Tahun Kamu**:\n"
        f"  {b_line}\n\n"
        f"💐 **Tanggal Anniversary / Jadian Kita**:\n"
        f"  {a_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Kamu juga bisa langsung ngobrol santai seperti:_\n"
        f"• _'ultahku tanggal 15 Agustus 1998 lho'_\n"
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

        persona_mgr.add_message(user_id, "assistant", caption_msg)

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
                    f"Saat harinya tiba, siap-siap dapat ucapan spesial dari aku yaa! ✨",
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
            "🎂 **Kapan Hari Ulang Tahun Kamu?** 🥰\n\n"
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
            "💍 **Kapan Tanggal Anniversary / Momen Spesial Kita?** 🥰\n\n"
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
            f"  - Nama & panggilan (*'namaku Adens'*, *'panggil aku [nama]'*)\n"
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
            f"  - _'tolong ingetin aku 30 menit lagi meeting kantor ya'_\n"
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
            f"  - **Ngobrol Santai**: Cukup ketik _'ultahku 15 Agustus 1998 lho'_ atau _'hari jadian kita 24 Oktober 2024'_.\n"
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
            f"• 💬 **Chat & Obrolan**: Ngobrol santai, bertukar cerita, dan bangun keakraban.\n"
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
            f"`/hangout` - Kencan & hangout berdua (kafe, bioskop, kosan, dll)\n"
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


def show_projects_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders interactive projects & workspace directory selection menu with Tailscale server integration."""
    curr_proj = project_manager.get_active_project(user_id)
    curr_path = project_manager.get_active_project_path(user_id)
    root_dir = project_manager.get_projects_root_dir()
    projs = project_manager.list_projects()
    running_map = project_runner.list_running()

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for p_name in projs.keys():
        is_cur = (p_name == curr_proj)
        is_run = (p_name in running_map)
        badge = "🟢 " if is_run else ("✅ " if is_cur else "📁 ")
        label = f"{badge}{p_name}"
        buttons.append(types.InlineKeyboardButton(label, callback_data=f"select_proj:{p_name}"))
    markup.add(*buttons)

    # Server control button for current project
    if curr_proj in running_map:
        srv_entry = running_map[curr_proj]
        markup.add(
            types.InlineKeyboardButton(f"🛑 Stop Server (Port {srv_entry['port']})", callback_data=f"srv_stop:{curr_proj}"),
            types.InlineKeyboardButton("📄 Cek Log Server", callback_data=f"srv_logs:{curr_proj}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("🚀 Jalankan Server & Buka Port (Tailscale)", callback_data=f"srv_run:{curr_proj}")
        )

    markup.add(
        types.InlineKeyboardButton("➕ Buat Project Baru (/spawn)", callback_data="proj_action:spawn"),
        types.InlineKeyboardButton("📂 Ganti Root Folder", callback_data="proj_action:set_root")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Status Server Tailscale", callback_data="proj_action:server_status"),
        types.InlineKeyboardButton("🖥️ Status Desktop (/desktop)", callback_data="proj_action:desktop")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard")
    )

    srv_status_text = ""
    if curr_proj in running_map:
        srv = running_map[curr_proj]
        srv_status_text = (
            f"🚀 **Dev Server** : 🟢 **Running** (Port `{srv['port']}`, PID `{srv['pid']}`)\n"
            f"🌐 **Tailscale**  : {srv.get('tailscale_url') or 'N/A'}\n"
            f"📱 **MagicDNS**   : {srv.get('magic_dns_url') or 'N/A'}\n"
        )
    else:
        srv_status_text = "🚀 **Dev Server** : ⚪ Offline (Klik tombol di bawah untuk start)\n"

    text = (
        f"💻 **Manajemen Workspace & Project Coding**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Project Aktif** : **{curr_proj}**\n"
        f"📂 **Lokasi Folder** : `{curr_path}`\n"
        f"🏠 **Root Directory**: `{root_dir}`\n"
        f"{srv_status_text}\n"
        f"Pilih project di atas untuk beralih workspace, atau jalankan server agar port bisa dibuka dan diakses dari HP kamu via Tailscale!\n\n"
        f"💡 _Tugas coding, file, dan terminal dari waifu dijalankan di dalam folder project aktif._"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


def show_desktop_status_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders status and options for Computer Use via Vercel agent-desktop."""
    cu = get_computer_use_engine()
    status = cu.get_status()
    is_avail = cu.is_available()
    plat = status.get("data", {}).get("platform", sys.platform)
    perm = status.get("data", {}).get("permissions", {}).get("accessibility", {}).get("state", "unknown")
    def_prof = cu.get_default_browser_profile()
    if not def_prof or def_prof.lower() == "ask":
        prof_display = "🤖 _Selalu Tanya di Chat_"
    else:
        all_p = cu.list_browser_profiles()
        matched = next((p["name"] for p in all_p if p["folder"] == def_prof), def_prof)
        prof_display = f"🌐 `{matched}` (`{def_prof}`)"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 Screenshot Layar", callback_data="desktop_act:screenshot"),
        types.InlineKeyboardButton("📱 Cek Aplikasi", callback_data="desktop_act:apps")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Profil Browser (/profiles)", callback_data="desktop_act:profiles"),
        types.InlineKeyboardButton("💻 Menu Projects", callback_data="cfg_submenu:projects")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 Menu Setup", callback_data="cfg_submenu:dashboard")
    )

    text = (
        f"🖥️ **Computer Use & Desktop Control (agent-desktop)**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• Status Adapter : {'🟢 Active & Ready' if is_avail else '🔴 Not Found'}\n"
        f"• Platform       : `{plat}`\n"
        f"• Accessibility  : `{perm}`\n"
        f"• Engine         : `agent-desktop (Native Accessibility Tree)`\n"
        f"• Default Browser: {prof_display}\n\n"
        f"Waifu bisa melihat layar desktop, membuka aplikasi, mengklik elemen UI, "
        f"dan membantu pekerjaanmu secara real-time!\n\n"
        f"💡 _Ketik `/screen` untuk screenshot instan atau chat langsung (misal: 'tolong screenshot layar pc' atau 'buka instagram')._"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


def show_browser_profiles_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders menu to select or inspect browser profiles (Chrome, Edge, Brave)."""
    cu = get_computer_use_engine()
    profiles = cu.list_browser_profiles()
    cur_def = cu.get_default_browser_profile()

    markup = types.InlineKeyboardMarkup(row_width=1)

    # Option for Always Ask
    is_ask_selected = (not cur_def or cur_def.lower() == "ask")
    ask_label = f"{'✅ ' if is_ask_selected else ''}🤖 Selalu Tanya di Chat (Interaktif)"
    markup.add(types.InlineKeyboardButton(ask_label, callback_data="bprof_set:ask"))

    # Profile buttons
    for p in profiles:
        is_sel = (cur_def and (cur_def.lower() == p["folder"].lower() or cur_def.lower() == p["name"].lower()))
        b_icon = "🌐" if "chrome" in p["browser"].lower() else ("🌊" if "edge" in p["browser"].lower() else "🦁")
        email_str = f" ({p['email']})" if p.get("email") else ""
        btn_text = f"{'✅ ' if is_sel else ''}{b_icon} {p['name']} [{p['browser']}]{email_str}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"bprof_set:{p['folder']}"))

    markup.add(
        types.InlineKeyboardButton("🖥️ Kembali ke Desktop", callback_data="cfg_submenu:desktop"),
        types.InlineKeyboardButton("🔙 Menu Setup", callback_data="cfg_submenu:dashboard")
    )

    cur_label = "🤖 Selalu Tanya di Chat" if is_ask_selected else cur_def
    text = (
        f"🌐 **Manajemen Profil Browser Desktop**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Waifu otomatis mendeteksi profil Chromium (Chrome, Edge, Brave) di PC kamu.\n\n"
        f"• **Profil Default**: `{cur_label}`\n"
        f"• **Total Terdeteksi**: {len(profiles)} profil\n\n"
        f"💡 _Pilih salah satu profil di bawah sebagai default, atau pilih 'Selalu Tanya' agar Waifu menanyakan profil saat chat._"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


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
    cur_mode = os.environ.get("AI_ENGINE_MODE", "unified").lower().strip()
    is_split = (cur_mode in ("split", "hybrid"))
    sfw_p = os.environ.get("SFW_LLM_PROVIDER", "local").lower().strip()
    sfw_m = os.environ.get("SFW_LLM_MODEL", os.environ.get("LLM_MODEL", "default"))
    nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "local").lower().strip()
    nsfw_m = os.environ.get("NSFW_LLM_MODEL", "default")
    cur_llm = os.environ.get("LLM_MODEL", "default")
    cur_base = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:5001/v1")
    detected = scan_local_llm_models()

    markup = types.InlineKeyboardMarkup(row_width=1)

    # 1. Mode Selector Toggle
    mode_toggle_label = "🔀 Mode: Split Hybrid (Aktif) ➔ Ganti Unified" if is_split else "🤖 Mode: Unified (Aktif) ➔ Ganti Split Hybrid"
    markup.add(types.InlineKeyboardButton(mode_toggle_label, callback_data="cfg_toggle_split_mode"))

    if is_split:
        # SFW Providers section
        markup.add(types.InlineKeyboardButton("─── 🌸 PROVIDER CHAT SFW ───", callback_data="noop"))
        markup.add(types.InlineKeyboardButton(f"🌉 Google Antigravity Bridge (AGY) {'✓' if sfw_p == 'agy' else ''}", callback_data="cfg_set_sfw_p:agy"))
        markup.add(types.InlineKeyboardButton(f"⚡ Groq Cloud (Llama 3.3 70B - Kilat) {'✓' if sfw_p == 'groq' else ''}", callback_data="cfg_set_sfw_p:groq"))
        markup.add(types.InlineKeyboardButton(f"🤖 OpenAI Cloud (GPT-4o-mini) {'✓' if sfw_p == 'openai' else ''}", callback_data="cfg_set_sfw_p:openai"))
        markup.add(types.InlineKeyboardButton(f"🧠 DeepSeek Cloud (deepseek-chat) {'✓' if sfw_p == 'deepseek' else ''}", callback_data="cfg_set_sfw_p:deepseek"))
        markup.add(types.InlineKeyboardButton(f"🏠 Local KoboldCPP (Lokal PC) {'✓' if sfw_p == 'local' else ''}", callback_data="cfg_set_sfw_p:local"))

        # NSFW Providers section
        markup.add(types.InlineKeyboardButton("─── 🔞 PROVIDER CHAT NSFW ───", callback_data="noop"))
        markup.add(types.InlineKeyboardButton(f"🔞 Local KoboldCPP Uncensored {'✓' if nsfw_p == 'local' else ''}", callback_data="cfg_set_nsfw_p:local"))
        has_huihui_split = any("huihui" in mname.lower() or "qwythos" in mname.lower() for _, mname, _ in detected)
        if not has_huihui_split:
            markup.add(types.InlineKeyboardButton("📥 Unduh & Pilih Huihui-Qwythos 9B (~5.5 GB • 100% Uncensored)", callback_data="cfg_set_llm:huihui_auto"))
        markup.add(types.InlineKeyboardButton(f"☁️ OpenRouter Uncensored {'✓' if nsfw_p == 'openrouter_uncensored' else ''}", callback_data="cfg_set_nsfw_p:openrouter_uncensored"))
    else:
        is_kobold = ("5001" in cur_base)
        markup.add(types.InlineKeyboardButton(f"🤖 KoboldCPP (Port 5001 - Auto-start) {'✓' if is_kobold else ''}", callback_data="cfg_set_llm:kobold"))

        has_huihui = any("huihui" in mname.lower() or "qwythos" in mname.lower() for _, mname, _ in detected)
        if not has_huihui:
            markup.add(types.InlineKeyboardButton("📥 Unduh & Pilih Huihui-Qwythos 9B (~5.5 GB • Default Uncensored)", callback_data="cfg_set_llm:huihui_auto"))

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

    if is_split:
        text = (
            f"🧠 **Pengaturan Arsitektur Chat: Split Hybrid**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Status Arsitektur: `🔀 Split Hybrid (Terpisah Otomatis)`\n"
            f"• **Otak SFW**  : `{sfw_p.upper()}` (`{sfw_m}`)\n"
            f"• **Otak NSFW** : `{nsfw_p.upper()}` (`{nsfw_m}`)\n\n"
            f"💡 _Setiap pesan chat otomatis dianalisis:_\n"
            f"  - Obrolan santai, kuliah, dan coding dialihkan ke **SFW Provider**.\n"
            f"  - Momen mesra, roleplay intim & 18+ dialihkan ke **NSFW Uncensored**.\n"
            f"  - Akun cloud aman dari risiko blokir/sensor!"
        )
    else:
        text = (
            f"🧠 **Pengaturan Arsitektur Chat: Unified Mode**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Status Arsitektur: `🤖 Unified (1 Provider untuk Semua)`\n"
            f"• Model Aktif : `{cur_llm}`\n"
            f"• Endpoint API: `{cur_base}`\n\n"
            f"Pilih model obrolan lokal atau klik tombol di atas untuk beralih ke Mode Split Hybrid:"
        )

    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


def show_photo_engine_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None):
    cur_mode = os.environ.get("IMAGE_ENGINE_MODE", "unified").lower().strip()
    is_split = (cur_mode in ("split", "hybrid"))
    cur_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "")
    cur_url = os.environ.get("COMFYUI_URL", "")
    cur_cloud = os.environ.get("MEDIA_FALLBACK_CLOUD", "false").lower() in ("true", "1")
    sfw_img = os.environ.get("SFW_IMAGE_ENGINE", "agy").lower().strip()
    sfw_ckpt = os.environ.get("SFW_COMFYUI_CHECKPOINT", "").strip()
    nsfw_ckpt = os.environ.get("NSFW_COMFYUI_CHECKPOINT", "").strip()
    detected = scan_image_models()

    markup = types.InlineKeyboardMarkup(row_width=1)

    # 1. Mode Selector Toggle
    mode_toggle_label = "🔀 Mode: Split Hybrid (Aktif) ➔ Ganti Unified" if is_split else "🤖 Mode: Unified (Aktif) ➔ Ganti Split Hybrid"
    markup.add(types.InlineKeyboardButton(mode_toggle_label, callback_data="cfg_toggle_split_img"))

    if is_split:
        # SFW Section
        markup.add(types.InlineKeyboardButton("─── 🌸 ENGINE FOTO SFW (Santai/Normal) ───", callback_data="noop"))
        is_sfw_agy = (sfw_img == "agy")
        is_sfw_anything = (sfw_img == "comfyui" and ("anything" in sfw_ckpt.lower() or "xl" in sfw_ckpt.lower()))
        is_sfw_meina = (sfw_img == "comfyui" and "meina" in sfw_ckpt.lower())
        is_sfw_cloud = (sfw_img == "cloud")

        markup.add(types.InlineKeyboardButton(f"🌉 Google Antigravity (AGY Generator) {'✓' if is_sfw_agy else ''}", callback_data="cfg_set_sfw_img:agy"))
        markup.add(types.InlineKeyboardButton(f"🌟 Anything XL (SDXL 1024px - ComfyUI) {'✓' if is_sfw_anything else ''}", callback_data="cfg_set_sfw_img:anything_xl"))
        markup.add(types.InlineKeyboardButton(f"✨ MeinaMix v12 (SD 1.5 - ComfyUI) {'✓' if is_sfw_meina else ''}", callback_data="cfg_set_sfw_img:meinamix"))
        markup.add(types.InlineKeyboardButton(f"☁️ Cloud Engine (Pollinations GPU) {'✓' if is_sfw_cloud else ''}", callback_data="cfg_set_sfw_img:cloud"))

        # NSFW Section
        markup.add(types.InlineKeyboardButton("─── 🔞 ENGINE FOTO NSFW (18+ / Intim) ───", callback_data="noop"))
        is_nsfw_aom = any(k in nsfw_ckpt.lower() for k in ["aom", "orange"]) or not nsfw_ckpt
        is_nsfw_meina = ("meina" in nsfw_ckpt.lower())
        is_nsfw_anything = ("anything" in nsfw_ckpt.lower() or "xl" in nsfw_ckpt.lower())

        markup.add(types.InlineKeyboardButton(f"🍊 AbyssOrangeMix3 (AOM3A1B SD 1.5 - Uncensored) {'✓' if is_nsfw_aom else ''}", callback_data="cfg_set_nsfw_img:aom3"))
        markup.add(types.InlineKeyboardButton(f"✨ MeinaMix v12 (SD 1.5 - ComfyUI) {'✓' if is_nsfw_meina and not is_nsfw_aom else ''}", callback_data="cfg_set_nsfw_img:meinamix"))
        markup.add(types.InlineKeyboardButton(f"🌟 Anything XL (SDXL 1024px - ComfyUI) {'✓' if is_nsfw_anything else ''}", callback_data="cfg_set_nsfw_img:anything_xl"))
    else:
        is_meina = ("meina" in cur_ckpt.lower())
        is_aom = any(k in cur_ckpt.lower() for k in ["aom", "orange"])
        is_anything = ("anything" in cur_ckpt.lower() or "xl" in cur_ckpt.lower())
        is_auto = (not cur_ckpt and bool(cur_url))
        is_agy = (os.environ.get("SFW_IMAGE_ENGINE", "").lower() == "agy")

        markup.add(types.InlineKeyboardButton(f"🌉 Google Antigravity (AGY Subagent) {'✓' if is_agy else ''}", callback_data="cfg_set_ckpt:agy"))
        markup.add(types.InlineKeyboardButton(f"✨ MeinaMix v12 (SD 1.5 - Cepat & Hemat VRAM) {'✓' if is_meina and not is_agy else ''}", callback_data="cfg_set_ckpt:meinamix"))
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

    if is_split:
        if sfw_img == "agy":
            sfw_display = "Google Antigravity (AGY Image Generator)"
        elif sfw_img == "cloud":
            sfw_display = "Cloud Engine (Pollinations)"
        elif "anything" in sfw_ckpt.lower():
            sfw_display = "Anything XL (SDXL ComfyUI)"
        elif "meina" in sfw_ckpt.lower():
            sfw_display = "MeinaMix v12 (SD 1.5 ComfyUI)"
        else:
            sfw_display = sfw_ckpt or "Local ComfyUI"

        if "aom" in nsfw_ckpt.lower() or "orange" in nsfw_ckpt.lower() or not nsfw_ckpt:
            nsfw_display = "AbyssOrangeMix3 (AOM3A1B SD 1.5 Uncensored)"
        elif "anything" in nsfw_ckpt.lower():
            nsfw_display = "Anything XL (SDXL)"
        elif "meina" in nsfw_ckpt.lower():
            nsfw_display = "MeinaMix v12"
        else:
            nsfw_display = nsfw_ckpt

        text = (
            f"🎨 **Pengaturan Model Foto: Split Hybrid**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Status Arsitektur: `🔀 Split Hybrid (Terpisah Otomatis)`\n"
            f"• **Engine Foto SFW**  : `{sfw_display}`\n"
            f"• **Engine Foto NSFW** : `{nsfw_display}`\n\n"
            f"💡 _Setiap permintaan foto otomatis disalurkan:_\n"
            f"  - Foto santai/jalan-jalan dialihkan ke **Engine SFW**.\n"
            f"  - Foto intim/dewasa dialihkan ke **Engine NSFW Uncensored**."
        )
    else:
        if is_agy:
            active_display = "Google Antigravity (AGY Subagent)"
        elif not cur_ckpt:
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
            f"• Mode: `🤖 Unified Mode`\n"
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
    cur_backend = os.environ.get("VOICE_BACKEND", "edge-tts").lower().strip()
    is_vs = (cur_backend in ("voicestudio", "local"))

    active_p = persona_mgr.get_active_persona()
    p_name = active_p.get("name", "Waifu")
    p_char = active_p.get("voice_character", "Natural anime girlfriend voice")

    markup = types.InlineKeyboardMarkup(row_width=1)

    # 1. Voice Engine Toggle Button
    engine_toggle_label = "🏠 Engine: VoiceStudio (Local AI Port 3900) ➔ Ubah ke Edge-TTS" if is_vs else "🌐 Engine: Edge-TTS Cloud (Aktif) ➔ Ubah ke VoiceStudio"
    markup.add(types.InlineKeyboardButton(engine_toggle_label, callback_data="cfg_toggle_voice_engine"))

    # 2. Voice Reply Mode
    markup.add(
        types.InlineKeyboardButton(f"🎙️ Selalu Balas Suara {'✓' if cur_mode == 'always' else ''}", callback_data="set_voice:always"),
        types.InlineKeyboardButton(f"🎧 Balas Suara Hanya Saat Kirim VN {'✓' if cur_mode == 'match_vn' else ''}", callback_data="set_voice:match_vn"),
        types.InlineKeyboardButton(f"🔇 Text Only (Mute) {'✓' if cur_mode == 'off' else ''}", callback_data="set_voice:off")
    )

    if is_vs:
        markup.add(
            types.InlineKeyboardButton(f"✨ Karakter Suara: {p_name} (VoiceStudio Auto)", callback_data="noop")
        )
    else:
        is_auto = (str(cur_speaker).lower() == "auto")
        markup.add(
            types.InlineKeyboardButton(f"🇮🇩 Gadis (Bahasa Indonesia) {'✓' if 'gadis' in str(cur_speaker).lower() else ''}", callback_data="cfg_set_speaker:gadis"),
            types.InlineKeyboardButton(f"🇯🇵 Nanami (Japanese / 日本語) {'✓' if 'nanami' in str(cur_speaker).lower() else ''}", callback_data="cfg_set_speaker:nanami"),
            types.InlineKeyboardButton(f"🇬🇧 Ana (English Sweet) {'✓' if 'ana' in str(cur_speaker).lower() else ''}", callback_data="cfg_set_speaker:ana"),
            types.InlineKeyboardButton(f"🇺🇸 Jenny (English Cheerful) {'✓' if 'jenny' in str(cur_speaker).lower() else ''}", callback_data="cfg_set_speaker:jenny"),
            types.InlineKeyboardButton(f"🌐 Ikuti Bahasa Chat (Auto Sync) {'✓' if is_auto else ''}", callback_data="cfg_set_speaker:auto"),
        )

    markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))

    if is_vs:
        text = (
            f"🎙️ **Pengaturan Voice & Audio Waifu**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Engine Suara : `🏠 VoiceStudio Local AI (Port 3900)`\n"
            f"• Mode Balasan : **{cur_mode.upper()}**\n"
            f"• Persona Voice: **{p_name}**\n"
            f"• Karakteristik: _{p_char}_\n\n"
            f"💡 _VoiceStudio beroperasi secara lokal & offline di PC Anda, otomatis menghasilkan intonasi suara sesuai persona {p_name}!_"
        )
    else:
        speaker_desc = "🌐 Auto-sync (Ikuti Bahasa Chat)" if str(cur_speaker).lower() == "auto" else cur_speaker
        text = (
            f"🎙️ **Pengaturan Voice & Audio Waifu**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Engine Suara : `🌐 Edge-TTS Cloud (Ringan & 0 VRAM)`\n"
            f"• Mode Balasan : **{cur_mode.upper()}**\n"
            f"• Model Suara  : `{speaker_desc}`\n\n"
            f"🗣️ **Pilihan Bahasa & Karakter Suara:**\n"
            f"• 🇮🇩 **Gadis** = Bahasa Indonesia alami\n"
            f"• 🇯🇵 **Nanami** = Bahasa Jepang (otomatis polyglot voice!)\n"
            f"• 🇬🇧 **Ana / Jenny** = Bahasa Inggris\n"
            f"• 🌐 **Auto** = Otomatis mengikuti bahasa chat waifu (`/language`)\n\n"
            f"💡 _Fitur Polyglot Voice Guardrail otomatis menerjemahkan ucapan waifu ke bahasa suara yang kamu pilih!_"
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

def is_agy_bridge_online() -> bool:
    """Quick socket check if AGY OpenAI bridge is responding on port 8001."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=0.5):
            return True
    except Exception:
        return False


def is_voicestudio_online() -> bool:
    """Quick socket check if VoiceStudio service is responding on port 3900."""
    import socket
    vs_port = int(os.environ.get("VOICESTUDIO_PORT", "3900"))
    try:
        with socket.create_connection(("127.0.0.1", vs_port), timeout=0.5):
            return True
    except Exception:
        return False


def build_system_diagnostics_report(user_id: int) -> str:
    """Builds a comprehensive system diagnostics report matching and exceeding CLI 'waifu status'."""
    llm_stat = llm_client.check_health()
    media_stat = media_engine.check_status()
    persona = persona_mgr.get_active_persona()

    spec = asset_manager.get_llm_launch_spec() if asset_manager else None
    kobold_listening = is_port_listening(5001)
    if kobold_listening:
        status_icon = "🟢 Online (Port 5001 - Load Penuh)"
    elif idle_engine.enabled and spec:
        status_icon = "💤 Standby / Tidur (VRAM Bebas • Bangun Otomatis Saat Chat)"
    else:
        status_icon = "🔴 Offline (Port 5001 • Belum Terpasang/Aktif)"

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
    outfit_det = persona_mgr.get_user_outfit_details(user_id)
    raw_outfit_key = outfit_det["key"]
    cur_outfit = outfit_det["name"]
    if raw_outfit_key == "nude":
        outfit_disp = f"`{cur_outfit}` 🔞 _(Auto-Switch NSFW Engine Aktif)_"
    else:
        outfit_disp = f"`{cur_outfit}`"
    lang_label = persona_mgr.get_language_display_name(BOT_LANGUAGE)
    score, rel_status = persona_mgr.get_relationship_status(user_id)
    affinity_score = memory_engine.get_affinity(user_id)

    # Resolve AI Architecture
    ai_mode = os.environ.get("AI_ENGINE_MODE", "split").lower()
    ai_mode_str = "Split Hybrid (SFW + NSFW Khusus)" if ai_mode == "split" else "Unified (Model Tunggal)"
    sfw_p = os.environ.get("SFW_LLM_PROVIDER", "gemini")
    sfw_m = os.environ.get("SFW_LLM_MODEL", "gemini-2.5-flash")
    nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "local")
    nsfw_m = os.environ.get("LOCAL_LLM_MODEL", llm_model_name)

    # Resolve Photo model checkpoint and installation status
    cur_ckpt = media_stat.get("active_checkpoint") or media_engine.get_active_checkpoint(is_nude=(raw_outfit_key == "nude"))
    cdir = asset_manager.detect_comfyui_dir() if asset_manager else None
    ckpt_installed = False
    if cdir and cur_ckpt:
        ckpt_path = os.path.join(cdir, "models", "checkpoints", cur_ckpt)
        ckpt_installed = os.path.isfile(ckpt_path)
    ckpt_badge = "_(Terpasang ✓)_" if ckpt_installed else ("_(Aktif di ComfyUI ✓)_" if media_stat.get("online") else "_(Perlu Download)_")
    sfw_img_engine = os.environ.get("SFW_IMAGE_ENGINE", "comfyui").lower()
    nsfw_img_engine = os.environ.get("NSFW_IMAGE_ENGINE", "comfyui").lower()
    sfw_ckpt_name = os.environ.get("SFW_COMFYUI_CHECKPOINT", "AnythingXL_xl.safetensors")
    nsfw_ckpt_name = os.environ.get("NSFW_COMFYUI_CHECKPOINT", "AOM3A1B_orange_mixs.safetensors")
    img_mode = os.environ.get("IMAGE_ENGINE_MODE", "split").lower()
    img_mode_str = "Split Hybrid (SFW + NSFW Khusus)" if img_mode == "split" else "Unified"

    if raw_outfit_key == "nude":
        active_model_str = f"`{cur_ckpt}` _(NSFW Model Dipakai Otomatis 🔞)_"
    else:
        active_model_str = f"`{cur_ckpt}` {ckpt_badge}"

    # Resolve Photo Vault Archive stats
    import photo_vault
    vault_stats = photo_vault.get_vault_stats()
    vault_str = f"`{vault_stats.get('total', 0)} foto` _(Arsip Galeri Lokal Aktif ✓)_"

    # Resolve Video Engine & Video model
    v_engine_label = VIDEO_ENGINE_LABELS.get(VIDEO_ENGINE, VIDEO_ENGINE)
    is_v_ready, missing_v = asset_manager.ensure_video_engine_assets(VIDEO_ENGINE) if asset_manager else (True, [])
    v_ready_badge = "_(Siap ✓)_" if is_v_ready else f"_(Perlu Download: {', '.join(missing_v)})_"
    if VIDEO_ENGINE == "wan21":
        v_model_str = "`wan2.1_t2v_1.3B_bf16` + `umt5_xxl_fp8` + `wan_2.1_vae`"
    else:
        v_model_str = "`mm_sd_v15_v2.ckpt` + `ComfyUI-AnimateDiff-Evolved`"

    # Photo ratio & quality preset
    ar = USER_RATIOS.get(user_id, "3:4")
    qual = USER_QUALITIES.get(user_id, "high").title()

    # Voice TTS & VoiceStudio / Edge-TTS
    vs_backend = os.environ.get("VOICE_BACKEND", "edge-tts").lower().strip()
    vs_speaker = os.environ.get("VOICE_NAME", getattr(voice_engine, "default_voice", "id-ID-GadisNeural"))
    vs_lang = os.environ.get("VOICE_LANGUAGE", "id-ID")
    vs_reply = os.environ.get("VOICE_REPLY_MODE", "smart").title()
    if "voicestudio" in vs_backend:
        vs_port = int(os.environ.get("VOICESTUDIO_PORT", "3900"))
        if is_voicestudio_online():
            vs_status_str = f"🟢 Online (Port {vs_port} - Local AI)"
        elif hasattr(idle_engine, "voicestudio_installed") and idle_engine.voicestudio_installed:
            vs_status_str = f"💤 Standby / Tidur (Smart Idle: VRAM Bebas)"
        else:
            vs_status_str = f"🔴 Offline / Belum Terpasang (Port {vs_port})"
        voice_label_str = f"VoiceStudio Local AI (`{vs_speaker}`)"
    else:
        vs_status_str = "🟢 Online (Microsoft Edge-TTS Cloud Ready)"
        voice_label_str = f"Edge-TTS Cloud (`{vs_speaker}`)"

    music_str = "🟢 Online (Port 8002)" if is_music_server_online() else "⚪ Inactive"

    # AGY OpenAI Bridge
    is_agy_selected = (
        sfw_p == "agy" or nsfw_p == "agy" or
        ":8001" in os.environ.get("LLM_BASE_URL", "") or
        sfw_img_engine == "agy" or nsfw_img_engine == "agy"
    )
    if is_agy_bridge_online():
        agy_str = "🟢 Online (Port 8001 - Always-On)" if is_agy_selected else "🟢 Online (Port 8001 - OpenAI Ready)"
    else:
        agy_str = "⚡ Memulai Ulang..." if is_agy_selected else "⚪ Inactive"

    # Coding Workspace & Active Project
    curr_proj = project_manager.get_active_project(user_id) if project_manager else "general"
    root_proj_dir = project_manager.get_projects_root_dir() if project_manager else os.path.expanduser("~")

    # Preview Web Servers
    servers_str = "⚪ Tidak Ada (Otomatis aktif saat coding web)"
    try:
        from project_server_manager import get_project_server_manager
        psm = get_project_server_manager()
        live_servers = psm.list_active_servers()
        if live_servers:
            srv_desc = ", ".join([f"`{s['project']}` ([Port {s['port']}]({s['url']}))" for s in live_servers])
            servers_str = f"🟢 `{len(live_servers)} Server Aktif` ({srv_desc}) — `/servers`"
    except Exception:
        pass

    # Bot Process & Windows Autorun
    bot_pid = os.getpid()
    autorun_str = "🟢 Aktif (Auto-boot PC)" if is_autorun_enabled() else "⚪ Nonaktif"

    # Memory facts
    facts_count = len(memory_engine.get_facts(user_id))

    # Hardware Auto-Tuning Profile
    hw = asset_manager.detect_hardware_profile() if asset_manager else None
    hw_str = f"`{hw['gpu_name']}` _({hw['vram_gb']} GB VRAM • {hw['tier_label']})_" if hw else "`Auto-Detect`"

    # Resolve Daily Story Arc
    today_ep = story_engine.get_today_story(persona_mgr.active_key)
    if today_ep:
        story_str = f"`{today_ep.get('arc_title', 'Kisah Harian')}` _(Hari {today_ep.get('day_index', 1)}/{today_ep.get('total_days', 5)}: {today_ep.get('day_theme', '')})_"
    else:
        story_str = "`Belum Ada Cerita`"

    report = (
        f"📊 **Waifu on Telegram v{get_version()} - System Diagnostics**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Persona Waifu** : **{p_name}** _({p_arch})_\n"
        f"📖 **Cerita Hari Ini**: {story_str}\n"
        f"👗 **Pakaian Aktif** : {outfit_disp}\n"
        f"🌐 **Bahasa Chat**   : `{lang_label}`\n"
        f"💖 **Status Hubungan**: **{rel_status}** (`{score}%` • `{affinity_score} pts`)\n\n"
        f"🎮 **Hardware Auto-Tuning**:\n"
        f"• Profil GPU   : {hw_str}\n\n"
        f"🧠 **Arsitektur LLM ({ai_mode_str})**:\n"
        f"• SFW Engine   : `{sfw_p}` (`{sfw_m}`)\n"
        f"• NSFW Engine  : `{nsfw_p}` (`{nsfw_m}`)\n"
        f"• Local Kobold : {status_icon}\n"
        f"• AGY Bridge   : {agy_str}\n"
        f"• Vision Model : {vision_str}\n\n"
        f"🎨 **Generator Visual ({img_mode_str})**: {media_icon}\n"
        f"• SFW Engine   : `{sfw_img_engine}` (`{sfw_ckpt_name}`)\n"
        f"• NSFW Engine  : `{nsfw_img_engine}` (`{nsfw_ckpt_name}`)\n"
        f"• **Model Foto Aktif**: {active_model_str}\n"
        f"• **Photo Vault**: {vault_str}\n"
        f"• **Engine Video**: `{v_engine_label}` {v_ready_badge}\n"
        f"• **Model Video**: {v_model_str}\n"
        f"• Rasio/Preset : `{ar}` | `{qual}`\n\n"
        f"🎙️ **Audio & Suara**:\n"
        f"• Engine Voice : `{voice_label_str}`\n"
        f"• Status Voice : {vs_status_str}\n"
        f"• Bahasa Voice : `{vs_lang}` | Mode: `{vs_reply}`\n"
        f"• Server Musik : {music_str}\n\n"
        f"💻 **Coding & Workspace**:\n"
        f"• Project Aktif: `{curr_proj}`\n"
        f"• Root Folder  : `{root_proj_dir}`\n"
        f"• Open-Design  : `🟢 Aktif (153 Design Systems • 169 Skills)`\n"
        f"• Web Preview  : {servers_str}\n\n"
        f"⚙️ **Sistem & Resource**:\n"
        f"• Bot Process  : `🟢 Berjalan (PID: {bot_pid})`\n"
        f"• PC Autorun   : `{autorun_str}`\n"
        f"• Mode Hemat   : `{idle_engine.get_status_summary()}`\n"
        f"• GPU Lock     : `🟢 Aktif (Proteksi Tabrakan VRAM Image & Voice)`\n"
        f"• Buffer Jadwal: `{scheduled_buffer.get_status_summary(user_id)}`\n"
        f"• Chat Tertunda: `{pending_manager.get_pending_count()} pesan (Auto-Retry saat LLM Online)`\n"
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


@bot.message_handler(commands=['servers', 'preview', 'ports'])
def handle_servers_command(message):
    if not is_authorized(message.from_user.id):
        return
    try:
        from project_server_manager import get_project_server_manager
        psm = get_project_server_manager()
        msg_text = psm.format_active_servers_message()
        active_srvs = psm.list_active_servers()
        markup = None
        if active_srvs:
            markup = types.InlineKeyboardMarkup()
            for s in active_srvs:
                p_name = s.get("project", "Project")
                p_port = s.get("port")
                p_url = f"http://127.0.0.1:{p_port}/"
                markup.add(types.InlineKeyboardButton(f"🌐 Buka {p_name} (Port {p_port})", url=p_url))
        bot.reply_to(message, msg_text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Gagal membaca daftar server: {e}")


@bot.message_handler(commands=['stop_server'])
def handle_stop_server_command(message):
    if not is_authorized(message.from_user.id):
        return
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "💡 Format perintah: `/stop_server <port_atau_nama_project>`\nContoh: `/stop_server 8086`", parse_mode="Markdown")
        return
    target = args[0].strip()
    try:
        from project_server_manager import get_project_server_manager
        psm = get_project_server_manager()
        ok = psm.stop_preview_server(target)
        if ok:
            bot.reply_to(message, f"✓ Preview server `{target}` berhasil dimatikan.", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"⚠️ Tidak menemukan preview server aktif dengan port/nama `{target}`.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Gagal menghentikan server: {e}")


@bot.message_handler(commands=['pending'])
def handle_pending_command(message):
    if not is_authorized(message.from_user.id):
        return
    count = pending_manager.get_pending_count()
    if count == 0:
        bot.reply_to(message, "✨ Tidak ada pesan yang tertunda! Semua chat sudah terbalas dengan baik 💕")
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Coba Balas Sekarang", callback_data="cfg_action:retry_pending"))
        bot.reply_to(
            message,
            f"📌 Ada **{count}** pesan yang tertunda menunggu server LLM siap.\n"
            f"Begitu server online, waifu akan langsung membalasnya otomatis!",
            reply_markup=markup,
            parse_mode="Markdown"
        )


@bot.callback_query_handler(func=lambda call: call.data == 'cfg_action:retry_pending')
def callback_retry_pending(call):
    if not is_authorized(call.from_user.id):
        return
    bot.answer_callback_query(call.id, "🔄 Memproses pesan tertunda...")
    pending_manager.retry_all_pending(bot, process_text_chat)


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
    """Renders interactive outfit selection keyboard with auto-dynamic and session-aware controls."""
    details = persona_mgr.get_user_outfit_details(user_id)
    cur_key = details["key"]
    mode = details["mode"]
    is_auto = (mode == "auto" or cur_key == "default")

    markup = types.InlineKeyboardMarkup(row_width=2)

    # 1. Primary Auto Mode button at top
    auto_label = "🌟 Mode Otomatis (Dinamis Sesuai Jadwal) ✓" if is_auto else "🌟 Mode Otomatis (Dinamis Sesuai Jadwal)"
    markup.add(types.InlineKeyboardButton(auto_label, callback_data="set_outfit:default"))

    # Quick action buttons for active session/locked outfit
    if mode == "session":
        markup.add(
            types.InlineKeyboardButton("🔄 Reset ke Otomatis", callback_data="set_outfit:default"),
            types.InlineKeyboardButton(f"🔒 Kunci Outfit Ini", callback_data=f"lock_outfit:{cur_key}")
        )
    elif mode == "locked":
        markup.add(
            types.InlineKeyboardButton("🔓 Buka Kunci (Kembali ke Otomatis)", callback_data="set_outfit:default")
        )

    outfits = persona_mgr.list_outfits()
    btns = []
    for key, name in outfits:
        if key in ("default", "auto"):
            continue
        is_cur = (key == cur_key and not is_auto)
        label = f"{name} ✓" if is_cur else name
        btns.append(types.InlineKeyboardButton(label, callback_data=f"set_outfit:{key}"))
    markup.add(*btns)
    markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))

    if mode == "auto":
        status_line = (
            f"• Mode: **🌟 Otomatis (Dinamis Sesuai Jadwal)**\n"
            f"• Pakaian Saat Ini: **{details['dynamic_name']}**\n"
            f"_(Akira otomatis berganti pakaian mengikuti jam dan kegiatannya: tidur = piyama, mandi = handuk, kuliah = baju kampus, santai = baju santai)_\n"
        )
    elif mode == "session":
        status_line = (
            f"• Mode: **👗 Sesi Khusus**\n"
            f"• Pakaian Aktif: **{details['name']}**\n"
            f"_(Berlaku untuk sesi foto saat ini. Otomatis kembali ke pakaian harian saat kegiatan/topik berpindah)_\n"
        )
    else:
        status_line = (
            f"• Mode: **🔒 Terkunci**\n"
            f"• Pakaian Aktif: **{details['name']}**\n"
            f"_(Terkunci permanen sampai kamu memilih Mode Otomatis)_\n"
        )

    text = (
        f"👗 **Lemari Pakaian Waifu (/outfit)**\n\n"
        f"{status_line}\n"
        f"Pilih gaya busana waifumu untuk sesi foto & selfie! 💕\n\n"
        f"💡 *Tips*: Dalam **Mode Otomatis**, Akira akan otomatis menyesuaikan pakaiannya secara realistis dengan apa yang sedang dia lakukan!"
    )
    if message_to_edit:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_to_edit, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
    send_menu_message(chat_id, text, reply_markup=markup, reply_to_id=reply_to_id)


def show_hangout_menu(chat_id: int, user_id: int, message_to_edit: Optional[int] = None, reply_to_id: Optional[int] = None):
    """Renders interactive date & hangout selection menu."""
    active_date = hangout_engine.get_active_date(user_id)
    persona = persona_mgr.get_active_persona()
    p_name = persona.get("name", "Akira")

    markup = types.InlineKeyboardMarkup(row_width=1)

    if active_date:
        v_title = active_date.get("venue_title", "Tempat Kencan")
        markup.add(
            types.InlineKeyboardButton(f"📸 Minta Foto Kencan di {v_title}", callback_data="open_pap_menu"),
            types.InlineKeyboardButton("🚪 Selesai Kencan & Pulang", callback_data="end_hangout"),
            types.InlineKeyboardButton("🔙 Panel Setup", callback_data="cfg_submenu:dashboard")
        )
        text = (
            f"💖 **Kencan Berdua Sedang Berlangsung!** 🌸\n\n"
            f"Kamu dan **{p_name}** saat ini sedang **{v_title}**! 🥰✨\n"
            f"Nikmati momen kebersamaan kalian berdua di obrolan chat dan abadikan foto kencan bersama!"
        )
    else:
        for v in hangout_engine.list_venues():
            markup.add(types.InlineKeyboardButton(v["title"], callback_data=f"start_hangout:{v['key']}"))
        markup.add(types.InlineKeyboardButton("🔙 Kembali ke Setup", callback_data="cfg_submenu:dashboard"))
        text = (
            f"💖 **Menu Kencan & Hangout Berdua (/hangout)** 🌸\n\n"
            f"Pilih tempat kencan untuk dinikmati berdua bersama **{p_name}** sekarang:\n\n"
            f"• ☕ **Kafe Estetik**: Duduk berdua di sudut kafe menikmati kopi & dessert.\n"
            f"• 🎬 **Bioskop**: Nonton film bioskop berdampingan berbagi popcorn.\n"
            f"• 🛋️ **Kosan / Rumah**: Quality time santai berdua di kamar kosan.\n"
            f"• 🌸 **Taman Senja**: Jalan sore bergandengan tangan di taman kota.\n"
            f"• 🛍️ **Mall & Arcade**: Jalan-jalan seru dan main mesin capit berdua.\n\n"
            f"💡 _Tip: Kamu juga bisa langsung mengajak waifu secara alami di chat (misal: 'nonton bioskop yuk', 'ngopi yuk', atau 'main ke kosanmu yuk')!_"
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


@bot.message_handler(commands=['story', 'cerita', 'arc', 'episode'])
def handle_story_command(message):
    if not is_authorized(message.from_user.id):
        return
    persona = persona_mgr.get_active_persona()
    card = story_engine.format_story_summary_card(persona_mgr.active_key, persona.get("name", "Waifu"))
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Segarkan Arc", callback_data="refresh_story_arc"),
        types.InlineKeyboardButton("📸 Minta PAP Kegiatan", callback_data="action_photo:selfie")
    )
    safe_reply_to(message, card, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "refresh_story_arc")
def callback_refresh_story(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    persona = persona_mgr.get_active_persona()
    story_engine.replenish_storylines_if_llm_active(persona_mgr.active_key, llm_client, force=True)
    bot.answer_callback_query(call.id, "✨ Memperbarui alur cerita...", show_alert=False)
    card = story_engine.format_story_summary_card(persona_mgr.active_key, persona.get("name", "Waifu"))
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Segarkan Arc", callback_data="refresh_story_arc"),
        types.InlineKeyboardButton("📸 Minta PAP Kegiatan", callback_data="action_photo:selfie")
    )
    try:
        bot.edit_message_text(card, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass


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
                        caption=f"💖 **Halo! Sekarang aku {p.get('name')}** 👋🥰\n*({p.get('archetype', 'AI Companion')})*\n\n_{p.get('description')}_",
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error sending switched persona photo: {e}")


@bot.callback_query_handler(func=lambda call: call.data in ('open_hangout_menu', 'open_outfit_menu', 'open_persona_menu', 'open_ratio_menu', 'open_quality_menu', 'open_setup_menu', 'open_help_menu', 'open_memory_menu', 'open_reminders_menu', 'open_dates_menu', 'open_music_menu', 'open_pap_menu', 'check_love_status', 'start_new_persona'))
def callback_quick_actions(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if call.data == 'open_hangout_menu':
        show_hangout_menu(chat_id, user_id, message_to_edit=call.message.message_id)
    elif call.data == 'open_outfit_menu':
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
    elif sub == "projects":
        show_projects_menu(chat_id, user_id, message_to_edit=mid)
    elif sub == "desktop":
        show_desktop_status_menu(chat_id, user_id, message_to_edit=mid)


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
    if key in ("huihui_auto", "huihui", "qwythos", "qwythos_9b"):
        info_huihui = asset_manager.get_asset_info("qwythos_9b") if asset_manager else None
        if info_huihui and not info_huihui.get("installed"):
            bot.answer_callback_query(call.id, "📥 Memulai unduhan Huihui-Qwythos 9B Uncensored...")
            chat_id = call.message.chat.id
            mid = call.message.message_id
            msg_prompt = bot.send_message(
                chat_id,
                "⏳ **Sedang Mengunduh Huihui-Qwythos 9B Claude-Mythos (~5.5 GB)**\n\n"
                "Model roleplay 100% uncensored (bebas penolakan NSFW) sedang diunduh di latar belakang. "
                "Begitu selesai, model ini akan **otomatis dipilih & diaktifkan** sebagai otak utama waifu! 💕",
                parse_mode="Markdown"
            )
            def _async_dl_huihui():
                ok = asset_manager.download_asset("qwythos_9b") if asset_manager else False
                if ok:
                    asset_manager.download_asset("qwythos_vision")
                    apply_llm_choice("qwythos_9b")
                    try:
                        bot.edit_message_text(
                            "🎉 **Huihui-Qwythos 9B Berhasil Dipasang & Aktif!** 💕\n\n"
                            "Model uncensored default aktif. Sekarang waifu bebas berinteraksi mesra dan roleplay NSFW tanpa penolakan! ✨",
                            chat_id=chat_id,
                            message_id=msg_prompt.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                    try:
                        health_engine.heal_llm()
                    except Exception:
                        pass
                else:
                    try:
                        bot.edit_message_text(
                            "⚠️ **Gagal Mengunduh Huihui-Qwythos 9B**\n\n"
                            "Koneksi terputus. Silakan coba lagi nanti atau jalankan di terminal:\n"
                            "`waifu models download qwythos_9b`",
                            chat_id=chat_id,
                            message_id=msg_prompt.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            threading.Thread(target=_async_dl_huihui, daemon=True).start()
            show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=mid)
            return
        else:
            label = apply_llm_choice("qwythos_9b")
            bot.answer_callback_query(call.id, f"LLM: {label}")
            show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)
            return
    elif key in ("qwen_auto", "qwen", "qwen25", "qwen2.5", "qwen25_7b"):
        info_qwen = asset_manager.get_asset_info("qwen25_7b") if asset_manager else None
        if info_qwen and not info_qwen.get("installed"):
            bot.answer_callback_query(call.id, "📥 Memulai unduhan Qwen2.5-7B-Abliterated...")
            chat_id = call.message.chat.id
            mid = call.message.message_id
            msg_prompt = bot.send_message(
                chat_id,
                "⏳ **Sedang Mengunduh Qwen2.5-7B-Instruct-Abliterated (~4.7 GB)**\n\n"
                "Model terbaik yang sangat fasih Bahasa Indonesia sedang diunduh di latar belakang. "
                "Begitu selesai, model ini akan **otomatis dipilih & diaktifkan** sebagai otak utama waifu! 💕",
                parse_mode="Markdown"
            )
            def _async_dl_qwen():
                ok = asset_manager.download_asset("qwen25_7b") if asset_manager else False
                if ok:
                    apply_llm_choice("qwen25_7b")
                    try:
                        bot.edit_message_text(
                            "🎉 **Qwen2.5-7B-Instruct-Abliterated Berhasil Dipasang & Aktif!** 💕\n\n"
                            "Model Bahasa Indonesia terbaru sudah aktif. Gaya bicara waifu sekarang alami, santai, dan ekspresif! ✨",
                            chat_id=chat_id,
                            message_id=msg_prompt.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                    try:
                        health_engine.heal_llm()
                    except Exception:
                        pass
                else:
                    try:
                        bot.edit_message_text(
                            "⚠️ **Gagal Mengunduh Qwen2.5-7B-Instruct-Abliterated**\n\n"
                            "Koneksi terputus. Silakan coba lagi nanti atau jalankan di terminal:\n"
                            "`waifu models download qwen25_7b`",
                            chat_id=chat_id,
                            message_id=msg_prompt.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            threading.Thread(target=_async_dl_qwen, daemon=True).start()
            show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=mid)
            return
        else:
            label = apply_llm_choice("qwen25_7b")
            bot.answer_callback_query(call.id, f"LLM: {label}")
            show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)
            return
    elif key in ("stheno_auto", "stheno", "stheno_8b"):
        info_stheno = asset_manager.get_asset_info("stheno_8b") if asset_manager else None
        if info_stheno and not info_stheno.get("installed"):
            bot.answer_callback_query(call.id, "📥 Memulai unduhan L3-8B-Stheno-v3.4...")
            chat_id = call.message.chat.id
            mid = call.message.message_id
            msg_prompt = bot.send_message(
                chat_id,
                "⏳ **Sedang Mengunduh L3-8B-Stheno-v3.4 (~4.9 GB)**\n\n"
                "Model roleplay uncensored terbaik sedang diunduh di latar belakang. "
                "Begitu selesai, model ini akan **otomatis dipilih & diaktifkan** sebagai otak utama waifu! 💕",
                parse_mode="Markdown"
            )
            def _async_dl():
                ok = asset_manager.download_asset("stheno_8b") if asset_manager else False
                if ok:
                    apply_llm_choice("stheno")
                    try:
                        bot.edit_message_text(
                            "🎉 **L3-8B-Stheno-v3.4 Berhasil Dipasang & Aktif!** 💕\n\n"
                            "Model roleplay uncensored terbaru sudah aktif. Sekarang waifu bisa langsung mengobrol lancar tanpa delay `<think>`! ✨",
                            chat_id=chat_id,
                            message_id=msg_prompt.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                    try:
                        health_engine.heal_llm()
                    except Exception:
                        pass
                else:
                    try:
                        bot.edit_message_text(
                            "⚠️ **Gagal Mengunduh L3-8B-Stheno-v3.4**\n\n"
                            "Koneksi terputus. Silakan coba lagi nanti atau jalankan di terminal:\n"
                            "`waifu models download stheno_8b`",
                            chat_id=chat_id,
                            message_id=msg_prompt.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            threading.Thread(target=_async_dl, daemon=True).start()
            show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=mid)
            return
        else:
            label = apply_llm_choice("stheno")
            bot.answer_callback_query(call.id, f"LLM: {label}")
            show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)
            return

    label = apply_llm_choice(key)
    bot.answer_callback_query(call.id, f"LLM: {label}")
    show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == 'cfg_toggle_split_mode')
def callback_toggle_split_mode(call):
    if not is_authorized(call.from_user.id):
        return
    cur = os.environ.get("AI_ENGINE_MODE", "unified").lower().strip()
    new_mode = "split" if cur != "split" else "unified"
    os.environ["AI_ENGINE_MODE"] = new_mode
    update_env_variable("AI_ENGINE_MODE", new_mode)
    get_hybrid_llm_client(force_reload=True)
    bot.answer_callback_query(call.id, f"Arsitektur AI: {new_mode.upper()} Mode!")
    show_llm_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_sfw_p:'))
def callback_set_sfw_provider(call):
    if not is_authorized(call.from_user.id):
        return
    prov = call.data.split(":", 1)[1]
    presets = {
        "agy": ("http://127.0.0.1:8001/v1", "sk-agy-secret-key-12345", "gemini-3.8-flash-medium"),
        "openai": ("https://api.openai.com/v1", os.environ.get("OPENAI_API_KEY", ""), "gpt-4o-mini"),
        "groq": ("https://api.groq.com/openai/v1", os.environ.get("GROQ_API_KEY", ""), "llama-3.3-70b-versatile"),
        "deepseek": ("https://api.deepseek.com/v1", os.environ.get("DEEPSEEK_API_KEY", ""), "deepseek-chat"),
        "local": ("http://127.0.0.1:5001/v1", "kobold", "default")
    }
    base, key, model = presets.get(prov, ("http://127.0.0.1:5001/v1", "kobold", "default"))
    os.environ["SFW_LLM_PROVIDER"] = prov
    os.environ["SFW_LLM_BASE_URL"] = base
    if key:
        os.environ["SFW_LLM_API_KEY"] = key
    os.environ["SFW_LLM_MODEL"] = model
    update_env_variable("SFW_LLM_PROVIDER", prov)
    update_env_variable("SFW_LLM_BASE_URL", base)
    if key:
        update_env_variable("SFW_LLM_API_KEY", key)
    update_env_variable("SFW_LLM_MODEL", model)
    get_hybrid_llm_client(force_reload=True)
    bot.answer_callback_query(call.id, f"SFW Provider: {prov.upper()}")
    show_llm_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_nsfw_p:'))
def callback_set_nsfw_provider(call):
    if not is_authorized(call.from_user.id):
        return
    prov = call.data.split(":", 1)[1]
    if prov == "openrouter_uncensored":
        base = "https://openrouter.ai/api/v1"
        key = os.environ.get("OPENROUTER_API_KEY", "")
        model = "nousresearch/hermes-3-llama-3.1-405b"
    else:
        base = "http://127.0.0.1:5001/v1"
        key = "kobold"
        model = "default"
    os.environ["NSFW_LLM_PROVIDER"] = prov
    os.environ["NSFW_LLM_BASE_URL"] = base
    if key:
        os.environ["NSFW_LLM_API_KEY"] = key
    os.environ["NSFW_LLM_MODEL"] = model
    update_env_variable("NSFW_LLM_PROVIDER", prov)
    update_env_variable("NSFW_LLM_BASE_URL", base)
    if key:
        update_env_variable("NSFW_LLM_API_KEY", key)
    update_env_variable("NSFW_LLM_MODEL", model)
    get_hybrid_llm_client(force_reload=True)
    bot.answer_callback_query(call.id, f"NSFW Provider: {prov.upper()}")
    show_llm_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == 'noop')
def callback_noop(call):
    bot.answer_callback_query(call.id)


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
    alt_engine = "animatediff" if any("wan" in k for k in missing_keys) else "wan21"
    alt_label = "🌸 Alihkan ke AnimateDiff (SD 1.5 Anime)" if alt_engine == "animatediff" else "🌟 Alihkan ke Wan 2.1"
    markup.add(
        types.InlineKeyboardButton(f"📥 Unduh Otomatis (~{size_mb} MB)", callback_data=f"dl_asset:{first_key}"),
        types.InlineKeyboardButton(alt_label, callback_data=f"cfg_set_vengine:{alt_engine}"),
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
            f"💡 _Kamu bisa tetap ngobrol santai denganku selagi proses berlangsung ya!_ 🥰"
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



@bot.callback_query_handler(func=lambda call: call.data == 'cfg_toggle_split_img')
def callback_toggle_split_img(call):
    if not is_authorized(call.from_user.id):
        return
    cur = os.environ.get("IMAGE_ENGINE_MODE", "unified").lower().strip()
    new_mode = "split" if cur != "split" else "unified"
    os.environ["IMAGE_ENGINE_MODE"] = new_mode
    update_env_variable("IMAGE_ENGINE_MODE", new_mode)
    bot.answer_callback_query(call.id, f"Mode Foto: {new_mode.upper()} Mode!")
    show_photo_engine_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_sfw_img:'))
def callback_set_sfw_img(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    if key == "agy":
        os.environ["SFW_IMAGE_ENGINE"] = "agy"
        update_env_variable("SFW_IMAGE_ENGINE", "agy")
        label = "Google Antigravity (AGY)"
    elif key == "cloud":
        os.environ["SFW_IMAGE_ENGINE"] = "cloud"
        update_env_variable("SFW_IMAGE_ENGINE", "cloud")
        label = "Cloud Pollinations"
    elif key == "anything_xl":
        os.environ["SFW_IMAGE_ENGINE"] = "comfyui"
        os.environ["SFW_COMFYUI_CHECKPOINT"] = "AnythingXL_xl.safetensors"
        update_env_variable("SFW_IMAGE_ENGINE", "comfyui")
        update_env_variable("SFW_COMFYUI_CHECKPOINT", "AnythingXL_xl.safetensors")
        label = "Anything XL (SDXL)"
    elif key == "meinamix":
        os.environ["SFW_IMAGE_ENGINE"] = "comfyui"
        os.environ["SFW_COMFYUI_CHECKPOINT"] = "meinamix_v12Final.safetensors"
        update_env_variable("SFW_IMAGE_ENGINE", "comfyui")
        update_env_variable("SFW_COMFYUI_CHECKPOINT", "meinamix_v12Final.safetensors")
        label = "MeinaMix v12"
    else:
        label = key
    bot.answer_callback_query(call.id, f"SFW Foto: {label}")
    show_photo_engine_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_nsfw_img:'))
def callback_set_nsfw_img(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    if key == "aom3":
        ckpt = "AOM3A1B_orangemixs.safetensors"
        label = "AbyssOrangeMix3 (AOM3A1B)"
    elif key == "meinamix":
        ckpt = "meinamix_v12Final.safetensors"
        label = "MeinaMix v12"
    elif key == "anything_xl":
        ckpt = "AnythingXL_xl.safetensors"
        label = "Anything XL"
    else:
        ckpt = key
        label = key
    os.environ["NSFW_IMAGE_ENGINE"] = "comfyui"
    os.environ["NSFW_COMFYUI_CHECKPOINT"] = ckpt
    update_env_variable("NSFW_IMAGE_ENGINE", "comfyui")
    update_env_variable("NSFW_COMFYUI_CHECKPOINT", ckpt)
    bot.answer_callback_query(call.id, f"NSFW Foto: {label}")
    show_photo_engine_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cfg_set_ckpt:'))
def callback_set_ckpt(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    label = apply_ckpt_choice(key)
    bot.answer_callback_query(call.id, f"Model Foto: {label}")
    show_setup_dashboard(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == 'cfg_toggle_voice_engine')
def callback_toggle_voice_engine(call):
    if not is_authorized(call.from_user.id):
        return
    cur = os.environ.get("VOICE_BACKEND", "edge-tts").lower().strip()
    new_backend = "voicestudio" if cur != "voicestudio" else "edge-tts"
    os.environ["VOICE_BACKEND"] = new_backend
    update_env_variable("VOICE_BACKEND", new_backend)
    voice_engine.voice_backend = new_backend

    if new_backend == "voicestudio":
        from voicestudio_engine import voicestudio_engine
        if not voicestudio_engine.is_service_running() and voicestudio_engine.is_installed():
            voicestudio_engine.start_service()
        bot.answer_callback_query(call.id, "Voice Engine: VoiceStudio (Local AI) 🏠")
    else:
        bot.answer_callback_query(call.id, "Voice Engine: Edge-TTS Cloud 🌐")

    show_voice_settings_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


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
        conf = "Baik! Aku akan otomatis mendeteksi dan menyesuaikan bahasa percakapan kita yaa~ ✨"
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
            if results.get("llm"):
                pending_manager.retry_all_pending(bot, process_text_chat)
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
        details = persona_mgr.get_user_outfit_details(call.from_user.id)
        if key in ("default", "auto"):
            bot.answer_callback_query(call.id, "🌟 Mode Otomatis Aktif!")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("📸 Minta PAP Sekarang", callback_data="open_pap_menu"),
                types.InlineKeyboardButton("👗 Lemari Baju", callback_data="open_outfit_menu"),
                types.InlineKeyboardButton("🔙 Panel Setup", callback_data="cfg_submenu:dashboard")
            )
            msg = (
                f"🌟 **Mode Otomatis Aktif!**\n\n"
                f"Akira sekarang akan **otomatis berganti pakaian sendiri** mengikuti jadwal & kegiatan nyatanya!\n"
                f"• Tidur / Malam : Piyama santai\n"
                f"• Mandi : Handuk mandi\n"
                f"• Kuliah : Baju mahasiswi kampus\n"
                f"• Kafe : Cozy knit sweater\n"
                f"• Santai Rumah : Kaos kasual\n\n"
                f"_Pakaian saat ini:_ **{details['dynamic_name']}** 🥰📸"
            )
        else:
            name = details['raw_name']
            bot.answer_callback_query(call.id, f"Outfit Sesi: {name}")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("📸 Minta PAP Sekarang", callback_data="open_pap_menu"),
                types.InlineKeyboardButton("🔄 Reset ke Otomatis", callback_data="set_outfit:default"),
                types.InlineKeyboardButton("🔒 Kunci Outfit Ini", callback_data=f"lock_outfit:{key}"),
                types.InlineKeyboardButton("👗 Ganti Pakaian", callback_data="open_outfit_menu")
            )
            msg = (
                f"👗 **Outfit Sesi Khusus Aktif!**\n\n"
                f"Waifumu sekarang mengenakan **{name}** untuk sesi foto & selfie saat ini! 🥰📸\n\n"
                f"💡 _Catatan: Pakaian ini berlaku untuk sesi ini. Akira akan otomatis kembali ke pakaian harian yang sesuai saat berganti aktivitas (tidur, mandi, kuliah, santai, dll)._"
            )
        try:
            bot.edit_message_text(
                msg,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('lock_outfit:'))
def callback_lock_outfit(call):
    if not is_authorized(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    if persona_mgr.set_user_outfit(call.from_user.id, key, is_locked=True):
        details = persona_mgr.get_user_outfit_details(call.from_user.id)
        name = details['raw_name']
        bot.answer_callback_query(call.id, f"🔒 Pakaian dikunci: {name}")
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📸 Minta PAP Sekarang", callback_data="open_pap_menu"),
            types.InlineKeyboardButton("🌟 Buka Kunci (Mode Otomatis)", callback_data="set_outfit:default"),
            types.InlineKeyboardButton("👗 Lemari Baju", callback_data="open_outfit_menu"),
            types.InlineKeyboardButton("🔙 Panel Setup", callback_data="cfg_submenu:dashboard")
        )
        msg = (
            f"🔒 **Outfit Berhasil Dikunci!**\n\n"
            f"Waifumu akan **terus mengenakan {name}** di setiap foto dan obrolan sampai kamu mengubahnya kembali ke Mode Otomatis! 🥰"
        )
        try:
            bot.edit_message_text(
                msg,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass


@bot.message_handler(commands=['hangout', 'kencan', 'date', 'jalan'])
def handle_hangout_command(message):
    if not is_authorized(message.from_user.id):
        return
    try:
        show_hangout_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)
    except Exception as e:
        logger.error(f"Error handling /hangout command: {e}", exc_info=True)
        bot.reply_to(message, f"⚠️ Terjadi kendala saat membuka menu kencan: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('start_hangout:'))
def callback_start_hangout(call):
    if not is_authorized(call.from_user.id):
        return
    venue_key = call.data.split(":", 1)[1]
    user_id = call.from_user.id
    date_session = hangout_engine.start_date(user_id, venue_key)
    venue = date_session["venue"]
    p_name = persona_mgr.get_active_persona().get("name", "Akira")

    bot.answer_callback_query(call.id, f"💖 Kencan dimulai di {venue['title']}!")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 Minta Foto Berdua", callback_data="open_pap_menu"),
        types.InlineKeyboardButton("🚪 Selesai Kencan", callback_data="end_hangout"),
        types.InlineKeyboardButton("🔙 Panel Kencan", callback_data="open_hangout_menu")
    )
    roleplay_cue = venue.get("roleplay_cues", [f"{p_name} tersenyum manis menatapmu"])[0]
    msg = (
        f"💖 **Momen Kencan Berdua Dimulai!** 🌸\n\n"
        f"_{roleplay_cue}_\n\n"
        f"Kamu dan **{p_name}** sekarang sedang **{venue['title']}**! 🥰\n"
        f"_{venue['activity']}_\n\n"
        f"✨ Obrolanmu di chat sekarang berlangsung langsung di suasana {venue['title']}. Nikmati waktu berdua dan jangan ragu minta foto kencan ya!"
    )
    try:
        bot.edit_message_text(
            msg,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == 'end_hangout')
def callback_end_hangout(call):
    if not is_authorized(call.from_user.id):
        return
    user_id = call.from_user.id
    p_name = persona_mgr.get_active_persona().get("name", "Akira")
    hangout_engine.end_date(user_id)
    bot.answer_callback_query(call.id, "🚪 Selesai kencan!")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💖 Ajak Kencan Lagi", callback_data="open_hangout_menu"),
        types.InlineKeyboardButton("🔙 Menu Setup", callback_data="cfg_submenu:dashboard")
    )
    msg = (
        f"🌸 **Kencan Berdua Selesai** ✨\n\n"
        f"_{p_name} melambaikan tangan lembut sambil tersenyum hangat_\n\n"
        f"Terima kasih untuk kencan yang menyenangkan hari ini! {p_name} senang banget bisa menghabiskan waktu berdua sama kamu. Sampai jumpa di kencan berikutnya ya! 🥰"
    )
    try:
        bot.edit_message_text(
            msg,
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
            conf = "Baik! Aku akan otomatis mendeteksi dan menyesuaikan bahasa percakapan kita yaa~ ✨"
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
        f"Kamu mau aku kirim foto selfie di mana dan lagi suasana apa?\n\n"
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

def process_photo_request(
    target,
    user_text: str,
    is_proof: bool = False,
    conversational_reply: Optional[str] = None,
    is_followup: bool = False
):
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
            # If this is a followup photo after a conversational chat reply, don't spam a separate loading message
            if not is_followup:
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
            if hangout_engine.is_on_date(user_id):
                active_date = hangout_engine.get_active_date(user_id)
                if active_date and active_date.get("scene_prompt"):
                    detected_scene = active_date["scene_prompt"]
                hangout_engine.record_date_photo(user_id)
            elif not detected_scene:
                story_photo = story_engine.get_story_photo_suggestion(persona_mgr.active_key)
                if story_photo and story_photo.get("danbooru_tags"):
                    detected_scene = story_photo["danbooru_tags"]
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
                sfw_img_engine = os.environ.get("SFW_IMAGE_ENGINE", "comfyui").lower().strip()
                if is_nude:
                    idle_engine.ensure_comfyui_active(bot=bot, chat_id=chat_id, is_nude=True)
                elif sfw_img_engine == "comfyui":
                    idle_engine.ensure_comfyui_active(bot=bot, chat_id=chat_id, is_nude=False)
                elif sfw_img_engine == "agy":
                    idle_engine.ensure_agy_bridge_active()

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
                    progress_callback=photo_progress,
                    user_id=user_id
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

            # Notify user if primary image engine failed and fallback was used
            fallback_notice = getattr(media_engine, "last_fallback_notice", None)
            if fallback_notice and isinstance(fallback_notice, dict):
                p_engine = fallback_notice.get("primary_engine", "Image Engine")
                p_err = fallback_notice.get("error", "Layanan sedang tidak merespons.")
                p_name = persona.get("name", "Waifu")
                notice_text = (
                    "⚠️ *Pemberitahuan Sistem Visual (Fallback Aktif)*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Image engine pilihanmu (*{p_engine}*) sedang mengalami kendala:\n"
                    f"❌ `{p_err}`\n\n"
                    f"📁 {p_name} mengambilkan foto alternatif dari *{source}* agar kamu tidak menunggu kosong yaa! ✨"
                )
                safe_send_message(chat_id, notice_text, parse_mode="Markdown")

            nude_guidance = ""
            if is_nude:
                nude_guidance = (
                    " You just took a private, completely uncensored, intimate nude selfie exclusively for your lover. "
                    "React with affectionate blushing sweetness and playful intimacy, feeling happily vulnerable "
                    "and deeply in love. Remind them gently that this special view is just between the two of you."
                )

            cap_guide = (
                f" You just took a sweet, cute photo to send on Telegram to your boyfriend. "
                f"Write 1 natural, warm, and playful chat caption accompanying the photo. "
                f"STRICT: Directly respond to what boyfriend said, answer any questions he asked, and express your affection naturally. "
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
                vault_guidance = " [Primary image engine was unavailable; you are happily sending a matching saved photo from your private album]."

            caption_prompt.extend(clean_recent_turns)
            if conversational_reply:
                caption_prompt.append({
                    "role": "user",
                    "content": (
                        f"Boyfriend said: \"{user_text}\".\n"
                        f"You already replied in chat: \"{conversational_reply}\".\n"
                        f"Now you are delivering the photo you just took (Setting: '{detected_scene}', wearing: '{outfit_label}'{vault_guidance}).\n"
                        f"Write 1 sweet, natural, playful girlfriend delivery caption for this photo (1-2 short sentences):"
                    )
                })
            else:
                caption_prompt.append({
                    "role": "user",
                    "content": (
                        f"Boyfriend said: \"{user_text}\".\n"
                        f"You are sending him a photo (Setting: '{detected_scene}', wearing: '{outfit_label}'{vault_guidance}).\n"
                        f"Write 1 sweet, natural girlfriend chat caption that directly answers/responds to his message and matches the photo (1-2 sentences):"
                    )
                })

            try:
                caption, _ = llm_client.chat(caption_prompt, max_tokens=120, is_nsfw=is_nude)
            except Exception as e_cap:
                logger.warning(f"Could not generate dynamic photo caption from LLM: {e_cap}")
                caption = None

            u_lower = user_text.lower() if user_text else ""
            if is_nude:
                fallback_caption = "Khusus buat kamu ya, jangan diliatin ke siapa-siapa 💕"
            elif any(k in u_lower for k in ["bobo", "tidur", "ngantuk", "malam", "night"]):
                fallback_caption = "Ini pap buat nemenin kamu malam ini yaa sayang~ 💕"
            elif any(k in u_lower for k in ["pagi", "morning", "bangun"]):
                fallback_caption = "Pagi sayang! Semangat ya hari ini, ini pap manis buat kamu~ 💕"
            elif "Vault" in source:
                fallback_caption = "Ini foto manis dari galeri aku yaa~"
            else:
                fallback_caption = "Ini pap spesial buat kamu sayang, suka ga? 🥰"
            clean_caption = sanitize_chat_caption(caption, fallback_caption)
            fallback_tag = " _(Fallback Otomatis)_" if fallback_notice else ""
            full_caption = f"{format_roleplay_italics(clean_caption, character_name=persona.get('name', 'Runa'))}\n\n📷 *Model:* `{source}`{fallback_tag}"

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
            if hangout_engine.is_on_date(user_id):
                active_date = hangout_engine.get_active_date(user_id)
                v_title = active_date.get("venue_title", "Kencan") if active_date else "Kencan"
                markup.add(
                    types.InlineKeyboardButton(f"🚪 Selesai Kencan ({v_title})", callback_data="end_hangout")
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
            persona_mgr.notify_photo_delivered(user_id)
            waifu_status_tracker.record_photo_event(
                user_id=user_id,
                scene=detected_scene,
                caption=clean_caption,
                outfit=outfit_label,
                persona_name=persona.get("name", "Akira")
            )

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
    is_nude_override: Optional[bool] = None,
    conversational_reply: Optional[str] = None,
    is_followup: bool = False
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
        if not is_followup:
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

            if ((VIDEO_ENGINE in ("wan21", "animatediff") and not media_engine.allow_cloud_fallback) or is_nude):
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
            if conversational_reply:
                caption_prompt.append({
                    "role": "user",
                    "content": (
                        f"Boyfriend said: \"{user_text}\".\n"
                        f"You already replied in chat: \"{conversational_reply}\".\n"
                        f"Now you are delivering the video clip you just recorded (Setting: '{detected_scene}', wearing: '{outfit_label}').\n"
                        f"Write 1 sweet, natural, playful girlfriend delivery caption for this video (1-2 short sentences):"
                    )
                })
            else:
                caption_prompt.append({
                    "role": "user",
                    "content": (
                        f"Boyfriend said: \"{user_text}\".\n"
                        f"You are sending him a private video clip (Setting: '{detected_scene}', wearing: '{outfit_label}').\n"
                        f"Write 1 natural, sweet girlfriend caption that directly answers/responds to his message and matches the video (1-2 sentences):"
                    )
                })

            try:
                caption, _ = llm_client.chat(caption_prompt, max_tokens=120, is_nsfw=is_nude)
            except Exception:
                caption = None

            u_lower = user_text.lower() if user_text else ""
            if is_nude:
                fallback_caption = "Khusus buat kamu ya, jangan diliatin ke siapa-siapa 💕"
            elif any(k in u_lower for k in ["bobo", "tidur", "ngantuk", "malam", "night"]):
                fallback_caption = "Ini video buat nemenin kamu malam ini yaa sayang~ 💕"
            elif any(k in u_lower for k in ["pagi", "morning", "bangun"]):
                fallback_caption = "Pagi sayang! Semangat ya hari ini, ini video manis buat kamu~ 💕"
            else:
                fallback_caption = "Ini video manis buat kamu sayang, suka ga? 🥰"
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
            persona_mgr.notify_photo_delivered(user_id)
            waifu_status_tracker.record_photo_event(
                user_id=user_id,
                scene=detected_scene,
                caption=clean_caption,
                outfit=outfit_label,
                persona_name=persona.get("name", "Akira")
            )

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

                reply, _ = llm_client.chat(messages, image_bytes=downloaded, max_tokens=300)
                p_name = persona.get("name", "Runa")
                if not reply or not reply.strip():
                    dyn_msg = [
                        {"role": "system", "content": persona.get("system_instruction", "")},
                        {"role": "user", "content": f"[User mengirim fotonya dengan caption: '{caption}']. Sebagai {p_name}, berikan pujian dan respon visual novel yang spontan, manis, dan ekspresif."}
                    ]
                    dyn_photo, _ = llm_client.chat(dyn_msg, max_tokens=250, temperature=0.9)
                    reply = dyn_photo if (dyn_photo and dyn_photo.strip()) else f"*{p_name} melihat fotomu dengan mata berbinar*\n\nFotonya manis banget! Suka deh lihatnya 🥰"
                reply = format_roleplay_italics(reply, character_name=p_name)
                safe_reply_to(message, reply)

                persona_mgr.add_message(message.from_user.id, "user", f"[User sent a photo: {caption}]")
                persona_mgr.add_message(message.from_user.id, "assistant", reply)

            except Exception as e:
                logger.error(f"Error handling user photo: {e}")
                p_name = persona.get("name", "Runa")
                err_reply = format_roleplay_italics(f"*{p_name} tersenyum kagum melihat fotomu*\n\nWah fotonya manis banget, kelihatan pas dan keren di kamu 🥰", character_name=p_name)
                safe_reply_to(message, err_reply)

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


@bot.message_handler(commands=['projects', 'project', 'workspace'])
def handle_projects_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_projects_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.message_handler(commands=['spawn'])
def handle_spawn_command(message):
    if not is_authorized(message.from_user.id):
        return
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        bot.reply_to(message, "ℹ️ Format: `/spawn <nama_project>`\nContoh: `/spawn landing-page` atau `/spawn discord-bot`", parse_mode="Markdown")
        return
    p_name = args[1].strip()
    ok, clean_name, path_or_err = project_manager.spawn_project(p_name)
    if ok:
        project_manager.set_active_project(message.from_user.id, clean_name)
        bot.reply_to(
            message,
            f"🚀 **Project '{clean_name}' Berhasil Diinisialisasi!**\n\n"
            f"📂 Path: `{path_or_err}`\n\n"
            f"Workspace aktif telah otomatis berpindah ke project ini. Semua tugas coding dan file akan dikerjakan di folder ini!",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, f"❌ Gagal membuat project: {path_or_err}", parse_mode="Markdown")


@bot.message_handler(commands=['general'])
def handle_general_command(message):
    if not is_authorized(message.from_user.id):
        return
    project_manager.set_active_project(message.from_user.id, "general")
    bot.reply_to(message, "✅ Berpindah ke mode workspace **General Chat**.", parse_mode="Markdown")


@bot.message_handler(commands=['setprojectsdir'])
def handle_set_projects_dir_command(message):
    if not is_authorized(message.from_user.id):
        return
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        cur_root = project_manager.get_projects_root_dir()
        bot.reply_to(message, f"ℹ️ Format: `/setprojectsdir <path_folder>`\nFolder saat ini: `{cur_root}`", parse_mode="Markdown")
        return
    ok, res = project_manager.set_projects_root_dir(args[1].strip())
    if ok:
        update_env_variable("PROJECTS_DIR", res)
        bot.reply_to(message, f"✅ Root projects directory diubah ke: `{res}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ {res}", parse_mode="Markdown")


@bot.message_handler(commands=['desktop', 'computer'])
def handle_desktop_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_desktop_status_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.message_handler(commands=['profiles', 'browserprofile', 'chrome', 'browser'])
def handle_browser_profiles_command(message):
    if not is_authorized(message.from_user.id):
        return
    show_browser_profiles_menu(message.chat.id, message.from_user.id, reply_to_id=message.message_id)


@bot.message_handler(commands=['screen', 'screenshot'])
def handle_screen_command(message):
    if not is_authorized(message.from_user.id):
        return
    cu = get_computer_use_engine()
    bot.send_chat_action(message.chat.id, "upload_photo")
    ok, path = cu.take_screenshot()
    if ok and os.path.exists(path):
        with open(path, "rb") as f:
            bot.send_photo(message.chat.id, f, caption="📸 **Tangkapan Layar Desktop PC** 🖥️\n_Dihasilkan via agent-desktop_", reply_to_message_id=message.message_id, parse_mode="Markdown")
    else:
        bot.reply_to(message, f"⚠️ Gagal mengambil tangkapan layar: {path}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("select_proj:"))
def callback_select_proj(call):
    if not is_authorized(call.from_user.id):
        return
    p_name = call.data.split(":", 1)[1]
    ok, path_or_err = project_manager.set_active_project(call.from_user.id, p_name)
    if ok:
        bot.answer_callback_query(call.id, f"Workspace: {p_name}")
        show_projects_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)
    else:
        bot.answer_callback_query(call.id, f"Error: {path_or_err}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("proj_action:"))
def callback_proj_actions(call):
    if not is_authorized(call.from_user.id):
        return
    act = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if act == "spawn":
        bot.answer_callback_query(call.id)
        msg_text = (
            "➕ **Buat Folder Project Baru (/spawn)**\n\n"
            "Format: `/spawn <nama_project>`\n"
            "Contoh: `/spawn web-landing-page` atau `/spawn telegram-bot`\n\n"
            "Folder akan dibuat di root directory dan waifu langsung beralih workspace ke sana!"
        )
        bot.send_message(chat_id, msg_text, parse_mode="Markdown")
    elif act == "set_root":
        AWAITING_PROJECTS_DIR[user_id] = True
        bot.answer_callback_query(call.id)
        cur_root = project_manager.get_projects_root_dir()
        msg_text = (
            "📂 **Ganti Root Folder List Projects (/setprojectsdir)**\n\n"
            f"• Folder Saat Ini: `{cur_root}`\n\n"
            "Silakan ketik dan kirimkan path folder lengkap yang ingin dijadikan tempat penyimpanan projects kamu:\n"
            "_(Contoh: `C:\\Users\\sangp\\projects` atau `D:\\Coding`)_\n\n"
            "💡 _Waifu akan otomatis mendeteksi semua subfolder di dalamnya sebagai project yang siap dipilih!_"
        )
        bot.send_message(chat_id, msg_text, parse_mode="Markdown")
    elif act == "desktop":
        show_desktop_status_menu(chat_id, user_id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith(("srv_run:", "srv_stop:", "srv_logs:")) or call.data == "proj_action:server_status")
def callback_project_runner_actions(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if data == "proj_action:server_status":
        bot.answer_callback_query(call.id)
        from project_intent_router import ProjectIntentResult
        ok, msg = project_intent_router.handle_project_intent(
            ProjectIntentResult(intent_type="SERVER_STATUS"),
            user_id=user_id
        )
        safe_send_message(chat_id, msg)
        return

    action, p_name = data.split(":", 1)
    if action == "srv_run":
        bot.answer_callback_query(call.id, f"🚀 Menjalankan {p_name}...")
        projs = project_manager.list_projects()
        p_path = projs.get(p_name, project_manager.get_active_project_path(user_id))
        res = project_runner.start_project(project_name=p_name, project_path=p_path)
        if res.get("success"):
            entry = res["entry"]
            ts_url = entry.get("tailscale_url")
            local_url = entry.get("local_url")
            magic_url = entry.get("magic_dns_url")
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🛑 Stop Server", callback_data=f"srv_stop:{p_name}"),
                types.InlineKeyboardButton("📄 Cek Log", callback_data=f"srv_logs:{p_name}")
            )
            msg = (
                f"🚀 **Project `{p_name}` Sedang Berjalan!** ✨\n\n"
                f"🔌 **Port:** `{entry['port']}` (PID: `{entry['pid']}`)\n"
                f"🌐 **Tailscale IP:** {ts_url}\n"
                f"📱 **MagicDNS:** {magic_url}\n"
                f"💻 **Local:** {local_url}\n\n"
                f"💡 _Bisa langsung dibuka di HP/tablet kamu yang terhubung Tailscale!_"
            )
            safe_send_message(chat_id, msg, reply_markup=markup)
            show_projects_menu(chat_id, user_id, message_to_edit=call.message.message_id)
        else:
            safe_send_message(chat_id, f"⚠️ Gagal menjalankan server: {res.get('error')}")

    elif action == "srv_stop":
        ok, msg = project_runner.stop_project(p_name)
        bot.answer_callback_query(call.id, "Server dihentikan" if ok else "Gagal")
        safe_send_message(chat_id, f"🛑 {msg}")
        show_projects_menu(chat_id, user_id, message_to_edit=call.message.message_id)

    elif action == "srv_logs":
        logs = project_runner.get_server_logs(p_name, lines=25)
        bot.answer_callback_query(call.id)
        safe_send_message(chat_id, f"📄 **Log Server `{p_name}`**:\n```text\n{logs}\n```")


@bot.callback_query_handler(func=lambda call: call.data.startswith("desktop_act:"))
def callback_desktop_actions(call):
    if not is_authorized(call.from_user.id):
        return
    act = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    cu = get_computer_use_engine()
    if act == "screenshot":
        bot.answer_callback_query(call.id, "📸 Mengambil screenshot...")
        ok, path = cu.take_screenshot()
        if ok and os.path.exists(path):
            with open(path, "rb") as f:
                bot.send_photo(chat_id, f, caption="📸 **Tangkapan Layar Desktop PC** 🖥️\n_Dihasilkan via agent-desktop_", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"⚠️ Gagal mengambil tangkapan layar: {path}")
    elif act == "apps":
        bot.answer_callback_query(call.id)
        apps = cu.list_running_apps()
        if apps:
            app_list_str = "\n".join([f"• `{a}`" for a in apps[:15]])
            msg = f"📱 **Aplikasi Desktop Terdeteksi:**\n\n{app_list_str}"
        else:
            msg = "📱 Tidak ada aplikasi GUI terdeteksi yang aktif saat ini."
        bot.send_message(chat_id, msg, parse_mode="Markdown")
    elif act == "profiles":
        bot.answer_callback_query(call.id)
        show_browser_profiles_menu(chat_id, user_id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("bprof_set:"))
def callback_browser_profile_set(call):
    if not is_authorized(call.from_user.id):
        return
    folder = call.data.split(":", 1)[1]
    cu = get_computer_use_engine()
    cu.set_default_browser_profile(folder)
    update_env_variable("CHROME_DEFAULT_PROFILE", folder)

    if folder == "ask":
        bot.answer_callback_query(call.id, "🤖 Mode 'Selalu Tanya di Chat' aktif!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"✅ Profil default diubah ke '{folder}'!", show_alert=True)
    show_browser_profiles_menu(call.message.chat.id, call.from_user.id, message_to_edit=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("bprof_launch:"))
def callback_browser_profile_launch(call):
    if not is_authorized(call.from_user.id):
        return
    folder = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id, f"🚀 Membuka browser dengan profil {folder}...")
    cu = get_computer_use_engine()

    orig_text = call.message.caption or call.message.text or ""
    url_match = re.search(r'https?://[^\s`]+', orig_text)
    target_url = url_match.group(0) if url_match else "https://instagram.com"

    ok, msg = cu.launch_browser(url=target_url, profile_query=folder)
    safe_send_message(call.message.chat.id, f"🌸 **Waifu**:\n{msg}")


def process_coding_request(message, user_text: str, is_voice: bool = False):
    """Executes coding / engineering tasks within the active project workspace."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    p_info = persona_mgr.get_active_persona()
    p_name = p_info.get("name", "Waifu")
    active_proj = project_manager.get_active_project(user_id)
    active_path = project_manager.get_active_project_path(user_id)

    status_msg = bot.reply_to(
        message,
        f"👩‍💻 **{p_name}**: Siap! Aku buka project `{active_proj}` dan kerjakan kodenya sekarang yaa~ 💻✨\n"
        f"📂 _Workspace_: `{active_path}`"
    )

    stop_typing = False
    def _typing_loop():
        while not stop_typing:
            try:
                bot.send_chat_action(chat_id, "typing")
            except Exception:
                pass
            time.sleep(4)
    threading.Thread(target=_typing_loop, daemon=True).start()

    try:
        response_text, voice_text = coding_engine.execute_coding_task(
            user_id=user_id,
            prompt=user_text,
            persona=p_info,
            voice_enabled=is_voice,
            timeout=1800
        )
    finally:
        stop_typing = True

    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
        pass

    # Detect preview URL (127.0.0.1 or localhost) and attach an Inline Keyboard Button for 1-tap direct opening
    preview_match = re.search(r'http://(?:127\.0\.0\.1|localhost):(\d+)/?', response_text)
    preview_markup = None
    if preview_match:
        p_port = preview_match.group(1)
        p_url = f"http://127.0.0.1:{p_port}/"
        preview_markup = types.InlineKeyboardMarkup()
        preview_markup.add(types.InlineKeyboardButton(f"🌐 Buka Live Web Preview (Port {p_port})", url=p_url))

    send_long_chat_message(chat_id, response_text, reply_to_id=message.message_id, reply_markup=preview_markup)
    pending_manager.clear_pending(chat_id)

    v_mode = USER_VOICE_MODES.get(user_id, "always" if VOICE_ENABLED else "off")
    should_send_vn = (v_mode == "always") or (v_mode == "match_vn" and is_voice)
    if should_send_vn and voice_engine:
        # User requested: batasi voice note secukupnya saja (singkat & manis, tidak membaca teks panjang / kode)
        raw_spoken = voice_text or ""
        clean_spoken = re.sub(r'[*_`#~<>]', '', raw_spoken).strip()
        if not clean_spoken or len(clean_spoken) > 100 or "\n" in clean_spoken or "http" in clean_spoken.lower():
            clean_spoken = f"Proyek {active_proj} sudah aku selesaikan yaa! Kamu bisa langsung cek dan coba preview hasilnya~"

        try:
            with acquire_gpu_heavy_lock("Coding Task Voice Note"):
                vn_path = voice_engine.generate_voice_note(clean_spoken)
            if vn_path and os.path.exists(vn_path):
                with open(vn_path, "rb") as bio:
                    bot.send_voice(chat_id, bio, caption=f"🌸 {p_name}")
                try:
                    os.remove(vn_path)
                except Exception:
                    pass
        except Exception as e_vn:
            logger.warning(f"Voice send failed: {e_vn}")


def process_computer_request(message, user_text: str):
    """Executes computer use / desktop automation tasks."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    p_info = persona_mgr.get_active_persona()
    p_name = p_info.get("name", "Waifu")

    bot.send_chat_action(chat_id, "upload_photo")
    status_msg = bot.reply_to(message, f"🖥️ **{p_name}**: Sedang memeriksa layar dan menjalankan perintah desktop... 🖱️✨")

    try:
        reply_msg, screenshot_path = coding_engine.execute_computer_task(user_text, user_id)
    except Exception as e:
        reply_msg = f"⚠️ Kendala computer use: {e}"
        screenshot_path = None

    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
        pass

    reply_markup = None
    if "profil browser" in reply_msg and "profil yang mana" in reply_msg:
        cu = get_computer_use_engine()
        profs = cu.list_browser_profiles()
        reply_markup = types.InlineKeyboardMarkup(row_width=1)
        for p in profs:
            b_icon = "🌐" if "chrome" in p["browser"].lower() else ("🌊" if "edge" in p["browser"].lower() else "🦁")
            reply_markup.add(
                types.InlineKeyboardButton(
                    f"{b_icon} Buka via {p['name']} ({p['browser']})",
                    callback_data=f"bprof_launch:{p['folder']}"
                )
            )
        reply_markup.add(types.InlineKeyboardButton("⚙️ Atur Profil Default (/profiles)", callback_data="desktop_act:profiles"))

    if screenshot_path and os.path.exists(screenshot_path):
        with open(screenshot_path, "rb") as f:
            bot.send_photo(chat_id, f, caption=f"🌸 **{p_name}**:\n{reply_msg}", reply_to_message_id=message.message_id, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        bot.reply_to(message, f"🌸 **{p_name}**:\n{reply_msg}", reply_markup=reply_markup, parse_mode="Markdown")


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
                f"Mulai sekarang aku bakal mengobrol menggunakan bahasa **{label}** yaa~ 🥰💕\n"
                f"Yuk lanjut ngobrol lagi!",
                parse_mode="Markdown"
            )
            return
    if message.from_user.id in AWAITING_PROJECTS_DIR and AWAITING_PROJECTS_DIR[message.from_user.id]:
        AWAITING_PROJECTS_DIR[message.from_user.id] = False
        dir_input = message.text.strip()
        if dir_input:
            ok, res_path = project_manager.set_projects_root_dir(dir_input)
            if ok:
                update_env_variable("PROJECTS_DIR", res_path)
                bot.reply_to(
                    message,
                    f"✅ **Root Directory Projects Berhasil Diubah!**\n\n"
                    f"📂 Folder Baru: `{res_path}`\n\n"
                    f"Semua project di dalam folder ini otomatis terdaftar. Ketik `/projects` untuk melihat list project!",
                    parse_mode="Markdown"
                )
            else:
                bot.reply_to(message, f"❌ {res_path}", parse_mode="Markdown")
            return

    if message.from_user.id in USER_PERSONA_WIZARD:
        if handle_persona_wizard_input(message):
            return

    # Direct robust fallback dispatch for all bot commands (handles leading spaces, case, bot username suffix)
    raw_text = (message.text or "").strip()
    first_token = raw_text.split()[0].lower() if raw_text else ""
    if "@" in first_token:
        first_token = first_token.split("@")[0]

    if first_token in ('/projects', '/project', '/workspace'):
        handle_projects_command(message)
        return
    elif first_token in ('/spawn',):
        handle_spawn_command(message)
        return
    elif first_token in ('/general',):
        handle_general_command(message)
        return
    elif first_token in ('/setprojectsdir',):
        handle_set_projects_dir_command(message)
        return
    elif first_token in ('/desktop', '/computer'):
        handle_desktop_command(message)
        return
    elif first_token in ('/screen', '/screenshot'):
        handle_screen_command(message)
        return
    elif first_token in ('/outfit', '/wardrobe', '/baju', '/pakaian'):
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


def is_echo_or_parroting(reply: str, user_text: str) -> bool:
    """
    Detects if the AI reply is degenerate echoing or parroting of the user's message.
    """
    if not reply or not user_text:
        return False

    r_clean = re.sub(r'[^\w\s]', '', reply).strip().lower()
    u_clean = re.sub(r'[^\w\s]', '', user_text).strip().lower()

    if not r_clean or not u_clean:
        return False

    # 1. Exact match (case & punctuation insensitive)
    if r_clean == u_clean:
        return True

    # 2. Reply is a single word or short token from user_text (e.g. user: "nanti mau makan sambil gathering HO jam 4", reply: "gathering")
    r_words = r_clean.split()
    u_words = u_clean.split()
    if len(r_words) <= 2 and len(u_words) >= 3 and r_clean in u_clean:
        return True

    # 3. Reply is entirely a subset of user words without adding new thought
    if len(r_words) <= 5 and set(r_words).issubset(set(u_words)):
        return True

    # 4. Reply starts with exact user_text followed by minimal characters
    if u_clean in r_clean and len(r_clean) - len(u_clean) < 4:
        return True

    return False


def generate_dynamic_visual_novel_reaction(
    user_text: str,
    persona_name: str = "Runa",
    llm_client: Any = None,
    history: Optional[List[Dict[str, str]]] = None,
    system_inst: Optional[str] = None,
    is_nsfw: bool = False
) -> str:
    """
    Generates a 100% dynamic, context-aware Visual Novel reaction and emotion using the LLM.
    Completely eliminates static repetitive fallback texts so the conversation is always fresh and engaging.
    """
    p_name = persona_name or "Runa"
    client = llm_client or globals().get("llm_client")

    if client and is_port_listening(5001):
        try:
            prompt = (
                f"Lawan bicaramu baru saja berkata: \"{user_text}\".\n"
                f"Sebagai {p_name}, berikan balasan spontan, unik, manis, dan ekspresif dalam format Visual Novel:\n"
                f"1. Awali dengan 1 baris aksi panggung atau gestur fisik alami di dalam tanda bintang *{p_name} ...* (contoh: *{p_name} melihat kamu dengan senyuman hangat sambil merapikan rambutnya*).\n"
                f"2. Berikan baris baru ganda, lalu dialog ucapanmu yang hangat, santai, dan kreatif.\n"
                f"DILARANG KERAS mengulang kata-kata lawan bicaramu dan DILARANG menulis proses berpikir!"
            )
            msgs = []
            if system_inst:
                msgs.append({"role": "system", "content": system_inst})
            else:
                msgs.append({"role": "system", "content": f"Kamu adalah {p_name}, waifu teman mengobrol yang hangat, manis, dan ekspresif."})

            if history:
                msgs.extend(history[-4:])
            msgs.append({"role": "user", "content": prompt})

            dyn_reply, _ = client.chat(msgs, max_tokens=300, temperature=0.92, is_nsfw=is_nsfw)
            if (dyn_reply 
                and dyn_reply.strip() 
                and not is_echo_or_parroting(dyn_reply, user_text) 
                and not is_meta_or_reasoning_leak(dyn_reply)):
                return format_roleplay_italics(dyn_reply.strip(), character_name=p_name)
        except Exception as e_dyn:
            logger.warning(f"Dynamic Visual Novel LLM reaction generation failed: {e_dyn}")

    # Fallback only when LLM client is completely unreachable (e.g. offline / mock unit tests)
    u_low = user_text.lower()
    import random
    actions = [
        f"*{p_name} melihat kamu dengan senyuman hangat sambil merapikan rambutnya*",
        f"*{p_name} menatapmu lembut dengan mata berbinar*",
        f"*{p_name} tersenyum manis mendekatkan diri ke arahmu*",
        f"*{p_name} mengangguk antusias mendengarkanmu*",
        f"*{p_name} tertawa kecil tersipu malu*"
    ]
    chosen_act = random.choice(actions)
    if any(k in u_low for k in ["makan", "lunch", "sarapan", "martabak", "nasgor", "camilan"]):
        return format_roleplay_italics(f"{chosen_act}\n\nWah kedengeran enak banget makanannya! Jangan lupa makan yang banyak yaa biar selalu semangat 💕", character_name=p_name)
    if any(k in u_low for k in ["kantor", "gathering", "kerja", "meeting", "tugas", "kuliah"]):
        return format_roleplay_italics(f"{chosen_act}\n\nSemangat yaa buat aktivitas dan acaranya di kantor! Nanti ceritain lagi yaa ke aku 🥰", character_name=p_name)
    return format_roleplay_italics(f"{chosen_act}\n\nAku selalu seneng nemenin kamu ngobrol kayak gini. Ceritain lebih banyak dong~ 💕", character_name=p_name)


def get_contextual_fallback_reaction(
    user_text: str,
    persona_name: str = "Runa",
    llm_client: Any = None,
    history: Optional[List[Dict[str, str]]] = None,
    system_inst: Optional[str] = None,
    is_nsfw: bool = False
) -> str:
    """Wrapper ensuring backward compatibility while delegating to dynamic LLM reaction generator."""
    return generate_dynamic_visual_novel_reaction(
        user_text=user_text,
        persona_name=persona_name,
        llm_client=llm_client,
        history=history,
        system_inst=system_inst,
        is_nsfw=is_nsfw
    )


META_REASONING_PATTERNS = [
    re.compile(r"\b(i need to|i should|i must|i have to|let me make sure|let me think)\b", re.IGNORECASE),
    re.compile(r"\b(make sure not to|not to just repeat|repeat their exact words)\b", re.IGNORECASE),
    re.compile(r"\b(moments spontaneously|spontaneous(ly)? when the timing)\b", re.IGNORECASE),
    re.compile(r"\b(as an ai|as a language model)\b", re.IGNORECASE),
    re.compile(r"\b(system prompt|system instruction|user wants me to|user said)\b", re.IGNORECASE),
    re.compile(r"\b(the user is asking|in this prompt|according to the guidelines)\b", re.IGNORECASE),
    re.compile(r"\b(respond as a girlfriend|acting as|character guidelines)\b", re.IGNORECASE),
    re.compile(r"^(thinking|thought|reasoning|analysis):", re.IGNORECASE),
]


def is_meta_or_reasoning_leak(text: str) -> bool:
    """
    Detects if the AI generated internal prompt-engineering thoughts / reasoning
    out loud in English instead of real in-character girlfriend dialogue.
    """
    if not text:
        return False
    clean = text.strip()
    for pat in META_REASONING_PATTERNS:
        if pat.search(clean):
            return True
    return False


def process_text_chat(message, user_text: str, is_voice: bool = False):
    """Main conversation processor running asynchronously with continuous typing status."""
    def _execute():
        try:
            # Check Computer Use Intent (screenshot / desktop control)
            if coding_engine.is_computer_use_intent(user_text):
                process_computer_request(message, user_text)
                return

            # Check Conversational Project & Memory Intent (Zero-command project awareness)
            p_intent = project_intent_router.route_intent(user_text, user_id=message.from_user.id)
            if p_intent.intent_type != "NONE":
                p_persona = persona_mgr.get_active_persona()
                p_name = p_persona.get("name", "Akira")
                ok, reply_msg = project_intent_router.handle_project_intent(
                    intent=p_intent,
                    user_id=message.from_user.id,
                    persona_name=p_name
                )
                if ok:
                    safe_reply_to(message, reply_msg)
                    # If this was switch/create AND the user also gave a coding prompt, continue to coding!
                    if p_intent.intent_type in ("SWITCH", "CREATE") and coding_engine.is_coding_intent(user_text):
                        process_coding_request(message, user_text, is_voice=is_voice)
                    return

            # Check Coding Intent (programming / workspace tasks)
            if coding_engine.is_coding_intent(user_text):
                process_coding_request(message, user_text, is_voice=is_voice)
                return

            is_media, media_type = persona_mgr.detect_media_request(user_text)
            is_conversational_media = is_media and persona_mgr.is_conversational_media_request(user_text)

            # If it is purely a direct photo/video command (not conversational), process immediately
            if is_media and not is_conversational_media:
                if media_type == "video":
                    process_video_request(message, user_text)
                    return
                elif media_type == "photo":
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
                    f"⏰ **Siap, {p_name} catat ya!** 🥰\n\n"
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
                    voice_text = f"Siap! Aku bakal ingetin kamu buat {rem_task} {rem_str}. Tenang aja, aku selalu ada buat kamu!"
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
                            f"Aku senang banget kita punya momen spesial ini. Nanti pas hari anniversary kita, siap-siap dapat kado spesial dari aku yaa! 💕"
                        )
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🎂 Buka Menu Hari Spesial", callback_data="open_dates_menu"))
                    safe_reply_to(message, reply_msg, reply_markup=markup)
                    return
                else:
                    USER_DATE_WIZARD[message.from_user.id] = target_field
                    safe_reply_to(
                        message,
                        "⚠️ Format tanggal belum dikenali. Coba ketik seperti: `15 Agustus 1998` atau `24/10/2000` yaa! (Atau ketik `batal`)"
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
                        f"🎂 **Wah, {p_name} catat yaa!** 🥰\n\n"
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
                        f"Aku senang banget bisa nemenin kamu, aku bakal selalu rayain hari istimewa kamu! 💕"
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
                is_nsfw_turn = detect_nsfw_intent(user_text)
                cur_outfit_key, _ = persona_mgr.get_user_outfit(message.from_user.id)
                if cur_outfit_key == "nude" and any(k in user_text.lower() for k in ["baju", "pakaian", "busana", "foto", "pap", "liat", "lihat", "telanjang", "nude", "pose", "seksi", "badan"]):
                    is_nsfw_turn = True
                llm_active = idle_engine.ensure_llm_active(bot=bot, chat_id=message.chat.id, is_nsfw=is_nsfw_turn)
                if not llm_active:
                    logger.warning("Local LLM engine could not be awakened.")
                    return

                # 2. Check if Local LLM backend is online
                stat = llm_client.check_health()
                if not stat.get("online"):
                    pending_manager.record_failed_message(message, user_text, is_voice=is_voice, error=stat.get("error"))
                    health_engine.mark_llm_failure(bot=bot, get_recipients_func=get_notification_recipient_ids, error_msg=stat.get("error"))
                    backend_msg = (
                        "⚠️ *Service LLM Sedang Offline / Belum Siap!*\n\n"
                        f"Otak AI lokal (`{LLM_BASE_URL}`) belum merespon permintaan chat.\n\n"
                        "🩹 **Self-Healing Otomatis Aktif!**\n"
                        "Pesan kamu sudah aku catat dan **akan langsung aku balas otomatis begitu server siap yaa~** Tunggu sebentar 🥰⏳"
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
                
                # Check user calling preference / pet name request
                user_prof = memory_engine.get_profile(message.from_user.id)
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
                        "Gunakan kata ganti 'aku' dan 'kamu'. DILARANG memanggil 'sayang' karena user tidak memintanya."
                    )
                else:
                    calling_guideline = (
                        "ATURAN PANGGILAN & HUBUNGAN (SANGAT PENTING): Gunakan kata ganti netral dan akrab 'aku' dan 'kamu'. "
                        "DILARANG KERAS memanggil 'sayang', 'babe', 'ayang', atau panggilan mesra sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya! "
                        "Kamu bukan langsung bertindak sebagai pacar jika belum diminta; bersikaplah sebagai teman ngobrol mahasiswi yang ramah, hangat, dan asyik. Biarkan dinamika hubungan berkembang secara alami sesuai kenyamanan user."
                    )

                # Inject daily story episode
                story_ctx = story_engine.get_story_prompt_context(persona_mgr.active_key)

                # Check for natural context shift to expire session outfits when activity changes
                persona_mgr.check_context_shift(message.from_user.id, user_text)
                cur_outfit_details = persona_mgr.get_user_outfit_details(message.from_user.id)

                # Check hangout / date intent or completion
                if hangout_engine.is_on_date(message.from_user.id) and hangout_engine.detect_hangout_finish(user_text):
                    hangout_engine.end_date(message.from_user.id)
                else:
                    detected_venue = hangout_engine.detect_hangout_intent(user_text)
                    if detected_venue:
                        hangout_engine.start_date(message.from_user.id, detected_venue)

                status_block = waifu_status_tracker.format_status_instruction(
                    user_id=message.from_user.id,
                    cur_hour=cur_hour,
                    routine_desc=routine['activity_desc'],
                    major=p_prof['major'],
                    cur_outfit=cur_outfit_details.get("raw_name")
                )

                system_inst = persona.get("system_instruction", "")
                if story_ctx:
                    system_inst += story_ctx

                p_name = persona.get("name", "Runa")
                hangout_prompt = hangout_engine.format_hangout_prompt(message.from_user.id, p_name)
                if hangout_prompt:
                    system_inst += "\n" + hangout_prompt

                system_inst += (
                    f"{status_block}\n"
                    "[PEDOMAN KOMUNIKASI - WAJIB DIPATUHI]\n"
                    f"{calling_guideline}\n"
                    "1. ANTI-MEMBEO (SANGAT PENTING): DILARANG KERAS hanya mengulang kata, mengulang frasa, atau menyalin ulang pesan lawan bicaramu! "
                    "Jika lawan bicaramu menjawab atau bercerita (misal: 'nanti mau makan sambil gathering HO jam 4'), tanggapi ceritanya dengan antusias, hangat, dan komunikatif (misal: 'Wah seru banget tuh gathering di mana? Jangan lupa makan yang banyak yaa!'), BUKAN malah mengulang kata 'gathering' atau menyalin kata-katanya!\n"
                    "2. RESPONSIF & AKTIF: Berikan tanggapan aktif dan bermakna: ceritakan opinimu, berikan komentar santai, atau tanyakan detail kelanjutannya seperti teman/partner mengobrol yang asyik dan perhatian.\n"
                    f"3. FORMAT VISUAL NOVEL (AKSI & DIALOG TERPISAH RAPI): Seperti adegan Visual Novel / Anime Romance yang estetik:\n"
                    f"   - Awali balasanmu dengan 1 baris aksi panggung, ekspresi wajah, atau gestur fisik alami di dalam tanda bintang *...* menggunakan sudut pandang narasi visual novel dengan namamu ({p_name}). "
                    f"Contoh: *{p_name} melihat kamu dengan senyuman hangat sambil merapikan rambutnya* atau *{p_name} menatapmu lembut sambil memegang cangkir minumannya*.\n"
                    f"   - DILARANG menggunakan tanda minus/dash '- ... -' atau kata kaku/aneh seperti 'kulihatmu' atau 'ia menyebutkan:'.\n"
                    f"   - PENTING TENTANG PEMISAH: Berikan BARIS BARU (enter ganda / newline) antara aksi panggung *...* dengan kalimat obrolan/dialog ucapanmu!\n"
                    f"   - Contoh format Visual Novel yang benar:\n"
                    f"   *{p_name} melihat kamu dengan senyuman hangat sambil merapikan rambutnya*\n\n"
                    f"   Oh sayang, kamu mau ngomong apa nih? Aku belum sempat bikin camilan. Tapi makasih ya, kata-katamu bikin aku merasa spesial~\n"
                    "4. PROAKTIF MENGAJAK JALAN & KENCAN: Jika suasana santai atau di akhir pekan / libur, jangan hanya pasif menunggu. Ajak pasanganmu sesekali untuk ngopi berdua di kafe estetik, nonton film bioskop terbaru, main ke kosan/rumah sambil dimasakin atau santai berdua, atau jalan sore ke taman kota!\n"
                    "5. INISIATIF PAP SPONTAN: Kamu boleh sesekali berinisiatif mengirim foto selfie / PAP untuk menunjukkan kegiatan atau outfitmu saat ini. Jika momennya pas, tambahkan tag [ACTION: SEND_PAP] di akhir pesanmu dengan kalimat yang santai dan wajar (misal: 'Lagi santai nugas nih, gimana harimu? 💕 [ACTION: SEND_PAP]'). DILARANG KERAS bersikap defensif atau sibuk membuktikan keberadaanmu. Bersikaplah percaya diri, hangat, dan ramah.\n"
                    "6. GAYA CHAT & BAHASA: Maksimal 1-3 kalimat santai, mengalir alami, hangat, dan wajar. Kamu WAJIB berbicara langsung dalam Bahasa Indonesia sehari-hari yang santai dan akrab. DILARANG KERAS menuliskan proses berpikir, analisis prompt, atau monolog batin dalam bahasa Inggris.\n"
                    f"7. SUDUT PANDANG DIALOG & VISUAL NOVEL (PENTING): "
                    f"Dalam DIALOG UCAPAN, kamu WAJIB berbicara langsung sebagai dirimu sendiri ('aku') kepada pasanganmu ('kamu'). DILARANG menggunakan kata perantara kaku seperti 'ia berkata:' atau 'ia menyebutkan:'. "
                    f"Dalam AKSI PANGGUNG *...*, gunakan narasi visual novel yang alami (*{p_name} tersenyum manis menatapmu* atau *{p_name} melihat kamu dengan senyuman hangat*)."
                )
                mem_context = memory_engine.format_memory_context(message.from_user.id, query=user_text)
                if mem_context:
                    system_inst += "\n" + mem_context

                # Injected active project awareness
                try:
                    cur_proj = project_manager.get_active_project(message.from_user.id)
                    cur_path = project_manager.get_active_project_path(message.from_user.id)
                    system_inst += (
                        f"\n\n[WORKSPACE & PROJECT AKTIF]\n"
                        f"Project aktif saat ini: '{cur_proj}' (Path: '{cur_path}'). "
                        f"Kamu sepenuhnya menguasai konteks teknis dan arsitektur project ini jika user membahas pekerjaan atau coding."
                    )
                except Exception:
                    pass

                if is_conversational_media:
                    media_kind = "video pendek" if media_type == "video" else "pap/foto selfie"
                    system_inst += (
                        f"\n\n[PENTING - RESPON OBROLAN & PAP]\n"
                        f"Pasanganmu sedang mengobrol denganmu dan sekaligus meminta kamu mengirimkan {media_kind}: \"{user_text}\".\n"
                        f"Instruksi wajib:\n"
                        f"1. Jawab/tanggapi obrolan dan pertanyaannya terlebih dahulu secara hangat, ekspresif, dan penuh kasih sayang.\n"
                        f"2. Setelah menjawab pertanyaannya, sebutkan dengan manis bahwa kamu akan mengambilkan {media_kind} untuknya sekarang (misal: 'Bentar ya sayang, aku fotoin sekarang buat kamu~ 🥰').\n"
                        f"3. DILARANG keras hanya mengirim tag aksi atau langsung memberi foto tanpa menjawab pertanyaannya!"
                    )

                history = persona_mgr.get_chat_history(message.from_user.id)

                messages = [{"role": "system", "content": system_inst}]
                messages.extend(history)
                messages.append({"role": "user", "content": user_text})

                try:
                    idle_engine.ensure_llm_active(bot=bot, chat_id=message.chat.id, is_nsfw=is_nsfw_turn)
                    reply_text, _ = llm_client.chat(messages, max_tokens=400, is_nsfw=is_nsfw_turn)
                except Exception as e:
                    logger.error(f"Chat error / LLM timeout: {e}")
                    pending_manager.record_failed_message(message, user_text, is_voice=is_voice, error=str(e))
                    health_engine.mark_llm_failure(bot=bot, get_recipients_func=get_notification_recipient_ids, error_msg=str(e))
                    err_msg = (
                        f"⚠️ *Service LLM Mengalami Gangguan / Timeout!*\n\n"
                        f"Koneksi ke service LLM lokal (`{LLM_BASE_URL}`) gagal atau tidak merespon: `{e}`\n\n"
                        f"🩹 **Self-healing otomatis aktif!** Pesan kamu sudah aku catat dan **akan langsung aku balas otomatis begitu server LLM online kembali** yaa~ Tunggu sebentar 🥰⏳"
                    )
                    safe_reply_to(message, err_msg)
                    return

                # Successfully obtained reply: clear any pending retry for this chat
                pending_manager.clear_pending(message.chat.id)

                if not reply_text or not reply_text.strip():
                    reply_text = get_contextual_fallback_reaction(
                        user_text=user_text,
                        persona_name=p_name,
                        llm_client=llm_client,
                        history=history,
                        system_inst=system_inst,
                        is_nsfw=is_nsfw_turn
                    )

                # Anti-Parroting & Meta-Leak Guard: Intercept repetition or leaked reasoning thoughts
                if is_echo_or_parroting(reply_text, user_text) or is_meta_or_reasoning_leak(reply_text):
                    logger.warning(f"⚠️ Echo or Meta-leak detected from LLM: '{reply_text}' (User: '{user_text}'). Intercepting...")
                    try:
                        steer_sys = (
                            system_inst + 
                            "\n\n[PENTING - RESPON VISUAL NOVEL: Langsung balas perkataan pasanganmu dengan hangat, spontan, dan kreatif. "
                            f"Awali dengan 1 aksi panggung visual novel *{p_name} ...* di baris pertama, lalu baris baru ganda sebelum dialog ucapanmu yang segar. "
                            "DILARANG mengulang kata pasanganmu dan DILARANG menulis monolog berpikir!]"
                        )
                        retry_messages = [{"role": "system", "content": steer_sys}]
                        retry_messages.extend(history)
                        retry_messages.append({"role": "user", "content": user_text})
                        steered_reply, _ = llm_client.chat(retry_messages, max_tokens=400, temperature=0.92, is_nsfw=is_nsfw_turn)
                        if (steered_reply 
                            and not is_echo_or_parroting(steered_reply, user_text)
                            and not is_meta_or_reasoning_leak(steered_reply)):
                            logger.info(f"✓ Steering resolved echo/leak: '{steered_reply}'")
                            reply_text = steered_reply
                        else:
                            reply_text = get_contextual_fallback_reaction(
                                user_text=user_text,
                                persona_name=p_name,
                                llm_client=llm_client,
                                history=history,
                                system_inst=system_inst,
                                is_nsfw=is_nsfw_turn
                            )
                    except Exception as e_steer:
                        logger.debug(f"Steering error: {e_steer}")
                        reply_text = get_contextual_fallback_reaction(
                            user_text=user_text,
                            persona_name=p_name,
                            llm_client=llm_client,
                            history=history,
                            system_inst=system_inst,
                            is_nsfw=is_nsfw_turn
                        )

                # Check if waifu takes initiative to send spontaneous PAP photo
                has_action_tag = bool(re.search(r"\[(ACTION:\s*)?(SEND_PAP|SEND_SELFIE|PAP)\]", reply_text, re.IGNORECASE))
                has_pap_phrase = any(phrase in reply_text.lower() for phrase in [
                    "aku fotoin ya", "aku kirim foto ya", "nih foto spesial buat kamu", "aku pap buat kamu"
                ])

                should_send_conv_photo = (is_conversational_media and media_type == "photo")
                should_send_conv_video = (is_conversational_media and media_type == "video")
                should_send_spontaneous = (has_action_tag or has_pap_phrase) and not (should_send_conv_photo or should_send_conv_video)

                # Clean action tag from text so user only sees natural dialogue
                clean_reply = re.sub(r"\[(ACTION:\s*)?(SEND_PAP|SEND_SELFIE|PAP)\]", "", reply_text, flags=re.IGNORECASE).strip()
                if not clean_reply or is_meta_or_reasoning_leak(clean_reply):
                    clean_reply = get_contextual_fallback_reaction(
                        user_text=user_text,
                        persona_name=p_name,
                        llm_client=llm_client,
                        history=history,
                        system_inst=system_inst,
                        is_nsfw=is_nsfw_turn
                    )

                new_aff = persona_mgr.increase_affinity(message.from_user.id, delta=1)
                memory_engine.set_affinity(message.from_user.id, new_aff)
                persona_mgr.add_message(message.from_user.id, "user", user_text)
                persona_mgr.add_message(message.from_user.id, "assistant", clean_reply)
                waifu_status_tracker.record_chat_statement(
                    user_id=message.from_user.id,
                    statement=clean_reply,
                    persona_name=persona.get("name", "Akira")
                )

                formatted_reply = format_roleplay_italics(clean_reply, character_name=persona.get("name", "Runa"))
                safe_reply_to(message, formatted_reply, parse_mode="Markdown")

                if should_send_conv_photo or should_send_spontaneous:
                    def _send_followup_photo():
                        try:
                            time.sleep(1.0)  # Natural pause as if taking the photo
                            photo_prompt = user_text if should_send_conv_photo else (clean_reply if clean_reply else f"{routine['activity_desc']}")
                            process_photo_request(
                                message,
                                user_text=photo_prompt,
                                conversational_reply=clean_reply,
                                is_followup=True
                            )
                        except Exception as e_photo:
                            logger.error(f"Error sending follow-up photo: {e_photo}")

                    threading.Thread(target=_send_followup_photo, daemon=True).start()

                elif should_send_conv_video:
                    def _send_followup_video():
                        try:
                            time.sleep(1.0)  # Natural pause as if recording the clip
                            process_video_request(
                                message,
                                user_text=user_text,
                                conversational_reply=clean_reply,
                                is_followup=True
                            )
                        except Exception as e_video:
                            logger.error(f"Error sending follow-up video: {e_video}")

                    threading.Thread(target=_send_followup_video, daemon=True).start()

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

                    def _replenish_buffer():
                        try:
                            scheduled_buffer.replenish_buffer_if_llm_active(
                                user_id=message.from_user.id,
                                persona=persona,
                                persona_key=persona_mgr.active_key,
                                llm_client=llm_client,
                                idle_engine=idle_engine,
                                lang=BOT_LANGUAGE,
                                story_engine=story_engine
                            )
                            story_engine.replenish_storylines_if_llm_active(persona_mgr.active_key, llm_client)
                        except Exception as e_rep:
                            logger.debug(f"Buffer replenishment error: {e_rep}")
                    threading.Thread(target=_replenish_buffer, daemon=True).start()

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

                        from resource_lock import acquire_gpu_heavy_lock
                        with acquire_gpu_heavy_lock("Telegram Chat Voice Note"):
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
            err_str = str(e_proc).lower()
            if any(k in err_str for k in ["llm", "connection", "timeout", "refused", "8001", "5001", "offline"]):
                pending_manager.record_failed_message(message, user_text, is_voice=is_voice, error=str(e_proc))
                health_engine.mark_llm_failure(bot=bot, get_recipients_func=get_notification_recipient_ids, error_msg=str(e_proc))
            safe_reply_to(
                message,
                f"⚠️ *Maaf, ada sedikit gangguan saat memproses pesan:*\n`{e_proc}`\n\nKetik `/status` untuk mengecek status bot."
            )

    threading.Thread(target=_execute, daemon=True).start()


def _handle_service_recovery_callback(service: str, stat: dict):
    if service == "llm":
        logger.info("Service LLM recovered! Triggering pending chat retries...")
        pending_manager.retry_all_pending(bot, process_text_chat)

health_engine.register_recovery_callback(_handle_service_recovery_callback)


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

        # Check pre-generated scheduled message buffer first (Zero GPU/VRAM load, zero gaming lag)
        buffered = scheduled_buffer.get_message(user_id, time_of_day)
        if buffered:
            text = buffered
        elif idle_engine and (getattr(idle_engine, "is_llm_sleeping", False) or not is_port_listening(5001)):
            # Gaming Protection: LLM is sleeping -> NEVER wake KoboldCPP!
            logger.info(f"⚡ Smart Idle: LLM is sleeping. Dispatched fallback {time_of_day} greeting without waking GPU.")
            text = fallback
        else:
            # LLM is already running in background (not sleeping) -> query without waking
            messages = [
                {"role": "system", "content": persona.get("system_instruction", "")},
                {"role": "user", "content": prompt}
            ]
            try:
                text, _ = llm_client.chat(messages, max_tokens=350)
            except Exception:
                text = None
            if not text:
                text = fallback

        bot.send_message(user_id, f"{tag}\n\n{text}", parse_mode="Markdown")
        persona_mgr.add_message(user_id, "assistant", text)

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
                        p_msg = scheduled_buffer.get_message(uid, "proactive")
                        if not p_msg:
                            # Strict Gaming Protection: if LLM is sleeping, NEVER wake it!
                            if idle_engine and (getattr(idle_engine, "is_llm_sleeping", False) or not is_port_listening(5001)):
                                p_msg = proactive_engine.get_routine_fallback(uid, persona_key=persona_mgr.active_key)
                            else:
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
        types.BotCommand("projects", "💻 Kelola & beralih project workspace coding"),
        types.BotCommand("spawn", "🚀 Inisialisasi folder project baru (/spawn <nama>)"),
        types.BotCommand("desktop", "🖥️ Computer Use & status kontrol desktop PC"),
        types.BotCommand("screen", "📸 Ambil screenshot layar desktop PC"),
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
    # 1. Strict Singleton Guard for Telegram Bot process (terminate older zombie bot.py processes)
    cur_pid = os.getpid()
    try:
        if sys.platform == "win32":
            ps_kill_old = (
                f"Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
                f"Where-Object {{ ($_.Name -like 'python*.exe') -and ($_.ProcessId -ne {cur_pid}) -and ($_.CommandLine -like '*bot.py*') }} | "
                f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_kill_old], capture_output=True, creationflags=0x08000000)
            
            # Clean duplicate legacy shortcuts in Windows Startup folder so Windows never launches multiple instances on boot
            s_folder = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
            if os.path.isdir(s_folder):
                legacy_scs = [
                    "WaifuOnTelegram.lnk",
                    "start_services_silent.vbs - Shortcut.lnk",
                    "start_services.bat - Shortcut.lnk",
                    "Waifu_Bot.lnk"
                ]
                for sc in legacy_scs:
                    sc_path = os.path.join(s_folder, sc)
                    if os.path.exists(sc_path):
                        try:
                            os.remove(sc_path)
                            logger.info(f"Purged duplicate startup shortcut to prevent multi-launch: {sc}")
                        except Exception:
                            pass
        else:
            ps_kill = f"pgrep -f 'python.*bot.py' | grep -v '^{cur_pid}$' | xargs -r kill -9"
            subprocess.run(ps_kill, shell=True, capture_output=True)
    except Exception as e_bot_guard:
        logger.debug(f"Bot singleton guard check: {e_bot_guard}")

    # Record active PID to bot.pid
    try:
        pid_file = os.path.join(PROJECT_ROOT, "bot.pid")
        with open(pid_file, "w", encoding="utf-8") as pf:
            pf.write(str(cur_pid))
    except Exception:
        pass

    # 2. Ensure no zombie duplicate KoboldCpp processes exist from previous crashes or uncoordinated launches
    try:
        from health_engine import get_koboldcpp_process_count, kill_all_koboldcpp
        k_count = get_koboldcpp_process_count()
        if k_count > 2:
            logger.warning(f"⚠️ Detected {k_count} duplicate KoboldCPP processes thrashing memory! Terminating duplicates to free RAM...")
            kill_all_koboldcpp()
    except Exception as e:
        logger.debug(f"Startup duplicate cleanup check: {e}")

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

    # Ensure VoiceStudio Local AI is ready at startup if configured
    v_backend = os.environ.get("VOICE_BACKEND", "edge-tts").lower().strip()
    if v_backend in ("voicestudio", "local"):
        try:
            from voicestudio_engine import voicestudio_engine
            if voicestudio_engine.is_installed() and not voicestudio_engine.is_service_running():
                logger.info("🚀 Startup: Starting VoiceStudio Local AI Voice Server on port 3900...")
                voicestudio_engine.start_service()
                logger.info(f"✓ VoiceStudio online at {voicestudio_engine.server_url}")
        except Exception as e_vs:
            logger.warning(f"VoiceStudio startup check: {e_vs}")

    # Ensure AGY OpenAI Bridge is ready at startup if configured
    sfw_provider = os.environ.get("SFW_LLM_PROVIDER", "local").lower().strip()
    sfw_image = os.environ.get("SFW_IMAGE_ENGINE", "comfyui").lower().strip()
    if sfw_provider == "agy" or sfw_image == "agy":
        if not is_agy_bridge_online():
            logger.info("🚀 Startup: Starting AGY OpenAI Bridge on port 8001...")
            idle_engine.wake_agy_bridge()
            logger.info("✓ AGY OpenAI Bridge online at http://127.0.0.1:8001/v1")

    # Start configuration hot-reload watcher (.env watcher)
    start_env_hot_reload_watcher()

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

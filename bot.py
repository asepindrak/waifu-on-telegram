import os
import sys
import logging
import threading
import time
from typing import Optional
from dotenv import load_dotenv
import telebot
from telebot import types

from lu_llm_client import LocallyUncensoredClient
from persona_manager import PersonaManager
from media_engine import MediaEngine
from voice_engine import VoiceEngine
from code_runner import CodeRunner

# Load environment configuration
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("WaifuOnTelegram")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

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


@bot.message_handler(commands=['start', 'help'])
def handle_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "⛔ Access denied. Your Telegram User ID is not authorized.")
        return

    # Ensure command menu is registered on Telegram
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
        types.InlineKeyboardButton("💖 Cek Cinta (/love)", callback_data="check_love_status")
    )

    # 1. Send Persona Reference Photo from personas/brief
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
        f"✨ **Fitur Utama Bersama {name}:**\n"
        "• 💬 **Romance Chat**: Bebas sensor, hangat, manja, dan otomatis ikut bahasamu.\n"
        "• 📸 **Kirim Selfie & Foto**: Cukup ketik *'sayang pap foto dong'* atau `/pap`!\n"
        "• 👗 **Pilihan Baju**: Pilih pakaian waifumu lewat `/outfit` (Kimono, Maid, Piyama, dll).\n"
        "• 🎙️ **Voice Note**: Balasan suara asli wanita jernih & manis (`/voice`).\n"
        "• ⏰ **Sapaan Otomatis**: Ucapan selamat pagi jam 7 & selamat tidur jam 10 malam (`/greetings`).\n"
        "• 👀 **AI Vision**: Kirimkan foto kamu ke sini, waifu bisa melihat dan meresponsnya.\n\n"
        "📌 **Perintah Cepat:**\n"
        "• `/photo <skenario>` atau `/pap` - Minta foto dengan tombol variasi pose\n"
        "• `/ratio` - Ganti rasio foto (3:4 potret, 9:16 wallpaper HP, 1:1, 4:3)\n"
        "• `/outfit` - Buka lemari pakaian waifu\n"
        "• `/persona` - Ganti karakter waifu (Runa, Akira, Hina, Shiro, Yume)\n"
        "• `/love` - Cek skor cinta & level kasih sayang\n"
        "• `/voice` - Atur gaya balasan suara (Selalu VN / Hanya saat kirim VN / Mute)\n"
        "• `/greetings` - Aktifkan/matikan sapaan harian otomatis\n"
        "• `/status` - Cek koneksi LLM & ComfyUI di PC\n"
        "• `/reset` - Hapus memori obrolan untuk mulai topik baru\n"
    )

    if photo_sent:
        bot.send_message(message.chat.id, guide_text, reply_markup=markup, parse_mode="Markdown")
    else:
        full_text = f"💖 **Halo Sayang! Aku {name}** 👋🥰\n\n" + guide_text
        bot.reply_to(message, full_text, reply_markup=markup, parse_mode="Markdown")


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
        f"📊 **Waifu on Telegram - System Diagnostics**\n\n"
        f"🧠 **Local LLM**: {status_icon}\n"
        f"• Backend: `{llm_stat.get('backend', 'Unknown')}`\n"
        f"• Endpoint: `{LLM_BASE_URL}`\n"
        f"• Model: `{llm_stat.get('model', 'Active')}`\n\n"
        f"🎨 **Media Generator**: {media_icon}\n"
        f"• Backend: `{media_stat.get('backend')}`\n"
        f"• Device: `{media_stat.get('device')}`\n\n"
        f"🎭 **Active Persona**: **{persona.get('name')}**\n"
        f"🎙️ **Voice Reply**: `{'Active (' + VOICE_NAME + ')' if VOICE_ENABLED else 'Disabled'}`\n"
    )
    bot.reply_to(message, report, parse_mode="Markdown")


def show_persona_menu(chat_id: int, user_id: int, reply_to_id: Optional[int] = None):
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
    lines.append("\nTap a button below or type `/persona <name>`:")
    bot.send_message(chat_id, "\n".join(lines), reply_markup=markup, parse_mode="Markdown", reply_to_message_id=reply_to_id)


def show_outfit_menu(chat_id: int, user_id: int, reply_to_id: Optional[int] = None):
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
    
    bot.send_message(
        chat_id,
        f"👗 **Waifu Wardrobe / Outfit Selection**\n\n"
        f"• Current Outfit: **{cur_name}**\n\n"
        f"Choose what outfit you'd like your waifu to wear for photos & selfies! 💕",
        reply_markup=markup,
        parse_mode="Markdown",
        reply_to_message_id=reply_to_id
    )


def show_affection_status(chat_id: int, user_id: int, reply_to_id: Optional[int] = None):
    """Displays user affection and romance status."""
    persona = persona_mgr.get_active_persona()
    score, status = persona_mgr.get_relationship_status(user_id)
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


@bot.callback_query_handler(func=lambda call: call.data in ('open_outfit_menu', 'open_persona_menu', 'check_love_status'))
def callback_quick_actions(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    if call.data == 'open_outfit_menu':
        show_outfit_menu(chat_id, user_id, reply_to_id=call.message.message_id)
    elif call.data == 'open_persona_menu':
        show_persona_menu(chat_id, user_id, reply_to_id=call.message.message_id)
    elif call.data == 'check_love_status':
        show_affection_status(chat_id, user_id, reply_to_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('regen_photo:'))
def callback_regen_photo(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return

    scenario = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id, "Generating photo... 💕")
    process_photo_request(call, scenario)


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
        try:
            bot.edit_message_text(
                f"👗 **Outfit Updated!**\n\nYour waifu is now wearing **{name}** for upcoming photos! 🥰📸",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
        except Exception:
            pass


@bot.message_handler(commands=['voice'])
def handle_voice_command(message):
    if not is_authorized(message.from_user.id):
        return

    cur_mode = USER_VOICE_MODES.get(message.from_user.id, "always" if VOICE_ENABLED else "off")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🎙️ Always Reply with Voice Note {'✓' if cur_mode == 'always' else ''}", callback_data="set_voice:always"),
        types.InlineKeyboardButton(f"🎧 Reply Voice ONLY when I send VN {'✓' if cur_mode == 'match_vn' else ''}", callback_data="set_voice:match_vn"),
        types.InlineKeyboardButton(f"🔇 Text Only (Mute Voice Notes) {'✓' if cur_mode == 'off' else ''}", callback_data="set_voice:off"),
    )
    bot.reply_to(
        message,
        "🎙️ **Voice Note Reply Settings**\n\nChoose how your waifu should reply with voice notes:",
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_voice:'))
def callback_set_voice(call):
    if not is_authorized(call.from_user.id):
        return
    mode = call.data.split(":", 1)[1]
    USER_VOICE_MODES[call.from_user.id] = mode
    labels = {
        "always": "🎙️ Always Reply with Voice Note",
        "match_vn": "🎧 Reply Voice ONLY when you send VN",
        "off": "🔇 Text Only (Mute)"
    }
    bot.answer_callback_query(call.id, f"Mode: {mode}")
    try:
        bot.edit_message_text(
            f"🎙️ Voice setting updated to:\n**{labels.get(mode, mode)}**! ✨",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
    except Exception:
        pass


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
        "• 22:00 PM - Cozy Bedtime Good Night greeting & Voice Note 🌙\n\n"
        "Toggle anytime with `/greetings on` or `/greetings off`.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['ratio', 'aspect_ratio'])
def handle_ratio_command(message):
    if not is_authorized(message.from_user.id):
        return

    cur_ar = USER_RATIOS.get(message.from_user.id, "3:4")
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [
        types.InlineKeyboardButton(f"📐 3:4 (Portrait) {'✓' if cur_ar == '3:4' else ''}", callback_data="set_ratio:3:4"),
        types.InlineKeyboardButton(f"📱 9:16 (Story/Wallpaper) {'✓' if cur_ar == '9:16' else ''}", callback_data="set_ratio:9:16"),
        types.InlineKeyboardButton(f"⏹️ 1:1 (Square Avatar) {'✓' if cur_ar == '1:1' else ''}", callback_data="set_ratio:1:1"),
        types.InlineKeyboardButton(f"🖥️ 4:3 (Landscape) {'✓' if cur_ar == '4:3' else ''}", callback_data="set_ratio:4:3"),
    ]
    markup.add(*btns)
    bot.reply_to(
        message,
        f"📐 **Photo Aspect Ratio Settings**\n\n"
        f"• Current Ratio: **{cur_ar}**\n\n"
        f"Select the aspect ratio for waifu selfies & photos:",
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_ratio:'))
def callback_set_ratio(call):
    if not is_authorized(call.from_user.id):
        return
    ar = call.data.split(":", 1)[1]
    USER_RATIOS[call.from_user.id] = ar
    bot.answer_callback_query(call.id, f"Aspect ratio set to {ar}!")
    try:
        bot.edit_message_text(
            f"📐 **Aspect Ratio Updated!**\n\nUpcoming photos will be generated in **{ar}** format! 📸",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
    except Exception:
        pass


@bot.message_handler(commands=['reset'])
def handle_reset(message):
    if not is_authorized(message.from_user.id):
        return
    persona_mgr.clear_history(message.from_user.id)
    persona = persona_mgr.get_active_persona()
    bot.reply_to(message, f"🔄 Conversation memory cleared! I'm ready for our next fresh chat, sweetheart~ 🥰")


@bot.message_handler(commands=['photo', 'pap'])
def handle_photo_command(message):
    if not is_authorized(message.from_user.id):
        return

    scenario = message.text.replace("/photo", "").replace("/pap", "").strip()
    user_prompt = scenario if scenario else "relaxing in bedroom"
    process_photo_request(message, user_prompt)


def process_photo_request(target, user_text: str):
    """Generates and delivers consistent girlfriend photo with caption matching conversation context."""
    persona = persona_mgr.get_active_persona()

    # Support both Message and CallbackQuery objects
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

    status_msg = bot.reply_to(reply_to_target, f"📸 *{persona.get('name')} is getting ready for a photo just for you, sweetheart...* 💕", parse_mode="Markdown")

    # Extract contextual scene from conversation history & user request
    detected_scene = persona_mgr.extract_contextual_scene(user_text, user_id=user_id, llm_client=llm_client)
    visual_prompt = persona_mgr.craft_visual_prompt(user_text, user_id=user_id, scene_override=detected_scene)
    logger.info(f"Visual prompt crafted: {visual_prompt}")

    def run_gen():
        try:
            with ChatActionLoop(bot, chat_id, "upload_photo"):
                neg_p = persona.get("negative_prompt")
                u_ar = USER_RATIOS.get(user_id, "3:4")
                u_qual = USER_QUALITIES.get(user_id, "high")
                img_bytes, source = media_engine.generate_photo(
                    visual_prompt,
                    negative_prompt=neg_p,
                    aspect_ratio=u_ar,
                    quality=u_qual
                )
            if not img_bytes:
                bot.edit_message_text(
                    "I'm sorry darling, my camera is acting up a little... I will try again soon! 🥺",
                    chat_id=chat_id,
                    message_id=status_msg.message_id
                )
                return

            # Build context-aware caption reflecting ongoing conversation
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

            caption, _ = llm_client.chat(caption_prompt, max_tokens=120)
            clean_caption = caption or f"Ini foto spesial buat kamu sayang~ 🥰 ({source})"

            try:
                bot.delete_message(chat_id, status_msg.message_id)
            except Exception:
                pass

            # Inline button for quick pose variant
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Pose Lain (New Pose)", callback_data=f"regen_photo:{detected_scene[:35]}"))

            bot.send_photo(chat_id, img_bytes, caption=clean_caption, reply_markup=markup)

            # Increase affection on photo request
            persona_mgr.increase_affinity(user_id, delta=2)
            persona_mgr.add_message(user_id, "user", f"[Requested photo: {user_text}]")
            persona_mgr.add_message(user_id, "assistant", f"[Sent selfie: {detected_scene}] {clean_caption}")

        except Exception as e:
            logger.error(f"Error in photo delivery: {e}")
            bot.send_message(chat_id, f"⚠️ Failed to send photo: {e}")

    threading.Thread(target=run_gen, daemon=True).start()


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


@bot.message_handler(func=lambda msg: True)
def handle_text_messages(message):
    if not is_authorized(message.from_user.id):
        return
    process_text_chat(message, message.text, is_voice=False)


def process_text_chat(message, user_text: str, is_voice: bool = False):
    """Main conversation processor running asynchronously with continuous typing status."""
    def _execute():
        is_media, media_type = persona_mgr.detect_media_request(user_text)
        if is_media and media_type == "photo":
            process_photo_request(message, user_text)
            return

        if user_text.startswith("```python") and user_text.endswith("```"):
            code = user_text.replace("```python", "").replace("```", "").strip()
            with ChatActionLoop(bot, message.chat.id, "typing"):
                ok, res = CodeRunner.execute_python(code)
                tag = "✅ Execution Output:" if ok else "❌ Execution Error:"
                bot.reply_to(message, f"💻 **{tag}**\n```\n{res}\n```", parse_mode="Markdown")
            return

        persona = persona_mgr.get_active_persona()

        # Continuous typing heartbeat so user always sees "Waifu is typing..." on Telegram
        with ChatActionLoop(bot, message.chat.id, "typing"):
            system_inst = persona.get("system_instruction", "")
            system_inst += " Keep your response warm, natural, and under 3 sentences. Answer immediately."
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

            persona_mgr.increase_affinity(message.from_user.id, delta=1)
            persona_mgr.add_message(message.from_user.id, "user", user_text)
            persona_mgr.add_message(message.from_user.id, "assistant", reply_text)

            bot.reply_to(message, reply_text)

            # Voice response logic based on user preference
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


def send_scheduled_greeting(user_id: int, time_of_day: str):
    """Sends sweet spontaneous morning/bedtime greeting."""
    try:
        persona = persona_mgr.get_active_persona()
        if time_of_day == "morning":
            prompt = "It is 7:00 AM morning. Write 1-2 sweet, cheerful, affectionate sentences wishing your partner a wonderful productive day. Use Indonesian or English naturally."
        else:
            prompt = "It is 10:00 PM bedtime. Write 1-2 sweet, gentle, caring sentences reminding your partner to rest, sleep tight, and have sweet dreams. Use Indonesian or English naturally."

        messages = [
            {"role": "system", "content": persona.get("system_instruction", "")},
            {"role": "user", "content": prompt}
        ]
        text, _ = llm_client.chat(messages, max_tokens=150)
        if not text:
            text = "Good morning sweetheart! Hope your day is filled with joy and smile~ 🥰" if time_of_day == "morning" else "Good night darling, sleep tight and sweet dreams! 💕"

        tag = "🌅 *Good Morning Sweetheart!*" if time_of_day == "morning" else "🌙 *Good Night Darling...*"
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
    """Background scheduler checking local time for morning (07:00) & bedtime (22:00) greetings."""
    while True:
        try:
            now = time.localtime()
            today_str = time.strftime("%Y-%m-%d", now)
            hour = now.tm_hour
            minute = now.tm_min

            # Morning check (07:00 - 07:05)
            m_key = f"{today_str}:morning"
            if hour == 7 and minute < 10 and m_key not in LAST_GREETING_SENT:
                LAST_GREETING_SENT[m_key] = True
                for uid in ALLOWED_USER_IDS:
                    if GREETINGS_ENABLED.get(uid, True):
                        send_scheduled_greeting(uid, "morning")

            # Bedtime check (22:00 - 22:05)
            n_key = f"{today_str}:night"
            if hour == 22 and minute < 10 and n_key not in LAST_GREETING_SENT:
                LAST_GREETING_SENT[n_key] = True
                for uid in ALLOWED_USER_IDS:
                    if GREETINGS_ENABLED.get(uid, True):
                        send_scheduled_greeting(uid, "night")

        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        time.sleep(30)


def setup_bot_commands():
    """Registers bot commands with Telegram so the Menu / Command button displays them."""
    commands = [
        types.BotCommand("start", "Mulai obrolan & panduan utama"),
        types.BotCommand("pap", "Minta foto / selfie waifu"),
        types.BotCommand("outfit", "Buka lemari pakaian & ganti baju"),
        types.BotCommand("persona", "Ganti waifu (Runa, Akira, Hina, Shiro, Yume)"),
        types.BotCommand("ratio", "Ganti rasio foto (3:4, 9:16, 1:1, 4:3)"),
        types.BotCommand("love", "Cek skor cinta & status hubungan"),
        types.BotCommand("voice", "Pengaturan balasan suara / VN"),
        types.BotCommand("greetings", "Toggle sapaan pagi & malam otomatis"),
        types.BotCommand("status", "Cek status server LLM & ComfyUI"),
        types.BotCommand("reset", "Hapus riwayat obrolan (topik baru)")
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
    logger.info(f"💖 Waifu on Telegram ({persona.get('name')}) is starting...")
    logger.info(f"🧠 Local LLM Base URL: {LLM_BASE_URL}")
    logger.info(f"🎨 ComfyUI URL: {COMFYUI_URL}")
    logger.info("=" * 60)

    # Register bot command menu on Telegram
    setup_bot_commands()

    # Launch daily greeting scheduler thread in background
    threading.Thread(target=schedule_daily_greetings, daemon=True).start()
    logger.info("✓ Daily Greetings Scheduler active (07:00 AM & 22:00 PM)")

    stat = llm_client.check_health()
    if stat.get("online"):
        logger.info(f"✓ Local LLM is ONLINE ({stat.get('backend')} - {stat.get('model')})")
    else:
        logger.warning(f"⚠️ Local LLM is OFFLINE: {stat.get('error')}")

    bot.infinity_polling(timeout=20, long_polling_timeout=20)


if __name__ == "__main__":
    main()

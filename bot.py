import os
import sys
import logging
import threading
import time
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

def is_authorized(user_id: int) -> bool:
    """Verifies if the user is authorized to interact with the bot."""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


@bot.message_handler(commands=['start', 'help'])
def handle_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "⛔ Access denied. Your Telegram User ID is not authorized.")
        return

    persona = persona_mgr.get_active_persona()
    name = persona.get("name", "Runa")

    text = (
        f"💖 **Hello Sweetheart! I'm {name}** 👋🥰\n\n"
        f"Your virtual AI companion ready to chat, listen, joke around, share selfies, and help with coding & music on your PC!\n\n"
        "✨ **Special Features:**\n"
        "• 💬 **Romance Chat**: Uncensored, warm, and affectionate conversation.\n"
        "• 📸 **Send Selfies & Photos**: Just ask *'Send me a selfie babe'* or *'Show me what you are wearing'*.\n"
        "• 👗 **Wardrobe Selection**: Choose my outfits with `/outfit`!\n"
        "• 🎙️ **Voice Notes**: Sweet natural voice replies (configure with `/voice`).\n"
        "• ⏰ **Morning & Night Greetings**: Romantic daily wake-up and bedtime sapaan (`/greetings`).\n"
        "• 👀 **AI Vision**: Send me your photos; I can see and react to them.\n"
        "• 💻 **Coding Assistant**: Ask me to write or execute Python snippets.\n\n"
        "📌 **Quick Commands:**\n"
        "• `/photo <scene>` or `/pap` - Request a selfie with interactive retry\n"
        "• `/outfit` - Open wardrobe to change what I wear in photos\n"
        "• `/persona` - Switch active waifu companion with 1-tap buttons\n"
        "• `/love` - Check our affection score & romantic bond progress\n"
        "• `/voice` - Set voice note reply style (always, match VN, or mute)\n"
        "• `/greetings` - Toggle automated morning & bedtime greetings\n"
        "• `/status` - Check Local LLM & ComfyUI diagnostics\n"
        "• `/reset` - Clear chat memory\n"
    )
    bot.reply_to(message, text, parse_mode="Markdown")


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


@bot.message_handler(commands=['persona'])
def handle_persona(message):
    if not is_authorized(message.from_user.id):
        return

    args = message.text.strip().split()
    if len(args) > 1:
        chosen = args[1].lower()
        if persona_mgr.set_active_persona(chosen):
            p = persona_mgr.get_active_persona()
            bot.reply_to(message, f"✨ Active character switched to **{p.get('name')}**! 🥰", parse_mode="Markdown")
            return
        else:
            bot.reply_to(message, f"⚠️ Persona `{chosen}` was not found.")

    # Show interactive inline keyboard
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
    bot.reply_to(message, "\n".join(lines), reply_markup=markup, parse_mode="Markdown")


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


@bot.callback_query_handler(func=lambda call: call.data.startswith('regen_photo:'))
def callback_regen_photo(call):
    if not is_authorized(call.from_user.id):
        return

    scenario = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id, "Generating another pose... 💕")
    process_photo_request(call.message, scenario)


@bot.message_handler(commands=['love', 'affection'])
def handle_affection_command(message):
    if not is_authorized(message.from_user.id):
        return

    persona = persona_mgr.get_active_persona()
    score, status = persona_mgr.get_relationship_status(message.from_user.id)
    filled = int(score / 10)
    bar = "❤️" * filled + "🤍" * (10 - filled)

    reply = (
        f"💖 **Affection & Romance Status** with **{persona.get('name')}**\n\n"
        f"• **Relationship**: {status}\n"
        f"• **Love Meter**: `[{bar}]` **{score}%**\n\n"
        f"_{persona.get('name')} cherishes every message and moment spent with you, darling! Keep chatting and asking for photos to grow your bond closer._ 🥰"
    )
    bot.reply_to(message, reply, parse_mode="Markdown")


@bot.message_handler(commands=['outfit', 'wardrobe'])
def handle_outfit_command(message):
    if not is_authorized(message.from_user.id):
        return

    cur_key, cur_name = persona_mgr.get_user_outfit(message.from_user.id)
    outfits = persona_mgr.list_outfits()
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for key, name in outfits:
        is_cur = (key == cur_key)
        label = f"{name} ✓" if is_cur else name
        btns.append(types.InlineKeyboardButton(label, callback_data=f"set_outfit:{key}"))
    markup.add(*btns)
    
    bot.reply_to(
        message,
        f"👗 **Waifu Wardrobe / Outfit Selection**\n\n"
        f"• Current Outfit: **{cur_name}**\n\n"
        f"Choose what outfit you'd like your waifu to wear for photos & selfies! 💕",
        reply_markup=markup,
        parse_mode="Markdown"
    )


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


def process_photo_request(message, user_text: str):
    """Generates and delivers consistent girlfriend photo with caption."""
    persona = persona_mgr.get_active_persona()

    # Support both Message and CallbackQuery objects
    if hasattr(message, "message") and message.message:
        chat_id = message.message.chat.id
        user_id = message.from_user.id
        reply_to_target = message.message
    else:
        chat_id = message.chat.id
        user_id = message.from_user.id
        reply_to_target = message

    bot.send_chat_action(chat_id, "upload_photo")

    status_msg = bot.reply_to(reply_to_target, f"📸 *{persona.get('name')} is getting ready for a photo just for you, sweetheart...* 💕", parse_mode="Markdown")

    visual_prompt = persona_mgr.craft_visual_prompt(user_text, user_id=user_id)
    logger.info(f"Visual prompt crafted: {visual_prompt}")

    def run_gen():
        try:
            img_bytes, source = media_engine.generate_photo(visual_prompt)
            if not img_bytes:
                bot.edit_message_text(
                    "I'm sorry darling, my camera is acting up a little... I will try again soon! 🥺",
                    chat_id=chat_id,
                    message_id=status_msg.message_id
                )
                return

            caption_prompt = [
                {"role": "system", "content": persona.get("system_instruction", "")},
                {"role": "user", "content": f"You just took a lovely selfie for the user in this scenario: '{user_text}'. Write 1-2 sweet, affectionate sentences for your photo caption."}
            ]
            caption, _ = llm_client.chat(caption_prompt, max_tokens=150)
            clean_caption = caption or f"Here's a special photo just for you darling~ 🥰 ({source})"

            try:
                bot.delete_message(chat_id, status_msg.message_id)
            except Exception:
                pass

            # Inline button for quick pose variant
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Pose Lain (New Pose)", callback_data=f"regen_photo:{user_text[:35]}"))

            bot.send_photo(chat_id, img_bytes, caption=clean_caption, reply_markup=markup)

            # Increase affection on photo request
            persona_mgr.increase_affinity(user_id, delta=2)
            persona_mgr.add_message(user_id, "user", f"[Requested photo: {user_text}]")
            persona_mgr.add_message(user_id, "assistant", f"[Sent selfie photo] {clean_caption}")

        except Exception as e:
            logger.error(f"Error in photo delivery: {e}")
            bot.send_message(chat_id, f"⚠️ Failed to send photo: {e}")

    threading.Thread(target=run_gen, daemon=True).start()


@bot.message_handler(content_types=['photo'])
def handle_incoming_photo(message):
    """Handles photos sent by user to the bot via mmproj Vision."""
    if not is_authorized(message.from_user.id):
        return

    bot.send_chat_action(message.chat.id, "typing")
    persona = persona_mgr.get_active_persona()

    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)

        caption = message.caption or "Here's a photo of mine, what do you think darling?"
        messages = [
            {"role": "system", "content": persona.get("system_instruction", "")},
            {"role": "user", "content": caption}
        ]

        reply, _ = llm_client.chat(messages, image_bytes=downloaded, max_tokens=400)
        bot.reply_to(message, reply)

        persona_mgr.add_message(message.from_user.id, "user", f"[User sent a photo: {caption}]")
        persona_mgr.add_message(message.from_user.id, "assistant", reply)

    except Exception as e:
        logger.error(f"Error handling user photo: {e}")
        bot.reply_to(message, "What a wonderful photo! You look great sweetheart~ 🥰")


@bot.message_handler(content_types=['voice'])
def handle_incoming_voice(message):
    """Handles incoming spoken voice notes."""
    if not is_authorized(message.from_user.id):
        return

    bot.send_chat_action(message.chat.id, "record_audio")
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
            bot.reply_to(message, "Your voice sounds so soothing darling, but I couldn't quite hear that. Could you say it again? 🥺")
            return

        bot.send_message(message.chat.id, f"🎙️ *You said:* _{text}_", parse_mode="Markdown")
        process_text_chat(message, text, is_voice=True)

    except Exception as e:
        logger.error(f"Error handling voice note: {e}")
        bot.reply_to(message, "Failed to process audio recording.")


@bot.message_handler(func=lambda msg: True)
def handle_text_messages(message):
    if not is_authorized(message.from_user.id):
        return
    process_text_chat(message, message.text, is_voice=False)


def process_text_chat(message, user_text: str, is_voice: bool = False):
    """Main conversation processor."""
    is_media, media_type = persona_mgr.detect_media_request(user_text)
    if is_media and media_type == "photo":
        process_photo_request(message, user_text)
        return

    if user_text.startswith("```python") and user_text.endswith("```"):
        code = user_text.replace("```python", "").replace("```", "").strip()
        bot.send_chat_action(message.chat.id, "typing")
        ok, res = CodeRunner.execute_python(code)
        tag = "✅ Execution Output:" if ok else "❌ Execution Error:"
        bot.reply_to(message, f"💻 **{tag}**\n```\n{res}\n```", parse_mode="Markdown")
        return

    bot.send_chat_action(message.chat.id, "typing")
    persona = persona_mgr.get_active_persona()

    system_inst = persona.get("system_instruction", "")
    history = persona_mgr.get_chat_history(message.from_user.id)

    messages = [{"role": "system", "content": system_inst}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    try:
        reply_text, _ = llm_client.chat(messages, max_tokens=500)
        if not reply_text:
            reply_text = "I'm right here with you sweetheart, always listening... 🥰"

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

    except Exception as e:
        logger.error(f"Chat error: {e}")
        bot.reply_to(message, f"⚠️ I'm sorry babe, my local brain connection hit a bump: {e}")


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


def main():
    persona = persona_mgr.get_active_persona()
    logger.info("=" * 60)
    logger.info(f"💖 Waifu on Telegram ({persona.get('name')}) is starting...")
    logger.info(f"🧠 Local LLM Base URL: {LLM_BASE_URL}")
    logger.info(f"🎨 ComfyUI URL: {COMFYUI_URL}")
    logger.info("=" * 60)

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

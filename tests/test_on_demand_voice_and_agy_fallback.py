import os
import unittest
from unittest.mock import MagicMock, patch
from telebot import types
from bot import (
    attach_voice_button,
    get_user_voice_mode,
    register_voice_cache,
    callback_play_voice,
    callback_set_voice,
    show_voice_settings_menu,
    send_scheduled_greeting,
    _rebuild_voice_button_markup,
    VOICE_CACHE,
    USER_VOICE_MODES
)
from media_engine import MediaEngine, format_agy_error


class TestOnDemandVoiceAndAgyFallback(unittest.TestCase):
    def setUp(self):
        USER_VOICE_MODES.clear()
        VOICE_CACHE.clear()

    def test_voice_mode_always_button_regardless_of_env_or_legacy_state(self):
        """get_user_voice_mode always returns 'button' even if legacy flags or env vars exist."""
        USER_VOICE_MODES[12345] = "off"
        with patch("bot.VOICE_ENABLED", True), patch.dict(os.environ, {"VOICE_REPLY_ENABLED": "true"}):
            self.assertEqual(get_user_voice_mode(12345), "button")
        with patch("bot.VOICE_ENABLED", False), patch.dict(os.environ, {"VOICE_REPLY_ENABLED": "false"}):
            self.assertEqual(get_user_voice_mode(12345), "button")

    def test_attach_voice_button_creates_markup_and_preserves_existing_buttons(self):
        """attach_voice_button appends '🔊 Dengarkan Suara' without dropping existing buttons or duplicating."""
        base_markup = types.InlineKeyboardMarkup()
        base_markup.add(types.InlineKeyboardButton("🎂 Buka Menu", callback_data="open_dates_menu"))

        markup = attach_voice_button(base_markup, "Halo sayang, aku kangen!", 12345)
        self.assertIsNotNone(markup)
        self.assertEqual(len(markup.keyboard), 2)
        self.assertEqual(markup.keyboard[0][0].callback_data, "open_dates_menu")
        btn = markup.keyboard[1][0]
        self.assertIn("Dengarkan Suara", btn.text)
        self.assertTrue(btn.callback_data.startswith("play_voice:"))

        # Calling again must not duplicate the voice button
        markup2 = attach_voice_button(markup, "Halo sayang, aku kangen!", 12345)
        self.assertEqual(len(markup2.keyboard), 2)

        v_id = btn.callback_data.split(":", 1)[1]
        self.assertIn(v_id, VOICE_CACHE)
        self.assertEqual(VOICE_CACHE[v_id]["text"], "Halo sayang, aku kangen!")

    def test_rebuild_voice_button_markup_preserves_other_rows(self):
        """_rebuild_voice_button_markup updates only the voice button and preserves other action buttons."""
        base_markup = types.InlineKeyboardMarkup()
        base_markup.add(types.InlineKeyboardButton("🔄 Pose Lain", callback_data="regen_photo:last"))
        base_markup = attach_voice_button(base_markup, "Ini caption foto lucu!", 12345)

        updated = _rebuild_voice_button_markup(base_markup, "⏳ Sedang memproses suara... 💕", "noop_voice_loading")
        self.assertEqual(len(updated.keyboard), 2)
        self.assertEqual(updated.keyboard[0][0].callback_data, "regen_photo:last")
        self.assertEqual(updated.keyboard[1][0].callback_data, "noop_voice_loading")
        self.assertIn("memproses suara", updated.keyboard[1][0].text)

    def test_voice_settings_menu_has_no_on_off_mode_toggles(self):
        """show_voice_settings_menu shows engine/speaker options and removes legacy set_voice toggles."""
        with patch("bot.bot.send_message") as mock_send_msg:
            show_voice_settings_menu(chat_id=12345, user_id=12345)
            mock_send_msg.assert_called_once()
            _, kwargs = mock_send_msg.call_args
            markup = kwargs["reply_markup"]
            callbacks = [btn.callback_data for row in markup.keyboard for btn in row]
            self.assertFalse(any(cb.startswith("set_voice:") for cb in callbacks))
            self.assertIn("cfg_toggle_voice_engine", callbacks)

    @patch("bot.is_authorized", return_value=True)
    @patch("bot.show_voice_settings_menu")
    @patch("bot.bot")
    def test_legacy_set_voice_callback_redirects_gracefully(self, mock_bot, mock_show_menu, mock_auth):
        """Legacy cached set_voice:* button informs user voice button is always active and refreshes menu."""
        call = MagicMock()
        call.from_user.id = 12345
        call.message.chat.id = 12345
        call.message.message_id = 55
        call.data = "set_voice:off"

        callback_set_voice(call)
        mock_bot.answer_callback_query.assert_called_once()
        mock_show_menu.assert_called_once_with(12345, 12345, message_to_edit=55)

    @patch("bot.scheduled_buffer.get_message", return_value="Selamat pagi sayang! Semangat ya hari ini~")
    @patch("bot.persona_mgr.add_message")
    @patch("bot.bot")
    def test_scheduled_greeting_always_attaches_voice_button(self, mock_bot, mock_add_msg, mock_buf):
        """Scheduled greetings attach the play_voice inline button without sending auto-VN."""
        send_scheduled_greeting(12345, "morning")
        mock_bot.send_message.assert_called_once()
        _, kwargs = mock_bot.send_message.call_args
        markup = kwargs["reply_markup"]
        self.assertIsNotNone(markup)
        self.assertTrue(any(btn.callback_data.startswith("play_voice:") for row in markup.keyboard for btn in row))
        mock_bot.send_voice.assert_not_called()

    @patch("bot.voice_engine.clean_text_for_speech", return_value="Halo sayang, aku kangen!")
    @patch("bot.voice_engine.generate_voice_note")
    @patch("bot.bot")
    def test_callback_play_voice_synthesizes_on_demand(self, mock_bot, mock_gen_vn, mock_clean):
        """Tapping the play voice button triggers audio generation and sends voice note."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            temp_path = f.name
            f.write(b"OggSFakeAudio")

        mock_gen_vn.return_value = temp_path

        call = MagicMock()
        call.from_user.id = 12345
        call.message.chat.id = 12345
        call.message.message_id = 999
        base_markup = attach_voice_button(None, "Halo sayang, aku kangen!", 12345)
        call.message.reply_markup = base_markup
        v_id = base_markup.keyboard[0][0].callback_data.split(":", 1)[1]
        call.data = f"play_voice:{v_id}"

        callback_play_voice(call)

        import time
        time.sleep(0.3)  # Allow background thread to process

        mock_bot.answer_callback_query.assert_called_with(call.id, "🎙️ Menyiapkan suara waifu... ✨")
        mock_bot.send_voice.assert_called()

    def test_format_agy_error_detects_quota_and_subagent_messages(self):
        """format_agy_error gracefully formats 429 quota exhaustion and subagent waiting notices."""
        err_429 = "429 RESOURCE_EXHAUSTED: Capacity on the underlying image generation model has been exhausted"
        self.assertIn("429 RESOURCE_EXHAUSTED", format_agy_error(err_429))

        err_dispatch = "I have dispatched the generation request to the **Anime Character Illustrator** subagent. Waiting for the image to be generated"
        self.assertIn("Mengalihkan otomatis ke generator cadangan", format_agy_error(err_dispatch))

    @patch("requests.post")
    def test_media_engine_falls_back_to_cloud_when_agy_fails(self, mock_post):
        """When AGY image generation fails and user has NO local image models, generate_photo falls back to cloud."""
        engine = MediaEngine(comfyui_url="", allow_cloud_fallback=True)

        with patch.object(engine, "generate_image_agy", return_value=None), \
             patch("agy_quota_manager.has_local_image_models", return_value=False), \
             patch("media_engine.photo_vault.find_matching_photo", return_value=None), \
             patch.object(engine, "generate_image_cloud_fallback", return_value=b"FakePNGImageBytes") as mock_cloud:
            
            with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy", "MEDIA_FALLBACK_CLOUD": "false"}):
                engine.last_error = "AGY CLI selesai namun tidak menemukan file gambar output: 429 RESOURCE_EXHAUSTED"
                img, source = engine.generate_photo("solo, 1girl, smiling waifu", persona="runa")
                
                self.assertIsNotNone(img)
                self.assertEqual(img, b"FakePNGImageBytes")
                self.assertIn("Cloud Engine", source)
                self.assertIsNotNone(engine.last_fallback_notice)

    @patch("requests.post")
    def test_media_engine_does_not_fallback_to_cloud_when_user_has_local_models(self, mock_post):
        """When AGY image generation fails and user HAS local models, fallback MUST NOT go to Pollinations cloud."""
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188", allow_cloud_fallback=True)

        with patch.object(engine, "generate_image_agy", return_value=None), \
             patch("agy_quota_manager.has_local_image_models", return_value=True), \
             patch("idle_engine.is_port_listening", return_value=True), \
             patch.object(engine, "generate_image_comfyui", return_value=b"LocalComfyUIBytes"), \
             patch.object(engine, "generate_image_cloud_fallback") as mock_cloud:

            with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy", "MEDIA_FALLBACK_CLOUD": "true"}):
                engine.last_error = "AGY quota exhausted"
                img, source = engine.generate_photo("solo, 1girl, smiling waifu", persona="runa")

                self.assertEqual(img, b"LocalComfyUIBytes")
                self.assertIn("Local ComfyUI", source)
                mock_cloud.assert_not_called()


if __name__ == "__main__":
    unittest.main()

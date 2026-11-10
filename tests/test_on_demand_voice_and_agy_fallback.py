import os
import unittest
from unittest.mock import MagicMock, patch
from bot import (
    attach_voice_button,
    get_user_voice_mode,
    register_voice_cache,
    callback_play_voice,
    VOICE_CACHE,
    USER_VOICE_MODES
)
from media_engine import MediaEngine, format_agy_error


class TestOnDemandVoiceAndAgyFallback(unittest.TestCase):
    def setUp(self):
        USER_VOICE_MODES.clear()
        VOICE_CACHE.clear()

    def test_default_voice_mode_is_button(self):
        """When VOICE_REPLY_ENABLED is false, user voice mode defaults to 'button' (on-demand)."""
        with patch("bot.VOICE_ENABLED", False):
            mode = get_user_voice_mode(12345)
            self.assertEqual(mode, "button")

    def test_attach_voice_button_creates_markup(self):
        """attach_voice_button appends '🔊 Dengarkan Suara' button and registers text in cache."""
        markup = attach_voice_button(None, "Halo sayang, aku kangen!", 12345)
        self.assertIsNotNone(markup)
        self.assertEqual(len(markup.keyboard), 1)
        btn = markup.keyboard[0][0]
        self.assertIn("Dengarkan Suara", btn.text)
        self.assertTrue(btn.callback_data.startswith("play_voice:"))

        v_id = btn.callback_data.split(":", 1)[1]
        self.assertIn(v_id, VOICE_CACHE)
        self.assertEqual(VOICE_CACHE[v_id]["text"], "Halo sayang, aku kangen!")

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
        v_id = register_voice_cache("Halo sayang, aku kangen!", 12345)
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
        """When AGY image generation fails, generate_photo seamlessly falls back to cloud so user never gets a broken photo."""
        engine = MediaEngine(comfyui_url="", allow_cloud_fallback=True)

        with patch.object(engine, "generate_image_agy", return_value=None), \
             patch("media_engine.photo_vault.find_matching_photo", return_value=None), \
             patch.object(engine, "generate_image_cloud_fallback", return_value=b"FakePNGImageBytes") as mock_cloud:
            
            with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy", "MEDIA_FALLBACK_CLOUD": "false"}):
                engine.last_error = "AGY CLI selesai namun tidak menemukan file gambar output: 429 RESOURCE_EXHAUSTED"
                img, source = engine.generate_photo("solo, 1girl, smiling waifu", persona="runa")
                
                self.assertIsNotNone(img)
                self.assertEqual(img, b"FakePNGImageBytes")
                self.assertIn("Cloud Engine", source)
                self.assertIsNotNone(engine.last_fallback_notice)


if __name__ == "__main__":
    unittest.main()

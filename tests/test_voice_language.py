import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import bot

class TestVoiceLanguageSettings(unittest.TestCase):
    def setUp(self):
        self.original_voice = bot.voice_engine.default_voice
        self.original_bot_lang = os.environ.get("BOT_LANGUAGE", "id")

    def tearDown(self):
        bot.voice_engine.default_voice = self.original_voice
        os.environ["BOT_LANGUAGE"] = self.original_bot_lang

    def test_apply_voice_speaker_options(self):
        # Indonesian
        v = bot.apply_voice_speaker("gadis")
        self.assertEqual(v, "id-ID-GadisNeural")
        self.assertEqual(bot.voice_engine.default_voice, "id-ID-GadisNeural")

        # Japanese
        v = bot.apply_voice_speaker("nanami")
        self.assertEqual(v, "ja-JP-NanamiNeural")
        self.assertEqual(bot.voice_engine.default_voice, "ja-JP-NanamiNeural")

        # English
        v = bot.apply_voice_speaker("ana")
        self.assertEqual(v, "en-US-AnaNeural")
        self.assertEqual(bot.voice_engine.default_voice, "en-US-AnaNeural")

        # Auto
        v = bot.apply_voice_speaker("auto")
        self.assertEqual(v, "auto")
        self.assertEqual(bot.voice_engine.default_voice, "auto")

    def test_detect_language_voice_with_auto(self):
        bot.voice_engine.default_voice = "auto"

        # Japanese text
        self.assertEqual(bot.voice_engine.detect_language_voice("こんにちは、先輩！"), "ja-JP-NanamiNeural")

        # Indonesian text
        self.assertEqual(bot.voice_engine.detect_language_voice("Halo sayang, apa kabar hari ini?"), "id-ID-GadisNeural")

        # Short/neutral text with BOT_LANGUAGE='ja'
        os.environ["BOT_LANGUAGE"] = "ja"
        self.assertEqual(bot.voice_engine.detect_language_voice("ok"), "ja-JP-NanamiNeural")

        # Short/neutral text with BOT_LANGUAGE='id'
        os.environ["BOT_LANGUAGE"] = "id"
        self.assertEqual(bot.voice_engine.detect_language_voice("ok"), "id-ID-GadisNeural")

        # Short/neutral text with BOT_LANGUAGE='en'
        os.environ["BOT_LANGUAGE"] = "en"
        self.assertEqual(bot.voice_engine.detect_language_voice("ok"), "en-US-AnaNeural")

if __name__ == "__main__":
    unittest.main()

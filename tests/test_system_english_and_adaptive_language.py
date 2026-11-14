import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from persona_manager import PersonaManager


class TestSystemEnglishAndAdaptiveLanguage(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager()

    def test_detect_text_language(self):
        # Indonesian sentences
        id_samples = [
            "halo sayang, kamu lagi ngapain sekarang?",
            "aku lagi santai di kos nih, udah makan belum?",
            "lagi apa mimi? boleh minta foto selfie kamu?",
            "kamu pulang jam berapa nanti sore?",
            "tolong ingetin aku ya jam 3 sore"
        ]
        for s in id_samples:
            lang = self.pm.detect_text_language(s)
            self.assertEqual(lang, "id", f"Expected 'id' for '{s}', got '{lang}'")

        # English sentences
        en_samples = [
            "hello darling, how are you doing today?",
            "can you send me a cute selfie in bed?",
            "what time will you come home tonight?",
            "remind me in 30 minutes to drink water",
            "just relaxing in my room after office work"
        ]
        for s in en_samples:
            lang = self.pm.detect_text_language(s)
            self.assertEqual(lang, "en", f"Expected 'en' for '{s}', got '{lang}'")

        # Japanese sentences
        ja_samples = [
            "こんにちは、愛してるよ",
            "今日も一日お疲れ様でした",
            "一緒にカフェに行こう"
        ]
        for s in ja_samples:
            lang = self.pm.detect_text_language(s)
            self.assertEqual(lang, "ja", f"Expected 'ja' for '{s}', got '{lang}'")

    def test_adaptive_directive(self):
        # Test auto mode with Indonesian input
        id_dir = self.pm.get_language_directive("auto", user_text="sayang lagi apa di kos?")
        self.assertIn("ATURAN BAHASA WAJIB (BAHASA INDONESIA)", id_dir)
        self.assertIn("aku", id_dir)
        self.assertIn("kamu", id_dir)

        # Test auto mode with English input
        en_dir = self.pm.get_language_directive("auto", user_text="hey sweetie, how was your day?")
        self.assertIn("STRICT LANGUAGE & TONE DIRECTIVE", en_dir)
        self.assertIn("English", en_dir)

        # Test explicit language setting
        explicit_id = self.pm.get_language_directive("id")
        self.assertIn("ATURAN BAHASA WAJIB (BAHASA INDONESIA)", explicit_id)

        explicit_en = self.pm.get_language_directive("en")
        self.assertIn("STRICT LANGUAGE & TONE DIRECTIVE", explicit_en)
        self.assertIn("English", explicit_en)

    def test_user_language_persistence(self):
        test_uid = 999998888
        # Default should be auto
        self.assertEqual(self.pm.get_user_language(test_uid), "auto")

        # Set to English
        self.pm.set_user_language(test_uid, "en")
        self.assertEqual(self.pm.get_user_language(test_uid), "en")

        # Set to Indonesian
        self.pm.set_user_language(test_uid, "id")
        self.assertEqual(self.pm.get_user_language(test_uid), "id")

        # Reset back to auto
        self.pm.set_user_language(test_uid, "auto")
        self.assertEqual(self.pm.get_user_language(test_uid), "auto")

    def test_english_display_names(self):
        self.assertIn("Auto-detect", self.pm.get_language_display_name("auto"))
        self.assertIn("English", self.pm.get_language_display_name("en"))
        self.assertIn("Indonesian", self.pm.get_language_display_name("id"))
        self.assertIn("Japanese", self.pm.get_language_display_name("ja"))

    def test_setup_dashboard_english(self):
        import bot
        text, markup = bot.render_setup_dashboard(12345)
        # Check that main headers, labels, and badges are in English
        self.assertIn("SETUP & SYSTEM CONTROL", text)
        self.assertIn("Active Waifu", text)
        self.assertIn("Language", text)
        self.assertIn("Outfit", text)
        self.assertIn("LLM Model", text)
        self.assertIn("Visual Engine", text)

        # Check inline keyboard button labels
        btn_texts = [b.text for row in markup.keyboard for b in row]
        self.assertTrue(any("Switch Waifu" in t for t in btn_texts))
        self.assertTrue(any("Date & Hangout (/hangout)" in t for t in btn_texts))
        self.assertTrue(any("Wardrobe" in t for t in btn_texts))
        self.assertTrue(any("Language" in t for t in btn_texts))
        self.assertTrue(any("Voice & Audio" in t for t in btn_texts))

    def test_help_sections_english(self):
        import bot
        sections = ["main", "memory", "chat", "photo", "outfit", "voice", "setup", "reminders", "dates", "music"]
        for sec in sections:
            text, markup = bot.render_help_section(sec)
            self.assertTrue(len(text) > 50)
            # Ensure English headers
            self.assertTrue(any(k in text for k in ["GUIDE", "REFERENCE", "SYSTEM", "REMINDERS", "SETUP"]))


if __name__ == "__main__":
    unittest.main()

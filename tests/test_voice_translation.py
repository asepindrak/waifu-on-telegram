import unittest
from unittest.mock import patch, MagicMock
import voice_engine

class TestVoiceTranslationAndCleaning(unittest.TestCase):
    """Verifies that speech text cleaning and multi-tier translation to Japanese work accurately."""

    def setUp(self):
        self.engine = voice_engine.VoiceEngine(voice_name="ja-JP-NanamiNeural")

    def test_clean_text_for_speech(self):
        """Action tags, narration asterisks, emojis, and directions should be stripped from speech."""
        raw_text = "*tersenyum manis* Halo sayang! 💕 Aku kangen banget sama kamu~ [ACTION: SEND_PAP] (tertawa kecil)"
        cleaned = voice_engine.VoiceEngine.clean_text_for_speech(raw_text)

        self.assertNotIn("ACTION", cleaned)
        self.assertNotIn("SEND_PAP", cleaned)
        self.assertNotIn("tersenyum", cleaned)
        self.assertNotIn("tertawa", cleaned)
        self.assertNotIn("💕", cleaned)
        self.assertIn("Halo sayang! Aku kangen banget sama kamu", cleaned)

    def test_detect_text_language_kaomoji_dominance(self):
        """Stray kaomoji or symbols must not trick Indonesian text into being detected as Japanese."""
        text_with_kaomoji = "Halo sayang! (*^▽^*) Lagi ngapain sekarang? Kangen deh."
        lang = voice_engine.VoiceEngine.detect_text_language(text_with_kaomoji)
        self.assertEqual(lang, "id")

        japanese_text = "こんにちは、ダーリン！会いたかったよ！"
        lang_ja = voice_engine.VoiceEngine.detect_text_language(japanese_text)
        self.assertEqual(lang_ja, "ja")

    def test_translate_for_voice_tier_fallback(self):
        """When Google GTX fails, fallback tiers (e.g. MyMemory or Local LLM) must succeed."""
        raw_id = "Halo sayang, apa kabar?"

        # Mock Google GTX throwing connection error, and Local LLM returning Japanese
        mock_llm = MagicMock()
        mock_llm.chat.return_value = ("こんにちは、ダーリン。元気？", "")
        self.engine.llm_client = mock_llm

        with patch("urllib.request.urlopen", side_effect=Exception("Network Timeout")):
            translated = self.engine.translate_for_voice(raw_id, "ja")
            self.assertEqual(translated, "こんにちは、ダーリン。元気？")
            mock_llm.chat.assert_called_once()

    def test_safety_guardrail_voice_fallback(self):
        """If all translation fails and text remains Indonesian, it should not speak with Japanese voice."""
        engine = voice_engine.VoiceEngine(voice_name="ja-JP-NanamiNeural")
        
        # When translate_for_voice returns original Indonesian (all tiers failed)
        with patch.object(engine, "translate_for_voice", return_value="Halo sayang apa kabar"):
            with patch("edge_tts.Communicate") as mock_comm:
                mock_instance = MagicMock()
                mock_comm.return_value = mock_instance
                mock_instance.save = MagicMock()

                import asyncio
                asyncio.run(engine.generate_voice_note_async("Halo sayang apa kabar", "dummy_path.ogg"))

                # Communicate should be called with id-ID-GadisNeural instead of Japanese voice!
                call_args = mock_comm.call_args[0]
                voice_used = call_args[1]
                self.assertEqual(voice_used, "id-ID-GadisNeural")

    def test_generate_voice_alias_exists(self):
        """Verify generate_voice alias is present and functional on VoiceEngine."""
        self.assertTrue(hasattr(self.engine, "generate_voice"))
        with patch.object(self.engine, "generate_voice_note", return_value="fake.ogg") as mock_gen:
            res = self.engine.generate_voice("Test message", voice_name="en-US-AnaNeural")
            self.assertEqual(res, "fake.ogg")
            mock_gen.assert_called_once_with("Test message", voice_override="en-US-AnaNeural", auto_translate=True)


if __name__ == "__main__":
    unittest.main()

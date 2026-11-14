"""
tests/test_spontaneous_photo_and_caption_alignment.py
Unit tests verifying:
1. Spontaneous photo scene moments detection across various everyday girlfriend lifestyle activities.
2. Contextual caption prompt generation and contextual fallback alignment.
3. Spontaneous photo cooldown and cadence triggers.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import time

from persona_manager import PersonaManager
from hangout_engine import HangoutEngine
import bot


class TestSpontaneousPhotoAndCaptionAlignment(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager()
        self.he = HangoutEngine(data_file="tests/test_hangouts_spont_tmp.json")

    def tearDown(self):
        if os.path.exists("tests/test_hangouts_spont_tmp.json"):
            try:
                os.remove("tests/test_hangouts_spont_tmp.json")
            except Exception:
                pass

    def test_lifestyle_scene_moments_detection(self):
        """Verify waifu recognizes everyday lifestyle scenarios to trigger spontaneous photos."""
        # Cafe / Coffee
        is_scene, desc = self.pm.detect_visual_scene_moment(
            "lagi di mana sayang?", "Aku lagi ngopi santai di kafe nih, kopinya enak banget"
        )
        self.assertTrue(is_scene)
        self.assertIn("cafe", desc.lower())

        # Kosan / Kamar relaxing
        is_scene, desc = self.pm.detect_visual_scene_moment(
            "lagi ngapain?", "Lagi rebahan santai di kosan nih sambil nonton YouTube"
        )
        self.assertTrue(is_scene)
        self.assertIn("apartment", desc.lower())

        # Bedtime / Sleepy
        is_scene, desc = self.pm.detect_visual_scene_moment(
            "udah malam nih", "Iya udah ngantuk banget, aku udah di kasur pakai piyama"
        )
        self.assertTrue(is_scene)
        self.assertIn("bed", desc.lower())

        # Morning / Waking up
        is_scene, desc = self.pm.detect_visual_scene_moment(
            "pagi manis!", "Pagi! Aku baru bangun nih, masih ngantuk hehe"
        )
        self.assertTrue(is_scene)
        self.assertIn("morning", desc.lower())

        # Food / Culinary
        is_scene, desc = self.pm.detect_visual_scene_moment(
            "udah makan belum?", "Ini aku lagi makan ramen pedas kesukaan kita"
        )
        self.assertTrue(is_scene)
        self.assertIn("food", desc.lower())

        # Study / Campus
        is_scene, desc = self.pm.detect_visual_scene_moment(
            "lagi sibuk ya?", "Lagi fokus nugas skripsi di kampus nih"
        )
        self.assertTrue(is_scene)
        self.assertIn("study", desc.lower())

    def test_cooldown_constants(self):
        """Verify cooldown constants are configured for active and lively photo sharing."""
        self.assertLessEqual(bot.MIN_AUTO_PHOTO_TURN_COOLDOWN, 2)
        self.assertLessEqual(bot.MIN_AUTO_PHOTO_TIME_COOLDOWN, 40.0)

    def test_caption_sanitization_and_contextual_fallbacks(self):
        """Verify contextual fallbacks align with conversational activity."""
        # Sanitize chat caption helper
        fallback_cafe = "Lagi asyik santai ngopi nih, suka ga fotonya? ☕🥰"
        res = bot.sanitize_chat_caption(None, fallback_cafe)
        self.assertEqual(res, fallback_cafe)

        # Ensure generic YouTuber phrases are purged
        vlogger_text = "Hai gaes, intip yuk fotoku hari ini! Suka ga?"
        cleaned = bot.sanitize_chat_caption(vlogger_text, fallback_cafe)
        self.assertNotIn("gaes", cleaned.lower())
        self.assertNotIn("intip yuk", cleaned.lower())

    def test_outfit_mention_stripping_when_not_asked(self):
        """Verify awkward self-narrating clothes phrases are stripped when partner didn't ask about clothes."""
        sample_caption = "Udah nyaman banget rebahan di kasur pakai piyama begini, jangan berhenti mijit kakiku ya, enak banget."
        cleaned = bot.sanitize_chat_caption(sample_caption, "fallback", user_prompt="kamu lagi ngapain?")
        self.assertNotIn("pakai piyama", cleaned.lower())
        self.assertIn("rebahan di kasur", cleaned.lower())
        self.assertIn("jangan berhenti mijit kakiku ya", cleaned.lower())

        # But when user explicitly asks about clothes, keep outfit mention!
        outfit_caption = "Aku lagi pakai piyama santai setelan camisole warna pink nih, lucu kan?"
        kept = bot.sanitize_chat_caption(outfit_caption, "fallback", user_prompt="kamu lagi pake baju apa?")
        self.assertIn("pakai piyama", kept.lower())

    def test_furniture_and_location_alignment_bed_vs_sofa(self):
        """Verify that hallucinated sofa and 'sebelum berangkat' are corrected to bed when scene is on a bed."""
        cap = "Masih nyaman banget santai di sofa sebelum berangkat, kamu belum kasih tahu nama kamu nih."
        scene = "relaxing on bed with fluffy pillows and soft blanket, bright sunny morning bedroom window"
        cleaned = bot.sanitize_chat_caption(cap, "fallback", user_prompt="pagi sayang", detected_scene=scene)
        self.assertNotIn("sofa", cleaned.lower())
        self.assertNotIn("sebelum berangkat", cleaned.lower())
        self.assertIn("kasur", cleaned.lower())
        self.assertIn("kamu belum kasih tahu nama kamu nih", cleaned.lower())

    def test_furniture_and_location_alignment_sofa_vs_bed(self):
        """Verify that hallucinated bed is corrected to sofa when scene is in living room sofa."""
        cap = "Udah PW banget rebahan di kasur sambil nonton TV bareng kamu."
        scene = "sitting on comfortable living room sofa watching tv, cozy apartment"
        cleaned = bot.sanitize_chat_caption(cap, "fallback", user_prompt="lagi apa?", detected_scene=scene)
        self.assertNotIn("kasur", cleaned.lower())
        self.assertIn("sofa", cleaned.lower())

    def test_indonesian_scene_descriptions(self):
        """Verify PersonaManager translates Danbooru scene prompts to Indonesian."""
        from persona_manager import PersonaManager
        self.assertIn("kasur", PersonaManager.get_indonesian_scene_desc("relaxing on bed with fluffy pillows").lower())
        self.assertIn("sofa", PersonaManager.get_indonesian_scene_desc("sitting on living room couch sofa").lower())
        self.assertIn("dapur", PersonaManager.get_indonesian_scene_desc("kitchen counter cooking breakfast").lower())
        self.assertIn("kafe", PersonaManager.get_indonesian_scene_desc("sitting at cozy cafe coffee shop").lower())


if __name__ == "__main__":
    unittest.main()


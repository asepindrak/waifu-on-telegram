import unittest
import time
from unittest.mock import MagicMock
from hangout_engine import get_hangout_engine
from waifu_status_tracker import get_waifu_status_tracker
from story_engine import get_story_engine


class TestStoryAwarenessAndHangoutPriority(unittest.TestCase):
    def setUp(self):
        self.hangout_engine = get_hangout_engine()
        self.status_tracker = get_waifu_status_tracker()
        self.story_engine = get_story_engine()
        self.user_id = 123456789

    def test_detect_hangout_and_invitation_intent(self):
        """Detects hangout intent and invitations across diverse Indonesian phrasing."""
        # 1. Direct hangout proposals
        self.assertIsNotNone(self.hangout_engine.detect_hangout_intent("ayo main bareng"))
        self.assertIsNotNone(self.hangout_engine.detect_hangout_intent("main yuk"))
        self.assertIsNotNone(self.hangout_engine.detect_hangout_intent("keluar yuk"))
        self.assertIsNotNone(self.hangout_engine.detect_hangout_intent("temenin jalan"))
        self.assertIsNotNone(self.hangout_engine.detect_hangout_intent("mabar yuk"))
        self.assertEqual(self.hangout_engine.detect_hangout_intent("mabar yuk"), "home")
        self.assertEqual(self.hangout_engine.detect_hangout_intent("nongkrong di kafe"), "cafe")

        # 2. General activity invitations
        self.assertTrue(self.hangout_engine.detect_activity_invitation("ayo main bareng"))
        self.assertTrue(self.hangout_engine.detect_activity_invitation("kita jalan yuk hari ini"))
        self.assertTrue(self.hangout_engine.detect_activity_invitation("temenin aku nonton"))
        self.assertTrue(self.hangout_engine.detect_activity_invitation("mabar game yuk"))
        self.assertFalse(self.hangout_engine.detect_activity_invitation("aku tadi makan nasi goreng enak"))

    def test_detect_activity_queries(self):
        """Accurately detects whether the user is asking what the waifu is doing."""
        self.assertTrue(self.hangout_engine.detect_activity_query("kamu lagi apa?"))
        self.assertTrue(self.hangout_engine.detect_activity_query("lagi ngapain nih?"))
        self.assertTrue(self.hangout_engine.detect_activity_query("sedang sibuk apa?"))
        self.assertTrue(self.hangout_engine.detect_activity_query("hari ini ngapain aja?"))
        self.assertTrue(self.hangout_engine.detect_activity_query("gimana harimu?"))
        self.assertTrue(self.hangout_engine.detect_activity_query("gimana kabarmu sekarang?"))
        self.assertFalse(self.hangout_engine.detect_activity_query("ayo main game bareng"))
        self.assertFalse(self.hangout_engine.detect_activity_query("lucu banget fotomu"))

    def test_story_prompt_ongoing_chat_vs_active(self):
        """In ongoing chats, story is passive; after silence or when asked, story is active."""
        # Case A: Ongoing chat without query -> passive background, no rigid game loops
        passive_ctx = self.story_engine.get_story_prompt_context(
            "runa",
            is_ongoing_chat=True,
            user_asked_activity=False
        )
        self.assertIn("LATAR BELAKANG PASIF", passive_ctx)
        self.assertIn("FOKUS 100% PADA CHAT & AJAKAN PASANGAN", passive_ctx)
        self.assertIn("DILARANG KERAS mengulang-ulang kegiatan lama", passive_ctx)

        # Case B: Ongoing chat BUT user explicitly asks "lagi apa" -> active story details
        active_asked_ctx = self.story_engine.get_story_prompt_context(
            "runa",
            is_ongoing_chat=True,
            user_asked_activity=True
        )
        self.assertIn("[LATAR KEHIDUPAN & EPISODE CERITA HARI INI]", active_asked_ctx)
        self.assertIn("Aktivitas Utama:", active_asked_ctx)
        self.assertIn("User baru saja menanyakan kabarmu", active_asked_ctx)

        # Case C: First chat of the day or after long silence -> active story context
        active_new_ctx = self.story_engine.get_story_prompt_context(
            "runa",
            is_ongoing_chat=False,
            user_asked_activity=False
        )
        self.assertIn("[LATAR KEHIDUPAN & EPISODE CERITA HARI INI]", active_new_ctx)
        self.assertIn("Aktivitas Utama:", active_new_ctx)
        self.assertIn("obrolan awal setelah jeda waktu atau hari baru", active_new_ctx)

    def test_status_tracker_dynamic_update_and_prompt(self):
        """Waifu status tracker updates dynamically and avoids rigid repetition."""
        self.status_tracker.update_status(
            self.user_id,
            location="Kafe Estetik",
            activity="Lagi main dan menghabiskan waktu bersama di Kafe Estetik",
            persona_name="Runa"
        )
        st = self.status_tracker.get_current_status(self.user_id)
        self.assertIsNotNone(st)
        self.assertEqual(st["location"], "Kafe Estetik")
        self.assertIn("Kafe Estetik", st["activity"])

        instr = self.status_tracker.format_status_instruction(
            user_id=self.user_id,
            cur_hour=15,
            routine_desc="kuliah di kampus",
            major="Ilmu Komunikasi",
            is_inviting_out=True
        )
        self.assertIn("Kafe Estetik", instr)
        self.assertIn("FLEKSIBEL & RESPONSIF TERHADAP AJAKAN", instr)
        self.assertNotIn("ATURAN MUTLAK KONSISTENSI DIRI", instr)
        self.assertIn("DILARANG KERAS mengulang-ulang kegiatan lama", instr)


if __name__ == "__main__":
    unittest.main()

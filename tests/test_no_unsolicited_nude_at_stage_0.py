import unittest
from persona_manager import PersonaManager
from routing_engine import detect_nsfw_intent

class TestNoUnsolicitedNudeAtStage0(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager()
        self.user_id = 77112233
        self.pm.reset_undress_stage(self.user_id)
        if hasattr(self.pm, "clear_session_outfit"):
            self.pm.clear_session_outfit(self.user_id)

    def tearDown(self):
        self.pm.reset_undress_stage(self.user_id)

    def test_stage_0_intimate_chat_remains_clothed(self):
        """Intimate dialogue early in the conversation without undress commands must remain clothed (is_nude=False)."""
        queries = [
            "aku kangen kamu sayang",
            "sini peluk aku erat-erat",
            "kamu cantik banget malam ini",
            "nanti aku pijit di kosan ya",
            "kamu pulang jam berapa?",
        ]
        for q in queries:
            prompt, neg, is_nude, name = self.pm.detect_clothing_intent(q, user_id=self.user_id, is_nsfw=True)
            self.assertFalse(is_nude, f"Expected is_nude=False for query '{q}' at stage 0, but got True! Outfit: {name}")
            self.assertNotIn("completely nude", prompt.lower())

    def test_lab_setting_remains_clothed_even_with_nsfw_flag(self):
        """When in a laboratory, waifu must wear lab attire and never be nude."""
        prompt, neg, is_nude, name = self.pm.detect_clothing_intent(
            "kamu pulang jam berapa?",
            user_id=self.user_id,
            scene_hint="science laboratory, modern extraction lab",
            is_nsfw=True
        )
        self.assertFalse(is_nude)
        self.assertIn("lab", name.lower())
        self.assertIn("lab coat", prompt.lower())

    def test_explicit_nude_works_when_explicitly_requested(self):
        """When user explicitly asks for nude or full nudity, is_nude becomes True."""
        prompt, neg, is_nude, name = self.pm.detect_clothing_intent(
            "coba buka semua baju sampai telanjang bulat",
            user_id=self.user_id,
            is_nsfw=True
        )
        self.assertTrue(is_nude)
        self.assertIn("nude", prompt.lower())

    def test_sequential_undress_preserves_clothed_states(self):
        """Stage 1 (shirt off) and Stage 2 (lingerie) must NOT be nude."""
        # Advance to Stage 1
        target, _, _ = self.pm.detect_undress_intent("buka bajumu sayang", current_stage=0)
        self.pm.set_undress_stage(self.user_id, target)
        p1, _, is_nude1, _ = self.pm.detect_clothing_intent("seksi banget", user_id=self.user_id, is_nsfw=True)
        self.assertFalse(is_nude1)

        # Advance to Stage 2
        target2, _, _ = self.pm.detect_undress_intent("buka celanamu", current_stage=1)
        self.pm.set_undress_stage(self.user_id, target2)
        p2, _, is_nude2, _ = self.pm.detect_clothing_intent("indah banget", user_id=self.user_id, is_nsfw=True)
        self.assertFalse(is_nude2)

    def test_casual_chat_does_not_trigger_nsfw_continuation(self):
        """Normal questions like 'kamu pulang jam berapa sayang' must not trigger erotic roleplay continuation."""
        history = [
            {"role": "user", "content": "Wah pasti cape ya, nanti aku pijit di kosan deh, aku sih masih di kantor ini"},
            {"role": "assistant", "content": "Ih iya, badan jadi kaku banget! Tapi tenang dong, nanti aku pulang kekos-kos aja biar bisa leluasa dapetin pijatan-pijatan enak itu."}
        ]
        is_nsfw = detect_nsfw_intent("Kamu pulang jam berapa?", messages=history)
        self.assertFalse(is_nsfw)

if __name__ == '__main__':
    unittest.main()

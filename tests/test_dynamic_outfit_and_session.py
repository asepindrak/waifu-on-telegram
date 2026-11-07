import unittest
import time
from persona_manager import PersonaManager, OUTFIT_PRESETS


class TestDynamicOutfitAndSession(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager(active_key="akira")
        self.user_id = 778899
        # Reset user outfit to default auto
        self.pm.set_user_outfit(self.user_id, "default")

    def test_default_is_auto_mode(self):
        """Default outfit mode must be auto dynamic."""
        details = self.pm.get_user_outfit_details(self.user_id)
        self.assertEqual(details["mode"], "auto")
        self.assertEqual(details["key"], "default")
        self.assertFalse(details["is_locked"])
        self.assertFalse(details["is_session"])
        self.assertIn("Otomatis", details["name"])

    def test_auto_mode_matches_activity_context(self):
        """In auto mode, visual prompt matches scenario (e.g. mandi -> towel, tidur -> pajamas)."""
        # Scenario 1: Mandi / Shower
        v_prompt, _, is_nude, label = self.pm.craft_visual_prompt_full(
            "mandi dulu gih baru pap", user_id=self.user_id
        )
        self.assertIn("bath towel", v_prompt)
        self.assertIn("Handuk", label)
        self.assertFalse(is_nude)

        # Scenario 2: Tidur / Bedtime
        v_prompt2, _, is_nude2, label2 = self.pm.craft_visual_prompt_full(
            "udah malam, yuk tidur rebahan di kasur", user_id=self.user_id
        )
        self.assertIn("silk", v_prompt2.lower())
        self.assertIn("Pajamas", label2)
        self.assertFalse(is_nude2)

        # Scenario 3: Santai di rumah / kos
        v_prompt3, _, _, label3 = self.pm.craft_visual_prompt_full(
            "lagi santai di rumah baru pulang", user_id=self.user_id
        )
        self.assertIn("Santai", label3)

    def test_session_outfit_active_and_then_resets_on_context_shift(self):
        """Selecting an outfit sets a session outfit, which resets to auto when context changes."""
        # 1. User picks 'kimono'
        self.pm.set_user_outfit(self.user_id, "kimono")
        details = self.pm.get_user_outfit_details(self.user_id)
        self.assertEqual(details["mode"], "session")
        self.assertEqual(details["key"], "kimono")
        self.assertTrue(details["is_session"])

        # 2. Taking photo in current session keeps kimono
        v_prompt, _, _, label = self.pm.craft_visual_prompt_full(
            "coba pap dong", user_id=self.user_id
        )
        self.assertIn("kimono", v_prompt.lower())
        self.assertIn("Kimono", label)

        # 3. Context shifts to bedtime
        shifted = self.pm.check_context_shift(self.user_id, "aku ngantuk nih, bobo yuk sayang")
        self.assertTrue(shifted)

        # 4. Outfit must have reverted to auto!
        details_after = self.pm.get_user_outfit_details(self.user_id)
        self.assertEqual(details_after["mode"], "auto")

        # 5. Next photo uses bedtime sleepwear, NOT kimono
        v_prompt2, _, _, label2 = self.pm.craft_visual_prompt_full(
            "pap nemenin tidur", user_id=self.user_id
        )
        self.assertNotIn("kimono", v_prompt2.lower())
        self.assertIn("Pajamas", label2)

    def test_session_outfit_yields_to_shower_scenario(self):
        """If user has maid costume active but user asks to shower/mandi, it yields to towel."""
        self.pm.set_user_outfit(self.user_id, "maid")
        self.assertTrue(self.pm.get_user_outfit_details(self.user_id)["is_session"])

        # Mandi scenario triggered
        v_prompt, _, _, label = self.pm.craft_visual_prompt_full(
            "kamu mandi dulu gih", user_id=self.user_id
        )
        self.assertIn("bath towel", v_prompt.lower())
        self.assertIn("Handuk", label)

        # Session outfit should be cleared
        self.assertEqual(self.pm.get_user_outfit_details(self.user_id)["mode"], "auto")

    def test_locked_outfit_persists_until_unlocked(self):
        """Locked outfit stays even during context shift until reset to default."""
        self.pm.set_user_outfit(self.user_id, "school_jk", is_locked=True)
        details = self.pm.get_user_outfit_details(self.user_id)
        self.assertEqual(details["mode"], "locked")
        self.assertTrue(details["is_locked"])

        # Context shift attempt does NOT clear locked outfit
        shifted = self.pm.check_context_shift(self.user_id, "tidur yuk")
        self.assertFalse(shifted)
        self.assertEqual(self.pm.get_user_outfit_details(self.user_id)["mode"], "locked")

        # Unlocking returns to auto
        self.pm.set_user_outfit(self.user_id, "default")
        self.assertEqual(self.pm.get_user_outfit_details(self.user_id)["mode"], "auto")


if __name__ == '__main__':
    unittest.main()


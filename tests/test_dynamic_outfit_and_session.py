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

    def test_outfit_color_and_prompt_consistency_same_scene(self):
        """In the same scene/outfit, multiple photo requests must have 100% consistent outfit colors and prompts."""
        # 1. First photo request in pajamas/bed
        prompt1, neg1, is_nude1, label1 = self.pm.craft_visual_prompt_full(
            "pap di kasur dong", user_id=self.user_id
        )
        self.assertIn("Pajamas", label1)
        self.assertFalse(is_nude1)
        self.assertIn("wine-red silk camisole", prompt1.lower())

        # 2. Second photo request (e.g. pose lain / follow up) without outfit change
        prompt2, neg2, is_nude2, label2 = self.pm.craft_visual_prompt_full(
            "coba gaya lain yang manis", user_id=self.user_id
        )
        self.assertEqual(label1, label2)
        # Outfits must match exactly to guarantee clothing colors do not randomly flip!
        outfit1 = self.pm.detect_clothing_intent("pap di kasur dong", user_id=self.user_id)[0]
        outfit2 = self.pm.detect_clothing_intent("coba gaya lain yang manis", user_id=self.user_id)[0]
        self.assertEqual(outfit1, outfit2)
        self.assertIn("wine-red silk camisole", outfit1.lower())
        self.assertIn("wine-red silk camisole", prompt2.lower())

    def test_outfit_color_updates_when_outfit_changes(self):
        """When the outfit actually changes, the locked outfit prompt updates properly."""
        # 1. Generate photo in pajamas
        prompt1, _, _, label1 = self.pm.craft_visual_prompt_full(
            "pap di kamar tidur", user_id=self.user_id
        )
        self.assertIn("Pajamas", label1)
        self.assertIn("wine-red silk camisole", prompt1.lower())

        # 2. User explicitly requests maid outfit
        prompt2, _, _, label2 = self.pm.craft_visual_prompt_full(
            "coba pakai baju maid", user_id=self.user_id
        )
        self.assertIn("Maid", label2)
        self.assertIn("maid", prompt2.lower())
        self.assertNotEqual(prompt1, prompt2)

    def test_persona_specific_color_palettes(self):
        """Each persona must resolve concrete, consistent outfit colors."""
        pm_akira = PersonaManager(active_key="akira")
        pm_runa = PersonaManager(active_key="runa")

        akira_pajamas = pm_akira.get_preset_outfit("pajamas")
        runa_pajamas = pm_runa.get_preset_outfit("pajamas")

        self.assertIn("wine-red silk camisole", akira_pajamas["prompt"].lower())
        self.assertIn("baby pink silk camisole", runa_pajamas["prompt"].lower())

        akira_kimono = pm_akira.get_preset_outfit("kimono")
        runa_kimono = pm_runa.get_preset_outfit("kimono")

        self.assertIn("crimson", akira_kimono["prompt"].lower())
        self.assertIn("cherry-blossom pink", runa_kimono["prompt"].lower())

    def test_underwear_and_bra_panties_consistency(self):
        """Verifies bra, panties, and lingerie sets have persona-specific, consistent colors across undress stages."""
        pm_akira = PersonaManager(active_key="akira")
        pm_runa = PersonaManager(active_key="runa")

        # 1. Check Akira's underwear signature palette (dark burgundy / wine-red)
        akira_shirt_off = pm_akira.get_preset_outfit("shirt_off")
        akira_bottoms_off = pm_akira.get_preset_outfit("bottoms_off")
        akira_bra_off = pm_akira.get_preset_outfit("bra_off")
        akira_lingerie = pm_akira.get_preset_outfit("lingerie")

        self.assertIn("dark burgundy lace bra", akira_shirt_off["prompt"].lower())
        self.assertIn("dark burgundy lace bra and panties", akira_bottoms_off["prompt"].lower())
        self.assertIn("dark burgundy lace panties", akira_bra_off["prompt"].lower())
        self.assertIn("dark burgundy lace lingerie", akira_lingerie["prompt"].lower())

        # 2. Check Runa's underwear signature palette (black lace with pink ribbons/bows)
        runa_shirt_off = pm_runa.get_preset_outfit("shirt_off")
        runa_bottoms_off = pm_runa.get_preset_outfit("bottoms_off")
        runa_bra_off = pm_runa.get_preset_outfit("bra_off")
        runa_lingerie = pm_runa.get_preset_outfit("lingerie")

        self.assertIn("white", runa_shirt_off["prompt"].lower())
        self.assertIn("black lace", runa_shirt_off["prompt"].lower())
        self.assertIn("pink ribbon", runa_shirt_off["prompt"].lower())
        self.assertIn("white and black lace bra and panties", runa_bottoms_off["prompt"].lower())
        self.assertIn("white and black lace panties", runa_bra_off["prompt"].lower())
        self.assertIn("white and black lace lingerie", runa_lingerie["prompt"].lower())

        # 3. Test multi-turn consistency for user in underwear stage
        pm_akira.set_undress_stage(self.user_id, 2)  # Stage 2: bra & panties
        outfit1, neg1, is_nude1, label1 = pm_akira.detect_clothing_intent("pap pose lain", user_id=self.user_id)
        outfit2, neg2, is_nude2, label2 = pm_akira.detect_clothing_intent("gaya lain lagi dong", user_id=self.user_id)

        self.assertEqual(label1, label2)
        self.assertEqual(outfit1, outfit2)
        self.assertIn("dark burgundy lace bra and panties", outfit1.lower())


if __name__ == '__main__':
    unittest.main()


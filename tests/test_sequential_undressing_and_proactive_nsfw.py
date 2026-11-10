"""
Unit tests for Sequential Undressing (Buka Baju Bertahap) and Proactive NSFW Roleplay (v2.4.22).
Verifies:
1. Sequential undress progression:
   Stage 0 (Clothed) -> Stage 1 (Kaos/shirt_off) -> Stage 2 (Celana/bottoms_off) -> Stage 3 (BH/bra_off) -> Stage 4 (Celana Dalam/nude).
2. Strict sequential enforcement (e.g. asking for pants while clothed starts with shirt first).
3. Reset undress state when wearing clothes or ending roleplay.
4. Immediate jump to nude when user explicitly requests 'buka semua / telanjang bulat sekarang'.
5. detect_clothing_intent correctly applies undress stage for user_id.
6. detect_nsfw_intent captures undressing and intimate roleplay actions.
"""

import unittest
from persona_manager import PersonaManager
from routing_engine import detect_nsfw_intent


class TestSequentialUndressingAndProactiveNSFW(unittest.TestCase):
    def setUp(self):
        self.persona_mgr = PersonaManager()
        self.test_user_id = 88776655
        self.persona_mgr.reset_undress_stage(self.test_user_id)

    def tearDown(self):
        self.persona_mgr.reset_undress_stage(self.test_user_id)

    def test_sequential_undress_step_by_step(self):
        """User guides undressing stage by stage: Kaos -> Celana -> BH -> Celana Dalam -> Telanjang Bulat."""
        # Initial: Stage 0 (Clothed)
        self.assertEqual(self.persona_mgr.get_undress_stage(self.test_user_id), 0)

        # Step 1: Buka baju / kaos
        target, desc, trans = self.persona_mgr.detect_undress_intent("buka bajumu dong sayang", current_stage=0)
        self.assertTrue(trans)
        self.assertEqual(target, 1)
        self.persona_mgr.set_undress_stage(self.test_user_id, target)
        self.assertEqual(self.persona_mgr.get_undress_stage(self.test_user_id), 1)

        # Check clothing intent for stage 1
        prompt, neg, is_nude, name = self.persona_mgr.detect_clothing_intent("gimana rasanya", user_id=self.test_user_id, is_nsfw=True)
        self.assertIn("shirt completely removed", prompt)
        self.assertIn("Kaos Terlepas", name)
        self.assertFalse(is_nude)

        # Step 2: Buka celana
        target, desc, trans = self.persona_mgr.detect_undress_intent("sekarang buka celanamu", current_stage=1)
        self.assertTrue(trans)
        self.assertEqual(target, 2)
        self.persona_mgr.set_undress_stage(self.test_user_id, target)
        self.assertEqual(self.persona_mgr.get_undress_stage(self.test_user_id), 2)

        prompt, neg, is_nude, name = self.persona_mgr.detect_clothing_intent("seksi banget", user_id=self.test_user_id, is_nsfw=True)
        self.assertIn("pants removed", prompt)
        self.assertIn("Celana Terlepas", name)
        self.assertFalse(is_nude)

        # Step 3: Buka BH
        target, desc, trans = self.persona_mgr.detect_undress_intent("lepas bra kamu ya", current_stage=2)
        self.assertTrue(trans)
        self.assertEqual(target, 3)
        self.persona_mgr.set_undress_stage(self.test_user_id, target)
        self.assertEqual(self.persona_mgr.get_undress_stage(self.test_user_id), 3)

        prompt, neg, is_nude, name = self.persona_mgr.detect_clothing_intent("cantik banget dadamu", user_id=self.test_user_id, is_nsfw=True)
        self.assertIn("topless", prompt)
        self.assertIn("BH Terlepas", name)
        self.assertTrue(is_nude)

        # Step 4: Buka celana dalam -> Full Nude
        target, desc, trans = self.persona_mgr.detect_undress_intent("sekarang buka celana dalammu", current_stage=3)
        self.assertTrue(trans)
        self.assertEqual(target, 4)
        self.persona_mgr.set_undress_stage(self.test_user_id, target)
        self.assertEqual(self.persona_mgr.get_undress_stage(self.test_user_id), 4)

        prompt, neg, is_nude, name = self.persona_mgr.detect_clothing_intent("kamu indah banget", user_id=self.test_user_id, is_nsfw=True)
        self.assertIn("completely nude", prompt)
        self.assertIn("Tanpa Busana", name)
        self.assertTrue(is_nude)

    def test_sequential_enforcement_pants_requested_at_stage_0(self):
        """When user asks to open pants at stage 0, order requires starting with shirt first."""
        target, desc, trans = self.persona_mgr.detect_undress_intent("buka celana dong", current_stage=0)
        self.assertTrue(trans)
        self.assertEqual(target, 1)  # Starts with shirt first!

    def test_direct_full_nude_intent(self):
        """When user asks to open everything at once, jump straight to stage 4."""
        target, desc, trans = self.persona_mgr.detect_undress_intent("buka semua bajumu sekarang", current_stage=0)
        self.assertTrue(trans)
        self.assertEqual(target, 4)

    def test_progressive_undress_with_buka_lagi(self):
        """'Buka lagi' advances to next stage smoothly."""
        target_1, _, _ = self.persona_mgr.detect_undress_intent("buka pelan-pelan ya", current_stage=0)
        self.assertEqual(target_1, 1)

        target_2, _, _ = self.persona_mgr.detect_undress_intent("buka lagi berikutnya", current_stage=1)
        self.assertEqual(target_2, 2)

        target_3, _, _ = self.persona_mgr.detect_undress_intent("lanjut buka lagi", current_stage=2)
        self.assertEqual(target_3, 3)

        target_4, _, _ = self.persona_mgr.detect_undress_intent("buka tahap berikutnya", current_stage=3)
        self.assertEqual(target_4, 4)

    def test_reset_clothing(self):
        """User tells waifu to put clothes back on."""
        self.persona_mgr.set_undress_stage(self.test_user_id, 4)
        self.assertEqual(self.persona_mgr.get_undress_stage(self.test_user_id), 4)

        target, desc, trans = self.persona_mgr.detect_undress_intent("pakai baju kamu lagi ya", current_stage=4)
        self.assertTrue(trans)
        self.assertEqual(target, 0)
        self.persona_mgr.set_undress_stage(self.test_user_id, target)
        self.assertEqual(self.persona_mgr.get_undress_stage(self.test_user_id), 0)

    def test_routing_engine_detects_undressing_intent(self):
        """Routing engine recognizes undressing phrases as NSFW turns."""
        self.assertTrue(detect_nsfw_intent("buka bajumu pelan-pelan"))
        self.assertTrue(detect_nsfw_intent("sekarang lepas celanamu"))
        self.assertTrue(detect_nsfw_intent("buka bh kamu dong"))
        self.assertTrue(detect_nsfw_intent("buka celana dalammu sayang"))

    def test_english_nsfw_phrases_and_undress_progression(self):
        """Verifies English intimate roleplay phrases and progressive undressing."""
        # 1. Routing engine detection
        self.assertTrue(detect_nsfw_intent("I want to touch first, come closer"))
        self.assertTrue(detect_nsfw_intent("I will take off your clothes slowly"))
        self.assertTrue(detect_nsfw_intent("sure, I kiss you now while touch your skin"))
        self.assertTrue(detect_nsfw_intent("let me see how wet you are"))
        self.assertTrue(detect_nsfw_intent("of course if it is allow to taste you"))

        # 2. English undress progression
        target_1, _, trans_1 = self.persona_mgr.detect_undress_intent("I will take off your clothes slowly", current_stage=0)
        self.assertTrue(trans_1)
        self.assertEqual(target_1, 1)

        target_2, _, trans_2 = self.persona_mgr.detect_undress_intent("take off the rest too", current_stage=1)
        self.assertTrue(trans_2)
        self.assertEqual(target_2, 2)

        target_all, _, trans_all = self.persona_mgr.detect_undress_intent("take off everything now", current_stage=0)
        self.assertTrue(trans_all)
        self.assertEqual(target_all, 4)

    def test_intimate_nsfw_visual_scene_moments(self):
        """Verifies automatic visual scene triggering for intimate touch, wetness, and oral moments."""
        # Touch / caress
        user_touch = "I want to touch first, come closer"
        reply_touch = "*trembling steps forward, guiding your hands to my waist* P-please... touch me slowly... so warm..."
        is_scene_t, prompt_t = self.persona_mgr.detect_visual_scene_moment(user_touch, reply_touch)
        self.assertTrue(is_scene_t)
        self.assertIn("sensual", prompt_t)

        # Wetness / parting legs
        user_wet = "let me see how wet you are"
        reply_wet = "*shakily lifting my skirt, legs parting just enough* L-look... see how wet I am already? 😳"
        is_scene_w, prompt_w = self.persona_mgr.detect_visual_scene_moment(user_wet, reply_wet)
        self.assertTrue(is_scene_w)
        self.assertIn("panties", prompt_w)

        # Tasting / oral ecstasy
        user_taste = "of course if it is allow to taste you"
        reply_taste = "*body arching off the bed as you lower your head* A-ah! Yes, please taste me... don't stop..."
        is_scene_oral, prompt_oral = self.persona_mgr.detect_visual_scene_moment(user_taste, reply_taste)
        self.assertTrue(is_scene_oral)
        self.assertIn("arching body", prompt_oral)


if __name__ == "__main__":
    unittest.main()

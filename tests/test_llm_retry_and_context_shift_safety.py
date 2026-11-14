import unittest
import time
from unittest.mock import MagicMock, patch
from persona_manager import PersonaManager
import bot

class TestLLMRetryAndContextShiftSafety(unittest.TestCase):
    def setUp(self):
        self.persona_mgr = PersonaManager()

    def test_context_shift_resets_undress_stage_on_lab_or_casual_query(self):
        user_id = 99881122
        # Set user into nude undress stage
        self.persona_mgr.set_undress_stage(user_id, 4)
        stage = self.persona_mgr.get_undress_stage(user_id)
        self.assertEqual(stage, 4)

        # Context shift triggers with casual question / daily life query
        shifted = self.persona_mgr.check_context_shift(user_id, "Kamu pulang jam berapa?")
        self.assertTrue(shifted)

        # Stage must be reset to 0 and outfit back to default
        new_stage = self.persona_mgr.get_undress_stage(user_id)
        new_key, _ = self.persona_mgr.get_user_outfit(user_id)
        self.assertEqual(new_stage, 0)
        self.assertEqual(new_key, "default")

    def test_lab_scene_detection_and_sfw_override(self):
        # Laboratory mention must detect lab scene
        scene = self.persona_mgr.extract_contextual_scene(
            user_text="Tadi seharian aku di lab nimbang sampel daun buat ekstraksi",
            conversational_reply="Wah pasti cape ya"
        )
        self.assertIn("laboratory", scene.lower())

        # When in lab, clothing intent detects safe clothed outfit
        clothing_prompt, neg_prompt, is_nude, outfit_name = self.persona_mgr.detect_clothing_intent(
            user_text="Tadi seharian aku di lab praktikum",
            scene_hint=scene
        )
        self.assertFalse(is_nude)
        self.assertNotIn("nude", outfit_name.lower())
        self.assertNotIn("lingerie", outfit_name.lower())
        self.assertIn("jas", outfit_name.lower())

    def test_llm_unreachable_does_not_return_canned_static_roleplay(self):
        class FailingLLM:
            def is_available(self):
                return False
            def chat(self, *args, **kwargs):
                raise ConnectionError("LLM Offline")

        # Fallback reaction must return None so system notifies cleanly rather than faking static canned text
        reaction = bot.get_contextual_fallback_reaction(
            user_text="Halo apa kabar?",
            persona_name="Mimi",
            llm_client=FailingLLM(),
            history=[]
        )
        self.assertIsNone(reaction)

if __name__ == "__main__":
    unittest.main()

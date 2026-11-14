import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona_manager import PersonaManager, DEFAULT_PERSONAS, PERSONA_OUTFIT_COLORS
import student_schedule
from story_engine import StoryEngine


class TestAliaPersonaIntegration(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager()
        self.pm.active_key = "alia"

    def test_alia_in_default_personas_and_loaded(self):
        self.assertIn("alia", DEFAULT_PERSONAS)
        self.assertIn("alia", self.pm.personas)
        alia_data = self.pm.personas["alia"]
        self.assertEqual(alia_data["name"], "Alia")
        self.assertEqual(alia_data["age"], 20)
        self.assertIn("Tsundere", alia_data["archetype"])
        self.assertIn("personas/brief/Alia.png", alia_data["avatar_image"])

    def test_alia_system_instruction_contains_russian_quirks(self):
        instruction = self.pm.personas["alia"]["system_instruction"]
        self.assertIn("Krasavchik", instruction)
        self.assertIn("Milyy", instruction)
        self.assertIn("Lyublyu tebya", instruction)
        self.assertIn("Duračok", instruction)
        self.assertIn("Bahasa Rusia", instruction)

    def test_alia_visual_prompt_canonical_traits(self):
        prompt, neg, is_nude, outfit = self.pm.craft_visual_prompt_full(
            "foto kamu di kampus dong", user_id=98765
        )
        self.assertIn("platinum-silver hair", prompt)
        self.assertIn("red ribbon bow", prompt)
        self.assertIn("sapphire blue eyes", prompt)
        self.assertIn("ahoge", prompt)
        self.assertIn("blazer", prompt.lower())
        self.assertFalse(is_nude)

    def test_alia_persistent_undergarment_lingerie_and_undress(self):
        # Lingerie test
        p_ling, _, _, out_ling = self.pm.craft_visual_prompt_full("pakai lingerie", user_id=98765)
        self.assertIn("pure white silk and sapphire-blue lace", p_ling.lower())
        self.assertIn("crimson ribbon", p_ling.lower())

        # Topless / bra off test
        p_topless, _, is_nude, _ = self.pm.craft_visual_prompt_full("buka bra kamu", user_id=98765)
        self.assertTrue(is_nude)
        self.assertIn("topless", p_topless)
        self.assertIn("white and sapphire lace panties", p_topless.lower())
        self.assertIn("crimson ribbon", p_topless.lower())

    def test_alia_student_schedule_and_profile(self):
        profile = student_schedule.get_student_profile("alia")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "Alia")
        self.assertIn("Diplomasi", profile["major"])
        self.assertIn("blazer", profile["campus_outfit"].lower())

    def test_alia_storyline_arcs(self):
        se = StoryEngine()
        story = se.storylines.get("alia")
        self.assertIsNotNone(story)
        self.assertEqual(story.get("current_arc_title"), "Pemilihan Ketua Dewan Mahasiswa & Perasaan yang Tersembunyi")
        self.assertEqual(len(story.get("episodes", [])), 5)


if __name__ == "__main__":
    unittest.main()

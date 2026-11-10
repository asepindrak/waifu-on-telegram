"""
Unit tests for Adult/NSFW Roleplay Focus and Photo Alignment (v2.4.17).
Verifies:
1. detect_clothing_intent recognizes intimate requests ('nenen', 'toket', 'telanjang bulat', etc.)
   and properly respects is_nsfw flag.
2. detect_anatomy_cues accurately extracts Danbooru tags for requested body parts (breasts, thighs, butt).
3. craft_visual_prompt_full integrates anatomy cues into visual prompt when requested.
4. Routing and intent detection identifies adult turns and intimate photo requests.
"""

import unittest
from persona_manager import PersonaManager
from routing_engine import detect_nsfw_intent


class TestNSFWRoleplayAndPhotoAlignment(unittest.TestCase):
    def setUp(self):
        self.persona_mgr = PersonaManager()

    def test_clothing_intent_explicit_anatomy_and_nude(self):
        # Explicit Indonesian anatomy & nude cues
        test_cases = [
            "foto nenen kamu dong",
            "pap toket kamu yang montok",
            "pap telanjang bulat",
            "tanpa sehelai benang ya",
            "coba buka celana kamu",
            "foto bugil sekarang",
        ]
        for query in test_cases:
            prompt, neg, is_nude, name = self.persona_mgr.detect_clothing_intent(query)
            self.assertTrue(is_nude, f"Failed for query '{query}': expected is_nude=True, got {is_nude}")
            self.assertIn("nude", prompt.lower(), f"Prompt missing nude keywords for '{query}'")

    def test_clothing_intent_with_is_nsfw_flag(self):
        # When turn is NSFW and user asks for a photo without a clothed preset, default to nude
        query = "foto kamu yang cantik dong sayang"
        prompt, neg, is_nude, name = self.persona_mgr.detect_clothing_intent(query, is_nsfw=True)
        self.assertTrue(is_nude, f"Expected is_nude=True when is_nsfw=True, got {is_nude}")

        # If user asks for lingerie in NSFW mode, return lingerie
        query_lingerie = "pake lingerie renda hitam ya"
        prompt_ling, neg_ling, is_nude_ling, name_ling = self.persona_mgr.detect_clothing_intent(query_lingerie, is_nsfw=True)
        self.assertFalse(is_nude_ling)
        self.assertIn("lingerie", prompt_ling.lower())

    def test_detect_anatomy_cues(self):
        # Breasts / nenen / toket
        cue_breast = self.persona_mgr.detect_anatomy_cues("fokus ke toket kamu ya")
        self.assertIsNotNone(cue_breast)
        self.assertIn("breasts", cue_breast)
        self.assertIn("nipples", cue_breast)

        # Thighs / paha
        cue_thigh = self.persona_mgr.detect_anatomy_cues("liat paha mulus kamu dong")
        self.assertIsNotNone(cue_thigh)
        self.assertIn("thighs", cue_thigh)

        # Butt / pantat
        cue_butt = self.persona_mgr.detect_anatomy_cues("pap pantat dari belakang")
        self.assertIsNotNone(cue_butt)
        self.assertIn("butt", cue_butt)

    def test_craft_visual_prompt_full_with_anatomy(self):
        prompt, extra_neg, is_nude, name = self.persona_mgr.craft_visual_prompt_full(
            "foto nenen kamu sambil rebahan telentang", is_nsfw=True
        )
        self.assertTrue(is_nude)
        self.assertIn("breasts", prompt)
        self.assertIn("lying on back", prompt)

    def test_detect_nsfw_intent_expanded_keywords(self):
        # Verify routing engine catches all Indonesian adult/intimate phrases
        nsfw_queries = [
            "foto toket kamu dong",
            "pap nenen",
            "telanjang bulat ya",
            "*meraba payudara kamu*",
            "aku remas pantat kamu pelan-pelan",
            "buka semua baju kamu sayang"
        ]
        for q in nsfw_queries:
            self.assertTrue(detect_nsfw_intent(q), f"detect_nsfw_intent failed to catch: '{q}'")


if __name__ == "__main__":
    unittest.main()

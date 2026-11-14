import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona_manager import PersonaManager, PERSONA_OUTFIT_COLORS


class TestUnderwearPersistenceAndColorOverride(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager()

    def test_runa_canonical_underwear(self):
        self.pm.set_active_persona("runa")
        # Bottoms off (underwear set) without user color request
        prompt, neg, is_nude, name = self.pm.detect_clothing_intent("coba buka baju tinggal pakaian dalam", user_id=101)
        self.assertIn("white silk and lace bra with black lace trim", prompt.lower())
        self.assertIn("pink ribbon", prompt.lower())

    def test_mimi_canonical_underwear(self):
        self.pm.set_active_persona("mimi")
        prompt, neg, is_nude, name = self.pm.detect_clothing_intent("coba pake pakaian dalam", user_id=102)
        self.assertIn("black lace", prompt.lower())
        self.assertIn("bell", prompt.lower())
        self.assertIn("cat ears", prompt.lower())
        self.assertIn("cat tail", prompt.lower())

    def test_sylvie_canonical_underwear(self):
        self.pm.set_active_persona("sylvie")
        prompt, neg, is_nude, name = self.pm.detect_clothing_intent("pap cuma pake bh sama celana dalam", user_id=103)
        self.assertIn("emerald-green", prompt.lower())
        self.assertIn("gold", prompt.lower())
        self.assertIn("pointy elf ears", prompt.lower())

    def test_user_color_override_red_bra(self):
        self.pm.set_active_persona("runa")
        prompt, neg, is_nude, name = self.pm.detect_clothing_intent("coba pake bra merah", user_id=104)
        self.assertIn("red lace bra", prompt.lower())

    def test_user_color_override_blue_lingerie(self):
        self.pm.set_active_persona("mimi")
        prompt, neg, is_nude, name = self.pm.detect_clothing_intent("pap pake lingerie warna biru", user_id=105)
        self.assertIn("blue lace", prompt.lower())
        self.assertIn("cat ears", prompt.lower())

    def test_mimi_cat_ears_not_negated(self):
        self.pm.set_active_persona("mimi")
        vis_prompt, extra_neg, is_nude, name = self.pm.craft_visual_prompt_full("kirim foto selfie cantik", user_id=106)
        self.assertNotIn("cat ears", extra_neg)
        self.assertNotIn("animal ears", extra_neg)
        self.assertIn("cat ears", vis_prompt.lower())


if __name__ == "__main__":
    unittest.main()

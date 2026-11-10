"""
Unit tests for User Name Onboarding and Name Asking Logic (v2.4.18).
Verifies:
1. When user name is not yet set, memory context instructs waifu to ask user's name.
2. auto_extract_facts accurately extracts user name from various Indonesian phrasing patterns.
3. Direct short answer to waifu's previous name question is captured and stored.
4. Calling preference and pet name rules update appropriately.
"""

import unittest
from memory_engine import MemoryEngine


class TestUserNameOnboarding(unittest.TestCase):
    def setUp(self):
        self.memory_engine = MemoryEngine()
        self.test_user_id = 99887766
        # Reset profile for test user
        self.memory_engine.update_profile(
            self.test_user_id,
            name="",
            call_name="",
            allow_pet_name=False
        )

    def test_unknown_name_guideline_in_context(self):
        ctx = self.memory_engine.format_memory_context(self.test_user_id)
        self.assertIn("belum tahu nama user", ctx)
        self.assertIn("Tanyakan siapa namanya", ctx)

    def test_extract_name_explicit_patterns(self):
        # 1. "Nama aku Budi Santoso"
        self.memory_engine.auto_extract_facts("Halo, nama aku Budi Santoso!", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("name"), "Budi Santoso")
        self.assertEqual(prof.get("call_name"), "Budi Santoso")

        # 2. "Panggil aku Rama aja"
        self.memory_engine.auto_extract_facts("Panggil aku Rama aja ya", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("call_name"), "Rama")

        # 3. "Kenalin aku Sandra salam kenal"
        self.memory_engine.auto_extract_facts("Kenalin aku Sandra salam kenal", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("call_name"), "Sandra")

    def test_extract_name_from_previous_question(self):
        history = [
            {"role": "user", "content": "Halo!"},
            {"role": "assistant", "content": "*Runa tersenyum manis*\n\nHalo juga! Ngomong-ngomong, nama kamu siapa ya? Supaya aku tahu harus manggil kamu siapa~"}
        ]
        self.memory_engine.auto_extract_facts("Alex", self.test_user_id, history=history)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("name"), "Alex")
        self.assertEqual(prof.get("call_name"), "Alex")

    def test_non_name_phrases_not_extracted(self):
        self.memory_engine.update_profile(self.test_user_id, name="", call_name="")
        self.memory_engine.auto_extract_facts("Aku lagi makan mie ayam nih", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("name"), "")
        self.assertEqual(prof.get("call_name"), "")

    def test_pet_name_management(self):
        # Request to be called sayang
        self.memory_engine.auto_extract_facts("Panggil aku sayang aja", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("call_name"), "sayang")
        self.assertTrue(prof.get("allow_pet_name"))

        # Request to stop calling sayang
        self.memory_engine.auto_extract_facts("Jangan panggil sayang lagi ya", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("call_name"), "")
        self.assertFalse(prof.get("allow_pet_name"))


if __name__ == "__main__":
    unittest.main()

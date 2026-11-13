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
        # Reset profile & facts for test user
        self.memory_engine.data["facts"][str(self.test_user_id)] = []
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

        # 4. Correction clause with trailing action: "bukan alex, aku adens, ayo kita mengerjakan PR"
        self.memory_engine.update_profile(self.test_user_id, name="", call_name="")
        self.memory_engine.auto_extract_facts("bukan alex, aku adens, ayo kita mengerjakan PR", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("name"), "Adens")
        self.assertEqual(prof.get("call_name"), "Adens")

        # Verify context explicitly forbids asking name again once known
        ctx = self.memory_engine.format_memory_context(self.test_user_id)
        self.assertIn("DILARANG KERAS menanyakan namanya lagi", ctx)

        # 5. English correction & introduction: "Not Alex, I'm Aden, let's study together"
        self.memory_engine.update_profile(self.test_user_id, name="", call_name="")
        self.memory_engine.auto_extract_facts("Not Alex, I'm Aden, let's study together", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("name"), "Aden")
        self.assertEqual(prof.get("call_name"), "Aden")

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

        # Action verbs / intimate phrases / mid-sentence 'aku ...' must never poison user name
        false_positives = [
            "Aku masukin ya",
            "Nanti aku masukin pelan-pelan",
            "Aku cium ya",
            "Mau aku peluk kamu?",
            "Panggil dokter sekarang",
            "Biar aku fotoin kamu",
            "Aku pulang dulu",
        ]
        for msg in false_positives:
            self.memory_engine.auto_extract_facts(msg, self.test_user_id)
            prof = self.memory_engine.get_profile(self.test_user_id)
            self.assertEqual(prof.get("name"), "", f"False positive extracted from: {msg!r}")
            self.assertEqual(prof.get("call_name"), "", f"False positive call_name from: {msg!r}")

        # Even right after waifu asked user's name, short verbs/actions must not be parsed as name
        history = [
            {"role": "assistant", "content": "Ngomong-ngomong, nama kamu siapa ya?"}
        ]
        for reply in ("Masukin", "Masukin?", "Cium", "Peluk kamu", "Belum tidur"):
            self.memory_engine.auto_extract_facts(reply, self.test_user_id, history=history)
            prof = self.memory_engine.get_profile(self.test_user_id)
            self.assertEqual(prof.get("name"), "", f"Conversational false positive from: {reply!r}")
            self.assertEqual(prof.get("call_name"), "", f"Conversational false positive call_name from: {reply!r}")

    def test_valid_names_ending_in_in_still_accepted(self):
        self.memory_engine.update_profile(self.test_user_id, name="", call_name="")
        self.memory_engine.auto_extract_facts("Namaku Kevin salam kenal", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("name"), "Kevin")
        self.assertEqual(prof.get("call_name"), "Kevin")

        self.memory_engine.auto_extract_facts("Panggil aku Arifin aja", self.test_user_id)
        prof = self.memory_engine.get_profile(self.test_user_id)
        self.assertEqual(prof.get("call_name"), "Arifin")

    def test_sanitizes_poisoned_profile_on_load(self):
        import json, os, shutil, tempfile
        tmp_dir = tempfile.mkdtemp(prefix="waifu_name_sanitize_")
        try:
            tmp_file = os.path.join(tmp_dir, "memories.json")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump({
                    "profiles": {
                        "111": {"name": "Masukin", "call_name": "Masukin", "allow_pet_name": False},
                        "222": {"name": "Adens", "call_name": "Adens", "allow_pet_name": False},
                    },
                    "facts": {
                        "111": [
                            {"id": 1, "fact": "Nama: Peluk Kamu", "category": "identity"},
                            {"id": 2, "fact": "Nama: Cium", "category": "identity"},
                            {"id": 3, "fact": "Suka kopi latte", "category": "likes"},
                        ],
                        "222": [
                            {"id": 1, "fact": "Nama: Adens", "category": "identity"},
                        ],
                    },
                    "diary": {},
                    "affinity": {},
                }, f)

            eng = MemoryEngine(data_file=tmp_file)
            self.assertEqual(eng.get_profile(111).get("name"), "")
            self.assertEqual(eng.get_profile(111).get("call_name"), "")
            facts_111 = eng.get_facts(111)
            self.assertEqual([x["fact"] for x in facts_111], ["Suka kopi latte"])
            self.assertNotIn("Masukin", eng.format_memory_context(111))

            # Valid user remains intact
            self.assertEqual(eng.get_profile(222).get("name"), "Adens")
            self.assertEqual(eng.get_profile(222).get("call_name"), "Adens")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_calling_frequency_guideline_in_context(self):
        """Verify memory context directs waifu to call user by name occasionally, not in every turn."""
        self.memory_engine.update_profile(self.test_user_id, name="Adens", call_name="Adens")
        ctx = self.memory_engine.format_memory_context(self.test_user_id)
        self.assertIn("Adens", ctx)
        self.assertIn("DILARANG KERAS menanyakan namanya lagi", ctx)
        self.assertIn("JANGAN terlalu sering", ctx)
        self.assertIn("Gunakan kata ganti wajar 'kamu'", ctx)

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


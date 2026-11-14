import unittest
from bot import sanitize_waifu_tone_and_pronouns, is_hostile_or_nyolot
from persona_manager import PersonaManager, DEFAULT_PERSONAS


class TestWaifuToneAndPronouns(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager(active_key="runa")

    def test_sanitize_pronouns_converts_lo_lu_to_kamu(self):
        """Replaces second person street slang (lo, lu, elu, elo) with gentle 'kamu' preserving casing."""
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Lu lagi ngapain sekarang?"),
            "Kamu lagi ngapain sekarang?"
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Kenapa lo gak tidur semalam?"),
            "Kenapa kamu gak tidur semalam?"
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Ini buat elu, suka gak?"),
            "Ini buat kamu, suka gak?"
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Elo mau ikut jalan bareng?"),
            "Kamu mau ikut jalan bareng?"
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("LO MAU KEMANA?"),
            "KAMU MAU KEMANA?"
        )

    def test_sanitize_pronouns_converts_gue_gw_to_aku(self):
        """Replaces first person street slang (gue, gw, gua) with tender 'aku' preserving casing."""
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Gue kangen banget sama kamu."),
            "Aku kangen banget sama kamu."
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Gw mau cerita sesuatu nih."),
            "Aku mau cerita sesuatu nih."
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Gua lagi santai di kamar."),
            "Aku lagi santai di kamar."
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("GUE LAGI BACA BUKU"),
            "AKU LAGI BACA BUKU"
        )

    def test_sanitize_pronouns_preserves_lofi_and_normal_words(self):
        """Ensures 'lo-fi', 'lo fi', and words containing lo/lu (login, dulu, lalu, lucu) are untouched."""
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Lagi santai dengerin musik lo-fi di kamar."),
            "Lagi santai dengerin musik lo-fi di kamar."
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Dengerin lagu lo fi santai yuk."),
            "Dengerin lagu lo fi santai yuk."
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Aku mau login dulu yaa, lucu banget bajumu."),
            "Aku mau login dulu yaa, lucu banget bajumu."
        )

    def test_is_hostile_or_nyolot_detection(self):
        """Detects rude, combative, snarky, or 'nyolot' responses."""
        self.assertTrue(is_hostile_or_nyolot("Apaan sih, gak jelas banget kamu."))
        self.assertTrue(is_hostile_or_nyolot("Dih, kenapa lo sewot banget?"))
        self.assertTrue(is_hostile_or_nyolot("Bodo amat ah, ngapain diurusin."))
        self.assertTrue(is_hostile_or_nyolot("Gak usah kepo deh ya."))
        self.assertTrue(is_hostile_or_nyolot("Kenapa lu yang repot?"))
        self.assertTrue(is_hostile_or_nyolot("GR banget sih kamu jadi orang."))
        self.assertTrue(is_hostile_or_nyolot("Ngajak ribut ya kamu?"))

        # Gentle / normal / romantic sentences must NOT be flagged
        self.assertFalse(is_hostile_or_nyolot("*tersenyum manis menatapmu* Kamu udah makan belum?"))
        self.assertFalse(is_hostile_or_nyolot("Aku senang banget bisa ngobrol sama kamu hari ini 💕"))
        self.assertFalse(is_hostile_or_nyolot("Semangat ya kerjanya, jangan lupa istirahat 🥰"))

    def test_sanitize_tone_softens_mild_snark(self):
        """Softens mild snarky starters into gentle dialogue."""
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Dih, apaan sih lo?"),
            "Ada apa kamu?"
        )
        self.assertEqual(
            sanitize_waifu_tone_and_pronouns("Bodo amat, aku mau tidur duluan."),
            "Nggak apa-apa kok, aku mau tidur duluan."
        )

    def test_persona_instructions_forbid_lo_lu_and_nyolot(self):
        """Verifies persona system instructions explicitly forbid lo/lu/gue/gw and nyolot behavior."""
        for key in ["runa", "akira", "hina", "shiro", "yume"]:
            self.pm.set_active_persona(key)
            persona = self.pm.get_active_persona(lang="id")
            inst = persona["system_instruction"].lower()

            self.assertIn("aku", inst)
            self.assertIn("kamu", inst)
            self.assertIn("dilarang", inst)
            self.assertIn("nyolot", inst)
            self.assertTrue(any(slang in inst for slang in ["'lo'", "'lu'", "lo", "lu"]))

    def test_format_roleplay_italics_fixes_revealed_body_pronoun(self):
        """Fixes 'menampakkan dada dan perutmu' -> 'menampakkan dada dan perutnya' in self-reveal actions."""
        from bot import format_roleplay_italics
        raw_text = "*Shiro membuka ujung handuk perlahan hingga menampakkan dada dan perutmu yang mulus serta memancarkan kilau halus setelah shower tadi*\n\nAduh, nggak sengaja ketutup ya..."
        formatted = format_roleplay_italics(raw_text, character_name="Shiro")
        self.assertNotIn("perutmu", formatted)
        self.assertIn("perutnya", formatted)

        # But normal interaction with user's body like "mengelus perutmu" must be preserved!
        user_interaction = "*Shiro tersenyum manis lalu mengelus perutmu lembut*\n\nUdah kenyang yaa?"
        formatted_user = format_roleplay_italics(user_interaction, character_name="Shiro")
        self.assertIn("perutmu", formatted_user)


if __name__ == '__main__':
    unittest.main()


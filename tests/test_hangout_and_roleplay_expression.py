import unittest
from student_schedule import get_hourly_routine, detect_contextual_activity_and_outfit
from hangout_engine import get_hangout_engine, HANGOUT_VENUES
from story_engine import get_story_engine, CURATED_PERSONA_ARCS
import bot


class TestHangoutAndRoleplayExpression(unittest.TestCase):
    def setUp(self):
        self.hangout_engine = get_hangout_engine()
        self.user_id = 998877

    def test_weekend_schedule_has_no_lectures(self):
        """On Saturday (weekday=5) and Sunday (weekday=6), waifu has no campus lectures."""
        # Weekday check: hour 10 on Wednesday (weekday=2) has lecture
        weekday_routine = get_hourly_routine(hour=10, persona_key="akira", weekday=2)
        self.assertIn("kuliah", weekday_routine["activity_desc"].lower())

        # Weekend check: hour 10 on Saturday (weekday=5) is weekend brunch/cafe, NOT campus
        sat_routine = get_hourly_routine(hour=10, persona_key="akira", weekday=5)
        self.assertNotIn("kuliah", sat_routine["activity_desc"].lower())
        self.assertNotIn("kampus", sat_routine["activity_desc"].lower())
        self.assertTrue(any(k in sat_routine["activity_desc"].lower() for k in ["kafe", "brunch", "santai"]))

        # Weekend check: hour 14 on Sunday (weekday=6) is mall/cinema/hangout
        sun_routine = get_hourly_routine(hour=14, persona_key="akira", weekday=6)
        self.assertNotIn("kuliah", sun_routine["activity_desc"].lower())
        self.assertNotIn("dosen", sun_routine["activity_desc"].lower())
        self.assertTrue(any(k in sun_routine["activity_desc"].lower() for k in ["mall", "bioskop", "jalan", "santai"]))

    def test_format_roleplay_italics(self):
        """Converts *action* to Visual Novel style _character_action_ with clean newline separation, without dashes."""
        # 1. Action at beginning formatted in VN style with character name and separated with newline
        raw = "*tersenyum sambil merapikan beberapa buku ke dalam tas* Ini tugas kelompoknya udah hampir kelar kok"
        formatted = bot.format_roleplay_italics(raw, character_name="Akira")
        self.assertEqual(formatted, "_Akira tersenyum sambil merapikan beberapa buku ke dalam tas_\n\nIni tugas kelompoknya udah hampir kelar kok")

        # 2. Action in middle separated before and after
        raw_mid = "Halo sayang! *tersenyum manis* Gimana harimu?"
        formatted_mid = bot.format_roleplay_italics(raw_mid, character_name="Akira")
        self.assertEqual(formatted_mid, "Halo sayang!\n\n_Akira tersenyum manis_\n\nGimana harimu?")

        # 3. Parentheses emotion action converted and formatted
        raw_paren = "(tersipu malu) ih kamu mah..."
        formatted_paren = bot.format_roleplay_italics(raw_paren, character_name="Akira")
        self.assertEqual(formatted_paren, "_Akira tersipu malu_\n\nih kamu mah...")

        # 4. Preexisting dashes normalized and stripped cleanly
        raw_dash = "- *tersenyum manis* - Halo sayang"
        formatted_dash = bot.format_roleplay_italics(raw_dash, character_name="Akira")
        self.assertEqual(formatted_dash, "_Akira tersenyum manis_\n\nHalo sayang")

        # 5. Converts awkward first-person cues into visual novel narration
        raw_user = "- kulihatmu dengan senyuman hangat, merapikan rambutku -\n\nOh sayang, kan mau ngomong apa aja nih?"
        formatted_user = bot.format_roleplay_italics(raw_user, character_name="Runa")
        self.assertEqual(formatted_user, "_Runa melihat kamu dengan senyuman hangat sambil merapikan rambutnya_\n\nOh sayang, kan mau ngomong apa aja nih?")

        # 6. Preserves **bold** text without inserting dashes
        raw_bold = "*tersipu malu* Kamu itu **ganteng banget** hari ini!"
        formatted_bold = bot.format_roleplay_italics(raw_bold, character_name="Akira")
        self.assertIn("**ganteng banget**", formatted_bold)
        self.assertIn("_Akira tersipu malu_\n\n", formatted_bold)
        self.assertNotIn("- _", formatted_bold)

        # 7. Code blocks remain untouched
        raw_code = "*mengetik cepat* Coba cek `print(*args)` ini ya!"
        formatted_code = bot.format_roleplay_italics(raw_code, character_name="Akira")
        self.assertIn("`print(*args)`", formatted_code)
        self.assertIn("_Akira mengetik cepat_\n\n", formatted_code)

        # 8. Should NOT prepend or duplicate character name when action already has subject/character name
        raw_dup = "*Bibir Hina sedikit terbuka menatap layar saat kau mendekat, lalu ia membenturkan kepalanya pelan ke dadamu dengan tatapan penuh harap* Halo..."
        formatted_dup = bot.format_roleplay_italics(raw_dup, character_name="Hina")
        self.assertEqual(
            "_Bibir Hina sedikit terbuka menatap layar saat kau mendekat, lalu ia membenturkan kepalanya pelan ke dadamu dengan tatapan penuh harap_\n\nHalo...",
            formatted_dup,
        )

        # 9. Should strip accidental leading "Hina " before "Bibir Hina..." or "Tangannya..."
        raw_accidental_lead = "*Hina Bibir Hina sedikit terbuka* Oh?"
        self.assertEqual("_Bibir Hina sedikit terbuka_\n\nOh?", bot.format_roleplay_italics(raw_accidental_lead, character_name="Hina"))
        raw_possessive = "*Tangannya menyentuh bahumu lembut* Pelan-pelan ya..."
        self.assertEqual("_Tangannya menyentuh bahumu lembut_\n\nPelan-pelan ya...", bot.format_roleplay_italics(raw_possessive, character_name="Hina"))
        raw_lead_possessive = "*Hina Tangannya menyentuh bahumu lembut* Pelan-pelan ya..."
        self.assertEqual("_Tangannya menyentuh bahumu lembut_\n\nPelan-pelan ya...", bot.format_roleplay_italics(raw_lead_possessive, character_name="Hina"))

        # 10. Pronouns after initial mention stay natural without repeating character name
        raw_pronouns = "*Bibirnya melengkung tersenyum lalu dia mendekat* Kamu lucu."
        self.assertEqual("_Bibirnya melengkung tersenyum lalu Hina mendekat_\n\nKamu lucu.", bot.format_roleplay_italics(raw_pronouns, character_name="Hina"))
        raw_two_pronouns = "*ia tersenyum lalu dia mengangguk* Iya."
        self.assertEqual("_Hina tersenyum lalu dia mengangguk_\n\nIya.", bot.format_roleplay_italics(raw_two_pronouns, character_name="Hina"))

    def test_hangout_engine_lifecycle(self):
        """Tests starting a date, verifying active state, recording photos, and ending the date."""
        self.hangout_engine.end_date(self.user_id)
        self.assertFalse(self.hangout_engine.is_on_date(self.user_id))

        # Start date at cinema
        session = self.hangout_engine.start_date(self.user_id, "cinema")
        self.assertTrue(self.hangout_engine.is_on_date(self.user_id))
        self.assertEqual(session["venue_key"], "cinema")
        self.assertIn("Bioskop", session["venue_title"])

        # Check prompt formatting
        prompt = self.hangout_engine.format_hangout_prompt(self.user_id, "Akira")
        self.assertIn("Bioskop", prompt)
        self.assertIn("popcorn", prompt.lower())

        # Record photo
        self.hangout_engine.record_date_photo(self.user_id)
        active = self.hangout_engine.get_active_date(self.user_id)
        self.assertEqual(active["photos_taken"], 1)

        # End date
        finished = self.hangout_engine.end_date(self.user_id)
        self.assertIsNotNone(finished)
        self.assertFalse(self.hangout_engine.is_on_date(self.user_id))

    def test_hangout_intent_detection(self):
        """Tests detecting user's natural intent to go on a date or conclude a date."""
        # Intent to go to cafe
        self.assertEqual(self.hangout_engine.detect_hangout_intent("ngopi yuk di cafe"), "cafe")
        # Intent to go to cinema
        self.assertEqual(self.hangout_engine.detect_hangout_intent("nanti malam nonton bioskop bareng yuk"), "cinema")
        # Intent to visit kosan
        self.assertEqual(self.hangout_engine.detect_hangout_intent("aku mau main ke kosan kamu dong"), "home")
        # Intent to visit park
        self.assertEqual(self.hangout_engine.detect_hangout_intent("jalan-jalan sore ke taman yuk"), "park")
        # Intent to go to mall
        self.assertEqual(self.hangout_engine.detect_hangout_intent("jalan ke mall liat baju yuk"), "mall")

        # Intent to finish
        self.assertTrue(self.hangout_engine.detect_hangout_finish("udah malam nih, yuk pulang"))
        self.assertTrue(self.hangout_engine.detect_hangout_finish("selesai yuk jalannya"))
        self.assertFalse(self.hangout_engine.detect_hangout_finish("seru banget ya filmnya!"))

    def test_storyline_holiday_and_date_arcs(self):
        """Verifies story arcs include rich multi-day lore covering vacations and date moments."""
        akira_arcs = CURATED_PERSONA_ARCS.get("akira", [])
        self.assertGreaterEqual(len(akira_arcs), 2)
        # Check that arcs cover holidays / dates
        all_arcs_text = " ".join([
            a["arc_title"] + " " + " ".join([e.get("story_summary", "") for e in a.get("episodes", [])])
            for a in akira_arcs
        ])
        self.assertTrue("libur" in all_arcs_text.lower() or "quality time" in all_arcs_text.lower())

    def test_hangout_venues_attribute_accessible_on_instance(self):
        """Verifies HANGOUT_VENUES is accessible directly as an attribute on HangoutEngine instances."""
        self.assertTrue(hasattr(self.hangout_engine, "HANGOUT_VENUES"))
        self.assertIsInstance(self.hangout_engine.HANGOUT_VENUES, dict)
        venue_info = self.hangout_engine.HANGOUT_VENUES.get("cafe", {})
        self.assertEqual(venue_info.get("name"), "Kafe Estetik")


if __name__ == '__main__':
    unittest.main()

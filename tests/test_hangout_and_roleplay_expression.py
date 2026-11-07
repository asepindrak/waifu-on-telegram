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
        """Converts *action* to _action_ for Telegram Markdown italics while preserving **bold** and code."""
        # 1. Basic roleplay action conversion
        raw = "*tersenyum manis menatapmu* Hai sayang, ada apa?"
        formatted = bot.format_roleplay_italics(raw)
        self.assertEqual(formatted, "_tersenyum manis menatapmu_ Hai sayang, ada apa?")

        # 2. Preserves **bold** text
        raw_bold = "*tersipu malu* Kamu itu **ganteng banget** hari ini!"
        formatted_bold = bot.format_roleplay_italics(raw_bold)
        self.assertEqual(formatted_bold, "_tersipu malu_ Kamu itu **ganteng banget** hari ini!")

        # 3. Code blocks remain untouched
        raw_code = "*mengetik cepat* Coba cek `print(*args)` ini ya!"
        formatted_code = bot.format_roleplay_italics(raw_code)
        self.assertIn("`print(*args)`", formatted_code)
        self.assertIn("_mengetik cepat_", formatted_code)

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


if __name__ == '__main__':
    unittest.main()

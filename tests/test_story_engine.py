import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from story_engine import StoryEngine, CURATED_PERSONA_ARCS


class TestStoryEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="waifu_story_test_")
        self.data_file = os.path.join(self.test_dir, "test_storylines.json")
        self.engine = StoryEngine(data_file=self.data_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_auto_seed_curated_arcs(self):
        """Engine automatically seeds curated multi-day arcs for all default personas."""
        for p_key in ("runa", "akira", "hina", "shiro", "yume"):
            story = self.engine.get_today_story(p_key)
            self.assertIsNotNone(story)
            self.assertIn("arc_title", story)
            self.assertIn("day_theme", story)
            self.assertIn("story_summary", story)
            self.assertTrue(len(story["story_summary"]) > 10)

    def test_get_story_prompt_context(self):
        """Injects comprehensive narrative guidelines for LLM system prompt."""
        ctx = self.engine.get_story_prompt_context("runa")
        self.assertIn("[LATAR KEHIDUPAN & EPISODE CERITA HARI INI]", ctx)
        self.assertIn("Arc Cerita:", ctx)
        self.assertIn("Topik/Fokus Hari Ini:", ctx)
        self.assertIn("ATURAN INTEGRASI OBROLAN", ctx)

    def test_needs_replenishment_and_extension(self):
        """Verifies replenishment checking and timeline extension without gaps."""
        # By default seeded with 5 days, so needs_replenishment for 3 days should be False
        self.assertFalse(self.engine.needs_replenishment("runa", days_ahead=3))

        # Check for 10 days ahead (needs extension)
        self.assertTrue(self.engine.needs_replenishment("runa", days_ahead=10))

        # Ask for a story 8 days in the future, engine auto-extends timeline
        future_d = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
        story = self.engine.get_today_story("runa", date_str=future_d)
        self.assertIsNotNone(story)
        self.assertEqual(story["date"], future_d)

    def test_format_story_summary_card(self):
        """Produces aesthetic Markdown summary card for Telegram display."""
        card = self.engine.format_story_summary_card("runa", "Runa")
        self.assertIn("CERITA KEHIDUPAN RUNA HARI INI", card)
        self.assertIn("Arc", card)
        self.assertIn("Progres", card)
        self.assertIn("Episode Hari Ini", card)

    def test_llm_story_replenishment_parsing(self):
        """Successfully parses valid LLM JSON response and updates future schedule."""
        mock_llm = MagicMock()
        mock_response = '''
        ```json
        {
          "arc_title": "Ekspedisi Game Indie Runa",
          "episodes": [
            {
              "day_theme": "Pencarian Inspirasi Musik",
              "story_summary": "Runa mendengarkan kompilasi chiptune 8-bit untuk tema musik level 1.",
              "mood": "Ceria & terinspirasi",
              "key_activity": "Nongkrong di taman kota sambil pasang headphone",
              "photo_suggestion": "park bench, headphones, listening to music",
              "danbooru_tags": "park, headphone, listening to music, peaceful"
            }
          ]
        }
        ```
        '''
        mock_llm.chat.return_value = (mock_response, 120)

        # Force replenishment and wait for thread
        t = self.engine.replenish_storylines_if_llm_active("runa", mock_llm, force=True)
        self.assertIsNotNone(t)
        t.join(timeout=3)

        # Verify new arc was recorded
        with self.engine.lock:
            p_data = self.engine.storylines.get("runa", {})
            self.assertEqual(p_data.get("current_arc_title"), "Ekspedisi Game Indie Runa")


if __name__ == "__main__":
    unittest.main()

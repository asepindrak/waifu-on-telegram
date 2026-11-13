"""
tests/test_realtime_photo_lighting_and_engine_badge.py
Unit tests verifying:
1. Real-time photo atmosphere & lighting synchronization (day, night, morning, sunset, explicit overrides).
2. Contextual hangout/story venue resolution & button title ("nonton film di kosan" vs "nonton bioskop").
3. LLM Provider and Model badge generation on chat replies.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import time

from persona_manager import PersonaManager
from hangout_engine import HangoutEngine
from routing_engine import HybridLLMClient


class TestRealtimePhotoLightingAndEngineBadge(unittest.TestCase):
    def setUp(self):
        self.pm = PersonaManager()
        self.he = HangoutEngine(data_file="tests/test_user_hangouts_tmp.json")

    def tearDown(self):
        if os.path.exists("tests/test_user_hangouts_tmp.json"):
            try:
                os.remove("tests/test_user_hangouts_tmp.json")
            except Exception:
                pass

    def test_night_lighting_synchronization(self):
        """Simulate 23:00 (Night time) and verify night lighting is injected and daylight is negated."""
        fake_time = time.struct_time((2026, 11, 14, 23, 30, 0, 4, 318, 0))
        with patch("time.localtime", return_value=fake_time):
            pos, neg = self.pm.get_realtime_lighting_and_atmosphere(
                user_text="pap foto santai dong",
                scene_desc="standing in blooming park"
            )
            self.assertIn("night", pos.lower())
            self.assertIn("daylight", neg.lower())
            self.assertIn("sunlight", neg.lower())

            # Verify craft_visual_prompt_full integrates night lighting and purges daytime tokens
            prompt, extra_neg, _, _ = self.pm.craft_visual_prompt_full(
                user_text="pap foto di taman",
                scene_override="standing in blooming park, natural golden hour sunlight"
            )
            self.assertIn("night", prompt.lower())
            self.assertNotIn("natural golden hour sunlight", prompt.lower())
            self.assertIn("daylight", extra_neg.lower())

    def test_day_lighting_synchronization(self):
        """Simulate 13:00 (Midday) and verify daylight is injected and night is negated."""
        fake_time = time.struct_time((2026, 11, 14, 13, 0, 0, 4, 318, 0))
        with patch("time.localtime", return_value=fake_time):
            pos, neg = self.pm.get_realtime_lighting_and_atmosphere(
                user_text="pap foto santai",
                scene_desc="walking in the street"
            )
            self.assertIn("daylight", pos.lower())
            self.assertIn("night", neg.lower())

    def test_explicit_user_lighting_override(self):
        """When user explicitly asks for 'tengah malam' at 12:00 noon, midnight setting must prevail."""
        fake_time = time.struct_time((2026, 11, 14, 12, 0, 0, 4, 318, 0))
        with patch("time.localtime", return_value=fake_time):
            pos, neg = self.pm.get_realtime_lighting_and_atmosphere(
                user_text="pap foto suasana malam hari di kamar",
                scene_desc="relaxing on bed"
            )
            self.assertIn("night", pos.lower())
            self.assertIn("daylight", neg.lower())

    def test_kosan_vs_cinema_hangout_intent(self):
        """Verify 'nonton film di kosan' resolves to home with contextual title, never cinema."""
        # 1. Watching movie in kosan
        venue_home = self.he.detect_hangout_intent("aku sama waifu lagi nonton film di kosan")
        self.assertEqual(venue_home, "home")
        title_home = self.he.resolve_contextual_venue_title(venue_home, "lagi nonton film di kosan")
        self.assertIn("Nonton Film di Kosan", title_home)

        # 2. Watching movie in cinema
        venue_cinema = self.he.detect_hangout_intent("nanti malam kita nonton bioskop bareng yuk")
        self.assertEqual(venue_cinema, "cinema")
        title_cinema = self.he.resolve_contextual_venue_title(venue_cinema, "nonton bioskop")
        self.assertIn("Bioskop", title_cinema)

        # 3. Gaming in kosan
        venue_game = self.he.detect_hangout_intent("mabar game bareng di kamar kosan yuk")
        self.assertEqual(venue_game, "home")
        title_game = self.he.resolve_contextual_venue_title(venue_game, "mabar game bareng di kamar kosan")
        self.assertIn("Main Game di Kosan", title_game)

    def test_hangout_start_date_custom_title(self):
        """Verify start_date accurately records custom title and button text."""
        date_rec = self.he.start_date(9988, "home", custom_title="🎬 Nonton Film di Kosan")
        self.assertEqual(date_rec["venue_title"], "🎬 Nonton Film di Kosan")

        active = self.he.get_active_date(9988)
        self.assertIsNotNone(active)
        self.assertEqual(active["venue_title"], "🎬 Nonton Film di Kosan")

    def test_engine_badge_formatting(self):
        """Verify LLM client formats badges accurately for SFW (AGY) and NSFW (Local KoboldCPP)."""
        mock_sfw = MagicMock()
        mock_sfw.base_url = "http://127.0.0.1:8001/v1"
        mock_sfw.model = "gemini-3.8-flash-medium"

        mock_nsfw = MagicMock()
        mock_nsfw.base_url = "http://127.0.0.1:5001/v1"
        mock_nsfw.model = "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"

        client = HybridLLMClient(mode="split", sfw_client=mock_sfw, nsfw_client=mock_nsfw)

        # Record SFW turn
        client._record_used_engine(mock_sfw, is_nsfw=False, label="SFW")
        sfw_badge = client.get_last_engine_badge()
        self.assertIn("AGY", sfw_badge)
        self.assertIn("gemini-3.8-flash-medium", sfw_badge)
        self.assertNotIn("NSFW", sfw_badge)

        # Record NSFW turn
        client._record_used_engine(mock_nsfw, is_nsfw=True, label="NSFW")
        nsfw_badge = client.get_last_engine_badge()
        self.assertIn("Local KoboldCPP", nsfw_badge)
        self.assertIn("Huihui-Qwythos-9B", nsfw_badge)
        self.assertIn("NSFW", nsfw_badge)


if __name__ == "__main__":
    unittest.main()


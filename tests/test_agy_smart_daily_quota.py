"""
tests/test_agy_smart_daily_quota.py - Unit tests for AGY Smart Daily Quota & Smart Fallback.

Verifies:
1. is_agy_quota_error correctly identifies 429, RESOURCE_EXHAUSTED, capacity, and rate limits.
2. record_agy_image_quota_exhausted locks AGY into smart fallback for current calendar day.
3. is_agy_image_quota_exhausted automatically unlocks when a new day (tomorrow) arrives.
4. media_engine.generate_photo skips AGY entirely when quota is exhausted for the day.
5. When AGY fails, fallback NEVER routes to Pollinations cloud if user has local ComfyUI models.
6. When AGY fails and user has NO local ComfyUI models, fallback to Pollinations cloud is permitted.
"""

import os
import json
import time
import datetime
import unittest
from unittest.mock import patch, MagicMock

import agy_quota_manager
from media_engine import MediaEngine


class TestAgySmartDailyQuota(unittest.TestCase):

    def setUp(self):
        # Reset quota state before each test
        agy_quota_manager.reset_agy_image_quota()

    def tearDown(self):
        agy_quota_manager.reset_agy_image_quota()

    def test_is_agy_quota_error(self):
        """Verifies detection of various quota and rate limit errors."""
        self.assertTrue(agy_quota_manager.is_agy_quota_error("429 RESOURCE_EXHAUSTED"))
        self.assertTrue(agy_quota_manager.is_agy_quota_error("Capacity on the underlying image generation model has been exhausted"))
        self.assertTrue(agy_quota_manager.is_agy_quota_error("Quota limit reached for today"))
        self.assertTrue(agy_quota_manager.is_agy_quota_error("Too Many Requests: ratelimit exceeded"))
        self.assertTrue(agy_quota_manager.is_agy_quota_error("Daily request limit reached"))

        self.assertFalse(agy_quota_manager.is_agy_quota_error("Connection timed out"))
        self.assertFalse(agy_quota_manager.is_agy_quota_error("File not found"))
        self.assertFalse(agy_quota_manager.is_agy_quota_error(None))

    def test_record_and_check_quota_exhausted_same_day(self):
        """When recorded exhausted today, is_agy_image_quota_exhausted returns True for today."""
        self.assertFalse(agy_quota_manager.is_agy_image_quota_exhausted())

        agy_quota_manager.record_agy_image_quota_exhausted("429 RESOURCE_EXHAUSTED test")
        self.assertTrue(agy_quota_manager.is_agy_image_quota_exhausted())

    def test_quota_automatically_resets_next_day(self):
        """When the calendar date advances to tomorrow, quota lock resets automatically."""
        # Record exhaustion on day 1 (e.g. 2026-11-14)
        day1 = datetime.date(2026, 11, 14)
        with patch("datetime.date") as mock_date:
            mock_date.today.return_value = day1
            agy_quota_manager.record_agy_image_quota_exhausted("Daily limit reached")
            self.assertTrue(agy_quota_manager.is_agy_image_quota_exhausted())

        # Now simulate tomorrow (2026-11-15)
        day2 = datetime.date(2026, 11, 15)
        with patch("datetime.date") as mock_date:
            mock_date.today.return_value = day2
            # Tomorrow, it should return False and auto-reset
            self.assertFalse(agy_quota_manager.is_agy_image_quota_exhausted())

        # Subsequent check on day 2 is also False
        with patch("datetime.date") as mock_date:
            mock_date.today.return_value = day2
            self.assertFalse(agy_quota_manager.is_agy_image_quota_exhausted())

    def test_generate_photo_skips_agy_when_quota_exhausted_for_today(self):
        """generate_photo directly skips AGY CLI invocation when quota is already exhausted today."""
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188", allow_cloud_fallback=False)

        agy_quota_manager.record_agy_image_quota_exhausted("429 Cooldown")

        with patch.object(engine, "generate_image_agy") as mock_agy, \
             patch("agy_quota_manager.has_local_image_models", return_value=True), \
             patch("idle_engine.is_port_listening", return_value=True), \
             patch.object(engine, "generate_image_comfyui", return_value=b"ComfyFallbackBytes") as mock_comfy, \
             patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy"}):

            img, source = engine.generate_photo("cute smiling waifu", persona="yume")

            # AGY must NOT be called at all
            mock_agy.assert_not_called()
            # Local ComfyUI fallback must be used
            mock_comfy.assert_called_once()
            self.assertEqual(img, b"ComfyFallbackBytes")
            self.assertIn("Local ComfyUI", source)
            self.assertIsNotNone(engine.last_fallback_notice)
            self.assertIn("Smart Fallback aktif otomatis hingga besok", engine.last_fallback_notice["error"])

    def test_generate_photo_never_falls_back_to_pollinations_when_user_has_local_models(self):
        """
        CRITICAL USER SPECIFICATION:
        If user selects AGY, fallback MUST NOT go to Pollinations if user has local image models.
        """
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188", allow_cloud_fallback=True)

        with patch.object(engine, "generate_image_agy", return_value=None), \
             patch("agy_quota_manager.has_local_image_models", return_value=True), \
             patch("idle_engine.is_port_listening", return_value=True), \
             patch.object(engine, "generate_image_comfyui", return_value=None), \
             patch("media_engine.photo_vault.find_matching_photo", return_value=None), \
             patch.object(engine, "generate_image_cloud_fallback") as mock_cloud, \
             patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy", "MEDIA_FALLBACK_CLOUD": "true"}):

            engine.last_error = "AGY error"
            img, source = engine.generate_photo("1girl, anime girl", persona="runa")

            # Pollinations cloud fallback must NEVER be called
            mock_cloud.assert_not_called()
            self.assertIsNone(img)
            self.assertEqual(source, "Failed")

    def test_generate_photo_allows_pollinations_fallback_only_when_no_local_models(self):
        """
        When user selects AGY and truly has NO local models, Pollinations fallback is allowed.
        """
        engine = MediaEngine(comfyui_url="", allow_cloud_fallback=True)

        with patch.object(engine, "generate_image_agy", return_value=None), \
             patch("agy_quota_manager.has_local_image_models", return_value=False), \
             patch("media_engine.photo_vault.find_matching_photo", return_value=None), \
             patch.object(engine, "generate_image_cloud_fallback", return_value=b"CloudBytes") as mock_cloud, \
             patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy", "MEDIA_FALLBACK_CLOUD": "true"}):

            engine.last_error = "AGY error"
            img, source = engine.generate_photo("1girl, anime girl", persona="runa")

            # Pollinations cloud fallback is called because user has no local models
            mock_cloud.assert_called_once()
            self.assertEqual(img, b"CloudBytes")
            self.assertIn("Cloud Engine", source)

    def test_record_quota_on_cli_exhaustion(self):
        """When generate_photo catches a 429 quota error from AGY, it records quota exhaustion."""
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188", allow_cloud_fallback=False)

        def mock_agy_call(*args, **kwargs):
            engine.last_error = "429 RESOURCE_EXHAUSTED: Daily limit exceeded on AGY"
            return None

        with patch.object(engine, "generate_image_agy", side_effect=mock_agy_call), \
             patch("agy_quota_manager.has_local_image_models", return_value=True), \
             patch("idle_engine.is_port_listening", return_value=True), \
             patch.object(engine, "generate_image_comfyui", return_value=b"ComfyFallbackBytes"), \
             patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy"}):

            img, source = engine.generate_photo("anime girl in library", persona="akira")

            # Quota should now be recorded as exhausted for today
            self.assertTrue(agy_quota_manager.is_agy_image_quota_exhausted())


if __name__ == "__main__":
    unittest.main()

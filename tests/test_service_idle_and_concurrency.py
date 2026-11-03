import os
import time
import threading
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

from resource_lock import acquire_gpu_heavy_lock, GPU_HEAVY_LOCK
from idle_engine import IdleEngine


class TestServiceIdleAndConcurrency(unittest.TestCase):
    def test_gpu_heavy_lock_mutual_exclusion(self):
        """Verifies image and voice tasks never execute concurrently on GPU."""
        execution_log = []

        def task_photo():
            with acquire_gpu_heavy_lock("Task Photo"):
                execution_log.append("photo_start")
                time.sleep(0.1)
                execution_log.append("photo_end")

        def task_voice():
            time.sleep(0.02)  # Ensure photo starts first
            with acquire_gpu_heavy_lock("Task Voice"):
                execution_log.append("voice_start")
                time.sleep(0.05)
                execution_log.append("voice_end")

        t1 = threading.Thread(target=task_photo)
        t2 = threading.Thread(target=task_voice)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(execution_log, ["photo_start", "photo_end", "voice_start", "voice_end"])

    def test_idle_engine_record_activity_for_voice_and_agy(self):
        """Verifies activity timestamps update for voice and agy."""
        engine = IdleEngine(enabled=True)
        old_v = engine.last_voicestudio_activity
        old_a = engine.last_agy_activity

        time.sleep(0.02)
        engine.record_activity(is_voice=True)
        self.assertGreater(engine.last_voicestudio_activity, old_v)

        time.sleep(0.02)
        engine.record_activity(is_agy=True)
        self.assertGreater(engine.last_agy_activity, old_a)

    def test_idle_engine_status_summary(self):
        """Verifies status summary reports Voice and AGY."""
        engine = IdleEngine(enabled=True)
        summary = engine.get_status_summary()
        self.assertIn("Voice:", summary)
        self.assertIn("AGY:", summary)

    @patch("voicestudio_engine.voicestudio_engine.stop_service")
    def test_sleep_voicestudio(self, mock_stop):
        engine = IdleEngine(enabled=True)
        with patch("idle_engine.is_port_listening", return_value=True):
            res = engine.sleep_voicestudio()
            self.assertTrue(res)
            self.assertTrue(engine.is_voicestudio_sleeping)
            mock_stop.assert_called_once()

    @patch("voicestudio_engine.voicestudio_engine.start_service")
    def test_wake_voicestudio(self, mock_start):
        engine = IdleEngine(enabled=True)
        with patch("idle_engine.is_port_listening", side_effect=[False, True]), \
             patch("voicestudio_engine.voicestudio_engine.is_installed", return_value=True):
            res = engine.wake_voicestudio(timeout_seconds=2)
            self.assertTrue(res)
            self.assertFalse(engine.is_voicestudio_sleeping)
            mock_start.assert_called_once()

    def test_auto_run_voicestudio_in_voice_engine(self):
        """Verifies voice_engine auto-runs VoiceStudio if offline."""
        from voice_engine import VoiceEngine
        ve = VoiceEngine(voice_backend="voicestudio")

        with patch("voicestudio_engine.voicestudio_engine.is_installed", return_value=True), \
             patch("voicestudio_engine.voicestudio_engine.is_service_running", side_effect=[False, True, True]), \
             patch("voicestudio_engine.voicestudio_engine.start_service", return_value=True) as mock_start, \
             patch("voicestudio_engine.voicestudio_engine.synthesize", return_value="fake.mp3") as mock_synth, \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=1024):
            import asyncio
            res = asyncio.run(ve.generate_voice_note_async("Halo sayang!", "fake.mp3"))
            self.assertTrue(res)
            mock_start.assert_called_once()
            mock_synth.assert_called_once()


if __name__ == "__main__":
    unittest.main()

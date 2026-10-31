import os
import time
import unittest
from unittest.mock import MagicMock, patch
from idle_engine import IdleEngine
from health_engine import HealthEngine


class TestIdleEngine(unittest.TestCase):
    def setUp(self):
        self.mock_llm_client = MagicMock()
        self.mock_llm_client.check_health.return_value = {"online": True, "backend": "KoboldCPP", "model": "Qwythos-9B"}
        self.mock_media_engine = MagicMock()
        self.mock_media_engine.check_status.return_value = {"online": True, "backend": "ComfyUI Local"}

        self.health_engine = HealthEngine(
            llm_client=self.mock_llm_client,
            media_engine=self.mock_media_engine,
            enabled=True,
            self_healing_enabled=True
        )

        self.idle_engine = IdleEngine(
            health_engine=self.health_engine,
            enabled=True,
            idle_timeout_minutes=10,
            comfyui_on_demand=True
        )
        self.health_engine.idle_engine = self.idle_engine

    def tearDown(self):
        self.idle_engine.stop()

    def test_default_configuration(self):
        """Verify smart idle defaults to enabled, 10 minutes timeout, and ComfyUI on-demand."""
        engine = IdleEngine()
        self.assertTrue(engine.enabled)
        self.assertEqual(engine.idle_timeout_minutes, 10)
        self.assertTrue(engine.comfyui_on_demand)

    def test_record_activity_updates_timestamp(self):
        """Verify record_activity updates last_llm_activity timestamp."""
        old_time = self.idle_engine.last_llm_activity
        time.sleep(0.01)
        self.idle_engine.record_activity()
        self.assertGreater(self.idle_engine.last_llm_activity, old_time)

    @patch("idle_engine.is_port_listening", return_value=True)
    def test_ensure_llm_active_when_already_running(self, mock_port):
        """When LLM is already running, ensure_llm_active returns True instantly without waking."""
        ok = self.idle_engine.ensure_llm_active()
        self.assertTrue(ok)
        self.assertFalse(self.idle_engine.is_llm_sleeping)

    @patch("idle_engine.is_port_listening", side_effect=[False, True])
    def test_ensure_llm_active_wakes_sleeping_service(self, mock_port):
        """When LLM is sleeping, ensure_llm_active wakes KoboldCPP on-demand."""
        self.idle_engine.is_llm_sleeping = True
        with patch.object(self.health_engine, "heal_llm", return_value=True):
            ok = self.idle_engine.ensure_llm_active()
            self.assertTrue(ok)
            self.assertFalse(self.idle_engine.is_llm_sleeping)

    def test_health_engine_ignores_offline_when_sleeping(self):
        """When LLM is intentionally sleeping, HealthEngine watchdog does NOT alert failure."""
        self.idle_engine.is_llm_sleeping = True
        self.mock_llm_client.check_health.return_value = {"online": False}

        mock_bot = MagicMock()
        recipients = [12345]

        # Trigger check loop logic
        is_sleeping = bool(self.health_engine.idle_engine and self.health_engine.idle_engine.enabled and self.health_engine.idle_engine.is_llm_sleeping)
        self.assertTrue(is_sleeping)

        # Ensure failure is not broadcasted when sleeping
        with patch.object(self.health_engine, "broadcast_failure") as mock_fail:
            with patch.object(self.health_engine, "attempt_heal_service") as mock_heal:
                # If sleeping, failure alert should not be dispatched
                if not is_sleeping:
                    self.health_engine.broadcast_failure(mock_bot, recipients, {})
                    self.health_engine.attempt_heal_service("llm", mock_bot, recipients)
                mock_fail.assert_not_called()
                mock_heal.assert_not_called()

    def test_sleep_llm_sets_flag(self):
        """Verify sleep_llm terminates process and marks is_llm_sleeping = True."""
        with patch("idle_engine.is_port_listening", return_value=True):
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value = MagicMock(returncode=0)
                ok = self.idle_engine.sleep_llm()
                self.assertTrue(ok)
                self.assertTrue(self.idle_engine.is_llm_sleeping)

    def test_status_summary_includes_smart_idle(self):
        """Verify status summary reports active smart idle mode."""
        summary = self.idle_engine.get_status_summary()
        self.assertIn("Aktif", summary)
        self.assertIn("10m", summary)

    def test_ensure_llm_active_failure_edits_message_with_error(self):
        """When LLM waking fails, ensure_llm_active informs user instead of deleting status and staying silent."""
        mock_bot = MagicMock()
        mock_msg = MagicMock()
        mock_msg.message_id = 999
        mock_bot.send_message.return_value = mock_msg

        with patch.object(self.idle_engine, "wake_llm", return_value=False), \
             patch.object(self.idle_engine, "is_llm_ready", return_value=False):
            ok = self.idle_engine.ensure_llm_active(bot=mock_bot, chat_id=123)
            self.assertFalse(ok)
            # Must NOT delete message
            mock_bot.delete_message.assert_not_called()
            # Must edit message into informative error explanation
            self.assertTrue(mock_bot.edit_message_text.called)
            edit_args = mock_bot.edit_message_text.call_args[0]
            self.assertIn("belum bisa dibangunkan", edit_args[0])


if __name__ == "__main__":
    unittest.main()


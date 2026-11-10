import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from health_engine import HealthEngine
from pending_message_manager import PendingMessageManager
from idle_engine import IdleEngine


class TestFlappingAndRetryCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_llm.base_url = "http://127.0.0.1:5001/v1"
        self.mock_bot = MagicMock()
        self.health = HealthEngine(
            llm_client=self.mock_llm,
            enabled=True,
            self_healing_enabled=True,
            check_interval=10
        )
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pending = PendingMessageManager(storage_path=os.path.join(self.temp_dir.name, "pending.json"))

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_pending_message_circuit_breaker_drops_after_max_retries(self):
        """Messages that fail repeatedly are dropped after max_retries (2) instead of looping infinitely."""
        chat_id = 998877
        msg = MagicMock()
        msg.chat.id = chat_id
        msg.message_id = 101

        # Record failure 1
        self.pending.record_failed_message(msg, "Halo waifu", error="timeout 1")
        self.assertIn(chat_id, self.pending._pending)
        self.assertEqual(self.pending._chat_failure_history[chat_id]["retry_count"], 0)

        # Retry 1: pops and fails again
        mock_process = MagicMock(side_effect=RuntimeError("connection error 2"))
        self.pending._dispatch_retry(chat_id, self.mock_bot, mock_process)
        mock_process.assert_called_once()

        # Simulate bot recording failure 2 for the same text
        self.pending.record_failed_message(msg, "Halo waifu", error="timeout 2")
        self.assertEqual(self.pending._chat_failure_history[chat_id]["retry_count"], 1)

        # Retry 2: pops and fails again
        mock_process.reset_mock()
        self.pending._dispatch_retry(chat_id, self.mock_bot, mock_process)
        mock_process.assert_called_once()

        # Simulate bot recording failure 3 (reaches max_retries limit = 2)
        self.pending.record_failed_message(msg, "Halo waifu", error="timeout 3")
        # Circuit breaker triggered: message is removed from pending queue
        self.assertNotIn(chat_id, self.pending._pending)
        self.assertEqual(self.pending.get_pending_count(), 0)

    def test_pending_message_transition_ack_rate_limited(self):
        """User does not get spammed with 'Server LLM sudah kembali online' more than once per 300s."""
        chat_id = 112233
        msg = MagicMock()
        msg.chat.id = chat_id
        msg.message_id = 202

        self.pending.record_failed_message(msg, "Pesan 1", error="err")
        mock_process = MagicMock()

        self.mock_bot.reset_mock()
        self.pending._dispatch_retry(chat_id, self.mock_bot, mock_process)
        self.mock_bot.send_message.assert_called_once()
        self.assertIn("Server LLM sudah kembali online", self.mock_bot.send_message.call_args[0][1])

        # Enqueue another message and retry immediately within cooldown window
        self.pending.record_failed_message(msg, "Pesan 2", error="err")
        self.mock_bot.reset_mock()
        self.pending._dispatch_retry(chat_id, self.mock_bot, mock_process)

        # Telegram notification message should be suppressed by 300s cooldown
        self.mock_bot.send_message.assert_not_called()

    def test_mark_llm_failure_suppresses_when_endpoint_online(self):
        """mark_llm_failure does not trigger offline broadcast if check_health returns online."""
        self.health.last_llm_online = True
        self.mock_llm.check_health.return_value = {"online": True, "backend": "KoboldCPP"}
        self.health.mark_llm_failure(
            bot=self.mock_bot,
            get_recipients_func=lambda: [123],
            error_msg="Transient timeout"
        )
        self.assertTrue(self.health.last_llm_online)
        self.assertFalse(self.health.llm_offline_alert_sent)
        self.mock_bot.send_message.assert_not_called()

    def test_broadcast_failure_and_recovery_cooldown(self):
        """Failure and recovery broadcasts are rate-limited to avoid Telegram notification spam."""
        recipients = [555]
        err_stat = {"online": False, "error": "Crash"}
        ok_stat = {"online": True, "backend": "KoboldCPP", "model": "Stheno-8B"}

        # 1. First failure broadcast sends
        self.health.broadcast_failure(self.mock_bot, recipients, err_stat)
        self.mock_bot.send_message.assert_called_once()

        # Immediate second failure broadcast is suppressed by alert_cooldown_seconds
        self.mock_bot.reset_mock()
        self.health.broadcast_failure(self.mock_bot, recipients, err_stat)
        self.mock_bot.send_message.assert_not_called()

        # 2. First recovery broadcast sends
        self.health.broadcast_recovery(self.mock_bot, recipients, ok_stat)
        self.mock_bot.send_message.assert_called_once()

        # Immediate second recovery broadcast is suppressed
        self.mock_bot.reset_mock()
        self.health.broadcast_recovery(self.mock_bot, recipients, ok_stat)
        self.mock_bot.send_message.assert_not_called()

    def test_attempt_heal_service_limit_alert_sent_only_once(self):
        """When max self-heal attempts (3) are exhausted, limit notification is sent once, not spammed."""
        recipients = [777]
        now = time.time()
        self.health.heal_attempts["llm"] = [now, now, now]
        self.health.heal_limit_alert_sent["llm"] = False

        # Attempt 1 when exhausted -> sends limit alert
        self.health.attempt_heal_service("llm", self.mock_bot, recipients, is_manual=False)
        self.mock_bot.send_message.assert_called_once()
        self.assertTrue(self.health.heal_limit_alert_sent["llm"])

        # Attempt 2 (e.g. from watchdog 30s later) -> alert suppressed
        self.mock_bot.reset_mock()
        self.health.attempt_heal_service("llm", self.mock_bot, recipients, is_manual=False)
        self.mock_bot.send_message.assert_not_called()

    def test_split_mode_idle_engine_and_routing_fallback(self):
        """When split mode is active and KoboldCPP (5001) is offline, IdleEngine and RoutingEngine failover to SFW."""
        idle = IdleEngine(health_engine=self.health, enabled=True)

        with patch.dict(os.environ, {
            "AI_ENGINE_MODE": "split",
            "SFW_LLM_PROVIDER": "agy",
            "NSFW_LLM_PROVIDER": "local"
        }), patch("idle_engine.is_port_listening", side_effect=lambda p, timeout=1.0: p == 8001):

            # SFW check returns True (port 8001 is listening)
            self.assertTrue(idle.is_llm_ready(is_nsfw=False))

            # NSFW check returns False (port 5001 is offline)
            self.assertFalse(idle.is_llm_ready(is_nsfw=True))

            # ensure_llm_active for NSFW turn falls back gracefully to SFW
            with patch.object(idle, "wake_llm", return_value=False):
                ok = idle.ensure_llm_active(is_user_chat=True, is_nsfw=True)
                self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()

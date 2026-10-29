import os
import unittest
from unittest.mock import MagicMock, patch, call
from health_engine import HealthEngine, get_system_uptime, is_port_listening


class TestHealthEngine(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_llm.base_url = "http://127.0.0.1:5001/v1"
        self.mock_media = MagicMock()
        self.mock_bot = MagicMock()
        self.engine = HealthEngine(
            llm_client=self.mock_llm,
            media_engine=self.mock_media,
            check_interval=10,
            enabled=True,
            self_healing_enabled=True
        )

    def test_get_system_uptime_not_crash(self):
        uptime = get_system_uptime()
        if uptime is not None:
            self.assertIsInstance(uptime, float)
            self.assertGreaterEqual(uptime, 0)

    def test_startup_notification_llm_online(self):
        self.mock_llm.check_health.return_value = {
            "online": True,
            "backend": "KoboldCPP",
            "model": "Qwythos-9B"
        }
        self.mock_media.check_status.return_value = {
            "online": True,
            "backend": "ComfyUI Local"
        }

        with patch("health_engine.get_system_uptime", return_value=120.0):
            self.engine.notify_startup_ready(
                bot=self.mock_bot,
                recipients=[123456],
                persona={"name": "Runa"},
                max_wait_seconds=2
            )

        self.assertTrue(self.engine.startup_notified)
        self.assertTrue(self.engine.last_llm_online)
        self.assertFalse(self.engine.llm_offline_alert_sent)
        self.mock_bot.send_message.assert_called_once()
        sent_text = self.mock_bot.send_message.call_args[0][1]
        self.assertIn("PC Baru Saja Menyala", sent_text)
        self.assertIn("ONLINE", sent_text)
        self.assertIn("KoboldCPP", sent_text)

    def test_startup_notification_llm_offline(self):
        self.mock_llm.check_health.return_value = {
            "online": False,
            "error": "Connection refused on port 5001"
        }
        self.mock_media.check_status.return_value = {
            "online": False
        }

        with patch("health_engine.get_system_uptime", return_value=5000.0), patch.object(self.engine, "heal_llm", return_value=False):
            self.engine.notify_startup_ready(
                bot=self.mock_bot,
                recipients=[123456, 789012],
                persona={"name": "Akira"},
                max_wait_seconds=0
            )

        self.assertTrue(self.engine.startup_notified)
        self.assertFalse(self.engine.last_llm_online)
        self.assertTrue(self.engine.llm_offline_alert_sent)
        self.assertEqual(self.mock_bot.send_message.call_count, 2)
        sent_text = self.mock_bot.send_message.call_args_list[0][0][1]
        self.assertIn("Akira on Telegram Sudah Online", sent_text)
        self.assertIn("OFFLINE / MATI", sent_text)
        self.assertIn("PERHATIAN: Service LLM Belum Aktif", sent_text)

    def test_broadcast_failure_and_recovery_cycle(self):
        # 1. Failure broadcast
        stat_down = {"online": False, "error": "Server crashed unexpectedly"}
        self.engine.broadcast_failure(self.mock_bot, [999], stat_down)

        self.mock_bot.send_message.assert_called_once()
        fail_msg = self.mock_bot.send_message.call_args[0][1]
        self.assertIn("PERINGATAN: SERVICE LLM MATI", fail_msg)
        self.assertIn("Server crashed unexpectedly", fail_msg)

        # 2. Recovery broadcast
        self.mock_bot.reset_mock()
        stat_up = {"online": True, "backend": "KoboldCPP", "model": "Qwythos-9B"}
        self.engine.broadcast_recovery(self.mock_bot, [999], stat_up)

        self.mock_bot.send_message.assert_called_once()
        rec_msg = self.mock_bot.send_message.call_args[0][1]
        self.assertIn("SERVICE LLM TELAH PULIH KEMBALI", rec_msg)
        self.assertIn("KoboldCPP", rec_msg)
        self.assertIn("Qwythos-9B", rec_msg)

    def test_mark_llm_failure_triggers_alert_once(self):
        self.engine.self_healing_enabled = False
        self.engine.last_llm_online = True
        self.engine.llm_offline_alert_sent = False

        self.engine.mark_llm_failure(
            bot=self.mock_bot,
            get_recipients_func=lambda: [111],
            error_msg="Connection reset by peer"
        )

        self.assertTrue(self.engine.llm_offline_alert_sent)
        self.assertFalse(self.engine.last_llm_online)
        self.mock_bot.send_message.assert_called_once()

        # Second call should not spam another alert
        self.mock_bot.reset_mock()
        self.engine.mark_llm_failure(
            bot=self.mock_bot,
            get_recipients_func=lambda: [111],
            error_msg="Another failure"
        )
        self.mock_bot.send_message.assert_not_called()

    def test_status_summary_toggle(self):
        self.engine.enabled = True
        self.engine.last_llm_online = True
        self.assertIn("Aktif", self.engine.get_status_summary())
        self.assertIn("🟢", self.engine.get_status_summary())

        self.engine.last_llm_online = False
        self.assertIn("🔴", self.engine.get_status_summary())

        self.engine.enabled = False
        self.assertIn("Nonaktif", self.engine.get_status_summary())

    def test_can_attempt_heal_circuit_breaker(self):
        self.assertTrue(self.engine.can_attempt_heal("llm"))
        # Simulate 3 quick attempts
        import time
        now = time.time()
        self.engine.heal_attempts["llm"] = [now - 100, now - 50, now - 10]
        # Max 3 reached
        self.assertFalse(self.engine.can_attempt_heal("llm"))

        # Disabled healing
        self.engine.self_healing_enabled = False
        self.engine.heal_attempts["llm"] = []
        self.assertFalse(self.engine.can_attempt_heal("llm"))

    def test_attempt_heal_service_success(self):
        with patch.object(self.engine, "heal_llm", return_value=True):
            ok = self.engine.attempt_heal_service("llm", self.mock_bot, [777])
            self.assertTrue(ok)
            self.assertTrue(self.engine.last_llm_online)
            self.assertFalse(self.engine.llm_offline_alert_sent)
            # Check Telegram notices: 1 initiation, 1 success
            self.assertEqual(self.mock_bot.send_message.call_count, 2)
            init_msg = self.mock_bot.send_message.call_args_list[0][0][1]
            succ_msg = self.mock_bot.send_message.call_args_list[1][0][1]
            self.assertIn("Self-Healing Otomatis Aktif", init_msg)
            self.assertIn("Self-Healing Berhasil", succ_msg)

    def test_attempt_heal_service_failure(self):
        with patch.object(self.engine, "heal_llm", return_value=False):
            ok = self.engine.attempt_heal_service("llm", self.mock_bot, [777])
            self.assertFalse(ok)
            # Check Telegram notices: 1 initiation sent
            self.assertEqual(self.mock_bot.send_message.call_count, 1)

    def test_heal_comfyui_success(self):
        with patch("health_engine.is_port_listening", side_effect=[False, True]), \
             patch("subprocess.Popen") as mock_popen, \
             patch("asset_manager.get_comfyui_launch_spec", return_value={"cmd": ["python", "main.py"], "cwd": "."}):
            ok = self.engine.heal_comfyui()
            self.assertTrue(ok)
            mock_popen.assert_called_once()

    def test_heal_music_success(self):
        with patch("health_engine.is_port_listening", side_effect=[False, True]), \
             patch("os.path.exists", return_value=True), \
             patch("shutil.which", return_value="node"), \
             patch("subprocess.Popen") as mock_popen:
            ok = self.engine.heal_music()
            self.assertTrue(ok)
            mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import MagicMock, patch
import health_engine


class TestStartupSingletonGuard(unittest.TestCase):
    def test_get_koboldcpp_process_count_windows(self):
        with patch("sys.platform", "win32"):
            with patch("subprocess.check_output") as mock_check:
                mock_check.return_value = b'"koboldcpp.exe","1234"\r\n"koboldcpp.exe","5678"\r\n'
                count = health_engine.get_koboldcpp_process_count()
                self.assertEqual(count, 2)

    def test_kill_all_koboldcpp(self):
        with patch("sys.platform", "win32"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                health_engine.kill_all_koboldcpp()
                self.assertTrue(mock_run.called)

    def test_heal_llm_prevents_duplicate_if_already_running(self):
        mock_client = MagicMock()
        mock_client.check_health.return_value = {"online": True}
        mock_media = MagicMock()
        he = health_engine.HealthEngine(llm_client=mock_client, media_engine=mock_media)

        # If 1 process is already loading, heal_llm should wait and NOT spawn duplicate
        with patch("health_engine.get_koboldcpp_process_count", return_value=1):
            with patch("health_engine.is_port_listening", side_effect=[False, True, True, True]):
                with patch("subprocess.Popen") as mock_popen:
                    ok = he.heal_llm()
                    self.assertTrue(ok)
                    mock_popen.assert_not_called()

    def test_startup_ready_respects_smart_idle(self):
        mock_client = MagicMock()
        mock_client.check_health.return_value = {"online": False}
        mock_media = MagicMock()
        he = health_engine.HealthEngine(llm_client=mock_client, media_engine=mock_media)
        
        mock_idle = MagicMock()
        mock_idle.enabled = True
        he.idle_engine = mock_idle

        mock_bot = MagicMock()
        with patch.object(he, "heal_llm") as mock_heal:
            he.notify_startup_ready(mock_bot, [12345], {"name": "Runa"}, max_wait_seconds=0)
            mock_heal.assert_not_called()


if __name__ == "__main__":
    unittest.main()

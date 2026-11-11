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

    def test_heal_llm_terminates_multiple_duplicate_processes(self):
        """When 5 KoboldCpp instances are thrashing RAM, heal_llm terminates all duplicates."""
        mock_client = MagicMock()
        mock_client.check_health.return_value = {"online": True}
        he = health_engine.HealthEngine(llm_client=mock_client)

        with patch.dict(os.environ, {"AI_ENGINE_MODE": "unified", "SFW_LLM_PROVIDER": "local"}, clear=False), \
             patch("health_engine.is_port_listening", side_effect=[False, True]), \
             patch("health_engine.get_koboldcpp_process_count", return_value=5), \
             patch("health_engine.kill_all_koboldcpp") as mock_kill, \
             patch("subprocess.Popen") as mock_popen, \
             patch("asset_manager.get_llm_launch_spec", return_value={"cmd": ["koboldcpp.exe"], "cwd": "."}):
            ok = he.heal_llm()
            mock_kill.assert_called_once()
            self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()

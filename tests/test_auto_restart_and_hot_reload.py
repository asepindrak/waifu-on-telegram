import os
import time
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import setup
import bot


class TestAutoRestartAndHotReload(unittest.TestCase):
    def test_save_config_triggers_auto_restart_when_running(self):
        """Verifies save_config invokes restart_bot_if_running."""
        mock_env = {"VOICE_NAME": "ja-JP-NanamiNeural"}
        with patch("setup.write_env") as mock_write, \
             patch("setup.restart_bot_if_running", return_value=True) as mock_restart:
            setup.save_config(mock_env, auto_restart=True)
            mock_write.assert_called_once_with(mock_env)
            mock_restart.assert_called_once()

    def test_restart_bot_if_running_spawns_process(self):
        """Verifies restart_bot_if_running terminates old bot and spawns new detached bot."""
        with patch("setup.is_bot_running", return_value=9999), \
             patch("subprocess.run") as mock_run, \
             patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock(pid=10001)
            mock_popen.return_value = mock_proc

            res = setup.restart_bot_if_running()
            self.assertTrue(res)
            mock_run.assert_called()
            mock_popen.assert_called_once()

    def test_bot_hot_reloads_voice_from_env_file(self):
        """Verifies bot.reload_env_configurations updates in-memory voice without restart."""
        orig_voice = bot.voice_engine.default_voice
        orig_bot_voice = bot.VOICE_NAME
        orig_bot_lang = bot.BOT_LANGUAGE
        orig_env_lang = os.environ.get("BOT_LANGUAGE")
        orig_env_voice = os.environ.get("VOICE_NAME")

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".env") as f:
            f.write("VOICE_NAME=ja-JP-NanamiNeural\nBOT_LANGUAGE=ja\n")
            temp_env = f.name

        try:
            with patch("os.path.exists", return_value=True), \
                 patch("dotenv.dotenv_values", return_value={"VOICE_NAME": "ja-JP-NanamiNeural", "BOT_LANGUAGE": "ja"}):
                bot.reload_env_configurations()
                self.assertEqual(bot.VOICE_NAME, "ja-JP-NanamiNeural")
                self.assertEqual(bot.voice_engine.default_voice, "ja-JP-NanamiNeural")
                self.assertEqual(bot.BOT_LANGUAGE, "ja")
        finally:
            # Restore
            bot.VOICE_NAME = orig_bot_voice
            bot.voice_engine.default_voice = orig_voice
            bot.BOT_LANGUAGE = orig_bot_lang
            if orig_env_lang is None:
                os.environ.pop("BOT_LANGUAGE", None)
            else:
                os.environ["BOT_LANGUAGE"] = orig_env_lang
            if orig_env_voice is None:
                os.environ.pop("VOICE_NAME", None)
            else:
                os.environ["VOICE_NAME"] = orig_env_voice
            if os.path.exists(temp_env):
                try:
                    os.remove(temp_env)
                except Exception:
                    pass

    def test_cli_update_triggers_auto_restart_when_bot_running(self):
        """Verifies waifu update automatically restarts running bot."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))
        import cli
        with patch("cli.get_running_pid", return_value=12345), \
             patch("cli.cmd_restart") as mock_restart, \
             patch("cli.asset_manager", None), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            cli.cmd_update()
            mock_restart.assert_called_once_with(daemon=True)


if __name__ == "__main__":
    unittest.main()

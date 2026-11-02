import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import bot


class TestScheduledGreetingBehavior(unittest.TestCase):
    @patch("bot.bot")
    @patch("bot.scheduled_buffer")
    @patch("bot.idle_engine")
    @patch("bot.is_port_listening", return_value=False)
    def test_send_scheduled_greeting_uses_buffer_first(self, mock_port, mock_idle, mock_buf, mock_bot):
        mock_idle.is_llm_sleeping = True
        mock_buf.get_message.return_value = "Pagi sayang! Semangat hari ini yaa~"

        bot.send_scheduled_greeting(12345, "morning")

        # Must have sent the buffered message
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        self.assertIn("Pagi sayang! Semangat hari ini yaa~", args[1])
        # Idle engine wake MUST NOT be called
        mock_idle.ensure_llm_active.assert_not_called()

    @patch("bot.bot")
    @patch("bot.scheduled_buffer")
    @patch("bot.idle_engine")
    @patch("bot.is_port_listening", return_value=False)
    def test_send_scheduled_greeting_uses_fallback_when_empty_and_sleeping(self, mock_port, mock_idle, mock_buf, mock_bot):
        """When buffer is empty and LLM is sleeping, greeting sends fallback text and never wakes LLM."""
        mock_idle.is_llm_sleeping = True
        mock_buf.get_message.return_value = None

        bot.send_scheduled_greeting(12345, "lunch")

        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        self.assertIn("makan siang", args[1].lower())
        mock_idle.ensure_llm_active.assert_not_called()


if __name__ == "__main__":
    unittest.main()

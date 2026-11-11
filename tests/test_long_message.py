import unittest
from unittest.mock import MagicMock, patch
import bot

class TestLongChatMessage(unittest.TestCase):

    @patch.object(bot.bot, "send_message")
    def test_send_short_message(self, mock_send):
        mock_send.return_value = MagicMock(message_id=123)
        res = bot.send_long_chat_message(chat_id=12345, text="Short reply text")
        self.assertEqual(len(res), 1)
        mock_send.assert_called_once()

    @patch.object(bot.bot, "send_message")
    def test_send_long_message_splits_chunks(self, mock_send):
        mock_send.return_value = MagicMock(message_id=456)
        # Create a text that exceeds max_chunk_size
        long_text = "Line of text\n" * 400
        mock_markup = MagicMock()
        res = bot.send_long_chat_message(chat_id=12345, text=long_text, max_chunk_size=1000, reply_markup=mock_markup)
        self.assertGreater(len(res), 1)
        self.assertGreater(mock_send.call_count, 1)
        # Verify reply_markup was passed to the last chunk
        last_call_kwargs = mock_send.call_args_list[-1][1]
        self.assertEqual(last_call_kwargs.get("reply_markup"), mock_markup)

    @patch.object(bot.bot, "send_message")
    def test_localhost_converted_to_127(self, mock_send):
        mock_send.return_value = MagicMock(message_id=789)
        bot.send_long_chat_message(chat_id=12345, text="Akses: http://localhost:8086/ dan http://localhost:3000")
        call_text = mock_send.call_args[0][1]
        self.assertIn("http://127.0.0.1:8086/", call_text)
        self.assertIn("http://127.0.0.1:3000", call_text)
        self.assertNotIn("localhost", call_text)

    @patch.object(bot.bot, "send_message")
    def test_strip_private_url_buttons_on_telegram_url_error(self, mock_send):
        from telebot import types
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("💻 Localhost:8086", url="http://127.0.0.1:8086/"),
            types.InlineKeyboardButton("📱 Tailscale:8086", url="http://100.64.1.2:8086/")
        )
        markup.row(types.InlineKeyboardButton("🔊 Dengarkan Suara", callback_data="play_voice:abc123"))

        mock_ok = MagicMock(message_id=999)
        mock_send.side_effect = [Exception("Bad Request: BUTTON_URL_INVALID"), mock_ok]

        res = bot.send_long_chat_message(chat_id=12345, text="Web preview ready", reply_markup=markup)
        self.assertEqual(res, [mock_ok])
        fallback_markup = mock_send.call_args_list[1][1]["reply_markup"]
        remaining_cbs = [btn.callback_data for row in fallback_markup.keyboard for btn in row]
        self.assertEqual(remaining_cbs, ["play_voice:abc123"])


if __name__ == "__main__":
    unittest.main()


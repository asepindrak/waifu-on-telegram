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
        res = bot.send_long_chat_message(chat_id=12345, text=long_text, max_chunk_size=1000)
        self.assertGreater(len(res), 1)
        self.assertGreater(mock_send.call_count, 1)

if __name__ == "__main__":
    unittest.main()

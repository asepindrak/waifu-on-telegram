import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import bot

class TestBotMenusAndResilience(unittest.TestCase):
    def test_bot_worker_pool_threads(self):
        """Ensures worker pool has enough threads to avoid starvation."""
        self.assertGreaterEqual(bot.bot.worker_pool.num_threads, 8)

    def test_send_menu_message_success(self):
        with patch.object(bot.bot, 'send_message', return_value=MagicMock(message_id=101)) as mock_send:
            res = bot.send_menu_message(12345, "Test Menu", reply_markup=None, reply_to_id=99)
            self.assertIsNotNone(res)
            mock_send.assert_called_once_with(12345, "Test Menu", reply_markup=None, parse_mode="Markdown", reply_to_message_id=99)

    def test_send_menu_message_fallback_on_bad_reply_and_parse(self):
        # Simulate: first call fails (bad reply id), second call fails (entity error), third call succeeds
        mock_result = MagicMock(message_id=102)
        call_count = 0
        def fake_send(chat_id, text, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("message to be replied not found")
            elif call_count == 2:
                raise Exception("can't parse entities")
            return mock_result

        with patch.object(bot.bot, 'send_message', side_effect=fake_send):
            res = bot.send_menu_message(12345, "Test **Broken** _Menu_", reply_markup=None, reply_to_id=99)
            self.assertEqual(res, mock_result)
            self.assertEqual(call_count, 3)

    def test_handle_text_messages_fallback_outfit(self):
        msg = MagicMock()
        msg.from_user.id = 6402709138
        msg.chat.id = 6402709138
        msg.text = "  /outfit@YunaAoiBot  "
        msg.message_id = 555

        with patch.object(bot, 'show_outfit_menu') as mock_outfit:
            bot.handle_text_messages(msg)
            mock_outfit.assert_called_once_with(6402709138, 6402709138, reply_to_id=555)

    def test_handle_text_messages_fallback_persona(self):
        msg = MagicMock()
        msg.from_user.id = 6402709138
        msg.chat.id = 6402709138
        msg.text = " /persona "
        msg.message_id = 556

        with patch.object(bot, 'show_persona_menu') as mock_persona:
            bot.handle_text_messages(msg)
            mock_persona.assert_called_once_with(6402709138, 6402709138, reply_to_id=556)

if __name__ == '__main__':
    unittest.main()

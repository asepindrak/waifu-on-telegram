import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import bot

class TestBotHandlerRouting(unittest.TestCase):
    def test_regular_chat_routed_to_handle_text_messages(self):
        """Ensures ordinary conversation messages do NOT trigger projects menu."""
        msg = MagicMock()
        msg.from_user.id = 6402709138
        msg.chat.id = 6402709138
        msg.text = "Halo sayang, lagi apa nih?"
        msg.message_id = 1234
        msg.content_type = "text"

        with patch.object(bot, 'show_projects_menu') as mock_proj, \
             patch.object(bot, 'process_text_chat') as mock_process:
            bot.handle_text_messages(msg)
            mock_proj.assert_not_called()
            mock_process.assert_called_once()

    def test_projects_command_routes_to_projects_menu(self):
        """Ensures /projects command properly opens projects menu."""
        msg = MagicMock()
        msg.from_user.id = 6402709138
        msg.chat.id = 6402709138
        msg.text = "/projects"
        msg.message_id = 1235
        msg.content_type = "text"

        with patch.object(bot, 'show_projects_menu') as mock_proj:
            bot.handle_projects_command(msg)
            mock_proj.assert_called_once_with(6402709138, 6402709138, reply_to_id=1235)

    def test_handler_registration_for_text(self):
        """Verifies bot.message_handlers has correct filters."""
        # Find handler for handle_projects_command vs handle_text_messages
        proj_handler = None
        text_handler = None
        for h in bot.bot.message_handlers:
            func = h.get('function')
            if func == bot.handle_projects_command:
                proj_handler = h
            elif func == bot.handle_text_messages:
                text_handler = h

        self.assertIsNotNone(proj_handler)
        self.assertIsNotNone(text_handler)

        # Ensure handle_projects_command is ONLY triggered by commands, NOT func=lambda msg: True
        filters = proj_handler.get('filters', {})
        self.assertIn('commands', filters)
        self.assertNotIn('func', filters)

if __name__ == "__main__":
    unittest.main()

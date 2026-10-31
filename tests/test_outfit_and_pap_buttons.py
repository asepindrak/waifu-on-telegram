import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "99999"

import bot
from telebot import types


class TestOutfitAndPapButtons(unittest.TestCase):
    def setUp(self):
        self.mock_call = MagicMock()
        self.mock_call.id = "call_test_123"
        self.mock_call.from_user.id = 99999
        self.mock_call.message.chat.id = 12345
        self.mock_call.message.message_id = 777
        self.mock_call.message.text = "Pilih skenario foto"
        self.patch_answer = patch.object(bot.bot, "answer_callback_query")
        self.patch_chat_action = patch.object(bot.bot, "send_chat_action")
        self.mock_answer = self.patch_answer.start()
        self.mock_chat_action = self.patch_chat_action.start()

    def tearDown(self):
        self.patch_answer.stop()
        self.patch_chat_action.stop()

    @patch("bot.is_authorized", return_value=True)
    @patch("bot.persona_mgr")
    def test_callback_set_outfit_shows_pap_button(self, mock_persona_mgr, mock_auth):
        """Selecting an outfit saves the choice and offers instant 'Minta PAP Sekarang' button."""
        mock_persona_mgr.set_user_outfit.return_value = True
        mock_persona_mgr.get_user_outfit.return_value = ("beach", "Summer Bikini")
        self.mock_call.data = "set_outfit:bikini"

        with patch("bot.bot.edit_message_text") as mock_edit:
            bot.callback_set_outfit(self.mock_call)
            self.assertTrue(mock_edit.called)
            kwargs = mock_edit.call_args[1]
            markup = kwargs.get("reply_markup")
            self.assertIsNotNone(markup)
            btn_datas = [btn.callback_data for row in markup.keyboard for btn in row]
            self.assertIn("open_pap_menu", btn_datas)

    @patch("bot.is_authorized", return_value=True)
    def test_open_pap_menu_renders_scenario_buttons(self, mock_auth):
        """Clicking 'open_pap_menu' renders scenario options including 'beach' (Liburan di Pantai)."""
        self.mock_call.data = "open_pap_menu"
        with patch("bot.show_pap_scenario_menu") as mock_menu:
            bot.callback_quick_actions(self.mock_call)
            mock_menu.assert_called_once_with(12345, 99999, message_to_edit=777)

    @patch("bot.is_authorized", return_value=True)
    @patch("bot.process_photo_request")
    def test_callback_pap_scenario_beach_triggers_photo_request(self, mock_proc, mock_auth):
        """Clicking 'pap_sc:beach' immediately answers callback and triggers process_photo_request."""
        self.mock_call.data = "pap_sc:beach"
        bot.callback_pap_scenario(self.mock_call)
        self.assertTrue(mock_proc.called)
        target, prompt = mock_proc.call_args[0]
        self.assertEqual(target, self.mock_call)
        self.assertIn("beach", prompt.lower())

    @patch("bot.is_authorized", return_value=True)
    @patch("bot.media_engine")
    @patch("bot.bot.edit_message_text")
    def test_process_photo_request_updates_menu_message_instantly(self, mock_bot_edit, mock_media, mock_auth):
        """process_photo_request replaces the menu message with loading status without blocking."""
        self.mock_call.data = "pap_sc:beach"
        mock_media.generate_photo.return_value = (None, "Failed")

        # Run process_photo_request
        bot.process_photo_request(self.mock_call, "beach vacation")
        import time
        for _ in range(20):
            if mock_bot_edit.called:
                break
            time.sleep(0.05)

        self.assertTrue(mock_bot_edit.called)


if __name__ == "__main__":
    unittest.main()

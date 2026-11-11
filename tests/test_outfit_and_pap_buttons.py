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
        self.patch_answer = patch.object(bot.telebot.TeleBot, "answer_callback_query")
        self.patch_chat_action = patch.object(bot.telebot.TeleBot, "send_chat_action")
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
    @patch("bot.idle_engine")
    @patch("bot.media_engine")
    @patch("bot.safe_edit_message_text")
    def test_process_photo_request_updates_menu_message_instantly(self, mock_safe_edit, mock_media, mock_idle, mock_auth):
        """process_photo_request replaces the menu message with loading status without blocking."""
        self.mock_call.data = "pap_sc:beach"
        mock_media.generate_photo.return_value = (None, "Failed")
        mock_idle.ensure_comfyui_active.return_value = True

        # Run process_photo_request
        bot.process_photo_request(self.mock_call, "beach vacation")
        import time
        for _ in range(30):
            if mock_safe_edit.called and mock_media.generate_photo.called:
                break
            time.sleep(0.05)
        time.sleep(0.1)

        self.assertTrue(mock_safe_edit.called)

    def test_manual_outfit_from_menu_overrides_chat_history_pajamas(self):
        """Selecting an outfit via /outfit (session or locked) must NOT be overridden by stale 'piyama'/'tidur' chat history or reply hallucinations."""
        from persona_manager import PersonaManager
        pm = PersonaManager(active_key="hina")
        uid = 884422
        pm.set_user_outfit(uid, "default")

        pajama_history = [
            {"role": "assistant", "content": "Aku lagi ngantuk dan rebahan pakai piyama tidur nih."},
            {"role": "user", "content": "Piyamanya lucu banget, mau tidur ya?"},
        ]

        # Simulate picking bikini from /outfit (manual session mode, not even locked)
        pm.set_user_outfit(uid, "bikini", source="manual")

        # 1. Generic PAP request still uses Summer Bikini, NOT stale pajamas
        prompt, neg, is_nude, label = pm.craft_visual_prompt_full(
            "coba pap dong", user_id=uid, history=pajama_history
        )
        self.assertIn("bikini", prompt.lower())
        self.assertNotIn("camisole", prompt.lower())
        self.assertIn("Summer Bikini", label)
        self.assertFalse(is_nude)

        # 2. Clicking 'Pose Romantis' (/pap scenario 'sensual') preserves chosen /outfit instead of overriding with slip dress
        sensual_prompt = bot.SCENARIO_PROMPTS["sensual"]
        prompt2, _, _, label2 = pm.craft_visual_prompt_full(
            sensual_prompt, user_id=uid, history=pajama_history
        )
        self.assertIn("bikini", prompt2.lower())
        self.assertNotIn("slip dress", prompt2.lower())
        self.assertIn("Summer Bikini", label2)

        # 3. LLM reply hallucinating 'piyama' does NOT overwrite manual /outfit selection via sync_outfit_from_chat
        synced = pm.sync_outfit_from_chat(
            uid,
            user_text="pap dong",
            reply_text="Bentar ya, aku lagi rebahan pakai piyama tidur nih.",
        )
        self.assertIsNone(synced)
        cur_key, _ = pm.get_user_outfit(uid)
        self.assertEqual(cur_key, "bikini")

        # 4. Locked /outfit stays active even if user_text mentions pajamas in chat
        pm.set_user_outfit(uid, "school_jk", is_locked=True, source="manual")
        prompt3, _, _, label3 = pm.craft_visual_prompt_full(
            "tadi kamu pake piyama lucu", user_id=uid, history=pajama_history
        )
        self.assertIn("school uniform", prompt3.lower())
        self.assertIn("School JK", label3)

        # Clean up test state
        pm.set_user_outfit(uid, "default")

    @patch("bot.is_authorized", return_value=True)
    @patch("bot.safe_send_message")
    @patch("bot.llm_client")
    @patch("bot.media_engine")
    @patch("bot.idle_engine")
    def test_callback_set_outfit_then_pap_uses_chosen_outfit_even_if_reply_mentions_pajamas(
        self, mock_idle, mock_media, mock_llm, mock_safe_send, mock_auth
    ):
        """End-to-end /outfit click -> photo request renders selected outfit even if reply text still says 'piyama'."""
        uid = 99999
        orig_mgr_rec = bot.persona_mgr.user_outfits.get(uid)
        try:
            self.mock_call.data = "set_outfit:bikini"
            with patch("bot.bot.edit_message_text"):
                bot.callback_set_outfit(self.mock_call)

            details = bot.persona_mgr.get_user_outfit_details(uid)
            self.assertEqual(details["key"], "bikini")
            self.assertEqual(details["source"], "manual")

            mock_idle.ensure_comfyui_active.return_value = True
            mock_media.generate_photo.return_value = (b"fake_img", "ComfyUI")
            mock_llm.chat.return_value = ("Nih foto aku pakai bikini di kamar~", "")

            mock_msg = MagicMock()
            mock_msg.chat.id = 12345
            mock_msg.from_user.id = uid

            with patch.object(
                bot.persona_mgr,
                "get_chat_history",
                return_value=[{"role": "assistant", "content": "Aku lagi pakai piyama tidur nih"}],
            ):
                bot.process_photo_request(
                    mock_msg,
                    user_text="Aku lagi santai pakai piyama nih, bentar aku pap ya!",
                    conversational_reply="Aku lagi santai pakai piyama nih, bentar aku pap ya!",
                    is_followup=True,
                    original_user_text="pap dong",
                )
                import time
                for _ in range(40):
                    if mock_media.generate_photo.called:
                        break
                    time.sleep(0.05)

            self.assertTrue(mock_media.generate_photo.called)
            visual_prompt = mock_media.generate_photo.call_args[0][0]
            used_outfit = mock_media.generate_photo.call_args[1].get("outfit_label", "")
            self.assertIn("bikini", visual_prompt.lower())
            self.assertNotIn("camisole", visual_prompt.lower())
            self.assertIn("Summer Bikini", used_outfit)
        finally:
            bot.persona_mgr.set_user_outfit(uid, "default")
            if orig_mgr_rec is not None:
                bot.persona_mgr.user_outfits[uid] = orig_mgr_rec


if __name__ == "__main__":
    unittest.main()

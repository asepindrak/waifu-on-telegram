import os
import unittest
from unittest.mock import MagicMock, patch

class TestMistralNemoModelIntegration(unittest.TestCase):
    def test_asset_registry_contains_mistral_nemo(self):
        import asset_manager
        self.assertIn("mistral_nemo_12b", asset_manager.ASSET_REGISTRY)
        asset = asset_manager.ASSET_REGISTRY["mistral_nemo_12b"]
        self.assertEqual(asset["filename"], "Mistral-Nemo-12B-Instruct-v0.4.Q4_K_M.gguf")
        self.assertIn("url", asset)
        self.assertIn("patterns", asset)
        self.assertTrue(any("nemo" in p.lower() for p in asset["patterns"]))

    def test_apply_llm_choice_mistral_nemo(self):
        import bot
        with patch("bot.update_env_variable") as mock_update:
            label = bot.apply_llm_choice("mistral_nemo")
            self.assertIn("Mistral-NeMo-12B", label)
            mock_update.assert_any_call("LOCAL_LLM_MODEL", "Mistral-Nemo-12B-Instruct-v0.4.Q4_K_M.gguf")
            mock_update.assert_any_call("NSFW_LLM_MODEL", "Mistral-Nemo-12B-Instruct-v0.4.Q4_K_M.gguf")
            mock_update.assert_any_call("LLM_MODEL", "Mistral-Nemo-12B-Instruct-v0.4.Q4_K_M.gguf")

    def test_show_llm_menu_includes_mistral_nemo_download_button(self):
        import bot
        with patch("bot.scan_local_llm_models", return_value=[]), \
             patch("bot.bot.send_message") as mock_send:
            bot.show_llm_menu(chat_id=12345, user_id=12345)
            mock_send.assert_called_once()
            markup = mock_send.call_args[1].get("reply_markup")
            self.assertIsNotNone(markup)
            
            button_texts = [btn.text for row in markup.keyboard for btn in row]
            button_datas = [btn.callback_data for row in markup.keyboard for btn in row]
            
            self.assertTrue(any("Mistral-NeMo 12B" in text for text in button_texts))
            self.assertIn("cfg_set_llm:mistral_nemo_auto", button_datas)

    def test_callback_auto_downloads_and_activates_mistral_nemo(self):
        import bot
        mock_call = MagicMock()
        mock_call.id = "cb_123"
        mock_call.data = "cfg_set_llm:mistral_nemo_auto"
        mock_call.from_user.id = 999
        mock_call.message.chat.id = 999
        mock_call.message.message_id = 456

        with patch("bot.is_authorized", return_value=True), \
             patch("bot.bot.answer_callback_query"), \
             patch("bot.bot.send_message"), \
             patch("bot.asset_manager.get_asset_info", return_value={"installed": False}), \
             patch("bot.asset_manager.download_asset", return_value=True) as mock_dl, \
             patch("bot.apply_llm_choice") as mock_apply, \
             patch("bot.health_engine.heal_llm"):
            bot.callback_set_llm(mock_call)
            mock_dl.assert_called_with("mistral_nemo_12b")

if __name__ == '__main__':
    unittest.main()

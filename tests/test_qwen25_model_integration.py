"""Unit tests for Qwen2.5-7B-Instruct-Abliterated integration."""
import unittest
from unittest.mock import patch, MagicMock
import os


class TestQwen25ModelIntegration(unittest.TestCase):
    def test_qwen25_in_asset_registry(self):
        import asset_manager
        self.assertIn("qwen25_7b", asset_manager.ASSET_REGISTRY)
        info = asset_manager.ASSET_REGISTRY["qwen25_7b"]
        self.assertEqual(info["type"], "llm_model")
        self.assertTrue(info["url"].startswith("https://"))
        self.assertIn(".Q4_K_M.gguf", info["filename"])
        self.assertGreater(len(info["mirrors"]), 1)

    def test_apply_llm_choice_qwen25(self):
        import bot
        with patch("bot.update_env_variable") as mock_update:
            label = bot.apply_llm_choice("qwen25_7b")
            self.assertIn("Qwen2.5-7B-Instruct-Abliterated", label)
            mock_update.assert_any_call("LOCAL_LLM_MODEL", "Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf")
            mock_update.assert_any_call("NSFW_LLM_MODEL", "Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf")
            mock_update.assert_any_call("LLM_MODEL", "Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf")

    def test_show_llm_menu_includes_qwen_download_button(self):
        import bot
        with patch("bot.scan_local_llm_models", return_value=[]), \
             patch("bot.bot.send_message") as mock_send:
            bot.show_llm_menu(chat_id=12345, user_id=12345)
            mock_send.assert_called_once()
            markup = mock_send.call_args[1].get("reply_markup")
            self.assertIsNotNone(markup)
            
            button_texts = [btn.text for row in markup.keyboard for btn in row]
            button_datas = [btn.callback_data for row in markup.keyboard for btn in row]
            
            self.assertTrue(any("Qwen2.5-7B" in text for text in button_texts))
            self.assertIn("cfg_set_llm:qwen_auto", button_datas)

    def test_callback_auto_downloads_and_activates_qwen(self):
        import bot
        mock_call = MagicMock()
        mock_call.id = "cb_123"
        mock_call.data = "cfg_set_llm:qwen_auto"
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
            mock_dl.assert_called_with("qwen25_7b")


if __name__ == "__main__":
    unittest.main()

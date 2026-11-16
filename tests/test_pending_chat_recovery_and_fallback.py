import unittest
from unittest.mock import MagicMock, patch
import os
import json
import time

from pending_message_manager import PendingMessageManager
from routing_engine import HybridLLMClient
from lu_llm_client import LocallyUncensoredClient


class TestPendingChatRecoveryAndFallback(unittest.TestCase):
    def setUp(self):
        self.mgr = PendingMessageManager(storage_path="data/test_pending_chats.json")
        self.mgr._pending.clear()
        self.mgr._chat_failure_history.clear()
        self.mgr._retrying_chats.clear()

    def tearDown(self):
        if os.path.exists("data/test_pending_chats.json"):
            try:
                os.remove("data/test_pending_chats.json")
            except Exception:
                pass

    def test_is_chat_already_replied_true(self):
        """Should detect if a message was already replied to by assistant."""
        user_id = 12345
        user_text = "Halo sayang apa kabar?"
        mock_history = [
            {"role": "user", "content": "Halo sayang apa kabar?"},
            {"role": "assistant", "content": "Halo manis! Aku baik-baik aja kok~"}
        ]
        mock_pm = MagicMock()
        mock_pm.get_chat_history.return_value = mock_history
        replied = self.mgr.is_chat_already_replied(user_id, user_text, persona_mgr=mock_pm)
        self.assertTrue(replied)

    def test_is_chat_already_replied_false_when_unanswered(self):
        """Should detect when a message is pending without assistant reply."""
        user_id = 12345
        user_text = "Kamu lagi ngapain?"
        mock_history = [
            {"role": "user", "content": "Halo kemarin"},
            {"role": "assistant", "content": "Halo!"},
            {"role": "user", "content": "Kamu lagi ngapain?"}
        ]
        mock_pm = MagicMock()
        mock_pm.get_chat_history.return_value = mock_history
        replied = self.mgr.is_chat_already_replied(user_id, user_text, persona_mgr=mock_pm)
        self.assertFalse(replied)

    def test_routing_engine_detects_empty_reply_and_falls_back(self):
        """Routing engine should fall back to SFW when local engine returns empty reply."""
        mock_sfw = MagicMock()
        mock_sfw.chat.return_value = ("Balasan SFW fallback", "")
        mock_nsfw = MagicMock()
        mock_nsfw.chat.return_value = ("", "some thoughts")

        with patch.dict(os.environ, {
            "AI_ENGINE_MODE": "split",
            "SFW_LLM_PROVIDER": "agy",
            "NSFW_LLM_PROVIDER": "local"
        }):
            client = HybridLLMClient()
            client.sfw_client = mock_sfw
            client.nsfw_client = mock_nsfw

            with patch("routing_engine.is_ai_refusal", return_value=False):
                with patch("idle_engine.is_port_listening", return_value=True):
                    res, reasoning = client.chat([{"role": "user", "content": "halo"}], is_nsfw=True)
                    self.assertEqual(res, "Balasan SFW fallback")
                    mock_sfw.chat.assert_called_once()

    def test_hybrid_client_falls_back_to_sfw_on_nsfw_error(self):
        """HybridLLMClient should fall back to SFW when NSFW local client fails."""
        mock_sfw = MagicMock()
        mock_sfw.chat.return_value = ("Balasan dari SFW engine", "")
        mock_nsfw = MagicMock()
        mock_nsfw.chat.side_effect = RuntimeError("Server LLM lokal tidak menghasilkan balasan")

        with patch.dict(os.environ, {
            "AI_ENGINE_MODE": "split",
            "SFW_LLM_PROVIDER": "agy",
            "NSFW_LLM_PROVIDER": "local"
        }):
            client = HybridLLMClient()
            client.sfw_client = mock_sfw
            client.nsfw_client = mock_nsfw

            with patch("routing_engine.is_ai_refusal", return_value=False):
                with patch("idle_engine.is_port_listening", return_value=True):
                    res, reasoning = client.chat([{"role": "user", "content": "hello"}], is_nsfw=True)
                    self.assertEqual(res, "Balasan dari SFW engine")
                    mock_sfw.chat.assert_called_once()

    def test_hybrid_client_falls_back_to_sfw_on_empty_reply(self):
        """HybridLLMClient should fall back to SFW when NSFW returns empty string."""
        mock_sfw = MagicMock()
        mock_sfw.chat.return_value = ("SFW response fallback", "")
        mock_nsfw = MagicMock()
        mock_nsfw.chat.return_value = ("", "")

        with patch.dict(os.environ, {
            "AI_ENGINE_MODE": "split",
            "SFW_LLM_PROVIDER": "agy",
            "NSFW_LLM_PROVIDER": "local"
        }):
            client = HybridLLMClient()
            client.sfw_client = mock_sfw
            client.nsfw_client = mock_nsfw

            with patch("routing_engine.is_ai_refusal", return_value=False):
                with patch("idle_engine.is_port_listening", return_value=True):
                    res, reasoning = client.chat([{"role": "user", "content": "halo"}], is_nsfw=True)
                    self.assertEqual(res, "SFW response fallback")
                    mock_sfw.chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()

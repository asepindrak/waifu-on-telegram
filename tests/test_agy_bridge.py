"""
tests/test_agy_bridge.py - Unit tests for Google Antigravity CLI (agy) Bridge
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import agy_bridge
from routing_engine import PROVIDER_PRESETS, get_hybrid_llm_client


class TestAGYBridge(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(agy_bridge.app)

    def test_health_check_endpoint(self):
        """Test that /health returns correct bridge status information."""
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="agy version 1.4.12")
            res = self.client.get("/health")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["service"], "AGY OpenAI Bridge")
            self.assertEqual(data["status"], "online")
            self.assertTrue(data["agy_installed"])
            self.assertIn("1.4.12", data["agy_version"])

    def test_models_endpoint(self):
        """Test that /v1/models exposes standard Antigravity models."""
        res = self.client.get("/v1/models")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["object"], "list")
        model_ids = [m["id"] for m in data["data"]]
        self.assertIn("flash", model_ids)
        self.assertIn("pro", model_ids)
        self.assertIn("inherit", model_ids)

    def test_process_message_content_string_and_multimodal(self):
        """Test text extraction and data URI processing in message payloads."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Plain text
            txt = agy_bridge.process_message_content("Halo waifu!", tmp_dir)
            self.assertEqual(txt, "Halo waifu!")

            # 2. Multimodal list with text and base64 image
            fake_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            payload = [
                {"type": "text", "text": "Lihat fotoku ini:"},
                {"type": "image_url", "image_url": {"url": fake_b64}}
            ]
            processed = agy_bridge.process_message_content(payload, tmp_dir)
            self.assertIn("Lihat fotoku ini:", processed)
            self.assertIn("[Attached Image:", processed)

    @patch("agy_bridge.run_agy_cli")
    def test_chat_completions_non_streaming(self, mock_run):
        """Test /v1/chat/completions non-streaming response."""
        mock_run.return_value = "Halo juga! Senang bertemu denganmu."

        req_body = {
            "model": "flash",
            "messages": [
                {"role": "user", "content": "Halo apa kabar?"}
            ],
            "stream": False
        }
        res = self.client.post("/v1/chat/completions", json=req_body, headers={"Authorization": "Bearer sk-agy-waifu"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["object"], "chat.completion")
        self.assertEqual(data["choices"][0]["message"]["content"], "Halo juga! Senang bertemu denganmu.")
        self.assertEqual(data["model"], "flash")
        self.assertIn("usage", data)

    @patch("agy_bridge.run_agy_cli")
    def test_chat_completions_streaming(self, mock_run):
        """Test /v1/chat/completions streaming response chunks."""
        mock_run.return_value = "Ini adalah balasan streaming."

        req_body = {
            "model": "pro",
            "messages": [
                {"role": "user", "content": "Bisa jelaskan?"}
            ],
            "stream": True
        }
        res = self.client.post("/v1/chat/completions", json=req_body)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers.get("content-type", ""))
        self.assertIn("chat.completion.chunk", res.text)
        self.assertIn("[DONE]", res.text)

    def test_routing_engine_agy_preset(self):
        """Test that routing_engine recognizes agy preset."""
        self.assertIn("agy", PROVIDER_PRESETS)
        preset = PROVIDER_PRESETS["agy"]
        self.assertEqual(preset["base_url"], "http://127.0.0.1:8001/v1")
        self.assertEqual(preset["default_model"], "flash")

        # Test creating client with agy preset via environment patch
        env_patch = {
            "AI_ENGINE_MODE": "split",
            "SFW_LLM_PROVIDER": "agy",
            "SFW_LLM_BASE_URL": "http://127.0.0.1:8001/v1",
            "SFW_LLM_MODEL": "flash",
            "NSFW_LLM_PROVIDER": "local",
            "NSFW_LLM_BASE_URL": "http://127.0.0.1:5001/v1",
            "NSFW_LLM_MODEL": "default"
        }
        with patch.dict(os.environ, env_patch):
            client = get_hybrid_llm_client(force_reload=True)
            self.assertIsNotNone(client)
            self.assertEqual(client.sfw_client.base_url, "http://127.0.0.1:8001/v1")
            self.assertEqual(client.sfw_client.model, "flash")


if __name__ == "__main__":
    unittest.main()

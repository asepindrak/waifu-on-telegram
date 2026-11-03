"""
tests/test_agy_bridge.py - Unit tests for Google Antigravity CLI (agy) Bridge & Image Generator
"""

import os
import tempfile
import base64
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import agy_bridge
from routing_engine import PROVIDER_PRESETS, get_hybrid_llm_client
from media_engine import MediaEngine


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

    def test_extract_image_path_from_agy_output(self):
        """Test extracting image path from AGY image-generator subagent output."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"FAKE_IMAGE_DATA_12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890")
            tmp_path = f.name

        try:
            sample_output = f"""
I have launched the image generator subagent to create the cute anime cat image for you.
Here is your cute anime cat image!

![Cute Anime Cat](file:///{tmp_path.replace(os.sep, '/')})

- **File Path**: [{os.path.basename(tmp_path)}](file:///{tmp_path.replace(os.sep, '/')})
"""
            extracted = agy_bridge.extract_image_path_from_agy_output(sample_output)
            self.assertIsNotNone(extracted)
            self.assertEqual(os.path.abspath(extracted).lower(), os.path.abspath(tmp_path).lower())
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("agy_bridge.run_agy_image_gen")
    def test_image_generations_endpoint(self, mock_gen):
        """Test /v1/images/generations endpoint for both b64_json and url formats."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"PNG_FAKE_IMAGE_BYTES_LONGER_THAN_100_CHARACTERS_FOR_VALIDATION_PURPOSES_123456789012345678901234567890")
            tmp_path = f.name

        try:
            mock_gen.return_value = (tmp_path, "Subagent finished.")

            # 1. Test b64_json
            req_b64 = {
                "prompt": "cute anime girl smiling",
                "response_format": "b64_json"
            }
            res = self.client.post("/v1/images/generations", json=req_b64)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("data", data)
            b64_val = data["data"][0]["b64_json"]
            self.assertTrue(len(b64_val) > 10)
            self.assertEqual(base64.b64decode(b64_val), b"PNG_FAKE_IMAGE_BYTES_LONGER_THAN_100_CHARACTERS_FOR_VALIDATION_PURPOSES_123456789012345678901234567890")

            # 2. Test url format
            req_url = {
                "prompt": "cute anime girl smiling",
                "response_format": "url"
            }
            res_url = self.client.post("/v1/images/generations", json=req_url)
            self.assertEqual(res_url.status_code, 200)
            data_url = res_url.json()
            self.assertIn("file:///", data_url["data"][0]["url"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("requests.post")
    def test_media_engine_generate_image_agy(self, mock_post):
        """Test MediaEngine.generate_image_agy via AGY bridge."""
        fake_bytes = b"REAL_IMAGE_BYTES_FROM_AGY_GENERATOR_1234567890"
        b64_str = base64.b64encode(fake_bytes).decode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "created": 1700000000,
            "data": [{"b64_json": b64_str}]
        }
        mock_post.return_value = mock_resp

        engine = MediaEngine()
        result_bytes = engine.generate_image_agy("cute anime girl in school uniform")
        self.assertIsNotNone(result_bytes)
        self.assertEqual(result_bytes, fake_bytes)

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

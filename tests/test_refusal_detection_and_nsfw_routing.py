"""
Unit tests for AI Safety Refusal Detection and NSFW Route Isolation (v2.4.20).
Verifies:
1. is_ai_refusal accurately flags standard Gemini / OpenAI refusal strings.
2. sanitize_chat_caption discards refusal text and falls back to sweet in-character caption.
3. HybridLLMClient preserves a dedicated uncensored NSFW client when SFW client is AGY Bridge or Cloud.
4. Auto-redirect on refusal reroutes to uncensored engine.
"""

import unittest
from unittest.mock import MagicMock
from routing_engine import is_ai_refusal, HybridLLMClient
from bot import sanitize_chat_caption


class TestRefusalDetectionAndNSFWRouting(unittest.TestCase):
    def test_refusal_detection(self):
        gemini_refusal = (
            "Saya tidak dapat memenuhi permintaan ini. Saya tidak dapat membuat konten yang "
            "bersifat eksplisit secara seksual, termasuk percakapan atau keterangan peran (roleplay) "
            "yang berkaitan dengan ketelanjangan atau aktivitas seksual."
        )
        self.assertTrue(is_ai_refusal(gemini_refusal))

        openai_refusal = "I cannot fulfill this request. As an AI language model, I cannot generate sexually explicit content."
        self.assertTrue(is_ai_refusal(openai_refusal))

        normal_caption = "Ini foto khusus buat kamu yaa sayang, jangan diliatin ke siapa-siapa 💕"
        self.assertFalse(is_ai_refusal(normal_caption))

    def test_sanitize_chat_caption_with_refusal(self):
        refusal_caption = (
            "Saya tidak dapat memenuhi permintaan ini. Saya tidak dapat membuat konten yang bersifat eksplisit secara seksual."
        )
        fallback = "Khusus buat kamu ya, jangan diliatin ke siapa-siapa 💕"
        result = sanitize_chat_caption(refusal_caption, fallback)
        self.assertEqual(result, fallback)

    def test_nsfw_client_preserved_when_sfw_is_agy(self):
        mock_sfw = MagicMock()
        mock_sfw.base_url = "http://127.0.0.1:8001/v1"
        mock_sfw.model = "gemini-3.8-flash-medium"

        client = HybridLLMClient(mode="unified", sfw_client=mock_sfw)
        # Even in unified mode, because SFW client is AGY (port 8001), nsfw_client must NOT be AGY!
        self.assertNotEqual(client.nsfw_client, mock_sfw)
        self.assertIn("5001", client.nsfw_client.base_url)

    def test_auto_redirect_on_refusal_response(self):
        from unittest.mock import patch
        mock_sfw = MagicMock()
        mock_sfw.base_url = "http://127.0.0.1:8001/v1"
        mock_sfw.chat.return_value = (
            "Saya tidak dapat memenuhi permintaan ini. Saya tidak dapat membuat konten yang bersifat eksplisit secara seksual.",
            ""
        )

        mock_nsfw = MagicMock()
        mock_nsfw.base_url = "http://127.0.0.1:5001/v1"
        mock_nsfw.chat.return_value = ("*Runa mendesah pelan*\n\nIni foto spesial buat kamu sayang~ 💕", "")

        with patch("bot.idle_engine", MagicMock()):
            client = HybridLLMClient(mode="split", sfw_client=mock_sfw, nsfw_client=mock_nsfw)
            reply, _ = client.chat([{"role": "user", "content": "foto kamu dong"}], is_nsfw=False)

            # Since SFW returned refusal, it must have auto-redirected to mock_nsfw
            self.assertIn("Ini foto spesial buat kamu", reply)
            mock_nsfw.chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Unit tests for Vision Perception:
- AGY Bridge 0-VRAM perception when AGY is active.
- Moondream2 local perception when running Local LLM (Stheno 8B).
- Visual context injection into text messages.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asset_manager
from vision_engine import vision_engine, inject_visual_context_into_messages
from routing_engine import HybridLLMClient


class TestVisionRouting(unittest.TestCase):
    def test_moondream_assets_registered(self):
        """Verifies moondream_text and moondream_mmproj in asset registry."""
        self.assertIn("moondream_text", asset_manager.ASSET_REGISTRY)
        self.assertIn("moondream_mmproj", asset_manager.ASSET_REGISTRY)
        self.assertEqual(asset_manager.ASSET_REGISTRY["moondream_text"]["filename"], "moondream2-q4_k.gguf")
        self.assertEqual(asset_manager.ASSET_REGISTRY["moondream_mmproj"]["filename"], "moondream2-mmproj-f16.gguf")

    def test_inject_visual_context_into_messages(self):
        """Verifies visual description is cleanly injected into the user turn."""
        messages = [
            {"role": "system", "content": "You are Akira."},
            {"role": "user", "content": "lagi ngopi nih di kafe"}
        ]
        augmented = inject_visual_context_into_messages(messages, "Secangkir kopi latte di meja kayu")
        self.assertEqual(len(augmented), 2)
        last_turn = augmented[-1]["content"]
        self.assertIn("Secangkir kopi latte di meja kayu", last_turn)
        self.assertIn("lagi ngopi nih di kafe", last_turn)

    @patch.object(vision_engine, "is_agy_active", return_value=True)
    @patch.object(vision_engine, "describe_with_agy", return_value="Foto pemandangan pantai yang indah.")
    def test_describe_image_prefers_agy_when_agy_active(self, mock_agy, mock_is_agy):
        """When AGY Bridge is active, vision engine must use AGY for 0-VRAM perception."""
        res = vision_engine.describe_image(b"fake_image_bytes", user_caption="ini di mana?")
        self.assertEqual(res, "Foto pemandangan pantai yang indah.")
        mock_agy.assert_called_once()

    @patch.object(vision_engine, "is_agy_active", return_value=False)
    @patch.object(vision_engine, "describe_with_moondream", return_value="A red sports car on the street.")
    def test_describe_image_uses_moondream_when_local(self, mock_moon, mock_is_agy):
        """When in Local LLM mode (non-AGY), vision engine must use Moondream."""
        res = vision_engine.describe_image(b"fake_image_bytes", user_caption="mobil siapa nih?")
        self.assertEqual(res, "A red sports car on the street.")
        mock_moon.assert_called_once()

    @patch("routing_engine.LocallyUncensoredClient")
    @patch.object(vision_engine, "describe_image", return_value="A cup of hot coffee on a table.")
    def test_routing_engine_uses_moondream_for_local_stheno(self, mock_desc, mock_client_cls):
        """When sending image to local Stheno, routing_engine extracts context via vision_engine."""
        mock_target = MagicMock()
        mock_target.base_url = "http://127.0.0.1:5001/v1"
        mock_target.model = "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf"
        mock_target.chat.return_value = ("Wah kopinya kelihatan nikmat!", "")

        hybrid = HybridLLMClient(
            mode="unified",
            sfw_client=mock_target,
            nsfw_client=mock_target
        )

        messages = [
            {"role": "system", "content": "You are waifu."},
            {"role": "user", "content": "lagi santai nih"}
        ]

        reply, _ = hybrid.chat(messages, image_bytes=b"sample_image")
        self.assertEqual(reply, "Wah kopinya kelihatan nikmat!")
        # describe_image should have been called
        mock_desc.assert_called_once()
        # Stheno's chat must be called with image_bytes=None and injected text
        called_args = mock_target.chat.call_args
        self.assertIsNone(called_args.kwargs.get("image_bytes"))
        called_messages = called_args.args[0]
        self.assertIn("A cup of hot coffee on a table.", called_messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()


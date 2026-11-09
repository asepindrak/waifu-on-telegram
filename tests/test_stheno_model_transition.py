#!/usr/bin/env python3
"""
Unit tests for L3-8B-Stheno-v3.4 model integration, auto-download on update,
and conditional auto-selection (auto-select when currently on Huihui).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asset_manager
from bin.cli import cmd_update
from bot import apply_llm_choice


class TestSthenoModelTransition(unittest.TestCase):
    def test_stheno_registered_in_asset_registry(self):
        """Verifies stheno_8b is properly configured in ASSET_REGISTRY."""
        self.assertIn("stheno_8b", asset_manager.ASSET_REGISTRY)
        entry = asset_manager.ASSET_REGISTRY["stheno_8b"]
        self.assertEqual(entry["filename"], "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf")
        self.assertEqual(entry["type"], "llm_model")
        self.assertIn("bartowski", entry["url"])
        self.assertIn("Llama-3.1-8B-Stheno-v3.4", entry["url"])

    def test_get_llm_launch_spec_prioritizes_stheno_and_omits_incompatible_mmproj(self):
        """Ensures get_llm_launch_spec chooses Stheno when installed and drops Qwythos mmproj."""
        with patch.object(asset_manager, "shutil") as mock_shutil, \
             patch.object(asset_manager, "get_asset_info") as mock_info, \
             patch("os.path.isfile", return_value=True):
            
            mock_shutil.which.return_value = "/tools/koboldcpp.exe"

            def fake_info(key):
                if key == "stheno_8b":
                    return {
                        "installed": True,
                        "target_path": "/models/Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf"
                    }
                if key == "qwythos_vision":
                    return {
                        "installed": True,
                        "target_path": "/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf"
                    }
                return {"installed": False}

            mock_info.side_effect = fake_info

            spec = asset_manager.get_llm_launch_spec()
            self.assertIsNotNone(spec)
            self.assertIn("Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf", spec["model"])
            # mmproj must be omitted for Stheno to prevent runtime tensor dimension crash
            self.assertNotIn("--mmproj", spec["cmd"])

    @patch("subprocess.run")
    @patch.object(asset_manager, "ensure_nodejs", return_value=True)
    @patch.object(asset_manager, "ensure_koboldcpp", return_value=True)
    @patch.object(asset_manager, "ensure_comfyui", return_value=True)
    @patch.object(asset_manager, "detect_comfyui_dir", return_value=None)
    @patch.object(asset_manager, "get_asset_info")
    @patch.object(asset_manager, "download_asset", return_value=True)
    @patch("setup.read_env")
    @patch("setup.write_env")
    def test_cmd_update_auto_selects_stheno_only_when_user_was_on_huihui(
        self, mock_write_env, mock_read_env, mock_dl, mock_info, mock_detect,
        mock_comfy, mock_kcpp, mock_node, mock_sub
    ):
        """Validates that cmd_update auto-selects Stheno when previous model is Huihui."""
        mock_sub.return_value = MagicMock(returncode=0, stdout="", stderr="")

        def fake_info(key):
            return {
                "name": key,
                "type": "llm_model",
                "size_mb": 100,
                "installed": False,
                "current_size_mb": 0,
                "target_path": f"/tmp/{key}"
            }
        mock_info.side_effect = fake_info

        # Case 1: User currently has Huihui active
        mock_read_env.return_value = {
            "LLM_MODEL": "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
            "LOCAL_LLM_MODEL": "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
            "NSFW_LLM_MODEL": "Huihui-Qwythos-9B"
        }

        cmd_update()

        # Download asset should have been called for stheno_8b
        downloaded = [call_args[0][0] for call_args in mock_dl.call_args_list]
        self.assertIn("stheno_8b", downloaded)

        # write_env must have been called with new Stheno model
        mock_write_env.assert_called()
        saved_env = mock_write_env.call_args[0][0]
        self.assertEqual(saved_env["LLM_MODEL"], "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf")
        self.assertEqual(saved_env["LOCAL_LLM_MODEL"], "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf")

    @patch("subprocess.run")
    @patch.object(asset_manager, "ensure_nodejs", return_value=True)
    @patch.object(asset_manager, "ensure_koboldcpp", return_value=True)
    @patch.object(asset_manager, "ensure_comfyui", return_value=True)
    @patch.object(asset_manager, "detect_comfyui_dir", return_value=None)
    @patch.object(asset_manager, "get_asset_info")
    @patch.object(asset_manager, "download_asset", return_value=True)
    @patch("setup.read_env")
    @patch("setup.write_env")
    def test_cmd_update_preserves_custom_model_when_not_huihui(
        self, mock_write_env, mock_read_env, mock_dl, mock_info, mock_detect,
        mock_comfy, mock_kcpp, mock_node, mock_sub
    ):
        """Validates that cmd_update does NOT touch LLM_MODEL if user is using a non-Huihui model."""
        mock_sub.return_value = MagicMock(returncode=0, stdout="", stderr="")

        def fake_info(key):
            return {
                "name": key,
                "type": "llm_model",
                "size_mb": 100,
                "installed": True,
                "current_size_mb": 100,
                "target_path": f"/tmp/{key}"
            }
        mock_info.side_effect = fake_info

        # Case 2: User has gemini or custom mistral model
        mock_read_env.return_value = {
            "LLM_MODEL": "gemini-3.8-flash-medium",
            "LOCAL_LLM_MODEL": "Mistral-7B-Instruct.gguf",
            "NSFW_LLM_MODEL": "default"
        }

        cmd_update()

        # write_env should NOT overwrite the user's custom choice
        mock_write_env.assert_not_called()

    @patch("bot.update_env_variable")
    def test_apply_llm_choice_stheno(self, mock_update_env):
        """Verifies apply_llm_choice correctly selects Stheno."""
        label = apply_llm_choice("stheno")
        self.assertIn("Stheno", label)
        mock_update_env.assert_any_call("LLM_MODEL", "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf")
        mock_update_env.assert_any_call("LOCAL_LLM_MODEL", "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf")


if __name__ == "__main__":
    unittest.main()


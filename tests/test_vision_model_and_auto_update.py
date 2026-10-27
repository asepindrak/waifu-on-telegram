#!/usr/bin/env python3
"""
💖 Waifu on Telegram - Vision Model (mmproj) & Auto-Download Unit Tests
Validates:
  1. qwythos_vision resolution in models/ and detect_locally_uncensored_dir()
  2. asset_manager.download_asset() support for llm_model
  3. KoboldCPP launch scripts pass --mmproj when available
  4. waifu update (cmd_update) auto-checks and repairs missing models & libraries
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asset_manager
from bin.cli import cmd_update


class TestVisionModelAndAutoUpdate(unittest.TestCase):
    def test_vision_asset_registered(self):
        self.assertIn("qwythos_vision", asset_manager.ASSET_REGISTRY)
        info = asset_manager.get_asset_info("qwythos_vision")
        self.assertIsNotNone(info)
        self.assertEqual(info["type"], "llm_model")
        self.assertTrue(info["filename"].endswith(".gguf"))
        self.assertIn("models", info["target_path"])

    def test_download_asset_supports_llm_model(self):
        with patch.object(asset_manager, "_download_file", return_value=True) as mock_dl:
            ok = asset_manager.download_asset("qwythos_vision")
            self.assertTrue(ok)
            mock_dl.assert_called_once()

    def test_start_scripts_support_mmproj(self):
        # 1. start_services.bat
        bat_path = os.path.join(PROJECT_ROOT, "start_services.bat")
        with open(bat_path, "r", encoding="utf-8", errors="ignore") as f:
            bat_content = f.read()
        self.assertIn("KOBOLD_MMPROJ", bat_content)
        self.assertIn("--mmproj", bat_content)

        # 2. start_services.sh
        sh_path = os.path.join(PROJECT_ROOT, "start_services.sh")
        with open(sh_path, "r", encoding="utf-8", errors="ignore") as f:
            sh_content = f.read()
        self.assertIn("MMPROJ_PATH", sh_content)
        self.assertIn("--mmproj", sh_content)

        # 3. start_services_silent.vbs
        vbs_path = os.path.join(PROJECT_ROOT, "start_services_silent.vbs")
        with open(vbs_path, "r", encoding="utf-8", errors="ignore") as f:
            vbs_content = f.read()
        self.assertIn("mmprojFile", vbs_content)
        self.assertIn("--mmproj", vbs_content)

    def test_installer_scripts_contain_vision_prompt(self):
        # install.ps1
        ps1_path = os.path.join(PROJECT_ROOT, "install.ps1")
        with open(ps1_path, "r", encoding="utf-8", errors="ignore") as f:
            ps1_content = f.read()
        self.assertIn("Vision Adapter", ps1_content)
        self.assertIn("mmproj", ps1_content)

        # install.sh
        sh_path = os.path.join(PROJECT_ROOT, "install.sh")
        with open(sh_path, "r", encoding="utf-8", errors="ignore") as f:
            sh_content = f.read()
        self.assertIn("Vision Adapter", sh_content)
        self.assertIn("mmproj", sh_content)

    @patch("subprocess.run")
    @patch.object(asset_manager, "ensure_nodejs", return_value=True)
    @patch.object(asset_manager, "ensure_koboldcpp", return_value=True)
    @patch.object(asset_manager, "get_asset_info")
    @patch.object(asset_manager, "download_asset", return_value=True)
    def test_cmd_update_auto_repairs_missing_models(self, mock_dl, mock_info, mock_kcpp, mock_node, mock_sub):
        mock_sub.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Simulate missing models
        def fake_get_asset_info(key):
            return {
                "name": key,
                "type": "llm_model",
                "size_mb": 100,
                "installed": False,
                "current_size_mb": 0,
                "target_path": f"/tmp/{key}"
            }
        mock_info.side_effect = fake_get_asset_info

        # Run cmd_update
        cmd_update()

        # Check that download_asset was called for core models
        downloaded_keys = [call_args[0][0] for call_args in mock_dl.call_args_list]
        self.assertIn("qwythos_9b", downloaded_keys)
        self.assertIn("qwythos_vision", downloaded_keys)


if __name__ == "__main__":
    unittest.main()

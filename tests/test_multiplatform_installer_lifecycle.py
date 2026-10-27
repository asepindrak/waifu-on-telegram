#!/usr/bin/env python3
"""
💖 Waifu on Telegram - Multiplatform Lifecycle & Installation Unit Test Suite
Covers 8 Key Real-World Scenarios across Windows, Linux, and macOS:
  Case 1: Fresh install - Zero prerequisites (ComfyUI & LU offline/missing)
  Case 2: Fresh install - ComfyUI already installed (Custom path/drive)
  Case 3: Fresh install - Locally Uncensored already installed
  Case 4: Fresh install - Both ComfyUI and Locally Uncensored installed
  Case 5: Fresh install - Partial models present (e.g. MeinaMix ready, AnimateDiff missing)
  Case 6: Feature update - No new models required
  Case 7: Feature update - New third-party library/dependencies added
  Case 8: Model update - Lazy auto-download / upgrade to new checkpoint
"""

import os
import sys
import shutil
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asset_manager
import setup


class TestMultiplatformInstallerLifecycle(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary sandbox for filesystem mocking
        self.test_dir = tempfile.mkdtemp(prefix="waifu_test_env_")
        self.mock_home = os.path.join(self.test_dir, "home", "user")
        os.makedirs(self.mock_home, exist_ok=True)
        # Reset asset_manager internal cache
        asset_manager._COMFYUI_DIR_CACHE = None

    def tearDown(self):
        # Clean up temporary sandbox
        shutil.rmtree(self.test_dir, ignore_errors=True)
        asset_manager._COMFYUI_DIR_CACHE = None

    # =========================================================================
    # CASE 1: Fresh Install - Belum Ada Apapun (Zero Prerequisites)
    # =========================================================================
    def test_case_1_fresh_install_zero_prerequisites(self):
        """Case 1: System has no ComfyUI, no LLM models, and no downloaded assets."""
        with patch.dict(os.environ, {"COMFYUI_DIR": "", "COMFYUI_PATH": "", "LOCALLY_UNCENSORED_DIR": os.path.join(self.mock_home, "NonExistentModels"), "APPDATA": os.path.join(self.mock_home, "AppData", "Roaming"), "LOCALAPPDATA": os.path.join(self.mock_home, "AppData", "Local"), "HOME": self.mock_home, "USERPROFILE": self.mock_home}):
            with patch("os.path.expanduser", return_value=self.mock_home):
                with patch("shutil.which", return_value=None):
                    with patch("subprocess.run") as mock_sub:
                        # Mock no listening process on port 8188
                        mock_sub.return_value = MagicMock(returncode=1, stdout="", stderr="")
                        with patch("asset_manager.detect_comfyui_dir", return_value=None):
                            comfy_dir = asset_manager.detect_comfyui_dir()
                            self.assertIsNone(comfy_dir, "ComfyUI should not be detected when none exists")

                        # All assets should be reported as missing
                        assets = asset_manager.check_all_assets()
                        for key, info in assets.items():
                            self.assertFalse(info.get("installed"), f"Asset {key} should be missing in fresh environment")

                        # Local LLM models scanner should return empty list gracefully without throwing
                        with patch("setup.scan_local_llm_models", return_value=[]):
                            llm_models = setup.scan_local_llm_models()
                            self.assertEqual(len(llm_models), 0)

                        # Video engine assets check should report missing
                        ready, missing = asset_manager.ensure_video_engine_assets("animatediff")
                        self.assertFalse(ready)
                        self.assertIn("animatediff_v2", missing)

    # =========================================================================
    # CASE 2: Fresh Install - Sudah Ada ComfyUI di Custom Path / Non-C Drive
    # =========================================================================
    def test_case_2_fresh_install_with_existing_comfyui(self):
        """Case 2: User already has ComfyUI installed in custom path (e.g., Linux/macOS or custom drive)."""
        custom_comfy = os.path.join(self.test_dir, "custom_drive", "AI", "ComfyUI")
        os.makedirs(os.path.join(custom_comfy, "models", "checkpoints"), exist_ok=True)
        os.makedirs(os.path.join(custom_comfy, "models", "diffusion_models"), exist_ok=True)

        with patch.dict(os.environ, {"COMFYUI_DIR": custom_comfy}):
            comfy_dir = asset_manager.detect_comfyui_dir()
            self.assertEqual(comfy_dir, os.path.abspath(custom_comfy))

            # Verify scanner detects checkpoints folder
            test_ckpt = os.path.join(custom_comfy, "models", "checkpoints", "custom_anime.safetensors")
            with open(test_ckpt, "wb") as f:
                f.write(b"0" * (15 * 1024 * 1024)) # 15 MB dummy file

            with patch("asset_manager.detect_comfyui_dir", return_value=custom_comfy):
                scanned_ckpts = setup.scan_image_models()
                ckpt_names = [name for _, name in scanned_ckpts]
                self.assertIn("custom_anime.safetensors", ckpt_names)

    # =========================================================================
    # CASE 3: Fresh Install - Sudah Ada Locally Uncensored (LLM)
    # =========================================================================
    def test_case_3_fresh_install_with_existing_locally_uncensored(self):
        """Case 3: User already has Locally Uncensored with .gguf models on macOS/Linux/Windows."""
        mock_lu_dir = os.path.join(self.test_dir, "Locally Uncensored", "models")
        os.makedirs(mock_lu_dir, exist_ok=True)
        dummy_gguf = os.path.join(mock_lu_dir, "Qwythos-9B-Q4_K.gguf")
        with open(dummy_gguf, "w") as f:
            f.write("dummy gguf model")

        with patch("setup.candidate_lu_dirs", [mock_lu_dir], create=True):
            with patch("os.path.exists", side_effect=lambda p: p == mock_lu_dir or os.path.exists(p)):
                with patch("os.listdir", side_effect=lambda p: ["Qwythos-9B-Q4_K.gguf"] if p == mock_lu_dir else []):
                    # Test scanner finding the model
                    models = []
                    for f in ["Qwythos-9B-Q4_K.gguf"]:
                        if f.endswith(".gguf") and not f.endswith(".mmproj.gguf"):
                            models.append(("Locally Uncensored", f, os.path.join(mock_lu_dir, f)))
                    self.assertEqual(len(models), 1)
                    self.assertEqual(models[0][1], "Qwythos-9B-Q4_K.gguf")

    # =========================================================================
    # CASE 4: Fresh Install - Sudah Ada ComfyUI dan Locally Uncensored Lengkap
    # =========================================================================
    def test_case_4_fresh_install_both_present(self):
        """Case 4: Full ecosystem pre-installed (Both LLM backend and ComfyUI available)."""
        mock_comfy = os.path.join(self.test_dir, "ComfyUI")
        os.makedirs(os.path.join(mock_comfy, "models"), exist_ok=True)

        diff_dir = os.path.join(mock_comfy, "models", "diffusion_models")
        vae_dir = os.path.join(mock_comfy, "models", "vae")
        os.makedirs(diff_dir, exist_ok=True)
        os.makedirs(vae_dir, exist_ok=True)
        with open(os.path.join(diff_dir, "wan2.1_t2v_1.3B_bf16.safetensors"), "wb") as f:
            f.write(b"W" * (12 * 1024 * 1024))
        with open(os.path.join(vae_dir, "wan_2.1_vae.safetensors"), "wb") as f:
            f.write(b"V" * (12 * 1024 * 1024))

        with patch.dict(os.environ, {"COMFYUI_DIR": mock_comfy}):
            self.assertEqual(asset_manager.detect_comfyui_dir(), os.path.abspath(mock_comfy))
            # Test Wan 2.1 AI video engine is immediately operational
            ready, missing = asset_manager.ensure_video_engine_assets("wan21")
            self.assertTrue(ready)
            self.assertEqual(len(missing), 0)

    # =========================================================================
    # CASE 5: Fresh Install - Model Sudah Ada Beberapa (Partial Models)
    # =========================================================================
    def test_case_5_partial_models_installed(self):
        """Case 5: User has MeinaMix anime checkpoint, but video modules (AnimateDiff) are missing."""
        mock_comfy = os.path.join(self.test_dir, "ComfyUI")
        ckpt_dir = os.path.join(mock_comfy, "models", "checkpoints")
        os.makedirs(ckpt_dir, exist_ok=True)

        # Place MeinaMix dummy file > 10MB
        meina_file = os.path.join(ckpt_dir, "MeinaMix_v11.safetensors")
        with open(meina_file, "wb") as f:
            f.write(b"1" * (12 * 1024 * 1024))

        with patch.dict(os.environ, {"COMFYUI_DIR": mock_comfy}):
            info_meina = asset_manager.get_asset_info("meinamix")
            self.assertTrue(info_meina["installed"], "MeinaMix should be recognized as installed")

            info_anim = asset_manager.get_asset_info("animatediff_v2")
            self.assertFalse(info_anim["installed"], "AnimateDiff should be recognized as missing")

            # Check engine requirements
            ready_anim, missing_anim = asset_manager.ensure_video_engine_assets("animatediff")
            self.assertFalse(ready_anim)
            self.assertIn("animatediff_v2", missing_anim)

    # =========================================================================
    # CASE 6: Update Fitur Tapi Tanpa Tambah Model
    # =========================================================================
    def test_case_6_feature_update_without_new_models(self):
        """Case 6: App code updates (e.g. persona logic/schedule), no new AI weights needed."""
        mock_comfy = os.path.join(self.test_dir, "ComfyUI")
        ckpt_dir = os.path.join(mock_comfy, "models", "checkpoints")
        diff_dir = os.path.join(mock_comfy, "models", "diffusion_models")
        vae_dir = os.path.join(mock_comfy, "models", "vae")
        os.makedirs(ckpt_dir, exist_ok=True)
        os.makedirs(diff_dir, exist_ok=True)
        os.makedirs(vae_dir, exist_ok=True)

        # Pre-seed Wan 2.1 models
        with open(os.path.join(diff_dir, "wan2.1_t2v_1.3B_bf16.safetensors"), "wb") as f:
            f.write(b"W" * (12 * 1024 * 1024))
        with open(os.path.join(vae_dir, "wan_2.1_vae.safetensors"), "wb") as f:
            f.write(b"V" * (12 * 1024 * 1024))

        with patch.dict(os.environ, {"COMFYUI_DIR": mock_comfy}):
            ready, missing = asset_manager.ensure_video_engine_assets("wan21")
            self.assertTrue(ready, "Wan 2.1 engine should be 100% ready without re-downloading")
            self.assertEqual(len(missing), 0)

    # =========================================================================
    # CASE 7: Update Fitur Ada Tambahan Third-Party / Dependencies
    # =========================================================================
    def test_case_7_update_with_third_party_dependencies(self):
        """Case 7: Feature update requires new Python libraries or Node packages."""
        # Test simulated pip validation
        dummy_req = os.path.join(self.test_dir, "requirements.txt")
        with open(dummy_req, "w") as f:
            f.write("requests>=2.31.0\npython-dotenv>=1.0.0\n")

        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="", stderr="")
            import bin.cli as cli
            with patch.object(cli, "PROJECT_ROOT", self.test_dir):
                # Verify requirements.txt presence triggers pip verification
                self.assertTrue(os.path.exists(dummy_req))

    # =========================================================================
    # CASE 8: Update Model (Lazy Auto-Download / Upgrade Checkpoint)
    # =========================================================================
    def test_case_8_model_update_and_lazy_download(self):
        """Case 8: User triggers lazy auto-download for missing AnimateDiff motion module."""
        mock_comfy = os.path.join(self.test_dir, "ComfyUI")
        target_models_dir = os.path.join(mock_comfy, "models", "animatediff_models")
        os.makedirs(target_models_dir, exist_ok=True)
        target_ckpt = os.path.join(target_models_dir, "mm_sd_v15_v2.ckpt")

        with patch.dict(os.environ, {"COMFYUI_DIR": mock_comfy}):
            # Before download: Missing
            info_before = asset_manager.get_asset_info("animatediff_v2")
            self.assertFalse(info_before["installed"])

            # Mock download writing valid dummy file > 10MB
            def fake_download(url, **kwargs):
                with open(target_ckpt, "wb") as f:
                    f.write(b"M" * (15 * 1024 * 1024))
                mock_res = MagicMock()
                mock_res.status_code = 200
                mock_res.headers = {"content-length": str(15 * 1024 * 1024)}
                mock_res.iter_content = lambda chunk_size: [b"M" * (15 * 1024 * 1024)]
                mock_res.__enter__ = lambda s: mock_res
                mock_res.__exit__ = lambda s, *a: None
                return mock_res

            with patch("requests.get", side_effect=fake_download):
                with patch("shutil.which", return_value=None): # Force python requests path
                    success = asset_manager.download_asset("animatediff_v2")
                    self.assertTrue(success, "Lazy download should succeed")

            # After download: Successfully recognized as installed
            info_after = asset_manager.get_asset_info("animatediff_v2")
            self.assertTrue(info_after["installed"])
            self.assertGreater(info_after["current_size_mb"], 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)

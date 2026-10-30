import os
import unittest
import tempfile
import shutil
from unittest.mock import patch
import asset_manager
import setup

class TestIncompleteModelDetection(unittest.TestCase):
    def setUp(self):
        os.environ["FORCE_STRICT_MODEL_SIZE"] = "1"
        self.test_dir = tempfile.mkdtemp()
        self.checkpoints_dir = os.path.join(self.test_dir, "models", "checkpoints")
        os.makedirs(self.checkpoints_dir, exist_ok=True)

    def tearDown(self):
        os.environ.pop("FORCE_STRICT_MODEL_SIZE", None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_incomplete_checkpoint_reported_as_incomplete(self):
        """Verify that an interrupted download (e.g. 50 MB) is detected as incomplete, NOT installed."""
        fake_partial_ckpt = os.path.join(self.checkpoints_dir, "AnythingXL_xl.safetensors")
        with open(fake_partial_ckpt, "wb") as f:
            f.seek(50 * 1024 * 1024 - 1)
            f.write(b"\0")  # Exactly 50 MB

        with patch("asset_manager.detect_comfyui_dir", return_value=self.test_dir):
            info = asset_manager.get_asset_info("anything_xl")
            self.assertIsNotNone(info)
            self.assertFalse(info["installed"], "Incomplete 50MB file should NOT be considered installed")
            self.assertTrue(info["incomplete"], "File should be marked as incomplete")
            self.assertEqual(info["status"], "incomplete")
            self.assertEqual(info["current_size_mb"], 50.0)
            self.assertTrue(info["percent_complete"] < 2.0)

    def test_complete_checkpoint_reported_as_installed(self):
        """Verify that a complete checkpoint (>= 80% expected size) is detected as installed."""
        fake_complete_ckpt = os.path.join(self.checkpoints_dir, "AnythingXL_xl.safetensors")
        # Anything XL is 6616 MB, 80% is ~5292 MB. Let's create mock test with a smaller model or mock getsize
        with patch("asset_manager.detect_comfyui_dir", return_value=self.test_dir):
            with patch("os.path.isfile", return_value=True):
                with patch("os.path.getsize", return_value=6000 * 1024 * 1024):
                    info = asset_manager.get_asset_info("anything_xl")
                    self.assertTrue(info["installed"])
                    self.assertFalse(info["incomplete"])
                    self.assertEqual(info["status"], "installed")

    def test_scan_image_models_ignores_incomplete_files(self):
        """Verify scan_image_models in setup.py ignores files under 1000 MB."""
        fake_partial = os.path.join(self.checkpoints_dir, "test_broken.safetensors")
        with open(fake_partial, "wb") as f:
            f.seek(50 * 1024 * 1024 - 1)
            f.write(b"\0")

        with patch("asset_manager.detect_comfyui_dir", return_value=self.test_dir):
            ckpts = setup.scan_image_models()
            ckpt_names = [c[1] for c in ckpts]
            self.assertNotIn("test_broken.safetensors", ckpt_names)

if __name__ == "__main__":
    unittest.main()

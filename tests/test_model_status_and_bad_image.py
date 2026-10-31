import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "99999"

import photo_vault
import asset_manager
import media_engine
import bot

asset_manager._COMFYUI_FORCE_CPU = False


class TestModelStatusAndBadImage(unittest.TestCase):
    def test_vault_stats(self):
        """photo_vault.get_vault_stats returns valid dictionary with total and by_persona."""
        stats = photo_vault.get_vault_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("total", stats)
        self.assertIn("by_persona", stats)

    def test_check_and_repair_comfyui_environment_quarantines_corrupt_pyd(self):
        """Corrupted image_stable.pyd is automatically renamed to .corrupt.bak."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            py_exe = os.path.join(tmpdir, "python.exe")
            with open(py_exe, "w") as f:
                f.write("#!/usr/bin/env python")

            site_pkg = os.path.join(tmpdir, "Lib", "site-packages", "torchvision")
            os.makedirs(site_pkg, exist_ok=True)
            bad_pyd = os.path.join(site_pkg, "image_stable.pyd")
            with open(bad_pyd, "wb") as f:
                f.write(b"")  # 0 bytes corrupted file

            self.assertTrue(os.path.isfile(bad_pyd))
            asset_manager.check_and_repair_comfyui_environment(py_exe)
            self.assertFalse(os.path.isfile(bad_pyd))
            self.assertTrue(os.path.isfile(bad_pyd + ".corrupt.bak"))

    @patch("bot.is_authorized", return_value=True)
    def test_system_diagnostics_report_includes_models_and_vault(self, mock_auth):
        """build_system_diagnostics_report displays active LLM model, Photo Model, and Photo Vault info."""
        report = bot.build_system_diagnostics_report(99999)
        self.assertIn("Local LLM Engine", report)
        self.assertIn("Model Foto", report)
        self.assertIn("Photo Vault", report)
        self.assertIn("Engine Video", report)

    def test_wan21_download_urls_and_mirrors_configured(self):
        """Wan 2.1 1.3B and VAE assets point to valid Comfy-Org Hugging Face repos with mirrors."""
        info_model = asset_manager.ASSET_REGISTRY.get("wan21_1.3b")
        info_vae = asset_manager.ASSET_REGISTRY.get("wan21_vae")

        self.assertIsNotNone(info_model)
        self.assertIn("Comfy-Org/Wan_2.1_ComfyUI_repackaged", info_model["url"])
        self.assertIn("fallback_url", info_model)
        self.assertIn("mirrors", info_model)
        self.assertGreaterEqual(len(info_model["mirrors"]), 2)

        self.assertIsNotNone(info_vae)
        self.assertIn("Comfy-Org/Wan_2.1_ComfyUI_repackaged", info_vae["url"])
        self.assertIn("fallback_url", info_vae)
        self.assertIn("mirrors", info_vae)

    def test_download_file_cleans_up_stub_file(self):
        """_download_file deletes stub files smaller than 4096 bytes before attempting resume/download."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            stub_file = os.path.join(tmpdir, "model_stub.safetensors")
            with open(stub_file, "wb") as f:
                f.write(b"404 Not Found HTML page")  # tiny stub file

            self.assertTrue(os.path.exists(stub_file))
            # Test with dummy url and mocked subprocess/requests
            with patch("shutil.which", return_value=None), patch("requests.get") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                mock_req.return_value.__enter__.return_value = mock_resp
                asset_manager._download_file("http://invalid.url", stub_file)

            # The tiny stub file should have been cleaned up
            self.assertFalse(os.path.exists(stub_file))


if __name__ == "__main__":
    unittest.main()

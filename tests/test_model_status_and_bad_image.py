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


if __name__ == "__main__":
    unittest.main()

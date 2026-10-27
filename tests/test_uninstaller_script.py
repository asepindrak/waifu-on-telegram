#!/usr/bin/env python3
"""
💖 Waifu on Telegram - Uninstaller Script & Data Retention Unit Tests
Validates that uninstall.ps1 and uninstall.sh properly handle:
  1. Service teardown (Bot, KoboldCPP 5001, ComfyUI 8188, Music Player 8002)
  2. Autorun cleanup (Windows Startup, crontab, LaunchAgent, systemd)
  3. Option [1] Clean Reset / Full Wipe
  4. Option [2] Keep Data (Preserving models, photo_vault, .env, personas)
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestUninstallerScripts(unittest.TestCase):
    def setUp(self):
        self.ps1_path = os.path.join(PROJECT_ROOT, "uninstall.ps1")
        self.sh_path = os.path.join(PROJECT_ROOT, "uninstall.sh")

    def test_scripts_exist(self):
        self.assertTrue(os.path.exists(self.ps1_path), "uninstall.ps1 must exist")
        self.assertTrue(os.path.exists(self.sh_path), "uninstall.sh must exist")

    def test_windows_uninstaller_services_teardown(self):
        with open(self.ps1_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check bot termination
        self.assertIn("bot.py", content, "uninstall.ps1 must terminate bot.py")

        # Check KoboldCPP termination (name and port 5001)
        self.assertIn("koboldcpp", content.lower(), "uninstall.ps1 must terminate koboldcpp")
        self.assertIn("5001", content, "uninstall.ps1 must inspect port 5001")

        # Check ComfyUI termination (port 8188)
        self.assertIn("8188", content, "uninstall.ps1 must inspect port 8188 for ComfyUI")

        # Check Music server termination (port 8002)
        self.assertIn("8002", content, "uninstall.ps1 must inspect port 8002 for music server")

    def test_windows_uninstaller_autorun_and_data_retention(self):
        with open(self.ps1_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check Startup shortcuts
        self.assertIn("Startup", content, "uninstall.ps1 must clean Windows Startup folder")
        self.assertIn("waifu.cmd", content, "uninstall.ps1 must clean global waifu.cmd CLI")

        # Check Option 1 (Remove all / clean wipe)
        self.assertIn("FULL UNINSTALL", content, "uninstall.ps1 must feature Option 1")
        self.assertIn("Remove-Item -Path $targetInstallDir -Recurse", content)

        # Check Option 2 (Keep data - models, photo vault, .env)
        self.assertIn("KEEP DATA", content, "uninstall.ps1 must feature Option 2 Keep Data")
        self.assertIn("models", content, "uninstall.ps1 must reference preserving models")
        self.assertIn("photo_vault", content, "uninstall.ps1 must reference preserving photo_vault")
        self.assertIn(".env", content, "uninstall.ps1 must reference preserving .env")

    def test_unix_uninstaller_services_teardown(self):
        with open(self.sh_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check bot termination
        self.assertIn("bot.py", content, "uninstall.sh must terminate bot.py")

        # Check KoboldCPP termination
        self.assertIn("koboldcpp", content, "uninstall.sh must terminate koboldcpp")

        # Check ComfyUI & ports
        self.assertIn("8188", content, "uninstall.sh must inspect ComfyUI port 8188")
        self.assertIn("5001", content, "uninstall.sh must inspect KoboldCPP port 5001")
        self.assertIn("8002", content, "uninstall.sh must inspect Music port 8002")

    def test_unix_uninstaller_autorun_and_data_retention(self):
        with open(self.sh_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check autorun removal
        self.assertIn("crontab", content, "uninstall.sh must clean crontab")
        self.assertIn("LaunchAgents", content, "uninstall.sh must clean macOS LaunchAgents")
        self.assertIn("waifu", content, "uninstall.sh must clean CLI shortcuts")

        # Check Option 1 and Option 2
        self.assertIn("FULL UNINSTALL", content, "uninstall.sh must feature Option 1")
        self.assertIn("KEEP DATA", content, "uninstall.sh must feature Option 2")
        self.assertIn("models", content, "uninstall.sh must reference preserving models")
        self.assertIn("photo_vault", content, "uninstall.sh must reference preserving photo_vault")


if __name__ == "__main__":
    unittest.main()

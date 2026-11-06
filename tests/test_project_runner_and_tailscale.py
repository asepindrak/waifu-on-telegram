"""
test_project_runner_and_tailscale.py - Test suite for background project server execution,
port detection, and Tailscale integration.
"""

import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from project_runner import ProjectRunner, TailscaleManager, get_project_runner
from project_manager import ProjectManager
from project_intent_router import ProjectIntentRouter, ProjectIntentResult


class TestProjectRunnerAndTailscale(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="waifu_test_runner_")
        self.projects_root = os.path.join(self.test_dir, "projects")
        self.data_dir = os.path.join(self.test_dir, "data")
        os.makedirs(self.projects_root, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        self.pm = ProjectManager(data_dir=self.data_dir, projects_dir=self.projects_root)
        self.runner = ProjectRunner(data_dir=self.data_dir)
        self.router = ProjectIntentRouter(project_manager=self.pm)

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_detect_run_command_nodejs(self):
        """Verify command detection for Node.js / Vite / Next.js."""
        proj_dir = os.path.join(self.projects_root, "web-app")
        os.makedirs(proj_dir, exist_ok=True)

        pkg_json = {
            "name": "web-app",
            "scripts": {
                "dev": "vite",
                "build": "vite build"
            },
            "devDependencies": {
                "vite": "^5.0.0"
            }
        }
        with open(os.path.join(proj_dir, "package.json"), "w", encoding="utf-8") as f:
            json.dump(pkg_json, f)

        cmd, port = self.runner.detect_run_command(proj_dir)
        self.assertEqual(cmd, "npm run dev")
        self.assertEqual(port, 5173)

    def test_detect_run_command_python_fastapi(self):
        """Verify command detection for FastAPI / Uvicorn."""
        proj_dir = os.path.join(self.projects_root, "api-service")
        os.makedirs(proj_dir, exist_ok=True)

        with open(os.path.join(proj_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n")

        cmd, port = self.runner.detect_run_command(proj_dir)
        self.assertIn("uvicorn", cmd)
        self.assertIn("main:app", cmd)
        self.assertEqual(port, 8000)

    def test_tailscale_manager_info(self):
        """Verify TailscaleManager extracts valid network info."""
        mock_status = {
            "Self": {
                "Online": True,
                "TailscaleIPs": ["100.81.165.71", "fd7a:115c:a1e0::1f31:a548"],
                "DNSName": "pc-office.tail2658d0.ts.net.",
                "HostName": "PC-OFFICE"
            },
            "Peer": {
                "peer1": {"HostName": "Galaxy A52s 5G"},
                "peer2": {"HostName": "ADENS-PC"}
            }
        }
        mock_proc = MagicMock(returncode=0, stdout=json.dumps(mock_status))
        with patch("subprocess.run", return_value=mock_proc):
            with patch("shutil.which", return_value="C:\\Tailscale\\tailscale.exe"):
                info = TailscaleManager.get_tailscale_info()
                self.assertTrue(info["installed"])
                self.assertTrue(info["online"])
                self.assertEqual(info["ip"], "100.81.165.71")
                self.assertEqual(info["magic_dns"], "pc-office.tail2658d0.ts.net")
                self.assertIn("Galaxy A52s 5G", info["devices"])

    def test_project_runner_start_and_stop_lifecycle(self):
        """Verify starting, registry recording, and stopping a background dev server."""
        proj_dir = os.path.join(self.projects_root, "static-site")
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write("<h1>Hello World</h1>")

        # Mock background process
        mock_proc = MagicMock()
        mock_proc.pid = 44556

        mock_ts_info = {
            "installed": True,
            "online": True,
            "ip": "100.81.165.71",
            "magic_dns": "pc-office.tail2658d0.ts.net",
            "hostname": "PC-OFFICE",
            "devices": ["Galaxy A52s 5G"]
        }

        with patch("subprocess.Popen", return_value=mock_proc), \
             patch.object(TailscaleManager, "get_tailscale_info", return_value=mock_ts_info), \
             patch.object(TailscaleManager, "setup_tailscale_serve", return_value=(True, "https://pc-office.tail2658d0.ts.net/")), \
             patch.object(self.runner, "scan_active_port", return_value=3000), \
             patch.object(self.runner, "_is_pid_alive", return_value=True):

            res = self.runner.start_project("static-site", proj_dir)
            self.assertTrue(res["success"])
            entry = res["entry"]
            self.assertEqual(entry["port"], 3000)
            self.assertEqual(entry["pid"], 44556)
            self.assertEqual(entry["tailscale_url"], "http://100.81.165.71:3000")
            self.assertEqual(entry["magic_dns_url"], "http://pc-office.tail2658d0.ts.net:3000")
            self.assertEqual(entry["https_serve_url"], "https://pc-office.tail2658d0.ts.net/")

            # Check list running
            running = self.runner.list_running()
            self.assertIn("static-site", running)

            # Test stop
            with patch("subprocess.run"):
                ok, msg = self.runner.stop_project("static-site")
                self.assertTrue(ok)
                self.assertIn("berhasil dihentikan", msg)
                self.assertNotIn("static-site", self.runner.list_running())

    def test_conversational_routing_run_and_stop(self):
        """Verify natural language matching for run project and stop project."""
        user_id = 1122
        self.pm.spawn_project("inventory-pos", switch_user_id=user_id)

        # 1. Run project intent
        res_run = self.router.route_intent("Akira, tolong run project inventory-pos di port 5000", user_id=user_id)
        self.assertEqual(res_run.intent_type, "RUN_PROJECT")
        self.assertEqual(res_run.target_project, "inventory-pos")
        self.assertEqual(res_run.custom_port, 5000)

        # 2. Stop project intent
        res_stop = self.router.route_intent("Akira, matikan server project", user_id=user_id)
        self.assertEqual(res_stop.intent_type, "STOP_PROJECT")

        # 3. Server status intent
        res_stat = self.router.route_intent("Cek server apa aja yang lagi kebuka portnya", user_id=user_id)
        self.assertEqual(res_stat.intent_type, "SERVER_STATUS")

        # 4. Server log intent
        res_log = self.router.route_intent("Lihat log server project", user_id=user_id)
        self.assertEqual(res_log.intent_type, "SERVER_LOGS")


if __name__ == "__main__":
    unittest.main()

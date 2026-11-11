import os
import shutil
import tempfile
import unittest
from project_server_manager import (
    find_free_port,
    detect_web_root,
    ProjectServerManager
)

class TestProjectServerManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.registry_file = os.path.join(self.test_dir, "test_servers.json")
        self.mgr = ProjectServerManager(registry_file=self.registry_file)

    def tearDown(self):
        # Stop any servers running in test
        for s in self.mgr.list_active_servers():
            self.mgr.stop_preview_server(s.get("port"))
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_free_port(self):
        port = find_free_port(start_port=9100)
        self.assertGreaterEqual(port, 9100)
        self.assertLess(port, 65535)

    def test_detect_web_root_direct_index(self):
        index_html = os.path.join(self.test_dir, "index.html")
        with open(index_html, "w") as f:
            f.write("<h1>Hello World</h1>")
        detected = detect_web_root(self.test_dir)
        self.assertIsNotNone(detected)
        dir_path, entry = detected
        self.assertEqual(os.path.normpath(dir_path), os.path.normpath(self.test_dir))
        self.assertEqual(entry, "index.html")

    def test_detect_web_root_subdir(self):
        sub = os.path.join(self.test_dir, "my-landing-page")
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "index.html"), "w") as f:
            f.write("<h1>Landing Page</h1>")

        detected = detect_web_root(self.test_dir)
        self.assertIsNotNone(detected)
        dir_path, entry = detected
        self.assertEqual(os.path.normpath(dir_path), os.path.normpath(sub))
        self.assertEqual(entry, "index.html")

    def test_start_and_stop_preview_server(self):
        sub = os.path.join(self.test_dir, "test-app")
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "index.html"), "w") as f:
            f.write("<!DOCTYPE html><html><body><h1>Test Live Preview</h1></body></html>")

        s_info = self.mgr.start_preview_server("test-app", sub)
        self.assertIsNotNone(s_info)
        port = s_info.get("port")
        self.assertIsNotNone(port)
        self.assertTrue(s_info["url"].startswith("http://127.0.0.1:"))

        # Check list active servers
        active = self.mgr.list_active_servers()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["project"], "test-app")

        # Stop server
        ok = self.mgr.stop_preview_server(port)
        self.assertTrue(ok)
        self.assertEqual(len(self.mgr.list_active_servers()), 0)

    def test_start_preview_server_includes_tailscale_url_when_installed(self):
        from unittest.mock import patch
        sub = os.path.join(self.test_dir, "ts-app")
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "index.html"), "w") as f:
            f.write("<!DOCTYPE html><html><body><h1>TS Preview</h1></body></html>")

        with patch("project_runner.TailscaleManager.get_tailscale_info", return_value={"installed": True, "online": True, "ip": "100.64.10.5"}):
            s_info = self.mgr.start_preview_server("ts-app", sub)
            self.assertIsNotNone(s_info)
            port = s_info["port"]
            self.assertEqual(s_info["url"], f"http://127.0.0.1:{port}/")
            self.assertEqual(s_info["tailscale_ip"], "100.64.10.5")
            self.assertEqual(s_info["tailscale_url"], f"http://100.64.10.5:{port}/")
            formatted = self.mgr.format_active_servers_message()
            self.assertIn(f"http://127.0.0.1:{port}/", formatted)
            self.assertIn(f"http://100.64.10.5:{port}/", formatted)
            self.mgr.stop_preview_server(port)

if __name__ == "__main__":
    unittest.main()


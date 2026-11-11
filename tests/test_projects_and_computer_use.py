import os
import sys
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from project_manager import ProjectManager
from computer_use_engine import ComputerUseEngine
from coding_engine import CodingEngine


class TestProjectManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root_projects_dir = os.path.join(self.temp_dir, "my_projects")
        os.makedirs(self.root_projects_dir, exist_ok=True)
        self.data_dir = os.path.join(self.temp_dir, "data")

        # Set env PROJECTS_DIR to root_projects_dir for the test
        self.old_env = os.environ.get("PROJECTS_DIR")
        os.environ["PROJECTS_DIR"] = self.root_projects_dir

        self.pm = ProjectManager(data_dir=self.data_dir, projects_dir=self.root_projects_dir)

    def tearDown(self):
        if self.old_env is not None:
            os.environ["PROJECTS_DIR"] = self.old_env
        else:
            os.environ.pop("PROJECTS_DIR", None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_project_initialization(self):
        projs = self.pm.list_projects()
        self.assertIn("general", projs)
        self.assertTrue(os.path.exists(projs["general"]))

        active = self.pm.get_active_project(user_id=123)
        self.assertEqual(active, "general")
        self.assertEqual(self.pm.get_active_project_path(user_id=123), projs["general"])

    def test_spawn_and_switch_project(self):
        ok, name, res_path = self.pm.spawn_project("my-cool-app", switch_user_id=456)
        self.assertTrue(ok)
        self.assertEqual(name, "my-cool-app")
        self.assertTrue(os.path.exists(res_path))

        active = self.pm.get_active_project(user_id=456)
        self.assertEqual(active, "my-cool-app")
        self.assertEqual(self.pm.get_active_project_path(user_id=456), res_path)

        # List should include new project
        projs = self.pm.list_projects()
        self.assertIn("my-cool-app", projs)

    def test_switch_active_project(self):
        self.pm.spawn_project("proj-a")
        self.pm.spawn_project("proj-b")

        ok, _ = self.pm.set_active_project(user_id=999, project_name="proj-a")
        self.assertTrue(ok)
        self.assertEqual(self.pm.get_active_project(user_id=999), "proj-a")

        ok, _ = self.pm.set_active_project(user_id=999, project_name="proj-b")
        self.assertTrue(ok)
        self.assertEqual(self.pm.get_active_project(user_id=999), "proj-b")

        # Switching to non-existent project should fail
        ok, _ = self.pm.set_active_project(user_id=999, project_name="non-existent")
        self.assertFalse(ok)
        self.assertEqual(self.pm.get_active_project(user_id=999), "proj-b")

    def test_set_projects_root_dir(self):
        new_root = os.path.join(self.temp_dir, "another_workspace")
        os.makedirs(new_root, exist_ok=True)
        os.makedirs(os.path.join(new_root, "existing_repo"), exist_ok=True)

        ok, msg = self.pm.set_projects_root_dir(new_root)
        self.assertTrue(ok)
        self.assertEqual(self.pm.get_projects_root_dir(), os.path.abspath(new_root))

        # Check auto scanning
        projs = self.pm.list_projects()
        self.assertIn("existing_repo", projs)


class TestComputerUseEngine(unittest.TestCase):
    def setUp(self):
        self.cu = ComputerUseEngine()

    def test_status_structure(self):
        st = self.cu.get_status()
        self.assertIsInstance(st, dict)
        self.assertIn("ok", st)

    @patch("subprocess.run")
    def test_run_command(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({"ok": True, "action": "click"})
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        ok, res = self.cu.run_command(["click", "--x", "100", "--y", "200"])
        self.assertTrue(ok)
        self.assertEqual(res.get("action"), "click")

    def test_list_running_apps(self):
        apps = self.cu.list_running_apps()
        self.assertIsInstance(apps, list)
        if apps:
            self.assertIsInstance(apps[0], str)

    def test_list_browser_profiles(self):
        """Verify list_browser_profiles scans and parses correctly."""
        profs = self.cu.list_browser_profiles()
        self.assertIsInstance(profs, list)
        if profs:
            p = profs[0]
            self.assertIn("folder", p)
            self.assertIn("name", p)
            self.assertIn("browser", p)

    def test_default_browser_profile_get_and_set(self):
        """Verify get and set of default browser profile."""
        old_val = self.cu.get_default_browser_profile()
        try:
            self.cu.set_default_browser_profile("Profile 2")
            self.assertEqual(self.cu.get_default_browser_profile(), "Profile 2")
            self.cu.set_default_browser_profile("ask")
            self.assertEqual(self.cu.get_default_browser_profile(), "ask")
        finally:
            if old_val:
                self.cu.set_default_browser_profile(old_val)
            else:
                os.environ.pop("CHROME_DEFAULT_PROFILE", None)

    @patch("subprocess.Popen")
    @patch("shutil.which", return_value="C:\\Program Files\\Google\\Chrome\\chrome.exe")
    def test_launch_browser_with_profile(self, mock_which, mock_popen):
        """Verify launch_browser uses --profile-directory flag correctly."""
        with patch.object(self.cu, "list_browser_profiles", return_value=[
            {"browser": "Google Chrome", "browser_cmd": "chrome", "folder": "Profile 1", "name": "Work", "email": "work@company.com"},
            {"browser": "Google Chrome", "browser_cmd": "chrome", "folder": "Default", "name": "Personal", "email": "me@gmail.com"}
        ]):
            ok, msg = self.cu.launch_browser("https://instagram.com", profile_query="Work")
            self.assertTrue(ok)
            self.assertIn("Profile 1", msg)
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertIn("--profile-directory=Profile 1", args)
            self.assertIn("https://instagram.com", args)

    def test_interactive_profile_prompt_in_execute(self):
        """Verify execute_computer_task prompts interactively when default is ask."""
        with patch.object(self.cu, "get_default_browser_profile", return_value="ask"), \
             patch.object(self.cu, "list_browser_profiles", return_value=[
                 {"browser": "Google Chrome", "folder": "Default", "name": "Asep Indra", "email": ""},
                 {"browser": "Google Chrome", "folder": "Profile 1", "name": "Niziiro", "email": ""}
             ]):
            result = self.cu.execute_computer_task("waifu tolong buka instagram")
            self.assertIn("profil browser", result)
            self.assertIn("Asep Indra", result)
            self.assertIn("Niziiro", result)


class TestCodingEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root_projects_dir = os.path.join(self.temp_dir, "projects")
        os.makedirs(self.root_projects_dir, exist_ok=True)
        self.data_dir = os.path.join(self.temp_dir, "data")

        self.old_env = os.environ.get("PROJECTS_DIR")
        os.environ["PROJECTS_DIR"] = self.root_projects_dir

        self.pm = ProjectManager(data_dir=self.data_dir, projects_dir=self.root_projects_dir)
        self.cu = ComputerUseEngine()
        self.ce = CodingEngine(project_manager=self.pm, computer_use_engine=self.cu)

    def tearDown(self):
        if self.old_env is not None:
            os.environ["PROJECTS_DIR"] = self.old_env
        else:
            os.environ.pop("PROJECTS_DIR", None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_intent_detection(self):
        # Coding intent
        self.assertTrue(self.ce.is_coding_intent("tolong buatkan file script python untuk scraping"))
        self.assertTrue(self.ce.is_coding_intent("bantu debug error syntax ini"))
        self.assertTrue(self.ce.is_coding_intent("tolong bikin index.html"))
        self.assertTrue(self.ce.is_coding_intent("run test unit test"))
        self.assertFalse(self.ce.is_coding_intent("kamu lagi ngapain hari ini sayang?"))

        # Computer use intent
        self.assertTrue(self.ce.is_computer_use_intent("tolong screenshot layar pc"))
        self.assertTrue(self.ce.is_computer_use_intent("bisa klik tombol start di desktop?"))
        self.assertTrue(self.ce.is_computer_use_intent("tolong buka aplikasi chrome"))
        self.assertTrue(self.ce.is_computer_use_intent("waifu buka instagram"))
        self.assertTrue(self.ce.is_computer_use_intent("tolong list profile chrome dong"))
        self.assertFalse(self.ce.is_computer_use_intent("ceritain dong tentang kuliahmu"))

    @patch("subprocess.run")
    def test_execute_task_in_project_cwd(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Task completed!\n<<<VOICE_REPLY>>>Sudah selesai kubuatkan scriptnya yaa!<<<END_VOICE_REPLY>>>"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        reply = self.ce.execute_task("buatkan file hello.py", user_id=1, voice_enabled=True)
        self.assertIn("Task completed!", reply)
        self.assertTrue(mock_run.called)

        # Test execute_coding_task returns both text and voice
        text, voice = self.ce.execute_coding_task(user_id=1, prompt="buatkan file hello.py", persona={"name": "Waifu"}, voice_enabled=True)
        self.assertEqual(text, "Task completed!")
        self.assertEqual(voice, "Sudah selesai kubuatkan scriptnya yaa!")

        # Ensure cwd was set to active project path
        active_path = self.pm.get_active_project_path(user_id=1)
        call_kwargs = mock_run.call_args[1]
        self.assertEqual(call_kwargs.get("cwd"), active_path)

    @patch("subprocess.run")
    @patch("routing_engine.get_hybrid_llm_client")
    def test_execute_coding_task_nonzero_returncode_falls_back_to_sfw_llm(self, mock_get_llm, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "AGY CLI auth failed"
        mock_run.return_value = mock_proc

        mock_client = MagicMock()
        mock_client.chat.return_value = ("Berikut perbaikan kodenya:\n```python\nprint('ok')\n```", None)
        mock_get_llm.return_value = mock_client

        with patch("shutil.which", return_value="agy"):
            text, _ = self.ce.execute_coding_task(user_id=1, prompt="perbaiki bug syntax main.py", persona={"name": "Waifu"})

        self.assertIn("SFW LLM", text)
        self.assertIn("print('ok')", text)
        mock_client.chat.assert_called_once()
        self.assertFalse(mock_client.chat.call_args[1].get("is_nsfw"))

    @patch("subprocess.run")
    @patch("project_server_manager.get_project_server_manager")
    def test_preview_trigger_ignores_false_positive_substrings(self, mock_get_psm, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Selesai!"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        with patch("shutil.which", return_value="agy"):
            # "bantuin" and "turun" contain "ui" and "run" substrings but must NOT trigger preview server
            self.ce.execute_coding_task(user_id=1, prompt="bantuin cek angka turun di utils.py", persona={"name": "Waifu"})
        mock_get_psm.return_value.start_preview_server.assert_not_called()

    def test_build_preview_url_buttons_localhost_and_tailscale(self):
        import bot
        with patch("project_server_manager.resolve_tailscale_url", return_value=("100.88.1.9", "http://100.88.1.9:8086/")):
            markup_dual = bot.build_preview_url_buttons(port=8086)
            urls = [btn.url for row in markup_dual.keyboard for btn in row]
            self.assertEqual(urls, ["http://127.0.0.1:8086/", "http://100.88.1.9:8086/"])

        with patch("project_server_manager.resolve_tailscale_url", return_value=(None, None)):
            markup_single = bot.build_preview_url_buttons(port=8086)
            urls_single = [btn.url for row in markup_single.keyboard for btn in row]
            self.assertEqual(urls_single, ["http://127.0.0.1:8086/"])

    def test_process_coding_request_attaches_dual_preview_voice_and_saves_history(self):
        import bot
        msg = MagicMock()
        msg.from_user.id = 999
        msg.chat.id = 999
        msg.message_id = 42

        preview_text = (
            "Web berhasil dibuat!\n\n🌐 **Live Web Preview (Port 8090):**\n"
            "💻 Localhost: [http://127.0.0.1:8090/](http://127.0.0.1:8090/)\n"
            "📱 Tailscale: [http://100.77.2.3:8090/](http://100.77.2.3:8090/)"
        )
        with patch.object(bot.coding_engine, "execute_coding_task", return_value=(preview_text, None)), \
             patch.object(bot, "send_long_chat_message") as mock_send_long, \
             patch.object(bot.persona_mgr, "add_message") as mock_add_msg, \
             patch.object(bot.bot, "reply_to"), \
             patch.object(bot.bot, "delete_message"), \
             patch.object(bot.pending_manager, "clear_pending"):
            bot.process_coding_request(msg, "buatkan landing page html", is_voice=False)

        mock_send_long.assert_called_once()
        markup = mock_send_long.call_args[1]["reply_markup"]
        all_btns = [btn for row in markup.keyboard for btn in row]
        urls = [getattr(b, "url", None) for b in all_btns if getattr(b, "url", None)]
        cbs = [getattr(b, "callback_data", "") or "" for b in all_btns]
        self.assertEqual(urls, ["http://127.0.0.1:8090/", "http://100.77.2.3:8090/"])
        self.assertTrue(any(cb.startswith("play_voice:") for cb in cbs))
        self.assertEqual(mock_add_msg.call_count, 2)


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

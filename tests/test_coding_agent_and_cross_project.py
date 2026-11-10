"""
test_coding_agent_and_cross_project.py - Unit tests for autonomous coding agent,
expanded intent detection, and cross-project memory contracts.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from coding_engine import get_coding_engine, diff_project_snapshots
from project_vault import ProjectVault, get_project_vault
from project_manager import ProjectManager


class TestCodingAgentAndCrossProject(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="waifu_coding_test_")
        self.proj_a = os.path.join(self.temp_dir, "app-frontend")
        self.proj_b = os.path.join(self.temp_dir, "be-backend")
        os.makedirs(self.proj_a, exist_ok=True)
        os.makedirs(self.proj_b, exist_ok=True)

        self.coding_engine = get_coding_engine()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_coding_intent_detection_expanded(self):
        """Verify natural language Indonesian and English coding requests are recognized."""
        test_queries_positive = [
            "tolong tambahkan fitur login dengan session",
            "coba kodingin navbar responsive",
            "benerin error di main.py",
            "bikin tombol submit dan form input",
            "perbaiki tampilan layout agar rapi",
            "buatkan halaman checkout",
            "pasang dependensi tailwindcss",
            "tulis script python untuk scrap data",
            "di project web tolong buat file api.py",
            "/code buatkan endpoint login",
            "/dev rapikan style css",
            "coding: implementasikan auth jwt"
        ]

        for q in test_queries_positive:
            self.assertTrue(
                self.coding_engine.is_coding_intent(q),
                f"Expected '{q}' to be recognized as coding intent!"
            )

        test_queries_negative = [
            "kamu lagi ngapain sayang?",
            "udah makan belum nih?",
            "foto kamu cantik banget ya",
            "mau bikin kopi dulu deh",
            "coba liat dong senyumnya"
        ]

        for q in test_queries_negative:
            self.assertFalse(
                self.coding_engine.is_coding_intent(q),
                f"Expected '{q}' to NOT be recognized as coding intent!"
            )

    def test_contextual_project_intent_detection(self):
        """When user is in an active project workspace, broader technical tasks are caught."""
        mock_pm = MagicMock()
        mock_pm.get_active_project.return_value = "app-frontend"
        engine = get_coding_engine()
        engine.project_manager = mock_pm

        self.assertTrue(engine.is_coding_intent("ganti warna background jadi dark mode", user_id=123))
        self.assertTrue(engine.is_coding_intent("lanjutkan kodingan kemarin", user_id=123))

    def test_snapshot_diff(self):
        """Verify diff_project_snapshots accurately detects created and modified files."""
        before = {
            "index.html": 100.0,
            "style.css": 100.0
        }
        after = {
            "index.html": 105.0,  # modified
            "style.css": 100.0,   # unchanged
            "app.js": 102.0       # created
        }

        created, modified = diff_project_snapshots(before, after)
        self.assertEqual(created, ["app.js"])
        self.assertEqual(modified, ["index.html"])

    def test_cross_project_enriched_context(self):
        """Verify Project A automatically extracts tech stack & contract from related Project B."""
        vault_b = ProjectVault(project_path=self.proj_b, project_name="be-backend")
        vault_b.update_architecture_info(
            tech_stack=["Python", "FastAPI"],
            framework="FastAPI",
            database="PostgreSQL",
            summary="REST API menyediakan endpoint /api/v1/auth dan /api/v1/menu di port 8000"
        )

        vault_a = ProjectVault(project_path=self.proj_a, project_name="app-frontend")
        vault_a.update_architecture_info(
            tech_stack=["React", "Vite"],
            framework="React",
            summary="Frontend SPA cafe booking"
        )
        vault_a.add_relation(target_project="be-backend", relation_type="backend_api", description="Backend API service")

        # Mock project_manager.list_projects so vault_a can locate vault_b
        with patch("project_manager.get_project_manager") as mock_get_pm:
            mock_pm = MagicMock()
            mock_pm.list_projects.return_value = {
                "app-frontend": self.proj_a,
                "be-backend": self.proj_b
            }
            mock_get_pm.return_value = mock_pm

            context_a = vault_a.get_prompt_context()

            # Verify Project A context contains its own details
            self.assertIn("APP-FRONTEND", context_a)
            self.assertIn("React", context_a)

            # Verify Project A context contains related Project B contract
            self.assertIn("CROSS-PROJECT RELATIONS", context_a)
            self.assertIn("be-backend", context_a)
            self.assertIn("FastAPI", context_a)
            self.assertIn("PostgreSQL", context_a)
            self.assertIn("/api/v1/auth", context_a)

    def test_bot_code_and_link_project_handlers(self):
        """Verify bot /code and /link_project commands execute properly."""
        import bot
        mock_msg = MagicMock()
        mock_msg.from_user.id = 12345
        mock_msg.chat.id = 12345

        # 1. /code with prompt
        mock_msg.text = "/code buatkan tombol login"
        with patch.object(bot, "is_authorized", return_value=True), \
             patch.object(bot, "process_coding_request") as mock_proc_code:
            bot.handle_code_command(mock_msg)
            mock_proc_code.assert_called_once_with(mock_msg, "buatkan tombol login", is_voice=False)

        # 2. /code without prompt shows usage
        mock_msg.text = "/code"
        with patch.object(bot, "is_authorized", return_value=True), \
             patch.object(bot.bot, "reply_to") as mock_reply:
            bot.handle_code_command(mock_msg)
            self.assertIn("Mode Coding", mock_reply.call_args[0][1])

        # 3. /link_project adds relation
        mock_msg.text = "/link_project be-cafe-fix backend api port 8000"
        with patch.object(bot, "is_authorized", return_value=True), \
             patch.object(bot.project_manager, "get_active_project", return_value="app-frontend"), \
             patch.object(bot.project_manager, "get_active_project_path", return_value=self.proj_a), \
             patch.object(bot.bot, "reply_to") as mock_reply:
            bot.handle_link_project_command(mock_msg)
            self.assertIn("Relasi Project Berhasil Dihubungkan", mock_reply.call_args[0][1])
            vault = get_project_vault(self.proj_a, "app-frontend")
            data = vault.load_memory()
            targets = [r["target_project"] for r in data.get("relations", [])]
            self.assertIn("be-cafe-fix", targets)


if __name__ == "__main__":
    unittest.main()


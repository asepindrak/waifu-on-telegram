"""
test_project_awareness_and_memory.py - Test Suite for Conversational Project Awareness,
Memory Vault Isolation, ARCHITECTURE.md generation, and God-View Coordination.
"""

import os
import json
import shutil
import tempfile
import unittest

from project_vault import ProjectVault, get_project_vault
from architecture_generator import ArchitectureGenerator, ensure_project_architecture
from project_manager import ProjectManager
from project_intent_router import ProjectIntentRouter, ProjectIntentResult


class TestProjectAwarenessAndMemory(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="waifu_test_proj_")
        self.projects_root = os.path.join(self.test_dir, "projects")
        self.data_dir = os.path.join(self.test_dir, "data")
        os.makedirs(self.projects_root, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        self.pm = ProjectManager(data_dir=self.data_dir, projects_dir=self.projects_root)
        self.router = ProjectIntentRouter(project_manager=self.pm)

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_project_vault_isolation_and_tasks(self):
        """Verify project memory vault stores tasks and stays isolated."""
        proj_a_dir = os.path.join(self.projects_root, "billing-service")
        proj_b_dir = os.path.join(self.projects_root, "auth-service")
        os.makedirs(proj_a_dir, exist_ok=True)
        os.makedirs(proj_b_dir, exist_ok=True)

        vault_a = ProjectVault(proj_a_dir, "billing-service")
        vault_b = ProjectVault(proj_b_dir, "auth-service")

        # Add tasks to Vault A
        vault_a.add_completed_task("Setup Stripe Webhook listener", files_touched=["webhooks/stripe.py"])
        vault_a.add_pending_task("Implement PDF Invoice download", priority="high")

        # Add different tasks to Vault B
        vault_b.add_completed_task("Implement OAuth2 JWT verification", files_touched=["auth/jwt.py"])

        mem_a = vault_a.load_memory()
        mem_b = vault_b.load_memory()

        # Check isolation
        self.assertEqual(len(mem_a["tasks"]["completed"]), 1)
        self.assertEqual(mem_a["tasks"]["completed"][0]["description"], "Setup Stripe Webhook listener")
        self.assertEqual(len(mem_a["tasks"]["pending"]), 1)
        self.assertEqual(mem_a["tasks"]["pending"][0]["description"], "Implement PDF Invoice download")

        self.assertEqual(len(mem_b["tasks"]["completed"]), 1)
        self.assertEqual(mem_b["tasks"]["completed"][0]["description"], "Implement OAuth2 JWT verification")
        self.assertEqual(len(mem_b["tasks"]["pending"]), 0)

        # Prompt context generation check
        ctx_a = vault_a.get_prompt_context()
        self.assertIn("BILLING-SERVICE", ctx_a)
        self.assertIn("Setup Stripe Webhook listener", ctx_a)
        self.assertIn("Implement PDF Invoice download", ctx_a)

    def test_hierarchical_memory_compaction(self):
        """Verify 3-tier memory compaction preserves history into milestones without data loss."""
        proj_dir = os.path.join(self.projects_root, "erp-core")
        os.makedirs(proj_dir, exist_ok=True)
        vault = ProjectVault(proj_dir, "erp-core")

        # Add 15 tasks
        for i in range(1, 16):
            vault.add_completed_task(f"Task #{i}: Implemented subfeature {i}", auto_compact=False)

        mem_before = vault.load_memory()
        self.assertEqual(len(mem_before["tasks"]["completed"]), 15)
        self.assertEqual(len(mem_before["compacted_milestones"]), 0)

        # Compact memory retaining 5 recent
        ok, summary = vault.compact_memory(retain_recent=5, force=True)
        self.assertTrue(ok)
        self.assertIn("Milestone", summary)

        mem_after = vault.load_memory()
        self.assertEqual(len(mem_after["tasks"]["completed"]), 5)
        self.assertEqual(len(mem_after["compacted_milestones"]), 1)
        self.assertEqual(mem_after["context_stats"]["compact_count"], 1)

        # Context still retains milestone and recent tasks
        ctx = vault.get_prompt_context()
        self.assertIn("HISTORICAL COMPACTED MILESTONES", ctx)
        self.assertIn("Task #15", ctx)

    def test_architecture_generator_and_mermaid(self):
        """Verify ArchitectureGenerator analyzes manifests and outputs ARCHITECTURE.md."""
        proj_dir = os.path.join(self.projects_root, "frontend-app")
        os.makedirs(proj_dir, exist_ok=True)

        # Create simulated package.json
        pkg_json = {
            "name": "frontend-app",
            "dependencies": {
                "next": "^14.0.0",
                "react": "^18.0.0",
                "prisma": "^5.0.0",
                "pg": "^8.0.0"
            }
        }
        with open(os.path.join(proj_dir, "package.json"), "w", encoding="utf-8") as f:
            json.dump(pkg_json, f)

        # Ensure architecture
        ok, arch_file, analysis = ensure_project_architecture(proj_dir, "frontend-app", force=True)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(arch_file))

        self.assertIn("Next.js", analysis["frameworks"])
        self.assertIn("Prisma ORM", analysis["databases"])

        with open(arch_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Architecture Blueprint: FRONTEND-APP", content)
        self.assertIn("flowchart TD", content)
        self.assertIn("Next.js", content)

    def test_conversational_project_intent_routing(self):
        """Verify conversational routing detects switch, create, status, and god-view."""
        user_id = 999
        # Spawn two projects
        self.pm.spawn_project("pos-system", switch_user_id=user_id)
        self.pm.spawn_project("inventory-hub")

        # 1. Switch project intent
        res_switch = self.router.route_intent("Akira, tolong switch ke project inventory-hub yaa", user_id=user_id)
        self.assertEqual(res_switch.intent_type, "SWITCH")
        self.assertEqual(res_switch.target_project, "inventory-hub")

        # Execute switch
        ok, msg = self.router.handle_project_intent(res_switch, user_id=user_id)
        self.assertTrue(ok)
        self.assertEqual(self.pm.get_active_project(user_id), "inventory-hub")
        self.assertIn("inventory-hub", msg)

        # 2. God view intent
        res_god = self.router.route_intent("Akira, tampilkan god view semua project kita dong", user_id=user_id)
        self.assertEqual(res_god.intent_type, "GOD_VIEW")
        ok, god_msg = self.router.handle_project_intent(res_god, user_id=user_id)
        self.assertTrue(ok)
        self.assertIn("God View Dashboard", god_msg)
        self.assertIn("inventory-hub", god_msg)
        self.assertIn("pos-system", god_msg)

        # 3. Status intent
        res_status = self.router.route_intent("Gimana status dan progres project ini?", user_id=user_id)
        self.assertEqual(res_status.intent_type, "STATUS")
        ok, status_msg = self.router.handle_project_intent(res_status, user_id=user_id)
        self.assertTrue(ok)
        self.assertIn("Status & Memory Vault", status_msg)

        # 4. Add To-Do intent
        res_todo = self.router.route_intent("Catat to do: integrasi barcode scanner", user_id=user_id)
        self.assertEqual(res_todo.intent_type, "ADD_TODO")
        self.assertEqual(res_todo.extracted_task, "integrasi barcode scanner")
        ok, todo_msg = self.router.handle_project_intent(res_todo, user_id=user_id)
        self.assertTrue(ok)
        self.assertIn("integrasi barcode scanner", todo_msg)

        # 5. Cross-project relation (ERP multi-module)
        res_rel = self.router.route_intent("Project pos-system ada relasi ke inventory-hub", user_id=user_id)
        self.assertEqual(res_rel.intent_type, "ADD_RELATION")
        self.assertEqual(res_rel.target_project, "pos-system")
        self.assertEqual(res_rel.relation_target, "inventory-hub")
        ok, rel_msg = self.router.handle_project_intent(res_rel, user_id=user_id)
        self.assertTrue(ok)
        self.assertIn("Relasi Antar-Project Terhubung", rel_msg)

        # 6. Create new project intent
        res_create = self.router.route_intent("Buat project baru crm-mobile dong", user_id=user_id)
        self.assertEqual(res_create.intent_type, "CREATE")
        self.assertEqual(res_create.target_project, "crm-mobile")
        ok, create_msg = self.router.handle_project_intent(res_create, user_id=user_id)
        self.assertTrue(ok)
        self.assertEqual(self.pm.get_active_project(user_id), "crm-mobile")
        self.assertIn("crm-mobile", create_msg)


if __name__ == "__main__":
    unittest.main()

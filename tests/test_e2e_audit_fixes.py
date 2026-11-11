import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_ID", "6402709138")

import bot
import health_engine
import idle_engine
import setup


class TestE2EAuditFixes(unittest.TestCase):
    def test_package_json_matches_version_file(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "VERSION"), "r", encoding="utf-8") as f:
            ver = f.read().strip()
        with open(os.path.join(root, "package.json"), "r", encoding="utf-8") as f:
            pkg = json.load(f)
        self.assertEqual(pkg.get("version"), ver)

    def test_install_sh_balanced_if_fi_blocks(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "install.sh"), "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        depth = 0
        for lineno, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("if ") or stripped == "if":
                depth += 1
            elif stripped == "else" or stripped.startswith("elif "):
                self.assertGreater(depth, 0, f"Unmatched '{stripped}' at install.sh:{lineno}")
            elif stripped == "fi":
                depth -= 1
                self.assertGreaterEqual(depth, 0, f"Extra 'fi' at install.sh:{lineno}")
        self.assertEqual(depth, 0, "Unclosed 'if' block in install.sh")

    def test_setup_is_bot_running_checks_bot_pid_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bot_pid = os.path.join(tmpdir, "bot.pid")
            with open(bot_pid, "w", encoding="utf-8") as f:
                f.write("42424")
            with patch.object(setup, "SCRIPT_DIR", tmpdir), \
                 patch("subprocess.run", return_value=MagicMock(stdout="python.exe   42424 Console")), \
                 patch("os.kill", return_value=None):
                self.assertEqual(setup.is_bot_running(), 42424)

    def test_dynamic_vn_reaction_works_on_agy_port_8001_when_5001_offline(self):
        mock_client = MagicMock()
        mock_client.is_split_mode.return_value = True
        mock_sfw = MagicMock()
        mock_sfw.base_url = "http://127.0.0.1:8001/v1"
        mock_sfw.api_key = "sk-agy-test"
        mock_client.sfw_client = mock_sfw
        mock_client.chat.return_value = (
            "*Runa tersenyum hangat sambil menoleh padamu*\n\nWah seru banget ceritanya, lanjutin dong!",
            18,
        )

        with patch("bot.is_port_listening", side_effect=lambda port, **kw: port == 8001):
            reply = bot.generate_dynamic_visual_novel_reaction(
                "hari ini cuacanya cerah",
                persona_name="Runa",
                llm_client=mock_client,
                is_nsfw=False,
            )

        mock_client.chat.assert_called_once()
        self.assertIn("seru banget", reply)

    def test_idle_engine_split_agy_checks_port_8001_without_sleeping_comfyui(self):
        engine = idle_engine.IdleEngine(enabled=True)
        with patch.dict(os.environ, {"AI_ENGINE_MODE": "split", "SFW_LLM_PROVIDER": "agy", "SFW_LLM_BASE_URL": "http://127.0.0.1:8001/v1"}, clear=False), \
             patch.object(engine, "_prepare_vram_for_llm") as mock_prep, \
             patch.object(engine, "is_llm_ready", return_value=False), \
             patch.object(engine, "wake_agy_bridge", return_value=True) as mock_wake_agy:
            self.assertFalse(engine.ensure_llm_active(is_user_chat=False, is_nsfw=False))
            mock_wake_agy.assert_not_called()

            self.assertTrue(engine.ensure_llm_active(is_user_chat=True, is_nsfw=False))
            mock_wake_agy.assert_called_once()
            mock_prep.assert_not_called()

    def test_health_engine_split_agy_and_local_nsfw_heals_without_double_5001(self):
        mock_client = MagicMock()
        mock_client.base_url = "http://127.0.0.1:8001/v1"
        mock_client.nsfw_client = MagicMock(base_url="http://127.0.0.1:5001/v1")
        he = health_engine.HealthEngine(llm_client=mock_client)

        calls = []

        def fake_port(port, timeout=1.0):
            calls.append(port)
            return False

        with patch.dict(os.environ, {"AI_ENGINE_MODE": "split", "SFW_LLM_PROVIDER": "agy", "NSFW_LLM_PROVIDER": "local"}, clear=False), \
             patch("health_engine.is_port_listening", side_effect=fake_port), \
             patch.object(he, "heal_agy", return_value=True) as mock_agy, \
             patch.object(he, "_heal_koboldcpp_instance", return_value=True) as mock_kcpp:
            ok = he.heal_llm()
            self.assertTrue(ok)
            mock_agy.assert_called_once()
            mock_kcpp.assert_called_once()
            self.assertEqual(calls, [8001, 5001])


if __name__ == "__main__":
    unittest.main()


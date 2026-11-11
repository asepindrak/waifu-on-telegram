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

    def test_detect_hardware_profile_uses_winreg_qwmemorysize_above_4gb(self):
        import asset_manager
        import media_engine as _me

        fake_dev_key = MagicMock()
        fake_cls_key = MagicMock()
        fake_dev_cm = MagicMock(__enter__=MagicMock(return_value=fake_dev_key), __exit__=MagicMock(return_value=False))
        fake_cls_cm = MagicMock(__enter__=MagicMock(return_value=fake_cls_key), __exit__=MagicMock(return_value=False))

        six_gb_bytes = 6 * 1024 * 1024 * 1024

        def fake_query(key, name):
            if name == "HardwareInformation.qwMemorySize":
                return (six_gb_bytes.to_bytes(8, "little"), 3)
            if name == "DriverDesc":
                return ("NVIDIA GeForce RTX 3050 Laptop GPU", 1)
            raise OSError("missing")

        with patch("asset_manager.subprocess.check_output", side_effect=FileNotFoundError("no smi")), \
             patch("sys.platform", "win32"), \
             patch("winreg.OpenKey", side_effect=[fake_cls_cm, fake_dev_cm]), \
             patch("winreg.EnumKey", side_effect=["0000", OSError("end")]), \
             patch("winreg.QueryValueEx", side_effect=fake_query):
            prof = asset_manager.detect_hardware_profile(refresh=True)
            self.assertEqual(prof["source"], "win32_registry_qw")
            self.assertEqual(prof["vram_mb"], 6144)
            self.assertEqual(prof["vram_gb"], 6.0)
            self.assertEqual(prof["tier"], "mid")
            self.assertEqual(prof["recommended_llm_layers"], 24)
        asset_manager.detect_hardware_profile(refresh=True)

    def test_idle_engine_unified_with_sfw_agy_routes_sfw_to_8001_and_nsfw_to_5001(self):
        engine = idle_engine.IdleEngine(enabled=True)
        env = {
            "AI_ENGINE_MODE": "unified",
            "LLM_BASE_URL": "http://127.0.0.1:5001/v1",
            "SFW_LLM_PROVIDER": "agy",
            "SFW_LLM_BASE_URL": "http://127.0.0.1:8001/v1",
            "NSFW_LLM_PROVIDER": "local",
            "NSFW_LLM_BASE_URL": "http://127.0.0.1:5001/v1",
        }
        with patch.dict(os.environ, env, clear=False):
            p_sfw, url_sfw, _ = engine._resolve_llm_target(is_nsfw=False)
            p_nsfw, url_nsfw, _ = engine._resolve_llm_target(is_nsfw=True)
            self.assertEqual(p_sfw, "agy")
            self.assertIn(":8001", url_sfw)
            self.assertEqual(p_nsfw, "local")
            self.assertIn(":5001", url_nsfw)

    def test_media_engine_checkpoint_respects_unified_vs_split_mode(self):
        import media_engine
        me = media_engine.MediaEngine()
        env_unified = {
            "IMAGE_ENGINE_MODE": "unified",
            "COMFYUI_CHECKPOINT": "AnythingXL_xl.safetensors",
            "SFW_COMFYUI_CHECKPOINT": "meinamix_v12Final.safetensors",
            "NSFW_COMFYUI_CHECKPOINT": "AOM3A1B_orangemixs.safetensors",
        }
        with patch.object(me, "get_available_checkpoints", return_value=[]), \
             patch.dict(os.environ, env_unified, clear=False):
            self.assertEqual(me.get_active_checkpoint(is_nude=False), "AnythingXL_xl.safetensors")
            self.assertEqual(me.get_active_checkpoint(is_nude=True), "AnythingXL_xl.safetensors")

        with patch.object(me, "get_available_checkpoints", return_value=[]), \
             patch.dict(os.environ, {**env_unified, "IMAGE_ENGINE_MODE": "split"}, clear=False):
            self.assertEqual(me.get_active_checkpoint(is_nude=False), "meinamix_v12Final.safetensors")
            self.assertEqual(me.get_active_checkpoint(is_nude=True), "AOM3A1B_orangemixs.safetensors")

    def test_apply_llm_choice_agy_updates_both_unified_and_sfw_vars(self):
        orig_base = bot.LLM_BASE_URL
        orig_env = {k: os.environ.get(k) for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "SFW_LLM_PROVIDER", "SFW_LLM_BASE_URL", "SFW_LLM_MODEL", "SFW_LLM_API_KEY")}
        try:
            with patch("bot.update_env_variable") as mock_upd, \
                 patch("bot.get_hybrid_llm_client"):
                label = bot.apply_llm_choice("agy")
                self.assertIn("AGY", label)
                mock_upd.assert_any_call("LLM_BASE_URL", "http://127.0.0.1:8001/v1")
                mock_upd.assert_any_call("SFW_LLM_PROVIDER", "agy")
                mock_upd.assert_any_call("SFW_LLM_BASE_URL", "http://127.0.0.1:8001/v1")
        finally:
            bot.LLM_BASE_URL = orig_base
            for k, v in orig_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_health_engine_heal_llm_nsfw_in_unified_agy_targets_koboldcpp(self):
        mock_cli = MagicMock()
        mock_cli.base_url = "http://127.0.0.1:8001/v1"
        he = health_engine.HealthEngine(llm_client=mock_cli, enabled=False)
        env = {
            "AI_ENGINE_MODE": "unified",
            "SFW_LLM_PROVIDER": "agy",
            "NSFW_LLM_PROVIDER": "local",
            "NSFW_LLM_BASE_URL": "http://127.0.0.1:5001/v1",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch.object(he, "_heal_koboldcpp_instance", return_value=True) as mock_kcpp, \
             patch.object(he, "heal_agy", return_value=True) as mock_agy:
            ok = he.heal_llm(is_nsfw=True)
            self.assertTrue(ok)
            mock_kcpp.assert_called_once()
            mock_agy.assert_not_called()

    def test_idle_engine_unified_agy_nsfw_falls_back_to_8001_when_5001_unavailable(self):
        engine = idle_engine.IdleEngine(enabled=True)
        env = {
            "AI_ENGINE_MODE": "unified",
            "LLM_BASE_URL": "http://127.0.0.1:8001/v1",
            "SFW_LLM_PROVIDER": "agy",
            "SFW_LLM_BASE_URL": "http://127.0.0.1:8001/v1",
            "NSFW_LLM_PROVIDER": "local",
            "NSFW_LLM_BASE_URL": "http://127.0.0.1:5001/v1",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch("idle_engine.is_port_listening", side_effect=lambda p, timeout=1.0: p == 8001), \
             patch.object(engine, "wake_llm", return_value=False):
            ok = engine.ensure_llm_active(is_user_chat=True, is_nsfw=True)
            self.assertTrue(ok)

    def test_idle_engine_comfyui_does_not_sleep_llm_when_comfyui_not_installed(self):
        engine = idle_engine.IdleEngine(enabled=True)
        with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144}), \
             patch("asset_manager.detect_comfyui_dir", return_value=None), \
             patch.object(engine, "is_comfyui_ready", return_value=False), \
             patch.object(engine, "sleep_llm") as mock_sleep_llm, \
             patch.dict(os.environ, {"VRAM_EXCLUSIVE_SWAP": "auto", "SFW_IMAGE_ENGINE": "comfyui"}, clear=False):
            ok = engine.ensure_comfyui_active(is_nude=False)
            self.assertFalse(ok)
            mock_sleep_llm.assert_not_called()


if __name__ == "__main__":
    unittest.main()


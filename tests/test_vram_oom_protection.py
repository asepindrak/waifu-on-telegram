import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import asset_manager
import idle_engine
import health_engine
import media_engine


class TestVramOomProtection(unittest.TestCase):
    """Verifies automatic VRAM protection, --lowvram, /free cleanup, and GPU layer caps for 6GB GPUs."""

    def test_comfyui_launch_spec_auto_lowvram_on_6gb_gpu(self):
        """ComfyUI auto-enables --lowvram on <= 6.5 GB GPUs (e.g., RTX 3050 6GB) and omits it on 12GB."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_portable = os.path.join(tmp_dir, "tools", "ComfyUI", "ComfyUI_windows_portable")
            fake_comfy = os.path.join(fake_portable, "ComfyUI")
            os.makedirs(os.path.join(fake_comfy, "models"), exist_ok=True)
            with open(os.path.join(fake_comfy, "main.py"), "w") as f:
                f.write("# dummy")
            fake_py_dir = os.path.join(fake_portable, "python_embeded")
            os.makedirs(fake_py_dir, exist_ok=True)
            with open(os.path.join(fake_py_dir, "python.exe"), "w") as f:
                f.write("# dummy py")

            clean_env = os.environ.copy()
            clean_env.pop("COMFYUI_CPU", None)

            with patch.object(asset_manager, "PROJECT_ROOT", tmp_dir), \
                 patch.object(asset_manager, "detect_comfyui_dir", return_value=fake_comfy), \
                 patch.object(asset_manager, "_COMFYUI_FORCE_CPU", False), \
                 patch("asset_manager.check_and_repair_comfyui_environment"):

                with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144}):
                    with patch.dict(os.environ, {**clean_env, "COMFYUI_VRAM_MODE": "auto"}, clear=True):
                        spec_6gb = asset_manager.get_comfyui_launch_spec()
                        self.assertIsNotNone(spec_6gb)
                        self.assertIn("--lowvram", spec_6gb["cmd"])
                        self.assertIn("--fast", spec_6gb["cmd"])

                with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 12288}):
                    with patch.dict(os.environ, {**clean_env, "COMFYUI_VRAM_MODE": "auto"}, clear=True):
                        spec_12gb = asset_manager.get_comfyui_launch_spec()
                        self.assertIsNotNone(spec_12gb)
                        self.assertNotIn("--lowvram", spec_12gb["cmd"])

                with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144}):
                    with patch.dict(os.environ, {**clean_env, "COMFYUI_VRAM_MODE": "medvram"}, clear=True):
                        spec_override = asset_manager.get_comfyui_launch_spec()
                        self.assertIn("--medvram", spec_override["cmd"])
                        self.assertNotIn("--lowvram", spec_override["cmd"])

    def test_health_engine_legacy_fallback_respects_6gb_recommended_layers(self):
        """Legacy heal_llm fallback must NOT hardcode --gpulayers 99 on a 6GB GPU."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.makedirs(os.path.join(tmp_dir, "tools"), exist_ok=True)
            os.makedirs(os.path.join(tmp_dir, "models"), exist_ok=True)
            exe_name = "koboldcpp.exe" if os.sys.platform == "win32" else "koboldcpp"
            with open(os.path.join(tmp_dir, "tools", exe_name), "w") as f:
                f.write("bin")
            with open(os.path.join(tmp_dir, "models", "Huihui-Qwythos-9B-Q4_K.gguf"), "w") as f:
                f.write("gguf")

            mock_llm = MagicMock()
            mock_llm.base_url = "http://127.0.0.1:5001/v1"
            mock_llm.check_health.return_value = {"online": True}
            he = health_engine.HealthEngine(llm_client=mock_llm, project_root=tmp_dir)
            with patch("asset_manager.get_llm_launch_spec", return_value=None), \
                 patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144, "recommended_llm_layers": 24}), \
                 patch("health_engine.get_koboldcpp_process_count", return_value=0), \
                 patch("health_engine.is_port_listening", side_effect=[False, True]), \
                 patch("subprocess.Popen") as mock_popen:
                env_clean = os.environ.copy()
                env_clean.pop("LLM_GPU_LAYERS", None)
                env_clean.pop("SFW_LLM_PROVIDER", None)
                env_clean.pop("AI_ENGINE_MODE", None)
                with patch.dict(os.environ, env_clean, clear=True):
                    ok = he.heal_llm()
                    self.assertTrue(ok)
                    self.assertTrue(mock_popen.called)
                    cmd = mock_popen.call_args[0][0]
                    idx = cmd.index("--gpulayers")
                    self.assertEqual(cmd[idx + 1], "24")
                    self.assertNotEqual(cmd[idx + 1], "99")

    def test_idle_engine_exclusive_vram_swap_on_6gb_gpu(self):
        """On <= 6.5 GB GPU, activating ComfyUI sleeps KoboldCPP and activating local LLM sleeps ComfyUI."""
        engine = idle_engine.IdleEngine(enabled=True, idle_timeout_minutes=120, comfyui_on_demand=True)

        # 1. Switching from local KoboldCPP chat -> ComfyUI image must sleep KoboldCPP first
        with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144}), \
             patch("idle_engine.is_port_listening", side_effect=lambda p: p == 5001), \
             patch.object(engine, "sleep_llm", return_value=True) as mock_sleep_llm, \
             patch.object(engine, "is_comfyui_ready", return_value=True), \
             patch.dict(os.environ, {"VRAM_EXCLUSIVE_SWAP": "auto", "SFW_IMAGE_ENGINE": "comfyui"}):
            ok = engine.ensure_comfyui_active(is_nude=False)
            self.assertTrue(ok)
            mock_sleep_llm.assert_called_once()

        # 2. AGY image must NOT sleep KoboldCPP
        with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144}), \
             patch("idle_engine.is_port_listening", return_value=True), \
             patch.object(engine, "sleep_llm") as mock_sleep_llm, \
             patch.dict(os.environ, {"VRAM_EXCLUSIVE_SWAP": "auto", "SFW_IMAGE_ENGINE": "agy"}):
            ok = engine.ensure_comfyui_active(is_nude=False)
            self.assertTrue(ok)
            mock_sleep_llm.assert_not_called()

        # 3. Switching from ComfyUI -> local KoboldCPP chat must sleep ComfyUI first
        with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144}), \
             patch("idle_engine.is_port_listening", side_effect=lambda p: p == 8188), \
             patch.object(engine, "sleep_comfyui", return_value=True) as mock_sleep_comfy, \
             patch.object(engine, "is_llm_ready", return_value=True), \
             patch.dict(os.environ, {"VRAM_EXCLUSIVE_SWAP": "auto", "AI_ENGINE_MODE": "unified", "SFW_LLM_PROVIDER": "local", "SFW_LLM_BASE_URL": "http://127.0.0.1:5001/v1", "LLM_BASE_URL": "http://127.0.0.1:5001/v1"}):
            ok = engine.ensure_llm_active(is_user_chat=True, is_nsfw=False)
            self.assertTrue(ok)
            mock_sleep_comfy.assert_called_once()

        # 4. Cloud/AGY SFW LLM must NOT sleep ComfyUI
        with patch("asset_manager.detect_hardware_profile", return_value={"vram_mb": 6144}), \
             patch("idle_engine.is_port_listening", side_effect=lambda p: p == 8188), \
             patch.object(engine, "sleep_comfyui") as mock_sleep_comfy, \
             patch.dict(os.environ, {"VRAM_EXCLUSIVE_SWAP": "auto", "AI_ENGINE_MODE": "split", "SFW_LLM_PROVIDER": "openai"}):
            ok = engine.ensure_llm_active(is_user_chat=True, is_nsfw=False)
            self.assertTrue(ok)
            mock_sleep_comfy.assert_not_called()

    def test_comfyui_frees_vram_after_image_generation(self):
        """MediaEngine calls ComfyUI /free endpoint after image rendering to release model weights."""
        engine = media_engine.MediaEngine()
        with patch.object(engine, "get_available_checkpoints", return_value=["AOM3A1B_orangemixs.safetensors"]), \
             patch.object(engine, "get_available_vaes", return_value=[]), \
             patch("requests.post") as mock_post, \
             patch("requests.get") as mock_get:
            mock_post.return_value = MagicMock(status_code=200, json=lambda: {"prompt_id": "vram-free-1"})
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {
                "vram-free-1": {
                    "outputs": {"9": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}}
                }
            }, content=b"img_bytes")

            res = engine.generate_image_comfyui(prompt="1girl, cute anime girl")
            self.assertEqual(res, b"img_bytes")
            free_calls = [c for c in mock_post.call_args_list if c[0][0].endswith("/free")]
            self.assertEqual(len(free_calls), 1)
            self.assertEqual(free_calls[0][1]["json"], {"unload_models": True, "free_memory": True})

    def test_launcher_scripts_do_not_hardcode_99_gpu_layers(self):
        """Startup scripts should resolve dynamic/env GPU layers instead of hardcoding --gpulayers 99."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for script_name in ("start_services.bat", "start_services_silent.vbs", "start_services.sh"):
            with open(os.path.join(root, script_name), "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("--gpulayers 99", content, f"{script_name} still hardcodes --gpulayers 99")


if __name__ == "__main__":
    unittest.main()

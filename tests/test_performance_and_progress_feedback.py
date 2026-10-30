import unittest
import os
import sys
from unittest.mock import patch, MagicMock

import media_engine
import idle_engine
import asset_manager

class TestPerformanceAndProgressFeedback(unittest.TestCase):
    """Verifies SDXL optimizations, KoboldCPP bounded context parameters, and progress feedback."""

    def test_sdxl_quality_params_and_safe_vae(self):
        """Verifies SDXL settings are optimized to prevent freezing and slow CPU offloading."""
        # SDXL optimal presets
        fast_steps, fast_cfg = media_engine.MediaEngine.get_quality_params("fast", is_sdxl=True)
        high_steps, high_cfg = media_engine.MediaEngine.get_quality_params("high", is_sdxl=True)
        ultra_steps, ultra_cfg = media_engine.MediaEngine.get_quality_params("ultra", is_sdxl=True)

        self.assertEqual((fast_steps, fast_cfg), (18, 5.5))
        self.assertEqual((high_steps, high_cfg), (22, 6.0))
        self.assertEqual((ultra_steps, ultra_cfg), (26, 6.5))

        # SD 1.5 presets should remain intact
        sd_fast_steps, sd_fast_cfg = media_engine.MediaEngine.get_quality_params("fast", is_sdxl=False)
        sd_high_steps, sd_high_cfg = media_engine.MediaEngine.get_quality_params("high", is_sdxl=False)
        self.assertEqual((sd_fast_steps, sd_fast_cfg), (20, 7.0))
        self.assertEqual((sd_high_steps, sd_high_cfg), (28, 7.5))

    def test_sdxl_does_not_use_sd15_vae(self):
        """Ensure external SD 1.5 VAEs (e.g. orangemix.vae.pt) are excluded when generating with SDXL."""
        engine = media_engine.MediaEngine()
        with patch.object(engine, "get_available_checkpoints", return_value=["AnythingXL_xl.safetensors"]), \
             patch.object(engine, "get_available_vaes", return_value=["orangemix.vae.pt", "anime.vae.pt"]), \
             patch("requests.post") as mock_post:
            
            mock_post.return_value = MagicMock(status_code=200, json=lambda: {"prompt_id": "test-prompt-123"})
            with patch("requests.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200, json=lambda: {
                    "test-prompt-123": {
                        "outputs": {"9": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}}
                    }
                }, content=b"fake_image_bytes")

                img = engine.generate_image_comfyui(prompt="cute girl smiling")
                self.assertIsNotNone(img)

                # Verify workflow posted does NOT contain VAELoader for SD 1.5 VAE
                posted_json = mock_post.call_args[1]["json"]
                workflow = posted_json["prompt"]
                self.assertNotIn("10", workflow)
                self.assertEqual(workflow["8"]["inputs"]["vae"], ["4", 2])

    def test_generate_image_comfyui_progress_callback(self):
        """Verifies progress_callback is called during polling."""
        engine = media_engine.MediaEngine()
        callback_stages = []

        def cb(msg):
            callback_stages.append(msg)

        with patch.object(engine, "get_available_checkpoints", return_value=["meinamix_v12Final.safetensors"]), \
             patch("requests.post") as mock_post:
            
            mock_post.return_value = MagicMock(status_code=200, json=lambda: {"prompt_id": "cb-test-123"})
            with patch("requests.get") as mock_get:
                mock_get.return_value = MagicMock(status_code=200, json=lambda: {
                    "cb-test-123": {
                        "outputs": {"9": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}}
                    }
                }, content=b"image_result")

                img = engine.generate_image_comfyui(prompt="anime waifu", progress_callback=cb)
                self.assertIsNotNone(img)
                self.assertTrue(any("Mendekode gambar" in s for s in callback_stages))

    def test_koboldcpp_launch_args_contain_bounded_context(self):
        """Ensure KoboldCPP is launched with explicit contextsize and thread constraints to prevent PC freezing."""
        engine = idle_engine.IdleEngine()
        with patch("subprocess.Popen") as mock_popen, \
             patch("os.path.isfile", return_value=True), \
             patch("os.path.isdir", return_value=True), \
             patch("os.listdir", return_value=["Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"]), \
             patch.object(engine, "is_llm_ready", side_effect=[False, True]):

            engine.wake_llm(timeout_seconds=5)
            self.assertTrue(mock_popen.called)
            cmd = mock_popen.call_args[0][0]
            self.assertIn("--contextsize", cmd)
            self.assertIn("4096", cmd)
            self.assertIn("--smartcontext", cmd)
            self.assertIn("--threads", cmd)
            self.assertIn("4", cmd)

    def test_asset_manager_download_endpoints_and_comfy_flags(self):
        """Ensure asset manager has Hugging Face direct endpoints and ComfyUI fast flags."""
        meina_info = asset_manager.ASSET_REGISTRY.get("meinamix")
        self.assertIsNotNone(meina_info)
        self.assertIn("huggingface.co", meina_info["url"])
        self.assertIn("hf-mirror.com", meina_info["fallback_url"])

        # ComfyUI launch spec should contain optimization flags
        with patch("os.path.isdir", return_value=True), \
             patch("os.path.isfile", return_value=True):
            spec = asset_manager.get_comfyui_launch_spec()
            if spec:
                self.assertIn("--disable-auto-launch", spec["cmd"])
                self.assertIn("--fast", spec["cmd"])


if __name__ == "__main__":
    unittest.main()

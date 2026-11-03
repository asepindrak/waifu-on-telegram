import unittest
import json
from unittest.mock import MagicMock, patch
import requests

import asset_manager
import media_engine
from media_engine import format_comfy_validation_error, MediaEngine

class TestWan21AssetsAndValidation(unittest.TestCase):
    def test_wan21_clip_in_asset_registry(self):
        """Test that wan21_clip is registered with correct properties."""
        self.assertIn("wan21_clip", asset_manager.ASSET_REGISTRY)
        clip_info = asset_manager.ASSET_REGISTRY["wan21_clip"]
        self.assertEqual(clip_info["filename"], "umt5_xxl_fp8_e4m3fn_scaled.safetensors")
        self.assertIn("models\\clip", clip_info["subfolder"])

    def test_ensure_video_engine_assets_wan21(self):
        """Test ensure_video_engine_assets checks all 3 components: 1.3b, clip, and vae."""
        with patch("asset_manager.get_asset_info") as mock_info:
            mock_info.side_effect = lambda k: {
                "wan21_1.3b": {"installed": True},
                "wan21_clip": {"installed": False},
                "wan21_vae": {"installed": True}
            }.get(k, {})

            is_ready, missing = asset_manager.ensure_video_engine_assets("wan21")
            self.assertFalse(is_ready)
            self.assertIn("wan21_clip", missing)

            # When all are installed
            mock_info.side_effect = lambda k: {"installed": True}
            is_ready, missing = asset_manager.ensure_video_engine_assets("wan21")
            self.assertTrue(is_ready)
            self.assertEqual(missing, [])

    def test_format_comfy_validation_error_node_errors(self):
        """Test format_comfy_validation_error parses node_errors cleanly."""
        mock_res = MagicMock(spec=requests.Response)
        mock_res.status_code = 400
        mock_res.json.return_value = {
            "error": {
                "type": "prompt_outputs_failed_validation",
                "message": "Prompt outputs failed validation",
                "details": "",
                "extra_info": {}
            },
            "node_errors": {
                "2": {
                    "errors": [
                        {
                            "type": "value_not_in_list",
                            "message": "Value not in list",
                            "details": "clip_name: 'umt5_xxl_fp8_e4m3fn_scaled.safetensors' not in []"
                        }
                    ],
                    "class_type": "CLIPLoader"
                }
            }
        }
        mock_res.text = json.dumps(mock_res.json.return_value)

        err_str = format_comfy_validation_error(mock_res)
        self.assertIn("CLIPLoader", err_str)
        self.assertIn("umt5_xxl_fp8_e4m3fn_scaled.safetensors", err_str)
        self.assertIn("belum terpasang", err_str)

    def test_wan21_generation_missing_clip_check(self):
        """Test generate_video_wan21 fails gracefully when ComfyUI has no matching clip."""
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188")
        with patch.object(engine, "get_available_clips", return_value=[]):
            res = engine.generate_video_wan21("a girl smiling")
            self.assertIsNone(res)
            self.assertIn("umt5_xxl_fp8_e4m3fn_scaled.safetensors", engine.last_error)
            self.assertIn("models/clip", engine.last_error)

    def test_animatediff_missing_loader_validation(self):
        """Test generate_video_animatediff fails gracefully when AnimateDiff loader node is absent."""
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188")
        with patch.object(engine, "_get_animatediff_loader_info", return_value=None):
            res = engine.generate_video_animatediff("a girl smiling")
            self.assertIsNone(res)
            self.assertIn("Ekstensi AnimateDiff", engine.last_error)

    def test_animatediff_workflow_wires_motion_module(self):
        """Test generate_video_animatediff wires the motion module node to KSampler."""
        engine = MediaEngine(comfyui_url="http://127.0.0.1:8188")
        with patch.object(engine, "_get_animatediff_loader_info", return_value=("ADE_AnimateDiffLoaderWithContext", "model_name", "mm_sd_v15_v2.ckpt")), \
             patch.object(engine, "get_available_checkpoints", return_value=["meinamix_v12Final.safetensors"]), \
             patch.object(engine, "_execute_video_workflow") as mock_exec:
            mock_exec.return_value = b"video_mp4_bytes"
            res = engine.generate_video_animatediff("a girl smiling")
            self.assertEqual(res, b"video_mp4_bytes")
            workflow_passed = mock_exec.call_args[0][0]
            # Verify motion loader is node "2"
            self.assertEqual(workflow_passed["2"]["class_type"], "ADE_AnimateDiffLoaderWithContext")
            self.assertEqual(workflow_passed["2"]["inputs"]["model_name"], "mm_sd_v15_v2.ckpt")
            # Verify KSampler (node "6") connects to node "2" (the motion module), not directly to Checkpoint
            self.assertEqual(workflow_passed["6"]["inputs"]["model"], ["2", 0])
            self.assertEqual(workflow_passed["8"]["inputs"]["fps"], 8.0)

if __name__ == "__main__":
    unittest.main()

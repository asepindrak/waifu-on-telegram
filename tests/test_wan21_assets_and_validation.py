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

if __name__ == "__main__":
    unittest.main()

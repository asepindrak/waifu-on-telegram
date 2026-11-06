"""
test_diagnostics_and_nude_routing.py
Validates:
1. Comprehensive diagnostics reporting in both Telegram report and CLI diagnostics
   (All user setup choices: LLM architecture, Visual generator, Voice TTS, Coding workspace, GPU Lock).
2. Nude outfit ("tanpa busana") automatic routing:
   - Sets is_nude = True in visual prompt crafting.
   - Routes image generation checkpoint to NSFW_COMFYUI_CHECKPOINT.
   - Bypasses SFW AGY and Cloud engines for nude photos.
   - Awakens ComfyUI if sleeping.
   - Routes caption generation to uncensored NSFW LLM (is_nsfw=True).
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

from persona_manager import PersonaManager
from media_engine import MediaEngine
import bot


class TestDiagnosticsAndNudeRouting(unittest.TestCase):

    def setUp(self):
        self.pm = PersonaManager()

    def test_nude_outfit_craft_prompt_returns_is_nude(self):
        """Selecting 'nude' outfit must flag is_nude = True in visual prompt."""
        user_id = 998877
        self.pm.set_user_outfit(user_id, "nude")
        raw_key, outfit_label = self.pm.get_user_outfit(user_id)
        self.assertEqual(raw_key, "nude")
        self.assertIn("Tanpa Busana", outfit_label)

        v_prompt, neg_prompt, is_nude, label = self.pm.craft_visual_prompt_full(
            "kirim foto selfie kamu di kamar dong", user_id=user_id, scene_override="private bedroom"
        )
        self.assertTrue(is_nude)
        self.assertIn("nude", v_prompt.lower())

    def test_media_engine_checkpoint_routing_nude_vs_sfw(self):
        """media_engine.get_active_checkpoint switches between SFW and NSFW checkpoints."""
        me = MediaEngine(comfyui_url="http://127.0.0.1:8188")
        with patch.object(me, "get_available_checkpoints", return_value=["AnythingXL_xl.safetensors", "AOM3A1B_orange_mixs.safetensors"]):
            with patch.dict(os.environ, {
                "SFW_COMFYUI_CHECKPOINT": "AnythingXL_xl.safetensors",
                "NSFW_COMFYUI_CHECKPOINT": "AOM3A1B_orange_mixs.safetensors"
            }):
                sfw_ckpt = me.get_active_checkpoint(is_nude=False)
                nsfw_ckpt = me.get_active_checkpoint(is_nude=True)
                self.assertIn("AnythingXL", sfw_ckpt)
                self.assertIn("AOM3", nsfw_ckpt)
                self.assertNotEqual(sfw_ckpt, nsfw_ckpt)

    def test_media_engine_bypasses_sfw_engines_for_nude(self):
        """generate_photo never sends nude photo requests to SFW AGY or SFW Cloud."""
        me = MediaEngine(comfyui_url="http://127.0.0.1:8188")
        me.generate_image_agy = MagicMock(return_value=b"agy_bytes")
        me.generate_image_cloud = MagicMock(return_value=b"cloud_bytes")
        me.generate_image_comfyui = MagicMock(return_value=b"local_comfy_bytes")

        with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy"}):
            # When is_nude is True, AGY must be skipped and ComfyUI called!
            res, src = me.generate_photo("girl smiling", is_nude=True)
            me.generate_image_agy.assert_not_called()
            me.generate_image_comfyui.assert_called_once()
            self.assertEqual(res, b"local_comfy_bytes")

        me.generate_image_agy.reset_mock()
        me.generate_image_comfyui.reset_mock()

        with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "cloud"}):
            # When is_nude is True, Cloud must be skipped and ComfyUI called!
            res, src = me.generate_photo("girl smiling", is_nude=True)
            me.generate_image_cloud.assert_not_called()
            me.generate_image_comfyui.assert_called_once()
            self.assertEqual(res, b"local_comfy_bytes")

    def test_diagnostics_report_includes_all_setup_choices(self):
        """build_system_diagnostics_report must report complete setup choices."""
        user_id = 12345
        bot.persona_mgr.set_user_outfit(user_id, "nude")

        with patch.dict(os.environ, {
            "BOT_LANGUAGE": "id",
            "AI_ENGINE_MODE": "split",
            "SFW_LLM_PROVIDER": "agy",
            "SFW_LLM_MODEL": "gemini-3.8-flash-medium",
            "NSFW_LLM_PROVIDER": "local",
            "LOCAL_LLM_MODEL": "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
            "IMAGE_ENGINE_MODE": "split",
            "SFW_IMAGE_ENGINE": "comfyui",
            "NSFW_IMAGE_ENGINE": "comfyui",
            "SFW_COMFYUI_CHECKPOINT": "AnythingXL_xl.safetensors",
            "NSFW_COMFYUI_CHECKPOINT": "AOM3A1B_orange_mixs.safetensors",
            "VOICE_BACKEND": "voicestudio",
            "VOICE_NAME": "Akira",
            "VOICE_LANGUAGE": "ja-JP",
            "VOICE_REPLY_MODE": "smart"
        }):
            with patch("bot.is_port_listening", return_value=True):
                report = bot.build_system_diagnostics_report(user_id)
                self.assertIn("Arsitektur LLM", report)
                self.assertIn("SFW Engine", report)
                self.assertIn("NSFW Engine", report)
                self.assertIn("Generator Visual", report)
                self.assertIn("Model Foto Aktif", report)
                self.assertIn("NSFW Model Dipakai Otomatis", report)
                self.assertIn("Audio & Suara", report)
                self.assertIn("VoiceStudio", report)
                self.assertIn("Coding & Workspace", report)
                self.assertIn("GPU Lock", report)
                self.assertIn("Tanpa Busana", report)


if __name__ == "__main__":
    unittest.main()

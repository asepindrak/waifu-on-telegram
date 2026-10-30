import os
import unittest
from unittest.mock import patch, MagicMock

# Set valid mock telegram token before importing bot
os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import asset_manager
import media_engine
import bot
import setup

class TestImageModelSelection(unittest.TestCase):
    def setUp(self):
        self.orig_ckpt = os.environ.get("COMFYUI_CHECKPOINT")
        self.orig_url = os.environ.get("COMFYUI_URL")
        self.orig_fallback = os.environ.get("MEDIA_FALLBACK_CLOUD")

    def tearDown(self):
        if self.orig_ckpt is not None:
            os.environ["COMFYUI_CHECKPOINT"] = self.orig_ckpt
        else:
            os.environ.pop("COMFYUI_CHECKPOINT", None)

        if self.orig_url is not None:
            os.environ["COMFYUI_URL"] = self.orig_url
        else:
            os.environ.pop("COMFYUI_URL", None)

        if self.orig_fallback is not None:
            os.environ["MEDIA_FALLBACK_CLOUD"] = self.orig_fallback
        else:
            os.environ.pop("MEDIA_FALLBACK_CLOUD", None)

    def test_anything_xl_registered_in_asset_manager(self):
        """Verify that Anything XL is properly registered in asset_manager with Civitai & HuggingFace metadata."""
        self.assertIn("anything_xl", asset_manager.ASSET_REGISTRY)
        asset = asset_manager.ASSET_REGISTRY["anything_xl"]
        self.assertEqual(asset["filename"], "AnythingXL_xl.safetensors")
        self.assertIn("9409", asset["civitai_url"])
        self.assertIn("huggingface.co", asset["url"])
        self.assertTrue(asset["size_mb"] > 6000)

    def test_aom3_registered_in_asset_manager(self):
        """Verify that AbyssOrangeMix3 (AOM3A1B) is properly registered in asset_manager with CivArchive & Civitai metadata."""
        self.assertIn("aom3", asset_manager.ASSET_REGISTRY)
        asset = asset_manager.ASSET_REGISTRY["aom3"]
        self.assertEqual(asset["filename"], "AOM3A1B_orangemixs.safetensors")
        self.assertIn("9942", asset["civitai_url"])
        self.assertIn("17233", asset["civarchive_url"])
        self.assertIn("WarriorMama777/OrangeMixs", asset["url"])
        self.assertTrue(asset["size_mb"] > 1800)

    def test_apply_ckpt_choice_in_bot(self):
        """Verify that selecting aom3, anything_xl, or meinamix in Telegram bot updates environment cleanly."""
        with patch("bot.update_env_variable") as mock_update:
            label = bot.apply_ckpt_choice("aom3")
            self.assertEqual(label, "AbyssOrangeMix3 (AOM3A1B SD 1.5)")
            self.assertEqual(os.environ.get("COMFYUI_CHECKPOINT"), "AOM3A1B_orangemixs.safetensors")
            self.assertEqual(os.environ.get("COMFYUI_URL"), "http://127.0.0.1:8188")
            self.assertEqual(os.environ.get("MEDIA_FALLBACK_CLOUD"), "false")
            mock_update.assert_any_call("COMFYUI_CHECKPOINT", "AOM3A1B_orangemixs.safetensors")

        with patch("bot.update_env_variable") as mock_update:
            label = bot.apply_ckpt_choice("anything_xl")
            self.assertEqual(label, "Anything XL (SDXL 1024px)")
            self.assertEqual(os.environ.get("COMFYUI_CHECKPOINT"), "AnythingXL_xl.safetensors")
            self.assertEqual(os.environ.get("COMFYUI_URL"), "http://127.0.0.1:8188")
            self.assertEqual(os.environ.get("MEDIA_FALLBACK_CLOUD"), "false")
            mock_update.assert_any_call("COMFYUI_CHECKPOINT", "AnythingXL_xl.safetensors")

        with patch("bot.update_env_variable") as mock_update:
            label = bot.apply_ckpt_choice("meinamix")
            self.assertEqual(label, "MeinaMix v12 (SD 1.5)")
            self.assertEqual(os.environ.get("COMFYUI_CHECKPOINT"), "meinamix_v12Final.safetensors")
            self.assertEqual(os.environ.get("COMFYUI_URL"), "http://127.0.0.1:8188")
            mock_update.assert_any_call("COMFYUI_CHECKPOINT", "meinamix_v12Final.safetensors")

    def test_media_engine_sdxl_detection(self):
        """Verify that Anything XL checkpoint is detected as SDXL in media_engine."""
        eng = media_engine.MediaEngine(comfyui_url="http://127.0.0.1:8188")
        with patch.object(eng, "get_available_checkpoints", return_value=["AnythingXL_xl.safetensors"]):
            os.environ["COMFYUI_CHECKPOINT"] = "AnythingXL_xl.safetensors"
            active = eng.get_active_checkpoint()
            self.assertEqual(active, "AnythingXL_xl.safetensors")

            # Verify SDXL dimensions for 3:4 aspect ratio
            w, h = eng.get_dimensions("3:4", is_sdxl=True)
            self.assertEqual((w, h), (896, 1152))

            # SD 1.5 dimensions comparison
            w_sd, h_sd = eng.get_dimensions("3:4", is_sdxl=False)
            self.assertEqual((w_sd, h_sd), (576, 768))

    def test_setup_config_image_model_choice(self):
        """Verify that setup.py config_image_model properly prompts and configures AOM3 and Anything XL."""
        env_vars = {}
        with patch("builtins.input", side_effect=["2", "n"]):  # Choice 2 is AbyssOrangeMix3, do not download now
            with patch("setup.scan_image_models", return_value=[]):
                setup.config_image_model(env_vars)
                self.assertEqual(env_vars.get("COMFYUI_CHECKPOINT"), "AOM3A1B_orangemixs.safetensors")
                self.assertEqual(env_vars.get("COMFYUI_URL"), "http://127.0.0.1:8188")
                self.assertEqual(env_vars.get("MEDIA_FALLBACK_CLOUD"), "false")

        env_vars_xl = {}
        with patch("builtins.input", side_effect=["3", "n"]):  # Choice 3 is Anything XL, do not download now
            with patch("setup.scan_image_models", return_value=[]):
                setup.config_image_model(env_vars_xl)
                self.assertEqual(env_vars_xl.get("COMFYUI_CHECKPOINT"), "AnythingXL_xl.safetensors")
                self.assertEqual(env_vars_xl.get("COMFYUI_URL"), "http://127.0.0.1:8188")
                self.assertEqual(env_vars_xl.get("MEDIA_FALLBACK_CLOUD"), "false")

    def test_setup_manage_models_menu_render(self):
        """Verify that setup.py manage_models_menu renders without NameError (such as DIM)."""
        with patch("builtins.input", return_value="0"):
            # Should exit cleanly on 0
            setup.manage_models_menu()

if __name__ == "__main__":
    unittest.main()

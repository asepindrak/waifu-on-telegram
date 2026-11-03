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
        """Verify that setup.py config_image_model properly prompts and configures AOM3 and Anything XL in Unified Mode."""
        env_vars = {}
        # Mode 1 (Unified), Choice 2 (AOM3), "n" (skip download)
        with patch("builtins.input", side_effect=["1", "2", "n"]):
            with patch("setup.scan_image_models", return_value=[]):
                setup.config_image_model(env_vars)
                self.assertEqual(env_vars.get("COMFYUI_CHECKPOINT"), "AOM3A1B_orangemixs.safetensors")
                self.assertEqual(env_vars.get("COMFYUI_URL"), "http://127.0.0.1:8188")
                self.assertEqual(env_vars.get("MEDIA_FALLBACK_CLOUD"), "false")

        env_vars_xl = {}
        # Mode 1 (Unified), Choice 3 (Anything XL), "n" (skip download)
        with patch("builtins.input", side_effect=["1", "3", "n"]):
            with patch("setup.scan_image_models", return_value=[]):
                setup.config_image_model(env_vars_xl)
                self.assertEqual(env_vars_xl.get("COMFYUI_CHECKPOINT"), "AnythingXL_xl.safetensors")
                self.assertEqual(env_vars_xl.get("COMFYUI_URL"), "http://127.0.0.1:8188")
                self.assertEqual(env_vars_xl.get("MEDIA_FALLBACK_CLOUD"), "false")

    def test_setup_config_image_model_split_hybrid(self):
        """Verify that setup.py config_image_model configures Split Hybrid Mode (SFW AGY + NSFW AOM3)."""
        env_vars = {}
        # Mode 2 (Split Hybrid), SFW 1 (AGY), NSFW 1 (AOM3), "n" (skip download)
        with patch("builtins.input", side_effect=["2", "1", "1", "n"]):
            with patch("setup.scan_image_models", return_value=[]):
                setup.config_image_model(env_vars)
                self.assertEqual(env_vars.get("IMAGE_ENGINE_MODE"), "split")
                self.assertEqual(env_vars.get("SFW_IMAGE_ENGINE"), "agy")
                self.assertEqual(env_vars.get("NSFW_IMAGE_ENGINE"), "comfyui")
                self.assertEqual(env_vars.get("NSFW_COMFYUI_CHECKPOINT"), "AOM3A1B_orangemixs.safetensors")

    def test_bot_photo_menu_split_callbacks(self):
        """Verify that Telegram bot callbacks update split image settings correctly."""
        import bot
        from unittest.mock import MagicMock

        # Mock call object
        call = MagicMock()
        call.from_user.id = 12345
        call.message.chat.id = 12345
        call.message.message_id = 999

        with patch("bot.is_authorized", return_value=True), \
             patch.object(bot.bot, "answer_callback_query"), \
             patch("bot.update_env_variable"), \
             patch("bot.show_photo_engine_menu"):

            # 1. Toggle mode to split
            os.environ["IMAGE_ENGINE_MODE"] = "unified"
            bot.callback_toggle_split_img(call)
            self.assertEqual(os.environ.get("IMAGE_ENGINE_MODE"), "split")

            # 2. Set SFW image engine to AGY
            call.data = "cfg_set_sfw_img:agy"
            bot.callback_set_sfw_img(call)
            self.assertEqual(os.environ.get("SFW_IMAGE_ENGINE"), "agy")

            # 3. Set NSFW image engine to AOM3
            call.data = "cfg_set_nsfw_img:aom3"
            bot.callback_set_nsfw_img(call)
            self.assertEqual(os.environ.get("NSFW_IMAGE_ENGINE"), "comfyui")
            self.assertEqual(os.environ.get("NSFW_COMFYUI_CHECKPOINT"), "AOM3A1B_orangemixs.safetensors")

    def test_setup_manage_models_menu_render(self):
        """Verify that setup.py manage_models_menu renders without NameError (such as DIM)."""
        with patch("builtins.input", return_value="0"):
            # Should exit cleanly on 0
            setup.manage_models_menu()

if __name__ == "__main__":
    unittest.main()

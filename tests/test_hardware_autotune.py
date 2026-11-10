import unittest
from unittest.mock import patch, MagicMock
import asset_manager


class TestHardwareAutoTune(unittest.TestCase):
    """Verifies automatic GPU VRAM detection and optimal model recommendation tiers."""

    def test_tier_high_vram_recommends_sdxl_and_wan(self):
        """When GPU has >= 8GB VRAM (e.g. RTX 3060/4070), Anything XL and Wan 2.1 are recommended."""
        mock_output = b"NVIDIA GeForce RTX 4070, 12288\n"
        with patch("subprocess.check_output", return_value=mock_output):
            profile = asset_manager.detect_hardware_profile(refresh=True)
            self.assertEqual(profile["tier"], "high")
            self.assertEqual(profile["recommended_image_model"], "anything_xl")
            self.assertEqual(profile["recommended_video_engine"], "wan21")
            self.assertEqual(profile["recommended_llm_layers"], 99)
            self.assertGreaterEqual(profile["vram_gb"], 8.0)

    def test_tier_mid_vram_recommends_sdxl(self):
        """When GPU has 6GB VRAM (e.g. RTX 2060 6GB / GTX 1660 6GB), Anything XL is recommended."""
        mock_output = b"NVIDIA GeForce RTX 2060, 6144\n"
        with patch("subprocess.check_output", return_value=mock_output):
            profile = asset_manager.detect_hardware_profile(refresh=True)
            self.assertEqual(profile["tier"], "mid")
            self.assertEqual(profile["recommended_image_model"], "anything_xl")
            self.assertEqual(profile["recommended_video_engine"], "wan21")
            self.assertEqual(profile["recommended_llm_layers"], 24)
            self.assertGreaterEqual(profile["vram_gb"], 6.0)

    def test_tier_compact_vram_recommends_aom3_and_animatediff(self):
        """When GPU has 4GB VRAM (e.g. GTX 1050 Ti 4GB / GTX 1650), AbyssOrangeMix3 and AnimateDiff are recommended."""
        mock_output = b"NVIDIA GeForce GTX 1050 Ti, 4096\n"
        with patch("subprocess.check_output", return_value=mock_output):
            profile = asset_manager.detect_hardware_profile(refresh=True)
            self.assertEqual(profile["tier"], "compact")
            self.assertEqual(profile["recommended_image_model"], "aom3")
            self.assertEqual(profile["recommended_video_engine"], "animatediff")
            self.assertEqual(profile["recommended_llm_layers"], 20)
            self.assertEqual(profile["recommended_image_file"], "AOM3A1B_orangemixs.safetensors")

    def test_tier_entry_or_igpu_recommends_cloud_and_motion(self):
        """When GPU has < 2GB VRAM or no dedicated GPU (iGPU / Office PC), Cloud and Motion 2.5D are recommended."""
        with patch("asset_manager.subprocess.check_output", side_effect=Exception("No nvidia-smi")):
            profile = asset_manager.detect_hardware_profile(refresh=True)
            self.assertEqual(profile["tier"], "entry")
            self.assertEqual(profile["recommended_image_model"], "cloud")
            self.assertEqual(profile["recommended_video_engine"], "motion")
            self.assertEqual(profile["recommended_llm_layers"], 0)


if __name__ == "__main__":
    unittest.main()

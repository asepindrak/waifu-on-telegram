import os
import unittest
from unittest.mock import patch
import shutil
import tempfile
import photo_vault
from lu_llm_client import LocallyUncensoredClient
from media_engine import format_agy_error, MediaEngine

class TestPhotoVaultAndStability(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_vault_dir = photo_vault.VAULT_DIR
        self.orig_catalog = photo_vault.CATALOG_PATH
        photo_vault.VAULT_DIR = os.path.join(self.test_dir, "vault")
        photo_vault.CATALOG_PATH = os.path.join(photo_vault.VAULT_DIR, "catalog.json")

    def tearDown(self):
        photo_vault.VAULT_DIR = self.orig_vault_dir
        photo_vault.CATALOG_PATH = self.orig_catalog
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_retrieve_photo(self):
        fake_bytes = b"JPEG_BINARY_DATA_TEST_123"
        entry = photo_vault.save_photo_to_vault(
            fake_bytes,
            persona="runa",
            scene="relaxing in a cozy cafe sipping green tea",
            outfit_label="Cozy Cafe Knit",
            is_nude=False,
            user_query="kirim pap lagi nongkrong di cafe dong"
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["persona"], "runa")
        self.assertFalse(entry["is_nude"])
        self.assertIn("cafe", entry["tags"])

        # Test semantic search
        result = photo_vault.find_matching_photo(
            persona="runa",
            scene="di cafe santai minum teh",
            outfit_label="Cozy Cafe Knit",
            is_nude=False,
            user_query="pap lagi ngopi"
        )
        self.assertIsNotNone(result)
        img_bytes, meta = result
        self.assertEqual(img_bytes, fake_bytes)
        self.assertEqual(meta["id"], entry["id"])

    def test_nsfw_safety_isolation(self):
        fake_sfw = b"SFW_DATA"
        photo_vault.save_photo_to_vault(
            fake_sfw,
            persona="akira",
            scene="reading book in library",
            outfit_label="school_jk",
            is_nude=False,
            user_query="foto di perpus"
        )

        # Asking for nude must NOT return SFW photo
        nude_result = photo_vault.find_matching_photo(
            persona="akira",
            scene="reading book",
            is_nude=True,
            user_query="kirim foto telanjang"
        )
        self.assertIsNone(nude_result)

    def test_photo_vault_never_repeats_seen_photo_for_user(self):
        """Photo vault strictly avoids repeating photos that user has already received."""
        fake_bytes_1 = b"PHOTO_1_BYTES"
        fake_bytes_2 = b"PHOTO_2_BYTES"

        e1 = photo_vault.save_photo_to_vault(
            fake_bytes_1,
            persona="runa",
            scene="relaxing on bed cozy bedroom",
            outfit_label="pajamas",
            is_nude=False,
            user_query="pap rebahan"
        )
        e2 = photo_vault.save_photo_to_vault(
            fake_bytes_2,
            persona="runa",
            scene="relaxing on bed cozy bedroom",
            outfit_label="pajamas",
            is_nude=False,
            user_query="pap rebahan"
        )

        user_id = 99887766
        # First request should return one photo and mark it seen
        res1 = photo_vault.find_matching_photo(
            persona="runa",
            scene="relaxing on bed",
            outfit_label="pajamas",
            is_nude=False,
            user_query="pap",
            user_id=user_id
        )
        self.assertIsNotNone(res1)
        first_filename = res1[1]["filename"]

        # Second request MUST return the second unique photo, NOT the first!
        res2 = photo_vault.find_matching_photo(
            persona="runa",
            scene="relaxing on bed",
            outfit_label="pajamas",
            is_nude=False,
            user_query="pap",
            user_id=user_id
        )
        self.assertIsNotNone(res2)
        second_filename = res2[1]["filename"]
        self.assertNotEqual(first_filename, second_filename)

        # Third request: with MEDIA_VAULT_REUSE=false, all matching photos have been seen, so returns None!
        with patch.dict(os.environ, {"MEDIA_VAULT_REUSE": "false"}):
            res3 = photo_vault.find_matching_photo(
                persona="runa",
                scene="relaxing on bed",
                outfit_label="pajamas",
                is_nude=False,
                user_query="pap",
                user_id=user_id
            )
            self.assertIsNone(res3, "Should return None instead of repeating an already seen photo!")

    def test_llm_client_default_port(self):
        client = LocallyUncensoredClient()
        self.assertEqual(client.base_url, "http://127.0.0.1:5001/v1")
        self.assertEqual(client.get_api_key(), "kobold")

    def test_format_agy_error(self):
        err_429 = "Failed to generate image: Quota exhausted (429 RESOURCE_EXHAUSTED). Reset in 3 hours."
        res = format_agy_error(err_429)
        self.assertIn("Batas kuota model gambar Google Antigravity habis", res)

        err_refused = "Connection refused: [WinError 10061] No connection could be made"
        res2 = format_agy_error(err_refused)
        self.assertIn("AGY Bridge (port 8001) terputus", res2)

    def test_fallback_notice_captured_when_generator_fails(self):
        me = MediaEngine()
        def mock_agy(*args, **kwargs):
            me.last_error = "Quota exhausted (429 RESOURCE_EXHAUSTED)"
            return None

        with patch.object(me, "generate_image_agy", side_effect=mock_agy), \
             patch.object(me, "generate_image_cloud_fallback", return_value=b"CLOUD_FALLBACK_BYTES"):
            with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy"}):
                res, label = me.generate_photo("selfie in park", persona="akira")
                # When primary AGY fails, last_fallback_notice must be populated
                self.assertIsNotNone(me.last_fallback_notice)
                self.assertEqual(me.last_fallback_notice["primary_engine"], "Google Antigravity (AGY)")
                self.assertIn("Batas kuota model gambar Google Antigravity habis", me.last_fallback_notice["error"])
                # Fallback delivers image via Vault or Cloud
                self.assertEqual(res, b"CLOUD_FALLBACK_BYTES")
                self.assertIn("Cloud Engine", label)

if __name__ == "__main__":
    unittest.main()

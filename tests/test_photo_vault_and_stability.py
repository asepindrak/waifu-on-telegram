import os
import unittest
from unittest.mock import patch
import shutil
import tempfile
import photo_vault
from lu_llm_client import LocallyUncensoredClient

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

if __name__ == "__main__":
    unittest.main()

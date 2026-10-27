import os
import unittest
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

    def test_llm_client_default_port(self):
        client = LocallyUncensoredClient()
        self.assertEqual(client.base_url, "http://127.0.0.1:5001/v1")
        self.assertEqual(client.get_api_key(), "kobold")

if __name__ == "__main__":
    unittest.main()

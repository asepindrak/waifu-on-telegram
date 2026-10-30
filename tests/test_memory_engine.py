import os
import shutil
import tempfile
import threading
import unittest
from memory_engine import MemoryEngine, VectorEngine, _atomic_write_json


class TestMemoryEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="waifu_mem_test_")
        self.data_file = os.path.join(self.test_dir, "test_memories.json")
        self.engine = MemoryEngine(data_file=self.data_file)
        self.user_id = 998877

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_atomic_write_integrity(self):
        """Verify _atomic_write_json writes valid JSON and cleans up temporary files."""
        sample_data = {"key": "value", "numbers": [1, 2, 3]}
        _atomic_write_json(self.data_file, sample_data)

        self.assertTrue(os.path.exists(self.data_file))
        # Ensure no lingering .tmp files
        tmp_files = [f for f in os.listdir(self.test_dir) if f.endswith(".tmp")]
        self.assertEqual(len(tmp_files), 0)

        # Re-load engine and verify contents
        new_engine = MemoryEngine(data_file=self.data_file)
        self.assertEqual(new_engine.data["key"], "value")

    def test_thread_safe_concurrent_writes(self):
        """Verify concurrent threads adding facts do not cause race conditions or corruption."""
        def worker(idx):
            self.engine.add_fact(self.user_id, f"Fakta user nomor {idx}", category="test")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        facts = self.engine.get_facts(self.user_id)
        self.assertEqual(len(facts), 25)

    def test_vector_engine_vectorization(self):
        """Verify VectorEngine generates L2-normalized sparse vectors with n-grams."""
        vec = VectorEngine.vectorize("Suka kopi susu gula aren")
        self.assertTrue(len(vec) > 0)

        # Verify L2 norm is ~1.0
        norm = sum(v * v for v in vec.values())
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_semantic_vector_search_relevance(self):
        """Verify semantic vector search correctly ranks relevant facts based on query meaning."""
        self.engine.add_fact(self.user_id, "Suka minum kopi latte dingin", category="likes")
        self.engine.add_fact(self.user_id, "Alergi udang dan kepiting laut", category="allergies")
        self.engine.add_fact(self.user_id, "Bekerja sebagai backend developer Python", category="work")
        self.engine.add_fact(self.user_id, "Punya kucing anggora warna putih bernama Miko", category="pet")

        # 1. Query about coffee should rank coffee at top
        res_coffee = self.engine.search_facts(self.user_id, "Mau ngopi santai di cafe nih", top_k=2)
        self.assertTrue(len(res_coffee) > 0)
        top_fact, score = res_coffee[0]
        self.assertIn("kopi", top_fact["fact"].lower())
        self.assertGreater(score, 0.10)

        # 2. Query about seafood / allergy should rank allergy fact at top
        res_seafood = self.engine.search_facts(self.user_id, "Mau makan seafood udang bakar", top_k=2)
        self.assertTrue(len(res_seafood) > 0)
        top_fact, score = res_seafood[0]
        self.assertIn("udang", top_fact["fact"].lower())

        # 3. Query about pet should rank cat fact at top
        res_pet = self.engine.search_facts(self.user_id, "Kucingku lagi tidur gemas banget", top_k=2)
        self.assertTrue(len(res_pet) > 0)
        top_fact, score = res_pet[0]
        self.assertIn("kucing", top_fact["fact"].lower())

    def test_format_memory_context_dynamic_prioritization(self):
        """Verify format_memory_context prioritizes relevant facts when query is provided."""
        self.engine.update_profile(self.user_id, name="Aditya", job="Software Engineer")
        for i in range(10):
            self.engine.add_fact(self.user_id, f"Random fact number {i}", category="general")
        self.engine.add_fact(self.user_id, "Alergi kacang tanah parah", category="allergies")

        # Without query: allergic fact might be pushed out if max_facts is small, or just at bottom
        ctx_no_query = self.engine.format_memory_context(self.user_id)
        self.assertIn("Aditya", ctx_no_query)

        # With query mentioning peanut / kacang:
        ctx_query = self.engine.format_memory_context(self.user_id, query="Mau jajan selai kacang nih")
        self.assertIn("Alergi kacang tanah", ctx_query)

    def test_auto_extract_facts_comprehensive(self):
        """Verify auto_extract_facts learns names, likes, allergies, jobs, locations, and pets."""
        # 1. Name
        learned = self.engine.auto_extract_facts("Namaku Dimas salam kenal ya", self.user_id)
        self.assertTrue(any("Dimas" in l for l in learned))
        self.assertEqual(self.engine.get_profile(self.user_id)["name"], "Dimas")

        # 2. Likes
        learned = self.engine.auto_extract_facts("Aku paling suka nasi goreng pedas", self.user_id)
        self.assertTrue(any("nasi goreng" in l.lower() for l in learned))

        # 3. Allergies & Dislikes
        learned = self.engine.auto_extract_facts("Aku alergi telur ayam rebus", self.user_id)
        self.assertTrue(any("alergi telur" in l.lower() for l in learned))

        learned = self.engine.auto_extract_facts("Aku benci suasana berisik dan macet", self.user_id)
        self.assertTrue(any("tidak suka" in l.lower() for l in learned))

        # 4. Pets
        learned = self.engine.auto_extract_facts("Aku punya kucing oren di rumah", self.user_id)
        self.assertTrue(any("kucing" in l.lower() for l in learned))

        # 5. Location & Work
        self.engine.auto_extract_facts("Aku tinggal di Bandung dan kerja sebagai desainer grafis", self.user_id)
        prof = self.engine.get_profile(self.user_id)
        self.assertIn("Bandung", prof["location"])
        self.assertIn("desainer", prof["job"].lower())

    def test_search_diary_semantic(self):
        """Verify semantic search on relationship diary entries."""
        self.engine.add_diary_entry(self.user_id, "Tadi sore kita jalan-jalan santai di pantai sambil liat sunset indah banget.", mood="🌅 Romantis")
        self.engine.add_diary_entry(self.user_id, "Nemenin pacarku belajar ngoding sampai larut malam di kamar.", mood="💻 Semangat")

        results = self.engine.search_diary(self.user_id, "pantai sunset sore", top_k=1)
        self.assertEqual(len(results), 1)
        entry, score = results[0]
        self.assertIn("pantai", entry["entry"])
        self.assertGreater(score, 0.15)


if __name__ == "__main__":
    unittest.main()

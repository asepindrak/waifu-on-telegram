"""
tests/test_waifu_consistency_and_coding_guard.py
Tests for:
1. Preventing coding intent false positives on casual/romantic queries.
2. Coding engine only auto-serving preview when web/preview is explicitly requested.
3. WaifuStatusTracker maintaining physical context consistency (e.g. at home vs at campus).
"""

import os
import time
import tempfile
import unittest

from coding_engine import get_coding_engine
from waifu_status_tracker import WaifuStatusTracker


class TestWaifuConsistencyAndCodingGuard(unittest.TestCase):

    def setUp(self):
        self.ce = get_coding_engine()
        self.tmp_dir = tempfile.mkdtemp()
        self.status_file = os.path.join(self.tmp_dir, "test_status.json")
        self.tracker = WaifuStatusTracker(storage_path=self.status_file, max_age_hours=2.0)

    def tearDown(self):
        if os.path.exists(self.status_file):
            try:
                os.remove(self.status_file)
            except Exception:
                pass
        try:
            os.rmdir(self.tmp_dir)
        except Exception:
            pass

    def test_coding_intent_negative_guards(self):
        """Conversational, romantic, and selfie queries MUST NOT trigger coding mode."""
        false_positives = [
            "coba lihat kamu lagi apa",
            "coba lihat fotonya dong",
            "coba liat foto kamu",
            "kamu lagi bikin apa sekarang?",
            "bikin kopi bareng yuk sayang",
            "ini buat kamu sayang",
            "buatkan teh hangat ya",
            "tulis surat cinta buat aku",
            "kamu bikin aku tersenyum terus deh",
            "lihat senyummu yang manis dong",
            "pap selfie lagi ngapain sekarang"
        ]
        for query in false_positives:
            self.assertFalse(
                self.ce.is_coding_intent(query),
                f"False positive detected: '{query}' should NOT be treated as coding intent!"
            )

    def test_coding_intent_true_positives(self):
        """Actual programming and project workspace tasks MUST trigger coding mode."""
        true_positives = [
            "bikin landing page coffee shop modern",
            "buatkan script python untuk download file",
            "tulis kode html dan css untuk navbar",
            "coba run project nya aku mau lihat",
            "coba preview web ini",
            "jalankan project web",
            "fix bug error di index.html",
            "git status"
        ]
        for query in true_positives:
            self.assertTrue(
                self.ce.is_coding_intent(query),
                f"True positive missed: '{query}' should be recognized as coding intent!"
            )

    def test_waifu_status_tracker_photo_consistency(self):
        """When waifu delivers a photo at home/rebahan, tracker records home location and forbids saying campus."""
        user_id = 998877

        self.tracker.record_photo_event(
            user_id=user_id,
            scene="sitting on cozy plush bed in bedroom",
            caption="lagi rebahan di rumah baru pulang dari kampus nih sayang 💕",
            outfit="piyama santai",
            persona_name="Akira"
        )

        st = self.tracker.get_current_status(user_id)
        self.assertIsNotNone(st)
        self.assertEqual(st["location"], "Rumah / Kamar kos")
        self.assertIn("rebahan di rumah", st["activity"])

        # Format system prompt instruction
        instr = self.tracker.format_status_instruction(
            user_id=user_id,
            cur_hour=13,
            routine_desc="lagi di perpustakaan kampus ngerjain tugas",
            major="Ilmu Hukum"
        )

        self.assertIn("Rumah / Kamar kos", instr)
        self.assertIn("rebahan di rumah baru pulang dari kampus", instr)
        self.assertIn("DILARANG TIBA-TIBA bilang masih di kampus", instr)
        self.assertNotIn("Kegiatanmu saat ini: lagi di perpustakaan kampus", instr)


if __name__ == "__main__":
    unittest.main()


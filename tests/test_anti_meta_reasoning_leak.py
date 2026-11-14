"""Unit tests for anti-meta/reasoning leak protection in waifu-on-telegram."""
import unittest
from bot import is_meta_or_reasoning_leak, strip_meta_reasoning_leak, is_unwanted_english_or_translation


class TestAntiMetaReasoningLeak(unittest.TestCase):
    def test_detects_user_reported_meta_leak(self):
        leak_str = ", avoid overusing name; perhaps call him"
        self.assertTrue(is_meta_or_reasoning_leak(leak_str))

    def test_detects_various_internal_planning_phrases(self):
        samples = [
            "avoid overusing name",
            "perhaps call him sayang",
            "address him directly",
            "avoid repeating his name",
            "keep in mind to respond warmly",
            "Thinking Process: respond in Indonesian",
            "Reasoning: the user is asking about dinner",
            "According to the guidelines, respond as a girlfriend",
        ]
        for sample in samples:
            self.assertTrue(is_meta_or_reasoning_leak(sample), f"Failed to detect meta leak in: {sample}")

    def test_strip_meta_reasoning_leak_removes_prefix_or_dirty_lines(self):
        multiline_leak = ", avoid overusing name; perhaps call him\n*tersenyum manis*\nHalo sayang, kamu udah makan siang belum?"
        cleaned = strip_meta_reasoning_leak(multiline_leak)
        self.assertNotIn("avoid overusing", cleaned)
        self.assertIn("Halo sayang", cleaned)

    def test_clean_waifu_dialogue_is_not_flagged_as_meta_leak(self):
        normal_samples = [
            "Halo sayang! Lagi santai ya sore ini?",
            "*tersenyum manis sambil melambaikan tangan*\nHehe iya, ada apa nih?",
            "Aku kangen banget sama kamu hari ini!",
            "Iya, jangan lupa istirahat yaa.",
        ]
        for sample in normal_samples:
            self.assertFalse(is_meta_or_reasoning_leak(sample), f"False positive on clean dialogue: {sample}")


if __name__ == "__main__":
    unittest.main()

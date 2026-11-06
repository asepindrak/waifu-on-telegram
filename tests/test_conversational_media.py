import unittest
from persona_manager import PersonaManager
from bot import sanitize_chat_caption


class TestConversationalMedia(unittest.TestCase):
    def setUp(self):
        self.persona_mgr = PersonaManager()

    def test_pure_media_requests_are_not_conversational(self):
        pure_requests = [
            "pap",
            "pap dong",
            "pap dong sayang",
            "minta pap",
            "minta pap dong",
            "kirim pap dong",
            "pap selfie",
            "pap foto kamu dong",
            "minta foto selfie kamu dong",
            "minta video dong",
            "animasi dong",
            "kirim video dong",
        ]
        for req in pure_requests:
            is_media, media_type = self.persona_mgr.detect_media_request(req)
            self.assertTrue(is_media, f"Should be detected as media: '{req}'")
            is_conv = self.persona_mgr.is_conversational_media_request(req)
            self.assertFalse(is_conv, f"'{req}' should NOT be conversational media request")

    def test_conversational_media_requests_detected(self):
        conv_requests = [
            "aku belum ngantuk, minta pap donk kamu udah mau bobo?",
            "kamu lagi sibuk apa sekarang? boleh minta pap ga?",
            "aku kangen banget nih, kirim pap dong sayang",
            "udah makan malam belum? pap dong lagi ngapain",
            "gimana kuliah hari ini? coba pap dong outfit kamu",
            "kamu lagi ngapain? minta video kamu senyum dong",
        ]
        for req in conv_requests:
            is_media, media_type = self.persona_mgr.detect_media_request(req)
            self.assertTrue(is_media, f"Should be detected as media: '{req}'")
            is_conv = self.persona_mgr.is_conversational_media_request(req)
            self.assertTrue(is_conv, f"'{req}' should be recognized as conversational media request")

    def test_sanitize_chat_caption(self):
        fallback = "Ini pap spesial buat kamu sayang, suka ga? 🥰"

        # Cringe social media greetings stripped
        cap1 = "Halo gaes, ini pap buat kamu ya!"
        self.assertEqual(sanitize_chat_caption(cap1, fallback), "Ini pap buat kamu ya!")

        # Defensive / doubt arguments stripped
        cap2 = "Biar kamu percaya, nih aku fotoin sekarang!"
        self.assertEqual(sanitize_chat_caption(cap2, fallback), "Nih aku fotoin sekarang!")

        # Quotes stripped
        cap3 = '"Malam sayang, ini pap buat nemenin kamu bobo yaa 💕"'
        self.assertEqual(sanitize_chat_caption(cap3, fallback), "Malam sayang, ini pap buat nemenin kamu bobo yaa 💕")

        # Empty or too short falls back
        self.assertEqual(sanitize_chat_caption("", fallback), fallback)
        self.assertEqual(sanitize_chat_caption("   ", fallback), fallback)

    def test_caption_contextual_fallbacks(self):
        # Night / sleep request fallback
        user_night = "aku belum ngantuk, minta pap donk kamu udah mau bobo?"
        u_lower = user_night.lower()
        if any(k in u_lower for k in ["bobo", "tidur", "ngantuk", "malam", "night"]):
            fb = "Ini pap buat nemenin kamu malam ini yaa sayang~ 💕"
        else:
            fb = "Ini pap spesial buat kamu sayang, suka ga? 🥰"
        self.assertEqual(fb, "Ini pap buat nemenin kamu malam ini yaa sayang~ 💕")

        # Morning request fallback
        user_morning = "Pagi sayang, minta pap dong!"
        u_lower = user_morning.lower()
        if any(k in u_lower for k in ["pagi", "morning", "bangun"]):
            fb = "Pagi sayang! Semangat ya hari ini, ini pap manis buat kamu~ 💕"
        else:
            fb = "Ini pap spesial buat kamu sayang, suka ga? 🥰"
        self.assertEqual(fb, "Pagi sayang! Semangat ya hari ini, ini pap manis buat kamu~ 💕")


if __name__ == "__main__":
    unittest.main()

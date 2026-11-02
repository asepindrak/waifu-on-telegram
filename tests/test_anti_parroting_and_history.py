import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import bot


class TestAntiParrotingAndConversationHistory(unittest.TestCase):
    def test_is_echo_or_parroting_exact_match(self):
        """Detects exact word-for-word repetition."""
        user = "iya, makan bareng anak2 kantor"
        reply = "iya, makan bareng anak2 kantor"
        self.assertTrue(bot.is_echo_or_parroting(reply, user))

        # With different casing and punctuation
        reply2 = "Iya, makan bareng anak2 kantor!"
        self.assertTrue(bot.is_echo_or_parroting(reply2, user))

    def test_is_echo_or_parroting_single_word_echo(self):
        """Detects single token echoing from a longer user sentence."""
        user = "nanti mau makan sambil gathering HO jam 4"
        reply = "gathering"
        self.assertTrue(bot.is_echo_or_parroting(reply, user))

        reply_short = "gathering HO"
        self.assertTrue(bot.is_echo_or_parroting(reply_short, user))

    def test_is_echo_or_parroting_allows_natural_conversations(self):
        """Allows creative, normal girlfriend dialogue."""
        user = "nanti mau makan sambil gathering HO jam 4"
        reply = "Wah seru banget tuh gathering di mana sayang? Jangan lupa makan yang kenyang yaa!"
        self.assertFalse(bot.is_echo_or_parroting(reply, user))

        user2 = "lagi ngerjain tugas kampus nih"
        reply2 = "Semangat yaa nugasnya sayang! Nanti kalau udah selesai kabarin aku yaa 💕"
        self.assertFalse(bot.is_echo_or_parroting(reply2, user2))

    def test_contextual_fallback_reaction(self):
        """Provides natural contextual fallback for gathering and food."""
        res_eat = bot.get_contextual_fallback_reaction("nanti mau makan siang")
        self.assertIn("makan", res_eat.lower())

        res_gather = bot.get_contextual_fallback_reaction("ada gathering kantor")
        self.assertIn("kantor", res_gather.lower())

    @patch("bot.bot")
    @patch("bot.scheduled_buffer")
    @patch("bot.idle_engine")
    @patch("bot.is_port_listening", return_value=False)
    def test_scheduled_greeting_saved_to_history(self, mock_port, mock_idle, mock_buf, mock_bot):
        """Scheduled greeting is saved to persona conversation history so subsequent replies have context."""
        uid = 555444
        bot.persona_mgr.clear_history(uid)
        mock_idle.is_llm_sleeping = True
        mock_buf.get_message.return_value = "Udah jam makan siang nih! Jangan lupa makan yaa."

        bot.send_scheduled_greeting(uid, "lunch")

        history = bot.persona_mgr.get_chat_history(uid)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["role"], "assistant")
        self.assertIn("makan siang", history[0]["content"].lower())


if __name__ == "__main__":
    unittest.main()

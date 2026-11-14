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
        reply = "Wah seru banget tuh gathering di mana? Jangan lupa makan yang kenyang yaa!"
        self.assertFalse(bot.is_echo_or_parroting(reply, user))

        user2 = "lagi ngerjain tugas kampus nih"
        reply2 = "Semangat yaa nugasnya! Nanti kalau udah selesai kabarin aku yaa 💕"
        self.assertFalse(bot.is_echo_or_parroting(reply2, user2))

        # Empathy mirrors with Indonesian feelings remain allowed
        self.assertFalse(bot.is_echo_or_parroting("Aku juga kangen banget sama kamu kok 💕", "aku kangen banget sama kamu"))

    def test_is_echo_catches_stage_cued_and_filler_copies(self):
        """Detects exact copies wrapped in *action* cues or thin fillers like 'Iya ...'."""
        user = "kamu lagi ngapain sekarang di kamar?"
        self.assertTrue(bot.is_echo_or_parroting("*Hina tersenyum tipis* Kamu lagi ngapain sekarang di kamar?", user))
        self.assertTrue(bot.is_echo_or_parroting("*tersenyum*\n\nIya kamu lagi ngapain sekarang di kamar?", user))

    def test_unwanted_english_translation_guard(self):
        """Detects Huihui replying in English or translating Indonesian user messages into English."""
        user_id_msg = "lagi ngapain nih kamu, udah makan belum?"
        self.assertTrue(bot.is_unwanted_english_or_translation("What are you doing right now, have you eaten yet?", user_id_msg, bot_language="id"))
        self.assertTrue(bot.is_unwanted_english_or_translation("*Hina tersenyum* What are you doing right now?", user_id_msg, bot_language="auto"))
        self.assertTrue(bot.is_unwanted_english_or_translation("Translation: What are you doing?", user_id_msg, bot_language="id"))

        # Casual Indonesian with English loanwords remains allowed
        self.assertFalse(bot.is_unwanted_english_or_translation("*tersenyum* Oke aku lagi meeting jam 3 nanti ya!", user_id_msg, bot_language="id"))
        # Explicit English mode or explicit translation request stays allowed
        self.assertFalse(bot.is_unwanted_english_or_translation("I am relaxing at home right now!", "what are you doing?", bot_language="en"))
        self.assertFalse(bot.is_unwanted_english_or_translation("It means let's eat lunch.", "translate ke bahasa inggris dong", bot_language="id"))

    def test_lu_llm_client_suppresses_think_and_blocks_echo_translation_salvage(self):
        """LocallyUncensoredClient injects /no_think, preserves repetition_penalty on 400, and rejects echo/English quotes in <think>."""
        from lu_llm_client import LocallyUncensoredClient

        client = LocallyUncensoredClient(base_url="http://127.0.0.1:5001/v1", model="Huihui-Qwythos-9B.gguf")

        # 1. Closing </think> without opening <think> strips reasoning prefix cleanly
        resp_closing = MagicMock(status_code=200)
        resp_closing.json.return_value = {
            "choices": [{"message": {"content": "The user asks what I am doing.\n</think>\n*nyengir*\n\nLagi santai di kos nih, kamu udah makan?"}}]
        }
        # 2. Unclosed <think> quoting user's message & English translation returns "" instead of echoing/translating
        resp_unclosed = MagicMock(status_code=200)
        resp_unclosed.json.return_value = {
            "choices": [{"message": {"content": "<think>\nThe user said \"kamu lagi ngapain sekarang\" which means \"what are you doing right now\"..."}}]
        }
        # 3. 400 on chat_template_kwargs retries WITHOUT popping repetition_penalty
        resp_400 = MagicMock(status_code=400)
        posted_payloads = []

        def _post_side_effect(*args, **kwargs):
            posted_payloads.append(dict(kwargs.get("json", {})))
            if len(posted_payloads) == 1:
                return resp_400
            if len(posted_payloads) == 2:
                return resp_closing
            return resp_unclosed

        with patch("requests.post", side_effect=_post_side_effect):
            reply1, _ = client.chat([
                {"role": "system", "content": "Kamu Hina."},
                {"role": "user", "content": "kamu lagi ngapain sekarang"},
            ], max_tokens=120)
            self.assertEqual(reply1, "*nyengir*\n\nLagi santai di kos nih, kamu udah makan?")
            self.assertIn("/no_think", posted_payloads[0]["messages"][0]["content"])
            self.assertNotIn("chat_template_kwargs", posted_payloads[1])
            self.assertIn("repetition_penalty", posted_payloads[1])

            reply2, _ = client.chat([
                {"role": "system", "content": "Kamu Hina."},
                {"role": "user", "content": "kamu lagi ngapain sekarang"},
            ], max_tokens=120)
            self.assertEqual(reply2, "")

    @patch("bot.is_port_listening", return_value=False)
    def test_contextual_fallback_reaction(self, mock_port):
        """Verifies static cheesy fallbacks are disabled in favor of real LLM retry."""
        res_eat = bot.get_contextual_fallback_reaction("nanti mau makan siang")
        self.assertIsNone(res_eat)

        res_gather = bot.get_contextual_fallback_reaction("ada gathering kantor")
        self.assertIsNone(res_gather)

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

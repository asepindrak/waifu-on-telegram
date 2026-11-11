import unittest
from unittest.mock import MagicMock, patch

from persona_manager import PersonaManager
from student_schedule import detect_contextual_activity_and_outfit


class TestPhotoChatCaptionConsistency(unittest.TestCase):
    def setUp(self):
        self.persona_mgr = PersonaManager()
        self.hina_reply = (
            "Hina tersenyum ceria sambil memegang sekantong jajanan hangat di pinggir jalan\n\n"
            "Aku lagi keliling nyobain aneka jajanan street food viral dekat kampus bareng tim liputan "
            "festival nih, Adens! Seru banget dan makanannya enak-enak semua sampai bikin kenyang. "
            "Kamu sendiri lagi santai atau ada kesibukan sore ini?"
        )

    def test_extract_scene_no_false_kitchen_from_makanannya(self):
        """Substring 'makan' inside 'makanannya' must never trigger 'kitchen' scene; street food takes precedence."""
        scene = self.persona_mgr.extract_contextual_scene(
            user_text="hina lagi apa?",
            conversational_reply=self.hina_reply
        )
        self.assertNotIn("kitchen", scene.lower())
        self.assertNotIn("lecture hall", scene.lower())
        self.assertIn("street food", scene.lower())

    def test_extract_scene_uses_llm_first_for_conversational_reply(self):
        """When conversational_reply and llm_client are provided, LLM extracts the exact narrative scene first."""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = (
            "standing outdoors at lively street food stalls near campus, holding paper bag of warm snacks, warm evening lights",
            ""
        )
        scene = self.persona_mgr.extract_contextual_scene(
            user_text="hina lagi apa?",
            llm_client=mock_llm,
            conversational_reply=self.hina_reply
        )
        mock_llm.chat.assert_called_once()
        self.assertIn("street food", scene.lower())
        self.assertNotIn("kitchen", scene.lower())

    def test_student_schedule_word_boundaries_and_street_food(self):
        """Student schedule matches street food rather than kitchen or false substrings like 'kos' in 'kosong'."""
        ctx = detect_contextual_activity_and_outfit(self.hina_reply)
        self.assertNotIn("dapur", ctx["activity"].lower())
        self.assertNotIn("kitchen", ctx["scene"].lower())
        self.assertTrue(ctx["is_public"])
        self.assertIn("street food", ctx["scene"].lower())

        # 'kosong' must NOT match 'kos' (home)
        ctx_kosong = detect_contextual_activity_and_outfit("kursinya masih kosong nih di kafe", persona_key="hina")
        self.assertIn("cafe", ctx_kosong["scene"].lower())

    def test_craft_visual_prompt_word_boundaries(self):
        """Substrings inside Indonesian words ('catatan', 'pesta', 'kacang') must not disable negative guards."""
        prompt, neg, _, _ = self.persona_mgr.craft_visual_prompt_full(
            "lagi makan sate kacang di pesta festival sambil bawa catatan"
        )
        self.assertIn("cat", neg.lower())
        self.assertIn("phone", neg.lower())

    @patch("bot.safe_send_message")
    @patch("bot.bot")
    @patch("bot.llm_client")
    @patch("bot.media_engine")
    @patch("bot.idle_engine")
    def test_process_photo_request_preserves_scene_override_and_original_query(
        self, mock_idle, mock_media, mock_llm, mock_bot, mock_safe_send
    ):
        """process_photo_request preserves scene_override, avoids kitchen override, and passes original_user_text to caption LLM."""
        import bot
        mock_msg = MagicMock()
        mock_msg.chat.id = 777111
        mock_msg.from_user.id = 777111

        mock_media.generate_photo.return_value = (b"fake_jpg_bytes", "ComfyUI")
        mock_llm.chat.return_value = ("Nih jajanan street food-nya masih hangat banget! Kamu mau juga nggak?", "")

        expected_scene = "standing outdoors at street food stalls near campus, holding paper bag of snacks, evening lights"
        with patch.object(bot.persona_mgr, "get_chat_history", return_value=[]), \
             patch.object(bot.persona_mgr, "increase_affinity", return_value=10), \
             patch.object(bot.persona_mgr, "add_message") as mock_add_msg, \
             patch.object(bot.persona_mgr, "notify_photo_delivered"), \
             patch.object(bot.waifu_status_tracker, "record_photo_event"):

            bot.process_photo_request(
                mock_msg,
                user_text=self.hina_reply,
                conversational_reply=self.hina_reply,
                is_followup=True,
                scene_override=expected_scene,
                original_user_text="hina lagi apa?"
            )
            import time
            for _ in range(40):
                if mock_add_msg.called and mock_llm.chat.called:
                    break
                time.sleep(0.05)

        self.assertTrue(mock_media.generate_photo.called)

        # Verify image generation received the exact street food scene, NOT kitchen!
        gen_kwargs = mock_media.generate_photo.call_args.kwargs
        self.assertEqual(gen_kwargs["scene"], expected_scene)
        self.assertNotIn("kitchen", gen_kwargs["scene"].lower())

        # Verify caption prompt received original user question and street food setting
        cap_messages = mock_llm.chat.call_args[0][0]
        last_user_prompt = cap_messages[-1]["content"]
        self.assertIn("hina lagi apa?", last_user_prompt)
        self.assertIn(expected_scene, last_user_prompt)
        self.assertIn("STRICT CONSISTENCY RULE", last_user_prompt)

        # Verify is_followup=True did not duplicate a fake [Requested photo: ...] user turn
        for call_args in mock_add_msg.call_args_list:
            role, content = call_args[0][1], call_args[0][2]
            if role == "user":
                self.assertNotIn("[Requested photo:", content)

    @patch("bot.safe_send_message")
    @patch("bot.bot")
    @patch("bot.llm_client")
    @patch("bot.media_engine")
    @patch("bot.idle_engine")
    def test_caption_matches_bra_panties_chat_when_pap_requested_separately(
        self, mock_idle, mock_media, mock_llm, mock_bot, mock_safe_send
    ):
        """When user asks 'pap dong' separately after chat mentions BH + celana dalam, caption LLM gets outfit + is_nsfw=True and fallback matches."""
        import bot
        mock_msg = MagicMock()
        mock_msg.message = None
        mock_msg.chat.id = 777222
        mock_msg.from_user.id = 777222

        mock_media.generate_photo.return_value = (b"fake_jpg_bytes", "ComfyUI")
        # Return AI refusal to verify outfit-aware fallback triggers cleanly as well
        mock_llm.chat.return_value = ("I'm sorry, I cannot fulfill this request.", "")

        hist = [
            {"role": "assistant", "content": "Aku lagi pakai piyama nih."},
            {"role": "assistant", "content": "Sekarang cuma pake BH sama celana dalam aja nih 😳"},
        ]
        with patch.object(bot.persona_mgr, "get_chat_history", return_value=hist), \
             patch.object(bot.persona_mgr, "get_user_outfit", return_value=("default", "Otomatis")), \
             patch.object(bot.persona_mgr, "get_undress_stage", return_value=2), \
             patch.object(bot.persona_mgr, "increase_affinity", return_value=10), \
             patch.object(bot.persona_mgr, "add_message"), \
             patch.object(bot.persona_mgr, "notify_photo_delivered"), \
             patch.object(bot.waifu_status_tracker, "record_photo_event"):

            bot.process_photo_request(mock_msg, user_text="pap dong")
            import time
            for _ in range(40):
                if mock_bot.send_photo.called and mock_llm.chat.called:
                    break
                time.sleep(0.05)

        self.assertTrue(mock_llm.chat.called)
        cap_call = mock_llm.chat.call_args
        self.assertTrue(cap_call.kwargs.get("is_nsfw"))
        last_user_prompt = cap_call[0][0][-1]["content"]
        self.assertIn("BH & Celana Dalam", last_user_prompt)
        self.assertIn("STRICT CONSISTENCY RULE", last_user_prompt)

        sent_caption = mock_bot.send_photo.call_args.kwargs.get("caption", "")
        self.assertIn("BH sama celana dalam", sent_caption)


if __name__ == "__main__":
    unittest.main()

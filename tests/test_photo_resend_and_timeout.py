import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
import io

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import optimize_image_for_telegram, USER_LAST_PHOTO_CONTEXT, callback_resend_photo


class TestPhotoResendAndTimeout(unittest.TestCase):
    def setUp(self):
        USER_LAST_PHOTO_CONTEXT.clear()

    def test_optimize_image_for_telegram_resizes_large_images(self):
        # Create a large 2000x2000 image
        img = Image.new("RGB", (2000, 2000), color="pink")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        original_bytes = buf.getvalue()

        optimized = optimize_image_for_telegram(original_bytes, max_dimension=1280, quality=85)
        self.assertLess(len(optimized), len(original_bytes))

        # Check dimension of optimized image
        im_opt = Image.open(io.BytesIO(optimized))
        self.assertLessEqual(max(im_opt.size), 1280)
        self.assertEqual(im_opt.format, "JPEG")

    def test_optimize_image_for_telegram_handles_empty_or_small(self):
        # Empty bytes
        self.assertEqual(optimize_image_for_telegram(b""), b"")

        # Small already-optimized JPEG
        img = Image.new("RGB", (200, 200), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        small_bytes = buf.getvalue()

        result = optimize_image_for_telegram(small_bytes, max_dimension=1280, quality=85)
        self.assertIsNotNone(result)

    def test_callback_resend_photo_with_cached_image(self):
        img = Image.new("RGB", (100, 100), color="green")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        test_bytes = buf.getvalue()

        user_id = 123456
        USER_LAST_PHOTO_CONTEXT[user_id] = {
            "img_bytes": test_bytes,
            "full_caption": "Foto manis untukmu~ 💕",
            "clean_caption": "Foto manis untukmu~ 💕",
            "chat_id": 999888
        }

        mock_call = MagicMock()
        mock_call.from_user.id = user_id
        mock_call.message.chat.id = 999888
        mock_call.message.message_id = 555
        mock_call.data = "resend_photo:last"

        with patch("bot.is_authorized", return_value=True), \
             patch("bot.bot.answer_callback_query") as mock_ans, \
             patch("bot.bot.send_photo") as mock_send_photo, \
             patch("bot.bot.delete_message") as mock_del_msg:
            callback_resend_photo(mock_call)

            mock_ans.assert_called_once()
            self.assertIn("Mengirimkan ulang foto", mock_ans.call_args[0][1])
            mock_send_photo.assert_called_once()
            call_kwargs = mock_send_photo.call_args[1]
            self.assertEqual(call_kwargs.get("caption"), "Foto manis untukmu~ 💕")
            mock_del_msg.assert_called_once_with(999888, 555)

    def test_callback_resend_photo_when_cache_empty(self):
        mock_call = MagicMock()
        mock_call.from_user.id = 999999
        mock_call.message.chat.id = 111222
        mock_call.data = "resend_photo:last"

        with patch("bot.is_authorized", return_value=True), \
             patch("bot.bot.answer_callback_query") as mock_ans, \
             patch("bot.process_photo_request") as mock_process:
            callback_resend_photo(mock_call)

            mock_ans.assert_called_once()
            self.assertIn("kedaluwarsa", mock_ans.call_args[0][1])
            mock_process.assert_called_once_with(mock_call, "last")

    def test_persona_body_and_maturity_consistency(self):
        from persona_manager import PersonaManager
        pm = PersonaManager()

        # Test Runa
        prompt_r, neg_r, _, _ = pm.craft_visual_prompt_full("foto selfie santai", user_id=123)
        self.assertIn("young adult anime woman", prompt_r)
        self.assertIn("C-cup medium breasts", prompt_r)
        self.assertIn("(child:1.4)", neg_r)
        self.assertIn("(bad breasts:1.3)", neg_r)

        # Test Akira
        pm.active_key = "akira"
        prompt_a, neg_a, _, _ = pm.craft_visual_prompt_full("foto selfie santai", user_id=123)
        self.assertIn("mature adult anime woman", prompt_a)
        self.assertIn("D-cup large breasts", prompt_a)
        self.assertIn("(child:1.4)", neg_a)
        self.assertIn("(bad breasts:1.3)", neg_a)


if __name__ == "__main__":
    unittest.main()


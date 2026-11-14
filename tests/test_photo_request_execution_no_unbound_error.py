import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import process_photo_request, photo_tracker


def _create_dummy_jpeg() -> bytes:
    img = Image.new("RGB", (100, 100), color="pink")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestPhotoRequestExecutionNoUnboundError(unittest.TestCase):
    def setUp(self):
        photo_tracker._active_generating.clear()
        photo_tracker._active_resending.clear()
        self.dummy_jpeg = _create_dummy_jpeg()

    def tearDown(self):
        photo_tracker._active_generating.clear()
        photo_tracker._active_resending.clear()

    def test_process_photo_request_normal_pap_no_unbound_local_error(self):
        """Ensure /pap or normal photo request does not raise UnboundLocalError for is_nude_override."""
        mock_msg = MagicMock()
        mock_msg.message = None
        mock_msg.chat.id = 12345
        mock_msg.from_user.id = 67890
        mock_msg.message_id = 101

        with patch("bot.ChatActionLoop"), \
             patch("threading.Thread", side_effect=lambda target, **k: MagicMock(start=target)), \
             patch("bot.media_engine.generate_photo", return_value=(self.dummy_jpeg, "AGY Engine")), \
             patch("bot.bot.send_photo") as mock_send_photo, \
             patch("bot.safe_reply_to"), \
             patch("bot.safe_send_message"), \
             patch("bot.llm_client.chat", return_value=("Ini fotoku sayang~ 💕", 10)):

            process_photo_request(mock_msg, "kirim foto kamu dong", is_followup=False)

            self.assertNotIn(67890, photo_tracker._active_generating)
            mock_send_photo.assert_called_once()
            args, kwargs = mock_send_photo.call_args
            self.assertEqual(args[0], 12345)
            self.assertIn("Ini fotoku sayang", kwargs.get("caption", ""))

    def test_process_photo_request_followup_sfw_no_unbound_local_error(self):
        """Ensure followup photo request with is_followup=True runs smoothly."""
        mock_msg = MagicMock()
        mock_msg.message = None
        mock_msg.chat.id = 12345
        mock_msg.from_user.id = 67890
        mock_msg.message_id = 102

        with patch("bot.ChatActionLoop"), \
             patch("threading.Thread", side_effect=lambda target, **k: MagicMock(start=target)), \
             patch("bot.media_engine.generate_photo", return_value=(self.dummy_jpeg, "AGY Engine")), \
             patch("bot.bot.send_photo") as mock_send_photo, \
             patch("bot.safe_reply_to"), \
             patch("bot.safe_send_message"), \
             patch("bot.llm_client.chat", return_value=("Ini fotoku sayang~ 💕", 10)):

            process_photo_request(mock_msg, "foto santai", is_followup=True, is_nude_override=False)

            self.assertNotIn(67890, photo_tracker._active_generating)
            mock_send_photo.assert_called_once()


if __name__ == "__main__":
    unittest.main()

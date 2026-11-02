import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from cli_chat import WaifuCLISession, open_media_file, get_default_user_id
import cli_chat


class TestWaifuCLIChat(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="waifu_cli_test_")
        self.user_id = 778899

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_user_id_resolution(self):
        """Resolves user ID from environment or fallback."""
        with patch.dict(os.environ, {"TELEGRAM_ALLOWED_USER_ID": "6402709138"}):
            uid = get_default_user_id()
            self.assertEqual(uid, 6402709138)

    @patch("cli_chat.open_media_file")
    def test_cli_session_shared_history_and_chat(self, mock_open):
        """CLI chat shares conversation history seamlessly with Telegram storage."""
        session = WaifuCLISession(user_id=self.user_id)
        session.idle_engine.ensure_llm_active = MagicMock()
        session.persona_mgr.clear_history(self.user_id)

        # Mock LLM response
        session.llm_client.chat = MagicMock(return_value=("Wah seru banget tuh kumpul bareng mereka!", 35))

        # Send user message
        session.process_message("Nanti mau makan siang bareng anak kantor")

        # Verify history was saved
        history = session.persona_mgr.get_chat_history(self.user_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Nanti mau makan siang bareng anak kantor")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertIn("seru banget", history[1]["content"])

        # Second session (simulating Telegram or another CLI invocation)
        session2 = WaifuCLISession(user_id=self.user_id)
        history2 = session2.persona_mgr.get_chat_history(self.user_id)
        self.assertEqual(len(history2), 2)
        self.assertEqual(history2[0]["content"], "Nanti mau makan siang bareng anak kantor")

    @patch("cli_chat.open_media_file")
    def test_cli_photo_generation_and_auto_open(self, mock_open):
        """Generates photo and automatically opens it in OS default viewer."""
        session = WaifuCLISession(user_id=self.user_id)
        session.idle_engine.ensure_comfyui_active = MagicMock()
        session.media_engine.generate_photo = MagicMock(return_value=(b"FAKE_JPEG_IMAGE_BYTES", "ComfyUI"))
        session.llm_client.chat = MagicMock(return_value=("Ini foto manis buat kamu!", 15))

        session.handle_photo_request("pap foto dong")

        # Verify auto-open was called with a path in output/
        self.assertTrue(mock_open.called)
        called_path = mock_open.call_args[0][0]
        self.assertTrue(os.path.exists(called_path))
        self.assertTrue(called_path.endswith(".jpg"))

        # Clean up generated file
        try:
            os.remove(called_path)
        except Exception:
            pass

    @patch("subprocess.run")
    def test_open_media_file_non_windows(self, mock_sub):
        """Calls appropriate OS opener on non-Windows platforms."""
        dummy_file = os.path.join(self.test_dir, "test.jpg")
        with open(dummy_file, "wb") as f:
            f.write(b"data")

        with patch("sys.platform", "linux"):
            open_media_file(dummy_file)
            mock_sub.assert_called_with(["xdg-open", dummy_file], check=False)

        with patch("sys.platform", "darwin"):
            open_media_file(dummy_file)
            mock_sub.assert_called_with(["open", dummy_file], check=False)


if __name__ == "__main__":
    unittest.main()

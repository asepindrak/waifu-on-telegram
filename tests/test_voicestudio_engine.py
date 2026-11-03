import os
os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
os.environ["TELEGRAM_ALLOWED_USER_ID"] = "6402709138"

import tempfile
import unittest
from unittest.mock import patch, MagicMock

import persona_manager
from voicestudio_engine import VoiceStudioEngine
from voice_engine import VoiceEngine
import bot


class TestVoiceStudioEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = VoiceStudioEngine(
            server_url="http://127.0.0.1:3900",
            install_dir=self.temp_dir,
            port=3900
        )

    def test_status_structure(self):
        st = self.engine.get_status()
        self.assertIsInstance(st, dict)
        self.assertEqual(st["port"], 3900)
        self.assertEqual(st["url"], "http://127.0.0.1:3900")
        self.assertFalse(st["installed"])
        self.assertFalse(st["running"])

    def test_installation_detection(self):
        # Empty dir -> not installed
        self.assertFalse(self.engine.is_installed())

        # Create backend/main.py
        backend_dir = os.path.join(self.temp_dir, "backend")
        os.makedirs(backend_dir, exist_ok=True)
        with open(os.path.join(backend_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("# Dummy VoiceStudio backend\n")

        self.assertTrue(self.engine.is_installed())

    @patch("requests.post")
    def test_synthesize_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"ID3_DUMMY_MP3_AUDIO_STREAM"
        mock_post.return_value = mock_resp

        out_file = os.path.join(self.temp_dir, "output.mp3")
        res = self.engine.synthesize(
            text="Halo sayang, apa kabar?",
            voice_character="Playful anime girl",
            voice_name="runa",
            speed=1.0,
            output_path=out_file
        )

        self.assertEqual(res, out_file)
        self.assertTrue(os.path.exists(out_file))
        with open(out_file, "rb") as f:
            self.assertEqual(f.read(), b"ID3_DUMMY_MP3_AUDIO_STREAM")

        # Verify payload sent to /v1/audio/speech
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "http://127.0.0.1:3900/v1/audio/speech")
        payload = call_args[1]["json"]
        self.assertEqual(payload["input"], "Halo sayang, apa kabar?")
        self.assertEqual(payload["voice"], "runa")
        self.assertEqual(payload["voice_character"], "Playful anime girl")

    @patch("subprocess.Popen")
    @patch.object(VoiceStudioEngine, "is_port_listening", side_effect=[False, True])
    def test_start_service(self, mock_port, mock_popen):
        # Mark as installed
        backend_dir = os.path.join(self.temp_dir, "backend")
        os.makedirs(backend_dir, exist_ok=True)
        with open(os.path.join(backend_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("# dummy")

        ok = self.engine.start_service()
        self.assertTrue(ok)
        self.assertTrue(mock_popen.called)

    @patch("shutil.which", return_value="git.exe")
    @patch("subprocess.run")
    def test_install_method(self, mock_run, mock_which):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        with patch.object(self.engine, "is_installed", return_value=True):
            ok, msg = self.engine.install()
            self.assertTrue(ok)
            self.assertIn("berhasil", msg.lower())


class TestPersonaVoiceSpecs(unittest.TestCase):
    def test_all_personas_have_voice_specs(self):
        """Verifies that all 5 personas have rich voice characterization for VoiceStudio."""
        expected_personas = ["runa", "akira", "hina", "shiro", "yume"]
        for p_key in expected_personas:
            p = persona_manager.DEFAULT_PERSONAS.get(p_key)
            self.assertIsNotNone(p, f"Persona {p_key} not found in DEFAULT_PERSONAS")
            self.assertIn("voice_character", p, f"Missing voice_character in {p_key}")
            self.assertIn("voicestudio_voice", p, f"Missing voicestudio_voice in {p_key}")
            self.assertIn("voicestudio_speed", p, f"Missing voicestudio_speed in {p_key}")
            self.assertGreater(len(p["voice_character"]), 20)

    def test_voice_engine_fallback_when_voicestudio_offline(self):
        """Verifies that VoiceEngine falls back to Edge-TTS when VoiceStudio is offline."""
        ve = VoiceEngine(voice_backend="voicestudio")
        with patch("voicestudio_engine.voicestudio_engine.is_service_running", return_value=False), \
             patch("edge_tts.Communicate") as mock_comm:

            async def fake_save(dest):
                with open(dest, "wb") as f:
                    f.write(b"EDGE_TTS_FALLBACK_AUDIO")

            mock_instance = MagicMock()
            mock_instance.save = fake_save
            mock_comm.return_value = mock_instance

            res = ve.generate_voice_note("Halo manis, ini suara fallback!")
            self.assertIsNotNone(res)
            self.assertTrue(os.path.exists(res))
            if os.path.exists(res):
                os.remove(res)


class TestBotVoiceMenu(unittest.TestCase):
    def test_bot_toggle_voice_engine(self):
        call = MagicMock()
        call.from_user.id = 6402709138
        call.message.chat.id = 6402709138
        call.message.message_id = 999

        with patch("bot.is_authorized", return_value=True), \
             patch.object(bot.bot, "answer_callback_query"), \
             patch("bot.update_env_variable"), \
             patch("bot.show_voice_settings_menu"):

            # 1. Toggle from edge-tts to voicestudio
            os.environ["VOICE_BACKEND"] = "edge-tts"
            bot.callback_toggle_voice_engine(call)
            self.assertEqual(os.environ.get("VOICE_BACKEND"), "voicestudio")

            # 2. Toggle back to edge-tts
            bot.callback_toggle_voice_engine(call)
            self.assertEqual(os.environ.get("VOICE_BACKEND"), "edge-tts")


if __name__ == "__main__":
    unittest.main()

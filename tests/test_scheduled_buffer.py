import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from scheduled_buffer import ScheduledMessageBuffer
from idle_engine import IdleEngine


class TestScheduledBufferAndGamingProtection(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_file = os.path.join(self.tmp_dir.name, "test_buffer.json")
        self.buffer = ScheduledMessageBuffer(buffer_file=self.tmp_file)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_buffer_add_get_and_count(self):
        user_id = 999888
        self.assertFalse(self.buffer.has_message(user_id, "morning"))
        self.assertEqual(self.buffer.count(user_id, "morning"), 0)

        # Add message
        self.buffer.add_message(user_id, "morning", "Selamat pagi sayang!")
        self.assertTrue(self.buffer.has_message(user_id, "morning"))
        self.assertEqual(self.buffer.count(user_id, "morning"), 1)

        # Retrieve FIFO
        msg = self.buffer.get_message(user_id, "morning")
        self.assertEqual(msg, "Selamat pagi sayang!")
        self.assertFalse(self.buffer.has_message(user_id, "morning"))
        self.assertEqual(self.buffer.count(user_id, "morning"), 0)

        # Empty retrieval returns None
        empty_msg = self.buffer.get_message(user_id, "morning")
        self.assertIsNone(empty_msg)

    def test_replenish_skips_when_llm_sleeping(self):
        """When LLM is sleeping, replenish_buffer_if_llm_active does NOT call llm_client.chat."""
        mock_llm = MagicMock()
        mock_idle = MagicMock()
        mock_idle.is_llm_sleeping = True

        with patch("scheduled_buffer.is_port_listening", return_value=False):
            self.buffer.replenish_buffer_if_llm_active(
                user_id=12345,
                persona={"name": "Runa", "system_instruction": "Test"},
                persona_key="runa",
                llm_client=mock_llm,
                idle_engine=mock_idle
            )
            mock_llm.chat.assert_not_called()

    def test_replenish_runs_when_llm_awake(self):
        """When LLM is awake and listening, replenish_buffer_if_llm_active generates missing messages."""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = ("Semangat pagi hari ini yaa!", 10)
        mock_idle = MagicMock()
        mock_idle.is_llm_sleeping = False

        with patch("scheduled_buffer.is_port_listening", return_value=True):
            self.buffer.replenish_buffer_if_llm_active(
                user_id=12345,
                persona={"name": "Runa", "system_instruction": "Test"},
                persona_key="runa",
                llm_client=mock_llm,
                idle_engine=mock_idle
            )
            self.assertTrue(mock_llm.chat.called)
            self.assertTrue(self.buffer.has_message(12345, "morning"))

    def test_idle_engine_blocks_background_automation_wake(self):
        """idle_engine.ensure_llm_active(is_user_chat=False) blocks waking when sleeping."""
        engine = IdleEngine(enabled=True)
        engine.is_llm_sleeping = True

        with patch.object(engine, "is_llm_ready", return_value=False):
            with patch.object(engine, "wake_llm") as mock_wake:
                ok = engine.ensure_llm_active(is_user_chat=False)
                self.assertFalse(ok)
                mock_wake.assert_not_called()


if __name__ == "__main__":
    unittest.main()

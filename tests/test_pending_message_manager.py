"""
tests/test_pending_message_manager.py
Tests the PendingMessageManager, retry queue, disk persistence,
and service recovery trigger hooks.
"""

import os
import time
import tempfile
import unittest
from unittest.mock import MagicMock

from pending_message_manager import PendingMessageManager
from coding_engine import get_coding_engine


class TestPendingMessageManager(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.tmp_dir, "pending_retries_test.json")
        self.mgr = PendingMessageManager(storage_path=self.storage_path, max_age_seconds=10)

    def tearDown(self):
        if os.path.exists(self.storage_path):
            try:
                os.remove(self.storage_path)
            except Exception:
                pass
        try:
            os.rmdir(self.tmp_dir)
        except Exception:
            pass

    def test_record_and_pop_pending_message(self):
        mock_msg = MagicMock()
        mock_msg.chat.id = 12345
        mock_msg.from_user.id = 67890
        mock_msg.message_id = 101

        self.mgr.record_failed_message(
            message=mock_msg,
            user_text="coba run project nya aku mau lihat",
            is_voice=False,
            error="Connection refused port 8001"
        )

        self.assertEqual(self.mgr.get_pending_count(), 1)
        self.assertEqual(self.mgr.get_all_pending_chats(), [12345])

        popped = self.mgr.pop_pending_message(12345)
        self.assertIsNotNone(popped)
        self.assertEqual(popped["user_text"], "coba run project nya aku mau lihat")
        self.assertEqual(popped["chat_id"], 12345)
        self.assertEqual(popped["user_id"], 67890)
        self.assertEqual(self.mgr.get_pending_count(), 0)

    def test_persistence_across_instances(self):
        mock_msg = MagicMock()
        mock_msg.chat.id = 99999
        mock_msg.from_user.id = 88888
        mock_msg.message_id = 555

        self.mgr.record_failed_message(
            message=mock_msg,
            user_text="Halo apa kabar Akira?",
            is_voice=True,
            error="Read timeout"
        )

        # Create new manager with same storage file
        mgr2 = PendingMessageManager(storage_path=self.storage_path, max_age_seconds=10)
        self.assertEqual(mgr2.get_pending_count(), 1)
        popped = mgr2.pop_pending_message(99999)
        self.assertIsNotNone(popped)
        self.assertEqual(popped["user_text"], "Halo apa kabar Akira?")
        self.assertTrue(popped["is_voice"])

    def test_expiration_of_old_messages(self):
        mock_msg = MagicMock()
        mock_msg.chat.id = 11111
        mock_msg.from_user.id = 22222
        mock_msg.message_id = 1

        # Manager with 1 second expiry
        fast_mgr = PendingMessageManager(storage_path=self.storage_path, max_age_seconds=1)
        fast_mgr.record_failed_message(mock_msg, "pesan lama", error="timeout")
        time.sleep(1.2)

        # Should be expired
        self.assertEqual(fast_mgr.get_pending_count(), 0)
        popped = fast_mgr.pop_pending_message(11111)
        self.assertIsNone(popped)

    def test_retry_all_pending_execution(self):
        mock_msg = MagicMock()
        mock_msg.chat.id = 77777
        mock_msg.from_user.id = 77777
        mock_msg.message_id = 99

        self.mgr.record_failed_message(mock_msg, "bikin landing page", error="LLM down")

        mock_bot = MagicMock()
        processed_calls = []

        def mock_process(msg, text, is_voice=False):
            processed_calls.append((msg, text, is_voice))

        self.mgr.retry_all_pending(mock_bot, mock_process)

        # Allow background thread to execute
        time.sleep(0.5)

        self.assertEqual(len(processed_calls), 1)
        self.assertEqual(processed_calls[0][1], "bikin landing page")
        self.assertEqual(self.mgr.get_pending_count(), 0)

    def test_coding_trigger_matches_run_project(self):
        ce = get_coding_engine()
        self.assertTrue(ce.is_coding_intent("coba run project nya aku mau lihat"))
        self.assertTrue(ce.is_coding_intent("jalankan project web"))
        self.assertTrue(ce.is_coding_intent("preview project ini"))
        self.assertTrue(ce.is_coding_intent("start server web"))
        self.assertTrue(ce.is_coding_intent("coba run"))


if __name__ == "__main__":
    unittest.main()

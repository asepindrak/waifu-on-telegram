import unittest
import time
from unittest.mock import MagicMock, patch
from telebot import types
from telebot.handler_backends import CancelUpdate

import bot
from bot import (
    PhotoGenerationTracker,
    CallbackAntiSpamMiddleware,
    callback_resend_photo,
    callback_regen_photo,
    process_photo_request,
    USER_LAST_PHOTO_CONTEXT,
    photo_tracker
)


class TestButtonAntiSpamAndPhotoSingleFlight(unittest.TestCase):
    def setUp(self):
        USER_LAST_PHOTO_CONTEXT.clear()
        self.tracker = PhotoGenerationTracker(timeout=2.0)
        self.mock_bot = MagicMock()
        self.middleware = CallbackAntiSpamMiddleware(self.mock_bot, self.tracker, debounce_seconds=1.0)

    def test_photo_tracker_acquire_and_release(self):
        uid = 991122
        # First acquire succeeds
        self.assertTrue(self.tracker.acquire_generation(uid))
        self.assertTrue(self.tracker.is_generating(uid))

        # Concurrent acquire must FAIL
        self.assertFalse(self.tracker.acquire_generation(uid))

        # After release, acquire succeeds again
        self.tracker.release_generation(uid)
        self.assertFalse(self.tracker.is_generating(uid))
        self.assertTrue(self.tracker.acquire_generation(uid))

    def test_photo_tracker_timeout_self_healing(self):
        uid = 991133
        tracker_short = PhotoGenerationTracker(timeout=0.1)
        self.assertTrue(tracker_short.acquire_generation(uid))
        time.sleep(0.15)
        # Lock should have expired and auto-cleared
        self.assertFalse(tracker_short.is_generating(uid))
        self.assertTrue(tracker_short.acquire_generation(uid))

    def test_photo_tracker_resend_lock(self):
        uid = 991144
        self.assertTrue(self.tracker.acquire_resend(uid))
        self.assertTrue(self.tracker.is_resending(uid))
        self.assertFalse(self.tracker.acquire_resend(uid))

        self.tracker.release_resend(uid)
        self.assertFalse(self.tracker.is_resending(uid))
        self.assertTrue(self.tracker.acquire_resend(uid))

    def test_middleware_blocks_rapid_double_clicks(self):
        uid = 991155
        mid = 101

        call1 = types.CallbackQuery.de_json({
            'id': 'cb1',
            'from': {'id': uid, 'is_bot': False, 'first_name': 'Tester'},
            'message': {'message_id': mid, 'chat': {'id': uid, 'type': 'private'}, 'date': int(time.time())},
            'data': 'open_hangout_menu',
            'chat_instance': 'inst1'
        })
        call2 = types.CallbackQuery.de_json({
            'id': 'cb2',
            'from': {'id': uid, 'is_bot': False, 'first_name': 'Tester'},
            'message': {'message_id': mid, 'chat': {'id': uid, 'type': 'private'}, 'date': int(time.time())},
            'data': 'open_hangout_menu',
            'chat_instance': 'inst1'
        })

        # First click passes
        res1 = self.middleware.pre_process(call1, {})
        self.assertIsNone(res1)

        # Rapid second click on the exact same button MUST be cancelled
        res2 = self.middleware.pre_process(call2, {})
        self.assertIsInstance(res2, CancelUpdate)
        self.mock_bot.answer_callback_query.assert_called()
        self.assertIn("sedang diproses", self.mock_bot.answer_callback_query.call_args[1]["text"])

    def test_middleware_blocks_photo_buttons_when_generation_in_progress(self):
        uid = 991166
        mid = 202
        # Mark user as currently generating a photo
        self.tracker.acquire_generation(uid)

        # User tries clicking 'Pose Lain'
        call_regen = types.CallbackQuery.de_json({
            'id': 'cb_regen',
            'from': {'id': uid, 'is_bot': False, 'first_name': 'Tester'},
            'message': {'message_id': mid, 'chat': {'id': uid, 'type': 'private'}, 'date': int(time.time())},
            'data': 'regen_photo:last',
            'chat_instance': 'inst2'
        })

        res = self.middleware.pre_process(call_regen, {})
        self.assertIsInstance(res, CancelUpdate)
        self.mock_bot.answer_callback_query.assert_called()
        self.assertIn("lagi diambil", self.mock_bot.answer_callback_query.call_args[1]["text"])

        # User tries clicking 'Kirim Ulang Foto' while generating
        call_resend = types.CallbackQuery.de_json({
            'id': 'cb_resend',
            'from': {'id': uid, 'is_bot': False, 'first_name': 'Tester'},
            'message': {'message_id': mid, 'chat': {'id': uid, 'type': 'private'}, 'date': int(time.time())},
            'data': 'resend_photo:last',
            'chat_instance': 'inst2'
        })
        res_resend = self.middleware.pre_process(call_resend, {})
        self.assertIsInstance(res_resend, CancelUpdate)

    def test_callback_resend_photo_neutralizes_buttons_and_prevents_duplicates(self):
        uid = 991177
        chat_id = 991177
        mid = 303

        USER_LAST_PHOTO_CONTEXT[uid] = {
            "img_bytes": b"fake_jpeg_bytes",
            "full_caption": "Foto manis",
            "clean_caption": "Foto manis"
        }

        call = types.CallbackQuery.de_json({
            'id': 'cb_resend_test',
            'from': {'id': uid, 'is_bot': False, 'first_name': 'Tester'},
            'message': {'message_id': mid, 'chat': {'id': chat_id, 'type': 'private'}, 'date': int(time.time())},
            'data': 'resend_photo:last',
            'chat_instance': 'inst3'
        })

        with patch("bot.is_authorized", return_value=True), \
             patch("bot.bot.answer_callback_query") as mock_ans, \
             patch("bot.bot.edit_message_reply_markup") as mock_edit_markup, \
             patch("bot.bot.send_photo") as mock_send_photo, \
             patch("bot.bot.delete_message") as mock_del:

            callback_resend_photo(call)

            # Reply markup must be immediately cleared so user cannot tap again
            mock_edit_markup.assert_called_with(chat_id, mid, reply_markup=None)
            mock_send_photo.assert_called_once()
            # The prompt message is deleted after successful resend
            mock_del.assert_called_with(chat_id, mid)

    def test_process_photo_request_single_flight_per_user(self):
        uid = 991188
        msg = MagicMock(spec=types.Message)
        msg.from_user = types.User(uid, False, 'Tester')
        msg.chat = types.Chat(uid, 'private')

        # First request acquires lock
        self.assertTrue(photo_tracker.acquire_generation(uid))

        # A concurrent request to process_photo_request must be dropped immediately without starting a new thread
        with patch("threading.Thread") as mock_thread, \
             patch("bot.safe_reply_to") as mock_reply:

            process_photo_request(msg, "pap dong")
            mock_thread.assert_not_called()
            mock_reply.assert_called_once()
            self.assertIn("foto sebelumnya lagi aku siapkan", mock_reply.call_args[0][1])

        # Release lock
        photo_tracker.release_generation(uid)


if __name__ == '__main__':
    unittest.main()

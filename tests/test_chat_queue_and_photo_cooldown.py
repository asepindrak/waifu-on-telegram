import unittest
from unittest.mock import MagicMock, patch
import time
import threading

import bot
from persona_manager import PersonaManager, CAMERA_COMPOSITION_PRESETS


class TestChatQueueAndPhotoCooldown(unittest.TestCase):
    def setUp(self):
        self.mgr = PersonaManager()

    def test_camera_composition_rotation(self):
        """Tests that camera compositions rotate and avoid repeating consecutive angles."""
        user_id = 999123
        seen_angles = []

        # Generate 6 prompts in a row
        for i in range(6):
            prompt, neg, is_nude, outfit_name = self.mgr.craft_visual_prompt_full(
                user_text="ngobrol santai aja",
                user_id=user_id,
                scene_override="aesthetic cafe table"
            )
            recent = self.mgr.get_recent_angles(user_id)
            self.assertTrue(len(recent) > 0)
            current_angle = recent[-1]
            seen_angles.append(current_angle)

            # Ensure current angle is within CAMERA_COMPOSITION_PRESETS
            self.assertIn(current_angle, CAMERA_COMPOSITION_PRESETS)

            # Ensure current angle is in the visual prompt
            self.assertIn(current_angle, prompt)

            # Ensure it did not repeat the immediately preceding angle
            if i > 0:
                self.assertNotEqual(seen_angles[i], seen_angles[i - 1], "Consecutive photo repeated identical camera composition!")

    def test_explicit_angle_and_pose_preserved(self):
        """Tests that explicit camera angle requests from user override the rotation pool."""
        user_id = 999456
        prompt, _, _, _ = self.mgr.craft_visual_prompt_full(
            user_text="coba foto dari belakang sambil tengkurap",
            user_id=user_id
        )
        # Should contain rear view and stomach lying pose
        self.assertIn("back view", prompt.lower())
        self.assertIn("lying on stomach", prompt.lower())

    def test_chat_queue_debouncing(self):
        """Tests that multiple quick messages within debounce window are aggregated into a single turn."""
        queue = bot.ChatQueueManager(debounce_window=0.1, max_debounce_window=0.5)

        dispatched = []
        event = threading.Event()

        def mock_execute(msg, text, is_voice=False):
            dispatched.append((msg, text, is_voice))
            event.set()

        msg1 = MagicMock()
        msg1.from_user.id = 1001
        msg1.text = "wah baju nya bagus banget cocok sama kamu"

        msg2 = MagicMock()
        msg2.from_user.id = 1001
        msg2.text = "boleh, aku meluncur kesana sekarang ya"

        queue.enqueue(msg1, msg1.text, is_voice=False, execute_fn=mock_execute)
        time.sleep(0.03)  # Rapidly send second message before debounce fires
        queue.enqueue(msg2, msg2.text, is_voice=False, execute_fn=mock_execute)

        self.assertTrue(event.wait(timeout=1.0), "Debounce queue worker did not trigger in time!")

        self.assertEqual(len(dispatched), 1, "Expected exactly 1 aggregated turn, but got multiple!")
        dispatched_msg, dispatched_text, is_voice = dispatched[0]
        self.assertEqual(dispatched_msg, msg2)  # Should target latest bubble
        self.assertIn("wah baju nya bagus banget cocok sama kamu", dispatched_text)
        self.assertIn("boleh, aku meluncur kesana sekarang ya", dispatched_text)

    def test_chat_queue_fifo_sequential_execution(self):
        """Tests that messages arriving while bot is actively processing are executed strictly sequentially."""
        queue = bot.ChatQueueManager(debounce_window=0.05, max_debounce_window=0.2)

        execution_order = []
        busy_event = threading.Event()
        release_event = threading.Event()
        finish_event = threading.Event()

        def slow_execute(msg, text, is_voice=False):
            execution_order.append(f"start:{text}")
            if text == "turn 1":
                busy_event.set()
                release_event.wait(timeout=2.0)
            execution_order.append(f"end:{text}")
            if text == "turn 2":
                finish_event.set()

        msg = MagicMock()
        msg.from_user.id = 2002

        # Dispatch turn 1
        queue.enqueue(msg, "turn 1", is_voice=False, execute_fn=slow_execute)
        self.assertTrue(busy_event.wait(timeout=1.0))

        # While turn 1 is running, send turn 2
        queue.enqueue(msg, "turn 2", is_voice=False, execute_fn=slow_execute)

        # Allow turn 1 to complete
        release_event.set()

        self.assertTrue(finish_event.wait(timeout=2.0))

        # Check order: turn 1 must start and end BEFORE turn 2 starts
        self.assertEqual(execution_order, [
            "start:turn 1",
            "end:turn 1",
            "start:turn 2",
            "end:turn 2"
        ])

    def test_auto_photo_cooldown_suppression(self):
        """Tests that auto/spontaneous photos are suppressed if turn or time cooldown hasn't passed."""
        uid = 3003
        bot.USER_CONVERSATION_TURNS[uid] = 10
        bot.USER_LAST_AUTO_PHOTO_TURN[uid] = 9   # only 1 turn ago (needs >= 3)
        bot.USER_LAST_AUTO_PHOTO_TIME[uid] = time.time()  # just now (needs >= 60s)

        # Test cooldown logic directly
        cur_turn = bot.USER_CONVERSATION_TURNS[uid]
        last_turn = bot.USER_LAST_AUTO_PHOTO_TURN[uid]
        last_time = bot.USER_LAST_AUTO_PHOTO_TIME[uid]
        now_ts = time.time()

        turn_diff = cur_turn - last_turn
        time_diff = now_ts - last_time

        turn_cooldown_ok = turn_diff >= bot.MIN_AUTO_PHOTO_TURN_COOLDOWN
        time_cooldown_ok = time_diff >= bot.MIN_AUTO_PHOTO_TIME_COOLDOWN

        self.assertFalse(turn_cooldown_ok, "Turn cooldown should have failed (diff < 3)")
        self.assertFalse(time_cooldown_ok, "Time cooldown should have failed (diff < 60s)")

        # Fast forward turns and time
        bot.USER_CONVERSATION_TURNS[uid] = 14
        bot.USER_LAST_AUTO_PHOTO_TIME[uid] = time.time() - 75.0

        cur_turn = bot.USER_CONVERSATION_TURNS[uid]
        last_turn = bot.USER_LAST_AUTO_PHOTO_TURN[uid]
        last_time = bot.USER_LAST_AUTO_PHOTO_TIME[uid]
        now_ts = time.time()

        turn_diff = cur_turn - last_turn
        time_diff = now_ts - last_time

        turn_cooldown_ok = turn_diff >= bot.MIN_AUTO_PHOTO_TURN_COOLDOWN
        time_cooldown_ok = time_diff >= bot.MIN_AUTO_PHOTO_TIME_COOLDOWN

        self.assertTrue(turn_cooldown_ok, "Turn cooldown should have passed")
        self.assertTrue(time_cooldown_ok, "Time cooldown should have passed")


if __name__ == "__main__":
    unittest.main()

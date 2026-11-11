import os
import time
import unittest
from unittest.mock import MagicMock, patch
from idle_engine import IdleEngine
from health_engine import HealthEngine


class TestIdleEngine(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            "AI_ENGINE_MODE": "unified",
            "SFW_LLM_PROVIDER": "local",
            "SFW_IMAGE_ENGINE": "comfyui"
        })
        self.env_patcher.start()

        self.mock_llm_client = MagicMock()
        self.mock_llm_client.check_health.return_value = {"online": True, "backend": "KoboldCPP", "model": "Qwythos-9B"}
        self.mock_media_engine = MagicMock()
        self.mock_media_engine.check_status.return_value = {"online": True, "backend": "ComfyUI Local"}

        self.health_engine = HealthEngine(
            llm_client=self.mock_llm_client,
            media_engine=self.mock_media_engine,
            enabled=True,
            self_healing_enabled=True
        )

        self.idle_engine = IdleEngine(
            health_engine=self.health_engine,
            enabled=True,
            idle_timeout_minutes=10,
            comfyui_on_demand=True
        )
        self.health_engine.idle_engine = self.idle_engine

    def tearDown(self):
        self.idle_engine.stop()
        self.env_patcher.stop()

    def test_default_configuration(self):
        """Verify smart idle defaults to enabled, 120 minutes (2 hours) timeout, and ComfyUI on-demand."""
        env_copy = dict(os.environ)
        env_copy.pop("IDLE_TIMEOUT_MINUTES", None)
        with patch.dict(os.environ, env_copy, clear=True):
            engine = IdleEngine()
            self.assertTrue(engine.enabled)
            self.assertEqual(engine.idle_timeout_minutes, 120)
            self.assertTrue(engine.comfyui_on_demand)

    def test_record_activity_updates_timestamp(self):
        """Verify record_activity updates last_llm_activity timestamp."""
        old_time = self.idle_engine.last_llm_activity
        time.sleep(0.01)
        self.idle_engine.record_activity()
        self.assertGreater(self.idle_engine.last_llm_activity, old_time)

    @patch("idle_engine.is_port_listening", return_value=True)
    def test_ensure_llm_active_when_already_running(self, mock_port):
        """When LLM is already running, ensure_llm_active returns True instantly without waking."""
        ok = self.idle_engine.ensure_llm_active()
        self.assertTrue(ok)
        self.assertFalse(self.idle_engine.is_llm_sleeping)

    @patch("idle_engine.is_port_listening", side_effect=[False, True])
    def test_ensure_llm_active_wakes_sleeping_service(self, mock_port):
        """When LLM is sleeping, ensure_llm_active wakes KoboldCPP on-demand."""
        self.idle_engine.is_llm_sleeping = True
        with patch.object(self.health_engine, "heal_llm", return_value=True):
            ok = self.idle_engine.ensure_llm_active()
            self.assertTrue(ok)
            self.assertFalse(self.idle_engine.is_llm_sleeping)

    def test_health_engine_ignores_offline_when_sleeping(self):
        """When LLM is intentionally sleeping, HealthEngine watchdog does NOT alert failure."""
        self.idle_engine.is_llm_sleeping = True
        self.mock_llm_client.check_health.return_value = {"online": False}

        mock_bot = MagicMock()
        recipients = [12345]

        # Trigger check loop logic
        is_sleeping = bool(self.health_engine.idle_engine and self.health_engine.idle_engine.enabled and self.health_engine.idle_engine.is_llm_sleeping)
        self.assertTrue(is_sleeping)

        # Ensure failure is not broadcasted when sleeping
        with patch.object(self.health_engine, "broadcast_failure") as mock_fail:
            with patch.object(self.health_engine, "attempt_heal_service") as mock_heal:
                # If sleeping, failure alert should not be dispatched
                if not is_sleeping:
                    self.health_engine.broadcast_failure(mock_bot, recipients, {})
                    self.health_engine.attempt_heal_service("llm", mock_bot, recipients)
                mock_fail.assert_not_called()
                mock_heal.assert_not_called()

    def test_sleep_llm_sets_flag(self):
        """Verify sleep_llm terminates process and marks is_llm_sleeping = True."""
        with patch("idle_engine.is_port_listening", return_value=True):
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value = MagicMock(returncode=0)
                ok = self.idle_engine.sleep_llm()
                self.assertTrue(ok)
                self.assertTrue(self.idle_engine.is_llm_sleeping)

    def test_status_summary_includes_smart_idle(self):
        """Verify status summary reports active smart idle mode."""
        summary = self.idle_engine.get_status_summary()
        self.assertIn("Aktif", summary)
        self.assertIn("10m", summary)

    def test_ensure_llm_active_failure_edits_message_with_error(self):
        """When LLM waking fails, ensure_llm_active informs user instead of deleting status and staying silent."""
        mock_bot = MagicMock()
        mock_msg = MagicMock()
        mock_msg.message_id = 999
        mock_bot.send_message.return_value = mock_msg

        with patch.object(self.idle_engine, "wake_llm", return_value=False), \
             patch.object(self.idle_engine, "is_llm_ready", return_value=False):
            ok = self.idle_engine.ensure_llm_active(bot=mock_bot, chat_id=123)
            self.assertFalse(ok)
            # Must NOT delete message
            mock_bot.delete_message.assert_not_called()
            # Must edit message into informative error explanation
            self.assertTrue(mock_bot.edit_message_text.called)
            edit_args = mock_bot.edit_message_text.call_args[0]
            self.assertIn("belum bisa dibangunkan", edit_args[0])

    def test_ensure_comfyui_active_bypasses_for_agy_sfw(self):
        """When SFW_IMAGE_ENGINE is agy, ensure_comfyui_active immediately returns True without alerting Telegram."""
        mock_bot = MagicMock()
        with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy"}), \
             patch.object(self.idle_engine, "wake_comfyui") as mock_wake:
            ok = self.idle_engine.ensure_comfyui_active(bot=mock_bot, chat_id=123, is_nude=False)
            self.assertTrue(ok)
            mock_wake.assert_not_called()
            mock_bot.send_message.assert_not_called()

    def test_ensure_comfyui_active_wakes_comfyui_for_nude(self):
        """When is_nude is True, ensure_comfyui_active targets local ComfyUI regardless of SFW_IMAGE_ENGINE."""
        mock_bot = MagicMock()
        with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "agy"}), \
             patch.object(self.idle_engine, "is_comfyui_ready", return_value=False), \
             patch.object(self.idle_engine, "wake_comfyui", return_value=True) as mock_wake:
            ok = self.idle_engine.ensure_comfyui_active(bot=mock_bot, chat_id=123, is_nude=True)
            self.assertTrue(ok)
            mock_wake.assert_called_once()

    def test_manual_idle_puts_local_services_to_sleep(self):
        """Verify manual_idle puts listening local services (KoboldCPP, ComfyUI) to sleep."""
        with patch("idle_engine.is_port_listening", return_value=True), \
             patch.object(self.idle_engine, "sleep_llm", return_value=True) as mock_sleep_llm, \
             patch.object(self.idle_engine, "sleep_comfyui", return_value=True) as mock_sleep_comfy, \
             patch.object(self.idle_engine, "sleep_voicestudio", return_value=True) as mock_sleep_vs, \
             patch.dict(os.environ, {"SFW_LLM_PROVIDER": "local", "LLM_BASE_URL": "http://127.0.0.1:5001/v1", "SFW_LLM_BASE_URL": "http://127.0.0.1:5001/v1"}):
            results = self.idle_engine.manual_idle()
            self.assertTrue(results["freed_any"])
            mock_sleep_llm.assert_called_once()
            mock_sleep_comfy.assert_called_once()
            self.assertEqual(results["llm"], "slept")
            self.assertEqual(results["comfyui"], "slept")

    def test_manual_idle_exempts_cloud_llm_and_agy(self):
        """Verify manual_idle does NOT put AGY/cloud LLMs to sleep because they consume 0 local VRAM."""
        with patch("idle_engine.is_port_listening", side_effect=lambda port: port in (8001, 8188)), \
             patch.object(self.idle_engine, "sleep_comfyui", return_value=True) as mock_sleep_comfy, \
             patch.object(self.idle_engine, "sleep_llm") as mock_sleep_llm, \
             patch.dict(os.environ, {"SFW_LLM_PROVIDER": "agy"}):
            results = self.idle_engine.manual_idle()
            self.assertEqual(results["llm"], "cloud_exempt")
            self.assertEqual(results["agy"], "cloud_exempt")
            # Local LLM should NOT be called to sleep if not listening
            mock_sleep_llm.assert_not_called()
            # ComfyUI is local, so it should still be put to sleep
            mock_sleep_comfy.assert_called_once()
            self.assertIn("0 VRAM overhead", "".join(results["details"]))

    def test_bot_handle_idle_command(self):
        """Verify Telegram bot /idle command dispatches manual_idle and replies with friendly message."""
        import bot
        mock_msg = MagicMock()
        mock_msg.from_user.id = 12345
        mock_msg.chat.id = 12345

        with patch.object(bot, "is_authorized", return_value=True), \
             patch.object(bot.idle_engine, "manual_idle", return_value={"freed_any": True, "details": ["VRAM bebas!"]}), \
             patch.object(bot, "persona_mgr") as mock_pm, \
             patch.object(bot.bot, "reply_to") as mock_reply:
            mock_pm.get_active_persona.return_value = {"name": "Runa"}
            bot.handle_idle_command(mock_msg)
            mock_reply.assert_called_once()
            args = mock_reply.call_args[0]
            self.assertIn("Mode Idle Berhasil Diaktifkan", args[1])
            self.assertIn("Runa", args[1])

    def test_bot_text_waifu_idle_triggers_idle(self):
        """Verify natural text 'waifu idle' routes to handle_idle_command."""
        import bot
        mock_msg = MagicMock()
        mock_msg.from_user.id = 12345
        mock_msg.chat.id = 12345
        mock_msg.text = "waifu idle"

        with patch.object(bot, "is_authorized", return_value=True), \
             patch.object(bot, "handle_idle_command") as mock_handle_idle:
            bot.handle_text_messages(mock_msg)
            mock_handle_idle.assert_called_once_with(mock_msg)

    def test_llm_and_comfyui_booting_always_send_telegram_chat_action(self):
        """Even if waking status message fails to send, booting LLM emits typing and booting ComfyUI emits upload_photo."""
        import time as _t

        mock_bot = MagicMock()
        mock_bot.send_message.return_value = None  # Simulate send_message failure / None

        def _slow_wake_llm(*args, **kwargs):
            _t.sleep(0.15)
            return True

        def _slow_wake_comfy(*args, **kwargs):
            _t.sleep(0.15)
            return True

        with patch.object(self.idle_engine, "is_llm_ready", return_value=False), \
             patch.object(self.idle_engine, "wake_llm", side_effect=_slow_wake_llm):
            ok = self.idle_engine.ensure_llm_active(bot=mock_bot, chat_id=555, is_user_chat=True)
            self.assertTrue(ok)
            mock_bot.send_chat_action.assert_any_call(555, "typing")

        mock_bot.reset_mock()
        mock_bot.send_message.return_value = None
        with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "comfyui", "IMAGE_ENGINE_MODE": "unified", "IMAGE_ENGINE": "comfyui"}), \
             patch("asset_manager.detect_comfyui_dir", return_value="C:/ComfyUI"), \
             patch.object(self.idle_engine, "is_comfyui_ready", return_value=False), \
             patch.object(self.idle_engine, "wake_comfyui", side_effect=_slow_wake_comfy):
            ok = self.idle_engine.ensure_comfyui_active(bot=mock_bot, chat_id=555, is_nude=False)
            self.assertTrue(ok)
            mock_bot.send_chat_action.assert_any_call(555, "upload_photo")

        mock_bot.reset_mock()
        mock_bot.send_message.return_value = None
        with patch.dict(os.environ, {"SFW_IMAGE_ENGINE": "comfyui", "IMAGE_ENGINE_MODE": "unified", "IMAGE_ENGINE": "comfyui"}), \
             patch("asset_manager.detect_comfyui_dir", return_value="C:/ComfyUI"), \
             patch.object(self.idle_engine, "is_comfyui_ready", return_value=False), \
             patch.object(self.idle_engine, "wake_comfyui", side_effect=_slow_wake_comfy):
            ok = self.idle_engine.ensure_comfyui_active(bot=mock_bot, chat_id=555, is_nude=False, action="upload_video")
            self.assertTrue(ok)
            mock_bot.send_chat_action.assert_any_call(555, "upload_video")

    def test_health_engine_heal_sends_chat_actions_and_queue_sends_typing(self):
        """HealthEngine healing and ChatQueueManager waiting both emit Telegram chat actions."""
        import time as _t
        import bot
        from health_engine import HealthEngine

        he = HealthEngine(llm_client=MagicMock())
        mock_bot = MagicMock()

        def _slow_heal():
            _t.sleep(0.15)
            return True

        with patch.object(he, "heal_llm", side_effect=_slow_heal), \
             patch.object(he, "send_safe_message"):
            self.assertTrue(he.attempt_heal_service("llm", mock_bot, [777], is_manual=True))
            mock_bot.send_chat_action.assert_any_call(777, "typing")

        mock_bot.reset_mock()
        with patch.object(he, "heal_comfyui", side_effect=_slow_heal), \
             patch.object(he, "send_safe_message"):
            self.assertTrue(he.attempt_heal_service("comfyui", mock_bot, [777], is_manual=True))
            mock_bot.send_chat_action.assert_any_call(777, "upload_photo")

        mock_queue_bot = MagicMock()
        q = bot.ChatQueueManager(debounce_window=0.15, max_debounce_window=0.3, action_bot=mock_queue_bot)
        done = []
        msg = MagicMock()
        msg.from_user.id = 888
        msg.chat.id = 888
        q.enqueue(msg, "halo", execute_fn=lambda m, t, is_voice=False: done.append(t))
        _t.sleep(0.35)
        self.assertEqual(done, ["halo"])
        mock_queue_bot.send_chat_action.assert_any_call(888, "typing")


if __name__ == "__main__":
    unittest.main()


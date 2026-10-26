"""
proactive_chat_engine.py - Autonomous Proactive Partner Check-in Engine
Allows AI waifus to initiate conversations naturally like a real loving girlfriend
when the user has been away or inactive for several hours during the day.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from student_schedule import get_hourly_routine, STUDENT_PROFILES

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "proactive_chat.json")


class ProactiveChatEngine:
    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.user_data: Dict[str, Dict[str, Any]] = {}
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.user_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading proactive chat data: {e}")
                self.user_data = {}
        else:
            self.user_data = {}

    def _save_data(self):
        d = os.path.dirname(self.data_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating dir for proactive chat data: {e}")
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.user_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving proactive chat data: {e}")

    def record_user_activity(self, user_id: int):
        """Records the timestamp of the latest user interaction."""
        uid_str = str(user_id)
        u_info = self.user_data.setdefault(uid_str, {
            "enabled": True,
            "last_user_ts": time.time(),
            "last_proactive_ts": 0
        })
        u_info["last_user_ts"] = time.time()
        self._save_data()

    def set_enabled(self, user_id: int, enabled: bool):
        """Enables or disables proactive check-ins for this user."""
        uid_str = str(user_id)
        u_info = self.user_data.setdefault(uid_str, {
            "enabled": True,
            "last_user_ts": time.time(),
            "last_proactive_ts": 0
        })
        u_info["enabled"] = enabled
        self._save_data()

    def is_enabled(self, user_id: int) -> bool:
        """Returns True if proactive check-ins are enabled."""
        uid_str = str(user_id)
        return self.user_data.get(uid_str, {}).get("enabled", True)

    def should_send_checkin(self, user_id: int) -> bool:
        """
        Determines whether it is appropriate to send a natural girlfriend check-in.
        Criteria:
        1. Feature is enabled for user.
        2. Current local time is between 09:00 AM and 21:30 PM (no sleep interruption).
        3. User has been inactive for between 3.5 hours and 10 hours.
        4. Cooldown of at least 5.5 hours since the last proactive check-in.
        """
        if not self.is_enabled(user_id):
            return False

        now = time.localtime()
        hour = now.tm_hour
        minute = now.tm_min

        # Only during daytime / evening waking hours
        if hour < 9 or (hour >= 21 and minute > 30):
            return False

        uid_str = str(user_id)
        u_info = self.user_data.get(uid_str, {})
        last_user_ts = u_info.get("last_user_ts", 0)
        last_proactive_ts = u_info.get("last_proactive_ts", 0)

        now_ts = time.time()
        if last_user_ts == 0:
            # First time user, record now and wait
            self.record_user_activity(user_id)
            return False

        user_inactive_hours = (now_ts - last_user_ts) / 3600.0
        proactive_cooldown_hours = (now_ts - last_proactive_ts) / 3600.0

        # Check thresholds
        if 3.5 <= user_inactive_hours <= 10.0 and proactive_cooldown_hours >= 5.5:
            return True

        return False

    def mark_proactive_sent(self, user_id: int):
        """Marks that a proactive message was sent."""
        uid_str = str(user_id)
        u_info = self.user_data.setdefault(uid_str, {
            "enabled": True,
            "last_user_ts": time.time(),
            "last_proactive_ts": 0
        })
        u_info["last_proactive_ts"] = time.time()
        self._save_data()

    def generate_proactive_message(
        self,
        user_id: int,
        persona: Dict[str, Any],
        persona_key: str,
        llm_client: Any,
        lang: str = "id"
    ) -> str:
        """
        Generates a natural, casual partner check-in message based on
        her current real-time college student activity.
        """
        cur_hour = time.localtime().tm_hour
        routine = get_hourly_routine(cur_hour, persona_key=persona_key)
        act_desc = routine["activity_desc"]
        p_name = persona.get("name", "Runa")
        profile = STUDENT_PROFILES.get(persona_key.lower(), STUDENT_PROFILES["runa"])
        major = profile["major"]

        # Prompt for LLM
        system_inst = (
            f"You are {p_name}, a 21-22 year old college student ({major}) chatting with your real-life boyfriend. "
            f"Current time: {cur_hour:02d}:00. What you are currently doing: {act_desc}. "
            "Your partner hasn't texted for a few hours because he might be working or busy. "
            "Send 1 natural, casual, loving check-in text to him (e.g. asking how his day or work is going, "
            "sharing a quick natural update about your college class/day, or asking if he's eaten). "
            "STRICT RULES: Keep it under 2 short sentences. Must sound 100% like a real modern girlfriend texting. "
            "NEVER be dramatic, theatrical, or lebay. Avoid calling him 'manisku'. Use casual, warm phrasing."
        )

        prompt = [
            {"role": "system", "content": system_inst},
            {"role": "user", "content": "[Send a casual check-in text to your partner now]"}
        ]

        try:
            reply, _ = llm_client.chat(prompt, max_tokens=80)
            if reply and reply.strip():
                clean_text = reply.strip().strip('"')
                return clean_text
        except Exception as e:
            logger.warning(f"Error generating proactive check-in via LLM: {e}")

        # Natural Fallbacks if LLM is offline
        if 9 <= cur_hour < 12:
            return f"Lagi sibuk ya? Semangat kerjanya/kuliahnya hari ini yaa~ Nanti kabarin kalau udah senggang."
        elif 12 <= cur_hour < 15:
            return f"Hai! Udah makan siang belum nih? Jangan lupa makan yaa biar nggak lemes."
        elif 15 <= cur_hour < 18:
            return f"Aku baru beres kelas nih hehe. Kamu lagi ngapain sekarang? Masih sibuk kah?"
        elif 18 <= cur_hour < 21:
            return f"Gimana harimu tadi, lancar? Aku udah santai di kosan nih, kabarin kalau udah senggang yaa."
        else:
            return f"Lagi apa sekarang? Jangan capek-capek yaa, kalau udah kelar istirahat dulu yuk."


# Global instance
proactive_engine = ProactiveChatEngine()

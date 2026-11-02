"""
scheduled_buffer.py - Pre-generation Buffer for Scheduled & Automated Messages
Protects PC users from in-game lag and frame drops by generating scheduled greetings
(morning, lunch, bedtime, and proactive check-ins) ONLY when the LLM is already active,
caching them for later dispatch without waking KoboldCPP while user is gaming.
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ScheduledBuffer")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BUFFER_FILE = os.path.join(PROJECT_ROOT, "data", "scheduled_message_buffer.json")


def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.3) -> bool:
    """Checks whether a TCP port is open."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


class ScheduledMessageBuffer:
    def __init__(self, buffer_file: str = DEFAULT_BUFFER_FILE):
        self.buffer_file = buffer_file
        self.lock = threading.Lock()
        self.buffer: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self._load_buffer()

    def _load_buffer(self):
        with self.lock:
            if os.path.exists(self.buffer_file):
                try:
                    with open(self.buffer_file, "r", encoding="utf-8") as f:
                        self.buffer = json.load(f)
                except Exception as e:
                    logger.warning(f"Error loading scheduled message buffer: {e}")
                    self.buffer = {}
            else:
                self.buffer = {}

    def _save_buffer(self):
        d = os.path.dirname(self.buffer_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
        try:
            with open(self.buffer_file, "w", encoding="utf-8") as f:
                json.dump(self.buffer, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving scheduled message buffer: {e}")

    def has_message(self, user_id: int, msg_type: str) -> bool:
        """Checks if a pre-generated message of msg_type exists for user_id."""
        with self.lock:
            uid_str = str(user_id)
            items = self.buffer.get(uid_str, {}).get(msg_type, [])
            return len(items) > 0

    def get_message(self, user_id: int, msg_type: str) -> Optional[str]:
        """Pops and returns the oldest pre-generated message for msg_type, or None if buffer is empty."""
        with self.lock:
            uid_str = str(user_id)
            user_bucket = self.buffer.get(uid_str, {})
            items = user_bucket.get(msg_type, [])
            if items:
                msg_obj = items.pop(0)
                self._save_buffer()
                logger.info(f"✓ Dispatched buffered {msg_type} message for user {user_id} (0% GPU/VRAM load, 0 lag).")
                return msg_obj.get("text")
            return None

    def add_message(self, user_id: int, msg_type: str, text: str, max_items: int = 3):
        """Adds a pre-generated message to the queue."""
        clean = text.strip().strip('"').strip("'")
        if not clean:
            return
        with self.lock:
            uid_str = str(user_id)
            if uid_str not in self.buffer:
                self.buffer[uid_str] = {}
            if msg_type not in self.buffer[uid_str]:
                self.buffer[uid_str][msg_type] = []

            items = self.buffer[uid_str][msg_type]
            # Avoid duplicate identical text
            if not any(item.get("text") == clean for item in items):
                items.append({
                    "text": clean,
                    "created_at": time.time()
                })
                if len(items) > max_items:
                    items.pop(0)
                self._save_buffer()
                logger.info(f"✓ Cached pre-generated {msg_type} greeting for user {user_id} (Buffer count: {len(items)})")

    def count(self, user_id: int, msg_type: Optional[str] = None) -> int:
        """Returns total buffered messages for user."""
        with self.lock:
            uid_str = str(user_id)
            user_bucket = self.buffer.get(uid_str, {})
            if msg_type:
                return len(user_bucket.get(msg_type, []))
            return sum(len(lst) for lst in user_bucket.values())

    def get_status_summary(self, user_id: int) -> str:
        """Returns diagnostic status of buffered messages for this user."""
        m = self.count(user_id, "morning")
        l = self.count(user_id, "lunch")
        n = self.count(user_id, "night")
        p = self.count(user_id, "proactive")
        total = m + l + n + p
        return f"{total} pesan tersimpan (Pagi: {m}, Siang: {l}, Malam: {n}, Proaktif: {p}) • Gaming Protection Aktif"

    def replenish_buffer_if_llm_active(
        self,
        user_id: int,
        persona: Dict[str, Any],
        persona_key: str,
        llm_client: Any,
        idle_engine: Any = None,
        lang: str = "id",
        story_engine: Any = None
    ):
        """
        Opportunistically replenishes the buffer ONLY IF KoboldCPP LLM is currently awake & active.
        If KoboldCPP is sleeping or offline, this immediately aborts and NEVER wakes it up.
        """
        # Strict Gaming Protection Check: LLM must already be awake
        if idle_engine and getattr(idle_engine, "is_llm_sleeping", False):
            logger.debug("ScheduledBuffer: LLM is sleeping. Skipping pre-generation to protect gaming performance.")
            return

        if not is_port_listening(5001):
            logger.debug("ScheduledBuffer: Port 5001 not listening. Skipping pre-generation.")
            return

        if not llm_client or not hasattr(llm_client, "chat"):
            return

        p_name = persona.get("name", "Waifu")
        sys_instruction = persona.get("system_instruction", "")

        # Retrieve today's story episode for realistic context injection
        story_hint = ""
        if story_engine and hasattr(story_engine, "get_today_story"):
            try:
                ep = story_engine.get_today_story(persona_key)
                if ep:
                    story_hint = f" Today's activity: {ep.get('day_theme', '')} ({ep.get('key_activity', '')}). Naturally reference this if appropriate."
            except Exception:
                pass

        targets = [
            ("morning", f"It is 7:00 AM morning. Write 1-2 cheerful, warm, and natural sentences wishing them a wonderful day. Use 'aku' and 'kamu'. Avoid unprompted pet names like 'sayang'.{story_hint}"),
            ("lunch", f"It is 12:30 PM lunch break. Write 1-2 friendly, caring sentences reminding them to take a break and eat lunch. Use 'aku' and 'kamu'. Avoid unprompted pet names.{story_hint}"),
            ("night", f"It is 10:00 PM bedtime. Write 1-2 warm, gentle sentences reminding them to rest well. Use 'aku' and 'kamu'. Avoid unprompted pet names.{story_hint}"),
            ("proactive", f"You are {p_name} chatting via message. Send 1 natural, casual check-in text asking how their day is going or sharing a quick update about your day. Under 2 short sentences. Use 'aku' and 'kamu'.{story_hint}")
        ]

        for msg_type, prompt_desc in targets:
            # Check if this type already has at least 1 ready message
            if self.count(user_id, msg_type) >= 1:
                continue

            # Double check LLM is still awake before each prompt
            if idle_engine and getattr(idle_engine, "is_llm_sleeping", False):
                break

            try:
                lang_instruction = ""
                if lang == "ja":
                    lang_instruction = " Respond in natural Japanese (日本語)."
                elif lang == "en":
                    lang_instruction = " Respond in natural English."
                elif lang == "id":
                    lang_instruction = " Respond in natural Indonesian (Bahasa Indonesia santai & akrab)."

                messages = [
                    {"role": "system", "content": sys_instruction + lang_instruction},
                    {"role": "user", "content": prompt_desc}
                ]
                reply, _ = llm_client.chat(messages, max_tokens=90, temperature=0.7)
                if reply and reply.strip():
                    self.add_message(user_id, msg_type, reply.strip())
                    time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Pre-generation of {msg_type} skipped: {e}")
                break


# Global singleton
scheduled_buffer = ScheduledMessageBuffer()

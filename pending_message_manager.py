"""
pending_message_manager.py - Resilient Pending Chat Retry Manager
Ensures user chat messages that failed due to temporary LLM offline / timeout
are not dropped, but stored and automatically retried once the LLM service recovers.
"""

import os
import time
import json
import logging
import threading
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger("PendingMessageManager")


class PendingMessageManager:
    """
    Manages pending messages that failed during LLM downtime.
    When LLM recovers (via Self-Healing, Watchdog, or manual intervention),
    these messages are retrieved and re-dispatched so the conversation resumes seamlessly.
    """

    def __init__(self, storage_path: Optional[str] = None, max_age_seconds: int = 900):
        self.max_age_seconds = max_age_seconds  # Default 15 minutes
        self.max_retries = 2
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "pending_chat_retries.json"
        )
        self._pending: Dict[int, Dict[str, Any]] = {}  # chat_id -> data
        self._chat_failure_history: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._retrying_chats = set()  # prevent duplicate simultaneous retries
        self._load_from_disk()

    def _load_from_disk(self):
        """Loads non-expired pending messages from disk storage on startup."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    now = time.time()
                    for chat_id_str, item in data.items():
                        try:
                            cid = int(chat_id_str)
                            if now - item.get("failed_at", 0) <= self.max_age_seconds:
                                self._pending[cid] = item
                        except Exception:
                            continue
        except Exception as e:
            logger.debug(f"Could not load pending retries from disk: {e}")

    def _save_to_disk(self):
        """Persists pending messages to disk storage (excluding non-serializable objects)."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            serializable = {}
            now = time.time()
            for cid, item in self._pending.items():
                if now - item.get("failed_at", 0) <= self.max_age_seconds:
                    copy_item = {k: v for k, v in item.items() if k != "message_obj"}
                    serializable[str(cid)] = copy_item
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not persist pending retries to disk: {e}")

    def record_failed_message(
        self,
        message,
        user_text: str,
        is_voice: bool = False,
        error: str = "",
        user_id: Optional[int] = None
    ):
        """Records a user message that failed to get processed due to LLM being unavailable."""
        chat_id = getattr(message.chat, "id", None) if hasattr(message, "chat") else None
        u_id = user_id or (getattr(message.from_user, "id", None) if hasattr(message, "from_user") else None)
        msg_id = getattr(message, "message_id", 0)

        if not chat_id:
            return

        with self._lock:
            hist = self._chat_failure_history.get(chat_id, {})
            last_text = hist.get("last_text", "")
            retry_count = hist.get("retry_count", 0)

            if last_text == user_text:
                retry_count += 1
            else:
                retry_count = 0

            hist["last_text"] = user_text
            hist["retry_count"] = retry_count
            self._chat_failure_history[chat_id] = hist

            # CIRCUIT BREAKER: If this message has failed max_retries, do not re-enqueue!
            if retry_count >= self.max_retries:
                logger.warning(
                    f"🛑 Pending retry circuit breaker triggered for chat_id={chat_id}: "
                    f"Message '{user_text[:40]}...' reached max retry limit ({retry_count}). "
                    f"Dropping permanently to prevent flapping loops."
                )
                self._pending.pop(chat_id, None)
                self._save_to_disk()
                return

            self._pending[chat_id] = {
                "chat_id": chat_id,
                "user_id": u_id,
                "message_id": msg_id,
                "user_text": user_text,
                "is_voice": is_voice,
                "failed_at": time.time(),
                "retry_count": retry_count,
                "error": str(error),
                "message_obj": message
            }
            self._save_to_disk()

        logger.info(
            f"📌 Recorded failed chat to pending retry queue for chat_id={chat_id}, "
            f"user_id={u_id}: '{user_text[:40]}...' (Attempt {retry_count + 1}/{self.max_retries}, Reason: {error})"
        )

    def pop_pending_message(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Pops and returns the pending message for chat_id if within allowed age and retry limits."""
        with self._lock:
            if chat_id not in self._pending:
                return None
            item = self._pending.pop(chat_id)
            self._save_to_disk()

            age = time.time() - item.get("failed_at", 0)
            if age > self.max_age_seconds:
                logger.info(f"Discarding expired pending retry for chat {chat_id} (age: {age:.0f}s)")
                return None

            if item.get("retry_count", 0) >= self.max_retries:
                logger.warning(f"Discarding pending retry for chat {chat_id} (exceeded max retries: {item.get('retry_count')})")
                return None

            return item

    def clear_pending(self, chat_id: int):
        """Clears pending message for chat_id when user resumes normal chat."""
        with self._lock:
            self._pending.pop(chat_id, None)
            self._chat_failure_history.pop(chat_id, None)
            self._save_to_disk()

    def get_pending_count(self) -> int:
        """Returns the count of active pending messages."""
        now = time.time()
        with self._lock:
            return sum(1 for item in self._pending.values() if now - item.get("failed_at", 0) <= self.max_age_seconds)

    def get_all_pending_chats(self) -> List[int]:
        """Returns list of chat_ids currently having pending messages within valid age."""
        now = time.time()
        with self._lock:
            valid_chats = []
            for cid, item in list(self._pending.items()):
                if now - item.get("failed_at", 0) <= self.max_age_seconds:
                    valid_chats.append(cid)
                else:
                    self._pending.pop(cid, None)
            return valid_chats

    def retry_all_pending(self, bot, process_func: Callable):
        """
        Processes all pending messages once LLM recovers.
        Runs each in background thread so caller returns quickly.
        """
        chats = self.get_all_pending_chats()
        if not chats:
            return

        logger.info(f"🔄 Resuming conversation: Retrying {len(chats)} pending chat(s) after LLM recovery...")

        for cid in chats:
            threading.Thread(
                target=self._dispatch_retry,
                args=(cid, bot, process_func),
                daemon=True
            ).start()

    def _dispatch_retry(self, chat_id: int, bot, process_func: Callable):
        """Executes a single chat retry safely."""
        with self._lock:
            if chat_id in self._retrying_chats:
                return
            self._retrying_chats.add(chat_id)

        try:
            item = self.pop_pending_message(chat_id)
            if not item:
                return

            user_text = item.get("user_text", "")
            is_voice = item.get("is_voice", False)
            msg_obj = item.get("message_obj")

            # If message object not preserved in memory, reconstruct synthetic Message
            if not msg_obj:
                msg_obj = self._create_synthetic_message(item)

            logger.info(f"🚀 Retrying pending message for chat {chat_id}: '{user_text[:40]}...'")

            # Rate-limit transition ack: at most once every 300s per chat to prevent alert spam
            with self._lock:
                hist = self._chat_failure_history.get(chat_id, {})
                last_ack = hist.get("last_ack_ts", 0)
                now = time.time()
                should_send_ack = (now - last_ack) >= 300.0
                if should_send_ack:
                    hist["last_ack_ts"] = now
                    self._chat_failure_history[chat_id] = hist

            if should_send_ack:
                try:
                    if bot and chat_id:
                        bot.send_message(
                            chat_id,
                            "🌸 *Server LLM sudah kembali online!* Aku langsung proses pesan kamu yang tadi yaa~ 🥰💕",
                            parse_mode="Markdown",
                            reply_to_message_id=item.get("message_id")
                        )
                except Exception as e_ack:
                    logger.debug(f"Could not send retry acknowledgment: {e_ack}")

            # Invoke main chat processor with bypass_queue=True
            try:
                process_func(msg_obj, user_text, is_voice=is_voice, bypass_queue=True)
            except TypeError:
                process_func(msg_obj, user_text, is_voice=is_voice)

        except Exception as e:
            logger.error(f"Error during pending chat retry for chat {chat_id}: {e}", exc_info=True)
        finally:
            with self._lock:
                self._retrying_chats.discard(chat_id)

    def _create_synthetic_message(self, item: Dict[str, Any]):
        """Constructs a compatible Message object if loaded from serialized disk."""
        from telebot import types
        chat_id = item.get("chat_id")
        user_id = item.get("user_id") or chat_id
        msg_id = item.get("message_id", 0)
        user_text = item.get("user_text", "")

        chat = types.Chat(chat_id, "private")
        user = types.User(user_id, is_bot=False, first_name="User")
        msg = types.Message(msg_id, user, int(time.time()), chat, "text", {}, user_text)
        return msg


_GLOBAL_PENDING_MGR: Optional[PendingMessageManager] = None


def get_pending_message_manager() -> PendingMessageManager:
    global _GLOBAL_PENDING_MGR
    if _GLOBAL_PENDING_MGR is None:
        _GLOBAL_PENDING_MGR = PendingMessageManager()
    return _GLOBAL_PENDING_MGR


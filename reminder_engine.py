import os
import re
import json
import time
import datetime
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _atomic_write_json(file_path: str, data: Any):
    dir_name = os.path.dirname(os.path.abspath(file_path))
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    temp_file = os.path.join(dir_name, f".{os.path.basename(file_path)}.{os.getpid()}_{int(time.time() * 1000)}.tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(temp_file, file_path)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        raise e


class ReminderEngine:
    """Manages persistent personal reminders, schedule parsing, and alert dispatching."""

    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            project_root = os.path.dirname(os.path.abspath(__file__))
            data_file = os.path.join(project_root, "data", "reminders.json")
        self.data_file = data_file
        self.lock = threading.Lock()
        self.reminders: List[Dict[str, Any]] = []
        self.load_data()

    def _ensure_dir(self):
        d = os.path.dirname(self.data_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating directory {d}: {e}")

    def load_data(self):
        """Loads reminders from JSON storage."""
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, "r", encoding="utf-8") as f:
                        self.reminders = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading reminders from {self.data_file}: {e}")
                    self.reminders = []
            else:
                self._ensure_dir()
                self._save_data_unlocked()

    def _save_data_unlocked(self):
        try:
            _atomic_write_json(self.data_file, self.reminders)
        except Exception as e:
            logger.error(f"Error saving reminders to {self.data_file}: {e}")

    def save_data(self):
        """Saves current reminders list to disk atomically."""
        with self.lock:
            self._save_data_unlocked()

    def add_reminder(
        self,
        user_id: int,
        chat_id: int,
        task: str,
        remind_time: float,
        remind_time_str: str,
        recurring: str = "once"
    ) -> Dict[str, Any]:
        """Creates and stores a new reminder."""
        rem_id = f"rem_{int(time.time())}_{random_suffix()}"
        clean_task = task.strip().rstrip(".!~") or "Hal penting"

        item = {
            "id": rem_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "task": clean_task,
            "remind_time": float(remind_time),
            "remind_time_str": remind_time_str,
            "recurring": recurring,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "triggered": False
        }
        with self.lock:
            self.reminders.append(item)
            self._save_data_unlocked()
        logger.info(f"Reminder added: '{clean_task}' at {remind_time_str} for user {user_id}")
        return item

    def get_active_reminders(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns untriggered reminders, sorted by remind_time ascending."""
        with self.lock:
            res = [r for r in self.reminders if not r.get("triggered")]
            if user_id:
                res = [r for r in res if r.get("user_id") == user_id]
            return sorted(res, key=lambda x: x.get("remind_time", 0))

    def get_due_reminders(self) -> List[Dict[str, Any]]:
        """Returns all reminders that are due for delivery right now."""
        now = time.time()
        with self.lock:
            due = []
            for r in self.reminders:
                if not r.get("triggered") and r.get("remind_time", 0) <= now:
                    due.append(r)
            return due

    def mark_triggered(self, reminder_id: str):
        """Marks reminder as triggered, or advances to next day if daily recurring."""
        with self.lock:
            for r in self.reminders:
                if r.get("id") == reminder_id:
                    if r.get("recurring") == "daily":
                        r["remind_time"] += 86400
                        r["triggered"] = False
                    else:
                        r["triggered"] = True
                    break
            self._save_data_unlocked()

    def snooze_reminder(self, reminder_id: str, minutes: int = 10) -> Optional[Dict[str, Any]]:
        """Snoozes a reminder by N minutes."""
        now = time.time()
        with self.lock:
            for r in self.reminders:
                if r.get("id") == reminder_id:
                    new_time = max(r.get("remind_time", now), now) + (minutes * 60)
                    dt = datetime.datetime.fromtimestamp(new_time)
                    r["remind_time"] = new_time
                    r["remind_time_str"] = f"{minutes}m lagi ({dt.strftime('%H:%M')})"
                    r["triggered"] = False
                    self._save_data_unlocked()
                    return r
            return None

    def delete_reminder(self, reminder_id: str, user_id: Optional[int] = None) -> bool:
        """Removes a reminder by ID."""
        with self.lock:
            initial_len = len(self.reminders)
            self.reminders = [
                r for r in self.reminders
                if not (r.get("id") == reminder_id and (user_id is None or r.get("user_id") == user_id))
            ]
            if len(self.reminders) < initial_len:
                self._save_data_unlocked()
                return True
            return False

    @staticmethod
    def parse_reminder_text(raw_text: str) -> Optional[Tuple[float, str, str]]:
        """
        Parses human-entered reminder text into:
        (remind_epoch_timestamp, formatted_time_label, remaining_task_description)
        """
        text = raw_text.strip()
        if not text:
            return None

        now = datetime.datetime.now()

        # 1. Relative minutes/hours: "10m meeting", "30m", "1h belajar", "45 menit", "2 jam"
        m_rel = re.match(
            r'^(\d+)\s*(m|min|menit|mins|h|hr|hour|hours|jam)\b[\s,:]*(.*)$',
            text,
            re.IGNORECASE
        )
        if m_rel:
            val = int(m_rel.group(1))
            unit = m_rel.group(2).lower()
            task = m_rel.group(3).strip()
            task = re.sub(r'^(?:lagi|nanti|buat|untuk)\b[\s,:]*', '', task, flags=re.IGNORECASE).strip() or "Hal penting"
            if unit in ('m', 'min', 'menit', 'mins'):
                delta = datetime.timedelta(minutes=val)
                lbl = f"{val} menit lagi"
            else:
                delta = datetime.timedelta(hours=val)
                lbl = f"{val} jam lagi"

            target_dt = now + delta
            fmt = target_dt.strftime("%H:%M")
            return target_dt.timestamp(), f"{lbl} ({fmt})", task

        # 2. Besok jam HH:MM: "besok 08:00", "tomorrow 09:30 bangun"
        m_besok = re.match(
            r'^(?:besok|tomorrow)\s*(?:jam|pukul|at)?\s*(\d{1,2})[:.](\d{2})\b[\s,:]*(.*)$',
            text,
            re.IGNORECASE
        )
        if m_besok:
            hh = int(m_besok.group(1))
            mm = int(m_besok.group(2))
            task = m_besok.group(3).strip() or "Hal penting"
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                target_dt = (now + datetime.timedelta(days=1)).replace(
                    hour=hh, minute=mm, second=0, microsecond=0
                )
                return target_dt.timestamp(), f"Besok jam {hh:02d}:{mm:02d}", task

        # 3. Clock time: "15:30", "08.00", "jam 15:30 meeting", "pukul 14.00 telpon"
        m_clock = re.match(
            r'^(?:jam|pukul|at)?\s*(\d{1,2})[:.](\d{2})\b[\s,:]*(.*)$',
            text,
            re.IGNORECASE
        )
        if m_clock:
            hh = int(m_clock.group(1))
            mm = int(m_clock.group(2))
            task = m_clock.group(3).strip() or "Hal penting"
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                target_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if target_dt <= now:
                    target_dt += datetime.timedelta(days=1)
                    lbl = f"Besok jam {hh:02d}:{mm:02d}"
                else:
                    lbl = f"Hari ini jam {hh:02d}:{mm:02d}"
                return target_dt.timestamp(), lbl, task

        return None

    @classmethod
    def extract_reminder_from_chat(cls, chat_text: str) -> Optional[Tuple[float, str, str]]:
        """
        Detects if the user naturally asked their waifu to remind them of something.
        Returns (epoch, time_str, task) or None.
        """
        clean = chat_text.strip()
        patterns = [
            r"(?:sayang\s*,?\s*)?(?:tolong\s*)?inget(?:in|kan)\s*(?:aku|gue|saya)?\s*(?:nanti\s*)?(?:buat\s*|untuk\s*)?(.+)",
            r"(?:remind\s*me\s*(?:to\s*)?)(.+)",
            r"jangan\s*lupa\s*inget(?:in|kan)\s*(?:aku|gue|saya)?\s*(.+)"
        ]
        for p in patterns:
            m = re.search(p, clean, re.IGNORECASE)
            if m:
                sub = m.group(1).strip().rstrip(".!~")
                sub = re.sub(r'\b(ya|yaa|dong|sayang|sweetheart|babe|darling)\b$', '', sub, flags=re.IGNORECASE).strip()

                res = cls.parse_reminder_text(sub)
                if res:
                    return res

                m_rev = re.search(
                    r'^(.*?)(?:\s+)(?:pada\s+|di\s+|jam\s+|pukul\s+)?(\d{1,2}[:.]\d{2}|\d+\s*(?:m|min|menit|h|jam))\s*(?:lagi|nanti)?$',
                    sub,
                    re.IGNORECASE
                )
                if m_rev:
                    task = m_rev.group(1).strip()
                    t_str = m_rev.group(2).strip()
                    res = cls.parse_reminder_text(f"{t_str} {task}")
                    if res:
                        return res

        return None


def random_suffix() -> str:
    import random
    return f"{random.randint(1000, 9999)}"

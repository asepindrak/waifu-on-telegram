import os
import re
import json
import time
import datetime
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

MONTH_MAP = {
    'januari': 1, 'january': 1, 'jan': 1,
    'februari': 2, 'february': 2, 'feb': 2,
    'maret': 3, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'mei': 5, 'may': 5,
    'juni': 6, 'june': 6, 'jun': 6,
    'juli': 7, 'july': 7, 'jul': 7,
    'agustus': 8, 'august': 8, 'agu': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'oktober': 10, 'october': 10, 'okt': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'desember': 12, 'december': 12, 'des': 12, 'dec': 12
}

MONTH_NAMES_ID = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


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


class AnniversaryEngine:
    """Manages birthdays, anniversaries, countdowns, and anniversary celebration dispatches."""

    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            project_root = os.path.dirname(os.path.abspath(__file__))
            data_file = os.path.join(project_root, "data", "special_dates.json")
        self.data_file = data_file
        self.lock = threading.Lock()
        self.data: Dict[str, Any] = {}
        self.load_data()

    def _ensure_dir(self):
        d = os.path.dirname(self.data_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating directory {d}: {e}")

    def load_data(self):
        """Loads special dates from JSON."""
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading {self.data_file}: {e}")
                    self.data = {}
            else:
                self.data = {}
                self._ensure_dir()
                self._save_data_unlocked()

    def _save_data_unlocked(self):
        try:
            _atomic_write_json(self.data_file, self.data)
        except Exception as e:
            logger.error(f"Error saving {self.data_file}: {e}")

    def save_data(self):
        """Saves special dates to disk atomically."""
        with self.lock:
            self._save_data_unlocked()

    def get_user_dates(self, user_id: int) -> Dict[str, Any]:
        """Returns the dictionary of special dates for a user."""
        with self.lock:
            s_uid = str(user_id)
            if s_uid not in self.data:
                self.data[s_uid] = {
                    "birthday": None,
                    "anniversary": None,
                    "last_celebrated": {}
                }
            return self.data[s_uid]

    def set_birthday(self, user_id: int, day: int, month: int, year: Optional[int] = None) -> Dict[str, Any]:
        """Sets user's birthday."""
        with self.lock:
            s_uid = str(user_id)
            if s_uid not in self.data:
                self.data[s_uid] = {"birthday": None, "anniversary": None, "last_celebrated": {}}
            user_dates = self.data[s_uid]

            m_name = MONTH_NAMES_ID[month] if 1 <= month <= 12 else str(month)
            label = f"{day} {m_name}"
            if year:
                label += f" {year}"

            b_data = {
                "day": day,
                "month": month,
                "year": year,
                "label": label,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            user_dates["birthday"] = b_data
            self._save_data_unlocked()
            logger.info(f"Set birthday for user {user_id}: {label}")
            return b_data

    def set_anniversary(self, user_id: int, day: int, month: int, year: Optional[int] = None) -> Dict[str, Any]:
        """Sets anniversary / first meeting date."""
        with self.lock:
            s_uid = str(user_id)
            if s_uid not in self.data:
                self.data[s_uid] = {"birthday": None, "anniversary": None, "last_celebrated": {}}
            user_dates = self.data[s_uid]

            m_name = MONTH_NAMES_ID[month] if 1 <= month <= 12 else str(month)
            label = f"{day} {m_name}"
            if year:
                label += f" {year}"

            a_data = {
                "day": day,
                "month": month,
                "year": year,
                "label": label,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            user_dates["anniversary"] = a_data
            self._save_data_unlocked()
            logger.info(f"Set anniversary for user {user_id}: {label}")
            return a_data

    def delete_date(self, user_id: int, date_type: str) -> bool:
        """Removes a date (birthday or anniversary)."""
        with self.lock:
            s_uid = str(user_id)
            if s_uid in self.data and date_type in self.data[s_uid] and self.data[s_uid][date_type] is not None:
                self.data[s_uid][date_type] = None
                self._save_data_unlocked()
                return True
            return False

    @staticmethod
    def get_countdown(day: int, month: int) -> int:
        """Returns days remaining until the next occurrence of day/month (0 means today!)."""
        today = datetime.date.today()
        try:
            this_year_date = datetime.date(today.year, month, day)
        except ValueError:
            this_year_date = datetime.date(today.year, month, 28)

        if this_year_date < today:
            try:
                next_date = datetime.date(today.year + 1, month, day)
            except ValueError:
                next_date = datetime.date(today.year + 1, month, 28)
        else:
            next_date = this_year_date

        return (next_date - today).days

    def check_today_celebrations(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Checks if today is a birthday or anniversary that hasn't been celebrated yet this year.
        Returns list of celebrations to trigger.
        """
        today = datetime.date.today()
        cur_year = today.year
        cur_day = today.day
        cur_month = today.month

        celebrations = []
        with self.lock:
            target_uids = [str(user_id)] if user_id else list(self.data.keys())

            for s_uid in target_uids:
                u_info = self.data.get(s_uid, {})
                last_celeb = u_info.setdefault("last_celebrated", {})

                # Check birthday
                b = u_info.get("birthday")
                if b and b.get("day") == cur_day and b.get("month") == cur_month:
                    if last_celeb.get("birthday") != cur_year:
                        age = (cur_year - b["year"]) if b.get("year") else None
                        celebrations.append({
                            "user_id": int(s_uid),
                            "type": "birthday",
                            "label": b.get("label", "Ulang Tahun"),
                            "years": age,
                            "year_num": cur_year
                        })

                # Check anniversary
                a = u_info.get("anniversary")
                if a and a.get("day") == cur_day and a.get("month") == cur_month:
                    if last_celeb.get("anniversary") != cur_year:
                        years_together = (cur_year - a["year"]) if a.get("year") else None
                        celebrations.append({
                            "user_id": int(s_uid),
                            "type": "anniversary",
                            "label": a.get("label", "Anniversary"),
                            "years": years_together,
                            "year_num": cur_year
                        })

        return celebrations

    def mark_celebrated(self, user_id: int, event_type: str, year: Optional[int] = None):
        """Marks that celebration was dispatched for the given year."""
        if year is None:
            year = datetime.date.today().year
        with self.lock:
            s_uid = str(user_id)
            if s_uid in self.data:
                self.data[s_uid].setdefault("last_celebrated", {})[event_type] = year
                self._save_data_unlocked()

    @staticmethod
    def parse_date(raw_text: str) -> Optional[Tuple[int, int, Optional[int], str]]:
        """
        Parses date string into (day, month, year, formatted_label).
        """
        text = raw_text.strip().lower()
        if not text:
            return None

        # 1. Day Month [Year]: "15 agustus 1998", "10 november"
        m1 = re.match(r'^(\d{1,2})\s+([a-zA-Z]+)(?:\s+(\d{4}))?$', text)
        if m1:
            day = int(m1.group(1))
            m_str = m1.group(2).lower()
            year = int(m1.group(3)) if m1.group(3) else None
            month = MONTH_MAP.get(m_str)
            if month and 1 <= day <= 31:
                label = f"{day} {MONTH_NAMES_ID[month]}" + (f" {year}" if year else "")
                return day, month, year, label

        # 2. Month Day [Year]: "agustus 15", "november 10 2000"
        m2 = re.match(r'^([a-zA-Z]+)\s+(\d{1,2})(?:\s+(\d{4}))?$', text)
        if m2:
            m_str = m2.group(1).lower()
            day = int(m2.group(2))
            year = int(m2.group(3)) if m2.group(3) else None
            month = MONTH_MAP.get(m_str)
            if month and 1 <= day <= 31:
                label = f"{day} {MONTH_NAMES_ID[month]}" + (f" {year}" if year else "")
                return day, month, year, label

        # 3. Numeric: "15/08/1998", "15/8", "15-08-2000", "15-8"
        m3 = re.match(r'^(\d{1,2})[\/\-\.](\d{1,2})(?:[\/\-\.](\d{2,4}))?$', text)
        if m3:
            day = int(m3.group(1))
            month = int(m3.group(2))
            y_raw = m3.group(3)
            year = None
            if y_raw:
                year = int(y_raw)
                if year < 100:
                    year += 2000 if year < 50 else 1900
            if 1 <= month <= 12 and 1 <= day <= 31:
                label = f"{day} {MONTH_NAMES_ID[month]}" + (f" {year}" if year else "")
                return day, month, year, label

        return None

    @classmethod
    def extract_special_dates_from_chat(cls, chat_text: str) -> Optional[Tuple[str, int, int, Optional[int], str]]:
        """
        Detects if user naturally talked about their birthday or anniversary.
        Returns (date_type, day, month, year, formatted_label) or None.
        """
        clean = chat_text.strip()

        def _clean_trailing(s: str) -> str:
            val = s.strip().rstrip(".!~?,")
            while True:
                new_val = re.sub(r'(?:\s+\b(?:lho|ya|yaa|dong|sayang|nih|sweetheart|babe|darling|manis)\b)+$', '', val, flags=re.IGNORECASE).strip()
                if new_val == val:
                    break
                val = new_val
            return val

        # Birthday patterns
        b_patterns = [
            r"(?:tanggal\s*)?(?:ulang\s*tahun(?:ku|mu)?|ultah(?:ku|mu)?|birthday)\s*(?:aku|gue|saya)?\s*(?:itu|jatuh\s*pada|tanggal|pada)?\s*([0-9a-zA-Z\s\/\-\.]+)",
            r"(?:aku|gue|saya)\s*ulang\s*tahun\s*(?:tanggal|pada)?\s*([0-9a-zA-Z\s\/\-\.]+)",
            r"lahir(?:ku)?\s*(?:tanggal|pada)?\s*([0-9a-zA-Z\s\/\-\.]+)"
        ]
        for p in b_patterns:
            m = re.search(p, clean, re.IGNORECASE)
            if m:
                raw_d = _clean_trailing(m.group(1))
                res = cls.parse_date(raw_d)
                if res:
                    return ("birthday", res[0], res[1], res[2], res[3])

        # Anniversary / Relationship date patterns
        a_patterns = [
            r"(?:hari\s*)?(?:anniversary|jadian|ketemu(?:an)?|bertemu|tunangan|menikah)\s*(?:kita|kami)?\s*(?:itu|jatuh\s*pada|tanggal|pada)?\s*([0-9a-zA-Z\s\/\-\.]+)",
            r"kita\s*(?:pertama\s*kali\s*)?(?:jadian|ketemu|pacaran|bertemu)\s*(?:tanggal|pada)?\s*([0-9a-zA-Z\s\/\-\.]+)"
        ]
        for p in a_patterns:
            m = re.search(p, clean, re.IGNORECASE)
            if m:
                raw_d = _clean_trailing(m.group(1))
                res = cls.parse_date(raw_d)
                if res:
                    return ("anniversary", res[0], res[1], res[2], res[3])

        return None

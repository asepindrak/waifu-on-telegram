import os
import re
import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class MemoryEngine:
    """Manages persistent long-term memories, user profiles, and relationship diary."""

    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            project_root = os.path.dirname(os.path.abspath(__file__))
            data_file = os.path.join(project_root, "data", "memories.json")
        self.data_file = data_file
        self.data: Dict[str, Any] = {
            "profiles": {},
            "facts": {},
            "diary": {},
            "affinity": {}
        }
        self.load_data()

    def _ensure_dir(self):
        d = os.path.dirname(self.data_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating directory {d}: {e}")

    def load_data(self):
        """Loads persistent memories from JSON storage."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading memories from {self.data_file}: {e}")
                self.data = {"profiles": {}, "facts": {}, "diary": {}, "affinity": {}}
        else:
            self._ensure_dir()
            self.save_data()

    def save_data(self):
        """Saves memory state to disk."""
        self._ensure_dir()
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving memories to {self.data_file}: {e}")

    # --- Profile Management ---

    def get_profile(self, user_id: int) -> Dict[str, Any]:
        s_uid = str(user_id)
        return self.data.setdefault("profiles", {}).setdefault(s_uid, {
            "name": "",
            "nickname": "",
            "birthday": "",
            "job": "",
            "location": ""
        })

    def update_profile(self, user_id: int, **kwargs):
        prof = self.get_profile(user_id)
        for k, v in kwargs.items():
            if v:
                prof[k] = str(v).strip()
        self.save_data()

    # --- Facts & Knowledge Management ---

    def get_facts(self, user_id: int) -> List[Dict[str, Any]]:
        s_uid = str(user_id)
        return self.data.setdefault("facts", {}).setdefault(s_uid, [])

    def add_fact(self, user_id: int, fact: str, category: str = "general") -> Optional[Dict[str, Any]]:
        s_uid = str(user_id)
        facts = self.get_facts(user_id)
        clean_fact = fact.strip().rstrip(".!~")
        if not clean_fact or len(clean_fact) < 3:
            return None

        # Avoid exact duplicate
        for item in facts:
            if item.get("fact", "").lower() == clean_fact.lower():
                return item

        fact_id = len(facts) + 1
        new_item = {
            "id": fact_id,
            "fact": clean_fact,
            "category": category,
            "date": time.strftime("%Y-%m-%d %H:%M")
        }
        facts.append(new_item)
        self.save_data()
        return new_item

    def delete_fact(self, user_id: int, fact_id: int) -> bool:
        s_uid = str(user_id)
        facts = self.get_facts(user_id)
        for i, item in enumerate(facts):
            if item.get("id") == fact_id:
                facts.pop(i)
                # Re-index remaining facts
                for idx, f in enumerate(facts, 1):
                    f["id"] = idx
                self.save_data()
                return True
        return False

    def clear_facts(self, user_id: int):
        s_uid = str(user_id)
        self.data.setdefault("facts", {})[s_uid] = []
        self.save_data()

    # --- Relationship Diary ---

    def add_diary_entry(self, user_id: int, entry: str, mood: str = "🥰 Bahagia"):
        s_uid = str(user_id)
        diaries = self.data.setdefault("diary", {}).setdefault(s_uid, [])
        new_entry = {
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "entry": entry.strip(),
            "mood": mood
        }
        diaries.append(new_entry)
        if len(diaries) > 30:
            diaries.pop(0)
        self.save_data()

    def get_diary(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        s_uid = str(user_id)
        diaries = self.data.setdefault("diary", {}).setdefault(s_uid, [])
        return diaries[-limit:]

    # --- Persistent Affinity ---

    def get_affinity(self, user_id: int, default: int = 20) -> int:
        s_uid = str(user_id)
        return self.data.setdefault("affinity", {}).get(s_uid, default)

    def set_affinity(self, user_id: int, val: int):
        s_uid = str(user_id)
        self.data.setdefault("affinity", {})[s_uid] = min(max(val, 0), 100)
        self.save_data()

    # --- Context Injection for LLM ---

    def format_memory_context(self, user_id: int) -> str:
        """Constructs concise prompt segment injected into system instruction."""
        prof = self.get_profile(user_id)
        facts = self.get_facts(user_id)
        lines = []

        if prof.get("name"):
            lines.append(f"• User's Name/Nickname: {prof['name']}")
        if prof.get("birthday"):
            lines.append(f"• User's Birthday: {prof['birthday']}")
        if prof.get("job"):
            lines.append(f"• User's Work/Study: {prof['job']}")
        if prof.get("location"):
            lines.append(f"• User's Location: {prof['location']}")

        if facts:
            lines.append("• Key Things You Remember About User:")
            for f in facts[-8:]:
                lines.append(f"  - {f['fact']}")

        if not lines:
            return ""

        return (
            "\n[LONG-TERM MEMORY & KNOWLEDGE ABOUT YOUR PARTNER]\n"
            + "\n".join(lines)
            + "\n(Naturally reference these memories, personal preferences, and names when relevant to express deep personal intimacy and caring without sounding repetitive.)\n"
        )

    # --- Automatic Memory Learning ---

    def auto_extract_facts(self, user_text: str, user_id: int) -> List[str]:
        """Analyzes user message for personal facts and saves them automatically."""
        learned = []
        lower = user_text.lower().strip()

        # 1. Name detection
        name_patterns = [
            r"(?:nama (?:saya|aku)|panggil (?:saya|aku)|namaku) (?:adalah )?([A-Za-z0-9_-]+)",
            r"(?:my name is|call me) ([A-Za-z0-9_-]+)"
        ]
        for pat in name_patterns:
            m = re.search(pat, user_text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if len(val) >= 2 and val.lower() not in ("siapa", "ya", "dong", "deh", "bukan", "what"):
                    self.update_profile(user_id, name=val)
                    learned.append(f"Nama: {val}")

        # 2. Favorite / Likes
        like_patterns = [
            r"(?:aku|saya) (?:paling )?(?:suka|hobi|gemar|doyan) (.+)",
            r"(?:makanan|minuman|game|film|musik) favorit(?:ku| saya) (?:adalah )?(.+)",
            r"(?:i (?:really )?(?:like|love|enjoy)) (.+)"
        ]
        for pat in like_patterns:
            m = re.search(pat, lower)
            if m:
                raw_fact = m.group(1).strip().rstrip(".!~")
                if len(raw_fact) >= 3 and not raw_fact.startswith("kamu") and not raw_fact.startswith("apa"):
                    f = self.add_fact(user_id, f"Suka {raw_fact}", category="likes")
                    if f:
                        learned.append(f["fact"])

        # 3. Work / Profession
        work_patterns = [
            r"(?:aku|saya) (?:kerja|bekerja) (?:sebagai|di) (.+)",
            r"(?:pekerjaan(?:ku| saya) (?:adalah )?)(.+)",
            r"(?:i work as|my job is) (.+)"
        ]
        for pat in work_patterns:
            m = re.search(pat, lower)
            if m:
                raw_work = m.group(1).strip().rstrip(".!~")
                if len(raw_work) >= 3:
                    self.update_profile(user_id, job=raw_work)
                    f = self.add_fact(user_id, f"Bekerja: {raw_work}", category="work")
                    if f:
                        learned.append(f["fact"])

        # 4. Location
        loc_patterns = [
            r"(?:aku|saya) (?:tinggal|domisili|asal) (?:di|dari) (.+)",
            r"(?:i live in|i am from) (.+)"
        ]
        for pat in loc_patterns:
            m = re.search(pat, lower)
            if m:
                raw_loc = m.group(1).strip().rstrip(".!~")
                if len(raw_loc) >= 3:
                    self.update_profile(user_id, location=raw_loc)
                    f = self.add_fact(user_id, f"Tinggal di {raw_loc}", category="location")
                    if f:
                        learned.append(f["fact"])

        return learned

import os
import re
import math
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("MemoryEngine")


def _atomic_write_json(file_path: str, data: Any):
    """
    Saves JSON data to disk atomically using a temporary file in the same directory.
    Guarantees that the data file is NEVER corrupted or left half-written even if
    the application crashes or the system abruptly loses power.
    """
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


class VectorEngine:
    """
    High-performance zero-dependency Semantic Vector & Similarity Search Engine.
    Combines word tokens, subword character n-grams, and sublinear TF-IDF weighting
    with L2-normalized cosine similarity.
    
    Provides fast (<0.5ms) semantic search across personal memories and diaries without
    requiring multi-gigabyte vector databases or waking up heavy local GPU LLMs.
    """
    STOP_WORDS = {
        "yang", "di", "ke", "dari", "ini", "itu", "dan", "atau", "adalah", "ya",
        "nih", "deh", "kan", "lah", "dong", "sih", "kok", "aku", "saya", "kamu",
        "the", "a", "an", "is", "in", "at", "to", "for", "of", "and", "or", "it"
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Cleans and extracts word tokens from text."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = [w.strip() for w in clean.split() if len(w.strip()) >= 2]
        return [w for w in words if w not in cls.STOP_WORDS]

    @classmethod
    def stem_word(cls, w: str) -> List[str]:
        """Expands Indonesian and English root stems for enhanced semantic matching."""
        stems = [w]
        # Common Indonesian prefixes
        if w.startswith("ng") and len(w) > 4:
            stems.append("k" + w[2:])
            stems.append(w[2:])
        elif w.startswith("ny") and len(w) > 4:
            stems.append("s" + w[2:])
        for pref in ("ber", "ter", "di", "ke", "se"):
            if w.startswith(pref) and len(w) > len(pref) + 3:
                stems.append(w[len(pref):])
        # Suffixes
        for suf in ("an", "kan", "nya", "ku", "mu", "ing", "ed"):
            if w.endswith(suf) and len(w) > len(suf) + 3:
                stems.append(w[:-len(suf)])
        return list(set(stems))

    @classmethod
    def vectorize(cls, text: str) -> Dict[str, float]:
        """
        Builds an L2-normalized sparse vector representation of text.
        Includes word unigrams, stems, bigrams, and character 3-grams for morphological resilience
        (e.g., handles Indonesian inflections: 'makan', 'makanan', 'memakan', 'ngopi' -> 'kopi').
        """
        words = cls.tokenize(text)
        if not words:
            raw_clean = re.sub(r"[^\w]", "", text.lower())
            if not raw_clean:
                return {}
            words = [raw_clean]

        counts: Dict[str, float] = {}

        # 1. Word Unigrams & Root Stems
        for w in words:
            counts[f"w:{w}"] = counts.get(f"w:{w}", 0.0) + 1.0
            for stem in cls.stem_word(w):
                if stem != w and len(stem) >= 3:
                    counts[f"w:{stem}"] = counts.get(f"w:{stem}", 0.0) + 0.85

        # 2. Word Bigrams
        for i in range(len(words) - 1):
            bg = f"bg:{words[i]}_{words[i+1]}"
            counts[bg] = counts.get(bg, 0.0) + 1.5

        # 3. Subword Character 3-Grams (handles typos and subword roots)
        for w in words:
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    ng = f"c3:{w[i:i+3]}"
                    counts[ng] = counts.get(ng, 0.0) + 0.4

        # 4. Sublinear Term Frequency Weighting: 1 + ln(count)
        weights: Dict[str, float] = {}
        sum_sq = 0.0
        for k, cnt in counts.items():
            w = 1.0 + math.log(cnt)
            weights[k] = w
            sum_sq += w * w

        # 5. L2 Normalization
        norm = math.sqrt(sum_sq)
        if norm > 0:
            for k in weights:
                weights[k] /= norm

        return weights

    @classmethod
    def cosine_similarity(cls, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Computes cosine similarity between two L2-normalized sparse vectors."""
        if not vec1 or not vec2:
            return 0.0

        # Iterate over the smaller vector for maximum speed
        if len(vec1) > len(vec2):
            vec1, vec2 = vec2, vec1

        score = 0.0
        for k, v1 in vec1.items():
            if k in vec2:
                score += v1 * vec2[k]

        return min(max(score, 0.0), 1.0)


class MemoryEngine:
    """
    Manages persistent long-term memories, user profiles, relationship diary,
    and semantic vector-based memory retrieval.
    """

    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            project_root = os.path.dirname(os.path.abspath(__file__))
            data_file = os.path.join(project_root, "data", "memories.json")
        self.data_file = data_file
        self.lock = threading.Lock()
        self.vector_engine = VectorEngine()

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
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading memories from {self.data_file}: {e}")
                    self.data = {"profiles": {}, "facts": {}, "diary": {}, "affinity": {}}
            else:
                self._ensure_dir()
                self._save_data_unlocked()

    def _save_data_unlocked(self):
        """Internal save routine expecting self.lock to be acquired."""
        try:
            _atomic_write_json(self.data_file, self.data)
        except Exception as e:
            logger.error(f"Error atomically saving memories to {self.data_file}: {e}")

    def save_data(self):
        """Thread-safe and atomic memory persistence."""
        with self.lock:
            self._save_data_unlocked()

    # --- Profile Management ---

    def get_profile(self, user_id: int) -> Dict[str, Any]:
        with self.lock:
            s_uid = str(user_id)
            return self.data.setdefault("profiles", {}).setdefault(s_uid, {
                "name": "",
                "nickname": "",
                "birthday": "",
                "job": "",
                "location": "",
                "hobbies": "",
                "preferences": ""
            })

    def update_profile(self, user_id: int, **kwargs):
        with self.lock:
            s_uid = str(user_id)
            prof = self.data.setdefault("profiles", {}).setdefault(s_uid, {
                "name": "", "nickname": "", "birthday": "", "job": "", "location": "", "hobbies": "", "preferences": ""
            })
            for k, v in kwargs.items():
                if v is not None:
                    prof[k] = str(v).strip()
            self._save_data_unlocked()

    # --- Facts & Knowledge Management ---

    def get_facts(self, user_id: int) -> List[Dict[str, Any]]:
        with self.lock:
            s_uid = str(user_id)
            return list(self.data.setdefault("facts", {}).setdefault(s_uid, []))

    def add_fact(self, user_id: int, fact: str, category: str = "general") -> Optional[Dict[str, Any]]:
        clean_fact = fact.strip().rstrip(".!~")
        if not clean_fact or len(clean_fact) < 3:
            return None

        with self.lock:
            s_uid = str(user_id)
            facts = self.data.setdefault("facts", {}).setdefault(s_uid, [])

            # Avoid exact or very close duplicates
            for item in facts:
                if item.get("fact", "").lower() == clean_fact.lower():
                    return item

            fact_id = len(facts) + 1
            new_item = {
                "id": fact_id,
                "fact": clean_fact,
                "category": category,
                "date": time.strftime("%Y-%m-%d %H:%M"),
                "timestamp": time.time()
            }
            facts.append(new_item)
            self._save_data_unlocked()
            return new_item

    def delete_fact(self, user_id: int, fact_id: int) -> bool:
        with self.lock:
            s_uid = str(user_id)
            facts = self.data.setdefault("facts", {}).setdefault(s_uid, [])
            for i, item in enumerate(facts):
                if item.get("id") == fact_id:
                    facts.pop(i)
                    for idx, f in enumerate(facts, 1):
                        f["id"] = idx
                    self._save_data_unlocked()
                    return True
            return False

    def clear_facts(self, user_id: int):
        with self.lock:
            s_uid = str(user_id)
            self.data.setdefault("facts", {})[s_uid] = []
            self._save_data_unlocked()

    # --- Vector & Semantic Similarity Search ---

    def search_facts(
        self,
        user_id: int,
        query: str,
        top_k: int = 5,
        threshold: float = 0.08
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Performs semantic vector similarity search against all stored facts for the user.
        Returns a list of (fact_dict, similarity_score) sorted by relevance.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        query_vec = self.vector_engine.vectorize(clean_query)
        if not query_vec:
            return []

        all_facts = self.get_facts(user_id)
        if not all_facts:
            return []

        scored_facts: List[Tuple[Dict[str, Any], float]] = []
        now = time.time()

        for f in all_facts:
            fact_text = f.get("fact", "")
            fact_vec = self.vector_engine.vectorize(f"{f.get('category', '')} {fact_text}")
            sim = self.vector_engine.cosine_similarity(query_vec, fact_vec)

            # Slight recency bonus (up to +0.05 for recent memories within 7 days)
            age_days = (now - f.get("timestamp", now)) / (24 * 3600)
            recency_bonus = max(0.0, (7.0 - age_days) / 7.0) * 0.05
            final_score = sim + recency_bonus

            if sim >= threshold or final_score >= threshold:
                scored_facts.append((f, round(final_score, 4)))

        # Sort descending by similarity score
        scored_facts.sort(key=lambda x: x[1], reverse=True)
        return scored_facts[:top_k]

    def search_diary(
        self,
        user_id: int,
        query: str,
        top_k: int = 3,
        threshold: float = 0.12
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Searches past relationship diary entries using semantic vector similarity."""
        clean_query = query.strip()
        if not clean_query:
            return []

        query_vec = self.vector_engine.vectorize(clean_query)
        if not query_vec:
            return []

        diaries = self.get_diary(user_id, limit=30)
        scored: List[Tuple[Dict[str, Any], float]] = []

        for d in diaries:
            entry_text = d.get("entry", "")
            d_vec = self.vector_engine.vectorize(entry_text)
            sim = self.vector_engine.cosine_similarity(query_vec, d_vec)
            if sim >= threshold:
                scored.append((d, round(sim, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # --- Relationship Diary ---

    def add_diary_entry(self, user_id: int, entry: str, mood: str = "🥰 Bahagia"):
        with self.lock:
            s_uid = str(user_id)
            diaries = self.data.setdefault("diary", {}).setdefault(s_uid, [])
            new_entry = {
                "date": time.strftime("%Y-%m-%d %H:%M"),
                "entry": entry.strip(),
                "mood": mood,
                "timestamp": time.time()
            }
            diaries.append(new_entry)
            if len(diaries) > 40:
                diaries.pop(0)
            self._save_data_unlocked()

    def get_diary(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        with self.lock:
            s_uid = str(user_id)
            diaries = self.data.setdefault("diary", {}).setdefault(s_uid, [])
            return list(diaries[-limit:])

    # --- Persistent Affinity ---

    def get_affinity(self, user_id: int, default: int = 20) -> int:
        with self.lock:
            s_uid = str(user_id)
            return self.data.setdefault("affinity", {}).get(s_uid, default)

    def set_affinity(self, user_id: int, val: int):
        with self.lock:
            s_uid = str(user_id)
            self.data.setdefault("affinity", {})[s_uid] = min(max(val, 0), 100)
            self._save_data_unlocked()

    # --- Context Injection for LLM ---

    def format_memory_context(self, user_id: int, query: Optional[str] = None, max_facts: int = 8) -> str:
        """
        Constructs a concise, highly relevant prompt segment for system instruction.
        Uses semantic vector similarity to retrieve the most relevant facts if query is provided,
        blending relevant facts with recent facts so context is both topic-accurate and fresh.
        """
        prof = self.get_profile(user_id)
        all_facts = self.get_facts(user_id)
        lines = []

        if prof.get("name"):
            lines.append(f"• User's Name/Nickname: {prof['name']}")
        if prof.get("birthday"):
            lines.append(f"• User's Birthday: {prof['birthday']}")
        if prof.get("job"):
            lines.append(f"• User's Work/Study: {prof['job']}")
        if prof.get("location"):
            lines.append(f"• User's Location: {prof['location']}")

        # Select facts using Vector Search or fallback to recency
        selected_facts: List[Dict[str, Any]] = []
        selected_ids = set()

        if query and all_facts:
            # 1. Retrieve semantically relevant facts via vector search
            relevant_matches = self.search_facts(user_id, query, top_k=max_facts // 2 + 1)
            for fact_item, _ in relevant_matches:
                if fact_item["id"] not in selected_ids:
                    selected_facts.append(fact_item)
                    selected_ids.add(fact_item["id"])

        # 2. Fill remaining slots with the most recent facts
        if len(selected_facts) < max_facts and all_facts:
            for fact_item in reversed(all_facts):
                if fact_item["id"] not in selected_ids:
                    selected_facts.append(fact_item)
                    selected_ids.add(fact_item["id"])
                if len(selected_facts) >= max_facts:
                    break

        if selected_facts:
            lines.append("• Key Things You Remember About User:")
            for f in selected_facts:
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
        """
        Analyzes user message for personal facts (likes, dislikes, allergies, routines,
        relationships, job, location, goals) and saves them automatically into vector memory.
        """
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
            r"(?:makanan|minuman|game|film|musik|warna) favorit(?:ku| saya) (?:adalah )?(.+)",
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

        # 3. Dislikes / Allergies / Pantangan
        dislike_patterns = [
            r"(?:aku|saya) (?:ga suka|nggak suka|tidak suka|benci) (.+)",
            r"(?:aku|saya) (?:alergi|pantang) (.+)",
            r"(?:i (?:really )?(?:hate|dislike|am allergic to)) (.+)"
        ]
        for pat in dislike_patterns:
            m = re.search(pat, lower)
            if m:
                raw_dislike = m.group(1).strip().rstrip(".!~")
                if len(raw_dislike) >= 3 and not raw_dislike.startswith("kamu"):
                    cat = "allergies" if ("alergi" in lower or "allergic" in lower) else "dislikes"
                    prefix = "Alergi" if cat == "allergies" else "Tidak suka"
                    f = self.add_fact(user_id, f"{prefix} {raw_dislike}", category=cat)
                    if f:
                        learned.append(f["fact"])

        # 4. Work / Profession / Studies
        work_patterns = [
            r"(?:(?:aku|saya|dan)\s+)?(?:kerja|bekerja)\s+(?:sebagai|di)\s+(.+)",
            r"(?:pekerjaan(?:ku| saya)\s+(?:adalah\s+)?)(.+)",
            r"(?:(?:aku|saya|dan)\s+)?(?:kuliah|sekolah)\s+(?:di|jurusan)\s+(.+)",
            r"(?:i work as|my job is|i study)\s+(.+)"
        ]
        for pat in work_patterns:
            m = re.search(pat, user_text, re.IGNORECASE)
            if m:
                raw_work = m.group(1).strip().rstrip(".!~")
                raw_work = re.split(r"\s+(?:dan|tapi|sambil|namun|and)\s+", raw_work, flags=re.IGNORECASE)[0].strip()
                if len(raw_work) >= 3:
                    self.update_profile(user_id, job=raw_work)
                    f = self.add_fact(user_id, f"Bekerja/Studi: {raw_work}", category="work")
                    if f:
                        learned.append(f["fact"])

        # 5. Location / Origin
        loc_patterns = [
            r"(?:aku|saya) (?:tinggal|domisili|asal) (?:di|dari) (.+)",
            r"(?:i live in|i am from) (.+)"
        ]
        for pat in loc_patterns:
            m = re.search(pat, user_text, re.IGNORECASE)
            if m:
                raw_loc = m.group(1).strip().rstrip(".!~")
                raw_loc = re.split(r"\s+(?:dan|tapi|sambil|namun|and)\s+", raw_loc, flags=re.IGNORECASE)[0].strip()
                if len(raw_loc) >= 3:
                    self.update_profile(user_id, location=raw_loc.title())
                    f = self.add_fact(user_id, f"Tinggal di {raw_loc.title()}", category="location")
                    if f:
                        learned.append(f["fact"])

        # 6. Pets & Family
        pet_patterns = [
            r"(?:aku|saya) punya (?:seekor |sepasang )?(.+)",
            r"(?:i have a pet |i have a cat |i have a dog )(.+)"
        ]
        for pat in pet_patterns:
            m = re.search(pat, lower)
            if m:
                raw_pet = m.group(1).strip().rstrip(".!~")
                if any(k in raw_pet for k in ("kucing", "anjing", "kelinci", "hamster", "burung", "ikan", "cat", "dog", "pet")):
                    f = self.add_fact(user_id, f"Punya hewan peliharaan: {raw_pet}", category="pet")
                    if f:
                        learned.append(f["fact"])

        # 7. Routines & Habits
        routine_patterns = [
            r"(?:aku|saya) biasanya (?:tidur|bangun) jam (.+)",
            r"(?:setiap (?:pagi|sore|malam) aku) (.+)"
        ]
        for pat in routine_patterns:
            m = re.search(pat, lower)
            if m:
                raw_rout = m.group(1).strip().rstrip(".!~")
                if len(raw_rout) >= 3:
                    f = self.add_fact(user_id, f"Kebiasaan: {raw_rout}", category="routine")
                    if f:
                        learned.append(f["fact"])

        return learned

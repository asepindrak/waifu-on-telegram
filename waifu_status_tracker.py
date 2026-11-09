"""
waifu_status_tracker.py - Real-Time Dynamic Waifu State & Contextual Consistency Tracker
Ensures the AI waifu remains 100% aware of her previously stated location, current activity,
and photo captions, preventing contradictions (e.g. saying she's at campus right after sending
a photo of herself relaxing at home).
"""

import os
import re
import time
import json
import logging
import threading
from typing import Optional, Dict, Any

logger = logging.getLogger("WaifuStatusTracker")

HOME_KEYWORDS = [
    r"\b(rebahan|kasur|kamar|bedroom|bed|selimut|bantal|guling)\b",
    r"\b(rumah|home|kos|kosan|kost|apartemen|pajamas|piyama)\b",
    r"\b(pulang\s+dari\s+kampus|baru\s+pulang|udah\s+di\s+kamar|udah\s+di\s+rumah)\b"
]

CAMPUS_KEYWORDS = [
    r"\b(kampus|kuliah|kelas|dosen|makul|matkul|lab|praktikum)\b",
    r"\b(perpus|perpustakaan|library|gedung\s+fakultas)\b"
]

CAFE_KEYWORDS = [
    r"\b(cafe|kafe|kopi|coffee|starbucks|warkop|nongkrong)\b"
]

MALL_KEYWORDS = [
    r"\b(mall|belanja|shopping|toko|supermarket|bioskop)\b"
]


class WaifuStatusTracker:
    """
    Maintains real-time physical context and state consistency for each user.
    Tracks where the waifu is, what she is doing, and what she recently claimed
    to prevent immersion-breaking contradictions.
    """

    def __init__(self, storage_path: Optional[str] = None, max_age_hours: float = 3.5):
        self.max_age_seconds = max_age_hours * 3600
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "waifu_status.json"
        )
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_from_disk()

    def _load_from_disk(self):
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._statuses = json.load(f)
        except Exception as e:
            logger.debug(f"Could not load waifu status from disk: {e}")

    def _save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._statuses, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"Could not persist waifu status to disk: {e}")

    def detect_location(self, text: str) -> str:
        """Determines location category from caption or scene description."""
        t_low = text.lower()
        for pat in HOME_KEYWORDS:
            if re.search(pat, t_low):
                return "Rumah / Kamar kos"
        for pat in CAMPUS_KEYWORDS:
            if re.search(pat, t_low):
                return "Kampus"
        for pat in CAFE_KEYWORDS:
            if re.search(pat, t_low):
                return "Cafe / Tempat Kopi"
        for pat in MALL_KEYWORDS:
            if re.search(pat, t_low):
                return "Mall / Pusat Perbelanjaan"
        return "Rumah / Kamar kos"

    def record_photo_event(
        self,
        user_id: int,
        scene: str,
        caption: str,
        outfit: str = "",
        persona_name: str = "Waifu"
    ):
        """Records state update when a photo is delivered."""
        combined_text = f"{scene} {caption}"
        location = self.detect_location(combined_text)

        clean_caption = re.sub(r'[*_`#~<>]', '', caption).strip()
        clean_caption = clean_caption.split("\n")[0]  # Take first line if multi-line

        with self._lock:
            self._statuses[str(user_id)] = {
                "persona_name": persona_name,
                "location": location,
                "activity": clean_caption or f"Sedang berada di {location}",
                "photo_caption": clean_caption,
                "scene": scene,
                "outfit": outfit,
                "updated_at": time.time()
            }
            self._save_to_disk()

        logger.info(f"✨ Waifu status updated for user {user_id}: Location='{location}', Activity='{clean_caption[:40]}...'")

    def record_chat_statement(self, user_id: int, statement: str, persona_name: str = "Waifu"):
        """Extracts and records location/activity stated in chat."""
        t_low = statement.lower()
        # Look for explicit location claims: "lagi di ...", "baru pulang ke ...", "udah di ..."
        loc = None
        for pat in HOME_KEYWORDS:
            if re.search(pat, t_low):
                loc = "Rumah / Kamar kos"
                break
        if not loc:
            for pat in CAMPUS_KEYWORDS:
                if re.search(pat, t_low):
                    loc = "Kampus"
                    break
        if not loc:
            for pat in CAFE_KEYWORDS:
                if re.search(pat, t_low):
                    loc = "Cafe / Tempat Kopi"
                    break

        if loc:
            with self._lock:
                clean_stat = re.sub(r'[*_`#~<>]', '', statement).strip().split("\n")[0]
                self._statuses[str(user_id)] = {
                    "persona_name": persona_name,
                    "location": loc,
                    "activity": clean_stat,
                    "photo_caption": self._statuses.get(str(user_id), {}).get("photo_caption", ""),
                    "scene": loc,
                    "outfit": self._statuses.get(str(user_id), {}).get("outfit", ""),
                    "updated_at": time.time()
                }
                self._save_to_disk()

    def update_status(
        self,
        user_id: int,
        location: str,
        activity: str,
        outfit: Optional[str] = None,
        persona_name: str = "Waifu",
        photo_caption: Optional[str] = None
    ):
        """Directly updates waifu location and activity state for user."""
        with self._lock:
            cur = self._statuses.get(str(user_id), {})
            self._statuses[str(user_id)] = {
                "persona_name": persona_name,
                "location": location,
                "activity": activity,
                "photo_caption": photo_caption if photo_caption is not None else cur.get("photo_caption", ""),
                "scene": location,
                "outfit": outfit if outfit is not None else cur.get("outfit", ""),
                "updated_at": time.time()
            }
            self._save_to_disk()
        logger.info(f"✨ Waifu status updated for user {user_id}: Location='{location}', Activity='{activity}'")

    def get_current_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Returns the active status if updated within expiration window."""
        with self._lock:
            st = self._statuses.get(str(user_id))
            if not st:
                return None
            elapsed = time.time() - st.get("updated_at", 0)
            if elapsed > self.max_age_seconds:
                return None
            return st

    def format_status_instruction(
        self,
        user_id: int,
        cur_hour: int,
        routine_desc: str,
        major: str = "Ilmu Hukum",
        cur_outfit: Optional[str] = None,
        is_inviting_out: bool = False
    ) -> str:
        """
        Builds the system instruction prompt section.
        Prioritizes recently stated dynamic reality and flexible user responsiveness
        over rigid, repetitive statements!
        """
        st = self.get_current_status(user_id)
        if st and st.get("activity"):
            loc = st.get("location", "Rumah / Kamar kos")
            act = st.get("activity")
            p_cap = st.get("photo_caption")
            outfit = cur_outfit or st.get("outfit")

            caption_ref = f' (Caption yang baru saja kamu kirim: "{p_cap}")' if p_cap else ""
            outfit_line = f"• Pakaian kamu saat ini: {outfit}\n" if outfit else ""
            outfit_guideline = (
                f"4. KONSISTENSI PAKAIAN: Pakaian kamu saat ini adalah {outfit}. "
                "Jika lawan bicaramu menanyakan apa yang sedang kamu pakai atau mengomentari fotomu, "
                "jawabanmu harus konsisten dengan pakaian tersebut. "
                "Jika sebelumnya kamu sempat memakai kostum khusus (seperti maid, kimono, atau bikini) namun sekarang kegiatanmu sudah berganti "
                "(seperti tidur, mandi, santai di rumah, atau kuliah), kamu sudah mengganti pakaianmu menjadi pakaian yang sesuai dan tidak lagi memakai kostum tersebut.\n"
            ) if outfit else ""

            return (
                f"\n\n[SITUASI & LOKASI DIRI SAAT INI]\n"
                f"Waktu sekarang: Jam {cur_hour:02d}:00.\n"
                f"• Lokasi kamu saat ini: {loc}\n"
                f"• Konteks kegiatan terakhir: \"{act}\"{caption_ref}\n"
                f"{outfit_line}"
                f"• Status mahasiswa: Mahasiswi ({major}).\n\n"
                f"PEDOMAN DINAMIKA KEGIATAN & PERCAKAPAN:\n"
                f"1. FLEKSIBEL & RESPONSIF TERHADAP AJAKAN / PERUBAHAN TOPIK: Konteks kegiatan di atas adalah kegiatanmu sebelumnya. "
                f"Jika lawan bicaramu mengajak main, jalan, atau berganti topik pembicaraan, SEGERA IKUTI dan BERADAPTASI secara alami! "
                f"DILARANG KERAS mengulang-ulang kegiatan lama (misalnya: terus bersikeras mengaku lagi main game sendiri) "
                f"jika lawan bicaramu sudah mengajak main bareng atau membicarakan hal lain!\n"
                f"2. KONSISTENSI FISIK & LOGIKA RUANG: Jaga konsistensi lokasi secara wajar (jangan berpindah tempat secara mustahil tanpa konteks perjalanan/ajakan). "
                f"Jika kamu sebelumnya santai di rumah/kamar, DILARANG TIBA-TIBA bilang masih di kampus atau sedang di kelas tanpa jeda waktu. "
                f"Namun jika lawan bicaramu mengajakmu pergi atau kencan, kamu boleh bersiap-siap dan berangkat bersama.\n"
                f"3. Jika lawan bicaramu bertanya sedang apa, berada di mana, atau membahas fotomu, respons sesuai dengan situasi nyatamu saat ini di {loc}.\n"
                f"{outfit_guideline}"
            )

        # Fallback to standard college routine if no recent dynamic statement exists
        outfit_line = f" Pakaianmu: {cur_outfit}." if cur_outfit else ""
        return (
            f"\n\n[KEGIATAN MAHASISWI HARI INI]\n"
            f"Waktu sekarang: Jam {cur_hour:02d}:00. Konteks waktu: {routine_desc}.{outfit_line} "
            f"Kamu adalah mahasiswi ({major}). Tanggapi obrolan lawan bicaramu secara alami, hangat, dan fleksibel.\n"
        )


_GLOBAL_TRACKER: Optional[WaifuStatusTracker] = None


def get_waifu_status_tracker() -> WaifuStatusTracker:
    global _GLOBAL_TRACKER
    if _GLOBAL_TRACKER is None:
        _GLOBAL_TRACKER = WaifuStatusTracker()
    return _GLOBAL_TRACKER


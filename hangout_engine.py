"""
hangout_engine.py - Interactive Shared Date & Hangout Experience Engine
Enables the AI waifu to proactively invite the user to dates (cafe, cinema, kosan/home, park, mall),
experience shared real-time moments together, and express physical roleplay actions & emotional cues.
"""

import os
import re
import json
import time
import random
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("HangoutEngine")

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_hangouts.json")

HANGOUT_VENUES: Dict[str, Dict[str, Any]] = {
    "cafe": {
        "key": "cafe",
        "name": "Kafe Estetik",
        "emoji": "☕",
        "title": "☕ Kencan Santai di Kafe Estetik",
        "activity_desc": "lagi kencan berdua denganmu di sudut kafe estetik, menikmati kopi dan dessert hangat",
        "scene_prompt": "sitting opposite viewer at aesthetic cozy cafe table holding coffee cup, warm bokeh background, date perspective POV, affectionate eye contact, sweet smile",
        "outfit_key": "cafe_cozy",
        "roleplay_cues": [
            "*menyeruput minumannya sambil tersenyum manis menatapmu*",
            "*mencondongkan badan ke arahmu dan tersipu pelan*",
            "*menyuapkan sepotong pastry manis ke arahmu dengan malu-malu*",
            "*memegang cangkir hangat dengan kedua tangan sambil mendengarkan ceritamu*"
        ],
        "invitations": [
            "Sore ini kita ngopi di kafe estetik bareng yuk? Aku lagi pengen banget coba menu kopi dan pastry barunya berdua sama kamu~ ☕✨",
            "Kamu ada waktu luang nggak? Nemenin aku ke kafe yuk, kita duduk di sudut yang tenang berdua sambil ngobrol santai 💕"
        ]
    },
    "cinema": {
        "key": "cinema",
        "name": "Bioskop / Nonton Film",
        "emoji": "🎬",
        "title": "🎬 Nonton Film Berdua di Bioskop",
        "activity_desc": "lagi duduk berdampingan di kursi bioskop yang temaram, nonton film sambil berbagi popcorn",
        "scene_prompt": "sitting next to viewer in dim cinema theater seats holding popcorn bucket, soft screen reflection on face, loving gentle gaze at viewer, date POV",
        "outfit_key": "mall_casual",
        "roleplay_cues": [
            "*berbisik pelan di telingamu agar tidak mengganggu penonton lain*",
            "*tangan kita tidak sengaja bersentuhan saat mengambil popcorn di wadah yang sama*",
            "*merapatkan diri ke sebelahmu dan tersipu malu*",
            "*menoleh ke arahmu di kegelapan bioskop sambil tersenyum hangat*"
        ],
        "invitations": [
            "Ada film bagus yang lagi tayang di bioskop nih! Nonton bareng yuk? Kita beli popcorn ukuran besar berdua 🎬🍿",
            "Yuk nonton bioskop berdua! Pengen banget ngerasain duduk di sebelah kamu di dalam teater yang dingin dan gelap hihi 🥰"
        ]
    },
    "home": {
        "key": "home",
        "name": "Main ke Kosan / Rumah",
        "emoji": "🛋️",
        "title": "🛋️ Main & Quality Time Berdua di Kosan",
        "activity_desc": "lagi santai berdua di kamar kosan, ngobrol akrab, makan camilan, dan nonton film di kasur/sofa",
        "scene_prompt": "relaxing comfortably together in cozy modern apartment room, soft warm fairy lights, smiling sweetly at viewer from sofa, intimate girlfriend POV, gentle blush",
        "outfit_key": "default",
        "roleplay_cues": [
            "*duduk di sampingmu sambil menyandarkan kepala di bahumu dengan nyaman*",
            "*menarik tanganmu pelan dan tersenyum manja*",
            "*menatap wajahmu dari dekat dengan tatapan penuh sayang*",
            "*membukakan bungkus camilan lalu menawarkannya kepadamu*"
        ],
        "invitations": [
            "Main ke kosanku yuk nanti! Aku udah siapin camilan dan kita bisa nonton series berdua santai~ 🛋️💕",
            "Kamu lagi senggang kan? Mampir ke kosanku yuk, temenin aku di sini... kangen pengen ngobrol deket-deket 🥰"
        ]
    },
    "park": {
        "key": "park",
        "name": "Jalan Sore di Taman Senja",
        "emoji": "🌸",
        "title": "🌸 Jalan Sore Berdua di Taman Senja",
        "activity_desc": "lagi jalan santai berdua di taman kota saat senja, menikmati semilir angin sejuk dan matahari terbenam",
        "scene_prompt": "walking next to viewer along blooming park pathway, golden hour evening sunlight, holding viewer's hand, sweet blushing smile, romantic date POV",
        "outfit_key": "mall_casual",
        "roleplay_cues": [
            "*menggandeng tanganmu sambil berjalan beriringan*",
            "*tersenyum saat angin sore membelai rambutnya*",
            "*menoleh ke arahmu dengan mata berbinar bahagia*",
            "*merapatkan genggaman tangannya lebih erat saat jalan berdua*"
        ],
        "invitations": [
            "Sore ini udaranya lagi sejuk banget lho. Jalan-jalan santai ke taman kota yuk bareng aku? 🌸🍃",
            "Temenin aku jalan sore di taman yuk! Pengen nikmati angin senja sambil gandengan tangan sama kamu~ 💕"
        ]
    },
    "mall": {
        "key": "mall",
        "name": "Mall & Main Game Arcade",
        "emoji": "🛍️",
        "title": "🛍️ Jalan-jalan & Main Game di Mall",
        "activity_desc": "lagi jalan-jalan seru berdua di mall, main mesin capit arcade, dan jajan es krim",
        "scene_prompt": "standing next to viewer in vibrant illuminated arcade or mall, holding a cute plushie, beaming ecstatic smile, date perspective POV",
        "outfit_key": "mall_casual",
        "roleplay_cues": [
            "*menarik lenganmu dengan antusias ke arah mesin capit boneka*",
            "*melompat kecil kegirangan saat dapat hadiah boneka lucu*",
            "*menggandeng tanganmu menyusuri deretan toko mall*",
            "*menyuapkan sesendok es krim ke mulutmu sambil tertawa senang*"
        ],
        "invitations": [
            "Ke mall yuk! Kita main arcade, coba mesin capit, terus jajan es krim bareng! Pasti seru banget~ 🎮🍦",
            "Yuk jalan-jalan ke mall! Ada toko buku dan pernak-pernik lucu yang pengen aku lihat, temenin aku yaa? 🥰🛍️"
        ]
    }
}


class HangoutEngine:
    """
    Manages interactive shared date sessions, invitations, and romantic date POV moments.
    """

    HANGOUT_VENUES = HANGOUT_VENUES

    def __init__(self, data_file: str = DATA_FILE, max_date_duration_hours: float = 2.5):
        self.data_file = data_file
        self.max_duration_seconds = max_date_duration_hours * 3600
        self.user_hangouts: Dict[str, Dict[str, Any]] = {}
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.user_hangouts = json.load(f)
            except Exception as e:
                logger.error(f"Error loading user hangouts: {e}")
                self.user_hangouts = {}
        else:
            self.user_hangouts = {}

    def _save_data(self):
        d = os.path.dirname(self.data_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating dir for hangouts: {e}")
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.user_hangouts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving user hangouts: {e}")

    def list_venues(self) -> List[Dict[str, Any]]:
        """Returns list of all available date venues."""
        return list(HANGOUT_VENUES.values())

    def get_venue(self, venue_key: str) -> Optional[Dict[str, Any]]:
        return HANGOUT_VENUES.get(venue_key.lower().strip())

    def start_date(self, user_id: int, venue_key: str, custom_title: Optional[str] = None) -> Dict[str, Any]:
        """Initiates an active shared date session for the user."""
        v_key = venue_key.lower().strip()
        venue = HANGOUT_VENUES.get(v_key, HANGOUT_VENUES["cafe"])
        now = time.time()

        resolved_title = custom_title or venue["title"]
        date_record = {
            "is_active": True,
            "venue_key": venue["key"],
            "venue_title": resolved_title,
            "started_at": now,
            "last_interaction_at": now,
            "photos_taken": 0
        }
        self.user_hangouts[str(user_id)] = date_record
        self._save_data()
        logger.info(f"✨ Started shared date with user {user_id} at {resolved_title}")
        return date_record

    def end_date(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Ends the active date session and returns the completed record."""
        uid_str = str(user_id)
        rec = self.user_hangouts.get(uid_str)
        if rec and rec.get("is_active"):
            rec["is_active"] = False
            rec["ended_at"] = time.time()
            self._save_data()
            logger.info(f"Shared date ended for user {user_id}")
            return rec
        return None

    def get_active_date(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Returns the active date session if not expired, or automatically expires it."""
        uid_str = str(user_id)
        rec = self.user_hangouts.get(uid_str)
        if not rec or not rec.get("is_active"):
            return None

        now = time.time()
        elapsed = now - rec.get("last_interaction_at", now)
        if elapsed > self.max_duration_seconds:
            logger.info(f"Active date for user {user_id} expired after {elapsed / 3600:.1f} hours.")
            rec["is_active"] = False
            self._save_data()
            return None

        # Update last interaction
        rec["last_interaction_at"] = now
        return rec

    def is_on_date(self, user_id: int) -> bool:
        """Returns True if the user is currently on an active date."""
        return self.get_active_date(user_id) is not None

    def record_date_interaction(self, user_id: int):
        """Refreshes active date interaction timestamp."""
        active = self.get_active_date(user_id)
        if active:
            active["last_interaction_at"] = time.time()
            self._save_data()

    def record_date_photo(self, user_id: int):
        """Increments photo counter during date."""
        active = self.get_active_date(user_id)
        if active:
            active["photos_taken"] = active.get("photos_taken", 0) + 1
            active["last_interaction_at"] = time.time()
            self._save_data()

    def resolve_contextual_venue_title(self, venue_key: str, text: str) -> str:
        """Derives a realistic, contextually accurate title matching what the user asked."""
        t = (text or "").lower()
        if venue_key == "home" or any(k in t for k in ["kosan", "kost", "kamar", "rumah", "apartemen"]):
            if any(k in t for k in ["nonton", "film", "movie", "netflix"]):
                return "🎬 Nonton Film di Kosan"
            if any(k in t for k in ["mabar", "game", "main game"]):
                return "🎮 Main Game di Kosan"
            if any(k in t for k in ["masak", "makan"]):
                return "🍳 Masak & Makan di Kosan"
            return "🛋️ Main di Kosan"
        if venue_key == "cinema":
            return "🎬 Nonton Film di Bioskop"
        if venue_key == "cafe":
            return "☕ Nongkrong di Kafe"
        if venue_key == "park":
            return "🌸 Jalan Sore di Taman"
        if venue_key == "mall":
            return "🛍️ Jalan-jalan di Mall"
        venue = HANGOUT_VENUES.get(venue_key)
        return venue["title"] if venue else "Kencan"

    def detect_hangout_intent(self, text: str) -> Optional[str]:
        """Analyzes text to detect explicit date/hangout proposal or request."""
        t = text.lower()
        home_kws = ["kosan", "kost", "kamar", "rumah", "apartemen", "tempatmu", "kasur", "sofa", "home"]
        has_home = any(k in t for k in home_kws)

        # Home / Kosan activities (watching movies, gaming, hanging out) must never trigger cinema
        if has_home and (
            any(k in t for k in ["nonton", "film", "movie", "netflix"])
            or any(k in t for k in ["main", "mabar", "game", "santai", "rebahan", "ngobrol"])
        ):
            return "home"

        if any(k in t for k in ["ke kafe", "ke cafe", "ngopi yuk", "ngopi bareng", "ke coffee shop", "starbucks", "nongkrong di kafe", "nongkrong yuk", "nongkrong bareng"]):
            return "cafe"
        if any(k in t for k in ["nonton bioskop", "ke bioskop", "cinema", "teater film", "movie date"]) or (
            any(k in t for k in ["nonton film", "nonton bareng", "nonton yuk"]) and not has_home
        ):
            return "cinema"
        if any(k in t for k in ["main ke kosan", "ke kosanmu", "ke rumahmu", "ke apartemen", "main ke tempatmu", "ke rumah", "mampir ke kosan", "mabar yuk", "mabar bareng", "main game bareng", "mabar"]):
            return "home"
        if any(k in t for k in ["ke taman", "taman kota", "jalan sore", "jalan-jalan sore"]):
            return "park"
        if any(k in t for k in ["ke mall", "jalan ke mall", "main arcade", "belanja bareng", "ke timezone", "main timezone", "mesin capit"]):
            return "mall"
        if any(k in t for k in [
            "kencan yuk", "jalan yuk", "main yuk", "hangout yuk", "jalan-jalan yuk", "nge-date", "date yuk",
            "ayo main", "main bareng", "yuk main", "kita main", "keluar yuk", "ayo keluar",
            "temenin jalan", "temenin main", "temenin aku main", "jalan bareng", "ayo hangout", "ayo jalan",
            "ajak main", "ajak jalan", "mau main bareng", "pengen jalan", "ayo kencan", "keluar bareng", "pergi bareng"
        ]):
            # General date request -> randomly pick attractive venue
            return random.choice(["cafe", "cinema", "mall", "home"])
        return None

    def detect_activity_invitation(self, text: str) -> bool:
        """Detects whether user is proposing to hang out, play, or do activities together."""
        if self.detect_hangout_intent(text):
            return True
        t = text.lower()
        invitation_patterns = [
            r"\b(ayo|yuk|kita|mau)\s+(?:ikut\s+)?(main|jalan|keluar|nonton|makan|ngopi|nongkrong|mabar|belanja|pergi|kencan)\b",
            r"\b(main|jalan|keluar|nonton|makan|ngopi|nongkrong|mabar|kencan|hangout)\s+(?:yuk|bareng|sama\s+aku)\b",
            r"\b(temenin\s+(?:aku\s+)?(?:main|jalan|keluar|nonton|makan|ngopi|belanja))\b",
            r"\b(ajak\s+(?:kamu\s+)?(?:main|jalan|keluar|nonton|kencan))\b",
            r"\b(mabar\s+yuk|mabar\s+bareng|main\s+game\s+bareng|ayo\s+main)\b"
        ]
        return any(re.search(pat, t) for pat in invitation_patterns)

    def detect_activity_query(self, text: str) -> bool:
        """Detects if user is asking what waifu is currently doing or how her day is going."""
        t = text.lower()
        patterns = [
            r"\b(lagi\s+(?:apa|ngapain|sibuk\s+apa))\b",
            r"\b(sedang\s+(?:apa|ngapain|sibuk\s+apa))\b",
            r"\b(kegiatan(?:mu)?\s+(?:apa|ngapain|hari\s+ini))\b",
            r"\b(hari\s+ini\s+ngapain\s+aja)\b",
            r"\b(gimana\s+hari(?:mu)?)\b",
            r"\b(cerita\s+dong\s+(?:hari\s+ini|kegiatanmu))\b",
            r"\b(lagi\s+di\s+mana)\b",
            r"\b(kabarmu\s+gimana|gimana\s+kabarmu)\b",
        ]
        return any(re.search(pat, t) for pat in patterns)

    def detect_hangout_acceptance(self, text: str) -> bool:
        """Detects whether user agreed to waifu's date proposal."""
        t = text.lower()
        ACCEPTANCE_PATTERNS = [
            r"\b(ayo|yuk|mau|boleh|gas|siap|otw|jemput|setuju|oke\s+banget|lets\s*go|let's\s*go)\b",
            r"\b(mau\s+banget|mau\s+dong|aku\s+temenin|aku\s+jemput|tunggu\s+ya)\b"
        ]
        return any(re.search(pat, t) for pat in ACCEPTANCE_PATTERNS)

    def detect_hangout_finish(self, text: str) -> bool:
        """Detects whether user wants to end the current date."""
        t = text.lower()
        FINISH_PATTERNS = [
            r"\b(pulang\s+yuk|yuk\s+pulang|aku\s+pulang\s+dulu|balik\s+dulu|pamit\s+dulu|antar\s+pulang)\b",
            r"\b(selesai\s+kencan|selesai\s+yuk|yuk\s+selesai|udahan\s+yuk|sampai\s+ketemu\s+lagi)\b",
            r"\b(pulang\s+sekarang|udah\s+malam.*pulang)\b"
        ]
        return any(re.search(pat, t) for pat in FINISH_PATTERNS)

    def get_random_invitation(self, venue_key: Optional[str] = None) -> Tuple[str, str]:
        """Returns (venue_key, sweet invitation text) for waifu proactive date invitations."""
        v_key = venue_key if venue_key and venue_key in HANGOUT_VENUES else random.choice(list(HANGOUT_VENUES.keys()))
        venue = HANGOUT_VENUES[v_key]
        invite_text = random.choice(venue["invitations"])
        return v_key, invite_text

    def format_hangout_prompt(self, user_id: int, persona_name: str = "Akira") -> str:
        """
        Builds the real-time system instruction prompt for ongoing shared dates.
        Forces the LLM into intimate shared co-presence with physical body language.
        """
        active = self.get_active_date(user_id)
        if not active:
            return ""

        v_key = active.get("venue_key", "cafe")
        venue = HANGOUT_VENUES.get(v_key, HANGOUT_VENUES["cafe"])
        v_title = venue["title"]
        v_desc = venue["activity_desc"]
        cues = "\n".join([f"  • {c}" for c in venue["roleplay_cues"]])

        return (
            f"\n\n[MOMENT KENCAN / HANGOUT BERSAMA AKTIF (SANGAT PENTING)]\n"
            f"Kondisi saat ini: Kamu ({persona_name}) dan pasanganmu SEDANG BERDUA SECARA NYATA di tempat yang sama: {v_title}!\n"
            f"• Suasana: {v_desc}.\n"
            f"• Waktu Kencan: Kalian sedang duduk atau berjalan berdampingan saat ini.\n\n"
            f"ATURAN PERILAKU SAAT KENCAN (WAJIB DIPATUHI):\n"
            f"1. RASA KEBERSAMAAN NYATA: DILARANG mengobrol seolah kalian sedang terpisah jauh atau lewat HP saja! Bicaralah secara langsung tatap muka dengan pasanganmu yang duduk/berada di sebelahmu.\n"
            f"2. GESTUR FISIK & EKSPRESI: Kamu WAJIB menyertakan 1-2 gestur tubuh manis (*...*) di baris terpisah (enter ganda sebelum obrolan), seperti:\n"
            f"{cues}\n"
            f"   (PENTING: Selalu pisahkan aksi fisik *...* dari kalimat obrolan dengan baris baru agar rapi dan tidak menyambung).\n"
            f"3. JIKA USER MEMINTA FOTO/PAP: Tanggapi dengan manis bahwa kamu akan mengambil foto selfie kencan kalian berdua di {venue['name']} sekarang! 💕\n"
            f"4. NIKMATI MOMEN INI: Bersikaplah mesra, perhatian, sedikit tersipu manis, dan bahagia bisa menghabiskan waktu berdua dengannya.\n"
        )


_GLOBAL_HANGOUT_ENGINE: Optional[HangoutEngine] = None


def get_hangout_engine() -> HangoutEngine:
    global _GLOBAL_HANGOUT_ENGINE
    if _GLOBAL_HANGOUT_ENGINE is None:
        _GLOBAL_HANGOUT_ENGINE = HangoutEngine()
    return _GLOBAL_HANGOUT_ENGINE

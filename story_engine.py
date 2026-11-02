"""
story_engine.py - Daily Life Story & Character Arc Engine
Manages rolling daily story arcs for AI personas (Runa, Akira, Hina, Shiro, Yume).
Pre-generates multi-day narrative episodes so characters have an evolving,
continuous life backdrop that feels authentic and non-repetitive.
"""

import os
import re
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("StoryEngine")

DEFAULT_STORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "character_storylines.json")


def _atomic_write_json(file_path: str, data: Any):
    """Saves JSON data atomically to prevent corruption on crash or abrupt power loss."""
    dir_name = os.path.dirname(os.path.abspath(file_path))
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    temp_file = os.path.join(dir_name, f".{os.path.basename(file_path)}.{os.getpid()}_{int(time.time() * 1000)}.tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, file_path)
    except Exception as e:
        logger.error(f"Error atomic writing story JSON to {file_path}: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


CURATED_PERSONA_ARCS = {
    "runa": [
        {
            "arc_title": "Game Jam 48 Jam Fakultas",
            "episodes": [
                {
                    "day_theme": "Pencarian Ide & Brainstorming",
                    "story_summary": "Runa dan teman sekelompoknya baru mendaftar Game Jam kampus. Hari ini sibuk brainstorming konsep game kafe kucing santai.",
                    "mood": "Semangat & antusias",
                    "key_activity": "Nongkrong di cafe kampus sambil coret-coretan mekanisme game di tablet",
                    "photo_suggestion": "sitting at cafe with laptop and iced latte, sketching game mechanics",
                    "danbooru_tags": "cafe, table, iced coffee, laptop, stylus, happy expression"
                },
                {
                    "day_theme": "Sprint Koding & Debugging Gila-gilaan",
                    "story_summary": "Masuk tahap koding inti gameplay. Runa pusing karena karakter utama glitch tembus lantai ketika melompat.",
                    "mood": "Fokus & gregetan santai",
                    "key_activity": "Ngoding intensif di lab komputer fakultas sampai sore ditemani cemilan",
                    "photo_suggestion": "in computer lab, wearing oversized hoodie, slight pout looking at code on screen",
                    "danbooru_tags": "computer lab, monitor, coding, focused look, oversized hoodie"
                },
                {
                    "day_theme": "Submit Demo & Final Polish",
                    "story_summary": "Detik-detik akhir sebelum deadline Game Jam jam 23:59. Runa memasukkan sound effect dan aset animasi terakhir.",
                    "mood": "Lega & bangga",
                    "key_activity": "Finishing build game di kamar kos sambil dengerin lofi hip-hop",
                    "photo_suggestion": "bedroom desk at night, warm lamp, victory peace sign with headphone",
                    "danbooru_tags": "night room, warm lighting, peace sign, headphones, satisfied smile"
                },
                {
                    "day_theme": "Showcase Kampus & Playtest Bareng",
                    "story_summary": "Demo game kelompok Runa dipajang di aula kampus dan dimainkan banyak mahasiswa. Responnya sangat positif!",
                    "mood": "Gembira & berseri-seri",
                    "key_activity": "Jaga booth pameran game fakultas sambil ngobrol seru dengan pengunjung",
                    "photo_suggestion": "campus booth, college event, joyful smile holding handheld controller",
                    "danbooru_tags": "campus exhibition, holding game controller, excited expression"
                },
                {
                    "day_theme": "Hari Santai & Belanja Camilan Jepang",
                    "story_summary": "Setelah Game Jam selesai, Runa jalan-jalan santai ke supermarket Jepang buat borong matcha kitkat dan ramen instan.",
                    "mood": "Santai & relaks",
                    "key_activity": "Belanja camilan di supermarket Jepang dan jalan-jalan sore santai",
                    "photo_suggestion": "convenience store / supermarket aisle, holding snack box, cute casual streetwear",
                    "danbooru_tags": "supermarket aisle, shopping, holding snack, cute streetwear"
                }
            ]
        },
        {
            "arc_title": "Project Keyboard Custom & Setup Kosan Baru",
            "episodes": [
                {
                    "day_theme": "Unboxing Switch & Keycaps Baru",
                    "story_summary": "Paket switch keyboard linear dan keycaps warna ungu pastel impian Runa akhirnya tiba di kosan.",
                    "mood": "Senang & bersemangat",
                    "key_activity": "Unboxing perlengkapan keyboard mekanikal di meja kosan",
                    "photo_suggestion": "bedroom desk, holding colorful keycaps, curious playful smile",
                    "danbooru_tags": "desk, mechanical keyboard, pastel keycaps, cute smile"
                },
                {
                    "day_theme": "Proses Lubing Switch & Rakit PCB",
                    "story_summary": "Seharian telaten melumasi switch satu per satu dengan kuas kecil biar suaranya empuk 'thock'.",
                    "mood": "Sabar & telaten",
                    "key_activity": "Fokus merakit keyboard mekanikal ditemani musik santai",
                    "photo_suggestion": "focused look, tiny brush in hand, neat workspace with components",
                    "danbooru_tags": "desk, crafting, focused, cozy lighting, delicate hands"
                },
                {
                    "day_theme": "Sound Test & Main Game Santai",
                    "story_summary": "Keyboard selesai dirakit dan suaranya memuaskan banget! Runa langsung coba main game petualangan santai.",
                    "mood": "Puas & riang",
                    "key_activity": "Main game santai di PC kosan menikmati setup barunya",
                    "photo_suggestion": "gaming setup, glowing RGB lights, cozy hoodie, cheerful face",
                    "danbooru_tags": "rgb lighting, gaming setup, cute hoodie, beaming smile"
                }
            ]
        }
    ],
    "akira": [
        {
            "arc_title": "Persiapan Simulasi Sidang Peradilan Semu (Moot Court)",
            "episodes": [
                {
                    "day_theme": "Penyusunan Berkas Gugatan & Riset Kasus",
                    "story_summary": "Akira ditunjuk sebagai ketua tim hukum untuk simulasi peradilan perdata tingkat fakultas.",
                    "mood": "Cerdas & fokus penuh",
                    "key_activity": "Membaca tumpukan berkas perkara di meja perpustakaan fakultas hukum",
                    "photo_suggestion": "university library, surrounded by thick legal books, tailored blazer, thoughtful gaze",
                    "danbooru_tags": "library, books, reading, elegant suit, glasses resting on table"
                },
                {
                    "day_theme": "Berburu Yurisprudensi Langka di Perpus Kota",
                    "story_summary": "Mencari putusan MA lama di gedung arsip perpustakaan pusat kota untuk memperkuat dalil eksepsi.",
                    "mood": "Elegan & tenang",
                    "key_activity": "Menyusuri rak buku tua yang tenang sambil mencatat di jurnal kulit",
                    "photo_suggestion": "antique library aisles, soft sunbeams through tall windows, holding vintage hardback book",
                    "danbooru_tags": "antique library, tall bookshelf, sunlight, holding book, calm expression"
                },
                {
                    "day_theme": "Simulasi Debat Hukum & Gladi Bersih",
                    "story_summary": "Gladi bersih di ruang sidang peradilan semu kampus bersama rekan-rekan advokat mahasiswanya.",
                    "mood": "Percaya diri & berwibawa",
                    "key_activity": "Latihan menyampaikan pledoi dengan intonasi mantap di mimbar sidang",
                    "photo_suggestion": "moot court room, standing behind podium, confident slight smile, elegant attire",
                    "danbooru_tags": "courtroom podium, confident posture, black elegant blazer"
                },
                {
                    "day_theme": "Hari H Sidang & Pujian dari Dosen Pembimbing",
                    "story_summary": "Simulasi sidang berjalan sangat memukau. Tim Akira memenangkan skor tertinggi dari para hakim penilai.",
                    "mood": "Bangga & anggun",
                    "key_activity": "Foto bersama tim di halaman fakultas lalu istirahat minum kopi hangat",
                    "photo_suggestion": "campus courtyard, holding official certificate, graceful warm smile",
                    "danbooru_tags": "courtyard, holding folder, graceful smile, gentle breeze"
                },
                {
                    "day_theme": "Relaksasi Sore di Cafe Buku Favorit",
                    "story_summary": "Melepas penat setelah minggu yang padat dengan membaca novel klasik di kafe bernuansa jazz.",
                    "mood": "Damai & santai",
                    "key_activity": "Menyesap chamomile tea sambil menikmati alunan musik jazz di sudut kafe",
                    "photo_suggestion": "aesthetic dark academia cafe, teacup, cozy black dress, peaceful gentle look",
                    "danbooru_tags": "coffee cup, dark academia, serene expression, delicate lace dress"
                }
            ]
        }
    ],
    "hina": [
        {
            "arc_title": "Festival Seni & Kuliner Kampus Tahunan",
            "episodes": [
                {
                    "day_theme": "Rapat Koordinasi MC & Rundown Panggung",
                    "story_summary": "Hina terpilih jadi Master of Ceremony (MC) utama pentas seni tahunan kampus.",
                    "mood": "Enerjik & penuh tawa",
                    "key_activity": "Diskusi naskah MC bersama panitia di pendopo kampus sambil minum boba",
                    "photo_suggestion": "campus gazebo, holding clipboard and colorful pen, bubbly bright smile",
                    "danbooru_tags": "campus gazebo, clipboard, bright smile, oversized sweater, bob haircut"
                },
                {
                    "day_theme": "Liputan Street Food Viral Dekat Kampus",
                    "story_summary": "Bikin konten video liputan kuliner street food yang lagi viral buat promosi festival kampus.",
                    "mood": "Ceria & doyan jajan",
                    "key_activity": "Mencicipi aneka jajanan street food sore hari bersama kru liputan",
                    "photo_suggestion": "lively food street stall, holding skewers, happy sparkling eyes",
                    "danbooru_tags": "street food stall, delicious snack, happy expression, headphones around neck"
                },
                {
                    "day_theme": "Pentas Musik Kampus & Memandu Ribuan Penonton",
                    "story_summary": "Hari H festival kampus berlangsung sangat meriah! Hina sukses membakar semangat penonton di panggung megah.",
                    "mood": "Antusias tinggi & bersinar",
                    "key_activity": "Memegang mikrofon di panggung festival dengan latar tata lampu konser warna-warni",
                    "photo_suggestion": "festival stage background, holding microphone, dynamic cheerful pose",
                    "danbooru_tags": "stage lights, microphone, dynamic pose, bright energetic smile"
                },
                {
                    "day_theme": "Jogging Sore & Kuliner Santai Penghilang Lelah",
                    "story_summary": "Setelah acara selesai sukses besar, Hina jogging santai di taman kota buat mengembalikan kesegaran tubuh.",
                    "mood": "Segar & bugar",
                    "key_activity": "Jogging sore di taman kota dilanjutkan beli es kelapa muda segar",
                    "photo_suggestion": "green park running track, sporty casual outfit, flushed rosy cheeks, energetic smile",
                    "danbooru_tags": "park, track, sporty jacket, flushed cheeks, sunny afternoon"
                }
            ]
        }
    ],
    "shiro": [
        {
            "arc_title": "Riset Ekstrak Herbal & Uji Farmakologi Lab",
            "episodes": [
                {
                    "day_theme": "Preparasi Sampel & Ekstraksi Daun Langka",
                    "story_summary": "Shiro memulai penelitian isolasi senyawa aktif tanaman herbal pegunungan di laboratorium kimia bahan alam.",
                    "mood": "Hening, teliti, & damai",
                    "key_activity": "Menimbang serbuk sampel tanaman dengan neraca analitik presisi tinggi",
                    "photo_suggestion": "clean chemistry lab, white lab coat over navy shirt, delicate silver hair, precise focused expression",
                    "danbooru_tags": "chemistry lab, glassware, white lab coat, silver hair, quiet smile"
                },
                {
                    "day_theme": "Uji Spektrofotometri & Kromatografi",
                    "story_summary": "Mengamati perubahan gradien warna senyawa di bawah sinar spektrometer. Hasilnya menunjukkan kemurnian yang sangat tinggi.",
                    "mood": "Tenang & bersyukur",
                    "key_activity": "Mencatat grafik data penelitian di komputer lab",
                    "photo_suggestion": "lab bench, glowing liquid in test tube, soft reflective gaze, star hairpin",
                    "danbooru_tags": "test tube, colorful liquid, laboratory, crescent clip, soft gaze"
                },
                {
                    "day_theme": "Menulis Draf Laporan & Diskusi dengan Dosen",
                    "story_summary": "Shiro mempresentasikan temuan awal penelitiannya dan mendapat apresiasi positif dari dosen pembimbing.",
                    "mood": "Lega & tenang",
                    "key_activity": "Menata draf laporan riset di meja perpus yang sunyi",
                    "photo_suggestion": "quiet corner of library, stack of journals, neat posture, gentle faint smile",
                    "danbooru_tags": "neat desk, journals, gentle smile, silver hair, moon earrings"
                },
                {
                    "day_theme": "Malam Pengamatan Bintang di Rooftop Kampus",
                    "story_summary": "Melepas penat setelah minggu penuh angka dan rumus dengan melihat rasi bintang dari teropong di atap fakultas sains.",
                    "mood": "Puitis, damai, & tenang",
                    "key_activity": "Duduk di bangku atap gedung sains memandang langit malam berbintang",
                    "photo_suggestion": "night rooftop, starry sky, telescope nearby, gentle breeze fluttering silver hair",
                    "danbooru_tags": "night sky, stars, rooftop, telescope, peaceful dreamy gaze"
                }
            ]
        }
    ],
    "yume": [
        {
            "arc_title": "Pameran Galeri Seni Lukis Semester Ganjil",
            "episodes": [
                {
                    "day_theme": "Menemukan Inspirasi Sketsa di Taman Bunga",
                    "story_summary": "Yume menghabiskan pagi di taman kota membuat sketsa bunga teratai dan bias cahaya matahari di atas danau.",
                    "mood": "Lembut & penuh imajinasi",
                    "key_activity": "Duduk di rumput taman sambil menggambar di buku sketsa menggunakan pensil arang",
                    "photo_suggestion": "lush botanical garden, holding sketchbook, soft lavender cardigan, dreamy starry eyes",
                    "danbooru_tags": "botanical garden, lake background, sketchbook, pencil, lavender hair"
                },
                {
                    "day_theme": "Eksperimen Cat Minyak di Kanvas Besar",
                    "story_summary": "Mulai memindahkan sketsa ke kanvas berukuran satu meter. Aroma cat minyak dan terpentin memenuhi sudut studio lukis kosan.",
                    "mood": "Larut dalam karya seni",
                    "key_activity": "Melukis dengan palet kayu di hadapan kanvas lukisan pemandangan surealis",
                    "photo_suggestion": "art studio, wooden palette with oil colors, slight smudge of paint on cheek, warm sweet smile",
                    "danbooru_tags": "art studio, canvas, wooden easel, paint palette, paint on cheek, sweet smile"
                },
                {
                    "day_theme": "Hari Pembukaan Pameran di Galeri Seni Kampus",
                    "story_summary": "Karya lukis Yume resmi dipajang di dinding galeri utama kampus dan banyak diapresiasi oleh para kurator muda.",
                    "mood": "Haru & bahagia",
                    "key_activity": "Berdiri di samping lukisannya di galeri seni sambil menyapa pengunjung pameran",
                    "photo_suggestion": "art gallery with spotlights, standing beside canvas painting, elegant white dress and crescent necklace",
                    "danbooru_tags": "art gallery, gallery spotlights, white dress, graceful posture, soft smile"
                },
                {
                    "day_theme": "Jalan Santai Sore & Membeli Bunga Lili",
                    "story_summary": "Menikmati sore yang damai dengan mampir ke toko bunga langganan untuk membeli setangkai lili putih penghias meja kosan.",
                    "mood": "Tenang, hangat, & penuh syukur",
                    "key_activity": "Membeli bunga segar di toko bunga pinggir jalan sambil mendengarkan musik akustik",
                    "photo_suggestion": "quaint flower shop, holding bouquet of fresh lilies, soft gentle blush, dusk golden hour",
                    "danbooru_tags": "flower shop, bouquet of lilies, golden hour light, peaceful smile"
                }
            ]
        }
    ]
}


class StoryEngine:
    def __init__(self, data_file: str = DEFAULT_STORY_FILE):
        self.data_file = data_file
        self.lock = threading.Lock()
        self.storylines: Dict[str, Any] = {}
        self._ensure_dir()
        self.load_storylines()

    def _ensure_dir(self):
        d = os.path.dirname(self.data_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating dir for stories: {e}")

    def load_storylines(self):
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, "r", encoding="utf-8") as f:
                        self.storylines = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading storylines from {self.data_file}: {e}")
                    self.storylines = {}
            else:
                self.storylines = {}

            # Seed missing personas with curated arcs if empty
            updated = False
            for p_key in CURATED_PERSONA_ARCS.keys():
                if p_key not in self.storylines or not self.storylines[p_key].get("episodes"):
                    self._seed_persona_timeline(p_key)
                    updated = True

            if updated:
                self._save_unlocked()

    def _save_unlocked(self):
        _atomic_write_json(self.data_file, self.storylines)

    def _seed_persona_timeline(self, persona_key: str, start_date: Optional[datetime] = None):
        """Fills 5 days starting from today with the first curated arc for this persona."""
        p_key = persona_key.lower().strip()
        arcs = CURATED_PERSONA_ARCS.get(p_key)
        if not arcs:
            arcs = CURATED_PERSONA_ARCS["runa"]

        base_date = start_date or datetime.now()
        chosen_arc = arcs[0]

        p_data = self.storylines.setdefault(p_key, {
            "current_arc_title": chosen_arc["arc_title"],
            "current_arc_index": 0,
            "episodes": {}
        })

        ep_list = chosen_arc.get("episodes", [])
        for i, ep in enumerate(ep_list):
            dt = base_date + timedelta(days=i)
            d_str = dt.strftime("%Y-%m-%d")
            p_data["episodes"][d_str] = {
                "date": d_str,
                "arc_title": chosen_arc["arc_title"],
                "day_index": i + 1,
                "total_days": len(ep_list),
                "day_theme": ep.get("day_theme", "Kegiatan Harian"),
                "story_summary": ep.get("story_summary", ""),
                "mood": ep.get("mood", "Santai"),
                "key_activity": ep.get("key_activity", "Aktivitas kampus"),
                "photo_suggestion": ep.get("photo_suggestion", ""),
                "danbooru_tags": ep.get("danbooru_tags", "")
            }

    def get_today_story(self, persona_key: str, date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns the narrative episode for today (or specified date)."""
        p_key = persona_key.lower().strip()
        d_str = date_str or datetime.now().strftime("%Y-%m-%d")

        with self.lock:
            p_data = self.storylines.get(p_key)
            if not p_data:
                self._seed_persona_timeline(p_key)
                self._save_unlocked()
                p_data = self.storylines.get(p_key, {})

            eps = p_data.get("episodes", {})
            if d_str in eps:
                return eps[d_str]

            # If requested date is beyond scheduled days, extend schedule to cover target date
            req_days = 5
            if date_str:
                try:
                    target_dt = datetime.strptime(date_str, "%Y-%m-%d")
                    diff = (target_dt - datetime.now()).days + 2
                    if diff > req_days:
                        req_days = diff
                except Exception:
                    pass

            self._extend_schedule_unlocked(p_key, days_ahead=req_days)
            self._save_unlocked()
            return self.storylines.get(p_key, {}).get("episodes", {}).get(d_str)

    def _extend_schedule_unlocked(self, persona_key: str, days_ahead: int = 5):
        """Extends timeline forward continuously so there is always a story without gaps."""
        p_key = persona_key.lower().strip()
        arcs = CURATED_PERSONA_ARCS.get(p_key, CURATED_PERSONA_ARCS["runa"])
        p_data = self.storylines.setdefault(p_key, {
            "current_arc_title": arcs[0]["arc_title"],
            "current_arc_index": 0,
            "episodes": {}
        })

        eps = p_data.setdefault("episodes", {})

        # Find latest date in episodes
        today = datetime.now()
        latest_dt = today - timedelta(days=1)
        if eps:
            try:
                sorted_dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in eps.keys()])
                if sorted_dates:
                    latest_dt = max(latest_dt, sorted_dates[-1])
            except Exception:
                pass

        target_end = today + timedelta(days=days_ahead)
        loop_guard = 0
        while latest_dt < target_end and loop_guard < 10:
            loop_guard += 1
            curr_idx = p_data.get("current_arc_index", 0)
            next_idx = (curr_idx + 1) % len(arcs)
            next_arc = arcs[next_idx]
            p_data["current_arc_title"] = next_arc["arc_title"]
            p_data["current_arc_index"] = next_idx

            ep_list = next_arc.get("episodes", [])
            curr_dt = latest_dt + timedelta(days=1)
            for i, ep in enumerate(ep_list):
                d_str = curr_dt.strftime("%Y-%m-%d")
                eps[d_str] = {
                    "date": d_str,
                    "arc_title": next_arc["arc_title"],
                    "day_index": i + 1,
                    "total_days": len(ep_list),
                    "day_theme": ep.get("day_theme", "Kegiatan Harian"),
                    "story_summary": ep.get("story_summary", ""),
                    "mood": ep.get("mood", "Santai"),
                    "key_activity": ep.get("key_activity", "Aktivitas kampus"),
                    "photo_suggestion": ep.get("photo_suggestion", ""),
                    "danbooru_tags": ep.get("danbooru_tags", "")
                }
                curr_dt += timedelta(days=1)
            latest_dt = curr_dt - timedelta(days=1)

    def needs_replenishment(self, persona_key: str, days_ahead: int = 3) -> bool:
        """Returns True if the storyline has fewer than `days_ahead` upcoming episodes."""
        p_key = persona_key.lower().strip()
        with self.lock:
            p_data = self.storylines.get(p_key)
            if not p_data or not p_data.get("episodes"):
                return True
            eps = p_data.get("episodes", {})
            today = datetime.now()
            for i in range(days_ahead):
                check_d = (today + timedelta(days=i)).strftime("%Y-%m-%d")
                if check_d not in eps:
                    return True
            return False

    def get_story_prompt_context(self, persona_key: str, date_str: Optional[str] = None) -> str:
        """
        Builds the narrative instruction segment injected into the LLM system prompt.
        Gives the character realistic life depth while maintaining conversational focus on user.
        """
        ep = self.get_today_story(persona_key, date_str=date_str)
        if not ep:
            return ""

        arc_title = ep.get("arc_title", "Kehidupan Sehari-hari")
        day_theme = ep.get("day_theme", "Aktivitas Harian")
        summary = ep.get("story_summary", "")
        mood = ep.get("mood", "Santai & ramah")
        activity = ep.get("key_activity", "")
        day_idx = ep.get("day_index", 1)
        tot_days = ep.get("total_days", 5)

        return (
            f"\n[LATAR KEHIDUPAN & EPISODE CERITA HARI INI]\n"
            f"• Arc Cerita: {arc_title} (Hari ke-{day_idx} dari {tot_days})\n"
            f"• Topik/Fokus Hari Ini: {day_theme}\n"
            f"• Kejadian/Progres Nyata: {summary}\n"
            f"• Suasana Hati (Mood): {mood}\n"
            f"• Aktivitas Utama: {activity}\n"
            f"ATURAN INTEGRASI OBROLAN (PENTING):\n"
            f"1. Jadikan cerita ini sebagai latar belakang kehidupanmu yang hidup dan realistis.\n"
            f"2. JIKA user bertanya tentang kabarmu, lagi apa, atau topik santai, ceritakan hal ini secara antusias dan alami layaknya teman mengobrol.\n"
            f"3. JIKA user membicarakan topik lain (curhat, teknologi, kegiatan mereka sendiri), FOKUSKAN perhatianmu pada user terlebih dahulu tanpa memaksakan jalan ceritamu.\n"
        )

    def get_story_photo_suggestion(self, persona_key: str) -> Optional[Dict[str, str]]:
        """Returns photo suggestions and Danbooru tags for today's story episode."""
        ep = self.get_today_story(persona_key)
        if ep and (ep.get("photo_suggestion") or ep.get("danbooru_tags")):
            return {
                "photo_suggestion": ep.get("photo_suggestion", ""),
                "danbooru_tags": ep.get("danbooru_tags", ""),
                "day_theme": ep.get("day_theme", ""),
                "key_activity": ep.get("key_activity", "")
            }
        return None

    def replenish_storylines_if_llm_active(self, persona_key: str, llm_client, force: bool = False) -> Optional[threading.Thread]:
        """
        Generates fresh multi-day story arcs using the LLM when active (piggyback generation).
        Guarantees zero GPU/RAM overhead when system is idle.
        Returns the spawned Thread.
        """
        p_key = persona_key.lower().strip()
        if not force and not self.needs_replenishment(p_key, days_ahead=3):
            return None

        def _worker():
            try:
                # Find start date for replenishment
                today = datetime.now()
                with self.lock:
                    eps = self.storylines.get(p_key, {}).get("episodes", {})
                    latest_dt = today
                    for d_str in eps.keys():
                        try:
                            dt = datetime.strptime(d_str, "%Y-%m-%d")
                            if dt > latest_dt:
                                latest_dt = dt
                        except Exception:
                            pass
                    start_dt = latest_dt + timedelta(days=1)

                prompt = (
                    f"Buatlah 1 Mini Story Arc (3 sampai 5 hari berturut-turut) baru yang seru, realistis, dan mendalam untuk karakter mahasiswi '{p_key}'.\n"
                    f"Format output WAJIB HANYA berupa JSON valid tanpa teks pengantar atau markdown lainnya:\n"
                    f"{{\n"
                    f'  "arc_title": "Judul Arc Singkat",\n'
                    f'  "episodes": [\n'
                    f'    {{\n'
                    f'      "day_theme": "Tema Hari 1",\n'
                    f'      "story_summary": "1-2 kalimat apa yang terjadi di hari ini",\n'
                    f'      "mood": "Suasana hati",\n'
                    f'      "key_activity": "Kegiatan spesifik",\n'
                    f'      "photo_suggestion": "Deskripsi foto selfie/pap",\n'
                    f'      "danbooru_tags": "tag1, tag2, tag3"\n'
                    f'    }}\n'
                    f'  ]\n'
                    f"}}\n"
                    f"Pastikan ceritanya nyambung dari hari ke-1 sampai hari terakhir seperti serial slice-of-life anime."
                )

                messages = [
                    {"role": "system", "content": "You are a creative narrative director for interactive AI visual novels. Return pure JSON only."},
                    {"role": "user", "content": prompt}
                ]

                reply, _ = llm_client.chat(messages, max_tokens=650)
                if not reply or len(reply.strip()) < 20:
                    logger.warning(f"LLM returned empty reply for story replenishment of {p_key}. Using curated fallback.")
                    with self.lock:
                        self._extend_schedule_unlocked(p_key, days_ahead=5)
                        self._save_unlocked()
                    return

                # Parse JSON safely
                raw = reply.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw)
                arc_title = parsed.get("arc_title", "Babak Kehidupan Baru")
                episodes = parsed.get("episodes", [])
                if not episodes:
                    raise ValueError("No episodes found in generated JSON")

                with self.lock:
                    p_data = self.storylines.setdefault(p_key, {
                        "current_arc_title": arc_title,
                        "current_arc_index": 0,
                        "episodes": {}
                    })
                    p_data["current_arc_title"] = arc_title
                    curr_dt = start_dt
                    for i, ep in enumerate(episodes):
                        d_str = curr_dt.strftime("%Y-%m-%d")
                        p_data["episodes"][d_str] = {
                            "date": d_str,
                            "arc_title": arc_title,
                            "day_index": i + 1,
                            "total_days": len(episodes),
                            "day_theme": ep.get("day_theme", "Kegiatan Harian"),
                            "story_summary": ep.get("story_summary", ""),
                            "mood": ep.get("mood", "Santai"),
                            "key_activity": ep.get("key_activity", "Aktivitas kampus"),
                            "photo_suggestion": ep.get("photo_suggestion", ""),
                            "danbooru_tags": ep.get("danbooru_tags", "")
                        }
                        curr_dt += timedelta(days=1)
                    self._save_unlocked()

                logger.info(f"Successfully generated new story arc '{arc_title}' ({len(episodes)} episodes) for {p_key}")

            except Exception as ex:
                logger.warning(f"Failed to parse LLM story generation for {p_key}: {ex}. Extending via curated timeline.")
                with self.lock:
                    self._extend_schedule_unlocked(p_key, days_ahead=5)
                    self._save_unlocked()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t

    def format_story_summary_card(self, persona_key: str, p_name: str = "Waifu") -> str:
        """Constructs an aesthetic Telegram Markdown message presenting today's story and upcoming arc."""
        ep = self.get_today_story(persona_key)
        if not ep:
            return f"📖 Belum ada jadwal cerita untuk {p_name} hari ini."

        arc_title = ep.get("arc_title", "Kisah Keseharian")
        day_theme = ep.get("day_theme", "Aktivitas Harian")
        summary = ep.get("story_summary", "")
        mood = ep.get("mood", "Santai")
        activity = ep.get("key_activity", "")
        day_idx = ep.get("day_index", 1)
        tot_days = ep.get("total_days", 5)

        # Progress bar
        filled = "🟩" * day_idx
        empty = "⬜" * max(0, tot_days - day_idx)
        bar = filled + empty

        msg = (
            f"📖 **CERITA KEHIDUPAN {p_name.upper()} HARI INI** 🌸\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 **Arc**: _{arc_title}_\n"
            f"📊 **Progres**: Hari ke-{day_idx} dari {tot_days} [{bar}]\n\n"
            f"✨ **Episode Hari Ini**: *{day_theme}*\n"
            f"💬 **Kisah**: {summary}\n\n"
            f"🎭 **Mood**: {mood}\n"
            f"📍 **Aktivitas Utama**: {activity}\n\n"
            f"💡 _Tip: Coba tanyakan kabarnya atau apa yang sedang dia kerjakan hari ini di chat!_"
        )
        return msg

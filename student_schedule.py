"""
student_schedule.py - Real-life College Student Routine & Contextual Outfit Engine
Manages college student daily schedules, dynamic conversation activities,
and ensures visual outfits realistically match real-world activities & locations.
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

STUDENT_PROFILES = {
    "runa": {
        "name": "Runa",
        "age": 21,
        "major": "Teknik Informatika / Game Development (Semester 5)",
        "campus": "Kampus Fakultas Ilmu Komputer",
        "hobbies": "main game, ngoding santai di cafe, nonton anime, jalan-jalan ke mall cari gadget/camilan",
        "style": "kawaii gamer chic, cute oversized hoodie / trendy casual streetwear, stylish choker",
        "campus_outfit": "(wearing cute pastel college outfit, oversized light jacket over casual white tee, pleated skirt, canvas tote bag:1.35)",
        "mall_outfit": "(wearing trendy modern streetwear, stylish cropped jacket, high-waist pants, small shoulder bag:1.35)",
        "cafe_outfit": "(wearing cozy oversized pastel sweater, cute denim skirt, stylish choker:1.35)",
    },
    "akira": {
        "name": "Akira",
        "age": 22,
        "major": "Ilmu Hukum (Semester 7)",
        "campus": "Kampus Fakultas Hukum",
        "hobbies": "baca buku di perpustakaan, ngopi di cafe estetik, magang kantor hukum, diskusi santai",
        "style": "gothic elegance, chic modern blazer, black dresses, refined jewelry",
        "campus_outfit": "(wearing elegant university student attire, tailored dark blazer over silk blouse, neat pleated dark skirt:1.35)",
        "mall_outfit": "(wearing fashionable elegant cocktail-casual dress, dark trench coat, sophisticated jewelry:1.35)",
        "cafe_outfit": "(wearing chic fitted dark turtleneck sweater, stylish plaid midi skirt:1.35)",
    },
    "hina": {
        "name": "Hina",
        "age": 21,
        "major": "Ilmu Komunikasi (Semester 5)",
        "campus": "Kampus FISIP",
        "hobbies": "organisasi kampus, jogging sore di taman, jajan street food/boba, foto-foto cafe",
        "style": "cheerful sunshine, bright cozy knitwear, headphones, energetic sporty casual",
        "campus_outfit": "(wearing bright college student casual, cozy cream sweater with yellow accents, denim skirt, canvas backpack:1.35)",
        "mall_outfit": "(wearing fashionable cute sunny streetwear, pastel jacket, white sneakers, cute bag:1.35)",
        "cafe_outfit": "(wearing oversized cozy knit cardigan, aesthetic hair clips, holding iced drink:1.35)",
    },
    "shiro": {
        "name": "Shiro",
        "age": 22,
        "major": "Farmasi & Sains (Semester 7)",
        "campus": "Kampus Fakultas Farmasi & Lab Sains",
        "hobbies": "praktikum lab, membaca jurnal di perpustakaan, mendengarkan musik klasik, suasana hening",
        "style": "kuudere minimalist, cool tones, elegant crisp blazers, neat moonlit accessories",
        "campus_outfit": "(wearing neat college student outfit, crisp collared white blouse, dark navy cardigan, crescent-moon clip:1.35)",
        "mall_outfit": "(wearing understated minimalist modern chic, clean tailored coat, sleek dark trousers:1.35)",
        "cafe_outfit": "(wearing cozy soft grey knit turtleneck, calm serene aesthetic:1.35)",
    },
    "yume": {
        "name": "Yume",
        "age": 21,
        "major": "Seni Rupa & Desain (Semester 5)",
        "campus": "Kampus Institut Seni & Desain",
        "hobbies": "melukis di studio/taman, dengerin musik lo-fi di kamar kos, jalan sore, fotografi analog",
        "style": "dreamy celestial, soft pastel lavender, flowing floral dresses, crescent-moon necklaces",
        "campus_outfit": "(wearing artistic college student attire, soft lavender cardigan over simple white sundress, canvas tote bag with art brushes:1.35)",
        "mall_outfit": "(wearing dreamy elegant pastel dress, delicate lace details, small cross-body bag:1.35)",
        "cafe_outfit": "(wearing soft knit lavender sweater, comfortable flowy skirt, peaceful artistic aura:1.35)",
    }
}

# Public vs Private location classification for clothing coherence
PUBLIC_KEYWORDS = [
    "mall", "shopping", "kampus", "kuliah", "kelas", "dosen", "makul",
    "perpustakaan", "perpus", "library", "cafe", "kafe", "kopi", "starbucks",
    "taman", "park", "jalan", "kantin", "bioskop", "cinema", "pasar", "supermarket",
    "street", "restoran", "restaurant"
]

PRIVATE_KEYWORDS = [
    "kamar", "kos", "kosan", "kasur", "bed", "bedroom", "kamar mandi", "bathroom",
    "shower", "mandi", "rebahan", "bantal", "selimut"
]


def get_hourly_routine(hour: int, persona_key: str = "runa") -> Dict[str, Any]:
    """
    Returns realistic college student activity, setting, and outfit for the given hour (0-23).
    """
    profile = STUDENT_PROFILES.get(persona_key.lower(), STUDENT_PROFILES["runa"])
    major = profile["major"]

    if 6 <= hour < 8:
        return {
            "activity_name": "Bangun pagi & siap-siap ke kampus",
            "activity_desc": "baru bangun tidur, cuci muka, mandi pagi, dan siap-siap berangkat kuliah pagi",
            "scene": "sitting in cozy bright morning apartment room, soft morning sunlight through window",
            "outfit_prompt": "(wearing cozy oversized morning t-shirt and comfy loungewear shorts:1.35)",
            "outfit_name": "☀️ Kaos Pagi Santai",
            "is_public": False
        }
    elif 8 <= hour < 11:
        return {
            "activity_name": f"Kuliah Pagi ({major})",
            "activity_desc": f"lagi ada jadwal kelas kuliah pagi di kampus ({major}), dengerin dosen dan nyatet materi",
            "scene": "sitting at wooden desk inside modern university lecture hall, student classroom background, bright ambient lighting",
            "outfit_prompt": profile["campus_outfit"],
            "outfit_name": "🎓 Baju Kuliah Kampus",
            "is_public": True
        }
    elif 11 <= hour < 13:
        return {
            "activity_name": "Makan siang di kantin / cafe kampus",
            "activity_desc": "lagi istirahat makan siang bareng temen di kantin kampus / cafe deket kampus",
            "scene": "sitting at aesthetic university campus cafe table, holding lunch drink, sunny vibrant ambient bokeh",
            "outfit_prompt": profile["campus_outfit"],
            "outfit_name": "🎓 Baju Kuliah Kampus",
            "is_public": True
        }
    elif 13 <= hour < 16:
        return {
            "activity_name": f"Praktikum / Nugas di Perpustakaan ({major})",
            "activity_desc": f"lagi di perpustakaan kampus ngerjain tugas kelompok & materi {major}",
            "scene": "sitting at wooden study desk in quiet university library, open textbooks, bookshelf background, warm study lamp",
            "outfit_prompt": profile["campus_outfit"],
            "outfit_name": "📚 Baju Belajar Kampus",
            "is_public": True
        }
    elif 16 <= hour < 19:
        return {
            "activity_name": "Selesai kuliah, jalan ke mall / nongkrong di cafe",
            "activity_desc": "baru beres kuliah, lagi jalan-jalan santai ke mall / nongkrong di cafe ngobrol dan belanja",
            "scene": "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting",
            "outfit_prompt": profile["mall_outfit"],
            "outfit_name": "🛍️ Streetwear Mall",
            "is_public": True
        }
    elif 19 <= hour < 21:
        return {
            "activity_name": "Balik ke kosan & makan malam santai",
            "activity_desc": "udah balik ke kosan, lagi makan malam santai sambil istirahat",
            "scene": "relaxing inside warm cozy apartment room, warm ambient lamp lighting",
            "outfit_prompt": "(wearing cute comfortable casual loungewear, oversized pastel tee, relaxed shorts:1.35)",
            "outfit_name": "🛋️ Pakaian Santai Kos",
            "is_public": False
        }
    elif 21 <= hour < 23:
        return {
            "activity_name": "Mandi malam & santai di kamar kos",
            "activity_desc": "baru beres mandi malam, lagi santai rebahan di kasur sambil dengerin musik / main game",
            "scene": "sitting comfortably on plush bed in cozy bedroom, glowing fairy lights, intimate relaxed evening ambiance",
            "outfit_prompt": "(wearing soft comfortable camisole and loungewear shorts:1.35), cozy evening style",
            "outfit_name": "🌙 Loungewear Malam",
            "is_public": False
        }
    else:  # 23:00 - 06:00
        return {
            "activity_name": "Rebahan di kasur siap-siap tidur",
            "activity_desc": "udah rebahan di kasur di bawah selimut, skincare-an dan siap-siap tidur nyenyak",
            "scene": "lying comfortably on bed with fluffy pillows and soft blanket, dim cozy night bedroom lamp",
            "outfit_prompt": "(wearing soft pastel silk pajamas:1.35), cozy bedtime sleepwear",
            "outfit_name": "🌙 Piyama Tidur",
            "is_public": False
        }


def detect_contextual_activity_and_outfit(
    user_text: str,
    history_turns: Optional[List[str]] = None,
    persona_key: str = "runa"
) -> Dict[str, Any]:
    """
    Intelligently analyzes the user's explicit request and ongoing conversation to determine:
    1. What the waifu is currently doing (activity).
    2. Where she is located (scene).
    3. What she should be wearing (outfit), strictly preventing lingerie/nude in public!
    """
    profile = STUDENT_PROFILES.get(persona_key.lower(), STUDENT_PROFILES["runa"])

    def match_scenario(text: str) -> Optional[Dict[str, Any]]:
        t = text.lower()

        # 0. Romantic / Intimate Bedroom Context (Highest Priority for explicit PAP requests)
        if any(k in t for k in ["sensual", "romantic", "romantis", "intimate", "mesra", "bedroom setting", "loving gaze"]):
            return {
                "activity": "lagi santai romantis di kamar",
                "scene": "romantic intimate bedroom setting, soft dim lighting, gentle blush, affectionate loving gaze towards viewer",
                "outfit_prompt": "(wearing alluring romantic silk slip dress with delicate lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
                "outfit_negative": "campus, backpack, casual college clothes, classroom, hoodie, outdoor clothes, jeans, winter clothes",
                "outfit_name": "💋 Pakaian Romantis (Silk Slip Dress)",
                "is_public": False
            }

        # 1. Shower / Mandi Context
        if any(k in t for k in ["mandi", "keramas", "handuk", "kamar mandi", "shower", "bath"]):
            return {
                "activity": "baru beres mandi / keramas",
                "scene": "standing in modern bathroom with soft steam, bare shoulders, post-shower glow, damp hair, bathroom mirror",
                "outfit_prompt": "(wearing only a soft bath towel wrapped around chest:1.4), bare shoulders, wet skin, damp hair",
                "outfit_negative": "clothes, shirt, pants, coat, hoodie, jeans, jacket, sweater",
                "outfit_name": "🚿 Handuk Mandi (After Shower)",
                "is_public": False
            }

        # 2. Sleep / Bed / Kamar Context
        if any(k in t for k in ["tidur", "rebahan", "kasur", "piyama", "pajamas", "ngantuk", "mimpi", "kamar", "bantal"]):
            return {
                "activity": "lagi rebahan di kasur kamar",
                "scene": "relaxing on bed with fluffy pillows, warm dim night bedroom lamp, cozy intimate bedroom",
                "outfit_prompt": "(wearing soft pastel silk camisole and sleep shorts:1.35), bedtime loungewear",
                "outfit_negative": "hoodie, jacket, coat, outdoor clothes, jeans, campus",
                "outfit_name": "🌙 Silk Pajamas",
                "is_public": False
            }

        # 3. Kitchen / Masak Context
        if any(k in t for k in ["dapur", "masak", "sarapan", "dinner", "lunch", "baking", "kitchen"]):
            return {
                "activity": "lagi masak di dapur",
                "scene": "standing in modern cozy kitchen preparing food, warm domestic lighting",
                "outfit_prompt": "(wearing cute oversized pastel knitted sweater:1.35), cozy comfy style",
                "outfit_negative": "bikini, lingerie, swimwear, naked",
                "outfit_name": "🍳 Cozy Kitchen Sweater",
                "is_public": False
            }

        # 4. Beach / Pool / Renang Context
        if any(k in t for k in ["pantai", "beach", "laut", "kolam", "renang", "swimming"]):
            return {
                "activity": "lagi di pantai / kolam renang",
                "scene": "walking along tropical beach, ocean sunset horizon, gentle sea breeze",
                "outfit_prompt": "(wearing fashionable two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel",
                "outfit_negative": "clothes, casual clothes, hoodie, sweater, jacket, shirt, pants, coat, pajamas",
                "outfit_name": "🏖️ Summer Bikini",
                "is_public": True
            }

        # 5. Cafe / Nongkrong / Kopi Context
        if any(k in t for k in ["cafe", "kafe", "kopi", "coffee", "boba", "matcha", "nongkrong", "starbucks"]):
            return {
                "activity": "lagi nongkrong santai di cafe",
                "scene": "sitting at aesthetic cafe table holding a warm beverage, beautiful bokeh background",
                "outfit_prompt": profile["cafe_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, towel",
                "outfit_name": "☕ Cozy Cafe Knit",
                "is_public": True
            }

        # 6. Shopping Mall / Jalan-jalan Context
        if any(k in t for k in ["mall", "shopping", "belanja", "bioskop", "nonton", "pameran", "jalan-jalan", "hangout"]):
            return {
                "activity": "lagi jalan-jalan di mall",
                "scene": "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting",
                "outfit_prompt": profile["mall_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, exposed chest, towel",
                "outfit_name": "🛍️ Trendy Mall Hangout",
                "is_public": True
            }

        # 7. Gym / Olahraga Context
        if any(k in t for k in ["gym", "workout", "olahraga", "fitness", "yoga", "jogging", "lari"]):
            return {
                "activity": "lagi olahraga / gym",
                "scene": "bright modern gym studio, fitness training equipment background",
                "outfit_prompt": "(wearing athletic sports bra and sleek yoga leggings:1.35), fitness activewear",
                "outfit_negative": "dress, hoodie, skirt, coat, bikini, naked",
                "outfit_name": "🏋️ Sporty Gym Activewear",
                "is_public": True
            }

        # 8. Campus / Kuliah Context (Excludes general 'tugas' to avoid overriding home homework)
        if any(k in t for k in ["kampus", "kuliah", "kelas", "dosen", "makul", "skripsi", "lab", "praktikum"]):
            return {
                "activity": "lagi di kampus kuliah",
                "scene": "sitting at desk in modern university lecture hall, college campus classroom background",
                "outfit_prompt": profile["campus_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, exposed chest, towel",
                "outfit_name": "🎓 Pakaian Kuliah Mahasiswi",
                "is_public": True
            }

        # 9. Library / Perpustakaan Context
        if any(k in t for k in ["perpus", "perpustakaan", "library"]):
            return {
                "activity": "lagi belajar di perpustakaan kampus",
                "scene": "sitting at wooden study desk in quiet university library, bookshelves, open study books, soft lamp",
                "outfit_prompt": profile["campus_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, exposed chest, towel",
                "outfit_name": "📚 Mahasiswi di Perpustakaan",
                "is_public": True
            }

        return None

    # Step A: Check current user_text explicitly FIRST!
    res = match_scenario(user_text)
    if res:
        return res

    # Step B: If user query has no explicit activity, inspect recent chat history (newest first)
    if history_turns:
        for turn in reversed(history_turns[-5:]):
            res = match_scenario(turn)
            if res:
                return res

    # Step C: Fallback to real-world hourly routine schedule
    cur_hour = time.localtime().tm_hour
    routine = get_hourly_routine(cur_hour, persona_key=persona_key)
    return {
        "activity": routine["activity_desc"],
        "scene": routine["scene"],
        "outfit_prompt": routine["outfit_prompt"],
        "outfit_negative": "bikini, lingerie, swimwear" if routine["is_public"] else "",
        "outfit_name": routine["outfit_name"],
        "is_public": routine["is_public"]
    }

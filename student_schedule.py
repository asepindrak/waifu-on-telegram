"""
student_schedule.py - Real-life College Student Routine & Contextual Outfit Engine
Manages college student daily schedules, dynamic conversation activities,
and ensures visual outfits realistically match real-world activities & locations.
"""

import re
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
        "style": "gothic-kawaii playful girlfriend, oversized off-shoulder black hoodie with cat graphics, delicate white camisole with black lace and pink bow, black choker with silver heart ring",
        "campus_outfit": "(wearing cute pastel college outfit, oversized light pastel pink jacket over casual white tee, pleated black skirt, canvas tote bag:1.35)",
        "mall_outfit": "(wearing trendy modern streetwear, stylish cropped black jacket, high-waist pants, small shoulder bag:1.35)",
        "cafe_outfit": "(wearing cozy oversized pastel pink sweater, cute dark denim skirt, stylish black choker:1.35)",
        "pajamas_outfit": "(wearing soft baby pink silk camisole and matching baby pink sleep shorts with black lace trim:1.35), cozy bedtime sleepwear",
        "morning_outfit": "(wearing cozy oversized white morning graphic t-shirt and comfy black loungewear shorts:1.35)",
        "loungewear_outfit": "(wearing cute comfortable casual loungewear, oversized baby pink tee, relaxed black shorts:1.35)",
        "sweater_outfit": "(wearing cute oversized pastel pink knitted sweater, black choker:1.35), cozy comfy style",
        "bikini_outfit": "(wearing fashionable black and pastel pink two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "romantic_outfit": "(wearing alluring romantic black silk slip dress with delicate pink lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
    },
    "akira": {
        "name": "Akira",
        "age": 22,
        "major": "Ilmu Hukum (Semester 7)",
        "campus": "Kampus Fakultas Hukum",
        "hobbies": "baca buku di perpustakaan, ngopi di cafe estetik, magang kantor hukum, diskusi santai",
        "style": "gothic elegance, elaborate black Gothic dress with dark burgundy accents, black lace, choker with ruby gemstone",
        "campus_outfit": "(wearing elegant university student attire, tailored dark charcoal blazer over cream silk blouse, neat pleated dark burgundy skirt:1.35)",
        "mall_outfit": "(wearing fashionable elegant dark crimson cocktail-casual dress, dark black trench coat, sophisticated jewelry:1.35)",
        "cafe_outfit": "(wearing chic fitted dark burgundy turtleneck sweater, stylish plaid midi skirt:1.35)",
        "pajamas_outfit": "(wearing luxurious wine-red silk camisole and matching wine-red sleep shorts with black lace trim:1.35), cozy bedtime sleepwear",
        "morning_outfit": "(wearing cozy oversized dark charcoal morning t-shirt and comfy burgundy loungewear shorts:1.35)",
        "loungewear_outfit": "(wearing elegant comfortable loungewear, dark burgundy silk top, relaxed black shorts:1.35)",
        "sweater_outfit": "(wearing chic fitted dark burgundy knit sweater:1.35), cozy comfy style",
        "bikini_outfit": "(wearing sophisticated deep burgundy and black two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "romantic_outfit": "(wearing alluring romantic wine-red silk slip dress with delicate black lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
    },
    "hina": {
        "name": "Hina",
        "age": 21,
        "major": "Ilmu Komunikasi (Semester 5)",
        "campus": "Kampus FISIP",
        "hobbies": "organisasi kampus, jogging sore di taman, jajan street food/boba, foto-foto cafe",
        "style": "cheerful hangout girlfriend, oversized cream ribbed sweater with yellow accents, headphones around neck, beige pleated skirt",
        "campus_outfit": "(wearing bright college student casual, cozy cream sweater with warm yellow accents, blue denim skirt, canvas backpack:1.35)",
        "mall_outfit": "(wearing fashionable cute sunny streetwear, pastel yellow jacket, white sneakers, cute bag:1.35)",
        "cafe_outfit": "(wearing oversized cozy cream and yellow knit cardigan, aesthetic hair clips, holding iced drink:1.35)",
        "pajamas_outfit": "(wearing soft pastel yellow silk camisole and matching pastel yellow sleep shorts with white lace trim:1.35), cozy bedtime sleepwear",
        "morning_outfit": "(wearing cozy oversized cream morning t-shirt and comfy light yellow loungewear shorts:1.35)",
        "loungewear_outfit": "(wearing cute comfortable casual loungewear, oversized cream tee with yellow accents, relaxed shorts:1.35)",
        "sweater_outfit": "(wearing oversized cozy cream ribbed knit sweater with warm yellow accents:1.35), cozy comfy style",
        "bikini_outfit": "(wearing cheerful sunny pastel yellow and white two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "romantic_outfit": "(wearing alluring romantic cream silk slip dress with delicate light yellow lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
    },
    "shiro": {
        "name": "Shiro",
        "age": 22,
        "major": "Farmasi & Sains (Semester 7)",
        "campus": "Kampus Fakultas Farmasi & Lab Sains",
        "hobbies": "praktikum lab, membaca jurnal di perpustakaan, nonton anime, main game, suasana hening malam hari",
        "style": "kuudere girlfriend, navy cardigan over white collared blouse, royal blue ribbon tie with star crystal brooch, crescent-moon clip",
        "campus_outfit": "(wearing neat college student outfit, crisp collared white blouse, dark navy cardigan, crescent-moon clip, pleated navy skirt:1.35)",
        "mall_outfit": "(wearing understated minimalist modern chic, clean tailored charcoal coat, sleek dark navy trousers:1.35)",
        "cafe_outfit": "(wearing cozy soft grey-blue knit turtleneck, calm serene aesthetic:1.35)",
        "pajamas_outfit": "(wearing soft cool ice-blue silk camisole and matching ice-blue sleep shorts with white trim:1.35), cozy bedtime sleepwear",
        "morning_outfit": "(wearing cozy oversized clean white morning t-shirt and comfy navy loungewear shorts:1.35)",
        "loungewear_outfit": "(wearing calm comfortable loungewear, oversized ice-blue tee, relaxed navy shorts:1.35)",
        "sweater_outfit": "(wearing cozy soft grey-blue knit sweater:1.35), cozy comfy style",
        "bikini_outfit": "(wearing clean dark navy and white two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "romantic_outfit": "(wearing alluring romantic cool ice-blue silk slip dress with delicate white lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
    },
    "yume": {
        "name": "Yume",
        "age": 21,
        "major": "Seni Rupa & Desain (Semester 5)",
        "campus": "Kampus Institut Seni & Desain",
        "hobbies": "melukis di studio/taman, membaca buku, mengagumi bintang malam, mendengarkan musik lo-fi, jalan sore",
        "style": "dreamy girlfriend, cozy lavender cardigan, white pleated camisole dress with lace, silver crescent-moon necklace",
        "campus_outfit": "(wearing artistic college student attire, soft lavender cardigan over simple white sundress, canvas tote bag with art brushes:1.35)",
        "mall_outfit": "(wearing dreamy elegant soft lavender dress, delicate white lace details, small cross-body bag:1.35)",
        "cafe_outfit": "(wearing soft knit lavender sweater, comfortable flowy white skirt, peaceful artistic aura:1.35)",
        "pajamas_outfit": "(wearing soft lavender silk camisole and matching lavender sleep shorts with delicate white lace trim:1.35), cozy bedtime sleepwear",
        "morning_outfit": "(wearing cozy oversized white morning t-shirt and comfy soft lavender loungewear shorts:1.35)",
        "loungewear_outfit": "(wearing dreamy comfortable casual loungewear, oversized soft lavender tee, relaxed white shorts:1.35)",
        "sweater_outfit": "(wearing cozy oversized soft lavender knitted sweater:1.35), cozy comfy style",
        "bikini_outfit": "(wearing dreamy pastel lavender and white two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "romantic_outfit": "(wearing alluring romantic soft lavender silk slip dress with delicate white lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
    },
    "asunayuuki": {
        "name": "Asuna Yuuki",
        "age": 21,
        "major": "Sastra & Bahasa Jepang (Semester 5)",
        "campus": "Kampus Universitas",
        "hobbies": "memasak resep lezat, jalan-jalan santai, nonton film seru, menemani pasangan mengobrol santai",
        "style": "cheerful loving girlfriend, elegant white knit sweater with cherry-red accents, pleated skirt",
        "campus_outfit": "(wearing stylish cream cardigan with red trim over white collared shirt, red pleated skirt, canvas tote bag:1.35)",
        "mall_outfit": "(wearing fashionable chic white and cherry-red streetwear, cropped jacket, high-waist pants:1.35)",
        "cafe_outfit": "(wearing cozy warm cream knit sweater with red accents, cute skirt:1.35)",
        "pajamas_outfit": "(wearing soft cherry-red and white silk camisole and matching sleep shorts:1.35), cozy bedtime sleepwear",
        "morning_outfit": "(wearing cozy oversized white morning t-shirt with red accents and comfy sleep shorts:1.35)",
        "loungewear_outfit": "(wearing cute comfortable casual loungewear, oversized white tee with red accents, relaxed shorts:1.35)",
        "sweater_outfit": "(wearing cozy warm cream knit sweater with cherry-red accents:1.35), cozy comfy style",
        "bikini_outfit": "(wearing vibrant white and cherry-red two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "romantic_outfit": "(wearing alluring romantic crimson and white silk slip dress with delicate lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
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


def get_hourly_routine(hour: int, persona_key: str = "runa", weekday: Optional[int] = None) -> Dict[str, Any]:
    """
    Returns realistic college student activity, setting, and outfit for the given hour (0-23).
    Differentiates between weekdays (Mon-Fri) and weekends/holidays (Sat-Sun) for authentic lore!
    """
    profile = STUDENT_PROFILES.get(persona_key.lower(), STUDENT_PROFILES["runa"])
    major = profile["major"]
    if weekday is None:
        weekday = time.localtime().tm_wday  # 0=Mon, ..., 5=Sat, 6=Sun
    is_weekend = (weekday in (5, 6))

    # --- WEEKEND / HARI LIBUR SCHEDULE (Sabtu & Minggu) ---
    if is_weekend:
        if 6 <= hour < 9:
            return {
                "activity_name": "Bangun pagi santai akhir pekan",
                "activity_desc": "lagi bangun agak siang di kasur kamar kos, menikmati hari libur kuliah sambil main HP santai",
                "scene": "relaxing on bed with fluffy pillows and soft blanket, bright sunny morning bedroom window",
                "outfit_prompt": profile.get("morning_outfit", "(wearing cozy oversized morning t-shirt and comfy loungewear shorts:1.35)"),
                "outfit_name": "☀️ Kaos Pagi Santai",
                "is_public": False,
                "is_weekend": True
            }
        elif 9 <= hour < 12:
            return {
                "activity_name": "Sarapan & bebersih kamar kos",
                "activity_desc": "lagi santai bebersih kamar kos, seduh kopi/matcha pagi, dan sarapan santai menikmati libur",
                "scene": "standing in cozy apartment room, sipping warm morning coffee, natural sunlight through window",
                "outfit_prompt": profile.get("loungewear_outfit", "(wearing cute comfortable casual loungewear, oversized tee, relaxed shorts:1.35)"),
                "outfit_name": "🛋️ Pakaian Santai Kos",
                "is_public": False,
                "is_weekend": True
            }
        elif 12 <= hour < 15:
            return {
                "activity_name": "Nongkrong di kafe estetik / hunting buku",
                "activity_desc": "lagi jalan santai libur akhir pekan, nongkrong di cafe estetik sambil ngopi dan baca buku",
                "scene": "sitting at aesthetic cafe table holding a sweet drink, bright bokeh background",
                "outfit_prompt": profile["cafe_outfit"],
                "outfit_name": "☕ Cozy Weekend Cafe",
                "is_public": True,
                "is_weekend": True
            }
        elif 15 <= hour < 18:
            return {
                "activity_name": "Jalan-jalan di mall / nonton bioskop",
                "activity_desc": "lagi jalan-jalan sore di mall, belanja camilan, atau nonton film bioskop seru",
                "scene": "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting",
                "outfit_prompt": profile["mall_outfit"],
                "outfit_name": "🛍️ Trendy Mall Hangout",
                "is_public": True,
                "is_weekend": True
            }
        elif 18 <= hour < 21:
            return {
                "activity_name": "Makan malam santai & santai di kosan",
                "activity_desc": "udah balik ke kosan sehabis jalan-jalan sore, lagi makan malam santai sambil istirahat",
                "scene": "relaxing inside warm cozy apartment room, warm ambient lamp lighting",
                "outfit_prompt": profile.get("loungewear_outfit", "(wearing cute comfortable casual loungewear, oversized tee, relaxed shorts:1.35)"),
                "outfit_name": "🛋️ Pakaian Santai Kos",
                "is_public": False,
                "is_weekend": True
            }
        elif 21 <= hour < 23:
            return {
                "activity_name": "Santai malam minggu di kamar kos",
                "activity_desc": "lagi santai rebahan di kasur kamar kos, dengerin musik lo-fi dan nonton series favorit",
                "scene": "sitting comfortably on plush bed in cozy bedroom, glowing fairy lights, intimate relaxed evening ambiance",
                "outfit_prompt": profile.get("loungewear_outfit", "(wearing soft comfortable camisole and loungewear shorts:1.35), cozy evening style"),
                "outfit_name": "🌙 Loungewear Malam",
                "is_public": False,
                "is_weekend": True
            }
        else:  # 23:00 - 06:00
            return {
                "activity_name": "Tidur lelap akhir pekan",
                "activity_desc": "udah rebahan di kasur di bawah selimut, skincare-an dan siap-siap tidur nyenyak",
                "scene": "lying comfortably on bed with fluffy pillows and soft blanket, dim cozy night bedroom lamp",
                "outfit_prompt": profile.get("pajamas_outfit", "(wearing soft pastel silk pajamas:1.35), cozy bedtime sleepwear"),
                "outfit_name": "🌙 Piyama Tidur",
                "is_public": False,
                "is_weekend": True
            }

    # --- WEEKDAY / HARI KULIAH SCHEDULE (Senin s/d Jumat) ---
    if 6 <= hour < 8:
        return {
            "activity_name": "Bangun pagi & siap-siap ke kampus",
            "activity_desc": "baru bangun tidur, cuci muka, mandi pagi, dan siap-siap berangkat kuliah pagi",
            "scene": "sitting in cozy bright morning apartment room, soft morning sunlight through window",
            "outfit_prompt": profile.get("morning_outfit", "(wearing cozy oversized morning t-shirt and comfy loungewear shorts:1.35)"),
            "outfit_name": "☀️ Kaos Pagi Santai",
            "is_public": False,
            "is_weekend": False
        }
    elif 8 <= hour < 11:
        return {
            "activity_name": f"Kuliah Pagi ({major})",
            "activity_desc": f"lagi ada jadwal kelas kuliah pagi di kampus ({major}), dengerin dosen dan nyatet materi",
            "scene": "sitting at wooden desk inside modern university lecture hall, student classroom background, bright ambient lighting",
            "outfit_prompt": profile["campus_outfit"],
            "outfit_name": "🎓 Baju Kuliah Kampus",
            "is_public": True,
            "is_weekend": False
        }
    elif 11 <= hour < 13:
        return {
            "activity_name": "Makan siang di kantin / cafe kampus",
            "activity_desc": "lagi istirahat makan siang bareng temen di kantin kampus / cafe deket kampus",
            "scene": "sitting at aesthetic university campus cafe table, holding lunch drink, sunny vibrant ambient bokeh",
            "outfit_prompt": profile["campus_outfit"],
            "outfit_name": "🎓 Baju Kuliah Kampus",
            "is_public": True,
            "is_weekend": False
        }
    elif 13 <= hour < 16:
        return {
            "activity_name": f"Praktikum / Nugas di Perpustakaan ({major})",
            "activity_desc": f"lagi di perpustakaan kampus ngerjain tugas kelompok & materi {major}",
            "scene": "sitting at wooden study desk in quiet university library, open textbooks, bookshelf background, warm study lamp",
            "outfit_prompt": profile["campus_outfit"],
            "outfit_name": "📚 Baju Belajar Kampus",
            "is_public": True,
            "is_weekend": False
        }
    elif 16 <= hour < 19:
        return {
            "activity_name": "Selesai kuliah, jalan ke mall / nongkrong di cafe",
            "activity_desc": "baru beres kuliah, lagi jalan-jalan santai ke mall / nongkrong di cafe ngobrol dan belanja",
            "scene": "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting",
            "outfit_prompt": profile["mall_outfit"],
            "outfit_name": "🛍️ Streetwear Mall",
            "is_public": True,
            "is_weekend": False
        }
    elif 19 <= hour < 21:
        return {
            "activity_name": "Balik ke kosan & makan malam santai",
            "activity_desc": "udah balik ke kosan, lagi makan malam santai sambil istirahat",
            "scene": "relaxing inside warm cozy apartment room, warm ambient lamp lighting",
            "outfit_prompt": profile.get("loungewear_outfit", "(wearing cute comfortable casual loungewear, oversized tee, relaxed shorts:1.35)"),
            "outfit_name": "🛋️ Pakaian Santai Kos",
            "is_public": False,
            "is_weekend": False
        }
    elif 21 <= hour < 23:
        return {
            "activity_name": "Mandi malam & santai di kamar kos",
            "activity_desc": "baru beres mandi malam, lagi santai rebahan di kasur sambil dengerin musik / main game",
            "scene": "sitting comfortably on plush bed in cozy bedroom, glowing fairy lights, intimate relaxed evening ambiance",
            "outfit_prompt": profile.get("loungewear_outfit", "(wearing soft comfortable camisole and loungewear shorts:1.35), cozy evening style"),
            "outfit_name": "🌙 Loungewear Malam",
            "is_public": False,
            "is_weekend": False
        }
    else:  # 23:00 - 06:00
        return {
            "activity_name": "Rebahan di kasur siap-siap tidur",
            "activity_desc": "udah rebahan di kasur di bawah selimut, skincare-an dan siap-siap tidur nyenyak",
            "scene": "lying comfortably on bed with fluffy pillows and soft blanket, dim cozy night bedroom lamp",
            "outfit_prompt": profile.get("pajamas_outfit", "(wearing soft pastel silk pajamas:1.35), cozy bedtime sleepwear"),
            "outfit_name": "🌙 Piyama Tidur",
            "is_public": False,
            "is_weekend": False
        }


def detect_contextual_activity_and_outfit(
    user_text: str,
    history_turns: Optional[List[str]] = None,
    persona_key: str = "runa",
    weekday: Optional[int] = None
) -> Dict[str, Any]:
    """
    Intelligently analyzes the user's explicit request and ongoing conversation to determine:
    1. What the waifu is currently doing (activity).
    2. Where she is located (scene).
    3. What she should be wearing (outfit), strictly preventing lingerie/nude in public!
    """
    profile = STUDENT_PROFILES.get(persona_key.lower(), STUDENT_PROFILES["runa"])

    def match_scenario(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        t = text.lower()

        def _has_kw(keywords: List[str]) -> bool:
            pat = r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b"
            return bool(re.search(pat, t, re.IGNORECASE))

        # 0. Romantic / Intimate Bedroom Context (Highest Priority for explicit PAP requests)
        if _has_kw(["sensual", "romantic", "romantis", "intimate", "mesra", "bedroom setting", "loving gaze"]):
            return {
                "activity": "lagi santai romantis di kamar",
                "scene": "romantic intimate bedroom setting, soft dim lighting, gentle blush, affectionate loving gaze towards viewer",
                "outfit_prompt": profile.get("romantic_outfit", "(wearing alluring romantic silk slip dress with delicate lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling"),
                "outfit_negative": "campus, backpack, casual college clothes, classroom, hoodie, outdoor clothes, jeans, winter clothes",
                "outfit_name": "💋 Pakaian Romantis (Silk Slip Dress)",
                "is_public": False
            }

        # 1. Shower / Mandi Context
        if _has_kw(["mandi", "keramas", "handuk", "kamar mandi", "shower", "bath", "bathroom", "steam"]):
            return {
                "activity": "baru beres mandi / keramas",
                "scene": "standing in modern bathroom with soft steam, bare shoulders, post-shower glow, damp hair, bathroom mirror",
                "outfit_prompt": "(wearing only a soft clean white bath towel wrapped around chest:1.4), bare shoulders, wet skin, damp hair",
                "outfit_negative": "clothes, shirt, pants, coat, hoodie, jeans, jacket, sweater",
                "outfit_name": "🚿 Handuk Mandi (After Shower)",
                "is_public": False
            }

        # 2. Sleep / Bed / Kamar Context
        if _has_kw(["tidur", "rebahan", "kasur", "piyama", "pajamas", "ngantuk", "mimpi", "kamar", "bantal"]):
            return {
                "activity": "lagi rebahan di kasur kamar",
                "scene": "relaxing on bed with fluffy pillows, warm dim night bedroom lamp, cozy intimate bedroom",
                "outfit_prompt": profile.get("pajamas_outfit", "(wearing soft pastel silk camisole and sleep shorts:1.35), bedtime loungewear"),
                "outfit_negative": "hoodie, jacket, coat, outdoor clothes, jeans, campus",
                "outfit_name": "🌙 Silk Pajamas",
                "is_public": False
            }

        # 2b. Street Food / Night Market / Culinary Hangout Context (BEFORE Kitchen & Campus!)
        if _has_kw(["street food", "jajanan", "jajan", "kaki lima", "pinggir jalan", "angkringan", "warung", "kuliner", "festival makanan", "food stall", "bazaar", "food court", "pasar malam"]):
            return {
                "activity": "lagi jajan street food & kulineran santai",
                "scene": "standing outdoors by lively street food stalls, warm evening street lights, holding paper bag of warm snacks, festive outdoor culinary atmosphere",
                "outfit_prompt": profile["mall_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, exposed chest, towel, pajama, apron",
                "outfit_name": "🍡 Streetwear Santai Outdoor",
                "is_public": True
            }

        # 3. Kitchen / Masak Context (Explicit cooking/kitchen only, not generic eating out)
        if _has_kw(["dapur", "masak", "memasak", "masakin", "baking", "cooking", "kitchen", "kompor", "nyiapin makan"]):
            return {
                "activity": "lagi masak di dapur",
                "scene": "standing in modern cozy kitchen preparing food, warm domestic lighting",
                "outfit_prompt": profile.get("sweater_outfit", "(wearing cute oversized pastel knitted sweater:1.35), cozy comfy style"),
                "outfit_negative": "bikini, lingerie, swimwear, naked",
                "outfit_name": "🍳 Cozy Kitchen Sweater",
                "is_public": False
            }

        # 4. Beach / Pool / Renang Context
        if _has_kw(["pantai", "beach", "laut", "kolam", "renang", "swimming"]):
            return {
                "activity": "lagi di pantai / kolam renang",
                "scene": "walking along tropical beach, ocean sunset horizon, gentle sea breeze",
                "outfit_prompt": profile.get("bikini_outfit", "(wearing fashionable two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel"),
                "outfit_negative": "clothes, casual clothes, hoodie, sweater, jacket, shirt, pants, coat, pajamas",
                "outfit_name": "🏖️ Summer Bikini",
                "is_public": True
            }

        # 5. Cafe / Nongkrong / Kopi Context
        if _has_kw(["cafe", "kafe", "kopi", "coffee", "boba", "matcha", "nongkrong", "starbucks"]):
            return {
                "activity": "lagi nongkrong santai di cafe",
                "scene": "sitting at aesthetic cafe table holding a warm beverage, beautiful bokeh background",
                "outfit_prompt": profile["cafe_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, towel",
                "outfit_name": "☕ Cozy Cafe Knit",
                "is_public": True
            }

        # 6. Shopping Mall / Jalan-jalan Context
        if _has_kw(["mall", "shopping", "belanja", "bioskop", "nonton", "pameran", "jalan-jalan", "hangout"]):
            return {
                "activity": "lagi jalan-jalan di mall",
                "scene": "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting",
                "outfit_prompt": profile["mall_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, exposed chest, towel",
                "outfit_name": "🛍️ Trendy Mall Hangout",
                "is_public": True
            }

        # 7. Gym / Olahraga Context
        if _has_kw(["gym", "workout", "olahraga", "fitness", "yoga", "jogging", "lari"]):
            return {
                "activity": "lagi olahraga / gym",
                "scene": "bright modern gym studio, fitness training equipment background",
                "outfit_prompt": "(wearing athletic sports bra and sleek yoga leggings:1.35), fitness activewear",
                "outfit_negative": "dress, hoodie, skirt, coat, bikini, naked",
                "outfit_name": "🏋️ Sporty Gym Activewear",
                "is_public": True
            }

        # 8. Campus / Kuliah Context (Excludes general 'tugas' to avoid overriding home homework)
        if _has_kw(["kampus", "kuliah", "kelas", "dosen", "makul", "skripsi", "lab", "praktikum"]):
            return {
                "activity": "lagi di kampus kuliah",
                "scene": "sitting at desk in modern university lecture hall, college campus classroom background",
                "outfit_prompt": profile["campus_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, exposed chest, towel",
                "outfit_name": "🎓 Pakaian Kuliah Mahasiswi",
                "is_public": True
            }

        # 9. Library / Perpustakaan Context
        if _has_kw(["perpus", "perpustakaan", "library"]):
            return {
                "activity": "lagi belajar di perpustakaan kampus",
                "scene": "sitting at wooden study desk in quiet university library, bookshelves, open study books, soft lamp",
                "outfit_prompt": profile["campus_outfit"],
                "outfit_negative": "bikini, lingerie, swimwear, naked, exposed chest, towel",
                "outfit_name": "📚 Mahasiswi di Perpustakaan",
                "is_public": True
            }

        # 10. Home / Relaxing / Kos Context
        if _has_kw(["rumah", "kosan", "kost", "kos", "apartemen", "santai di rumah", "pulang ke rumah"]):
            return {
                "activity": "lagi santai di rumah / kamar kos",
                "scene": "relaxing comfortably in cozy modern apartment room, warm ambient lighting",
                "outfit_prompt": profile.get("loungewear_outfit", "(wearing cute comfortable casual loungewear, oversized tee, relaxed shorts:1.35)"),
                "outfit_negative": "bikini, lingerie, swimwear, naked, uniform, coat",
                "outfit_name": "🛋️ Pakaian Santai Rumahan",
                "is_public": False
            }

        return None

    # Step A: Check current user_text explicitly FIRST!
    res = match_scenario(user_text)
    if res:
        res["is_explicit"] = True
        return res

    # Step B: If user query has no explicit activity, inspect recent chat history (newest first)
    if history_turns:
        for turn in reversed(history_turns[-5:]):
            res = match_scenario(turn)
            if res:
                res["is_explicit"] = True
                return res

    # Step C: Fallback to real-world hourly routine schedule
    cur_hour = time.localtime().tm_hour
    routine = get_hourly_routine(cur_hour, persona_key=persona_key, weekday=weekday)
    return {
        "activity": routine["activity_desc"],
        "scene": routine["scene"],
        "outfit_prompt": routine["outfit_prompt"],
        "outfit_negative": "bikini, lingerie, swimwear" if routine["is_public"] else "",
        "outfit_name": routine["outfit_name"],
        "is_public": routine["is_public"],
        "is_explicit": False
    }

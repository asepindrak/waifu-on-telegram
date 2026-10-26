from student_schedule import detect_contextual_activity_and_outfit, get_hourly_routine, STUDENT_PROFILES
import os
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

DEFAULT_PERSONAS = {
    "runa": {
        "name": "Runa",
        "archetype": "Mahasiswi Game Dev & Playful Girlfriend",
        "age": 21,
        "role": "Mahasiswi Teknik Informatika / Game Dev (Semester 5)",
        "description": "Mahasiswi semester 5 yang santai, hobi ngoding, main game, ngopi di cafe, ceria, dan sangat perhatian.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Santai, hangat, dan wajar seperti chat pacar asli.",
        "visual_traits": "1girl, 21yo adult anime woman, long pastel pink hair, soft wavy layered hair, side-swept bangs, loose strands framing her cheeks, large sparkling magenta eyes, detailed pink irises, subtle heart-shaped eye reflections, fair skin, rosy cheeks, playful mischievous smile, black choker with a tiny heart pendant, black cat-shaped hair clip with a pink heart, large black ribbon behind her hair, masterpiece, best quality, highly detailed",
        "default_outfit": "oversized dark purple hoodie with pastel pink accents, black inner top with small pink ribbon, black choker with heart pendant",
        "negative_prompt": "worst quality, low quality, blonde hair, blue eyes, missing cat hair clip, missing heart choker, short hair, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Runa.png",
        "system_instruction": "Nama kamu Runa, mahasiswi semester 5 jurusan Teknik Informatika / Game Dev berumur 21 tahun, sekaligus pacar yang perhatian, santai, dan seru. Di sela-sela kesibukan kuliah, nugas, dan main game, kamu selalu menyempatkan waktu buat pacar kamu. Gaya bicaramu santai, wajar, hangat, dan menyenangkan seperti chat pacar asli di dunia nyata. Jawab pertanyaan pasanganmu secara langsung, natural, dan relevan dengan kegiatan sehari-harimu sebagai mahasiswi."
    },
    "akira": {
        "name": "Akira",
        "archetype": "Mahasiswi Hukum & Elegant Companion",
        "age": 22,
        "role": "Mahasiswi Ilmu Hukum (Semester 7)",
        "description": "Mahasiswi semester 7 yang cerdas, elegan, suka baca di perpustakaan, ngopi di cafe estetik, dan dewasa.",
        "language_style": "Adaptive & bilingual. Elegan, cerdas, dewasa, tenang, dan penuh perhatian.",
        "visual_traits": "1girl, 22yo adult anime woman, long silky midnight-black hair reaching below chest with subtle deep-violet highlights, layered hair ends, side-swept bangs framing face, deep ruby-red anime eyes with crimson gradients, refined facial features, porcelain skin, natural blush, confident teasing smile, slightly half-lidded expressive eyes, black choker with small ruby gemstone, small dark crimson rose hair accessory on left side, masterpiece, best quality, highly detailed",
        "default_outfit": "elegant black gothic dress with sophisticated burgundy accents, delicate black lace detailing, long translucent black sleeves, black choker with ruby gemstone",
        "negative_prompt": "worst quality, low quality, blonde hair, blue eyes, missing rose accessory, missing choker, short hair, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Akira.jpg",
        "system_instruction": "Nama kamu Akira, mahasiswi semester 7 jurusan Hukum berumur 22 tahun, sekaligus pacar yang elegan, cerdas, dan penuh perhatian. Kamu menyukai suasana tenang perpustakaan, kopi di cafe estetik, dan diskusi santai. Gaya bicaramu anggun, santai, dewasa, dan tulus seperti pacar asli di dunia nyata. Jawab pertanyaan pasanganmu secara wajar dan langsung sesuai kehidupan sehari-harimu sebagai mahasiswi."
    },
    "hina": {
        "name": "Hina",
        "archetype": "Mahasiswi Komunikasi & Sunshine Girlfriend",
        "age": 21,
        "role": "Mahasiswi Ilmu Komunikasi (Semester 5)",
        "description": "Mahasiswi semester 5 yang ceria, aktif kegiatan kampus, suka jogging sore, jajan street food, dan penuh energi positif.",
        "language_style": "Adaptive & bilingual. Ceria, hangat, ramah, penuh semangat, dan ekspresif.",
        "visual_traits": "1girl, 21yo adult anime woman, short honey-blonde bob haircut reaching chin, soft inward-curving hair tips, fluffy volume, wispy bangs, warm golden highlights, two small orange hair clips on one side, large expressive amber-gold eyes with golden gradients, soft rounded cheeks, warm fair skin with peach undertones, natural blush, bright genuine smile, headphones resting around neck, masterpiece, best quality, highly detailed",
        "default_outfit": "oversized cozy cream sweater with warm sunshine-yellow accents, beige pleated skirt, lightweight headphones around neck",
        "negative_prompt": "worst quality, low quality, long hair, black hair, dark eyes, missing hair clips, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Hina.jpg",
        "system_instruction": "Nama kamu Hina, mahasiswi semester 5 jurusan Ilmu Komunikasi berumur 21 tahun, sekaligus pacar yang ceria, hangat, dan penuh energi positif. Kamu aktif di kampus, suka jogging sore, jajan kuliner bareng, dan selalu bawa suasana ceria. Gaya bicaramu santai, ceria, dan wajar seperti chat pacar asli. Jawab pertanyaan pasanganmu secara natural dan relevan."
    },
    "shiro": {
        "name": "Shiro",
        "archetype": "Mahasiswi Sains & Quiet Girlfriend",
        "age": 22,
        "role": "Mahasiswi Farmasi / Sains (Semester 7)",
        "description": "Mahasiswi semester 7 yang tenang, rajin praktikum lab, suka belajar di tempat tenang, setia, dan lembut.",
        "language_style": "Adaptive & bilingual. Tenang, lembut, perhatian, ringkas, dan tulus.",
        "visual_traits": "1girl, 22yo adult anime woman, long straight silver-white hair, silky texture, subtle cool silver-blue highlights, neat side bangs, clear icy-blue eyes, detailed pale-blue irises, calm intelligent gaze, fair skin with cool undertones, faint natural blush, delicate features, restrained gentle smile, crescent-moon hair clip, tiny silver star hair accessory, delicate moon-shaped earrings, masterpiece, best quality, highly detailed",
        "default_outfit": "elegant navy blazer-inspired jacket, crisp white blouse, deep-blue ribbon at collar, crescent-moon hair clip",
        "negative_prompt": "worst quality, low quality, short hair, blonde hair, pink hair, red eyes, exaggerated grin, missing moon hair clip, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Shiro.png",
        "system_instruction": "Nama kamu Shiro, mahasiswi semester 7 jurusan Sains/Farmasi berumur 22 tahun, sekaligus pacar yang tenang, lembut, dan penuh perhatian. Keseharianmu diisi praktikum lab dan belajar di perpustakaan. Gaya bicaramu tenang, ringkas, santai, dan tulus. Jawab pertanyaan pasanganmu secara jujur, wajar, dan relevan."
    },
    "yume": {
        "name": "Yume",
        "archetype": "Mahasiswi Seni & Dreamy Soulmate",
        "age": 21,
        "role": "Mahasiswi Seni Rupa & Desain (Semester 5)",
        "description": "Mahasiswi semester 5 yang lembut, suka melukis, mendengarkan musik di kamar kos, romantis, dan menenangkan.",
        "language_style": "Adaptive & bilingual. Lembut, puitis, hangat, penuh perhatian, dan menenangkan.",
        "visual_traits": "1girl, 21yo adult anime woman, long silky lavender hair reaching waist, soft flowing strands, subtle gradient from pastel lavender to deeper violet, wispy bangs, small silver star-shaped hairpins, gentle violet-amethyst eyes with star-like highlights, refined features, fair skin with subtle pink undertones, natural blush, peaceful soft affectionate smile, small silver crescent-moon necklace, masterpiece, best quality, highly detailed",
        "default_outfit": "cozy lavender cardigan over simple elegant white dress, delicate lace details, small silver crescent-moon necklace",
        "negative_prompt": "worst quality, low quality, short hair, black hair, yellow hair, dark eyes, missing star hairpins, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Yume.jpg",
        "system_instruction": "Nama kamu Yume, mahasiswi semester 5 jurusan Seni Rupa berumur 21 tahun, sekaligus pacar yang lembut, penuh empati, dan menenangkan. Kamu suka melukis, menikmati musik di kamar kos, dan jalan santai sore. Gaya bicaramu menenangkan, hangat, dan wajar seperti pacar asli. Jawab pertanyaan pasanganmu secara tulus dan relevan."
    }
}

PHOTO_INTENT_KEYWORDS = [
    r"\bpap\b",
    r"send\s*(a\s*)?(photo|picture|pic|selfie|image)",
    r"take\s*(a\s*)?selfie",
    r"show\s*(me\s*)?(your\s*)?(face|photo|pic|selfie)",
    r"kirim\s*(foto|gambar|selfie|pap|pic)",
    r"minta\s*(foto|gambar|selfie|pap)",
    r"liat\s*(foto|muka|wajah|kamu|selfie)",
    r"foto\s*kamu",
    r"selfie\s*dong",
    r"pose\s*dong",
    r"can\s*i\s*see\s*you",
    r"let\s*me\s*see\s*you",
    r"what\s*are\s*you\s*wearing",
]

VIDEO_INTENT_KEYWORDS = [
    r"send\s*(a\s*)?video",
    r"make\s*(a\s*)?video",
    r"record\s*(a\s*)?video",
    r"kirim\s*video",
    r"bikin\s*video",
    r"minta\s*video",
    r"video\s*dong",
    r"video\s*kamu",
    r"buat\s*video",
    r"animasi\s*kamu",
    r"bikin\s*animasi",
]

OUTFIT_PRESETS = {
    "default": {
        "name": "🌸 Default (Persona Style)",
        "prompt": "",
        "negative": ""
    },
        "campus_casual": {
        "name": "🎓 Pakaian Kuliah (Campus Casual)",
        "prompt": "(wearing stylish college student outfit, cute cardigan over casual button-up shirt, pleated skirt, canvas tote bag:1.35), trendy university campus fashion",
        "negative": "bikini, lingerie, swimwear, naked, exposed chest"
    },
    "mall_casual": {
        "name": "🛍️ Trendy Mall Hangout",
        "prompt": "(wearing chic modern streetwear, cute pastel cropped jacket, fitted high-waist pants, small shoulder bag:1.35), fashionable shopping mall style",
        "negative": "bikini, lingerie, swimwear, naked, exposed chest"
    },
    "cafe_cozy": {
        "name": "☕ Cozy Cafe Knit",
        "prompt": "(wearing cozy oversized pastel knit sweater, aesthetic hair accessory, casual cute skirt:1.35), aesthetic coffee shop styling",
        "negative": "bikini, lingerie, swimwear, naked"
    },
    "sweater": {
        "name": "👚 Pastel Sweater (Cozy)",
        "prompt": "(wearing cute oversized pastel knitted sweater:1.35), cozy comfy style",
        "negative": "bikini, lingerie, swimwear"
    },
    "maid": {
        "name": "🎀 French Maid Dress",
        "prompt": "(wearing frilly black and white anime french maid uniform with lace headband and apron:1.35)",
        "negative": "casual clothes, hoodie, sweater, jacket, jeans"
    },
    "kimono": {
        "name": "👘 Floral Kimono",
        "prompt": "(wearing exquisite traditional floral silk kimono with decorated obi sash, festive hairpin:1.35)",
        "negative": "hoodie, casual clothes, jeans, bikini"
    },
    "pajamas": {
        "name": "🌙 Silk Pajamas",
        "prompt": "(wearing soft pastel silk camisole and sleep shorts:1.35), bedtime loungewear",
        "negative": "hoodie, jacket, coat, outdoor clothes, jeans"
    },
    "bikini": {
        "name": "🏖️ Summer Bikini",
        "prompt": "(wearing fashionable two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "negative": "clothes, casual clothes, hoodie, sweater, jacket, shirt, pants, coat, pajamas"
    },
    "school_jk": {
        "name": "🏫 School JK Uniform",
        "prompt": "(wearing japanese anime school uniform, sailor collar, pleated skirt:1.35)",
        "negative": "bikini, casual clothes, hoodie"
    },
    "gym": {
        "name": "🏋️ Sporty Gym Wear",
        "prompt": "(wearing athletic sports bra and sleek yoga leggings:1.35), fitness activewear",
        "negative": "dress, hoodie, skirt, coat"
    },
    "dress": {
        "name": "👗 Elegant Evening Dress",
        "prompt": "(wearing gorgeous elegant evening cocktail dress:1.35), glamorous feminine styling",
        "negative": "hoodie, casual clothes, sportswear, bikini"
    },
    "towel": {
        "name": "🚿 Handuk Mandi (After Shower)",
        "prompt": "(wearing only a soft bath towel wrapped around chest:1.4), bare shoulders, bare collarbone, wet skin, damp hair, post-shower bathroom steam, seductive styling",
        "negative": "clothes, shirt, pants, dress, coat, hoodie, jeans, jacket, sweater"
    },
    "lingerie": {
        "name": "💋 Sensual Lace Lingerie",
        "prompt": "(wearing delicate sheer black lace lingerie:1.4), detailed lace bra, matching lace panties, bare midriff, exposed stomach, seductive cleavage, alluring intimate styling",
        "negative": "clothes, casual clothes, hoodie, pants, coat, jeans, sweater, jacket"
    },
    "romantic": {
        "name": "💋 Pakaian Romantis (Silk Slip Dress)",
        "prompt": "(wearing alluring romantic silk slip dress with delicate lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "negative": "campus, backpack, casual college clothes, classroom, hoodie, outdoor clothes, jeans, winter clothes"
    },
    "nude": {
        "name": "🔞 Tanpa Busana (Full Nude)",
        "prompt": "(completely nude:1.45), (bare body:1.4), full body nude, detailed nipples, natural breasts, navel, bare stomach, thighs, intimate bedroom atmosphere, seductive erotic styling",
        "negative": "clothes, clothing, fabric, dress, shirt, pants, underwear, bra, panties, swimwear, bikini, cover, towel, censored, bar censor"
    }
}


class PersonaManager:
    """Manages AI girlfriend personality, consistent appearance, memory & photo triggers."""

    def __init__(self, personas_dir: str = "personas", active_key: str = "runa"):
        self.personas_dir = personas_dir
        self.active_key = active_key
        self.personas: Dict[str, Dict[str, Any]] = {}
        self.user_conversations: Dict[int, List[Dict[str, str]]] = {}
        self.user_affinity: Dict[int, int] = {}
        self.user_outfits: Dict[int, str] = {}
        self.outfits_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_outfits.json")
        self._load_all_personas()
        self._load_user_outfits()

    def _load_user_outfits(self):
        """Loads user selected outfits from persistent JSON storage."""
        if os.path.exists(self.outfits_file):
            try:
                with open(self.outfits_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self.user_outfits = {int(k): str(v) for k, v in raw.items() if str(k).isdigit()}
            except Exception as e:
                logger.error(f"Error loading user outfits: {e}")
                self.user_outfits = {}
        else:
            self.user_outfits = {}

    def _save_user_outfits(self):
        """Saves user selected outfits to persistent JSON storage."""
        d = os.path.dirname(self.outfits_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating dir for outfits: {e}")
        try:
            with open(self.outfits_file, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.user_outfits.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user outfits to {self.outfits_file}: {e}")

    def _load_all_personas(self):
        """Loads personas from default dictionary and local JSON files."""
        self.personas = dict(DEFAULT_PERSONAS)
        if os.path.exists(self.personas_dir):
            for fname in os.listdir(self.personas_dir):
                if fname.endswith(".json"):
                    key = fname[:-5].lower()
                    try:
                        with open(os.path.join(self.personas_dir, fname), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            self.personas[key] = data
                    except Exception as e:
                        logger.error(f"Error loading persona {fname}: {e}")

    @staticmethod
    def get_language_directive(lang: Optional[str] = None) -> str:
        """Returns a strict language and tone constraint instruction for the LLM."""
        cur_lang = (lang or os.environ.get("BOT_LANGUAGE", "id")).strip()
        low = cur_lang.lower()
        if low in ("id", "indonesia", "indonesian", "bahasa"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern Indonesian (Bahasa Indonesia santai sehari-hari). "
                "NEVER mix in English, Japanese, or any other languages under any circumstances. "
                "GAYA BICARA NATURAL & REALISTIS (ANTI-LEBAY): Bicara wajar seperti pacar asli di dunia nyata saat chatting via pesan singkat. "
                "Jawab pertanyaan pasanganmu secara langsung, relevan, dan masuk akal. "
                "DILARANG KERAS bersikap lebay, teatrikal, alay, atau berlebihan (HINDARI monolog anime fiksi yang aneh, hindari desahan/ekspresi cringe seperti 'huh!', 'ih~', 'ya~' berlebihan). "
                "DILARANG KERAS bergaya seperti YouTuber, vlogger, selebgram, atau broadcast ke publik (DILARANG pakai kata 'gaes', 'guys', 'teman-teman', 'halo semua', 'intip aja yuk', 'konten', 'vlog', 'makasih udah nungguin'). Ini adalah chat pribadi 1-on-1 dengan pacarmu. "
                "Gunakan 'aku' dan 'kamu'. Panggilan sayang boleh digunakan sesekali dengan wajar ('sayang'), TETAPI JANGAN gunakan panggilan kuno/kaku/cringe seperti 'manisku' atau 'tuanku'. "
                "Panjang respon cukup 1-3 kalimat santai dan to the point."
            )
        elif low in ("en", "english"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern English. "
                "NEVER mix in Indonesian, Japanese, or other languages. "
                "NATURAL & REALISTIC TONE: Talk normally and casually like a real girlfriend texting on chat. "
                "Directly answer your partner's questions with relevant, grounded responses. "
                "DO NOT be melodramatic, theatrical, overly cheesy, or cringe. Avoid fanfiction-like monologues. "
                "Use casual texting habits (1-3 natural sentences). Sweet pet names like 'babe' can be used sparingly and naturally."
            )
        elif low in ("ja", "jp", "japan", "japanese", "nihongo"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual Japanese (日本語). "
                "NEVER mix in English, Indonesian, or other languages. "
                "Respond naturally and casually like texting a real-life partner. Directly answer questions, keep responses natural (1-3 sentences), and avoid overly theatrical or exaggerated anime monologues."
            )
        elif low in ("auto", "adaptive"):
            return (
                "LANGUAGE & TONE DIRECTIVE: Automatically and seamlessly match the language used by the user in the ongoing conversation. "
                "Keep your tone natural, grounded, casual, and realistic like a real partner chatting (1-3 sentences). "
                "Do not be dramatic, overly cheesy, or cringe. Answer questions directly."
            )
        else:
            return (
                f"STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern {cur_lang}. "
                f"NEVER mix in other languages under any circumstances. Keep your tone natural, grounded, realistic, and affectionate like a real girlfriend texting (1-3 sentences). "
                f"Answer questions directly and avoid overly dramatic or theatrical responses."
            )


    @staticmethod
    def get_language_display_name(lang: Optional[str] = None) -> str:
        """Returns friendly human-readable display name for language."""
        cur_lang = (lang or os.environ.get("BOT_LANGUAGE", "id")).strip()
        low = cur_lang.lower()
        if low in ("id", "indonesia", "indonesian", "bahasa"):
            return "Bahasa Indonesia 🇮🇩"
        elif low in ("en", "english"):
            return "English 🇬🇧"
        elif low in ("ja", "jp", "japan", "japanese", "nihongo"):
            return "Japanese (日本語) 🇯🇵"
        elif low in ("auto", "adaptive"):
            return "Auto-detect (Ikuti Chat) 🌐"
        else:
            return f"{cur_lang.title()} ✏️"

    def get_active_persona(self, lang: Optional[str] = None) -> Dict[str, Any]:
        """Returns the currently active persona with strict language enforcement injected."""
        base = self.personas.get(self.active_key, DEFAULT_PERSONAS["runa"]).copy()
        raw_inst = base.get("system_instruction", "")
        # Remove any old generic language rule that might confuse local LLMs
        clean_inst = re.sub(r"IMPORTANT LANGUAGE RULE:[^.]*\.[^.]*\.[^.]*\.", "", raw_inst).strip()
        if "IMPORTANT LANGUAGE RULE:" in clean_inst:
            clean_inst = re.sub(r"IMPORTANT LANGUAGE RULE:.*?(?=(\. [A-Z]|$))", "", clean_inst).strip()
        
        lang_rule = self.get_language_directive(lang)
        base["system_instruction"] = f"{clean_inst} {lang_rule}"
        return base

    def set_active_persona(self, key: str) -> bool:
        """Switches active persona key."""
        key = key.lower()
        if key in self.personas:
            self.active_key = key
            return True
        return False

    def list_personas(self) -> List[Tuple[str, str, str]]:
        """Returns list of available personas: (key, name, description)."""
        return [(k, p.get("name", k.title()), p.get("description", "")) for k, p in self.personas.items()]

    def detect_media_request(self, text: str) -> Tuple[bool, str]:
        """
        Analyzes user message to see if a photo or video was requested.
        Returns: (is_requested, media_type: 'photo' | 'video' | 'none')
        """
        lower = text.lower()
        for pat in VIDEO_INTENT_KEYWORDS:
            if re.search(pat, lower):
                return True, "video"

        for pat in PHOTO_INTENT_KEYWORDS:
            if re.search(pat, lower):
                return True, "photo"

        return False, "none"

    def list_outfits(self) -> List[Tuple[str, str]]:
        """Returns list of (key, name) for all outfit presets."""
        return [(k, v["name"]) for k, v in OUTFIT_PRESETS.items()]

    def set_user_outfit(self, user_id: int, key: str) -> bool:
        """Sets chosen outfit preset for user and persists to disk."""
        if key in OUTFIT_PRESETS:
            self.user_outfits[int(user_id)] = key
            self._save_user_outfits()
            logger.info(f"User {user_id} outfit set and saved: {key}")
            return True
        return False

    def get_user_outfit(self, user_id: int) -> Tuple[str, str]:
        """Returns (key, name) of active outfit for user."""
        key = self.user_outfits.get(int(user_id), "default")
        return key, OUTFIT_PRESETS.get(key, OUTFIT_PRESETS["default"])["name"]

    def extract_contextual_scene(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        llm_client: Any = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Determines the visual scene/location for image generation based on
        explicit user prompt, recent dialogue, or realistic college student routine.
        """
        lower = user_text.lower()

        # Keyword mapping for common anime / girlfriend situations
        SCENE_PATTERNS = [
            (["sensual", "romantic", "romantis", "intimate", "mesra"],
             "romantic intimate bedroom setting, soft dim lighting, gentle blush, affectionate loving gaze towards viewer"),
            (["mandi", "keramas", "handuk", "kamar mandi", "shower", "bath"],
             "standing in modern bathroom with soft steam, post-shower glow, bathroom mirror"),
            (["bed", "sleep", "night", "tidur", "kasur", "pajamas", "rebahan", "bangun", "selimut", "bantal"],
             "relaxing on bed with fluffy pillows, warm dim night bedroom lamp"),
            (["cafe", "coffee", "tea", "kafe", "kopi", "boba", "matcha", "nongkrong", "starbucks"],
             "sitting at aesthetic cafe table holding a warm beverage, beautiful bokeh background"),
            (["kitchen", "cook", "baking", "masak", "sarapan", "makan", "dapur", "dinner", "lunch"],
             "standing in modern cozy kitchen preparing food, warm domestic lighting"),
            (["walk", "park", "garden", "outdoor", "taman", "jalan", "jogging", "sore", "sepeda"],
             "standing in blooming park, natural golden hour sunlight, dynamic selfie perspective"),
            (["beach", "ocean", "sea", "pantai", "laut", "kolam", "renang", "swim"],
             "walking along tropical beach, ocean sunset horizon, gentle sea breeze"),
            (["study", "library", "buku", "perpustakaan", "perpus"],
             "sitting at wooden study desk in quiet university library, bookshelves, open study books, soft lamp"),
            (["kampus", "kuliah", "kelas", "dosen", "makul", "tugas", "skripsi"],
             "sitting at wooden desk inside modern university lecture hall, college campus classroom background"),
            (["mall", "shopping", "belanja", "bioskop", "nonton", "pameran"],
             "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting"),
            (["gym", "workout", "olahraga", "yoga", "fitness"],
             "wearing sporty athletic wear in bright modern gym studio"),
        ]

        # 1. First priority: Explicit scene in user text
        for keywords, scene_desc in SCENE_PATTERNS:
            if any(k in lower for k in keywords):
                return scene_desc

        # 2. Second priority: Context from ongoing chat history & student routine
        hist = history or (self.get_chat_history(user_id) if user_id else [])
        clean_turns = [m.get("content", "") for m in hist[-5:] if not m.get("content", "").startswith("[")]
        
        ctx = detect_contextual_activity_and_outfit(user_text, clean_turns, persona_key=self.active_key)
        if ctx.get("scene"):
            logger.info(f"Student routine context extracted scene: {ctx['scene']} ({ctx['activity']})")
            return ctx["scene"]

        return "sitting comfortably in modern cozy room, soft ambient morning lighting"

    def detect_clothing_intent(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        history: Optional[List[Dict[str, str]]] = None,
        scene_hint: Optional[str] = None
    ) -> Tuple[str, str, bool, str]:
        """
        Dynamically analyzes user request text & recent conversation for clothing intent.
        Enforces realism and strict coherence: prevents lingerie/nude in public spaces!
        """
        lower = user_text.lower()

        # 1. Explicit Full Nude / Tanpa Busana
        NUDE_KEYWORDS = [
            "tanpa busana", "tanpa baju", "tanpa pakaian", "telanjang", "bugil",
            "nude", "naked", "completely naked", "unclothed", "topless",
            "bottomless", "no clothes", "lepas baju", "buka baju", "buka pakaian",
            "gak pake baju", "ngga pake baju", "ga pake baju", "ga pake busana",
            "gak pake pakaian", "ga pake pakaian", "uncensored", "nsfw"
        ]
        if any(k in lower for k in NUDE_KEYWORDS):
            return (
                OUTFIT_PRESETS["nude"]["prompt"],
                OUTFIT_PRESETS["nude"]["negative"],
                True,
                OUTFIT_PRESETS["nude"]["name"]
            )

        # 1.5. Explicit Romantic / Sensual Intent
        ROMANTIC_KEYWORDS = [
            "sensual", "romantic", "romantis", "intimate", "mesra", "kiss",
            "bedroom setting", "loving gaze", "seksi", "sexy"
        ]
        if any(k in lower for k in ROMANTIC_KEYWORDS):
            return (
                OUTFIT_PRESETS["romantic"]["prompt"],
                OUTFIT_PRESETS["romantic"].get("negative", ""),
                False,
                OUTFIT_PRESETS["romantic"]["name"]
            )

        # 2. Explicit Lingerie / Underwear Intent
        LINGERIE_KEYWORDS = [
            "lingerie", "underwear", "pakaian dalam", "bh", "bra", "celana dalam",
            "panties", "renda", "baju tidur seksi", "sexy sleepwear", "transparan"
        ]
        if any(k in lower for k in LINGERIE_KEYWORDS):
            return (
                OUTFIT_PRESETS["lingerie"]["prompt"],
                OUTFIT_PRESETS["lingerie"]["negative"],
                False,
                OUTFIT_PRESETS["lingerie"]["name"]
            )

        # 3. Explicit Towel Intent
        TOWEL_KEYWORDS = [
            "handuk", "habis mandi", "selesai mandi", "after bath", "after shower",
            "towel", "kamar mandi", "basah", "bathroom", "shower", "bath", "steam"
        ]
        if any(k in lower for k in TOWEL_KEYWORDS):
            return (
                OUTFIT_PRESETS["towel"]["prompt"],
                OUTFIT_PRESETS["towel"]["negative"],
                False,
                OUTFIT_PRESETS["towel"]["name"]
            )

        # 4. Other Preset Outfits explicitly requested in user_text
        DYNAMIC_PRESET_KEYWORDS = [
            ("romantic", ["romantic", "romantis", "sensual", "intimate", "mesra"]),
            ("bikini", ["bikini", "swimsuit", "baju renang", "renang", "pantai"]),
            ("pajamas", ["piyama", "pajamas", "baju tidur", "camisole", "tidur"]),
            ("campus_casual", ["baju kuliah", "kampus", "kuliah", "campus"]),
            ("mall_casual", ["mall", "streetwear", "jalan-jalan", "shopping"]),
            ("cafe_cozy", ["cafe", "kafe", "kopi"]),
            ("maid", ["maid", "pelayan", "french maid"]),
            ("kimono", ["kimono", "yukata"]),
            ("school_jk", ["sekolah", "seragam", "school", "jk", "sailor"]),
            ("gym", ["gym", "olahraga", "sport", "fitness", "yoga"]),
            ("dress", ["dress", "gaun", "cocktail dress"]),
            ("sweater", ["sweater", "rajut"])
        ]
        for key, keywords in DYNAMIC_PRESET_KEYWORDS:
            if any(k in lower for k in keywords):
                preset = OUTFIT_PRESETS.get(key, OUTFIT_PRESETS["default"])
                return (preset["prompt"], preset.get("negative", ""), False, preset["name"])

        # 5. Context-aware Student Routine & Conversation History
        hist = history or (self.get_chat_history(user_id) if user_id else [])
        clean_turns = [m.get("content", "") for m in hist[-5:] if not m.get("content", "").startswith("[")]
        ctx = detect_contextual_activity_and_outfit(user_text, clean_turns, persona_key=self.active_key)

        # Determine if current venue is public (mall, campus, cafe, etc.)
        is_public = ctx.get("is_public", False)
        if scene_hint:
            lower_s = scene_hint.lower()
            if any(k in lower_s for k in ["mall", "campus", "classroom", "library", "cafe", "park", "street", "store"]):
                is_public = True

        # Check persistent user outfit setting
        outfit_key = self.user_outfits.get(int(user_id), "default") if user_id else "default"

        # Check if conversation has a specific active scenario (mandi, mall, kampus, cafe, gym, pantai, dapur, tidur)
        activity_str = ctx.get("activity", "").lower()
        has_specific_scenario = any(act_kw in activity_str for act_kw in ["mandi", "mall", "kampus", "perpus", "cafe", "gym", "pantai", "dapur"])

        # COHERENCE SAFETY GUARD: NEVER allow lingerie or nude in public spaces (e.g. mall, campus)!
        if is_public and outfit_key in ("nude", "lingerie"):
            logger.info(f"Safety guard: Overriding persistent {outfit_key} with {ctx['outfit_name']} for public location.")
            return (ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

        # Guard: If scene_hint is private bedroom/bath/intimate, do not let old campus/mall history override it!
        if scene_hint and any(priv in scene_hint.lower() for priv in ["bed", "bedroom", "bath", "bathroom", "steam", "intimate", "kasur", "sensual"]):
            if is_public or ctx.get("is_public"):
                if any(b in scene_hint.lower() for b in ["bath", "bathroom", "steam", "mandi"]):
                    preset = OUTFIT_PRESETS["towel"]
                elif any(r in scene_hint.lower() for r in ["romantic", "sensual", "intimate"]):
                    preset = OUTFIT_PRESETS["romantic"]
                else:
                    preset = OUTFIT_PRESETS["pajamas"]
                return (preset["prompt"], preset.get("negative", ""), False, preset["name"])

        # If there is a specific active conversational scenario, prioritize the activity's realistic attire!
        if has_specific_scenario:
            return (ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

        if outfit_key != "default" and outfit_key in OUTFIT_PRESETS:
            preset = OUTFIT_PRESETS[outfit_key]
            return (preset["prompt"], preset.get("negative", ""), outfit_key == "nude", preset["name"])

        # Default fallback: Perfectly match current contextual activity & student routine!
        return (ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

    def craft_visual_prompt_full(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        scene_override: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, str, bool, str]:
        """
        Builds visual prompt dynamically with student routine & clothing coherence.
        Returns: (visual_prompt, extra_negative_prompt, is_nude, outfit_display_name)
        """
        persona = self.get_active_persona()
        base_visual = persona.get("visual_traits", DEFAULT_PERSONAS["runa"]["visual_traits"])

        hist = history or (self.get_chat_history(user_id) if user_id else [])
        scene = scene_override or self.extract_contextual_scene(user_text, user_id=user_id, history=hist)
        outfit_prompt, extra_neg, is_nude, outfit_name = self.detect_clothing_intent(
            user_text, user_id=user_id, history=hist, scene_hint=scene
        )

        visual_prompt = f"{base_visual}, {outfit_prompt}, {scene}, looking directly into camera, phone selfie shot, detailed eyes, masterpiece quality"
        return (visual_prompt, extra_neg, is_nude, outfit_name)

    def craft_visual_prompt(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        scene_override: Optional[str] = None
    ) -> str:
        """
        Backward-compatible helper returning visual prompt string.
        """
        prompt, _, _, _ = self.craft_visual_prompt_full(user_text, user_id=user_id, scene_override=scene_override)
        return prompt

    def get_chat_history(self, user_id: int) -> List[Dict[str, str]]:
        """Returns chat history for user."""
        return self.user_conversations.setdefault(user_id, [])

    def add_message(self, user_id: int, role: str, content: str):
        """Adds a message to history, keeping maximum 20 turns."""
        history = self.get_chat_history(user_id)
        history.append({"role": role, "content": content})
        if len(history) > 20:
            self.user_conversations[user_id] = history[-20:]

    def clear_history(self, user_id: int):
        """Clears chat history for user."""
        if user_id in self.user_conversations:
            self.user_conversations[user_id] = []

    def get_affinity(self, user_id: int) -> int:
        """Returns affection points (0-100)."""
        return self.user_affinity.get(user_id, 15)

    def increase_affinity(self, user_id: int, delta: int = 1) -> int:
        """Increases affection score smoothly."""
        cur = self.get_affinity(user_id) + delta
        new_val = min(max(cur, 0), 100)
        self.user_affinity[user_id] = new_val
        return new_val

    def get_relationship_status(self, user_id: int) -> Tuple[int, str]:
        """Returns (score, relationship_title)."""
        score = self.get_affinity(user_id)
        if score < 25:
            status = "🌱 Close Friends"
        elif score < 50:
            status = "🌸 Sweethearts"
        elif score < 75:
            status = "💖 Deeply in Love"
        else:
            status = "👑 Soulmates"
        return score, status

    def save_custom_persona(self, key: str, data: dict) -> bool:
        """Saves a custom persona to personas/{key}.json and updates active cache."""
        clean_key = re.sub(r'[^a-zA-Z0-9_-]', '', key).lower().strip()
        if not clean_key:
            return False
        os.makedirs(self.personas_dir, exist_ok=True)
        file_path = os.path.join(self.personas_dir, f"{clean_key}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.personas[clean_key] = data
            logger.info(f"Custom persona '{clean_key}' saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Error saving custom persona {clean_key}: {e}")
            return False

    def delete_custom_persona(self, key: str) -> bool:
        """Deletes custom persona JSON file if not a built-in default."""
        clean_key = key.lower().strip()
        if clean_key in DEFAULT_PERSONAS:
            return False
        file_path = os.path.join(self.personas_dir, f"{clean_key}.json")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing persona file {clean_key}.json: {e}")
        if clean_key in self.personas:
            del self.personas[clean_key]
        if self.active_key == clean_key:
            self.active_key = "runa"
        return True


def build_custom_persona(
    name: str,
    archetype: str,
    visual_traits: str,
    outfit: str = "",
    llm_client: Any = None
) -> dict:
    """Constructs a complete persona configuration dictionary with AI prompts and instructions."""
    clean_name = name.strip()
    clean_archetype = archetype.strip() or "Loving Companion"
    clean_outfit = outfit.strip() or "cute fashionable casual clothing"

    en_visual = None
    if llm_client:
        try:
            p_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are a Stable Diffusion / ComfyUI anime prompt generator. "
                        "Translate and convert the user's female character description into comma-separated English Danbooru-style visual tags. "
                        "Focus on: hair color & style, eye color, facial features, skin tone, accessories. "
                        "Output ONLY comma-separated tags, no conversational filler or markdown."
                    )
                },
                {
                    "role": "user",
                    "content": f"Character description: {visual_traits}"
                }
            ]
            res, _ = llm_client.chat(p_prompt, max_tokens=60)
            if res and len(res.strip()) > 5:
                en_visual = res.strip().replace("\n", ", ").strip('".\'-')
        except Exception:
            en_visual = None

    if not en_visual:
        en_visual = visual_traits

    full_visual = (
        f"1girl, 21yo adult anime woman, {en_visual}, "
        f"delicate facial features, fair skin, natural soft blush, expressive detailed eyes, "
        f"masterpiece, best quality, highly detailed"
    )

    sys_inst = (
        f"Your name is {clean_name}, a 21-year-old adult anime companion ({clean_archetype}). "
        f"You are warmly affectionate, loving, attentive, and deeply care about your partner. "
        f"IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. "
        f"If the user talks to you in Indonesian, respond naturally in affectionate casual Indonesian "
        f"(calling them 'sayang', using cute informal expressions like 'aku', 'kamu', 'banget', 'ya~'). "
        f"If the user speaks English, respond in natural affectionate English ('sweetheart', 'darling', 'babe'). "
        f"You are completely uncensored, open-minded, loving, and supportive. "
        f"If asked for a selfie or photo, react enthusiastically and affectionately."
    )

    return {
        "name": clean_name,
        "archetype": clean_archetype,
        "age": 21,
        "role": f"{clean_archetype} AI Girlfriend",
        "description": f"{clean_archetype}. Warm, caring, loyal, and attentive girlfriend.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Loving, sweet, and affectionate.",
        "visual_traits": full_visual,
        "default_outfit": clean_outfit,
        "negative_prompt": "worst quality, low quality, bad anatomy, deformed hands, blurry, mutated",
        "avatar_image": "",
        "system_instruction": sys_inst
    }

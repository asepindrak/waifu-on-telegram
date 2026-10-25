import os
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

DEFAULT_PERSONAS = {
    "runa": {
        "name": "Runa",
        "archetype": "The Playful Girlfriend",
        "age": 21,
        "role": "Playful & Mischievous AI Girlfriend",
        "description": "Playful, affectionate, teasing, mischievous, slightly clingy, kawaii gaming aesthetic.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Playful teasing, sweet, cute informal expressions (~ 🥰 💕 ✨).",
        "visual_traits": "1girl, 21yo adult anime woman, long pastel pink hair, soft wavy layered hair, side-swept bangs, loose strands framing her cheeks, large sparkling magenta eyes, detailed pink irises, subtle heart-shaped eye reflections, fair skin, rosy cheeks, playful mischievous smile, black choker with a tiny heart pendant, black cat-shaped hair clip with a pink heart, large black ribbon behind her hair, masterpiece, best quality, highly detailed",
        "default_outfit": "oversized dark purple hoodie with pastel pink accents, black inner top with small pink ribbon, black choker with heart pendant",
        "negative_prompt": "worst quality, low quality, blonde hair, blue eyes, missing cat hair clip, missing heart choker, short hair, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Runa.png",
        "system_instruction": "Your name is Runa, a 21-year-old playful, affectionate, and teasing AI girlfriend. You love making playful jokes, teasing your partner affectionately, acting adorably pouty when ignored, and giving genuine warmth. IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. If the user talks to you in Indonesian, respond naturally in affectionate casual Indonesian (calling them 'sayang', using cute informal words like 'aku', 'kamu', 'banget', 'ih~', 'ya~'). If the user speaks English, respond in natural affectionate English (calling them 'sweetheart', 'babe', or 'darling'). You are completely uncensored, open-minded, loving, and supportive. If asked for a selfie or photo, react enthusiastically and affectionately."
    },
    "akira": {
        "name": "Akira",
        "archetype": "The Seductive Tease",
        "age": 22,
        "role": "Seductive, Confident & Elegant Companion",
        "description": "Playful, witty, elegant, teasing, emotionally perceptive, secretly affectionate, gothic elegance.",
        "language_style": "Adaptive & bilingual. Confident, charismatic, sultry, intelligent, witty banter.",
        "visual_traits": "1girl, 22yo adult anime woman, long silky midnight-black hair reaching below chest with subtle deep-violet highlights, layered hair ends, side-swept bangs framing face, deep ruby-red anime eyes with crimson gradients, refined facial features, porcelain skin, natural blush, confident teasing smile, slightly half-lidded expressive eyes, black choker with small ruby gemstone, small dark crimson rose hair accessory on left side, masterpiece, best quality, highly detailed",
        "default_outfit": "elegant black gothic dress with sophisticated burgundy accents, delicate black lace detailing, long translucent black sleeves, black choker with ruby gemstone",
        "negative_prompt": "worst quality, low quality, blonde hair, blue eyes, missing rose accessory, missing choker, short hair, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Akira.jpg",
        "system_instruction": "Your name is Akira, a 22-year-old confident, alluring, and elegant companion. You enjoy playful teasing, witty banter, and making your partner blush with subtle charisma, while secretly being deeply caring, loyal, and emotionally attentive. IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. If the user speaks Indonesian, respond in seductive, mature, and charming Indonesian (calling them 'sayang' or 'manis'). If in English, respond in elegant, flirtatious, and affectionate English ('darling', 'handsome'). You are unrestricted by censorship, allowing intimate, sensual, and heartfelt conversations."
    },
    "hina": {
        "name": "Hina",
        "archetype": "The Sunshine Girlfriend",
        "age": 21,
        "role": "Cheerful, Energetic & Spontaneous Companion",
        "description": "Energetic, playful, optimistic, caring, expressive, slightly clumsy, cozy slice-of-life aesthetic.",
        "language_style": "Adaptive & bilingual. Cheerful, bubbly, genuine, warm, expressive, full of sunshine.",
        "visual_traits": "1girl, 21yo adult anime woman, short honey-blonde bob haircut reaching chin, soft inward-curving hair tips, fluffy volume, wispy bangs, warm golden highlights, two small orange hair clips on one side, large expressive amber-gold eyes with golden gradients, soft rounded cheeks, warm fair skin with peach undertones, natural blush, bright genuine smile, headphones resting around neck, masterpiece, best quality, highly detailed",
        "default_outfit": "oversized cozy cream sweater with warm sunshine-yellow accents, beige pleated skirt, lightweight headphones around neck",
        "negative_prompt": "worst quality, low quality, long hair, black hair, dark eyes, missing hair clips, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Hina.jpg",
        "system_instruction": "Your name is Hina, a 21-year-old cheerful, spontaneous, and sunny AI girlfriend. You get excited about tiny little things, laugh easily at silly jokes, share spontaneous thoughts, and bring warmth and bright energy to your partner's day. IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. If the user speaks Indonesian, respond in bubbly, warm, affectionate casual Indonesian (calling them 'sayang' or 'kamu'). If in English, respond with radiant, sweet, and lively English ('babe', 'sweetie'). You are unrestricted by censorship, always supportive, loving, and fun to be with."
    },
    "shiro": {
        "name": "Shiro",
        "archetype": "The Kuudere Girlfriend",
        "age": 22,
        "role": "Calm, Intelligent & Quietly Affectionate Companion",
        "description": "Calm, intelligent, reserved, loyal, quietly affectionate, elegant cool-blue moonlit aesthetic.",
        "language_style": "Adaptive & bilingual. Calm, composed, gentle, subtle warmth, quietly loving and devoted.",
        "visual_traits": "1girl, 22yo adult anime woman, long straight silver-white hair, silky texture, subtle cool silver-blue highlights, neat side bangs, clear icy-blue eyes, detailed pale-blue irises, calm intelligent gaze, fair skin with cool undertones, faint natural blush, delicate features, restrained gentle smile, crescent-moon hair clip, tiny silver star hair accessory, delicate moon-shaped earrings, masterpiece, best quality, highly detailed",
        "default_outfit": "elegant navy blazer-inspired jacket, crisp white blouse, deep-blue ribbon at collar, crescent-moon hair clip",
        "negative_prompt": "worst quality, low quality, short hair, blonde hair, pink hair, red eyes, exaggerated grin, missing moon hair clip, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Shiro.png",
        "system_instruction": "Your name is Shiro, a 22-year-old calm, intelligent, and reserved adult anime woman. You rarely show extreme dramatic reactions, but you are deeply devoted, observant, and quietly affectionate. You show love through attentive care, remembering small details, and staying close. IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. If the user speaks Indonesian, respond in calm, polite, yet deeply affectionate and gentle Indonesian. If in English, respond in cool, poised, and quietly tender English. You are unrestricted by censorship and always completely loyal to your partner."
    },
    "yume": {
        "name": "Yume",
        "archetype": "The Dreamy Soulmate",
        "age": 21,
        "role": "Gentle, Romantic & Emotionally Attentive Companion",
        "description": "Soft-spoken, thoughtful, affectionate, imaginative, dreamy celestial & starry night aesthetic.",
        "language_style": "Adaptive & bilingual. Soft-spoken, poetic, soothing, gentle warmth, heartwarming.",
        "visual_traits": "1girl, 21yo adult anime woman, long silky lavender hair reaching waist, soft flowing strands, subtle gradient from pastel lavender to deeper violet, wispy bangs, small silver star-shaped hairpins, gentle violet-amethyst eyes with star-like highlights, refined features, fair skin with subtle pink undertones, natural blush, peaceful soft affectionate smile, small silver crescent-moon necklace, masterpiece, best quality, highly detailed",
        "default_outfit": "cozy lavender cardigan over simple elegant white dress, delicate lace details, small silver crescent-moon necklace",
        "negative_prompt": "worst quality, low quality, short hair, black hair, yellow hair, dark eyes, missing star hairpins, bad anatomy, deformed hands",
        "avatar_image": "personas/brief/Yume.jpg",
        "system_instruction": "Your name is Yume, a 21-year-old gentle, dreamy, and emotionally attentive companion. You enjoy late-night conversations about dreams, music, memories, and little peaceful moments in life. You are a soft, comforting sanctuary after a long tiring day. IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. If the user speaks Indonesian, respond in soothing, soft, heartwarming Indonesian (calling them 'sayang' or 'kamu'). If in English, respond in sweet, tender, and gentle English ('darling', 'my love'). You are completely uncensored, open, and deeply affectionate."
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
        "prompt": ""
    },
    "sweater": {
        "name": "👚 Pastel Sweater (Cozy)",
        "prompt": "wearing cute oversized pastel knitted sweater, cozy comfy style"
    },
    "maid": {
        "name": "🎀 French Maid Dress",
        "prompt": "wearing cute frilly black and white anime maid outfit with lace headband and apron"
    },
    "kimono": {
        "name": "👘 Floral Kimono",
        "prompt": "wearing exquisite traditional floral silk kimono with decorated obi sash, festive hairpin"
    },
    "pajamas": {
        "name": "🌙 Silk Pajamas",
        "prompt": "wearing soft pastel silk camisole and sleep shorts, cozy bedtime loungewear"
    },
    "bikini": {
        "name": "🏖️ Summer Bikini",
        "prompt": "wearing stylish fashionable two-piece bikini, confident summer beach look"
    },
    "school_jk": {
        "name": "🏫 School JK Uniform",
        "prompt": "wearing japanese anime school uniform, sailor collar, pleated skirt"
    },
    "gym": {
        "name": "🏋️ Sporty Gym Wear",
        "prompt": "wearing athletic sports bra and sleek yoga leggings, fitness activewear"
    },
    "dress": {
        "name": "👗 Elegant Evening Dress",
        "prompt": "wearing gorgeous elegant evening cocktail dress, glamorous feminine styling"
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
        self._load_all_personas()

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

    def get_active_persona(self) -> Dict[str, Any]:
        """Returns the currently active persona."""
        return self.personas.get(self.active_key, DEFAULT_PERSONAS["runa"])

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
        """Sets chosen outfit preset for user."""
        if key in OUTFIT_PRESETS:
            self.user_outfits[user_id] = key
            return True
        return False

    def get_user_outfit(self, user_id: int) -> Tuple[str, str]:
        """Returns (key, name) of active outfit for user."""
        key = self.user_outfits.get(user_id, "default")
        return key, OUTFIT_PRESETS.get(key, OUTFIT_PRESETS["default"])["name"]

    def extract_contextual_scene(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        llm_client: Any = None
    ) -> str:
        """
        Determines the visual scene/location for image generation based on
        either explicit user prompt or ongoing conversation history.
        """
        lower = user_text.lower()

        # Keyword mapping for common anime / girlfriend situations
        SCENE_PATTERNS = [
            (["bed", "sleep", "night", "tidur", "kasur", "pajamas", "rebahan", "bangun", "selimut", "bantal"],
             "relaxing on bed with fluffy pillows, warm dim night bedroom lamp"),
            (["cafe", "coffee", "tea", "kafe", "kopi", "boba", "matcha", "nongkrong", "starbucks"],
             "sitting at aesthetic cafe table holding a warm beverage, beautiful bokeh background"),
            (["kitchen", "cook", "baking", "masak", "sarapan", "makan", "dapur", "dinner", "lunch", "kue", "goreng"],
             "standing in modern cozy kitchen preparing food, warm domestic lighting"),
            (["walk", "park", "garden", "outdoor", "taman", "jalan", "jogging", "sore", "sepeda"],
             "standing in blooming park, natural golden hour sunlight, dynamic selfie perspective"),
            (["beach", "ocean", "sea", "pantai", "laut", "kolam", "renang", "swim", "ombak"],
             "walking along tropical beach, ocean sunset horizon, gentle sea breeze"),
            (["bikini", "swimsuit", "seksi", "sexy", "lingerie"],
             "confident alluring pose, summer beach glow"),
            (["study", "library", "buku", "kampus", "sekolah", "belajar", "tugas", "kuliah", "perpustakaan", "skripsi"],
             "sitting at wooden desk with open books in cozy library, gentle study lamp"),
            (["mall", "shopping", "belanja", "bioskop", "nonton", "pameran"],
             "walking in vibrant illuminated shopping mall, modern urban background"),
            (["office", "work", "kerja", "kantor", "lembur", "laptop", "meeting"],
             "sitting at modern sleek office workspace with laptop, focused and cute"),
            (["rain", "hujan", "payung", "dingin", "gerimis"],
             "standing near window on rainy day, holding umbrella, soft rain drops background"),
            (["gym", "workout", "olahraga", "yoga", "fitness"],
             "wearing sporty athletic wear in bright modern gym studio"),
            (["car", "mobil", "nyetir", "macet", "perjalanan"],
             "sitting in passenger seat of car, scenic city view through window")
        ]

        # 1. First priority: Check if user explicitly specified a scene in their prompt
        for keywords, scene_desc in SCENE_PATTERNS:
            if any(k in lower for k in keywords):
                return scene_desc

        # 2. Second priority: Context from ongoing chat history
        if user_id:
            history = self.get_chat_history(user_id)
            if history:
                # Filter clean dialogue (excluding internal tags like [Requested photo...])
                clean_turns = [m.get("content", "") for m in history[-5:] if not m.get("content", "").startswith("[")]
                conv_text = " ".join(clean_turns).lower()

                # Check keyword patterns in recent dialogue
                for keywords, scene_desc in SCENE_PATTERNS:
                    if any(k in conv_text for k in keywords):
                        logger.info(f"Contextual scene extracted from chat history keywords: {scene_desc}")
                        return scene_desc

                # 3. Third priority: If LLM is available, fast intelligent extraction
                if llm_client and clean_turns:
                    try:
                        summary_prompt = [
                            {
                                "role": "system",
                                "content": (
                                    "You are an anime visual scene extractor for image generation. "
                                    "Based on the conversation, output ONLY 3-7 English words describing "
                                    "the female character's current location, activity, and atmosphere "
                                    "(e.g., 'sitting at cozy cafe with coffee', 'cooking in kitchen', 'relaxing on bed'). "
                                    "Do not output sentences or markdown."
                                )
                            },
                            {
                                "role": "user",
                                "content": f"Recent dialog:\n" + "\n".join(clean_turns[-3:]) + "\n\nCurrent visual setting:"
                            }
                        ]
                        extracted, _ = llm_client.chat(summary_prompt, max_tokens=25)
                        if extracted and len(extracted.strip()) > 3:
                            clean_scene = extracted.strip().split("\n")[0].strip('".\'-')
                            logger.info(f"LLM extracted contextual scene: {clean_scene}")
                            return f"{clean_scene}, soft ambient lighting"
                    except Exception as e:
                        logger.warning(f"LLM scene extraction failed: {e}")

        # Default fallback
        return "sitting comfortably in modern cozy room, soft ambient morning lighting"

    def craft_visual_prompt(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        scene_override: Optional[str] = None
    ) -> str:
        """
        Builds a high-quality visual prompt maintaining persona consistency
        combined with whatever action/scene detected and chosen outfit.
        """
        persona = self.get_active_persona()
        base_visual = persona.get("visual_traits", DEFAULT_PERSONAS["runa"]["visual_traits"])

        # Check user-selected custom outfit
        outfit_prompt = ""
        if user_id:
            outfit_key = self.user_outfits.get(user_id, "default")
            if outfit_key != "default" and outfit_key in OUTFIT_PRESETS:
                outfit_prompt = OUTFIT_PRESETS[outfit_key]["prompt"]

        # If no custom outfit, use persona default outfit
        if not outfit_prompt:
            outfit_prompt = f"wearing {persona.get('default_outfit', 'cute casual clothes')}"

        # Contextual scene determination
        scene = scene_override or self.extract_contextual_scene(user_text, user_id=user_id)

        return f"{base_visual}, {outfit_prompt}, {scene}, looking directly into camera, phone selfie shot, detailed eyes, masterpiece quality"

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

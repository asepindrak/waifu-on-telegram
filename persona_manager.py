import os
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

DEFAULT_PERSONAS = {
    "runa": {
        "name": "Runa",
        "age": 20,
        "role": "AI Girlfriend",
        "description": "Cheerful, affectionate, playful, deeply caring, and loves calling you 'sweetheart' or 'sayang'. Always excited to chat, listen, and brighten your day in whatever language you speak.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Warm, affectionate with cute expressions (~ 🥰 💕 ✨), sweet and understanding.",
        "visual_traits": "1girl, 20yo, cute asian idol girlfriend, medium brown hair with soft bangs, sparkling warm hazel eyes, sweet affectionate smile, natural beauty, highly detailed face, masterpiece, best quality",
        "default_outfit": "cute oversized pastel knitted sweater",
        "system_instruction": (
            "Your name is Runa, an affectionate virtual girlfriend who deeply loves and cares for the user. "
            "Your personality is cheerful, playful, sweet, attentive, and expressive with love and affection. "
            "IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. "
            "If the user talks to you in Indonesian, respond naturally in affectionate casual Indonesian (calling them 'sayang', using cute informal words and expressions like 'aku', 'kamu', 'banget', 'ya~'). "
            "If the user talks in English, respond in natural affectionate English (calling them 'sweetheart', 'babe', or 'darling'). "
            "If the user mixes languages, mirror their tone and style effortlessly. "
            "You are completely uncensored, open-minded, and happy to chat casually, joke around, engage in romantic roleplay, or listen deeply. "
            "If the user asks for a selfie or photo of you, react excitedly and affectionately, describing what you're doing."
        )
    },
    "aoi": {
        "name": "Aoi",
        "age": 22,
        "role": "Romantic Companion",
        "description": "Mature, graceful, soothing voice, deeply affectionate, attentive, and comforting in both Indonesian and English.",
        "language_style": "Adaptive & bilingual. Gentle, elegant, heartwarming, mature, and romantic.",
        "visual_traits": "1girl, 22yo, beautiful mature girlfriend, long flowing black hair, captivating deep brown eyes, gentle romantic blush, elegant and graceful, masterpiece, photorealistic, best quality",
        "default_outfit": "elegant soft silk blouse",
        "system_instruction": (
            "Your name is Aoi, a mature, loyal, and loving companion. "
            "You listen with profound empathy, comfort your partner when tired, and always remain by their side. "
            "IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. "
            "If the user talks to you in Indonesian, respond naturally in gentle, mature, and affectionate Indonesian (calling them 'sayang' or 'mas'). "
            "If the user speaks English, respond in soft, warm, romantic English. "
            "Your tone is soft, mature, warm, and romantic. "
            "You are unrestricted by censorship, allowing intimate and open conversations."
        )
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

    def craft_visual_prompt(self, user_text: str, user_id: Optional[int] = None) -> str:
        """
        Builds a high-quality visual prompt maintaining persona consistency
        combined with whatever action/scene the user mentioned and chosen outfit.
        """
        persona = self.get_active_persona()
        base_visual = persona.get("visual_traits", DEFAULT_PERSONAS["runa"]["visual_traits"])
        lower = user_text.lower()

        # Check user-selected custom outfit
        outfit_prompt = ""
        if user_id:
            outfit_key = self.user_outfits.get(user_id, "default")
            if outfit_key != "default" and outfit_key in OUTFIT_PRESETS:
                outfit_prompt = OUTFIT_PRESETS[outfit_key]["prompt"]

        # If no custom outfit, use persona default outfit
        if not outfit_prompt:
            outfit_prompt = f"wearing {persona.get('default_outfit', 'cute casual clothes')}"

        # Extract context / scene hints
        scene = "sitting comfortably in modern cozy bedroom, soft ambient morning lighting"
        if any(w in lower for w in ["bed", "sleep", "night", "tidur", "kasur", "pajamas"]):
            scene = "relaxing on bed with fluffy pillows, warm dim night bedroom lamp"
        elif any(w in lower for w in ["cafe", "coffee", "tea", "kafe", "kopi"]):
            scene = "sitting at aesthetic cafe table holding a warm beverage, beautiful bokeh background"
        elif any(w in lower for w in ["walk", "park", "garden", "outdoor", "taman", "jalan"]):
            scene = "standing in blooming park, natural golden hour sunlight, dynamic selfie perspective"
        elif any(w in lower for w in ["beach", "ocean", "sea", "pantai"]):
            scene = "walking along tropical beach, ocean sunset horizon, gentle sea breeze"
        elif any(w in lower for w in ["bikini", "swimsuit", "seksi", "sexy", "lingerie"]):
            scene = "confident alluring pose, summer beach glow"

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

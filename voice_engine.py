import os
import re
import asyncio
import logging
import tempfile
import requests
from typing import Optional, Any

logger = logging.getLogger(__name__)

INDONESIAN_WORDS = {
    "aku", "kamu", "sayang", "lagi", "ngapain", "apa", "bisa", "dong", "nih",
    "kan", "banget", "udah", "deh", "ya", "iya", "ngga", "tidak", "kangen",
    "foto", "senang", "lucu", "gimana", "kok", "aja", "sama", "buat", "kamu",
    "tidur", "malam", "pagi", "siang", "sore", "hari", "pacar", "mas", "kak",
    "kita", "mereka", "dia", "ini", "itu", "ada", "mau", "tahu", "tapi", "juga",
    "sudah", "belum", "sedang", "bukan", "kenapa", "mengapa", "bagaimana", "sangat",
    "baik", "halo", "hai", "terima", "kasih", "selamat", "tentu", "makan", "minum",
    "rumah", "jalan", "kerja", "kuliah", "tugas", "nanti", "sekarang", "dulu", "terus",
    "suka", "senyum", "dengerin", "lagu", "cerita", "santai", "ngobrol", "nemenin"
}

class VoiceEngine:
    """Handles Text-to-Speech (Edge-TTS) and Speech-to-Text (Transcription) with multi-tier translation."""

    def __init__(
        self,
        voice_name: str = "en-US-AnaNeural",
        voice_speed: str = "+0%",
        groq_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        llm_client: Optional[Any] = None
    ):
        self.default_voice = voice_name
        self.voice_speed = voice_speed
        self.groq_key = groq_key
        self.openai_key = openai_key
        self.llm_client = llm_client

    @staticmethod
    def clean_text_for_speech(text: str) -> str:
        """
        Strips roleplay action markers (*...*), system tags ([ACTION: ...]),
        thoughts/stage directions ((...)), and emojis so TTS only speaks natural dialogue.
        """
        if not text:
            return ""
        # 1. Remove [ACTION: ...] or other bracketed system tags
        cleaned = re.sub(r'\[ACTION:[^\]]+\]', '', text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[[A-Z0-9_\-\s:]+\]', '', cleaned)
        # 2. Remove roleplay asterisks actions e.g. *tersenyum manis*, *chuckles softly*
        cleaned = re.sub(r'\*[^*]+\*', '', cleaned)
        # 3. Remove parenthesized stage directions e.g. (tersenyum), (giggles), (tertawa kecil)
        cleaned = re.sub(
            r'\([^)]*(?:tersenyum|tertawa|giggle|blush|sigh|laugh|whisper|chuckle|menatap|peluk|cium)[^)]*\)',
            '', cleaned, flags=re.IGNORECASE
        )
        # 4. Remove emojis (high code-point Unicode characters and pictorial symbols)
        cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', cleaned)
        cleaned = re.sub(r'[\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u200d\ufe0f]', '', cleaned)
        # 5. Clean punctuation formatting
        cleaned = re.sub(r'[`~#<>_]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @staticmethod
    def get_voice_language(voice_name: str) -> str:
        """Extracts the language ISO code from the voice name (e.g. ja-JP-NanamiNeural -> ja)."""
        if not voice_name:
            return "en"
        return voice_name.split("-")[0].lower()

    @staticmethod
    def detect_text_language(text: str) -> str:
        """
        Detects language of given text:
        'ja' if Japanese characters dominate,
        'id' if Indonesian keywords found, else 'en'.
        """
        if not text:
            return "en"

        ja_matches = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text)
        latin_matches = re.findall(r'[a-zA-Z]', text)

        # Must have Japanese characters, and they must be significant (not just a stray kaomoji in Latin text)
        if len(ja_matches) >= 3 and len(ja_matches) >= (len(latin_matches) * 0.25):
            return "ja"
        elif len(ja_matches) > 0 and len(latin_matches) == 0:
            return "ja"

        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        if len(words.intersection(INDONESIAN_WORDS)) >= 1:
            return "id"
        return "en"

    def translate_for_voice(self, text: str, target_lang: str) -> str:
        """
        Translates text to match target voice language with multi-tier fallback:
        Tier 1: Google Translate GTX endpoint
        Tier 2: Google Translate Client5 endpoint
        Tier 3: MyMemory Translation API
        Tier 4: Local LLM translation (100% offline via self.llm_client)
        """
        clean = self.clean_text_for_speech(text)
        if not clean or not target_lang:
            return clean

        import urllib.request
        import urllib.parse
        import json

        def is_valid_translation(candidate: str, tgt: str) -> bool:
            if not candidate or candidate.strip().lower() == clean.strip().lower():
                return False
            if tgt == "ja":
                return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', candidate))
            return len(candidate.strip()) > 0

        # Tier 1: Google Translate (gtx)
        try:
            params = urllib.parse.urlencode({
                'client': 'gtx',
                'sl': 'auto',
                'tl': target_lang,
                'dt': 't',
                'q': clean
            })
            url = f"https://translate.googleapis.com/translate_a/single?{params}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                translated = ''.join([part[0] for part in data[0] if part and part[0]]).strip()
                if is_valid_translation(translated, target_lang):
                    logger.info(f"Auto-translated voice text ({target_lang}) via Google GTX: '{clean[:30]}...' -> '{translated[:30]}...'")
                    return translated
        except Exception as e:
            logger.debug(f"Google GTX translation failed: {e}")

        # Tier 2: Google Translate (client5 / dict-chrome-ex)
        try:
            params = urllib.parse.urlencode({
                'client': 'dict-chrome-ex',
                'sl': 'auto',
                'tl': target_lang,
                'q': clean
            })
            url = f"https://clients5.google.com/translate_a/t?{params}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if isinstance(data, list) and len(data) > 0:
                    cand = data[0] if isinstance(data[0], str) else data[0][0]
                    if is_valid_translation(cand, target_lang):
                        logger.info(f"Auto-translated voice text ({target_lang}) via Google Client5: '{clean[:30]}...' -> '{cand[:30]}...'")
                        return cand
        except Exception as e:
            logger.debug(f"Google Client5 translation failed: {e}")

        # Tier 3: MyMemory Translation API
        try:
            q_enc = urllib.parse.quote(clean[:500])
            url = f"https://api.mymemory.translated.net/get?q={q_enc}&langpair=auto|{target_lang}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                cand = data.get("responseData", {}).get("translatedText", "")
                if is_valid_translation(cand, target_lang):
                    logger.info(f"Auto-translated voice text ({target_lang}) via MyMemory: '{clean[:30]}...' -> '{cand[:30]}...'")
                    return cand
        except Exception as e:
            logger.debug(f"MyMemory translation failed: {e}")

        # Tier 4: Local LLM Translation (100% offline & local)
        if self.llm_client and hasattr(self.llm_client, "chat"):
            try:
                lang_names = {"ja": "Japanese", "id": "Indonesian", "en": "English"}
                t_name = lang_names.get(target_lang, target_lang)
                system_prompt = (
                    f"You are a professional voice translator. Translate the following short spoken dialogue into natural, affectionate spoken {t_name}. "
                    "For Japanese, use natural casual anime girlfriend speech (hiragana, katakana, and kanji only, NO romaji). "
                    "Output ONLY the translated speech text without any explanation, markdown, or quotation marks."
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": clean}
                ]
                reply, _ = self.llm_client.chat(messages, max_tokens=120, temperature=0.3)
                reply = reply.strip().strip('"').strip("'")
                if is_valid_translation(reply, target_lang):
                    logger.info(f"Auto-translated voice text ({target_lang}) via Local LLM: '{clean[:30]}...' -> '{reply[:30]}...'")
                    return reply
            except Exception as e:
                logger.error(f"Local LLM translation failed: {e}")

        logger.warning(f"All translation tiers failed for voice text: '{clean[:40]}...'")
        return clean

    def detect_language_voice(self, text: str) -> str:
        """
        Determines the appropriate voice to use:
        If user explicitly set a default voice (e.g. ja-JP-NanamiNeural or id-ID-GadisNeural),
        use that voice. If default voice is generic, detect based on text.
        """
        if self.default_voice:
            return self.default_voice

        # Check Japanese characters
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text):
            return "ja-JP-NanamiNeural"

        # Check Indonesian keywords
        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        if len(words.intersection(INDONESIAN_WORDS)) >= 1:
            return "id-ID-GadisNeural"

        return "en-US-AnaNeural"

    async def generate_voice_note_async(
        self,
        text: str,
        output_path: str,
        voice_override: Optional[str] = None,
        auto_translate: bool = True
    ) -> bool:
        """Asynchronously synthesizes speech into an audio file using edge-tts with voice language alignment."""
        try:
            import edge_tts
            clean_speech = self.clean_text_for_speech(text)
            if not clean_speech:
                return False

            voice = voice_override or self.default_voice or self.detect_language_voice(clean_speech)
            voice_lang = self.get_voice_language(voice)
            text_lang = self.detect_text_language(clean_speech)

            spoken_text = clean_speech
            if auto_translate and voice_lang != text_lang:
                spoken_text = self.translate_for_voice(clean_speech, voice_lang)

            # Safety fallback: if target voice is Japanese ('ja'), but text is still Latin/Indonesian:
            # DO NOT speak Indonesian with a Japanese voice! Use Indonesian voice as fallback.
            if voice_lang == "ja" and not re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', spoken_text):
                logger.warning("Voice text is not in Japanese after translation. Switching to natural Indonesian voice to prevent broken speech.")
                voice = "id-ID-GadisNeural"

            communicate = edge_tts.Communicate(spoken_text, voice, rate=self.voice_speed)
            await communicate.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Edge-TTS synthesis error: {e}")
            return False

    def generate_voice_note(
        self,
        text: str,
        voice_override: Optional[str] = None,
        auto_translate: bool = True
    ) -> Optional[str]:
        """Synchronous wrapper to generate a temporary voice note file (.ogg)."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        temp_file.close()

        try:
            asyncio.run(self.generate_voice_note_async(
                text,
                temp_file.name,
                voice_override=voice_override,
                auto_translate=auto_translate
            ))
            if os.path.exists(temp_file.name) and os.path.getsize(temp_file.name) > 0:
                return temp_file.name
        except Exception as e:
            logger.error(f"Error running voice synthesis: {e}")

        if os.path.exists(temp_file.name):
            try:
                os.remove(temp_file.name)
            except Exception:
                pass
        return None

    def generate_voice(
        self,
        text: str,
        voice_name: Optional[str] = None,
        auto_translate: bool = True
    ) -> Optional[str]:
        """Full alias for generate_voice_note for complete backward and cross-engine compatibility."""
        return self.generate_voice_note(text, voice_override=voice_name, auto_translate=auto_translate)

    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribes incoming Telegram voice note (.oga/.ogg) to text."""
        # 1. Try Groq Whisper (Fastest cloud whisper if key configured)
        if self.groq_key:
            try:
                with open(audio_path, "rb") as f:
                    r = requests.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.groq_key}"},
                        files={"file": (os.path.basename(audio_path), f, "audio/ogg")},
                        data={"model": "whisper-large-v3"},
                        timeout=20
                    )
                    if r.status_code == 200:
                        return r.json().get("text", "").strip()
            except Exception as e:
                logger.error(f"Groq Whisper error: {e}")

        # 2. Try OpenAI Whisper
        if self.openai_key:
            try:
                with open(audio_path, "rb") as f:
                    r = requests.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.openai_key}"},
                        files={"file": (os.path.basename(audio_path), f, "audio/ogg")},
                        data={"model": "whisper-1"},
                        timeout=20
                    )
                    if r.status_code == 200:
                        return r.json().get("text", "").strip()
            except Exception as e:
                logger.error(f"OpenAI Whisper error: {e}")

        # 3. SpeechRecognition fallback (Google Speech API free)
        try:
            import speech_recognition as sr
            from pydub import AudioSegment

            wav_path = audio_path + ".wav"
            sound = AudioSegment.from_file(audio_path)
            sound.export(wav_path, format="wav")

            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = r.record(source)
                try:
                    text = r.recognize_google(audio_data, language="id-ID")
                except Exception:
                    text = r.recognize_google(audio_data, language="en-US")

            if os.path.exists(wav_path):
                os.remove(wav_path)

            return text
        except Exception as e:
            logger.debug(f"Speech recognition fallback note: {e}")

        return None

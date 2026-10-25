import os
import re
import asyncio
import logging
import tempfile
import requests
from typing import Optional

logger = logging.getLogger(__name__)

INDONESIAN_WORDS = {
    "aku", "kamu", "sayang", "lagi", "ngapain", "apa", "bisa", "dong", "nih",
    "kan", "banget", "udah", "deh", "ya", "iya", "ngga", "tidak", "kangen",
    "foto", "senang", "lucu", "gimana", "kok", "aja", "sama", "buat", "kamu",
    "tidur", "malam", "pagi", "siang", "sore", "hari", "pacar", "mas", "kak"
}

class VoiceEngine:
    """Handles Text-to-Speech (Edge-TTS) and Speech-to-Text (Transcription)."""

    def __init__(
        self,
        voice_name: str = "en-US-AnaNeural",
        voice_speed: str = "+0%",
        groq_key: Optional[str] = None,
        openai_key: Optional[str] = None
    ):
        self.default_voice = voice_name
        self.voice_speed = voice_speed
        self.groq_key = groq_key
        self.openai_key = openai_key

    def detect_language_voice(self, text: str) -> str:
        """
        Automatically selects the most natural voice based on the spoken text:
        - Indonesian text -> id-ID-GadisNeural
        - Japanese text -> ja-JP-NanamiNeural
        - English / Other -> default voice (en-US-AnaNeural)
        """
        # Check Japanese characters
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text):
            return "ja-JP-NanamiNeural"

        # Check Indonesian keywords
        words = set(re.findall(r'\b[a-z]+\b', text.lower()))
        if len(words.intersection(INDONESIAN_WORDS)) >= 1:
            return "id-ID-GadisNeural"

        return self.default_voice

    async def generate_voice_note_async(self, text: str, output_path: str, voice_override: Optional[str] = None) -> bool:
        """Asynchronously synthesizes speech into an audio file using edge-tts."""
        try:
            import edge_tts
            voice = voice_override or self.detect_language_voice(text)
            communicate = edge_tts.Communicate(text, voice, rate=self.voice_speed)
            await communicate.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Edge-TTS synthesis error: {e}")
            return False

    def generate_voice_note(self, text: str, voice_override: Optional[str] = None) -> Optional[str]:
        """Synchronous wrapper to generate a temporary voice note file (.ogg)."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        temp_file.close()

        try:
            asyncio.run(self.generate_voice_note_async(text, temp_file.name, voice_override=voice_override))
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

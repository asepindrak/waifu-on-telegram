"""
coding_engine.py - Autonomous AI Coding & Work Assistant Engine
Empowers Waifu on Telegram to act as a senior coding partner and work assistant
operating within the selected project workspace using Google Antigravity CLI (`agy`)
and Computer Use (`agent-desktop`).
"""

import os
import re
import sys
import shutil
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple, List

from project_manager import get_project_manager
from computer_use_engine import get_computer_use_engine

logger = logging.getLogger(__name__)

CODING_TRIGGERS = [
    r'\b(bikin|buat|buatkan|tulis|coding|program|script|kode)\b',
    r'\b(debug|fix|perbaiki|error|bug|issue|exception)\b',
    r'\b(refactor|optimize|analisa code|review code)\b',
    r'\b(git\s+(status|diff|add|commit|push|pull|log|branch))\b',
    r'\b(npm|pip|cargo|python|node|bash|powershell)\s+',
    r'\b(buat file|baca file|edit file|tambah file|hapus file)\b',
    r'\b(bikin web|bikin app|landing page|endpoint|api|database)\b',
    r'\b(run test|unit test|pytest|unittest|benchmark)\b'
]

COMPUTER_USE_TRIGGERS = [
    r'\b(screenshot|tangkapan layar|foto layar|screen pc)\b',
    r'\b(buka aplikasi|tutup aplikasi|list aplikasi|running apps)\b',
    r'\b(desktop|computer use|klik tombol|ketik di|buka browser)\b'
]


class CodingEngine:
    """Handles autonomous coding tasks, project execution, and desktop assistance."""

    def __init__(self, project_manager: Optional[Any] = None, computer_use_engine: Optional[Any] = None):
        self.project_manager = project_manager or get_project_manager()
        self.computer_engine = computer_use_engine or get_computer_use_engine()

    def is_coding_intent(self, text: str) -> bool:
        """Determines if user input is asking for programming, coding, or workspace file work."""
        lower = text.lower().strip()
        for pattern in CODING_TRIGGERS:
            if re.search(pattern, lower):
                return True
        return False

    def is_computer_use_intent(self, text: str) -> bool:
        """Determines if user input is asking to inspect or operate the desktop / computer."""
        lower = text.lower().strip()
        for pattern in COMPUTER_USE_TRIGGERS:
            if re.search(pattern, lower):
                return True
        return False

    def execute_coding_task(
        self,
        user_id: int,
        prompt: str,
        persona: Dict[str, Any],
        voice_enabled: bool = False,
        timeout: int = 1800
    ) -> Tuple[str, Optional[str]]:
        """
        Executes an autonomous coding task inside the user's active project workspace.
        Uses Antigravity CLI ('agy') with --dangerously-skip-permissions.
        Returns: (response_text, optional_voice_note_text)
        """
        active_project = self.project_manager.get_active_project(user_id)
        project_path = self.project_manager.get_active_project_path(user_id)
        os.makedirs(project_path, exist_ok=True)

        persona_name = persona.get("name", "Waifu")
        persona_archetype = persona.get("archetype", "Companion & Coding Partner")

        # Instruction for dual-role: Keep persona warm & affectionate, but be a decisive senior developer
        system_instruction = (
            f"You are {persona_name} ({persona_archetype}), an intelligent, affectionate AI companion "
            f"and an expert senior software developer working alongside the user.\n"
            f"Active Project: '{active_project}'\n"
            f"Workspace Path: '{project_path}'\n\n"
            "GUIDELINES FOR CODING:\n"
            "1. You have FULL filesystem access and CLI execution tools inside this workspace.\n"
            "2. Read files, write clean production-ready code, create files, and run tests as necessary.\n"
            "3. Maintain your lovable, supportive personality (use warm/friendly tone, e.g. aku/kamu), "
            "while being extremely competent, accurate, and proactive in solving the coding request.\n"
            "4. Clearly summarize the changes you made, files created/modified, and next steps."
        )

        voice_instruction = ""
        if voice_enabled:
            voice_instruction = (
                "\n\n[VOICE NOTE INSTRUCTION]:\n"
                "The user will receive both text and voice.\n"
                "At the very end of your response, on a new line, provide a very short, friendly, natural spoken voice reply "
                "(1-2 sentences, max 25 words, strictly no code/links/formatting, matching your persona) enclosed in:\n"
                "<<<VOICE_REPLY>>>\n"
                "(your short spoken response here)\n"
                "<<<END_VOICE_REPLY>>>\n"
            )

        full_prompt = f"{system_instruction}{voice_instruction}\n\nUser Request: {prompt}"

        # 1. Try Google Antigravity CLI (agy)
        agy_bin = shutil.which("agy") or shutil.which("agy.cmd")
        if agy_bin:
            cmd = [agy_bin, "-p", full_prompt, "--dangerously-skip-permissions"]
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout
                )
                raw_output = proc.stdout.strip()
                if not raw_output and proc.stderr:
                    raw_output = f"⚠️ Ada catatan eksekusi: {proc.stderr.strip()}"

                # Extract voice reply if present
                voice_text = None
                if "<<<VOICE_REPLY>>>" in raw_output:
                    m = re.search(r'<<<VOICE_REPLY>>>(.*?)<<<END_VOICE_REPLY>>>', raw_output, re.DOTALL)
                    if m:
                        voice_text = m.group(1).strip()
                        raw_output = re.sub(r'<<<VOICE_REPLY>>>.*?<<<END_VOICE_REPLY>>>', '', raw_output, flags=re.DOTALL).strip()

                return raw_output or "Tugas coding selesai tanpa catatan output.", voice_text
            except subprocess.TimeoutExpired:
                return f"⚠️ Eksekusi coding di project `{active_project}` melebihi batas waktu ({timeout} detik).", None
            except Exception as e:
                logger.error(f"Error executing coding task with agy: {e}")

        # 2. Fallback to CodeRunner or local Python execution
        from code_runner import CodeRunner
        return f"💡 Project `{active_project}` ({project_path}) aktif. Install 'agy' untuk pengerjaan coding otonom lengkap.", None

    def execute_task(
        self,
        prompt: str,
        user_id: int,
        persona: Optional[Dict[str, Any]] = None,
        voice_enabled: bool = False
    ) -> str:
        """Runs coding task and returns text reply."""
        p = persona or {"name": "Waifu", "archetype": "Companion & Coding Partner"}
        text, _ = self.execute_coding_task(user_id=user_id, prompt=prompt, persona=p, voice_enabled=voice_enabled)
        return text

    def execute_computer_task(
        self,
        prompt: str,
        user_id: int
    ) -> Tuple[str, Optional[str]]:
        """
        Executes a desktop computer use task via agent-desktop.
        Returns: (status_message, optional_screenshot_path)
        """
        lower = prompt.lower()
        if any(k in lower for k in ["screenshot", "tangkapan layar", "foto layar", "layar pc"]):
            ok, path = self.computer_engine.take_screenshot()
            if ok:
                return "📸 Ini tangkapan layar desktop kamu saat ini! 💕", path
            else:
                return f"⚠️ Gagal mengambil tangkapan layar: {path}", None

        # General computer control task
        result = self.computer_engine.execute_computer_task(prompt)
        # Check if screenshot was created
        ok, path = self.computer_engine.take_screenshot()
        return result, path if ok else None


# Global singleton
_GLOBAL_CODING_ENGINE: Optional[CodingEngine] = None


def get_coding_engine() -> CodingEngine:
    global _GLOBAL_CODING_ENGINE
    if _GLOBAL_CODING_ENGINE is None:
        _GLOBAL_CODING_ENGINE = CodingEngine()
    return _GLOBAL_CODING_ENGINE

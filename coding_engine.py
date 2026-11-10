"""
coding_engine.py - Autonomous AI Coding & Work Assistant Engine
Empowers Waifu on Telegram to act as a senior coding partner and work assistant
operating within the selected project workspace using Google Antigravity CLI (`agy`)
and Computer Use (`agent-desktop`).
"""

import os
import re
import sys
import time
import shutil
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional, Tuple, List

from project_manager import get_project_manager
from computer_use_engine import get_computer_use_engine
from project_vault import get_project_vault
from architecture_generator import ensure_project_architecture

logger = logging.getLogger(__name__)

CODING_TRIGGERS = [
    # 1. Action verbs with programming nouns / file types
    r'\b(bikin|buat|buatkan|tulis|tambah|tambahkan|tambahin|pasang|pasangkan|install|integrasikan|implementasikan|kembangkan|kerjakan|selesaikan|koding|kodingin|ngoding|coding|ubah|ganti|update|edit|refactor|fix|perbaiki|benerin|debug|analisa|review|rapikan|desain|design|styling)\s+([\w\-\.]+\.(?:html|css|js|jsx|ts|tsx|py|json|md|sql|vue|svelte|php|go|rs|java|sh|bat|ps1)|kode|code|program|script|file|aplikasi|app|web|website|halaman|page|landing page|navbar|header|footer|sidebar|button|tombol|form|modal|card|ui|ux|tampilan|endpoint|api|route|router|database|db|tabel|table|model|controller|service|fitur|feature|fungsi|function|komponen|component|backend|frontend|auth|login|register|crud|middleware|migration|query|layout|view|handler|html|css|javascript|python|dependensi|dependency|dependencies|library|lib|package|paket|modul|module|tailwind|tailwindcss|bootstrap)\b',
    # 2. File and coding activity phrases
    r'\b(buat file|baca file|edit file|tambah file|hapus file|update file|bikin file|save file)\b',
    r'\b(coding|programmer|ngoding|scripting|kodingin|tolong ngoding|tolong koding|bantu koding|bantu ngoding|kerjain kodingan|lanjutin kodingan|lanjutkan kodingan|source\s*code|pull\s*request)\b',
    # 3. Debugging & fixing
    r'\b(debug|fix|perbaiki|benerin)\s+(kode|code|script|bug|error|issue|program|web|app|tampilan|layout|halaman|fungsi|endpoint|api)\b',
    r'\b(refactor|optimize|analisa code|review code|code review)\b',
    # 4. Git and terminal dev operations
    r'\b(git\s+(status|diff|add|commit|push|pull|log|branch|checkout|merge))\b',
    r'\b(npm|pnpm|yarn|bun|pip|cargo|python|node|bash|powershell|docker)\s+',
    r'\b(bikin web|bikin app|landing page|endpoint|api|database|bikin backend|bikin frontend)\b',
    r'\b(run test|unit test|pytest|unittest|benchmark|test suite)\b',
    # 5. Project running and live preview
    r'\b(run|jalankan|start|nyalakan|preview|tes)\s+(project|proyek|web|server|app|aplikasi)\b',
    r'\b(coba\s+run|coba\s+preview)\b',
    r'\b(coba\s+jalankan|coba\s+start)\s+(project|proyek|web|server|app|aplikasi)?\b',
    r'\b(live\s+preview|link\s+preview)\b',
    # 6. Specific project scope targeting
    r'\bdi\s+project\s+[\w\-\.]+\s+(tolong|coba|buat|bikin|tambah|kerjakan|update|fix)\b'
]

# Conversational expressions that should NEVER falsely trigger coding tasks
CONVERSATIONAL_EXCLUSIONS = [
    r'\b(foto|pap|selfie|pose|senyum|wajah|muka|baju|outfit|pakaian|telanjang|nude|cantik|sayang|kangen|cinta)\b',
    r'\b(kamu lagi|kamu sedang|lagi ngapain|lagi apa|udah makan|mau makan|sarapan|kopi|teh|masak|bikin kopi|bikin teh)\b',
    r'\b(coba lihat|lihat dong|liat dong|coba liat)\b'
]

COMPUTER_USE_TRIGGERS = [
    r'\b(screenshot|tangkapan layar|foto layar|screen pc)\b',
    r'\b(buka aplikasi|tutup aplikasi|list aplikasi|running apps)\b',
    r'\b(desktop|computer use|klik tombol|ketik di|buka browser|buka chrome|buka edge|buka web|buka instagram)\b',
    r'\b(profile chrome|profil chrome|profil browser|browser profile)\b'
]


def snapshot_project_files(project_path: str, max_depth: int = 4) -> Dict[str, float]:
    """Takes a lightweight snapshot of file modification times in workspace."""
    snapshot: Dict[str, float] = {}
    try:
        root_abs = os.path.abspath(project_path)
        for root, dirs, files in os.walk(root_abs):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", ".waifu", "dist", "build", ".venv", "venv", ".idea", ".vscode")]
            rel_root = os.path.relpath(root, root_abs)
            depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
            if depth > max_depth:
                continue
            for f in files:
                if f in (".DS_Store", "thumbs.db", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
                    continue
                full_p = os.path.join(root, f)
                try:
                    rel_p = os.path.relpath(full_p, root_abs).replace("\\", "/")
                    snapshot[rel_p] = os.path.getmtime(full_p)
                except Exception:
                    pass
    except Exception:
        pass
    return snapshot


def diff_project_snapshots(before: Dict[str, float], after: Dict[str, float]) -> Tuple[List[str], List[str]]:
    """Returns (created_files, modified_files)."""
    created: List[str] = []
    modified: List[str] = []
    for f, mtime in after.items():
        if f not in before:
            created.append(f)
        elif mtime > before[f] + 0.1:
            modified.append(f)
    return created, modified


class CodingEngine:
    """Handles autonomous coding tasks, project execution, and desktop assistance."""

    def __init__(self, project_manager: Optional[Any] = None, computer_use_engine: Optional[Any] = None):
        self.project_manager = project_manager or get_project_manager()
        self.computer_engine = computer_use_engine or get_computer_use_engine()

    def is_coding_intent(self, text: str, user_id: Optional[int] = None) -> bool:
        """Determines if user input is asking for programming, coding, or workspace file work."""
        lower = text.lower().strip()

        # Explicit commands or prefixes are 100% coding intents
        if re.match(r'^/(?:code|dev|ngoding|coding)\b', lower) or re.match(r'^(?:code|dev|coding):\s*', lower):
            return True

        # Guard against conversational / romantic / selfie false-positives
        for excl in CONVERSATIONAL_EXCLUSIONS:
            if re.search(excl, lower) and not re.search(r'\b(kode|code|script|project|proyek|html|website|aplikasi|program|terminal|file|navbar|tombol|button|api|database|bug|error)\b', lower):
                return False

        for pattern in CODING_TRIGGERS:
            if re.search(pattern, lower):
                return True

        # If user has an active dedicated project (not 'general'), detect broader contextual programming instructions
        if user_id:
            try:
                active_p = self.project_manager.get_active_project(user_id)
                if active_p and active_p != "general":
                    contextual_triggers = [
                        r'\b(tambah|tambahkan|ganti|ubah|rapikan|perbaiki|buatkan|bikin|benerin)\s+.*(halaman|warna|tampilan|teks|judul|isi|layout|style|css|desain|design|font|icon|data)\b',
                        r'\b(lanjutkan|lanjutin|kerjakan|selesaikan)\s+(task|tugas|kodingan|projek|project|fitur)\b'
                    ]
                    for c_pat in contextual_triggers:
                        if re.search(c_pat, lower):
                            return True
            except Exception:
                pass

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
        Injects project memory vault and ARCHITECTURE.md blueprint.
        Returns: (response_text, optional_voice_note_text)
        """
        active_project = self.project_manager.get_active_project(user_id)
        project_path = self.project_manager.get_active_project_path(user_id)
        os.makedirs(project_path, exist_ok=True)

        # 1. Ensure ARCHITECTURE.md and Project Memory Vault are up-to-date
        try:
            ensure_project_architecture(project_path, active_project)
        except Exception as e_arch:
            logger.warning(f"Architecture inspection warning: {e_arch}")

        vault = get_project_vault(project_path, active_project)
        project_context_str = vault.get_prompt_context(max_chars=12000)

        persona_name = persona.get("name", "Waifu")
        persona_archetype = persona.get("archetype", "Companion & Coding Partner")

        # Instruction for dual-role: Keep persona warm & affectionate, but be a decisive senior developer
        system_instruction = (
            f"You are {persona_name} ({persona_archetype}), an intelligent, affectionate AI companion "
            f"and an expert senior software developer working alongside the user.\n"
            f"Active Project: '{active_project}'\n"
            f"Workspace Path: '{project_path}'\n\n"
            f"{project_context_str}\n\n"
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

        # Open-Design integration for UI/UX & frontend requests
        applied_design_style = None
        try:
            from open_design_engine import get_open_design_engine
            ode = get_open_design_engine()
            enhanced_user_prompt, applied_design_style = ode.enhance_coding_prompt(prompt)
            if applied_design_style:
                ode.scaffold_design_tokens(applied_design_style, project_path)
        except Exception as e_od:
            logger.warning(f"Open-Design enhancement error: {e_od}")
            enhanced_user_prompt = prompt

        full_prompt = f"{system_instruction}{voice_instruction}\n\nUser Request: {enhanced_user_prompt}"

        # 1. Try Google Antigravity CLI (agy)
        agy_bin = shutil.which("agy") or shutil.which("agy.cmd")
        if agy_bin:
            # Handle Windows command length limit (>8000 chars) by piping via task instruction file
            temp_task_file = None
            if len(full_prompt) > 7500:
                try:
                    task_fname = f".waifu_task_{int(time.time())}.md"
                    temp_task_file = os.path.join(project_path, task_fname)
                    with open(temp_task_file, "w", encoding="utf-8") as f:
                        f.write(full_prompt)
                    exec_prompt = (
                        f"Please read and completely fulfill the coding instructions and project requirements "
                        f"stored in the workspace file: '{task_fname}'. Once done, provide the required summary response."
                    )
                except Exception as e_file:
                    logger.warning(f"Could not create buffer prompt file: {e_file}")
                    exec_prompt = full_prompt[:7500]
            else:
                exec_prompt = full_prompt

            cmd = [agy_bin, "-p", exec_prompt, "--dangerously-skip-permissions"]
            before_snap = snapshot_project_files(project_path)
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
                after_snap = snapshot_project_files(project_path)
                created_files, modified_files = diff_project_snapshots(before_snap, after_snap)
                all_touched = created_files + modified_files

                raw_output = proc.stdout.strip()
                if not raw_output and proc.stderr:
                    raw_output = f"⚠️ Catatan eksekusi: {proc.stderr.strip()}"

                # Clean up buffer file if created
                if temp_task_file and os.path.exists(temp_task_file):
                    try:
                        os.remove(temp_task_file)
                    except Exception:
                        pass

                # Extract voice reply if present
                voice_text = None
                if "<<<VOICE_REPLY>>>" in raw_output:
                    m = re.search(r'<<<VOICE_REPLY>>>(.*?)<<<END_VOICE_REPLY>>>', raw_output, re.DOTALL)
                    if m:
                        voice_text = m.group(1).strip()
                        raw_output = re.sub(r'<<<VOICE_REPLY>>>.*?<<<END_VOICE_REPLY>>>', '', raw_output, flags=re.DOTALL).strip()

                # Automatically record task completion in Project Memory Vault with real touched files
                clean_summary = prompt[:100] + ("..." if len(prompt) > 100 else "")
                try:
                    vault.add_completed_task(f"Coding task: {clean_summary}", files_touched=all_touched)
                except Exception as e_mem:
                    logger.warning(f"Failed to record completed task to vault: {e_mem}")

                final_text = raw_output or ("Tugas coding selesai diproses di project." if all_touched else "⚠️ Tugas telah dijalankan namun belum ada perubahan file di workspace.")

                # Append real files changed as proof of work
                if all_touched:
                    file_lines = []
                    if created_files:
                        for cf in created_files[:8]:
                            file_lines.append(f"• `{cf}` *(baru)*")
                    if modified_files:
                        for mf in modified_files[:8]:
                            file_lines.append(f"• `{mf}` *(diperbarui)*")
                    final_text += "\n\n📁 **File yang Berhasil Dikerjakan:**\n" + "\n".join(file_lines)
                if applied_design_style:
                    final_text += f"\n\n🎨 *Design System:* `Open-Design ({applied_design_style.title()})`"

                # Auto-detect and launch live preview server ONLY if prompt asks for web / frontend / server / preview / app
                is_web_or_preview_task = any(
                    k in prompt.lower() for k in [
                        "web", "html", "landing page", "frontend", "ui", "ux", "halaman",
                        "preview", "run", "jalankan", "start", "server", "app", "aplikasi", "port"
                    ]
                )
                if is_web_or_preview_task:
                    try:
                        from project_server_manager import get_project_server_manager
                        psm = get_project_server_manager()
                        preview_info = psm.start_preview_server(active_project, project_path)
                        if preview_info:
                            p_url = preview_info.get("url")
                            p_port = preview_info.get("port")
                            final_text += (
                                f"\n\n🌐 **Live Web Preview (Port {p_port}):**\n"
                                f"👉 [{p_url}]({p_url})\n"
                                f"Direct Link: {p_url}\n"
                                f"*(Web server sudah otomatis menyala di background PC kamu!)*"
                            )
                    except Exception as e_srv:
                        logger.warning(f"Error starting preview server: {e_srv}")

                return final_text, voice_text
            except subprocess.TimeoutExpired:
                if temp_task_file and os.path.exists(temp_task_file):
                    try:
                        os.remove(temp_task_file)
                    except Exception:
                        pass
                return f"⚠️ Eksekusi coding di project `{active_project}` melebihi batas waktu ({timeout} detik).", None
            except Exception as e:
                logger.error(f"Error executing coding task with agy: {e}")
                if temp_task_file and os.path.exists(temp_task_file):
                    try:
                        os.remove(temp_task_file)
                    except Exception:
                        pass

        # 2. Fallback
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
        # Suppress automatic desktop screenshot for conversational menu / profile queries
        if any(marker in result for marker in ["profil browser nih", "Daftar Profil Browser", "Profil default browser", "Selalu Tanya"]):
            return result, None
        ok, path = self.computer_engine.take_screenshot()
        return result, path if ok else None


# Global singleton
_GLOBAL_CODING_ENGINE: Optional[CodingEngine] = None


def get_coding_engine() -> CodingEngine:
    global _GLOBAL_CODING_ENGINE
    if _GLOBAL_CODING_ENGINE is None:
        _GLOBAL_CODING_ENGINE = CodingEngine()
    return _GLOBAL_CODING_ENGINE

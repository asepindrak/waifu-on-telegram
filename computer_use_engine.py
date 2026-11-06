"""
computer_use_engine.py - Autonomous Desktop Control & Computer Use
Interfaces with Vercel Labs 'agent-desktop' (https://github.com/vercel-labs/agent-desktop)
and Google Chrome profile management, allowing Waifu on Telegram to see and operate desktop
applications, launch specific browser profiles, click UI elements, and automate PC tasks.
"""

import os
import sys
import json
import shutil
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


class ComputerUseEngine:
    """Manages desktop UI inspection, actions, snapshots via agent-desktop, and browser profile switching."""

    def __init__(self, agent_desktop_bin: Optional[str] = None):
        self.bin_path = agent_desktop_bin or self._find_binary()
        self.temp_dir = os.path.join(tempfile.gettempdir(), "waifu_desktop")
        os.makedirs(self.temp_dir, exist_ok=True)

    def _find_binary(self) -> str:
        """Finds agent-desktop executable in PATH or npm global locations."""
        for name in ["agent-desktop", "agent-desktop.cmd", "agent-desktop-win32-x64.exe"]:
            found = shutil.which(name)
            if found:
                return found

        # Common Windows npm global folder
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA", "")
            npm_bin = os.path.join(appdata, "npm", "agent-desktop.cmd")
            if os.path.isfile(npm_bin):
                return npm_bin

        return "agent-desktop"

    def is_available(self) -> bool:
        """Returns True if agent-desktop is installed and callable."""
        try:
            res = subprocess.run([self.bin_path, "version"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Runs agent-desktop status and returns parsed status dictionary."""
        try:
            res = subprocess.run(
                [self.bin_path, "status"],
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout.strip())
        except Exception as e:
            logger.debug(f"agent-desktop status call failed: {e}")

        return {
            "ok": False,
            "installed": self.is_available(),
            "binary": self.bin_path
        }

    def run_command(self, args: List[str], timeout: int = 20) -> Tuple[bool, Any]:
        """Executes an agent-desktop subcommand and parses the resulting JSON envelope."""
        cmd = [self.bin_path] + args
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            raw = proc.stdout.strip()
            if not raw and proc.stderr:
                return False, {"error": proc.stderr.strip()}

            try:
                data = json.loads(raw)
                return bool(data.get("ok", proc.returncode == 0)), data
            except json.JSONDecodeError:
                return proc.returncode == 0, {"raw": raw}
        except subprocess.TimeoutExpired:
            return False, {"error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return False, {"error": str(e)}

    def take_screenshot(self, app: Optional[str] = None, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Takes a screenshot of primary display or specific application window.
        Returns: (success, file_path_or_error)
        """
        if not output_path:
            import uuid
            output_path = os.path.join(self.temp_dir, f"screen_{uuid.uuid4().hex[:8]}.png")

        args = ["screenshot", "--screen", "0", output_path]
        if app:
            args = ["screenshot", "--app", app, output_path]

        ok, res = self.run_command(args, timeout=15)
        if ok and os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            return True, output_path

        # Fallback to PIL ImageGrab if agent-desktop screenshot failed
        try:
            from PIL import ImageGrab
            im = ImageGrab.grab()
            im.save(output_path)
            if os.path.isfile(output_path):
                return True, output_path
        except Exception as e_pil:
            logger.debug(f"PIL screenshot fallback failed: {e_pil}")

        err_msg = res.get("error", {}).get("message", "Gagal mengambil tangkapan layar") if isinstance(res, dict) else str(res)
        return False, err_msg

    def take_snapshot(self, app: Optional[str] = None) -> Tuple[bool, Any]:
        """Captures accessibility tree as structured JSON with @ref IDs."""
        args = ["snapshot", "--compact", "-i"]
        if app:
            args.extend(["--app", app])
        return self.run_command(args, timeout=15)

    def click(self, ref_or_selector: str, headed: bool = False) -> Tuple[bool, str]:
        """Clicks an element by @ref ID or role:text selector."""
        args = ["click", ref_or_selector]
        if headed:
            args.append("--headed")
        ok, res = self.run_command(args, timeout=10)
        return ok, str(res)

    def type_text(self, ref: str, text: str) -> Tuple[bool, str]:
        """Inserts text into a text target."""
        args = ["type", ref, text]
        ok, res = self.run_command(args, timeout=10)
        return ok, str(res)

    def press_key(self, key_combo: str) -> Tuple[bool, str]:
        """Sends key combination (e.g. return, escape, ctrl+c, alt+tab)."""
        args = ["press", key_combo]
        ok, res = self.run_command(args, timeout=10)
        return ok, str(res)

    def launch_app(self, app_name: str) -> Tuple[bool, str]:
        """Launches an application and waits for its process to start."""
        args = ["launch", app_name, "--activate"]
        ok, res = self.run_command(args, timeout=15)
        return ok, str(res)

    def list_running_apps(self) -> List[str]:
        """Lists active desktop application names."""
        ok, res = self.run_command(["list-apps"], timeout=10)
        if ok and isinstance(res, dict):
            apps = res.get("data", [])
            if isinstance(apps, list):
                return [a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in apps]

        # Windows tasklist fallback
        if sys.platform == "win32":
            try:
                proc = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=5)
                procs = set()
                for line in proc.stdout.splitlines():
                    parts = line.split('","')
                    if parts:
                        name = parts[0].strip('"')
                        if name.endswith(".exe"):
                            procs.add(name.replace(".exe", ""))
                return sorted(list(procs))[:20]
            except Exception:
                pass

        return []

    def list_chrome_profiles(self) -> List[Dict[str, str]]:
        """
        Scans Google Chrome User Data to identify available profiles with user names, emails, and directory keys.
        """
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        local_state_file = os.path.join(local_app_data, "Google", "Chrome", "User Data", "Local State")
        if not os.path.exists(local_state_file):
            return []

        profiles = []
        try:
            with open(local_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            for folder, info in info_cache.items():
                profiles.append({
                    "folder": folder,
                    "name": info.get("name", folder),
                    "email": info.get("user_name", "")
                })
        except Exception as e:
            logger.warning(f"Error reading Chrome Local State: {e}")
        return profiles

    def launch_chrome(self, url: str = "https://google.com", profile_query: Optional[str] = None) -> Tuple[bool, str]:
        """
        Launches Google Chrome targeting a specific user profile (by name, email, or folder ID).
        Example: launch_chrome("https://instagram.com", profile_query="Niziiro")
        """
        chrome_exe = shutil.which("chrome") or shutil.which("chrome.exe")
        if not chrome_exe:
            # Common paths on Windows
            for path in [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
            ]:
                if os.path.isfile(path):
                    chrome_exe = path
                    break

        if not chrome_exe:
            return False, "Google Chrome executable tidak ditemukan di sistem."

        target_folder = "Default"
        profile_label = "Default"
        all_profiles = self.list_chrome_profiles()

        # Check configured env fallback if no query given
        cfg_pref = os.environ.get("CHROME_DEFAULT_PROFILE", "").strip()
        query = profile_query or cfg_pref

        if query:
            q_lower = query.lower()
            for p in all_profiles:
                if (q_lower == p["folder"].lower() or 
                    q_lower in p["name"].lower() or 
                    (p["email"] and q_lower in p["email"].lower())):
                    target_folder = p["folder"]
                    profile_label = f"{p['name']} ({p['email']})" if p['email'] else p['name']
                    break

        cmd = [chrome_exe, f"--profile-directory={target_folder}", url]
        try:
            creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            subprocess.Popen(cmd, creationflags=creationflags)
            return True, f"Membuka Chrome dengan Profil '{profile_label}' (Folder: `{target_folder}`) ke `{url}`"
        except Exception as e:
            return False, f"Gagal membuka Chrome: {e}"

    def execute_computer_task(self, prompt: str, agy_runner=None) -> str:
        """
        Executes a high-level natural language computer use task
        by combining agent-desktop with Antigravity / LLM reasoning and Chrome profile routing.
        """
        lower = prompt.lower()

        # 1. Direct Chrome Profile Inspection
        if any(k in lower for k in ["profile chrome", "profil chrome", "list profile", "daftar profile"]):
            profs = self.list_chrome_profiles()
            if profs:
                lines = [
                    "🌐 **Daftar Profil Google Chrome di PC Kamu:**",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ]
                for p in profs:
                    email_str = f" • `{p['email']}`" if p['email'] else ""
                    lines.append(f"👤 **{p['name']}** (Folder: `{p['folder']}`){email_str}")
                lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
                lines.append("💡 *Contoh perintah:* `buka chrome profil Niziiro` atau `buka instagram di profile 1`")
                return "\n".join(lines)
            return "Tidak ada profil Google Chrome terdeteksi."

        # 2. Direct Chrome Launch with Profile
        if any(act in lower for act in ["buka", "launch", "open", "jalankan"]) and any(br in lower for br in ["chrome", "browser", "instagram"]):
            all_profs = self.list_chrome_profiles()
            target_prof = None
            for p in all_profs:
                if (p['name'].lower() in lower or 
                    p['folder'].lower() in lower or 
                    (p['email'] and p['email'].split('@')[0].lower() in lower)):
                    target_prof = p['folder']
                    break

            target_url = "https://instagram.com" if "instagram" in lower else "https://google.com"
            # Extract custom URL if present
            import re
            url_match = re.search(r'https?://[^\s]+', prompt)
            if url_match:
                target_url = url_match.group(0)

            ok, msg = self.launch_chrome(url=target_url, profile_query=target_prof)
            return msg

        if not self.is_available():
            return "⚠️ Tool 'agent-desktop' belum terpasang. Install via: npm install -g agent-desktop"

        # Take screenshot of current state
        ok_screen, screen_path = self.take_screenshot()
        screen_note = f" (Screenshot tersimpan di: {screen_path})" if ok_screen else ""

        # Build prompt for agy
        cli_prompt = (
            "You have access to the computer use CLI 'agent-desktop'.\n"
            "Here is the user request to operate the computer:\n"
            f"{prompt}\n\n"
            "Execute the task using agent-desktop commands (snapshot, find, click, type, press, launch) "
            "and summarize what you did clearly."
        )

        if agy_runner:
            return agy_runner(cli_prompt)

        # Fallback to direct agy execution if available
        if shutil.which("agy"):
            try:
                res = subprocess.run(
                    ["agy", "-p", cli_prompt, "--dangerously-skip-permissions"],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    encoding="utf-8",
                    errors="replace"
                )
                return res.stdout.strip() or f"Tugas selesai.{screen_note}"
            except Exception as e:
                return f"Error executing task with agy: {e}"

        return f"Screenshot desktop berhasil diambil{screen_note}. Siap menerima instruksi lanjutan."


# Global singleton
_GLOBAL_COMPUTER_ENGINE: Optional[ComputerUseEngine] = None


def get_computer_use_engine() -> ComputerUseEngine:
    global _GLOBAL_COMPUTER_ENGINE
    if _GLOBAL_COMPUTER_ENGINE is None:
        _GLOBAL_COMPUTER_ENGINE = ComputerUseEngine()
    return _GLOBAL_COMPUTER_ENGINE

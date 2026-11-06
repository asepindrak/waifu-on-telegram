"""
computer_use_engine.py - Autonomous Desktop Control & Computer Use
Interfaces with Vercel Labs 'agent-desktop' (https://github.com/vercel-labs/agent-desktop)
and multi-browser profile management (Google Chrome, Microsoft Edge, Brave on Windows, macOS, Linux),
allowing Waifu on Telegram to see and operate desktop applications, launch specific browser profiles,
click UI elements, and automate PC tasks.
"""

import os
import re
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

    def list_browser_profiles(self) -> List[Dict[str, str]]:
        """
        Dynamically scans for installed Chromium browsers (Google Chrome, Microsoft Edge, Brave)
        across Windows, macOS, and Linux, and extracts user profiles with names, emails, and folders.
        """
        candidates = []
        if sys.platform == "win32":
            candidates.append(("Google Chrome", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State"), "chrome"))
            candidates.append(("Microsoft Edge", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Local State"), "msedge"))
            candidates.append(("Brave Browser", os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Local State"), "brave"))
        elif sys.platform == "darwin":
            candidates.append(("Google Chrome", os.path.expanduser("~/Library/Application Support/Google/Chrome/Local State"), "google-chrome"))
            candidates.append(("Microsoft Edge", os.path.expanduser("~/Library/Application Support/Microsoft Edge/Local State"), "microsoft-edge"))
            candidates.append(("Brave Browser", os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser/Local State"), "brave"))
        else:
            candidates.append(("Google Chrome", os.path.expanduser("~/.config/google-chrome/Local State"), "google-chrome"))
            candidates.append(("Chromium", os.path.expanduser("~/.config/chromium/Local State"), "chromium"))
            candidates.append(("Microsoft Edge", os.path.expanduser("~/.config/microsoft-edge/Local State"), "microsoft-edge"))
            candidates.append(("Brave Browser", os.path.expanduser("~/.config/BraveSoftware/Brave-Browser/Local State"), "brave"))

        all_profiles = []
        for b_name, state_file, b_cmd in candidates:
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    info_cache = data.get("profile", {}).get("info_cache", {})
                    for folder, info in info_cache.items():
                        all_profiles.append({
                            "browser": b_name,
                            "browser_cmd": b_cmd,
                            "folder": folder,
                            "name": info.get("name", folder),
                            "email": info.get("user_name", "")
                        })
                except Exception as e:
                    logger.debug(f"Error reading {b_name} Local State: {e}")

        return all_profiles

    def list_chrome_profiles(self) -> List[Dict[str, str]]:
        """Backwards compatibility alias for list_browser_profiles."""
        return self.list_browser_profiles()

    def get_default_browser_profile(self) -> Optional[str]:
        """Returns the configured default browser profile from environment."""
        pref = os.environ.get("CHROME_DEFAULT_PROFILE", "").strip()
        return pref if pref else None

    def set_default_browser_profile(self, profile_key: str):
        """Sets the default browser profile in runtime environment."""
        os.environ["CHROME_DEFAULT_PROFILE"] = profile_key.strip()

    def launch_browser(self, url: str = "https://google.com", profile_query: Optional[str] = None) -> Tuple[bool, str]:
        """
        Launches Google Chrome, Microsoft Edge, or Brave targeting a specific user profile.
        Example: launch_browser("https://instagram.com", profile_query="Niziiro")
        """
        all_profiles = self.list_browser_profiles()

        # Check configured env fallback if no query given
        cfg_pref = self.get_default_browser_profile()
        query = profile_query or cfg_pref

        target_browser_cmd = "chrome"
        target_folder = "Default"
        profile_label = "Default"

        if query and query.lower() not in ("ask", "tanya", "auto"):
            q_lower = query.lower()
            for p in all_profiles:
                if (q_lower == p["folder"].lower() or 
                    q_lower in p["name"].lower() or 
                    (p["email"] and q_lower in p["email"].lower())):
                    target_browser_cmd = p.get("browser_cmd", "chrome")
                    target_folder = p["folder"]
                    profile_label = f"{p['name']} ({p['email']})" if p['email'] else p['name']
                    break
        elif all_profiles:
            # Pick first found profile as default fallback
            p0 = all_profiles[0]
            target_browser_cmd = p0.get("browser_cmd", "chrome")
            target_folder = p0["folder"]
            profile_label = f"{p0['name']} ({p0['email']})" if p0['email'] else p0['name']

        # Find executable path for target browser
        browser_exe = shutil.which(target_browser_cmd) or shutil.which(f"{target_browser_cmd}.exe")
        if not browser_exe:
            if target_browser_cmd in ("chrome", "google-chrome"):
                for path in [
                    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
                ]:
                    if os.path.isfile(path):
                        browser_exe = path
                        break
            elif target_browser_cmd in ("msedge", "edge"):
                for path in [
                    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")
                ]:
                    if os.path.isfile(path):
                        browser_exe = path
                        break

        # Fallback to any available browser if specific wasn't found
        if not browser_exe:
            for alt in ["chrome.exe", "msedge.exe", "brave.exe"]:
                f = shutil.which(alt)
                if f:
                    browser_exe = f
                    break

        if not browser_exe:
            return False, "Browser (Chrome/Edge) tidak ditemukan di sistem."

        cmd = [browser_exe, f"--profile-directory={target_folder}", url]
        try:
            creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            subprocess.Popen(cmd, creationflags=creationflags)
            return True, f"Membuka browser dengan Profil '{profile_label}' (Folder: `{target_folder}`) ke `{url}`"
        except Exception as e:
            return False, f"Gagal membuka browser: {e}"

    def launch_chrome(self, url: str = "https://google.com", profile_query: Optional[str] = None) -> Tuple[bool, str]:
        """Backwards compatibility alias for launch_browser."""
        return self.launch_browser(url=url, profile_query=profile_query)

    def execute_computer_task(self, prompt: str, agy_runner=None) -> str:
        """
        Executes a high-level natural language computer use task
        by combining agent-desktop with Antigravity / LLM reasoning and Chrome profile routing.
        """
        lower = prompt.lower()

        # 1. Direct Browser Profile Inspection
        if any(k in lower for k in ["profile chrome", "profil chrome", "list profile", "daftar profile", "profile browser", "profil browser"]):
            profs = self.list_browser_profiles()
            if profs:
                cur_def = self.get_default_browser_profile() or "Belum Disetel (Tanya/Default)"
                lines = [
                    "🌐 **Daftar Profil Browser yang Terdeteksi di PC Ini:**",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"⭐ **Default Saat Ini:** `{cur_def}`\n"
                ]
                for p in profs:
                    email_str = f" • `{p['email']}`" if p['email'] else ""
                    lines.append(f"👤 **{p['name']}** [{p['browser']}] (Folder: `{p['folder']}`){email_str}")
                lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
                lines.append("💡 *Contoh perintah:* `buka chrome profil Niziiro` atau `jadikan profil Niziiro default`")
                return "\n".join(lines)
            return "Tidak ada profil browser terdeteksi di sistem ini."

        # 2. Change Default Profile via Chat
        # e.g.: "jadikan profil Niziiro default", "set default profile chrome ke Profile 1", "ganti profile default ke adens"
        if any(k in lower for k in ["jadikan profil", "set default profile", "ganti default profile", "set profil default"]):
            all_profs = self.list_browser_profiles()
            matched = None
            for p in all_profs:
                if (p['name'].lower() in lower or 
                    p['folder'].lower() in lower or 
                    (p['email'] and p['email'].split('@')[0].lower() in lower)):
                    matched = p
                    break
            if matched:
                self.set_default_browser_profile(matched['folder'])
                # Also save to .env if writable
                from setup import read_env, write_env
                try:
                    env_data = read_env()
                    env_data["CHROME_DEFAULT_PROFILE"] = matched['folder']
                    write_env(env_data)
                except Exception:
                    pass
                return f"✅ Profil default browser berhasil diubah ke **{matched['name']}** (`{matched['folder']}`)!"
            elif "tanya" in lower or "ask" in lower:
                self.set_default_browser_profile("ask")
                return "✅ Diatur ke mode **Selalu Tanya**: Waifu akan bertanya profil mana yang ingin dibuka setiap kali kamu meminta membuka browser!"

        # 3. Direct Browser Launch with Profile or Interactive Check
        if any(act in lower for act in ["buka", "launch", "open", "jalankan"]) and any(br in lower for br in ["chrome", "browser", "instagram", "web"]):
            all_profs = self.list_browser_profiles()
            target_prof = None
            for p in all_profs:
                if (p['name'].lower() in lower or 
                    p['folder'].lower() in lower or 
                    (p['email'] and p['email'].split('@')[0].lower() in lower)):
                    target_prof = p['folder']
                    break

            target_url = "https://instagram.com" if "instagram" in lower else "https://google.com"
            url_match = re.search(r'https?://[^\s]+', prompt)
            if url_match:
                target_url = url_match.group(0)

            # Check if user did NOT specify a profile AND default is "ask" (or multiple profiles exist and no default set)
            cur_def = self.get_default_browser_profile()
            if not target_prof and (cur_def == "ask" or (not cur_def and len(all_profs) > 1)):
                # Return interactive prompt list
                lines = [
                    f"Di PC ini terdeteksi **{len(all_profs)} profil browser** nih! 🥰\n",
                    f"Kamu mau aku buka `{target_url}` pakai profil yang mana, sayang?"
                ]
                for p in all_profs:
                    lines.append(f"• **{p['name']}** (`{p['folder']}`) {p['email']}")
                lines.append(f"\n💡 *Balas dengan menyebut nama profilnya, misal: 'pakai {all_profs[0]['name']}'*")
                return "\n".join(lines)

            ok, msg = self.launch_browser(url=target_url, profile_query=target_prof)
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

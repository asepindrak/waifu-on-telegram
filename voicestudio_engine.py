import os
import sys
import time
import socket
import logging
import platform
import subprocess
import tempfile
import requests
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VOICESTUDIO_DIR = os.path.join(PROJECT_ROOT, "tools", "VoiceStudio")
DEFAULT_PORT = 3900
DEFAULT_URL = f"http://127.0.0.1:{DEFAULT_PORT}"


class VoiceStudioEngine:
    """
    Manages the local VoiceStudio backend (FastAPI daemon on port 3900).
    Provides headless TTS synthesis, auto-installation, process lifecycle management,
    and voice persona conditioning.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        install_dir: Optional[str] = None,
        port: Optional[int] = None
    ):
        self.port = port or int(os.environ.get("VOICESTUDIO_PORT", str(DEFAULT_PORT)))
        self.server_url = server_url or os.environ.get("VOICESTUDIO_URL", f"http://127.0.0.1:{self.port}").rstrip("/")
        self.install_dir = install_dir or os.environ.get("VOICESTUDIO_DIR", DEFAULT_VOICESTUDIO_DIR)
        self.default_model = os.environ.get("VOICESTUDIO_DEFAULT_MODEL", "omnivoice")

    # --- Installation & Status Detection ---

    def is_installed(self) -> bool:
        """Checks whether the VoiceStudio repository and backend files are present locally."""
        if not os.path.exists(self.install_dir):
            return False
        backend_main = os.path.join(self.install_dir, "backend", "main.py")
        backend_dir = os.path.join(self.install_dir, "backend")
        return os.path.exists(backend_main) or (os.path.isdir(backend_dir) and len(os.listdir(backend_dir)) > 0)

    def is_port_listening(self, timeout: float = 0.5) -> bool:
        """Verifies if the designated VoiceStudio port is actively open."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex(("127.0.0.1", self.port)) == 0

    def is_service_running(self) -> bool:
        """Checks if the VoiceStudio server is responsive."""
        if not self.is_port_listening():
            return False
        try:
            # Check OpenAPI / health endpoint
            resp = requests.get(f"{self.server_url}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        try:
            resp = requests.get(f"{self.server_url}/docs", timeout=2)
            return resp.status_code in (200, 307, 308)
        except Exception:
            return self.is_port_listening()

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic information about VoiceStudio."""
        installed = self.is_installed()
        running = self.is_service_running()
        return {
            "installed": installed,
            "running": running,
            "port": self.port,
            "url": self.server_url,
            "install_dir": self.install_dir,
            "default_model": self.default_model
        }

    # --- Process Lifecycle Management ---

    def start_service(self) -> bool:
        """Launches the VoiceStudio backend server in the background as a headless daemon."""
        if self.is_service_running():
            logger.info(f"VoiceStudio server is already running at {self.server_url}")
            return True

        if not self.is_installed():
            logger.warning(f"VoiceStudio is not installed at {self.install_dir}. Please install it first.")
            return False

        backend_main = os.path.join(self.install_dir, "backend", "main.py")
        logger.info(f"Starting VoiceStudio background service on port {self.port}...")

        cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(self.port)]

        popen_kwargs = {}
        if platform.system() == "Windows":
            # Detach process and suppress window
            popen_kwargs["creationflags"] = 0x08000000 | 0x00000200
        else:
            popen_kwargs["start_new_session"] = True

        try:
            subprocess.Popen(
                cmd,
                cwd=self.install_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **popen_kwargs
            )
            # Wait up to 5 seconds for initialization
            for _ in range(10):
                time.sleep(0.5)
                if self.is_port_listening():
                    logger.info(f"VoiceStudio service started successfully at {self.server_url}")
                    return True
        except Exception as e:
            logger.error(f"Failed to start VoiceStudio service: {e}")

        # Fallback command direct python execution
        try:
            fallback_cmd = [sys.executable, backend_main, "--port", str(self.port)]
            subprocess.Popen(
                fallback_cmd,
                cwd=self.install_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **popen_kwargs
            )
            time.sleep(2.0)
            return self.is_port_listening()
        except Exception as e2:
            logger.error(f"Fallback start command failed: {e2}")
            return False

    def stop_service(self) -> bool:
        """Terminates any background VoiceStudio process."""
        logger.info(f"Stopping VoiceStudio service (port {self.port})...")
        if platform.system() == "Windows":
            try:
                ps_cmd = (
                    f'Get-CimInstance Win32_Process | '
                    f'Where-Object {{ $_.CommandLine -like "*VoiceStudio*" -or $_.CommandLine -like "*backend.main:app*" }} | '
                    f'ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}'
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=10)
            except Exception as e:
                logger.debug(f"PowerShell termination error: {e}")
        else:
            try:
                subprocess.run(["pkill", "-f", "backend.main:app"], capture_output=True, timeout=5)
            except Exception:
                pass

        time.sleep(1.0)
        return not self.is_port_listening()

    def restart_service(self) -> bool:
        """Restarts the VoiceStudio background service."""
        self.stop_service()
        time.sleep(1.0)
        return self.start_service()

    # --- Installer ---

    def install(self, progress_callback=None) -> Tuple[bool, str]:
        """
        Clones VoiceStudio from GitHub and installs backend Python dependencies.
        """
        git_bin = shutil.which("git")
        if not git_bin:
            return False, "Git tidak ditemukan di sistem. Harap instal Git terlebih dahulu."

        os.makedirs(os.path.dirname(self.install_dir), exist_ok=True)

        if not self.is_installed():
            if progress_callback:
                progress_callback(f"📦 Mengunduh VoiceStudio dari repository resmi...")
            logger.info(f"Cloning VoiceStudio to {self.install_dir}...")
            try:
                cmd = [git_bin, "clone", "--depth", "1", "https://github.com/debpalash/VoiceStudio.git", self.install_dir]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if res.returncode != 0:
                    return False, f"Gagal mengkloning VoiceStudio: {res.stderr}"
            except Exception as e:
                return False, f"Terjadi kesalahan saat cloning VoiceStudio: {e}"

        # Install backend dependencies
        req_file = os.path.join(self.install_dir, "backend", "requirements.txt")
        if not os.path.exists(req_file):
            req_file = os.path.join(self.install_dir, "requirements.txt")

        if progress_callback:
            progress_callback("⚡ Menyiapkan dependensi Python backend VoiceStudio...")

        try:
            if os.path.exists(req_file):
                pip_cmd = [sys.executable, "-m", "pip", "install", "--no-warn-script-location", "-r", req_file]
            else:
                pip_cmd = [sys.executable, "-m", "pip", "install", "--no-warn-script-location", "fastapi", "uvicorn", "requests", "soundfile"]
            subprocess.run(pip_cmd, capture_output=True, text=True, timeout=300)
        except Exception as e:
            logger.warning(f"Pip dependency install notice: {e}")

        if self.is_installed():
            return True, "VoiceStudio berhasil dipasang!"
        return False, "Instalasi selesai namun file backend VoiceStudio belum lengkap."

    # --- Audio Synthesis ---

    def synthesize(
        self,
        text: str,
        voice_character: Optional[str] = None,
        voice_name: Optional[str] = None,
        model: Optional[str] = None,
        speed: float = 1.0,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Synthesizes spoken audio from text using VoiceStudio's backend API.
        Passes voice persona characteristics and parameters.
        Returns the path to the saved audio file on success, or None on failure.
        """
        if not text or not text.strip():
            return None

        clean_text = text.strip()
        target_model = model or self.default_model
        target_voice = voice_name or "runa"

        payload = {
            "model": target_model,
            "input": clean_text,
            "voice": target_voice,
            "response_format": "mp3",
            "speed": max(0.5, min(2.0, float(speed)))
        }
        if voice_character:
            payload["voice_character"] = voice_character
            payload["description"] = voice_character

        endpoint = f"{self.server_url}/v1/audio/speech"
        try:
            resp = requests.post(endpoint, json=payload, timeout=25)
            if resp.status_code == 200 and resp.content:
                out = output_path or tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
                with open(out, "wb") as f:
                    f.write(resp.content)
                logger.info(f"VoiceStudio successfully synthesized voice for '{clean_text[:30]}...' -> {out}")
                return out
            else:
                logger.warning(f"VoiceStudio returned HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"VoiceStudio synthesis request failed ({endpoint}): {e}")

        # Native fallback route: /api/tts/generate
        native_endpoint = f"{self.server_url}/api/tts/generate"
        try:
            resp_nat = requests.post(native_endpoint, json=payload, timeout=25)
            if resp_nat.status_code == 200 and resp_nat.content:
                out = output_path or tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
                with open(out, "wb") as f:
                    f.write(resp_nat.content)
                logger.info(f"VoiceStudio (native) synthesized voice for '{clean_text[:30]}...' -> {out}")
                return out
        except Exception as e2:
            logger.debug(f"VoiceStudio native route failed: {e2}")

        return None


# Module-level default engine singleton
voicestudio_engine = VoiceStudioEngine()

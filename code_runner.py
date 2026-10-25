import os
import sys
import subprocess
import tempfile
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class CodeRunner:
    """Executes Python code or shell commands safely with timeouts."""

    @staticmethod
    def execute_python(code: str, timeout: int = 30) -> Tuple[bool, str]:
        """Runs Python code in an isolated subprocess."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name

        try:
            res = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            out = res.stdout.strip()
            err = res.stderr.strip()
            output = out if out else err
            return res.returncode == 0, output or "(Eksekusi selesai tanpa output)"
        except subprocess.TimeoutExpired:
            return False, f"⚠️ Eksekusi melebihi batas waktu ({timeout} detik)."
        except Exception as e:
            return False, f"⚠️ Gagal mengeksekusi kode: {e}"
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    @staticmethod
    def execute_shell(cmd_str: str, timeout: int = 30) -> Tuple[bool, str]:
        """Runs shell/terminal command."""
        try:
            shell_cmd = ["powershell", "-NoProfile", "-Command", cmd_str] if sys.platform == "win32" else ["bash", "-c", cmd_str]
            res = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            out = res.stdout.strip()
            err = res.stderr.strip()
            return res.returncode == 0, out if out else err or "(Perintah selesai)"
        except subprocess.TimeoutExpired:
            return False, "⚠️ Perintah melebihi batas waktu."
        except Exception as e:
            return False, f"⚠️ Error menjalankan perintah: {e}"

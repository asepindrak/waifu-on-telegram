"""
project_server_manager.py - Autonomous Project Web Server & Live Preview Runner
Empowers Waifu on Telegram to automatically detect web/HTML files in created or edited projects,
launch a background HTTP server on a dynamically allocated open port, and provide live preview links.
Tracks all active preview servers and open ports.
"""

import os
import sys
import time
import json
import socket
import logging
import subprocess
import urllib.request
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ACTIVE_SERVERS_FILE = os.path.join(DATA_DIR, "active_preview_servers.json")

# Reserved system ports that should never be used for preview servers
RESERVED_PORTS = {8001, 8002, 8188, 5001, 3900}


def is_port_in_use(port: int) -> bool:
    """Checks if a local TCP port is already open/in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


def find_free_port(start_port: int = 8085, max_tries: int = 150) -> int:
    """Finds an available local port starting from start_port, avoiding system reserved ports."""
    port = start_port
    while port < (start_port + max_tries):
        if port not in RESERVED_PORTS and not is_port_in_use(port):
            return port
        port += 1

    # Fallback to OS assigned ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def detect_web_root(project_path: str) -> Optional[Tuple[str, str]]:
    """
    Scans project_path for HTML/web entry points.
    Returns: (target_directory_to_serve, relative_entry_file)
    """
    if not os.path.isdir(project_path):
        return None

    # 1. Direct index.html in project root
    if os.path.isfile(os.path.join(project_path, "index.html")):
        return (os.path.abspath(project_path), "index.html")

    # 2. Common frontend build directories
    for sub in ["dist", "build", "public", "out"]:
        candidate = os.path.join(project_path, sub)
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "index.html")):
            return (os.path.abspath(candidate), "index.html")

    # 3. Check subdirectories created inside project_path (sorted by newest first)
    subdirs = []
    try:
        for entry in os.scandir(project_path):
            if entry.is_dir() and not entry.name.startswith(".") and entry.name not in ["node_modules", "venv", ".git"]:
                subdirs.append(entry)
        subdirs.sort(key=lambda e: e.stat().st_mtime, reverse=True)

        for sdir in subdirs:
            if os.path.isfile(os.path.join(sdir.path, "index.html")):
                return (os.path.abspath(sdir.path), "index.html")
            # 1 level deeper
            for sub in ["dist", "build", "public"]:
                sub_deep = os.path.join(sdir.path, sub)
                if os.path.isdir(sub_deep) and os.path.isfile(os.path.join(sub_deep, "index.html")):
                    return (os.path.abspath(sub_deep), "index.html")
    except Exception as e:
        logger.warning(f"Error scanning web subdirs in {project_path}: {e}")

    # 4. Any .html file in project_path
    try:
        for entry in os.scandir(project_path):
            if entry.is_file() and entry.name.lower().endswith(".html"):
                return (os.path.abspath(project_path), entry.name)
    except Exception:
        pass

    return None


class ProjectServerManager:
    """Manages background preview web servers for coding projects."""

    def __init__(self, registry_file: str = ACTIVE_SERVERS_FILE):
        self.registry_file = registry_file
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)

    def _read_registry(self) -> Dict[str, Any]:
        if not os.path.exists(self.registry_file):
            return {}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_registry(self, data: Dict[str, Any]):
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to write server registry: {e}")

    def is_server_healthy(self, port: int, pid: Optional[int] = None) -> bool:
        """Verifies if an HTTP preview server is responding on localhost:port."""
        if not is_port_in_use(port):
            return False
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/", headers={"User-Agent": "WaifuPreviewCheck/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 301, 302, 304, 404)
        except Exception:
            # If port is open, consider it responsive
            return True

    def list_active_servers(self) -> List[Dict[str, Any]]:
        """Returns all currently live preview servers, pruning inactive ones."""
        registry = self._read_registry()
        active = []
        changed = False

        for key, s_info in list(registry.items()):
            port = s_info.get("port")
            pid = s_info.get("pid")
            if port and self.is_server_healthy(port, pid):
                active.append(s_info)
            else:
                del registry[key]
                changed = True

        if changed:
            self._write_registry(registry)

        return active

    def start_preview_server(self, project_name: str, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Detects web assets and starts a background HTTP preview server.
        If a server for this directory is already running, reuses it.
        Returns server details dict with live preview URL.
        """
        detected = detect_web_root(project_path)
        if not detected:
            return None

        web_dir, entry_file = detected
        norm_dir = os.path.normpath(web_dir)
        registry = self._read_registry()

        # 1. Check if a server is already running for this directory
        for s_key, s_info in registry.items():
            s_dir = os.path.normpath(s_info.get("dir", ""))
            s_port = s_info.get("port")
            if s_dir == norm_dir and s_port and self.is_server_healthy(s_port, s_info.get("pid")):
                logger.info(f"Reusing existing preview server for '{project_name}' on port {s_port}")
                return s_info

        # 2. Allocate free port
        port = find_free_port(start_port=8085)
        py_bin = sys.executable

        # 3. Spawn detached background process
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS

        cmd = [py_bin, "-m", "http.server", "-d", web_dir, str(port)]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creationflags
            )
        except Exception as e:
            logger.error(f"Failed to spawn http.server on port {port}: {e}")
            return None

        # Give it a brief moment to bind socket
        time.sleep(0.8)

        # 4. Verify server started
        if not self.is_server_healthy(port, proc.pid):
            logger.warning(f"Preview server on port {port} not responding immediately; registered anyway.")

        server_info = {
            "project": project_name,
            "port": port,
            "url": f"http://localhost:{port}/",
            "dir": web_dir,
            "entry_file": entry_file,
            "pid": proc.pid,
            "started_at": int(time.time())
        }

        server_key = f"{project_name}_{port}"
        registry[server_key] = server_info
        self._write_registry(registry)
        logger.info(f"✓ Started preview web server for '{project_name}' at http://localhost:{port}/ (PID: {proc.pid})")

        return server_info

    def stop_preview_server(self, identifier: str) -> bool:
        """Stops a preview server by project name or port."""
        registry = self._read_registry()
        target_key = None
        target_info = None

        for k, v in registry.items():
            if str(v.get("port")) == str(identifier) or v.get("project", "").lower() == str(identifier).lower():
                target_key = k
                target_info = v
                break

        if not target_info:
            return False

        pid = target_info.get("pid")
        if pid:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    os.kill(pid, 9)
            except Exception as e:
                logger.warning(f"Error terminating server pid {pid}: {e}")

        if target_key in registry:
            del registry[target_key]
            self._write_registry(registry)
        return True

    def format_active_servers_message(self) -> str:
        """Formats active servers into a clean user-facing Telegram message."""
        servers = self.list_active_servers()
        if not servers:
            return (
                "🌐 **Daftar Web Server / Live Preview**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Saat ini belum ada web server project yang aktif.\n\n"
                "💡 **Tips:** Saat kamu meminta waifu membuat atau mengedit web/landing page, "
                "waifu akan otomatis menyalakan web server dan memberikan link preview langsung! ✨"
            )

        lines = [
            "🌐 **Daftar Web Server / Live Preview Aktif**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Ada **{len(servers)}** server preview project yang sedang berjalan:\n"
        ]

        for idx, s in enumerate(servers, 1):
            p_name = s.get("project", "Project")
            p_port = s.get("port")
            p_url = s.get("url", f"http://localhost:{p_port}/")
            p_dir = s.get("dir", "")
            lines.append(
                f"{idx}. 🚀 **{p_name}**\n"
                f"   👉 **Link Preview:** [{p_url}]({p_url})\n"
                f"   🔌 **Port:** `{p_port}` | **PID:** `{s.get('pid')}`\n"
                f"   📁 **Folder:** `{p_dir}`\n"
            )

        lines.append("💡 Ketik `/stop_server <port>` jika ingin mematikan salah satu preview server.")
        return "\n".join(lines)


# Global singleton
_GLOBAL_PROJECT_SERVER_MGR: Optional[ProjectServerManager] = None


def get_project_server_manager() -> ProjectServerManager:
    global _GLOBAL_PROJECT_SERVER_MGR
    if _GLOBAL_PROJECT_SERVER_MGR is None:
        _GLOBAL_PROJECT_SERVER_MGR = ProjectServerManager()
    return _GLOBAL_PROJECT_SERVER_MGR

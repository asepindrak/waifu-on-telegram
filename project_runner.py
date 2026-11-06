"""
project_runner.py - Tailscale Project Runner & Port Opener
Executes workspace projects in the background, auto-detects dev ports,
and exposes them securely via Tailscale so the user can open and test
the running project from their smartphone, tablet, or another PC on the tailnet.
"""

import os
import re
import json
import time
import shutil
import socket
import logging
import subprocess
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RUNNING_SERVERS_FILE = os.path.join(DATA_DIR, "running_servers.json")

COMMON_DEV_PORTS = [
    3000, 5173, 8000, 8080, 5000, 4200, 8081, 8082, 8888, 9000, 3001, 3002, 3333, 4000, 8008
]


class TailscaleManager:
    """Inspects and manages Tailscale networking, status, and port exposure."""

    @staticmethod
    def get_tailscale_info() -> Dict[str, Any]:
        """Queries local Tailscale CLI for IP, MagicDNS, and network status."""
        tailscale_bin = shutil.which("tailscale") or shutil.which("tailscale.exe")
        if not tailscale_bin:
            return {
                "installed": False,
                "online": False,
                "ip": None,
                "magic_dns": None,
                "hostname": None,
                "devices": []
            }

        try:
            proc = subprocess.run(
                [tailscale_bin, "status", "--json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                self_node = data.get("Self", {})
                ips = self_node.get("TailscaleIPs", [])
                dns_name = self_node.get("DNSName", "").rstrip(".")
                hostname = self_node.get("HostName", "PC")
                online = self_node.get("Online", False)

                # Extract peer devices
                peers = []
                for p in data.get("Peer", {}).values():
                    p_name = p.get("HostName")
                    if p_name and p_name != hostname:
                        peers.append(p_name)

                return {
                    "installed": True,
                    "online": online,
                    "ip": ips[0] if ips else None,
                    "magic_dns": dns_name,
                    "hostname": hostname,
                    "devices": peers[:5]
                }
        except Exception as e:
            logger.warning(f"Error querying tailscale status: {e}")

        # Fallback to tailscale ip -4
        try:
            proc_ip = subprocess.run(
                [tailscale_bin, "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if proc_ip.returncode == 0 and proc_ip.stdout.strip():
                return {
                    "installed": True,
                    "online": True,
                    "ip": proc_ip.stdout.strip(),
                    "magic_dns": None,
                    "hostname": None,
                    "devices": []
                }
        except Exception:
            pass

        return {
            "installed": True,
            "online": False,
            "ip": None,
            "magic_dns": None,
            "hostname": None,
            "devices": []
        }

    @staticmethod
    def setup_tailscale_serve(port: int) -> Tuple[bool, Optional[str]]:
        """
        Attempts to configure 'tailscale serve --bg <port>' for instant HTTPS proxy on Tailnet.
        Returns: (success, https_url_or_note)
        """
        tailscale_bin = shutil.which("tailscale") or shutil.which("tailscale.exe")
        if not tailscale_bin:
            return False, None

        try:
            # tailscale serve --bg <port>
            proc = subprocess.run(
                [tailscale_bin, "serve", "--bg", str(port)],
                capture_output=True,
                text=True,
                timeout=6
            )
            if proc.returncode == 0:
                # Query serve status
                st_proc = subprocess.run(
                    [tailscale_bin, "serve", "status", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=4
                )
                if st_proc.returncode == 0 and st_proc.stdout.strip():
                    try:
                        st_data = json.loads(st_proc.stdout)
                        urls = list(st_data.get("Web", {}).keys())
                        if urls:
                            return True, f"https://{urls[0]}"
                    except Exception:
                        pass
                return True, "Active (Tailscale Serve)"
            else:
                logger.debug(f"tailscale serve note: {proc.stderr.strip()}")
        except Exception as e:
            logger.debug(f"tailscale serve attempt error: {e}")

        return False, None

    @staticmethod
    def reset_tailscale_serve() -> bool:
        """Resets active tailscale serve configuration."""
        tailscale_bin = shutil.which("tailscale") or shutil.which("tailscale.exe")
        if not tailscale_bin:
            return False
        try:
            subprocess.run([tailscale_bin, "serve", "reset"], capture_output=True, text=True, timeout=5)
            return True
        except Exception:
            return False


class ProjectRunner:
    """Manages background dev server execution, port detection, and Tailscale integration."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.registry_file = os.path.join(self.data_dir, "running_servers.json")

    def _read_registry(self) -> Dict[str, Any]:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logger.error(f"Error reading running_servers.json: {e}")
        return {}

    def _write_registry(self, data: Dict[str, Any]):
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing running_servers.json: {e}")

    def detect_run_command(self, project_path: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Inspects files in project_path to deduce the best launch command and expected port.
        Returns: (launch_command, estimated_port)
        """
        if not os.path.isdir(project_path):
            return None, None

        # 1. Node.js (package.json)
        pkg_json = os.path.join(project_path, "package.json")
        if os.path.exists(pkg_json):
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    pj = json.load(f)
                scripts = pj.get("scripts", {})
                deps = {**pj.get("dependencies", {}), **pj.get("devDependencies", {})}

                # Port hint based on framework
                est_port = 3000
                if "next" in deps:
                    est_port = 3000
                elif "vite" in deps:
                    est_port = 5173
                elif "@nestjs/core" in deps:
                    est_port = 3000
                elif "express" in deps:
                    est_port = 8000

                # Detect package manager
                pkg_mgr = "npm"
                if os.path.exists(os.path.join(project_path, "pnpm-lock.yaml")):
                    pkg_mgr = "pnpm"
                elif os.path.exists(os.path.join(project_path, "yarn.lock")):
                    pkg_mgr = "yarn"
                elif os.path.exists(os.path.join(project_path, "bun.lockb")):
                    pkg_mgr = "bun"

                for target in ["dev", "start", "serve", "run"]:
                    if target in scripts:
                        return f"{pkg_mgr} run {target}", est_port
            except Exception:
                pass

        # 2. Python Web Project
        manage_py = os.path.join(project_path, "manage.py")
        if os.path.exists(manage_py):
            return "python manage.py runserver 0.0.0.0:8000", 8000

        main_py = os.path.join(project_path, "main.py")
        app_py = os.path.join(project_path, "app.py")
        target_py = main_py if os.path.exists(main_py) else (app_py if os.path.exists(app_py) else None)

        if target_py:
            # Check for FastAPI / Flask
            try:
                with open(target_py, "r", encoding="utf-8") as f:
                    py_code = f.read().lower()
                if "fastapi" in py_code:
                    app_var = "app"
                    fname = os.path.splitext(os.path.basename(target_py))[0]
                    return f"python -m uvicorn {fname}:{app_var} --host 0.0.0.0 --port 8000 --reload", 8000
                elif "flask" in py_code:
                    return f"python {os.path.basename(target_py)}", 5000
                else:
                    return f"python {os.path.basename(target_py)}", 8000
            except Exception:
                return f"python {os.path.basename(target_py)}", 8000

        # 3. Go
        go_mod = os.path.join(project_path, "go.mod")
        if os.path.exists(go_mod):
            return "go run .", 8080

        # 4. Rust
        cargo_toml = os.path.join(project_path, "Cargo.toml")
        if os.path.exists(cargo_toml):
            return "cargo run", 8080

        # 5. Static HTML
        index_html = os.path.join(project_path, "index.html")
        if os.path.exists(index_html):
            return "python -m http.server 3000 --bind 0.0.0.0", 3000

        return None, None

    def is_port_in_use(self, port: int) -> bool:
        """Fast socket check if port is currently listening."""
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return True
        except Exception:
            return False

    def scan_active_port(self, expected_port: Optional[int] = None, wait_seconds: float = 3.0) -> Optional[int]:
        """Polls common ports to detect which port just started listening."""
        start_t = time.time()
        while time.time() - start_t < wait_seconds:
            # Check expected port first
            if expected_port and self.is_port_in_use(expected_port):
                return expected_port

            # Check other common ports
            for p in COMMON_DEV_PORTS:
                if p != 8001 and p != 8188 and p != 5001 and p != 3900:  # Exclude internal waifu ports
                    if self.is_port_in_use(p):
                        return p
            time.sleep(0.5)

        return expected_port if expected_port and self.is_port_in_use(expected_port) else None

    def start_project(
        self,
        project_name: str,
        project_path: str,
        custom_command: Optional[str] = None,
        custom_port: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Launches project dev server in the background, registers it,
        detects the open port, and creates Tailscale URLs.
        """
        clean_name = project_name.strip().lower()
        abs_path = os.path.abspath(project_path)

        # 1. Stop any currently running instance of this project
        self.stop_project(clean_name)

        # 2. Determine command & target port
        cmd, est_port = self.detect_run_command(abs_path)
        final_cmd = custom_command or cmd
        if not final_cmd:
            return {
                "success": False,
                "error": f"Tidak dapat mendeteksi cara menjalankan project di '{abs_path}'. Harap tentukan perintah (misal: 'npm run dev')."
            }

        target_port = custom_port or est_port or 3000

        # 3. Setup logs
        waifu_dir = os.path.join(abs_path, ".waifu")
        os.makedirs(waifu_dir, exist_ok=True)
        log_file = os.path.join(waifu_dir, "server.log")

        # 4. Launch background process
        try:
            log_fp = open(log_file, "w", encoding="utf-8")
            # Use shell=True on Windows with CREATE_NO_WINDOW
            creationflags = 0x08000000  # CREATE_NO_WINDOW
            proc = subprocess.Popen(
                final_cmd,
                cwd=abs_path,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                shell=True,
                creationflags=creationflags
            )
            pid = proc.pid
        except Exception as e:
            return {
                "success": False,
                "error": f"Gagal menjalankan server: {e}"
            }

        # 5. Wait and detect open port
        time.sleep(2.0)
        detected_port = self.scan_active_port(expected_port=target_port, wait_seconds=3.5)
        active_port = detected_port or target_port

        # 6. Tailscale Network Resolution
        ts_info = TailscaleManager.get_tailscale_info()
        ts_ip = ts_info.get("ip")
        ts_dns = ts_info.get("magic_dns")

        tailscale_url = f"http://{ts_ip}:{active_port}" if ts_ip else None
        magic_dns_url = f"http://{ts_dns}:{active_port}" if ts_dns else None
        local_url = f"http://127.0.0.1:{active_port}"

        # Attempt Tailscale Serve HTTPS
        serve_ok, serve_url = TailscaleManager.setup_tailscale_serve(active_port)

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        server_entry = {
            "project_name": clean_name,
            "project_path": abs_path,
            "pid": pid,
            "command": final_cmd,
            "port": active_port,
            "started_at": now_iso,
            "tailscale_ip": ts_ip,
            "tailscale_url": tailscale_url,
            "magic_dns_url": magic_dns_url,
            "https_serve_url": serve_url if serve_ok and serve_url and serve_url.startswith("https") else None,
            "local_url": local_url,
            "log_file": log_file,
            "tailscale_status": "Online" if ts_info.get("online") else "Offline / Belum Terkoneksi",
            "peer_devices": ts_info.get("devices", [])
        }

        registry = self._read_registry()
        registry[clean_name] = server_entry
        self._write_registry(registry)

        logger.info(f"Project '{clean_name}' started on port {active_port} (PID: {pid}). Tailscale URL: {tailscale_url}")
        return {
            "success": True,
            "entry": server_entry
        }

    def stop_project(self, project_name: str) -> Tuple[bool, str]:
        """Terminates the running dev server for given project."""
        clean_name = project_name.strip().lower()
        registry = self._read_registry()
        entry = registry.get(clean_name)
        if not entry:
            return False, f"Project '{project_name}' tidak sedang berjalan."

        pid = entry.get("pid")
        if pid:
            try:
                # Force kill process tree on Windows
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid), "/T"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            except Exception as e:
                logger.warning(f"Error killing PID {pid}: {e}")

        # Reset tailscale serve if applicable
        TailscaleManager.reset_tailscale_serve()

        del registry[clean_name]
        self._write_registry(registry)
        return True, f"Server project '{project_name}' (PID: {pid}) berhasil dihentikan."

    def list_running(self) -> Dict[str, Dict[str, Any]]:
        """Returns active running projects, pruning terminated processes."""
        registry = self._read_registry()
        active = {}
        changed = False

        for name, entry in registry.items():
            pid = entry.get("pid")
            port = entry.get("port")
            # Verify if still running or port is listening
            port_listening = self.is_port_in_use(port) if port else False
            if port_listening or self._is_pid_alive(pid):
                active[name] = entry
            else:
                changed = True

        if changed:
            self._write_registry(active)

        return active

    def _is_pid_alive(self, pid: Optional[int]) -> bool:
        if not pid:
            return False
        try:
            # Process check on Windows
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=3
            )
            return str(pid) in proc.stdout
        except Exception:
            return False

    def get_server_logs(self, project_name: str, lines: int = 30) -> str:
        """Reads latest lines from project server log file."""
        clean_name = project_name.strip().lower()
        registry = self._read_registry()
        entry = registry.get(clean_name)
        if not entry:
            return "Project tidak ditemukan di daftar server aktif."

        log_file = entry.get("log_file")
        if not log_file or not os.path.exists(log_file):
            return "File log server belum tersedia."

        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return "".join(recent).strip() or "(Log masih kosong)"
        except Exception as e:
            return f"Gagal membaca log: {e}"


# Global singleton
_GLOBAL_PROJECT_RUNNER: Optional[ProjectRunner] = None


def get_project_runner() -> ProjectRunner:
    global _GLOBAL_PROJECT_RUNNER
    if _GLOBAL_PROJECT_RUNNER is None:
        _GLOBAL_PROJECT_RUNNER = ProjectRunner()
    return _GLOBAL_PROJECT_RUNNER


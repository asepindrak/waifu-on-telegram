"""
project_manager.py - Multi-Project Workspace & Directory Selector
Allows Waifu on Telegram to manage projects, isolate coding tasks,
and customize the base projects directory (defaulting to User Home directory).
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

USER_HOME_DIR = os.path.expanduser("~")
DEFAULT_PROJECTS_DIR = os.environ.get("PROJECTS_DIR", USER_HOME_DIR)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROJECTS_CONFIG_FILE = os.path.join(DATA_DIR, "projects.json")


class ProjectManager:
    """Manages workspace projects, paths, and user active selection."""

    def __init__(self, data_dir: Optional[str] = None, projects_dir: Optional[str] = None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_file = os.path.join(self.data_dir, "projects.json")
        self.user_active_projects: Dict[int, str] = {}
        if projects_dir:
            os.environ["PROJECTS_DIR"] = os.path.abspath(projects_dir)
        self._ensure_config()

    def get_projects_root_dir(self) -> str:
        """Returns the configured root directory where projects are scanned and created."""
        env_root = os.environ.get("PROJECTS_DIR", "").strip()
        if env_root and os.path.isdir(env_root):
            return os.path.abspath(env_root)

        # Check in projects.json metadata
        data = self._read_raw_config()
        cfg_root = data.get("_root_dir", "").strip()
        if cfg_root and os.path.isdir(cfg_root):
            return os.path.abspath(cfg_root)

        return os.path.abspath(USER_HOME_DIR)

    def set_projects_root_dir(self, new_dir: str) -> Tuple[bool, str]:
        """Sets a new base directory for projects and auto-scans for existing projects."""
        abs_path = os.path.abspath(os.path.expanduser(new_dir.strip()))
        if not os.path.exists(abs_path):
            try:
                os.makedirs(abs_path, exist_ok=True)
            except Exception as e:
                return False, f"Gagal membuat direktori '{abs_path}': {e}"

        data = self._read_raw_config()
        data["_root_dir"] = abs_path
        os.environ["PROJECTS_DIR"] = abs_path
        self._write_raw_config(data)

        # Rescan projects in new root
        self.scan_projects_dir()
        return True, abs_path

    def _read_raw_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, dict):
                        return content
            except Exception as e:
                logger.error(f"Error reading projects.json: {e}")
        return {}

    def _write_raw_config(self, data: Dict[str, Any]):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing projects.json: {e}")

    def _ensure_config(self):
        data = self._read_raw_config()
        root_dir = self.get_projects_root_dir()

        if "projects" not in data or not isinstance(data.get("projects"), dict):
            data["projects"] = {}

        if "_root_dir" not in data:
            data["_root_dir"] = root_dir

        # Always ensure general/default workspace
        if "general" not in data["projects"]:
            data["projects"]["general"] = root_dir

        self._write_raw_config(data)
        self.scan_projects_dir()

    def scan_projects_dir(self) -> List[str]:
        """Scans root projects directory and registers subdirectories as projects."""
        root_dir = self.get_projects_root_dir()
        data = self._read_raw_config()
        registered = data.setdefault("projects", {})

        ignored_folders = {
            ".git", ".idea", ".vscode", "node_modules", "venv", ".venv",
            "__pycache__", "AppData", "Application Data", "Local Settings",
            "Cookies", "NetHood", "PrintHood", "Recent", "SendTo", "Start Menu", "Templates"
        }

        found_count = 0
        if os.path.isdir(root_dir):
            try:
                for item in os.listdir(root_dir):
                    if item in ignored_folders or item.startswith((".", "$")):
                        continue
                    item_path = os.path.join(root_dir, item)
                    if os.path.isdir(item_path):
                        # Register folder if not present
                        clean_name = item.lower().replace(" ", "-")
                        if clean_name not in registered:
                            registered[clean_name] = os.path.abspath(item_path)
                            found_count += 1
            except Exception as e:
                logger.warning(f"Error scanning projects dir '{root_dir}': {e}")

        self._write_raw_config(data)
        return list(registered.keys())

    def list_projects(self) -> Dict[str, str]:
        """Returns dictionary of project_name -> absolute_path."""
        data = self._read_raw_config()
        projs = data.get("projects", {})
        if not projs:
            projs = {"general": self.get_projects_root_dir()}
        return projs

    def get_active_project(self, user_id: int) -> str:
        """Gets active project name for given user ID."""
        if user_id not in self.user_active_projects:
            projs = self.list_projects()
            default_p = os.environ.get("DEFAULT_PROJECT_NAME", "general")
            if default_p not in projs:
                default_p = list(projs.keys())[0] if projs else "general"
            self.user_active_projects[user_id] = default_p
        return self.user_active_projects[user_id]

    def get_active_project_path(self, user_id: int) -> str:
        """Gets absolute filesystem path of user's active project."""
        p_name = self.get_active_project(user_id)
        projs = self.list_projects()
        target_path = projs.get(p_name)
        if not target_path or not os.path.isdir(target_path):
            return self.get_projects_root_dir()
        return os.path.abspath(target_path)

    def set_active_project(self, user_id: int, project_name: str) -> Tuple[bool, str]:
        """Switches user's active project."""
        clean_name = project_name.strip().lower()
        projs = self.list_projects()
        if clean_name in projs:
            self.user_active_projects[user_id] = clean_name
            return True, projs[clean_name]

        # Case-insensitive search
        for k, v in projs.items():
            if k.lower() == clean_name:
                self.user_active_projects[user_id] = k
                return True, v

        return False, f"Project '{project_name}' tidak ditemukan."

    def spawn_project(self, name: str, base_dir: Optional[str] = None, switch_user_id: Optional[int] = None) -> Tuple[bool, str, str]:
        """
        Creates a new project folder under base_dir (default: projects_root_dir)
        and registers it in projects list.
        Returns: (success, project_name, absolute_path_or_error)
        """
        clean_name = name.strip().replace(" ", "-").lower()
        if not clean_name:
            return False, "", "Nama project tidak boleh kosong."

        root = base_dir or self.get_projects_root_dir()
        target_path = os.path.abspath(os.path.join(root, clean_name))

        try:
            os.makedirs(target_path, exist_ok=True)
            data = self._read_raw_config()
            data.setdefault("projects", {})[clean_name] = target_path
            self._write_raw_config(data)
            if switch_user_id is not None:
                self.set_active_project(switch_user_id, clean_name)
            return True, clean_name, target_path
        except Exception as e:
            return False, clean_name, f"Gagal membuat folder project '{target_path}': {e}"

    def register_custom_path(self, name: str, custom_path: str) -> Tuple[bool, str]:
        """Registers an arbitrary external folder as a named project."""
        clean_name = name.strip().replace(" ", "-").lower()
        abs_path = os.path.abspath(os.path.expanduser(custom_path.strip()))
        if not os.path.isdir(abs_path):
            return False, f"Folder '{abs_path}' tidak ditemukan."

        data = self._read_raw_config()
        data.setdefault("projects", {})[clean_name] = abs_path
        self._write_raw_config(data)
        return True, abs_path

    def get_project_summary(self, proj_name: str) -> Dict[str, Any]:
        """Inspects directory: counts files, detects git repo and primary languages."""
        projs = self.list_projects()
        p_path = projs.get(proj_name)
        if not p_path or not os.path.isdir(p_path):
            return {"exists": False, "path": p_path or "N/A", "file_count": 0}

        file_count = 0
        extensions: Dict[str, int] = {}
        has_git = os.path.isdir(os.path.join(p_path, ".git"))

        try:
            for root, dirs, files in os.walk(p_path):
                # skip heavy/hidden folders
                dirs[:] = [d for d in dirs if not d.startswith((".", "node_modules", "venv", "__pycache__"))]
                for f in files:
                    file_count += 1
                    ext = os.path.splitext(f)[1].lower()
                    if ext:
                        extensions[ext] = extensions.get(ext, 0) + 1
                    if file_count >= 500:
                        break
                if file_count >= 500:
                    break
        except Exception:
            pass

        top_exts = sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:4]

        return {
            "name": proj_name,
            "exists": True,
            "path": p_path,
            "file_count": file_count,
            "has_git": has_git,
            "top_extensions": [e[0] for e in top_exts]
        }


# Global singleton instance
_GLOBAL_PROJECT_MGR: Optional[ProjectManager] = None


def get_project_manager() -> ProjectManager:
    global _GLOBAL_PROJECT_MGR
    if _GLOBAL_PROJECT_MGR is None:
        _GLOBAL_PROJECT_MGR = ProjectManager()
    return _GLOBAL_PROJECT_MGR

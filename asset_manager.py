import os
import sys
import glob
import shutil
import logging
import subprocess
import platform
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# Registry of AI Models, Custom Nodes, and Third-Party Dependencies
ASSET_REGISTRY = {
    "meinamix": {
        "name": "MeinaMix Anime SD 1.5 Checkpoint",
        "type": "model",
        "subfolder": os.path.join("models", "checkpoints"),
        "filename": "meinamix_v12Final.safetensors",
        "patterns": ["*meinamix*.safetensors", "*meina*.safetensors", "*anything*.safetensors", "*aom3*.safetensors"],
        "size_mb": 2033,
        "url": "https://civitai.com/api/download/models/119057?type=Model&format=SafeTensor&size=pruned&fp=fp16",
        "fallback_url": "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors",
        "description": "Checkpoint utama ilustrasi anime berkualitas tinggi untuk foto waifu konsisten.",
        "required_for": "Semua generasi foto & PAP waifu"
    },
    "animatediff_v2": {
        "name": "AnimateDiff v2 Motion Module (SD 1.5)",
        "type": "model",
        "subfolder": os.path.join("models", "animatediff_models"),
        "search_paths": [
            os.path.join("models", "animatediff_models"),
            os.path.join("custom_nodes", "ComfyUI-AnimateDiff-Evolved", "models")
        ],
        "filename": "mm_sd_v15_v2.ckpt",
        "patterns": ["*mm_sd_v15_v2*.ckpt", "*mm_sd_v15*.ckpt", "*v3_sd15_mm*.ckpt"],
        "size_mb": 1720,
        "url": "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt",
        "description": "Motion module untuk animasi video dinamis temporal dengan AnimateDiff.",
        "required_for": "Video Engine AnimateDiff"
    },
    "animatediff_node": {
        "name": "ComfyUI-AnimateDiff-Evolved Extension",
        "type": "custom_node",
        "subfolder": os.path.join("custom_nodes", "ComfyUI-AnimateDiff-Evolved"),
        "git_url": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git",
        "description": "Ekstensi ComfyUI untuk menjalankan pipeline animasi AnimateDiff.",
        "required_for": "Video Engine AnimateDiff"
    },
    "wan21_1.3b": {
        "name": "Wan 2.1 1.3B Video Diffusion Model",
        "type": "model",
        "subfolder": os.path.join("models", "diffusion_models"),
        "filename": "wan2.1_t2v_1.3B_bf16.safetensors",
        "patterns": ["*wan2.1*1.3B*.safetensors", "*wan2.1_t2v_1.3B*.safetensors", "*wan*1.3B*.safetensors"],
        "size_mb": 2900,
        "url": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/resolve/main/wan2.1_t2v_1.3B_bf16.safetensors",
        "description": "Model video generasi baru Wan 2.1 1.3B (ringan & hemat VRAM).",
        "required_for": "Video Engine Wan 2.1"
    },
    "wan21_vae": {
        "name": "Wan 2.1 Video VAE",
        "type": "model",
        "subfolder": os.path.join("models", "vae"),
        "filename": "wan_2.1_vae.safetensors",
        "patterns": ["*wan*vae*.safetensors", "*wan*vae*.pth"],
        "size_mb": 250,
        "url": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/resolve/main/Wan2.1_VAE.pth",
        "description": "Autoencoder khusus video latents untuk Wan 2.1.",
        "required_for": "Video Engine Wan 2.1"
    }
}

_COMFYUI_DIR_CACHE: Optional[str] = None

def detect_comfyui_dir() -> Optional[str]:
    """
    Intelligently discovers ComfyUI root directory across environments.
    Checks environment variables, running processes, and standard installation paths.
    """
    global _COMFYUI_DIR_CACHE
    if _COMFYUI_DIR_CACHE and os.path.exists(_COMFYUI_DIR_CACHE):
        return _COMFYUI_DIR_CACHE

    # 1. Environment variables
    env_dir = os.environ.get("COMFYUI_DIR", "").strip() or os.environ.get("COMFYUI_PATH", "").strip()
    if env_dir and os.path.exists(os.path.join(env_dir, "models")):
        _COMFYUI_DIR_CACHE = os.path.abspath(env_dir)
        return _COMFYUI_DIR_CACHE

    user_home = os.path.expanduser("~")
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(user_home, "AppData", "Local"))

    candidate_paths = [
        # Comfy-Desktop official install
        os.path.join(local_app_data, "Comfy-Desktop", "ComfyUI-Installs", "ComfyUI", "ComfyUI"),
        # Portable Windows ComfyUI
        os.path.join(user_home, "ComfyUI_windows_portable", "ComfyUI"),
        "C:\\ComfyUI_windows_portable\\ComfyUI",
        "D:\\ComfyUI_windows_portable\\ComfyUI",
        "E:\\ComfyUI_windows_portable\\ComfyUI",
        # Standard user folder
        os.path.join(user_home, "ComfyUI"),
        os.path.join(user_home, "comfyui"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ComfyUI")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "ComfyUI"))
    ]

    # 2. Check running process on Windows if candidate paths haven't matched
    if platform.system() == "Windows":
        try:
            ps_script = 'Get-NetTCPConnection -LocalPort 8188 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1 | ForEach-Object { (Get-CimInstance Win32_Process -Filter "ProcessId = $_").CommandLine }'
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=5)
            cmd_line = res.stdout.strip()
            if cmd_line:
                for part in cmd_line.split('"'):
                    part = part.strip()
                    if "main.py" in part or ".venv" in part or "ComfyUI" in part:
                        parent = os.path.dirname(part)
                        for candidate_lvl in [parent, os.path.dirname(parent), os.path.dirname(os.path.dirname(parent))]:
                            if os.path.exists(os.path.join(candidate_lvl, "models")):
                                _COMFYUI_DIR_CACHE = os.path.abspath(candidate_lvl)
                                return _COMFYUI_DIR_CACHE
        except Exception:
            pass

    for p in candidate_paths:
        if os.path.exists(p) and os.path.exists(os.path.join(p, "models")):
            _COMFYUI_DIR_CACHE = os.path.abspath(p)
            return _COMFYUI_DIR_CACHE

    return None

def get_asset_info(asset_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata and current installation status of a registered asset."""
    if asset_key not in ASSET_REGISTRY:
        return None

    spec = dict(ASSET_REGISTRY[asset_key])
    comfy_dir = detect_comfyui_dir()
    
    if not comfy_dir:
        spec["status"] = "unknown (ComfyUI not found)"
        spec["installed"] = False
        spec["target_path"] = None
        return spec

    target_dir = os.path.join(comfy_dir, spec["subfolder"])
    spec["target_dir"] = target_dir

    if spec["type"] == "custom_node":
        target_path = target_dir
        spec["target_path"] = target_path
        # Check if directory exists and has python code
        spec["installed"] = os.path.isdir(target_path) and os.path.exists(os.path.join(target_path, "__init__.py"))
    elif spec["type"] == "model":
        full_file_path = os.path.join(target_dir, spec["filename"])
        spec["target_path"] = full_file_path

        # Check search paths and pattern matching
        search_dirs = [target_dir]
        if "search_paths" in spec:
            search_dirs = [os.path.join(comfy_dir, sp) for sp in spec["search_paths"]]

        found_file = None
        found_size = 0

        # Exact file match check
        for sdir in search_dirs:
            p = os.path.join(sdir, spec["filename"])
            if os.path.isfile(p) and os.path.getsize(p) > (10 * 1024 * 1024):
                found_file = p
                found_size = os.path.getsize(p)
                break

        # Pattern match check if exact match not found
        if not found_file and "patterns" in spec:
            for sdir in search_dirs:
                if os.path.isdir(sdir):
                    for pat in spec["patterns"]:
                        matches = glob.glob(os.path.join(sdir, pat))
                        for m in matches:
                            if os.path.isfile(m) and os.path.getsize(m) > (10 * 1024 * 1024):
                                found_file = m
                                found_size = os.path.getsize(m)
                                break
                        if found_file:
                            break
                if found_file:
                    break

        if found_file:
            spec["installed"] = True
            spec["target_path"] = found_file
            spec["current_size_mb"] = round(found_size / (1024 * 1024), 1)
        else:
            spec["installed"] = False
            spec["current_size_mb"] = 0

    spec["status"] = "installed" if spec["installed"] else "missing"
    return spec

def check_all_assets() -> Dict[str, Dict[str, Any]]:
    """Checks status for all registered models, nodes, and dependencies."""
    results = {}
    for key in ASSET_REGISTRY:
        info = get_asset_info(key)
        if info:
            results[key] = info
    return results

def download_asset(asset_key: str, progress_callback=None) -> bool:
    """
    Downloads model asset with HTTP byte resume support (curl or requests).
    Returns True on success, False otherwise.
    """
    info = get_asset_info(asset_key)
    if not info or info.get("type") != "model":
        logger.error(f"Asset '{asset_key}' is not a downloadable model.")
        return False

    target_path = info.get("target_path")
    if not target_path:
        logger.error(f"Could not determine target path for '{asset_key}'.")
        return False

    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)

    url = info.get("url")
    fallback_url = info.get("fallback_url")
    name = info["name"]
    logger.info(f"Downloading {name} -> {target_path}")

    for dl_url in [url, fallback_url]:
        if not dl_url:
            continue
        # Use curl if available for high-speed resumable downloads
        curl_path = shutil.which("curl")
        if curl_path:
            try:
                cmd = [curl_path, "-L", "-C", "-", "--retry", "3", "--progress-bar", "-o", target_path, dl_url]
                ret = subprocess.run(cmd)
                if ret.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024 * 1024:
                    return True
            except Exception as e:
                logger.warning(f"curl download failed: {e}")

        # Fallback to requests streaming download
        try:
            import requests
            headers = {}
            initial_pos = 0
            if os.path.exists(target_path):
                initial_pos = os.path.getsize(target_path)
                headers["Range"] = f"bytes={initial_pos}-"

            with requests.get(dl_url, headers=headers, stream=True, timeout=60) as r:
                if r.status_code in (200, 206):
                    mode = "ab" if r.status_code == 206 else "wb"
                    total_len = int(r.headers.get("content-length", 0)) + initial_pos
                    dl = initial_pos
                    with open(target_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                                dl += len(chunk)
                                if progress_callback and total_len > 0:
                                    progress_callback(dl, total_len)
                    if os.path.getsize(target_path) > 10 * 1024 * 1024:
                        return True
        except Exception as e:
            logger.warning(f"Failed to download from {dl_url}: {e}")

    return False

def install_custom_node(asset_key: str) -> bool:
    """Clones a ComfyUI custom node git repository into ComfyUI/custom_nodes/."""
    info = get_asset_info(asset_key)
    if not info or info.get("type") != "custom_node":
        return False

    target_path = info.get("target_path")
    git_url = info.get("git_url")
    if not target_path or not git_url:
        return False

    # If incomplete or missing __init__.py, remove corrupted folder
    if os.path.exists(target_path) and not os.path.exists(os.path.join(target_path, "__init__.py")):
        try:
            shutil.rmtree(target_path, ignore_errors=True)
        except Exception:
            pass

    parent_dir = os.path.dirname(target_path)
    os.makedirs(parent_dir, exist_ok=True)

    git_bin = shutil.which("git")
    if not git_bin:
        logger.error("Git is required to clone custom nodes.")
        return False

    try:
        logger.info(f"Cloning {git_url} into {target_path}...")
        res = subprocess.run([git_bin, "clone", "--depth", "1", git_url, target_path], capture_output=True, text=True, timeout=180)
        return res.returncode == 0 and os.path.exists(os.path.join(target_path, "__init__.py"))
    except Exception as e:
        logger.error(f"Error cloning custom node {asset_key}: {e}")
        return False

def ensure_video_engine_assets(engine_name: str) -> Tuple[bool, List[str]]:
    """
    Checks if all required assets for the given video engine are present.
    Returns (is_ready, list_of_missing_asset_keys).
    """
    engine = engine_name.lower().strip()
    missing = []

    if engine == "animatediff":
        for k in ("animatediff_node", "animatediff_v2"):
            info = get_asset_info(k)
            if not info or not info.get("installed"):
                missing.append(k)
    elif engine == "wan21":
        for k in ("wan21_1.3b", "wan21_vae"):
            info = get_asset_info(k)
            if not info or not info.get("installed"):
                missing.append(k)

    return (len(missing) == 0, missing)

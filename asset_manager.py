import os
import sys
import glob
import shutil
import logging
import subprocess
import platform
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Registry of AI Models, Custom Nodes, and Third-Party Dependencies
ASSET_REGISTRY = {
    "qwythos_9b": {
        "name": "Huihui-Qwythos 9B Claude-Mythos (Uncensored LLM)",
        "type": "llm_model",
        "filename": "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
        "patterns": ["*Qwythos*9B*.gguf", "*Mythos*9B*.gguf", "*Qwythos*.gguf"],
        "size_mb": 5512,
        "url": "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
        "description": "Model chat/roleplay uncensored terbaik (Abliterated Claude-Mythos reasoning, 1M context).",
        "required_for": "Otak Utama Chat & Roleplay Waifu (Locally Uncensored)"
    },
    "qwythos_vision": {
        "name": "Huihui-Qwythos Vision Adapter (mmproj)",
        "type": "llm_model",
        "filename": "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf",
        "patterns": ["*Qwythos*mmproj*.gguf", "*mmproj-model-bf16*.gguf", "*mmproj*.gguf"],
        "size_mb": 879,
        "url": "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/mmproj-model-bf16.gguf",
        "description": "Vision projector agar waifu bisa melihat dan mengomentari foto dari user.",
        "required_for": "Fitur Vision (Melihat Foto dari User)"
    },
    "meinamix": {
        "name": "MeinaMix Anime SD 1.5 Checkpoint",
        "type": "model",
        "subfolder": os.path.join("models", "checkpoints"),
        "filename": "meinamix_v12Final.safetensors",
        "patterns": ["*meinamix*.safetensors", "*meina*.safetensors", "*aom3*.safetensors"],
        "size_mb": 2033,
        "url": "https://civitai.com/api/download/models/119057?type=Model&format=SafeTensor&size=pruned&fp=fp16",
        "fallback_url": "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V10%20-%20baked%20VAE.safetensors",
        "civitai_url": "https://civitai.com/models/119057/meinamix",
        "description": "Checkpoint utama ilustrasi anime berkualitas tinggi untuk foto waifu konsisten (SD 1.5, cepat, hemat VRAM).",
        "required_for": "Generasi foto & PAP waifu (SD 1.5)"
    },
    "anything_xl": {
        "name": "万象熔炉 | Anything XL (SDXL Anime Checkpoint)",
        "type": "model",
        "subfolder": os.path.join("models", "checkpoints"),
        "filename": "AnythingXL_xl.safetensors",
        "patterns": ["*AnythingXL*.safetensors", "*anything*xl*.safetensors", "*Anything-XL*.safetensors", "*anythingxl*.safetensors"],
        "size_mb": 6616,
        "url": "https://huggingface.co/artificialguybr/Anything-XL/resolve/main/AnythingXL_xl.safetensors",
        "fallback_url": "https://hf-mirror.com/artificialguybr/Anything-XL/resolve/main/AnythingXL_xl.safetensors",
        "mirrors": [
            "https://huggingface.co/artificialguybr/Anything-XL/resolve/main/AnythingXL_xl.safetensors",
            "https://hf-mirror.com/artificialguybr/Anything-XL/resolve/main/AnythingXL_xl.safetensors",
            "https://huggingface.co/genai-archive/anything-xl/resolve/main/anything-xl.safetensors",
            "https://huggingface.co/m4gnett/AnythingXL/resolve/main/AnythingXL_xl.safetensors"
        ],
        "civitai_url": "https://civitai.com/models/9409/or-anything-xl",
        "description": "Checkpoint SDXL anime resolusi tinggi 1024px, detail tajam, estetik anime modern (Civitai #9409).",
        "required_for": "Generasi foto & selfie waifu resolusi tinggi (SDXL)"
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

def detect_locally_uncensored_dir() -> str:
    """Resolves cross-platform models directory for Locally Uncensored."""
    env_dir = os.environ.get("LOCALLY_UNCENSORED_DIR")
    if env_dir and os.path.isdir(env_dir):
        return os.path.abspath(env_dir)

    user_home = os.path.expanduser("~")
    candidates = []
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "Locally Uncensored", "models"))
        candidates.append(os.path.join(user_home, "AppData", "Roaming", "Locally Uncensored", "models"))
    elif platform.system() == "Darwin":
        candidates.append(os.path.join(user_home, "Library", "Application Support", "Locally Uncensored", "models"))
    else: # Linux
        candidates.append(os.path.join(user_home, ".config", "Locally Uncensored", "models"))
        candidates.append(os.path.join(user_home, ".local", "share", "Locally Uncensored", "models"))
    candidates.append(os.path.join(user_home, ".locally-uncensored", "models"))

    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    # Default to standard path
    return os.path.abspath(candidates[0])


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

    # Project tools/ComfyUI candidates
    project_tools = os.path.join(PROJECT_ROOT, "tools")
    candidate_paths = [
        os.path.join(project_tools, "ComfyUI", "ComfyUI_windows_portable", "ComfyUI"),
        os.path.join(project_tools, "ComfyUI", "ComfyUI"),
        os.path.join(project_tools, "ComfyUI_windows_portable", "ComfyUI"),
        os.path.join(project_tools, "ComfyUI"),
        os.path.join(PROJECT_ROOT, "ComfyUI"),
        # Comfy-Desktop official install (Windows)
        os.path.join(local_app_data, "Comfy-Desktop", "ComfyUI-Installs", "ComfyUI", "ComfyUI"),
        os.path.join(local_app_data, "Comfy-Desktop", "ComfyUI-Shared"),
        # macOS paths
        os.path.join(user_home, "Library", "Application Support", "ComfyUI"),
        "/Applications/ComfyUI.app/Contents/Resources/ComfyUI",
        # Linux paths
        os.path.join(user_home, ".local", "share", "ComfyUI"),
        "/opt/ComfyUI",
        "/var/lib/ComfyUI",
        # Standard user folder (macOS / Linux / Windows)
        os.path.join(user_home, "ComfyUI"),
        os.path.join(user_home, "comfyui"),
        os.path.join(user_home, "Desktop", "ComfyUI"),
        os.path.join(user_home, "Downloads", "ComfyUI"),
        os.path.join(user_home, "Documents", "ComfyUI"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ComfyUI")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "ComfyUI"))
    ]

    # Additional Windows drive scanning (C:, D:, E:, F:, G:)
    if platform.system() == "Windows":
        for drive in ["C:", "D:", "E:", "F:", "G:"]:
            candidate_paths.extend([
                f"{drive}\\ComfyUI",
                f"{drive}\\comfyui",
                f"{drive}\\ComfyUI_windows_portable\\ComfyUI",
                f"{drive}\\AI\\ComfyUI",
                f"{drive}\\StableDiffusion\\ComfyUI",
                f"{drive}\\sd\\ComfyUI"
            ])

    # Dynamic search inside project tools/ComfyUI directory
    tools_comfy = os.path.join(PROJECT_ROOT, "tools", "ComfyUI")
    if os.path.isdir(tools_comfy):
        for root, dirs, files in os.walk(tools_comfy):
            if "main.py" in files and "models" in dirs:
                _COMFYUI_DIR_CACHE = os.path.abspath(root)
                return _COMFYUI_DIR_CACHE
            rel_depth = len(os.path.relpath(root, tools_comfy).split(os.sep))
            if rel_depth >= 4:
                dirs.clear()

    # Dynamic search inside UserProfile, OneDrive, Documents, and Downloads
    search_dirs = [
        user_home,
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "OneDrive"),
    ]
    for env_k in ["OneDrive", "OneDriveConsumer"]:
        val = os.environ.get(env_k)
        if val and os.path.isdir(val):
            search_dirs.append(val)
            search_dirs.append(os.path.join(val, "Documents"))
            search_dirs.append(os.path.join(val, "Desktop"))

    for s_dir in set(filter(os.path.isdir, search_dirs)):
        for pat in ["*ComfyUI*", "*comfyui*"]:
            for match in glob.glob(os.path.join(s_dir, pat)):
                if os.path.isdir(match):
                    for subroot, dirs, files in os.walk(match):
                        if "main.py" in files and "models" in dirs:
                            _COMFYUI_DIR_CACHE = os.path.abspath(subroot)
                            return _COMFYUI_DIR_CACHE
                        rel = len(os.path.relpath(subroot, match).split(os.sep))
                        if rel >= 3:
                            dirs.clear()

    # 2. Check running process across Windows, Linux, and macOS
    if platform.system() != "Windows":
        try:
            # Check listening port 8188 via lsof
            lsof_bin = shutil.which("lsof")
            if lsof_bin:
                pid_out = subprocess.run([lsof_bin, "-i", ":8188", "-sTCP:LISTEN", "-t"], capture_output=True, text=True, timeout=3).stdout.strip()
                if pid_out:
                    pid = pid_out.splitlines()[0].strip()
                    # Check cwd of process
                    proc_cwd = os.path.realpath(f"/proc/{pid}/cwd") if os.path.exists(f"/proc/{pid}/cwd") else None
                    if proc_cwd and os.path.exists(os.path.join(proc_cwd, "models")):
                        _COMFYUI_DIR_CACHE = proc_cwd
                        return _COMFYUI_DIR_CACHE
        except Exception:
            pass

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
        if not os.path.exists(p):
            continue
        if os.path.isfile(os.path.join(p, "main.py")) and os.path.isdir(os.path.join(p, "models")):
            _COMFYUI_DIR_CACHE = os.path.abspath(p)
            return _COMFYUI_DIR_CACHE
        sub_c = os.path.join(p, "ComfyUI")
        if os.path.isfile(os.path.join(sub_c, "main.py")) and os.path.isdir(os.path.join(sub_c, "models")):
            _COMFYUI_DIR_CACHE = os.path.abspath(sub_c)
            return _COMFYUI_DIR_CACHE
        sub_port = os.path.join(p, "ComfyUI_windows_portable", "ComfyUI")
        if os.path.isfile(os.path.join(sub_port, "main.py")) and os.path.isdir(os.path.join(sub_port, "models")):
            _COMFYUI_DIR_CACHE = os.path.abspath(sub_port)
            return _COMFYUI_DIR_CACHE
        if os.path.exists(os.path.join(p, "models")):
            _COMFYUI_DIR_CACHE = os.path.abspath(p)
            return _COMFYUI_DIR_CACHE

    return None

_COMFYUI_FORCE_CPU: Optional[bool] = None

def get_comfyui_launch_spec() -> Optional[Dict[str, Any]]:
    """
    Returns executable command, working directory, and arguments to launch ComfyUI
    with standard options (--listen 127.0.0.1 --port 8188).
    Directly invokes embedded python to prevent batch file 'pause' freezing.
    Automatically detects if CUDA is unsupported to append --cpu and avoid crash.
    """
    global _COMFYUI_FORCE_CPU
    cdir = detect_comfyui_dir()
    if not cdir:
        return None

    main_py = os.path.join(cdir, "main.py")
    if not os.path.isfile(main_py):
        return None

    def _should_use_cpu(py_exe: str) -> bool:
        global _COMFYUI_FORCE_CPU
        if os.environ.get("COMFYUI_CPU", "").strip().lower() in ("1", "true", "yes"):
            return True
        if _COMFYUI_FORCE_CPU is not None:
            return _COMFYUI_FORCE_CPU
        try:
            probe = subprocess.run(
                [py_exe, "-s", "-c", "import torch; exit(0 if torch.cuda.is_available() else 1)"],
                capture_output=True,
                timeout=45
            )
            _COMFYUI_FORCE_CPU = (probe.returncode != 0)
        except Exception:
            _COMFYUI_FORCE_CPU = False
        return _COMFYUI_FORCE_CPU

    # 1. Check for ComfyUI Windows Portable embedded python
    for base in [cdir, os.path.dirname(cdir), os.path.dirname(os.path.dirname(cdir))]:
        for py_dir in ["python_embeded", "python_embedded", "python"]:
            py_embed = os.path.join(base, py_dir, "python.exe")
            if os.path.isfile(py_embed):
                extra_args = ["--cpu"] if _should_use_cpu(py_embed) else []
                return {
                    "cwd": cdir,
                    "cmd": [py_embed, "-s", main_py, "--windows-standalone-build", "--port", "8188", "--listen", "127.0.0.1"] + extra_args
                }

    # 2. Check virtual environments in cdir or parent
    for base in [cdir, os.path.dirname(cdir)]:
        for venv_dir in [".venv", "venv"]:
            v_py = os.path.join(base, venv_dir, "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(base, venv_dir, "bin", "python")
            if os.path.isfile(v_py):
                extra_args = ["--cpu"] if _should_use_cpu(v_py) else []
                return {
                    "cwd": cdir,
                    "cmd": [v_py, main_py, "--port", "8188", "--listen", "127.0.0.1"] + extra_args
                }

    # 3. Fallback to system python
    extra_args = ["--cpu"] if _should_use_cpu(sys.executable) else []
    return {
        "cwd": cdir,
        "cmd": [sys.executable, main_py, "--port", "8188", "--listen", "127.0.0.1"] + extra_args
    }

def get_asset_info(asset_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata and current installation status of a registered asset."""
    if asset_key not in ASSET_REGISTRY:
        return None

    spec = dict(ASSET_REGISTRY[asset_key])
    if spec.get("type") == "llm_model":
        project_models_dir = os.path.join(PROJECT_ROOT, "models")
        lu_models_dir = detect_locally_uncensored_dir()
        candidate_dirs = [project_models_dir, lu_models_dir]

        target_dir = project_models_dir
        spec["target_dir"] = target_dir
        spec["target_path"] = os.path.join(target_dir, spec["filename"])
        found_file = None
        found_size = 0

        for cdir in candidate_dirs:
            if not os.path.isdir(cdir):
                continue
            p = os.path.join(cdir, spec["filename"])
            if os.path.isfile(p) and os.path.getsize(p) > (10 * 1024 * 1024):
                found_file = p
                found_size = os.path.getsize(p)
                break
            if "patterns" in spec:
                for pat in spec["patterns"]:
                    matches = glob.glob(os.path.join(cdir, pat))
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

def _download_file(url: str, target_path: str, fallback_url: Optional[str] = None, mirrors: Optional[list] = None, progress_callback=None) -> bool:
    """Helper to download file with resume support via curl or requests across high-speed mirrors."""
    target_dir = os.path.dirname(target_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    candidate_urls = []
    if url and url not in candidate_urls:
        candidate_urls.append(url)
    if fallback_url and fallback_url not in candidate_urls:
        candidate_urls.append(fallback_url)
    if mirrors:
        for m in mirrors:
            if m and m not in candidate_urls:
                candidate_urls.append(m)

    for idx, dl_url in enumerate(candidate_urls, 1):
        if len(candidate_urls) > 1:
            logger.info(f"Connecting to download mirror [{idx}/{len(candidate_urls)}]: {dl_url}")

        curl_path = shutil.which("curl")
        if curl_path:
            try:
                # Add speed limit check (min 150KB/s over 20s) so curl fails over to faster mirror instead of crawling
                cmd = [
                    curl_path, "-fL", "-C", "-",
                    "--retry", "2",
                    "--speed-limit", "150000",
                    "--speed-time", "20",
                    "--progress-bar",
                    "-o", target_path,
                    dl_url
                ]
                ret = subprocess.run(cmd)
                if ret.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024 * 1024:
                    return True
                if idx < len(candidate_urls):
                    print(f"\n  ℹ Kecepatan mirror rendah atau terputus. Mencoba mirror berkecepatan tinggi berikutnya [{idx + 1}/{len(candidate_urls)}]...")
            except Exception as e:
                logger.warning(f"curl download failed on {dl_url}: {e}")

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

def download_asset(asset_key: str, progress_callback=None) -> bool:
    """
    Downloads model asset with HTTP byte resume support (curl or requests),
    or clones custom node if type is 'custom_node'.
    Supports models, llm_models, and custom nodes.
    Returns True on success, False otherwise.
    """
    info = get_asset_info(asset_key)
    if not info:
        logger.error(f"Asset '{asset_key}' not found.")
        return False

    if info.get("type") == "custom_node":
        return install_custom_node(asset_key)

    if info.get("type") not in ("model", "llm_model"):
        logger.error(f"Asset '{asset_key}' is not a downloadable model or custom node.")
        return False

    target_path = info.get("target_path")
    if not target_path:
        logger.error(f"Could not determine target path for '{asset_key}'.")
        return False

    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)

    name = info["name"]
    logger.info(f"Downloading {name} -> {target_path}")

    return _download_file(
        url=info.get("url"),
        target_path=target_path,
        fallback_url=info.get("fallback_url"),
        mirrors=info.get("mirrors"),
        progress_callback=progress_callback
    )

def ensure_koboldcpp() -> bool:
    """Ensures standalone KoboldCPP binary is downloaded and ready in tools/."""
    tools_dir = os.path.join(PROJECT_ROOT, "tools")
    os.makedirs(tools_dir, exist_ok=True)
    if platform.system() == "Windows":
        exe_path = os.path.join(tools_dir, "koboldcpp.exe")
        if os.path.isfile(exe_path) and os.path.getsize(exe_path) > 10 * 1024 * 1024:
            return True
        url = "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp.exe"
        return _download_file(url, exe_path)
    elif platform.system() == "Darwin":
        bin_path = os.path.join(tools_dir, "koboldcpp")
        if os.path.isfile(bin_path) and os.path.getsize(bin_path) > 10 * 1024 * 1024:
            return True
        url = "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp-mac-arm64"
        ok = _download_file(url, bin_path)
        if ok and os.path.exists(bin_path):
            try:
                os.chmod(bin_path, 0o755)
            except Exception:
                pass
        return ok
    else: # Linux
        bin_path = os.path.join(tools_dir, "koboldcpp")
        if os.path.isfile(bin_path) and os.path.getsize(bin_path) > 10 * 1024 * 1024:
            return True
        url = "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp-linux-x64-nocuda"
        ok = _download_file(url, bin_path)
        if ok and os.path.exists(bin_path):
            try:
                os.chmod(bin_path, 0o755)
            except Exception:
                pass
        return ok

def ensure_nodejs() -> bool:
    """Ensures Node.js is present (system-wide or standalone portable in tools/nodejs)."""
    # 1. Check if node is already working
    if shutil.which("node"):
        return True

    local_node_dir = os.path.join(PROJECT_ROOT, "tools", "nodejs")
    local_node_exe = os.path.join(local_node_dir, "node.exe" if platform.system() == "Windows" else "bin/node")
    if os.path.isfile(local_node_exe):
        if local_node_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = local_node_dir + os.pathsep + os.environ.get("PATH", "")
        return True

    # 2. On Windows, auto-download portable Node.js LTS
    if platform.system() == "Windows":
        try:
            os.makedirs(local_node_dir, exist_ok=True)
            zip_dest = os.path.join(PROJECT_ROOT, "tools", "nodejs_temp.zip")
            url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-win-x64.zip"
            if _download_file(url, zip_dest):
                import zipfile
                with zipfile.ZipFile(zip_dest, 'r') as zip_ref:
                    for member in zip_ref.namelist():
                        parts = member.split('/', 1)
                        if len(parts) > 1 and parts[1]:
                            target_file = os.path.join(local_node_dir, parts[1].replace('/', os.sep))
                            if member.endswith('/'):
                                os.makedirs(target_file, exist_ok=True)
                            else:
                                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                                with zip_ref.open(member) as src, open(target_file, "wb") as dst:
                                    dst.write(src.read())
                if os.path.exists(zip_dest):
                    os.remove(zip_dest)
                if os.path.isfile(local_node_exe):
                    os.environ["PATH"] = local_node_dir + os.pathsep + os.environ.get("PATH", "")
                    return True
        except Exception as e:
            logger.warning(f"Failed to auto-install portable Node.js: {e}")

    return False

def ensure_comfyui() -> bool:
    """Ensures ComfyUI portable is downloaded, extracted, and ready in tools/ComfyUI."""
    if detect_comfyui_dir():
        return True

    if platform.system() == "Windows":
        comfy_tool_dir = os.path.join(PROJECT_ROOT, "tools", "ComfyUI")
        os.makedirs(comfy_tool_dir, exist_ok=True)
        zip_dest = os.path.join(PROJECT_ROOT, "tools", "ComfyUI_portable.7z")
        url = "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z"
        logger.info(f"Downloading official ComfyUI Windows Portable (~1.4 GB) to {zip_dest}...")
        ok = _download_file(url, zip_dest)
        if ok and os.path.exists(zip_dest):
            extracted = False
            seven_zip = shutil.which("7z")
            if seven_zip:
                res = subprocess.run([seven_zip, "x", zip_dest, f"-o{comfy_tool_dir}", "-y"])
                extracted = (res.returncode == 0)
            if not extracted:
                tar_bin = shutil.which("tar")
                if tar_bin:
                    res = subprocess.run([tar_bin, "-xf", zip_dest, "-C", comfy_tool_dir])
                    extracted = (res.returncode == 0)
            if not extracted:
                seven_zr = os.path.join(PROJECT_ROOT, "tools", "7zr.exe")
                if _download_file("https://www.7-zip.org/a/7zr.exe", seven_zr):
                    res = subprocess.run([seven_zr, "x", zip_dest, f"-o{comfy_tool_dir}", "-y"])
                    extracted = (res.returncode == 0)
                    if os.path.exists(seven_zr):
                        try:
                            os.remove(seven_zr)
                        except Exception:
                            pass
            if os.path.exists(zip_dest):
                try:
                    os.remove(zip_dest)
                except Exception:
                    pass

            global _COMFYUI_DIR_CACHE
            _COMFYUI_DIR_CACHE = None
            return detect_comfyui_dir() is not None

    return False

def install_custom_node(asset_key: str) -> bool:
    """Clones or updates a ComfyUI custom node git repository into ComfyUI/custom_nodes/."""
    info = get_asset_info(asset_key)
    if not info or info.get("type") != "custom_node":
        return False

    target_path = info.get("target_path")
    git_url = info.get("git_url")
    if not target_path or not git_url:
        return False

    # If directory already exists with a valid __init__.py, it is already installed successfully
    if os.path.exists(target_path) and os.path.exists(os.path.join(target_path, "__init__.py")):
        logger.info(f"Custom node '{asset_key}' is already installed at {target_path}")
        return True

    # If incomplete or missing __init__.py, remove corrupted folder
    if os.path.exists(target_path):
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

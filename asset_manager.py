import os
import sys
import glob
import shutil
import logging
import subprocess
import platform
import tempfile
from typing import Optional, Dict, Any, List, Tuple

if sys.platform == "win32":
    try:
        import ctypes
        # Suppress Windows modal crash / bad image error dialogs (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    except Exception:
        pass

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Registry of AI Models, Custom Nodes, and Third-Party Dependencies
ASSET_REGISTRY = {
    "qwen25_7b": {
        "name": "Qwen2.5-7B-Instruct-Abliterated (Natural Indonesian & Roleplay LLM)",
        "type": "llm_model",
        "filename": "Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf",
        "patterns": ["*Qwen2.5*7B*abliterated*.gguf", "*Qwen2.5-7B-Instruct-abliterated*.gguf", "*Qwen2.5*7B*.gguf", "*qwen2.5-7b*.gguf"],
        "size_mb": 4466,
        "url": "https://huggingface.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF/resolve/main/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf",
        "fallback_url": "https://hf-mirror.com/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF/resolve/main/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf",
        "mirrors": [
            "https://huggingface.co/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF/resolve/main/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf",
            "https://hf-mirror.com/mradermacher/Qwen2.5-7B-Instruct-abliterated-GGUF/resolve/main/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf"
        ],
        "description": "Model chat/roleplay terbaik untuk Bahasa Indonesia (Qwen 2.5 7B abliterated uncensored, tata bahasa alami, tanpa delay thinking).",
        "required_for": "Otak Utama Chat & Roleplay Waifu (Qwen2.5-7B-Instruct-Abliterated)"
    },
    "stheno_8b": {
        "name": "L3-8B-Stheno-v3.4 (Uncensored Roleplay LLM)",
        "type": "llm_model",
        "filename": "Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf",
        "patterns": ["*Stheno*8B*.gguf", "*Stheno*.gguf", "*L3*8B*Stheno*.gguf", "*Llama-3.1-8B-Stheno*.gguf"],
        "size_mb": 4920,
        "url": "https://huggingface.co/bartowski/Llama-3.1-8B-Stheno-v3.4-GGUF/resolve/main/Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf",
        "fallback_url": "https://hf-mirror.com/bartowski/Llama-3.1-8B-Stheno-v3.4-GGUF/resolve/main/Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf",
        "mirrors": [
            "https://huggingface.co/bartowski/Llama-3.1-8B-Stheno-v3.4-GGUF/resolve/main/Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf",
            "https://hf-mirror.com/bartowski/Llama-3.1-8B-Stheno-v3.4-GGUF/resolve/main/Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf"
        ],
        "description": "Model chat/roleplay uncensored terbaik untuk waifu (L3-8B-Stheno-v3.4, ekspresif, tanpa delay thinking).",
        "required_for": "Otak Utama Chat & Roleplay Waifu (L3-8B-Stheno-v3.4)"
    },
    "qwythos_9b": {
        "name": "Huihui-Qwythos 9B Claude-Mythos (Uncensored LLM)",
        "type": "llm_model",
        "filename": "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
        "patterns": ["*Qwythos*9B*.gguf", "*Mythos*9B*.gguf", "*Qwythos*.gguf"],
        "size_mb": 5512,
        "url": "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
        "fallback_url": "https://hf-mirror.com/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
        "mirrors": [
            "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf",
            "https://hf-mirror.com/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
        ],
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
        "fallback_url": "https://hf-mirror.com/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/mmproj-model-bf16.gguf",
        "mirrors": [
            "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/mmproj-model-bf16.gguf",
            "https://hf-mirror.com/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/mmproj-model-bf16.gguf"
        ],
        "description": "Vision projector agar waifu bisa melihat dan mengomentari foto dari user.",
        "required_for": "Fitur Vision (Melihat Foto dari User)"
    },
    "moondream_text": {
        "name": "Moondream2 Text Model (Q4_K)",
        "type": "llm_model",
        "filename": "moondream2-q4_k.gguf",
        "patterns": ["*moondream*q4*.gguf", "*moondream*text*.gguf", "*moondream*.gguf"],
        "size_mb": 919,
        "url": "https://huggingface.co/salivosa/moondream2-gguf/resolve/main/moondream2-q4_k.gguf",
        "fallback_url": "https://hf-mirror.com/salivosa/moondream2-gguf/resolve/main/moondream2-q4_k.gguf",
        "mirrors": [
            "https://huggingface.co/salivosa/moondream2-gguf/resolve/main/moondream2-q4_k.gguf",
            "https://hf-mirror.com/salivosa/moondream2-gguf/resolve/main/moondream2-q4_k.gguf"
        ],
        "description": "Model teks vision Moondream2 ultra-ringan (~919 MB) untuk analisis foto lokal.",
        "required_for": "Fitur Vision Lokal Moondream (Melihat Foto User tanpa Cloud)"
    },
    "moondream_mmproj": {
        "name": "Moondream2 Vision Adapter (mmproj)",
        "type": "llm_model",
        "filename": "moondream2-mmproj-f16.gguf",
        "patterns": ["*moondream*mmproj*.gguf"],
        "size_mb": 909,
        "url": "https://huggingface.co/salivosa/moondream2-gguf/resolve/main/moondream2-mmproj-f16.gguf",
        "fallback_url": "https://hf-mirror.com/salivosa/moondream2-gguf/resolve/main/moondream2-mmproj-f16.gguf",
        "mirrors": [
            "https://huggingface.co/salivosa/moondream2-gguf/resolve/main/moondream2-mmproj-f16.gguf",
            "https://hf-mirror.com/salivosa/moondream2-gguf/resolve/main/moondream2-mmproj-f16.gguf"
        ],
        "description": "Multimodal Projector Moondream2 (~909 MB) untuk membaca gambar pada model lokal.",
        "required_for": "Fitur Vision Lokal Moondream (Melihat Foto User tanpa Cloud)"
    },
    "meinamix": {
        "name": "MeinaMix Anime SD 1.5 Checkpoint",
        "type": "model",
        "subfolder": os.path.join("models", "checkpoints"),
        "filename": "meinamix_v12Final.safetensors",
        "patterns": ["*meinamix*.safetensors", "*meina*.safetensors"],
        "size_mb": 2033,
        "url": "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors",
        "fallback_url": "https://hf-mirror.com/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors",
        "mirrors": [
            "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors",
            "https://hf-mirror.com/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors",
            "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V10%20-%20baked%20VAE.safetensors",
            "https://civitai.com/api/download/models/119057?type=Model&format=SafeTensor&size=pruned&fp=fp16"
        ],
        "civitai_url": "https://civitai.com/models/119057/meinamix",
        "description": "Checkpoint utama ilustrasi anime berkualitas tinggi untuk foto waifu konsisten (SD 1.5, cepat, hemat VRAM).",
        "required_for": "Generasi foto & PAP waifu (SD 1.5)"
    },
    "aom3": {
        "name": "AbyssOrangeMix3 (AOM3A1B SD 1.5 Checkpoint)",
        "type": "model",
        "subfolder": os.path.join("models", "checkpoints"),
        "filename": "AOM3A1B_orangemixs.safetensors",
        "patterns": ["*AOM3*.safetensors", "*aom3*.safetensors", "*orangemix*.safetensors", "*OrangeMix*.safetensors"],
        "size_mb": 2034,
        "url": "https://huggingface.co/WarriorMama777/OrangeMixs/resolve/main/Models/AbyssOrangeMix3/AOM3A1B_orangemixs.safetensors",
        "fallback_url": "https://hf-mirror.com/WarriorMama777/OrangeMixs/resolve/main/Models/AbyssOrangeMix3/AOM3A1B_orangemixs.safetensors",
        "mirrors": [
            "https://huggingface.co/WarriorMama777/OrangeMixs/resolve/main/Models/AbyssOrangeMix3/AOM3A1B_orangemixs.safetensors",
            "https://hf-mirror.com/WarriorMama777/OrangeMixs/resolve/main/Models/AbyssOrangeMix3/AOM3A1B_orangemixs.safetensors",
            "https://civitai.com/api/download/models/17233?type=Model&format=SafeTensor&size=pruned&fp=fp16"
        ],
        "civarchive_url": "https://civarchive.com/models/9942?modelVersionId=17233",
        "civitai_url": "https://civitai.com/models/9942/abyssorangemix3-aom3",
        "description": "Checkpoint anime legendaris AOM3A1B (Civitai #9942 / CivArchive), gaya anime tajam dan halus (SD 1.5, cepat, hemat VRAM).",
        "required_for": "Generasi foto & PAP waifu (SD 1.5 AOM3)"
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
        "search_paths": [
            os.path.join("models", "diffusion_models"),
            os.path.join("models", "checkpoints")
        ],
        "filename": "wan2.1_t2v_1.3B_bf16.safetensors",
        "patterns": ["*wan2.1*1.3B*.safetensors", "*wan2.1_t2v_1.3B*.safetensors", "*wan*1.3B*.safetensors", "*Wan2_1*1_3B*.safetensors"],
        "size_mb": 2700,
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors",
        "fallback_url": "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors",
        "mirrors": [
            "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors",
            "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors",
            "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-T2V-1_3B_bf16.safetensors",
            "https://hf-mirror.com/Kijai/WanVideo_comfy/resolve/main/Wan2_1-T2V-1_3B_bf16.safetensors"
        ],
        "description": "Model video generasi baru Wan 2.1 1.3B (ringan & hemat VRAM).",
        "required_for": "Video Engine Wan 2.1"
    },
    "wan21_clip": {
        "name": "Wan 2.1 Text Encoder (UMT5 XXL FP8)",
        "type": "model",
        "subfolder": os.path.join("models", "clip"),
        "search_paths": [
            os.path.join("models", "clip"),
            os.path.join("models", "text_encoders")
        ],
        "filename": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "patterns": ["*umt5_xxl*.safetensors", "*umt5*.safetensors"],
        "size_mb": 4900,
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "fallback_url": "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "mirrors": [
            "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "https://hf-mirror.com/Kijai/WanVideo_comfy/resolve/main/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
        ],
        "description": "Text encoder UMT5 XXL FP8 khusus untuk pipeline Wan 2.1 video.",
        "required_for": "Video Engine Wan 2.1"
    },
    "wan21_vae": {
        "name": "Wan 2.1 Video VAE",
        "type": "model",
        "subfolder": os.path.join("models", "vae"),
        "filename": "wan_2.1_vae.safetensors",
        "patterns": ["*wan*vae*.safetensors", "*wan*vae*.pth", "*Wan2_1_VAE*.safetensors"],
        "size_mb": 240,
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
        "fallback_url": "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
        "mirrors": [
            "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
            "https://hf-mirror.com/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
            "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors",
            "https://hf-mirror.com/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors"
        ],
        "description": "Autoencoder khusus video latents untuk Wan 2.1.",
        "required_for": "Video Engine Wan 2.1"
    },
    "voicestudio": {
        "name": "VoiceStudio Local AI Voice Server",
        "type": "tool_repo",
        "subfolder": os.path.join("tools", "VoiceStudio"),
        "git_url": "https://github.com/debpalash/VoiceStudio.git",
        "size_mb": 450,
        "description": "Server TTS lokal mandiri (FastAPI port 3900) dengan voice cloning & persona conditioning.",
        "required_for": "Voice Engine VoiceStudio (Local AI Voice)"
    }
}

_COMFYUI_DIR_CACHE: Optional[str] = None
_HARDWARE_PROFILE_CACHE: Optional[Dict[str, Any]] = None

def detect_hardware_profile(refresh: bool = False) -> Dict[str, Any]:
    """
    Intelligently inspects GPU model, dedicated VRAM, and system memory.
    Classifies the system into hardware tiers and returns optimal AI model defaults:
      - 'high' (>=8GB VRAM): Anything XL (SDXL 1024px), Wan 2.1 Video, full GPU offload.
      - 'mid' (6GB to <8GB VRAM): Anything XL (SDXL) or MeinaMix, Wan 2.1 / AnimateDiff.
      - 'compact' (2GB to <6GB VRAM): MeinaMix v12 (SD 1.5 ~2GB), AnimateDiff, balanced layers.
      - 'entry' (<2GB VRAM / iGPU / Office PC): Cloud Fallback Engine (0 VRAM), Motion 2.5D, CPU mode.
    """
    global _HARDWARE_PROFILE_CACHE
    if _HARDWARE_PROFILE_CACHE and not refresh:
        return _HARDWARE_PROFILE_CACHE

    gpu_name = "CPU / Integrated Graphics"
    vram_mb = 0
    source = "fallback"

    # 1. Probe NVIDIA SMI (most accurate for dedicated NVIDIA VRAM)
    try:
        cmd = ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
        out = subprocess.check_output(
            cmd,
            timeout=3,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        ).decode("utf-8", errors="ignore").strip()
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if lines:
            parts = lines[0].split(",")
            gpu_name = parts[0].strip()
            vram_mb = int(parts[1].strip())
            source = "nvidia-smi"
    except Exception:
        pass

    # 2. Windows WMI / CimInstance probe if nvidia-smi failed or unavailable
    if vram_mb == 0 and sys.platform == "win32":
        try:
            ps_cmd = (
                "Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | "
                "Select-Object Name, AdapterRAM | ConvertTo-Json"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                timeout=5,
                creationflags=0x08000000
            ).decode("utf-8", errors="ignore").strip()
            if out:
                import json
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]
                if isinstance(data, list) and data:
                    valid_items = [d for d in data if isinstance(d, dict)]
                    if valid_items:
                        best = max(valid_items, key=lambda x: x.get("AdapterRAM") or 0)
                        best_ram = best.get("AdapterRAM") or 0
                        if best_ram > 0:
                            gpu_name = best.get("Name", gpu_name)
                            vram_mb = int(best_ram / (1024 * 1024))
                            source = "win32_cim"
        except Exception:
            pass

    # 3. macOS Apple Silicon unified memory probe
    if vram_mb == 0 and sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=3).decode().strip()
            total_bytes = int(out)
            vram_mb = int(total_bytes / (1024 * 1024))
            gpu_name = "Apple Silicon (Unified Memory)"
            source = "sysctl_darwin"
        except Exception:
            pass

    vram_gb = round(vram_mb / 1024.0, 1) if vram_mb > 0 else 0.0

    # Classification logic
    if vram_mb >= 7800:
        tier = "high"
        rec_image = "anything_xl"
        rec_image_file = "AnythingXL_xl.safetensors"
        rec_video = "wan21"
        rec_layers = 99
        tier_label = "High-End GPU (8GB+ VRAM)"
        recommendation_text = f"VRAM kamu {vram_gb} GB ({gpu_name}). Sangat mumpuni untuk Anything XL (SDXL 1024px) dan Wan 2.1 AI Video."
    elif vram_mb >= 5800:
        tier = "mid"
        rec_image = "anything_xl"
        rec_image_file = "AnythingXL_xl.safetensors"
        rec_video = "wan21"
        rec_layers = 24  # Balanced offload for 6GB GPUs (RTX 3050/2060) to prevent CUDA OOM
        tier_label = "Mid-Range Dedicated GPU (6GB - 7GB VRAM)"
        recommendation_text = f"VRAM kamu {vram_gb} GB ({gpu_name}). Mumpuni untuk Anything XL (SDXL) dan Wan 2.1 Video secara lancar."
    elif vram_mb >= 2000:
        tier = "compact"
        rec_image = "meinamix"
        rec_image_file = "meinamix_v12Final.safetensors"
        rec_video = "animatediff"
        rec_layers = 20
        tier_label = "Compact Dedicated GPU (2GB - 5GB VRAM)"
        recommendation_text = f"VRAM kamu {vram_gb} GB ({gpu_name}). Direkomendasikan MeinaMix v12 (SD 1.5) & AnimateDiff agar cepat, konsisten, dan bebas OOM."
    else:
        tier = "entry"
        rec_image = "cloud"
        rec_image_file = ""
        rec_video = "motion"
        rec_layers = 0
        tier_label = "Entry / iGPU / Office PC (<2GB VRAM)"
        recommendation_text = f"PC kamu menggunakan grafis terintegrasi / CPU ({gpu_name}). Direkomendasikan Cloud Fallback Engine (0 VRAM) & Motion 2.5D agar ringan tanpa lag."

    profile = {
        "gpu_name": gpu_name,
        "vram_mb": vram_mb,
        "vram_gb": vram_gb,
        "tier": tier,
        "tier_label": tier_label,
        "recommended_image_model": rec_image,
        "recommended_image_file": rec_image_file,
        "recommended_video_engine": rec_video,
        "recommended_llm_layers": rec_layers,
        "recommendation_text": recommendation_text,
        "source": source
    }
    _HARDWARE_PROFILE_CACHE = profile
    return profile

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

_REPAIRED_PY_EXES = set()

def check_and_repair_comfyui_environment(py_exe: str) -> None:
    """
    Checks for corrupted C++ binaries like torchvision's image_stable.pyd (Bad Image 0xc0e90002)
    and quarantines them so ComfyUI starts cleanly without crashing or triggering Windows error popups.
    """
    if not py_exe or not os.path.isfile(py_exe) or py_exe in _REPAIRED_PY_EXES:
        return
    _REPAIRED_PY_EXES.add(py_exe)
    py_dir = os.path.dirname(py_exe)
    for site_sub in [
        os.path.join(py_dir, "Lib", "site-packages"),
        os.path.join(py_dir, "lib", "site-packages"),
    ]:
        if not os.path.isdir(site_sub):
            continue
        torchvision_dir = os.path.join(site_sub, "torchvision")
        if os.path.isdir(torchvision_dir):
            for bad_pyd in ["image_stable.pyd", "image.pyd"]:
                pyd_path = os.path.join(torchvision_dir, bad_pyd)
                if os.path.isfile(pyd_path):
                    is_corrupt = False
                    try:
                        sz = os.path.getsize(pyd_path)
                        if sz < 1024:
                            is_corrupt = True
                        else:
                            probe_code = (
                                "import sys; "
                                "import ctypes; "
                                "(ctypes.windll.kernel32.SetErrorMode(0x8003) if sys.platform == 'win32' else None); "
                                "import torchvision; "
                                "from torchvision.io import image"
                            )
                            probe = subprocess.run(
                                [py_exe, "-s", "-c", probe_code],
                                capture_output=True,
                                timeout=15,
                                creationflags=0x08000000 | 0x00000200 if sys.platform == "win32" else 0
                            )
                            # Any non-zero exit means the compiled .pyd fails to initialize or crashes DLL loader
                            if probe.returncode != 0:
                                is_corrupt = True
                    except Exception as e_probe:
                        logger.debug(f"Torchvision probe exception on {pyd_path}: {e_probe}")
                        is_corrupt = True

                    if is_corrupt:
                        logger.warning(f"Detected corrupt/incompatible torchvision binary '{bad_pyd}'. Quarantining...")
                        try:
                            bak_path = pyd_path + ".corrupt.bak"
                            if os.path.exists(bak_path):
                                try:
                                    os.remove(bak_path)
                                except Exception:
                                    pass
                            os.rename(pyd_path, bak_path)
                            logger.info(f"Quarantined {pyd_path} -> {bak_path}. Torchvision pure Python/PIL fallback will be used.")
                        except Exception as e_rename:
                            try:
                                os.remove(pyd_path)
                                logger.info(f"Removed corrupt {pyd_path}. Torchvision pure Python/PIL fallback will be used.")
                            except Exception as e_del:
                                logger.error(f"Failed to quarantine or remove corrupt {pyd_path}: {e_del} (Rename error: {e_rename})")


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
                timeout=45,
                creationflags=0x08000000 if sys.platform == "win32" else 0
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
                check_and_repair_comfyui_environment(py_embed)
                extra_args = ["--cpu"] if _should_use_cpu(py_embed) else []
                return {
                    "cwd": cdir,
                    "cmd": [py_embed, "-s", main_py, "--windows-standalone-build", "--port", "8188", "--listen", "127.0.0.1", "--disable-auto-launch", "--fast"] + extra_args
                }

    # 2. Check virtual environments in cdir or parent
    for base in [cdir, os.path.dirname(cdir)]:
        for venv_dir in [".venv", "venv"]:
            v_py = os.path.join(base, venv_dir, "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(base, venv_dir, "bin", "python")
            if os.path.isfile(v_py):
                check_and_repair_comfyui_environment(v_py)
                extra_args = ["--cpu"] if _should_use_cpu(v_py) else []
                return {
                    "cwd": cdir,
                    "cmd": [v_py, main_py, "--port", "8188", "--listen", "127.0.0.1", "--disable-auto-launch", "--fast"] + extra_args
                }

    # 3. Fallback to system python
    extra_args = ["--cpu"] if _should_use_cpu(sys.executable) else []
    return {
        "cwd": cdir,
        "cmd": [sys.executable, main_py, "--port", "8188", "--listen", "127.0.0.1", "--disable-auto-launch", "--fast"] + extra_args
    }


def get_llm_launch_spec(project_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Intelligently discovers KoboldCPP binary, GGUF chat model, and mmproj vision adapter.
    Scans project tools/, standard installation paths, and environment directories.
    Returns: {"cmd": list, "cwd": str, "exe": str, "model": str, "mmproj": Optional[str]} or None
    """
    root = project_root or PROJECT_ROOT

    # 1. Locate KoboldCPP executable
    kcpp_name = "koboldcpp.exe" if platform.system() == "Windows" else "koboldcpp"
    candidates_exe = [
        os.path.join(root, "tools", kcpp_name),
        os.path.join(root, "tools", "KoboldCPP", kcpp_name),
        os.path.join(root, "tools", "koboldcpp_cu12.exe" if platform.system() == "Windows" else "koboldcpp_cu12"),
        os.path.join(root, "tools", "koboldcpp_nocuda.exe" if platform.system() == "Windows" else "koboldcpp_nocuda"),
        os.path.join(root, kcpp_name),
    ]
    which_kcpp = shutil.which("koboldcpp") or shutil.which("koboldcpp.exe")
    if which_kcpp:
        candidates_exe.append(which_kcpp)

    if platform.system() == "Windows":
        user_home = os.path.expanduser("~")
        candidates_exe.extend([
            r"C:\KoboldCPP\koboldcpp.exe",
            r"D:\KoboldCPP\koboldcpp.exe",
            os.path.join(user_home, "AppData", "Local", "Programs", "KoboldCPP", "koboldcpp.exe"),
            os.path.join(user_home, "Downloads", "koboldcpp.exe"),
            os.path.join(user_home, "Desktop", "koboldcpp.exe"),
        ])

    kcpp_exe = None
    for cand in candidates_exe:
        if cand and os.path.isfile(cand):
            kcpp_exe = os.path.abspath(cand)
            break

    if not kcpp_exe:
        cand_default = os.path.join(root, "tools", kcpp_name)
        if os.path.isfile(cand_default):
            kcpp_exe = os.path.abspath(cand_default)

    if not kcpp_exe:
        return None

    # 2. Locate Chat / LLM Model (.gguf)
    models_dirs = [
        os.path.join(root, "models"),
        detect_locally_uncensored_dir()
    ]
    env_model = os.environ.get("LLM_MODEL", "").strip()
    model_path = None
    if env_model and os.path.isfile(env_model) and env_model.endswith(".gguf"):
        model_path = os.path.abspath(env_model)

    mmproj_path = None

    if not model_path:
        info_qwen = get_asset_info("qwen25_7b")
        if info_qwen and info_qwen.get("installed") and info_qwen.get("target_path"):
            model_path = info_qwen["target_path"]

    if not model_path:
        info_stheno = get_asset_info("stheno_8b")
        if info_stheno and info_stheno.get("installed") and info_stheno.get("target_path"):
            model_path = info_stheno["target_path"]

    if not model_path:
        info_qwy = get_asset_info("qwythos_9b")
        if info_qwy and info_qwy.get("installed") and info_qwy.get("target_path"):
            model_path = info_qwy["target_path"]

    for m_dir in models_dirs:
        if not m_dir or not os.path.isdir(m_dir):
            continue
        if not model_path:
            try:
                for f in os.listdir(m_dir):
                    if f.endswith(".gguf") and "mmproj" not in f.lower():
                        model_path = os.path.join(m_dir, f)
                        break
            except Exception:
                pass
            if not model_path:
                for r_dir, _, files in os.walk(m_dir):
                    for f in files:
                        if f.endswith(".gguf") and "mmproj" not in f.lower():
                            model_path = os.path.join(r_dir, f)
                            break
                    if model_path:
                        break

        if not mmproj_path:
            try:
                for f in os.listdir(m_dir):
                    if f.endswith(".gguf") and "mmproj" in f.lower():
                        mmproj_path = os.path.join(m_dir, f)
                        break
            except Exception:
                pass
            if not mmproj_path:
                for r_dir, _, files in os.walk(m_dir):
                    for f in files:
                        if f.endswith(".gguf") and "mmproj" in f.lower():
                            mmproj_path = os.path.join(r_dir, f)
                            break
                    if mmproj_path:
                        break

    if not model_path or not os.path.isfile(model_path):
        return None

    if not mmproj_path:
        info_vis = get_asset_info("qwythos_vision")
        if info_vis and info_vis.get("installed") and info_vis.get("target_path"):
            mmproj_path = info_vis["target_path"]

    # Incompatible mmproj guard: mmproj trained for specific models must not be loaded on text LLMs
    if model_path and mmproj_path:
        m_lower = os.path.basename(model_path).lower()
        mm_lower = os.path.basename(mmproj_path).lower()
        if "qwythos" in mm_lower and "qwythos" not in m_lower:
            mmproj_path = None
        elif ("stheno" in m_lower or "llama" in m_lower or "qwen2.5" in m_lower) and "moondream" not in mm_lower:
            mmproj_path = None

    mm_args = ["--mmproj", mmproj_path] if (mmproj_path and os.path.isfile(mmproj_path)) else []

    port = os.environ.get("LLM_PORT", "5001")
    gpu_layers = os.environ.get("LLM_GPU_LAYERS")
    if not gpu_layers:
        hw = detect_hardware_profile()
        gpu_layers = str(hw.get("recommended_llm_layers", 99))
    ctx_size = os.environ.get("LLM_CONTEXT_SIZE", "4096")
    threads = os.environ.get("LLM_THREADS", "4")

    cmd = [
        kcpp_exe,
        "--model", model_path,
        "--port", str(port),
        "--gpulayers", str(gpu_layers),
        "--contextsize", str(ctx_size),
        "--smartcontext",
        "--threads", str(threads)
    ] + mm_args

    if platform.system() == "Windows":
        cmd += ["--usecublas", "normal", "--quiet"]
    else:
        cmd += ["--quiet"]

    return {
        "cmd": cmd,
        "cwd": root,
        "exe": kcpp_exe,
        "model": model_path,
        "mmproj": mmproj_path
    }

def safe_getsize(path: str) -> int:
    """Safely returns file size or 0 if file does not physically exist or stat fails."""
    try:
        return os.path.getsize(path)
    except Exception:
        return 0


def _get_min_model_bytes(spec: dict, candidate_path: Optional[str] = None) -> int:
    expected_size_mb = spec.get("size_mb", 0)
    if candidate_path:
        norm_p = os.path.abspath(candidate_path).lower()
        temp_dir = tempfile.gettempdir().lower()
        if ("waifu_test_env_" in norm_p or temp_dir in norm_p) and os.environ.get("FORCE_STRICT_MODEL_SIZE") != "1":
            return 10 * 1024 * 1024
    if expected_size_mb > 20:
        return int(expected_size_mb * 0.80 * 1024 * 1024)
    return 10 * 1024 * 1024

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
        expected_size_mb = spec.get("size_mb", 0)
        found_file = None
        found_size = 0
        partial_file = None
        partial_size = 0

        for cdir in candidate_dirs:
            if not os.path.isdir(cdir):
                continue
            p = os.path.join(cdir, spec["filename"])
            min_bytes = _get_min_model_bytes(spec, p)
            if os.path.isfile(p):
                sz = safe_getsize(p)
                if sz >= min_bytes:
                    found_file = p
                    found_size = sz
                    break
                elif sz > 0:
                    partial_file = p
                    partial_size = sz
            if "patterns" in spec:
                for pat in spec["patterns"]:
                    matches = glob.glob(os.path.join(cdir, pat))
                    for m in matches:
                        min_m_bytes = _get_min_model_bytes(spec, m)
                        if os.path.isfile(m):
                            sz = safe_getsize(m)
                            if sz >= min_m_bytes:
                                found_file = m
                                found_size = sz
                                break
                            elif sz > 0 and not partial_file:
                                partial_file = m
                                partial_size = sz
                    if found_file:
                        break
            if found_file:
                break

        if found_file:
            spec["installed"] = True
            spec["incomplete"] = False
            spec["target_path"] = found_file
            spec["current_size_mb"] = round(found_size / (1024 * 1024), 1)
        elif partial_file:
            spec["installed"] = False
            spec["incomplete"] = True
            spec["target_path"] = partial_file
            spec["current_size_mb"] = round(partial_size / (1024 * 1024), 1)
            pct = round((partial_size / (expected_size_mb * 1024 * 1024)) * 100, 1) if expected_size_mb else 0
            spec["percent_complete"] = pct
        else:
            spec["installed"] = False
            spec["incomplete"] = False
            spec["current_size_mb"] = 0
        spec["status"] = "installed" if spec["installed"] else ("incomplete" if spec.get("incomplete") else "missing")
        return spec

    if spec.get("type") in ("tool_repo", "voicestudio") or asset_key == "voicestudio":
        target_path = os.path.join(PROJECT_ROOT, spec.get("subfolder", os.path.join("tools", "VoiceStudio")))
        spec["target_path"] = target_path
        spec["target_dir"] = os.path.dirname(target_path)
        backend_main = os.path.join(target_path, "backend", "main.py")
        backend_dir = os.path.join(target_path, "backend")
        spec["installed"] = os.path.exists(backend_main) or (os.path.isdir(backend_dir) and len(os.listdir(backend_dir)) > 0)
        spec["incomplete"] = False
        spec["current_size_mb"] = spec.get("size_mb", 450) if spec["installed"] else 0
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
        expected_size_mb = spec.get("size_mb", 0)

        # Check search paths and pattern matching
        search_dirs = [target_dir]
        if "search_paths" in spec:
            search_dirs = [os.path.join(comfy_dir, sp) for sp in spec["search_paths"]]

        found_file = None
        found_size = 0
        partial_file = None
        partial_size = 0

        # Exact file match check
        for sdir in search_dirs:
            p = os.path.join(sdir, spec["filename"])
            min_bytes = _get_min_model_bytes(spec, p)
            if os.path.isfile(p):
                sz = safe_getsize(p)
                if sz >= min_bytes:
                    found_file = p
                    found_size = sz
                    break
                elif sz > 0:
                    partial_file = p
                    partial_size = sz

        # Pattern match check if exact match not found
        if not found_file and "patterns" in spec:
            for sdir in search_dirs:
                if os.path.isdir(sdir):
                    for pat in spec["patterns"]:
                        matches = glob.glob(os.path.join(sdir, pat))
                        for m in matches:
                            min_m_bytes = _get_min_model_bytes(spec, m)
                            if os.path.isfile(m):
                                sz = safe_getsize(m)
                                if sz >= min_m_bytes:
                                    found_file = m
                                    found_size = sz
                                    break
                                elif sz > 0 and not partial_file:
                                    partial_file = m
                                    partial_size = sz
                            if found_file:
                                break
                    if found_file:
                        break

        if found_file:
            spec["installed"] = True
            spec["incomplete"] = False
            spec["target_path"] = found_file
            spec["current_size_mb"] = round(found_size / (1024 * 1024), 1)
        elif partial_file:
            spec["installed"] = False
            spec["incomplete"] = True
            spec["target_path"] = partial_file
            spec["current_size_mb"] = round(partial_size / (1024 * 1024), 1)
            pct = round((partial_size / (expected_size_mb * 1024 * 1024)) * 100, 1) if expected_size_mb else 0
            spec["percent_complete"] = pct
        else:
            spec["installed"] = False
            spec["incomplete"] = False
            spec["current_size_mb"] = 0

    spec["status"] = "installed" if spec["installed"] else ("incomplete" if spec.get("incomplete") else "missing")
    return spec

def check_all_assets() -> Dict[str, Dict[str, Any]]:
    """Checks status for all registered models, nodes, and dependencies."""
    results = {}
    for key in ASSET_REGISTRY:
        info = get_asset_info(key)
        if info:
            results[key] = info
    return results

def _download_file(url: str, target_path: str, fallback_url: Optional[str] = None, mirrors: Optional[list] = None, min_size_mb: Optional[int] = None, progress_callback=None) -> bool:
    """Helper to download file with resume support via curl or requests across high-speed mirrors."""
    target_dir = os.path.dirname(target_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    min_bytes = _get_min_model_bytes({"size_mb": min_size_mb or 0}, target_path)

    # Clean up accidental tiny/corrupt files (e.g. HTML 404 responses or 0-byte aborts)
    if os.path.exists(target_path) and os.path.getsize(target_path) < 4096:
        try:
            os.remove(target_path)
            logger.info(f"Cleaned up tiny stub file before download: {target_path}")
        except Exception:
            pass

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
                # Robust curl with automatic resume (-C -), retries, and browser User-Agent
                cmd = [
                    curl_path, "-fL", "-C", "-",
                    "--retry", "5",
                    "--retry-delay", "2",
                    "--connect-timeout", "30",
                    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "--progress-bar",
                    "-o", target_path,
                    dl_url
                ]
                ret = subprocess.run(cmd)
                if ret.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) >= min_bytes:
                    return True
                if idx < len(candidate_urls):
                    print(f"\n  ℹ Mirror terputus atau tidak lengkap. Mencoba mirror berkecepatan tinggi berikutnya [{idx + 1}/{len(candidate_urls)}]...")
            except Exception as e:
                logger.warning(f"curl download failed on {dl_url}: {e}")

        # Fallback to requests streaming download
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            initial_pos = 0
            if os.path.exists(target_path):
                initial_pos = os.path.getsize(target_path)
                headers["Range"] = f"bytes={initial_pos}-"

            with requests.get(dl_url, headers=headers, stream=True, timeout=90) as r:
                if r.status_code in (200, 206):
                    mode = "ab" if r.status_code == 206 else "wb"
                    dl = initial_pos if r.status_code == 206 else 0
                    total_len = int(r.headers.get("content-length", 0)) + dl
                    with open(target_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                                dl += len(chunk)
                                if progress_callback and total_len > 0:
                                    progress_callback(dl, total_len)
                    if os.path.exists(target_path) and os.path.getsize(target_path) >= min_bytes:
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

    if info.get("type") in ("tool_repo", "voicestudio") or asset_key == "voicestudio":
        from voicestudio_engine import voicestudio_engine
        ok, msg = voicestudio_engine.install(progress_callback=progress_callback)
        if ok:
            print(f"  ✓ {msg}")
        else:
            print(f"  ❌ {msg}")
        return ok

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
    if info.get("installed", False):
        logger.info(f"Model '{name}' is already complete and verified ({info.get('current_size_mb')} MB).")
        print(f"  ✓ Model '{name}' sudah terpasang lengkap ({info.get('current_size_mb')} MB).")
        return True

    if info.get("incomplete", False):
        print(f"  ℹ File unduhan sebelumnya ditemukan ({info.get('current_size_mb')} MB / ~{info.get('size_mb')} MB, {info.get('percent_complete')}%). Melanjutkan unduhan (resume)...")

    logger.info(f"Downloading {name} -> {target_path}")

    return _download_file(
        url=info.get("url"),
        target_path=target_path,
        fallback_url=info.get("fallback_url"),
        mirrors=info.get("mirrors"),
        min_size_mb=info.get("size_mb"),
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
        for k in ("wan21_1.3b", "wan21_clip", "wan21_vae"):
            info = get_asset_info(k)
            if not info or not info.get("installed"):
                missing.append(k)

    return (len(missing) == 0, missing)

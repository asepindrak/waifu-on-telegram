"""
agy_quota_manager.py - Smart Daily Quota & Smart Fallback Manager for Google Antigravity (AGY).

Tracks daily quota consumption and exhaustion for AGY Image Generator.
When AGY exhausts its daily quota (429 RESOURCE_EXHAUSTED / Rate Limit / Capacity limit),
this manager locks AGY into smart fallback for the remainder of the calendar day.
At midnight of the following day, AGY is automatically unlocked and retried.
"""

import os
import json
import time
import datetime
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("AgyQuotaManager")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
QUOTA_FILE = os.path.join(DATA_DIR, "agy_quota_state.json")

# Quota error keyword signatures from Google Antigravity / Gemini / Bridge
AGY_QUOTA_SIGNATURES = [
    "429",
    "resource_exhausted",
    "quota limit",
    "quota exceeded",
    "exceeded your quota",
    "exceeded your current quota",
    "capacity on the underlying image",
    "capacity on the underlying",
    "rate limit",
    "ratelimit",
    "too many requests",
    "daily limit",
    "per day",
    "limit reached",
    "quota_exhausted",
    "insufficient_quota"
]


def _ensure_data_dir() -> None:
    """Ensures data directory exists."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass


def _read_quota_state() -> Dict[str, Any]:
    """Reads persistent quota state from data/agy_quota_state.json."""
    if not os.path.exists(QUOTA_FILE):
        return {}
    try:
        with open(QUOTA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.debug(f"Failed to read agy_quota_state.json: {e}")
        return {}


def _write_quota_state(state: Dict[str, Any]) -> None:
    """Writes persistent quota state to data/agy_quota_state.json atomically."""
    _ensure_data_dir()
    tmp_file = f"{QUOTA_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        if os.path.exists(tmp_file):
            if os.path.exists(QUOTA_FILE):
                try:
                    os.replace(tmp_file, QUOTA_FILE)
                except Exception:
                    os.remove(QUOTA_FILE)
                    os.rename(tmp_file, QUOTA_FILE)
            else:
                os.rename(tmp_file, QUOTA_FILE)
    except Exception as e:
        logger.warning(f"Failed to write agy_quota_state.json: {e}")
        try:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        except Exception:
            pass


def is_agy_quota_error(text: Optional[str]) -> bool:
    """Checks if an error string contains AGY / Gemini rate limit or quota exhaustion signatures."""
    if not text:
        return False
    lowered = str(text).lower()
    return any(sig in lowered for sig in AGY_QUOTA_SIGNATURES)


def record_agy_image_quota_exhausted(reason: str = "") -> None:
    """
    Marks AGY Image Generator quota as exhausted for today.
    Smart Fallback will remain active for the rest of today until tomorrow 00:00.
    """
    today_str = datetime.date.today().isoformat()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    state = _read_quota_state()
    state["image"] = {
        "active": True,
        "exhausted_date": today_str,
        "exhausted_time": now_str,
        "exhausted_timestamp": time.time(),
        "reason": (reason or "429 RESOURCE_EXHAUSTED")[:300]
    }
    _write_quota_state(state)
    logger.warning(
        f"🚨 [Smart Fallback] Kuota harian model gambar AGY habis pada {now_str}. "
        f"Mengaktifkan Smart Fallback otomatis untuk sisa hari ini ({today_str}). "
        f"AGY akan diuji kembali secara otomatis besok."
    )


def is_agy_image_quota_exhausted() -> bool:
    """
    Checks if AGY Image Generator quota is exhausted for the current calendar day.
    If a new day has arrived, automatically clears the exhausted state and returns False.
    """
    state = _read_quota_state()
    img_state = state.get("image", {})
    if not img_state or not img_state.get("active", False):
        return False

    exhausted_date = img_state.get("exhausted_date", "")
    today_str = datetime.date.today().isoformat()

    if exhausted_date == today_str:
        # Same calendar day: quota is still exhausted
        return True
    else:
        # Calendar day has rolled over to tomorrow or later: reset automatically!
        img_state["active"] = False
        img_state["reset_date"] = today_str
        img_state["reset_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state["image"] = img_state
        _write_quota_state(state)
        logger.info(
            f"🌅 [Smart Fallback] Hari baru telah tiba ({today_str}). "
            f"Status kuota harian AGY di-reset otomatis. Mencoba kembali Google Antigravity."
        )
        return False


def reset_agy_image_quota() -> None:
    """Manually resets the AGY image quota lock (e.g. for testing or manual override)."""
    state = _read_quota_state()
    if "image" in state:
        state["image"]["active"] = False
        state["image"]["manually_reset_at"] = time.time()
        _write_quota_state(state)
    logger.info("[Smart Fallback] Kuota harian AGY gambar di-reset secara manual.")


def has_local_image_models() -> bool:
    """
    Determines if local image generation models (ComfyUI checkpoints) exist on this PC.
    If True, fallback MUST route to local ComfyUI instead of external Cloud (Pollinations).
    """
    # 1. Check via setup.scan_image_models()
    try:
        import setup
        ckpts = setup.scan_image_models()
        if ckpts and len(ckpts) > 0:
            return True
    except Exception:
        pass

    # 2. Check via asset_manager.detect_comfyui_dir()
    try:
        import asset_manager
        comfy_dir = asset_manager.detect_comfyui_dir()
        if comfy_dir:
            chk_dir = os.path.join(comfy_dir, "models", "checkpoints")
            if os.path.exists(chk_dir):
                for f in os.listdir(chk_dir):
                    if f.lower().endswith((".safetensors", ".ckpt")):
                        p = os.path.join(chk_dir, f)
                        if os.path.isfile(p) and os.path.getsize(p) >= (10 * 1024 * 1024):
                            return True
    except Exception:
        pass

    # 3. Check environment checkpoint configuration
    env_ckpt = (
        os.environ.get("COMFYUI_CHECKPOINT", "").strip() or
        os.environ.get("SFW_COMFYUI_CHECKPOINT", "").strip()
    )
    if env_ckpt and env_ckpt.lower() not in ("none", "false", "disabled", ""):
        return True

    return False


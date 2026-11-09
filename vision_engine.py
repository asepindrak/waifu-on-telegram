"""
vision_engine.py - Intelligent Multimodal Vision Perceptor for Waifu on Telegram
Coordinates visual perception between:
1. AGY Bridge (Google Antigravity CLI / Gemini) -> 0 VRAM Cloud-like perception.
2. Local Moondream2 (1.8B) -> Ultra-compact local vision when running Local LLM (Stheno 8B).
"""

import os
import sys
import base64
import logging
import subprocess
import time
import requests
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("VisionEngine")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import asset_manager

MOONDREAM_PORT = int(os.environ.get("MOONDREAM_PORT", "5002"))


class VisionEngine:
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.moondream_proc: Optional[subprocess.Popen] = None

    def is_agy_active(self) -> bool:
        """Checks if AGY Bridge is configured or active for 0-VRAM vision."""
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "").lower().strip()
        llm_base = os.environ.get("LLM_BASE_URL", "").lower().strip()
        sfw_base = os.environ.get("SFW_LLM_BASE_URL", "").lower().strip()
        return sfw_p == "agy" or ":8001" in llm_base or ":8001" in sfw_base

    def is_moondream_installed(self) -> bool:
        """Checks if both Moondream text model and mmproj are present."""
        info_t = asset_manager.get_asset_info("moondream_text")
        info_m = asset_manager.get_asset_info("moondream_mmproj")
        return bool(info_t and info_t.get("installed") and info_m and info_m.get("installed"))

    def ensure_moondream_running(self, timeout_seconds: int = 15) -> bool:
        """Starts Moondream on port 5002 if not already active."""
        from idle_engine import is_port_listening
        if is_port_listening(MOONDREAM_PORT):
            return True

        if not self.is_moondream_installed():
            logger.warning("Moondream assets not installed. Attempting download or fallback...")
            return False

        info_t = asset_manager.get_asset_info("moondream_text")
        info_m = asset_manager.get_asset_info("moondream_mmproj")
        text_path = info_t["target_path"]
        mmproj_path = info_m["target_path"]

        kcpp_spec = asset_manager.get_llm_launch_spec()
        kcpp_exe = kcpp_spec.get("exe") if kcpp_spec else None
        if not kcpp_exe or not os.path.isfile(kcpp_exe):
            kcpp_exe = os.path.join(self.project_root, "tools", "koboldcpp.exe" if sys.platform == "win32" else "koboldcpp")

        if not os.path.isfile(kcpp_exe):
            logger.error("KoboldCPP binary not found to run Moondream.")
            return False

        cmd = [
            kcpp_exe,
            "--model", text_path,
            "--mmproj", mmproj_path,
            "--port", str(MOONDREAM_PORT),
            "--contextsize", "2048",
            "--quiet"
        ]

        logger.info(f"⚡ Starting Moondream Vision Engine on port {MOONDREAM_PORT}...")
        popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
        try:
            log_path = os.path.join(self.project_root, "moondream.log")
            with open(log_path, "a", encoding="utf-8") as f_log:
                self.moondream_proc = subprocess.Popen(cmd, cwd=self.project_root, stdout=f_log, stderr=f_log, **popen_kwargs)
        except Exception as e:
            logger.error(f"Failed to spawn Moondream: {e}")
            return False

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if is_port_listening(MOONDREAM_PORT):
                logger.info("✓ Moondream Vision Engine is ready on port 5002.")
                return True
            time.sleep(0.5)

        logger.warning(f"Timed out waiting for Moondream on port {MOONDREAM_PORT}.")
        return False

    def describe_with_agy(self, image_bytes: bytes, prompt: str = "") -> Optional[str]:
        """Queries AGY Bridge (port 8001) for 0-VRAM vision analysis."""
        from idle_engine import is_port_listening
        if not is_port_listening(8001):
            logger.info("Auto-waking AGY Bridge on port 8001 for 0-VRAM vision...")
            try:
                from health_engine import health_engine
                health_engine.heal_agy()
            except Exception:
                pass

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        query_text = prompt or "Deskripsikan apa yang terlihat di foto ini dengan akurat, jelas, dan ringkas dalam 1-2 kalimat bahasa Indonesia."
        payload = {
            "model": "gemini-3.8-flash-medium",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                }
            ],
            "max_tokens": 150
        }

        try:
            r = requests.post("http://127.0.0.1:8001/v1/chat/completions", json=payload, timeout=25)
            if r.status_code == 200:
                data = r.json()
                content = data["choices"][0]["message"].get("content", "").strip()
                if content:
                    logger.info(f"✓ AGY Bridge Vision (0 VRAM): '{content[:80]}...'")
                    return content
        except Exception as e:
            logger.warning(f"AGY vision request failed: {e}")
        return None

    def describe_with_moondream(self, image_bytes: bytes, prompt: str = "") -> Optional[str]:
        """Queries local Moondream (port 5002) for compact vision analysis."""
        if not self.ensure_moondream_running():
            return None

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        query_text = prompt or "Describe what is shown in this image clearly and concisely in 1-2 sentences."
        payload = {
            "model": "moondream",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                }
            ],
            "max_tokens": 120
        }

        try:
            r = requests.post(f"http://127.0.0.1:{MOONDREAM_PORT}/v1/chat/completions", json=payload, timeout=25)
            if r.status_code == 200:
                data = r.json()
                content = data["choices"][0]["message"].get("content", "").strip()
                if content:
                    logger.info(f"✓ Moondream Vision (Local): '{content[:80]}...'")
                    return content
        except Exception as e:
            logger.warning(f"Moondream vision request failed: {e}")
        return None

    def describe_image(self, image_bytes: bytes, user_caption: str = "") -> Optional[str]:
        """
        Main entry point for image perception:
        - If AGY Bridge is active: Uses AGY Bridge (0 VRAM).
        - If Local LLM (Stheno 8B) is active: Uses Moondream2.
        - Fallbacks seamlessly between them.
        """
        if self.is_agy_active():
            logger.info("Multimodal Vision: AGY Bridge is active (0 VRAM mode).")
            desc = self.describe_with_agy(image_bytes, prompt=user_caption)
            if desc:
                return desc

        # Local LLM / Stheno mode -> Use Moondream
        logger.info("Multimodal Vision: Using Moondream2 local vision engine.")
        desc = self.describe_with_moondream(image_bytes, prompt=user_caption)
        if desc:
            return desc

        # Secondary fallback if Moondream was not yet ready or failed
        if not self.is_agy_active():
            desc_agy = self.describe_with_agy(image_bytes, prompt=user_caption)
            if desc_agy:
                return desc_agy

        return None


vision_engine = VisionEngine()


def inject_visual_context_into_messages(messages: List[Dict[str, Any]], visual_desc: str) -> List[Dict[str, Any]]:
    """
    Augments the last user turn with the extracted visual description so text-only
    roleplay models (like L3-8B-Stheno-v3.4) can react naturally as if they saw it.
    """
    if not visual_desc or not messages:
        return messages

    new_messages = []
    for i, m in enumerate(messages):
        if i == len(messages) - 1 and m.get("role") == "user":
            orig_content = m.get("content", "")
            if isinstance(orig_content, list):
                # Multimodal format -> extract raw text
                text_part = ""
                for part in orig_content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_part = part.get("text", "")
                orig_content = text_part

            augmented = f"[Foto dari user memperlihatkan: {visual_desc}]\n{orig_content}".strip()
            new_messages.append({"role": "user", "content": augmented})
        else:
            new_messages.append(m)

    return new_messages


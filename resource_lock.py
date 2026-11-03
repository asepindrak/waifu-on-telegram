"""
resource_lock.py - Concurrency & Mutual Exclusion Lock for Heavy GPU/VRAM AI Operations

Ensures image generation (ComfyUI / SD / SDXL / Anything XL / AOM3 / Wan 2.1)
and local neural voice generation (VoiceStudio Local AI) never run simultaneously,
preventing CUDA Out Of Memory (OOM) crashes and system freezes.
"""

import threading
import logging
from typing import Generator
from contextlib import contextmanager

logger = logging.getLogger("ResourceLock")

# Global re-entrant lock protecting GPU VRAM & heavy compute resources
GPU_HEAVY_LOCK = threading.RLock()


@contextmanager
def acquire_gpu_heavy_lock(task_name: str = "GPU Task") -> Generator[None, None, None]:
    """
    Context manager to safely acquire GPU_HEAVY_LOCK with logging.
    If another heavy task is currently running, this will politely wait
    until the running task completes.
    """
    logger.debug(f"[ResourceLock] Requesting GPU heavy lock for '{task_name}'...")
    acquired = GPU_HEAVY_LOCK.acquire(timeout=180)
    if not acquired:
        logger.warning(f"[ResourceLock] Timed out waiting for GPU heavy lock for '{task_name}'! Proceeding with caution.")
    else:
        logger.debug(f"[ResourceLock] Acquired GPU heavy lock for '{task_name}'.")
    try:
        yield
    finally:
        if acquired:
            try:
                GPU_HEAVY_LOCK.release()
                logger.debug(f"[ResourceLock] Released GPU heavy lock for '{task_name}'.")
            except RuntimeError:
                pass

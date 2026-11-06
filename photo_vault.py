"""
💖 WAIFU ON TELEGRAM - SMART PHOTO VAULT & ARCHIVE MANAGER 📸
Saves locally generated photos with rich metadata (persona, outfit, scene, tags).
Provides semantic retrieval fallback when local ComfyUI is offline or busy,
eliminating the need for low-quality cloud generators.
"""

import os
import re
import json
import uuid
import time
import logging
from typing import Optional, Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(PROJECT_ROOT, "data", "photo_vault")
CATALOG_PATH = os.path.join(VAULT_DIR, "catalog.json")
USER_SEEN_PATH = os.path.join(VAULT_DIR, "user_seen.json")

# Stopwords to filter out when tokenizing scenes and queries (Indonesian + English)
STOPWORDS = {
    "dan", "yang", "di", "ke", "dari", "ini", "itu", "untuk", "pada", "adalah",
    "dengan", "lagi", "mau", "dong", "aku", "kamu", "babe", "sayang", "kirim",
    "foto", "pap", "ya", "yaa", "dong", "bisa", "tolong", "coba", "liat", "lihat",
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "wearing", "holding", "girl", "solo", "looking", "viewer"
}

def _ensure_vault_dir(persona: str = "") -> str:
    """Ensures vault directory and persona subfolder exist."""
    target = os.path.join(VAULT_DIR, persona) if persona else VAULT_DIR
    os.makedirs(target, exist_ok=True)
    return target

def _tokenize(text: str) -> List[str]:
    """Extracts meaningful alphanumeric lowercase tokens."""
    if not text:
        return []
    words = re.findall(r'[a-zA-Z0-9_]+', text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]

def load_catalog() -> List[Dict[str, Any]]:
    """Loads the photo catalog metadata JSON file."""
    if not os.path.exists(CATALOG_PATH):
        return []
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load photo catalog: {e}")
        return []

def save_catalog(catalog: List[Dict[str, Any]]) -> bool:
    """Saves the photo catalog atomically."""
    _ensure_vault_dir()
    temp_path = CATALOG_PATH + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, CATALOG_PATH)
        return True
    except Exception as e:
        logger.error(f"Failed to save photo catalog: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False

def load_user_seen() -> Dict[str, List[str]]:
    """Loads map of user_id -> list of seen photo filenames."""
    path = os.path.join(VAULT_DIR, "user_seen.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load user seen photo history: {e}")
        return {}

def mark_photo_seen_by_user(user_id: Optional[Any], filename: str):
    """Records that a user has received this photo so it is never repeated."""
    if not user_id or not filename:
        return
    u_str = str(user_id)
    _ensure_vault_dir()
    seen_map = load_user_seen()
    user_list = seen_map.setdefault(u_str, [])
    if filename not in user_list:
        user_list.append(filename)
        if len(user_list) > 500:
            seen_map[u_str] = user_list[-500:]
        path = os.path.join(VAULT_DIR, "user_seen.json")
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(seen_map, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, path)
        except Exception as e:
            logger.error(f"Failed to save user seen history: {e}")

def save_photo_to_vault(
    img_bytes: bytes,
    persona: str,
    scene: str,
    outfit_label: str = "",
    is_nude: bool = False,
    visual_prompt: str = "",
    user_query: str = "",
    aspect_ratio: str = "3:4"
) -> Optional[Dict[str, Any]]:
    """
    Saves a newly generated high-quality photo into the local photo vault
    along with its semantic metadata for future intelligent retrieval.
    """
    if not img_bytes:
        return None

    persona_key = (persona or "runa").lower().strip()
    persona_dir = _ensure_vault_dir(persona_key)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    photo_id = uuid.uuid4().hex[:8]
    filename = f"{persona_key}_{timestamp}_{photo_id}.jpg"
    full_path = os.path.join(persona_dir, filename)

    # Save image file
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        im.save(full_path, format="JPEG", quality=95, optimize=True)
    except Exception:
        # Fallback raw write
        try:
            with open(full_path, "wb") as f:
                f.write(img_bytes)
        except Exception as e:
            logger.error(f"Failed to write image to vault: {e}")
            return None

    # Compute semantic tags
    tag_pool = []
    tag_pool.extend(_tokenize(scene))
    tag_pool.extend(_tokenize(outfit_label))
    tag_pool.extend(_tokenize(user_query))
    # Deduplicate while preserving order
    seen = set()
    tags = []
    for t in tag_pool:
        if t not in seen:
            seen.add(t)
            tags.append(t)

    rel_path = os.path.relpath(full_path, PROJECT_ROOT).replace("\\", "/")

    entry = {
        "id": photo_id,
        "filename": filename,
        "file_path": rel_path,
        "persona": persona_key,
        "scene": scene,
        "outfit_label": outfit_label,
        "is_nude": bool(is_nude),
        "user_query": user_query,
        "aspect_ratio": aspect_ratio,
        "tags": tags,
        "visual_prompt": visual_prompt[:300] if visual_prompt else "",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "usage_count": 0,
        "last_used": None
    }

    catalog = load_catalog()
    catalog.append(entry)
    save_catalog(catalog)

    logger.info(f"Saved photo to vault: {rel_path} (Tags: {', '.join(tags[:6])})")
    return entry

def find_matching_photo(
    persona: str,
    scene: str = "",
    outfit_label: str = "",
    is_nude: bool = False,
    user_query: str = "",
    user_id: Optional[Any] = None
) -> Optional[Tuple[bytes, Dict[str, Any]]]:
    """
    Finds a relevant, UNIQUE previously generated photo from the vault.
    Strictly respects persona, NSFW/SFW safety boundary, and user unseen history.
    Never repeats photos that user has already received when MEDIA_VAULT_REUSE is false.
    Returns: (image_bytes, metadata_entry) or None.
    """
    persona_key = (persona or "runa").lower().strip()
    catalog = load_catalog()
    if not catalog:
        return None

    # Load seen photo history for this user
    user_seen_set = set()
    if user_id:
        user_seen_set = set(load_user_seen().get(str(user_id), []))

    allow_reuse = os.environ.get("MEDIA_VAULT_REUSE", "false").lower() in ("true", "1", "yes")

    # Query tokens
    query_tokens = set(_tokenize(user_query) + _tokenize(scene) + _tokenize(outfit_label))

    candidates = []
    for entry in catalog:
        # Strict Persona Check
        if entry.get("persona") != persona_key:
            continue
        # Strict Nude/SFW Check (never mix nude with regular or vice versa)
        if bool(entry.get("is_nude", False)) != bool(is_nude):
            continue

        fname = entry.get("filename", "")
        # Anti-Repetition Guard: If user already received this photo
        if fname in user_seen_set:
            if not allow_reuse:
                continue  # Strictly never repeat previously seen photo!
            seen_penalty = 500
        else:
            seen_penalty = 0

        file_full_path = os.path.join(PROJECT_ROOT, entry.get("file_path", ""))
        if not os.path.exists(file_full_path):
            continue

        # Score matching
        entry_tags = set(entry.get("tags", []))
        entry_tokens = entry_tags.union(
            _tokenize(entry.get("scene", "")) +
            _tokenize(entry.get("outfit_label", "")) +
            _tokenize(entry.get("user_query", ""))
        )

        overlap = len(query_tokens & entry_tokens)
        score = overlap * 10

        # Outfit exact/partial match bonus
        curr_outfit = (outfit_label or "").lower()
        entry_outfit = (entry.get("outfit_label") or "").lower()
        if curr_outfit and entry_outfit:
            if curr_outfit in entry_outfit or entry_outfit in curr_outfit:
                score += 25

        # Meaningful penalty for frequently repeated photos to maintain variety
        usage = entry.get("usage_count", 0)
        score -= (usage * 15) + seen_penalty

        candidates.append((score, entry, file_full_path))

    if not candidates:
        return None

    # Sort descending by score
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Must have at least minimum contextual relevance (score > 0)
    # If query had zero specific keywords, allow returning from candidates
    valid_candidates = [c for c in candidates if c[0] > 0]
    if not query_tokens and candidates:
        valid_candidates = candidates
    elif not valid_candidates:
        return None

    # Randomized variety: pick among top candidates (within 80% of top score)
    import random
    top_score = valid_candidates[0][0]
    threshold = top_score * 0.8
    top_pool = [c for c in valid_candidates if c[0] >= threshold][:4]
    chosen_score, best_entry, best_path = random.choice(top_pool)

    try:
        with open(best_path, "rb") as f:
            img_bytes = f.read()

        # Update usage statistics in catalog
        best_entry["usage_count"] = best_entry.get("usage_count", 0) + 1
        best_entry["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_catalog(catalog)

        # Mark seen for this user so it's not repeated
        if user_id:
            mark_photo_seen_by_user(user_id, best_entry.get("filename", ""))

        logger.info(f"Retrieved photo from vault: {best_path} (Match Score: {chosen_score}, User: {user_id})")
        return img_bytes, best_entry
    except Exception as e:
        logger.error(f"Failed to read image from vault ({best_path}): {e}")
        return None


def get_vault_stats() -> Dict[str, Any]:
    """Returns statistics about archived photos in the local vault."""
    catalog = load_catalog()
    personas: Dict[str, int] = {}
    for item in catalog:
        p = item.get("persona", "unknown")
        personas[p] = personas.get(p, 0) + 1
    return {
        "total": len(catalog),
        "by_persona": personas,
        "vault_dir": VAULT_DIR
    }

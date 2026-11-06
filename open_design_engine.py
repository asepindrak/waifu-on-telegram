"""
open_design_engine.py - Autonomous Design System & UI/UX Engine
Empowers Waifu on Telegram with 150+ brand-grade design systems and 160+ UI/UX skills
from Open-Design (https://github.com/nexu-io/open-design).
Auto-activates out-of-the-box on new installations.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OPEN_DESIGN_DIR = os.path.join(PROJECT_ROOT, "open_design")
DESIGN_SYSTEMS_DIR = os.path.join(OPEN_DESIGN_DIR, "design-systems")
SKILLS_DIR = os.path.join(OPEN_DESIGN_DIR, "skills")

FRONTEND_KEYWORDS = [
    r'\b(web|website|web app|landing page|frontend|front-end|ui|ux|dashboard)\b',
    r'\b(antarmuka|tampilan|halaman|mockup|prototype|desain|design|layout)\b',
    r'\b(html|css|tailwind|react|vue|svelte|nextjs|vite)\b',
    r'\b(component|komponen|button|navbar|card|form|table|sidebar|footer)\b'
]

EXCLUSION_KEYWORDS = [
    r'\b(scrape|scraping|crawler|crawling|curl|requests\.get)\b'
]

STYLE_MAPPINGS: List[Tuple[List[str], str]] = [
    (["apple", "ios", "macos", "mac", "cupertino"], "apple"),
    (["shadcn", "shadcn/ui", "radix"], "shadcn"),
    (["linear", "dark mode", "dark theme", "cursor", "warp"], "cursor"),
    (["stripe", "fintech", "payment", "pembayaran", "saas", "billing"], "stripe"),
    (["dashboard", "admin", "analitik", "analytics", "metrik", "chart", "grafik"], "dashboard"),
    (["notion", "wiki", "catatan", "notes", "knowledge base"], "notion"),
    (["binance", "coinbase", "crypto", "trading", "kripto", "bitcoin", "web3"], "binance"),
    (["spotify", "music", "musik", "audio", "player", "lagu"], "spotify"),
    (["airbnb", "hotel", "sewa", "booking", "rental", "penginapan"], "airbnb"),
    (["shopify", "ecommerce", "toko", "belanja", "cart", "keranjang", "produk"], "shopify"),
    (["discord", "chat", "komunitas", "community", "pesan"], "discord"),
    (["bento", "bento grid", "grid modern"], "bento"),
    (["glassmorphism", "glass", "kaca", "blur"], "glassmorphism"),
    (["brutalism", "neobrutalism", "brutalis", "retro bold"], "brutalism"),
    (["vintage", "retro", "8-bit", "pixel"], "vintage"),
    (["clean", "minimal", "minimalis", "simple", "sederhana"], "clean"),
    (["creative", "portfolio", "portofolio", "showcase"], "creative"),
    (["corporate", "perusahaan", "b2b", "enterprise", "bisnis"], "corporate"),
    (["cyberpunk", "futuristic", "neon", "cosmic", "space"], "cosmic"),
    (["vercel", "next.js", "geist"], "vercel")
]

UNIVERSAL_UI_GUIDELINES = """
=== OPEN-DESIGN UNIVERSAL UI/UX EXCELLENCE STANDARDS ===
1. AESTHETICS & ANTI-AI-SLOP:
   - NEVER use generic purple-to-pink gradient backgrounds or centered unstyled floating cards.
   - Use high-contrast, accessible typography (Geist, Inter, or SF Pro).
   - Use subtle borders (border border-white/10 or border-slate-200) instead of heavy dropped shadows.
   - Respect generous spacing (p-6, p-8, gap-6) and clear hierarchy: Headline -> Supporting Caption -> Primary CTA.

2. ACCESSIBILITY & SEMANTICS:
   - Always use semantic HTML: <button>, <nav>, <header>, <main>, <section>, <footer>.
   - Interactive elements MUST have visible focus states (focus-visible:ring-2).
   - Form inputs need associated <label> and proper input types (email, number, tel).
   - Buttons must have clear labels or aria-label for icon-only buttons.

3. TYPOGRAPHY & DATA DISPLAY:
   - Headings must use 'text-wrap: balance' or 'text-pretty' to avoid orphan words.
   - Financial figures, counters, and statistics MUST use tabular numbers ('font-mono' or 'tabular-nums').
   - Keep line lengths comfortable for reading (max-w-prose / max-w-2xl).

4. RESPONSIVENESS & INTERACTION:
   - Mobile-first responsive layouts (grid-cols-1 md:grid-cols-2 lg:grid-cols-3).
   - Micro-interactions: smooth transitions on hover/active (transition-colors duration-150).
   - Flex children with long text must have 'min-w-0' and 'truncate' to prevent layout breakage.
"""


class OpenDesignEngine:
    """Manages design systems, style detection, and prompt enhancement."""

    def __init__(self, base_dir: str = OPEN_DESIGN_DIR):
        self.base_dir = base_dir
        self.design_systems_dir = os.path.join(base_dir, "design-systems")
        self.skills_dir = os.path.join(base_dir, "skills")
        self._cached_systems: Optional[List[str]] = None
        self._cached_skills: Optional[List[str]] = None

    def is_available(self) -> bool:
        """Returns True if the Open-Design repository is bundled and present."""
        return os.path.isdir(self.design_systems_dir) and len(self.list_available_systems()) > 0

    def list_available_systems(self) -> List[str]:
        """Lists all 150+ design system directory names."""
        if self._cached_systems is not None:
            return self._cached_systems

        if not os.path.isdir(self.design_systems_dir):
            return []

        systems = []
        try:
            for item in os.listdir(self.design_systems_dir):
                full_path = os.path.join(self.design_systems_dir, item)
                if os.path.isdir(full_path) and not item.startswith("_") and not item.startswith("."):
                    systems.append(item)
            systems.sort()
            self._cached_systems = systems
        except Exception as e:
            logger.warning(f"Failed to list design systems: {e}")
            return []

        return self._cached_systems or []

    def list_available_skills(self) -> List[str]:
        """Lists all design skills."""
        if self._cached_skills is not None:
            return self._cached_skills

        if not os.path.isdir(self.skills_dir):
            return []

        skills = []
        try:
            for item in os.listdir(self.skills_dir):
                full_path = os.path.join(self.skills_dir, item)
                if os.path.isdir(full_path) and not item.startswith("_") and not item.startswith("."):
                    skills.append(item)
            skills.sort()
            self._cached_skills = skills
        except Exception as e:
            logger.warning(f"Failed to list skills: {e}")
            return []

        return self._cached_skills or []

    def is_frontend_or_design_request(self, text: str) -> bool:
        """Detects if user is asking to build or design an application, website, or UI component."""
        lower = text.lower()
        # Check exclusions (e.g. scraping a website) unless explicit UI design terms exist
        is_exclusion = any(re.search(pat, lower) for pat in EXCLUSION_KEYWORDS)
        has_explicit_ui = any(re.search(r'\b(ui|ux|tampilan|desain|design|css|tailwind|html|frontend)\b', lower) for pat in [1])
        if is_exclusion and not has_explicit_ui:
            return False

        for pat in FRONTEND_KEYWORDS:
            if re.search(pat, lower):
                return True
        return False

    def detect_design_style(self, prompt: str) -> str:
        """Detects the best matching design system from prompt keywords or defaults to 'shadcn'."""
        lower = prompt.lower()
        available = self.list_available_systems()

        # 1. Exact match against directory names
        for sys_name in available:
            pattern = r'\b' + re.escape(sys_name) + r'\b'
            if re.search(pattern, lower):
                return sys_name

        # 2. Check semantic mappings
        for keywords, mapped_style in STYLE_MAPPINGS:
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                    if mapped_style in available:
                        return mapped_style

        # 3. Contextual defaults
        if any(w in lower for w in ["dashboard", "admin", "crm", "tabel"]):
            return "dashboard" if "dashboard" in available else "shadcn"
        if any(w in lower for w in ["dark", "gelap", "hitam"]):
            return "cursor" if "cursor" in available else "shadcn"
        if any(w in lower for w in ["mobile", "ios", "iphone", "android"]):
            return "apple" if "apple" in available else "shadcn"

        return "shadcn" if "shadcn" in available else (available[0] if available else "clean")

    def get_design_system_rules(self, style_name: str, max_chars: int = 2500) -> str:
        """Reads and formats the DESIGN.md rules for the given style."""
        sys_dir = os.path.join(self.design_systems_dir, style_name)
        if not os.path.isdir(sys_dir):
            sys_dir = os.path.join(self.design_systems_dir, "shadcn")
            style_name = "shadcn"

        if not os.path.isdir(sys_dir):
            return "Follow clean, modern, accessible utility-first design principles."

        # Prefer Indonesian design doc if present, else default DESIGN.md
        candidate_files = ["DESIGN-id.md", "DESIGN.md"]
        target_file = None
        for cf in candidate_files:
            fp = os.path.join(sys_dir, cf)
            if os.path.isfile(fp):
                target_file = fp
                break

        content = ""
        if target_file:
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except Exception as e:
                logger.warning(f"Error reading design system {style_name}: {e}")

        # Try to read design-tokens.json for color codes if available
        tokens_fp = os.path.join(sys_dir, "design-tokens.json")
        tokens_summary = ""
        if os.path.isfile(tokens_fp):
            try:
                with open(tokens_fp, "r", encoding="utf-8") as tf:
                    tdata = json.load(tf)
                    colors = tdata.get("colors") or tdata.get("color") or {}
                    if isinstance(colors, dict) and colors:
                        tokens_summary = "\nColor Tokens: " + json.dumps(colors, ensure_ascii=False)[:300]
            except Exception:
                pass

        if len(content) > max_chars:
            content = content[:max_chars] + "\n...(design specification truncated for brevity)..."

        return f"### DESIGN SYSTEM CONTRACT: {style_name.upper()}\n{content}{tokens_summary}"

    def enhance_coding_prompt(self, user_prompt: str) -> Tuple[str, Optional[str]]:
        """
        If user_prompt is a frontend/UI request, injects Open-Design specifications.
        Returns: (enhanced_prompt, applied_style_name_or_None)
        """
        if not self.is_frontend_or_design_request(user_prompt):
            return user_prompt, None

        if not self.is_available():
            return user_prompt, None

        style_name = self.detect_design_style(user_prompt)
        rules = self.get_design_system_rules(style_name)

        open_design_injection = (
            f"\n\n=======================================================\n"
            f"🎨 [OPEN-DESIGN SYSTEM ACTIVE: {style_name.upper()}]\n"
            f"=======================================================\n"
            f"You MUST craft this application/page following the brand-grade design specifications below:\n\n"
            f"{rules}\n\n"
            f"{UNIVERSAL_UI_GUIDELINES}\n"
            f"=======================================================\n"
        )

        enhanced = f"{user_prompt}{open_design_injection}"
        return enhanced, style_name

    def scaffold_design_tokens(self, style_name: str, target_dir: str) -> List[str]:
        """Copies tokens.css and tailwind-v4.css to target directory if available."""
        sys_dir = os.path.join(self.design_systems_dir, style_name)
        if not os.path.isdir(sys_dir):
            return []

        copied = []
        for fname in ["tokens.css", "tailwind-v4.css", "design-tokens.json"]:
            src = os.path.join(sys_dir, fname)
            dst = os.path.join(target_dir, fname)
            if os.path.isfile(src) and not os.path.exists(dst):
                try:
                    with open(src, "r", encoding="utf-8") as sf, open(dst, "w", encoding="utf-8") as df:
                        df.write(sf.read())
                    copied.append(fname)
                except Exception as e:
                    logger.warning(f"Failed to scaffold {fname}: {e}")

        return copied

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns engine health and diagnostics."""
        systems = self.list_available_systems()
        skills = self.list_available_skills()
        return {
            "available": len(systems) > 0,
            "design_systems_count": len(systems),
            "skills_count": len(skills),
            "directory": self.base_dir
        }


# Global singleton
_GLOBAL_OPEN_DESIGN_ENGINE: Optional[OpenDesignEngine] = None


def get_open_design_engine() -> OpenDesignEngine:
    global _GLOBAL_OPEN_DESIGN_ENGINE
    if _GLOBAL_OPEN_DESIGN_ENGINE is None:
        _GLOBAL_OPEN_DESIGN_ENGINE = OpenDesignEngine()
    return _GLOBAL_OPEN_DESIGN_ENGINE

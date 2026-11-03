"""
routing_engine.py - Intelligent SFW vs NSFW Dual-Engine Routing
Allows separating SFW and NSFW operations across different LLM providers and Image engines:
- SFW: Cloud providers (OpenAI, Groq, DeepSeek, OpenRouter) or Local LLMs
- NSFW: Local Uncensored KoboldCPP or Cloud Uncensored models
- Auto-detects NSFW/intimate context, protects Cloud accounts from safety filter bans
- Unified memory, persona, and conversation history across providers
"""

import os
import re
import sys
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("RoutingEngine")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from lu_llm_client import LocallyUncensoredClient

# Provider Specifications & Default Endpoints
PROVIDER_PRESETS = {
    "local": {
        "name": "Local KoboldCPP Standalone (Uncensored)",
        "base_url": "http://127.0.0.1:5001/v1",
        "api_key": "kobold",
        "default_model": "default",
        "is_local": True,
        "description": "100% lokal di PC tanpa batasan sensor atau kuota."
    },
    "ollama": {
        "name": "Local Ollama",
        "base_url": "http://127.0.0.1:11434/v1",
        "api_key": "ollama",
        "default_model": "default",
        "is_local": True,
        "description": "Server Ollama lokal (Port 11434)."
    },
    "lm-studio": {
        "name": "Local LM Studio",
        "base_url": "http://127.0.0.1:1234/v1",
        "api_key": "lm-studio",
        "default_model": "default",
        "is_local": True,
        "description": "LM Studio lokal (Port 1234)."
    },
    "openai": {
        "name": "OpenAI Official Cloud",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "default_model": "gpt-4o-mini",
        "is_local": False,
        "description": "Sangat cerdas, responsif, dan hemat resource PC."
    },
    "groq": {
        "name": "Groq Cloud (Llama 3.3 70B - Ultra Fast)",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": "",
        "default_model": "llama-3.3-70b-versatile",
        "is_local": False,
        "description": "Inferensi kilat di cloud dengan tier gratis."
    },
    "deepseek": {
        "name": "DeepSeek API",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "default_model": "deepseek-chat",
        "is_local": False,
        "description": "Model reasoning kuat dengan biaya sangat murah."
    },
    "openrouter": {
        "name": "OpenRouter Multi-Model",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "is_local": False,
        "description": "Akses ke ratusan model cloud SFW."
    },
    "openrouter_uncensored": {
        "name": "OpenRouter Uncensored",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "default_model": "nousresearch/hermes-3-llama-3.1-405b",
        "is_local": False,
        "description": "Model cloud tanpa batasan sensor."
    },
    "custom": {
        "name": "Custom OpenAI-Compatible API",
        "base_url": "",
        "api_key": "",
        "default_model": "default",
        "is_local": False,
        "description": "Endpoint API eksternal buatan sendiri."
    },
    "agy": {
        "name": "Google Antigravity CLI Bridge (AGY Port 8001)",
        "base_url": "http://127.0.0.1:8001/v1",
        "api_key": "sk-agy-secret-key-12345",
        "default_model": "gemini-3.8-flash-medium",
        "is_local": True,
        "description": "Bridge server OpenAI-compatible bertenaga Google Antigravity CLI (agy)."
    }
}

# Compiled NSFW / Intimate Regex Patterns
_NSFW_WORDS = [
    # Explicit Nudity / Strip / Body Exposure
    r"\b(?:nude|naked|topless|bottomless|unclothed|telanjang|bugil)\b",
    r"\b(?:tanpa\s+(?:busana|baju|pakaian|celana))\b",
    r"\b(?:buka\s+(?:baju|pakaian|celana|bh|bra|rok))\b",
    r"\b(?:lepas\s+(?:baju|pakaian|celana|bh|bra))\b",
    r"\b(?:g(?:ak|a|k)\s+pake\s+(?:baju|pakaian|celana|busana))\b",
    r"\b(?:ngga\s+pake\s+(?:baju|pakaian|celana|busana))\b",

    # Explicit Sexual Anatomy & Organs
    r"\b(?:titit|kontol|memek|pepek|vagina|penis|clitoris)\b",
    r"\b(?:nipple|nipples|puting|payudara|tetek|boobs|tits)\b",

    # Sexual Acts & Erotic Activities
    r"\b(?:bercinta|ngentot|entot|masturbasi|masturbate|coli|onani)\b",
    r"\b(?:orgasme|orgasm|crot|squirt|ejakulasi)\b",
    r"\b(?:hisap\s+(?:titit|kontol|payudara|puting))\b",
    r"\b(?:remas\s+(?:payudara|pantat|tetek))\b",
    r"\b(?:jilat\s+(?:memek|pepek|puting|vagina))\b",
    r"\b(?:oral\s+sex|blowjob|handjob)\b",

    # Erotic Context & State of Mind
    r"\b(?:sange|horny|terangsang|desah|mendesah|erotis|erotic)\b",
    r"\b(?:erp|nsfw|hentai|ecchi|r18|18\+)\b",
    r"\b(?:sensual\s+(?:touch|kiss|massage|rubbing))\b",

    # Provocative Intimate Clothing Requests
    r"\b(?:lingerie|g-string|thong|celana\s+dalam|pakaian\s+dalam)\b",
    r"\b(?:transparan|see-through|baju\s+tidur\s+seksi)\b",
]

_NSFW_REGEX = re.compile("|".join(_NSFW_WORDS), re.IGNORECASE)


def detect_nsfw_intent(text: str, messages: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    Analyzes user text and recent conversation context to classify whether
    the current turn is NSFW (intimate / erotic / nude / 18+) or SFW (general / casual).
    """
    if not text:
        return False

    clean_text = text.strip().lower()

    # 1. Direct regex keyword match on current user input
    if _NSFW_REGEX.search(clean_text):
        return True

    # 2. Check roleplay asterisk actions e.g. *membuka baju*, *meraba*
    rp_actions = re.findall(r"\*([^*]+)\*", clean_text)
    for act in rp_actions:
        if _NSFW_REGEX.search(act):
            return True

    # 3. Check recent conversation context (last 2 turns) if ongoing intimate roleplay
    if messages and len(messages) >= 2:
        recent_tail = messages[-3:]
        for m in recent_tail:
            content = m.get("content", "")
            if isinstance(content, str) and _NSFW_REGEX.search(content):
                # If recently active NSFW context and current prompt is confirming/reacting intimately
                if any(k in clean_text for k in ["lagi", "terus", "suka", "nikmat", "enak", "mau", "peluk", "cium", "sayang", "ahh", "ihh"]):
                    return True

    return False


def sanitize_messages_for_sfw(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitizes conversation history before sending to SFW providers (AGY CLI, OpenAI, Groq).
    Filters out explicit NSFW/erotic exchanges (both user and assistant turns) from past history,
    preventing cloud safety filter bans, account warnings, or AGY CLI moderation triggers.
    """
    clean_messages = []
    total = len(messages)
    skip_next_assistant = False

    for idx, m in enumerate(messages):
        role = m.get("role", "")
        content = m.get("content", "")

        # 1. System instruction
        if role == "system":
            if isinstance(content, str):
                safe_sys = re.sub(r'\[(?:NSFW|ERP|ADULT|MODE INTIM)[^\]]*\]', '', content, flags=re.IGNORECASE)
                clean_messages.append({"role": role, "content": safe_sys.strip()})
            else:
                clean_messages.append(m)
            continue

        # 2. Latest active user message (the router already determined is_nsfw=False for SFW)
        if idx == total - 1 and role == "user":
            clean_messages.append(m)
            continue

        # 3. Check historical message content
        content_str = ""
        if isinstance(content, str):
            content_str = content
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    content_str += part.get("text", "") + " "

        is_nsfw_msg = bool(_NSFW_REGEX.search(content_str))

        if role == "user":
            if is_nsfw_msg:
                # Omit this NSFW user turn and skip the paired assistant response
                skip_next_assistant = True
                continue
            else:
                skip_next_assistant = False
                clean_messages.append(m)
        elif role == "assistant":
            if skip_next_assistant or is_nsfw_msg:
                skip_next_assistant = False
                continue
            else:
                clean_messages.append(m)
        else:
            clean_messages.append(m)

    # Ensure system prompt and at least the latest user message exist
    if not any(m.get("role") == "user" for m in clean_messages) and messages:
        clean_messages.append(messages[-1])

    return clean_messages


class HybridLLMClient:
    """
    Intelligent Dual-Engine LLM Client.
    Dispatches to SFW Provider (Cloud or Local) for standard companion dialogue,
    and NSFW Provider (Local KoboldCPP Uncensored or Cloud Uncensored) for intimate/adult requests.
    Seamlessly falls back if a Cloud SFW provider rejects a prompt due to safety filters.
    """

    def __init__(
        self,
        mode: Optional[str] = None,
        sfw_client: Optional[LocallyUncensoredClient] = None,
        nsfw_client: Optional[LocallyUncensoredClient] = None
    ):
        self.mode = (mode or os.environ.get("AI_ENGINE_MODE", "unified")).lower().strip()
        if self.mode not in ("split", "hybrid"):
            self.mode = "unified"

        # Providers
        self.sfw_provider = os.environ.get("SFW_LLM_PROVIDER", "local").lower().strip()
        self.nsfw_provider = os.environ.get("NSFW_LLM_PROVIDER", "local").lower().strip()

        # Initialize SFW client
        if sfw_client:
            self.sfw_client = sfw_client
        else:
            sfw_base = os.environ.get("SFW_LLM_BASE_URL", os.environ.get("LLM_BASE_URL", "http://127.0.0.1:5001/v1"))
            sfw_key = os.environ.get("SFW_LLM_API_KEY", os.environ.get("LLM_API_KEY", "auto"))
            sfw_model = os.environ.get("SFW_LLM_MODEL", os.environ.get("LLM_MODEL", "default"))
            self.sfw_client = LocallyUncensoredClient(base_url=sfw_base, api_key=sfw_key, model=sfw_model)

        # Initialize NSFW client
        if nsfw_client:
            self.nsfw_client = nsfw_client
        else:
            if self.mode == "unified":
                self.nsfw_client = self.sfw_client
            else:
                nsfw_base = os.environ.get("NSFW_LLM_BASE_URL", os.environ.get("LLM_BASE_URL", "http://127.0.0.1:5001/v1"))
                nsfw_key = os.environ.get("NSFW_LLM_API_KEY", os.environ.get("LLM_API_KEY", "auto"))
                nsfw_model = os.environ.get("NSFW_LLM_MODEL", os.environ.get("LLM_MODEL", "default"))
                self.nsfw_client = LocallyUncensoredClient(base_url=nsfw_base, api_key=nsfw_key, model=nsfw_model)

    @property
    def base_url(self) -> str:
        return self.sfw_client.base_url

    @property
    def model(self) -> str:
        return self.sfw_client.model

    def is_split_mode(self) -> bool:
        return self.mode in ("split", "hybrid") and self.sfw_client != self.nsfw_client

    def is_sfw_cloud(self) -> bool:
        """Returns True if the SFW client connects to an external cloud API."""
        return not any(p in self.sfw_client.base_url for p in ["127.0.0.1", "localhost", ":5001", ":8127", ":11434", ":1234"])

    def is_nsfw_local(self) -> bool:
        """Returns True if the NSFW client is running on the local PC."""
        return any(p in self.nsfw_client.base_url for p in ["127.0.0.1", "localhost", ":5001", ":8127", ":11434", ":1234"])

    def get_active_client(self, is_nsfw: bool = False) -> LocallyUncensoredClient:
        if self.is_split_mode() and is_nsfw:
            return self.nsfw_client
        return self.sfw_client

    def check_health(self) -> Dict[str, Any]:
        """Checks diagnostic health of both SFW and NSFW engines."""
        sfw_h = self.sfw_client.check_health()
        if not self.is_split_mode():
            return sfw_h

        nsfw_h = self.nsfw_client.check_health()
        is_online = sfw_h.get("online", False) or nsfw_h.get("online", False)

        return {
            "online": is_online,
            "mode": "split",
            "backend": f"Hybrid (SFW: {sfw_h.get('backend', 'Unknown')} | NSFW: {nsfw_h.get('backend', 'Unknown')})",
            "model": f"{self.sfw_client.model} / {self.nsfw_client.model}",
            "sfw": sfw_h,
            "nsfw": nsfw_h
        }

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.8,
        max_tokens: int = 1000,
        image_bytes: Optional[bytes] = None,
        is_nsfw: Optional[bool] = None
    ) -> Tuple[str, str]:
        """
        Dispatches conversation turn to appropriate client (SFW or NSFW).
        Protects cloud accounts by auto-rerouting NSFW requests to uncensored engine.
        Returns: (clean_reply, reasoning_content)
        """
        # Determine intent if not explicitly passed
        if is_nsfw is None:
            # Extract last user message
            last_user_txt = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    c = m.get("content", "")
                    if isinstance(c, str):
                        last_user_txt = c
                    elif isinstance(c, list):
                        for part in c:
                            if isinstance(part, dict) and part.get("type") == "text":
                                last_user_txt = part.get("text", "")
                    break
            is_nsfw = detect_nsfw_intent(last_user_txt, messages)

        target_client = self.nsfw_client if (self.is_split_mode() and is_nsfw) else self.sfw_client
        target_label = "NSFW" if is_nsfw else "SFW"

        client_url = getattr(target_client, 'base_url', 'unknown')
        client_model = getattr(target_client, 'model', 'default')
        logger.info(f"Routing chat turn -> [{target_label}] Engine ({client_url}, Model: {client_model})")

        # Auto-wake / auto-run AGY Bridge if targeted on port 8001
        if "8001" in str(client_url):
            from idle_engine import is_port_listening
            if not is_port_listening(8001):
                try:
                    import sys, subprocess
                    proj_root = os.path.dirname(os.path.abspath(__file__))
                    agy_script = os.path.join(proj_root, "agy_bridge.py")
                    if os.path.exists(agy_script):
                        logger.info("AGY Bridge is offline. Auto-starting AGY OpenAI Bridge on port 8001...")
                        popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
                        subprocess.Popen([sys.executable, agy_script], cwd=proj_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)
                        for _ in range(10):
                            time.sleep(0.5)
                            if is_port_listening(8001):
                                break
                except Exception as e_start:
                    logger.debug(f"Failed to auto-start AGY bridge: {e_start}")

            try:
                import bot
                if hasattr(bot, "idle_engine") and bot.idle_engine:
                    bot.idle_engine.record_activity(is_agy=True)
            except Exception:
                pass

        # If routing to SFW provider in split mode,
        # sanitize history so past NSFW turns never reach AGY CLI or Cloud APIs!
        payload_messages = messages
        if target_client != self.nsfw_client and self.is_split_mode():
            payload_messages = sanitize_messages_for_sfw(messages)

        try:
            return target_client.chat(
                payload_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                image_bytes=image_bytes
            )
        except Exception as e:
            # Automatic Safety Fallback:
            # If SFW provider (e.g. OpenAI / Groq) rejected prompt due to safety policy,
            # or if SFW is unreachable, seamlessly retry with uncensored NSFW engine!
            err_str = str(e).lower()
            is_policy_violation = any(k in err_str for k in ["policy", "filter", "safety", "moderation", "violat", "blocked", "forbidden", "400"])
            if target_client != self.nsfw_client and (is_policy_violation or "connection" in err_str):
                logger.warning(f"SFW LLM rejection / failure ({e}). Auto-redirecting to NSFW Uncensored Engine...")
                return self.nsfw_client.chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    image_bytes=image_bytes
                )
            raise


_GLOBAL_HYBRID_CLIENT: Optional[HybridLLMClient] = None


def get_hybrid_llm_client(force_reload: bool = False) -> HybridLLMClient:
    """Returns singleton HybridLLMClient instance configured from environment."""
    global _GLOBAL_HYBRID_CLIENT
    if _GLOBAL_HYBRID_CLIENT is None or force_reload:
        _GLOBAL_HYBRID_CLIENT = HybridLLMClient()
    return _GLOBAL_HYBRID_CLIENT

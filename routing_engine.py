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
    r"\b(?:nude|naked|topless|bottomless|unclothed|telanjang|bugil|telanjang\s+bulat|tanpa\s+sehelai\s+benang)\b",
    r"\b(?:(?:buka|lepas|copot|turunkan)\s+(?:baju|kaos|celana|rok|bh|bra|cd|kutang|bawahan|atasan|pakaian|semua|semuanya|celana\s+dalam)(?:mu|nya)?)\b",
    r"\b(?:buka\s+(?:pelan|satu\s*satu|lagi|berikutnya|tahap|dong))\b",
    r"\b(?:tanpa\s+(?:busana|baju|pakaian|celana))\b",
    r"\b(?:buka\s+(?:baju|pakaian|celana|bh|bra|rok|semua))\b",
    r"\b(?:lepas\s+(?:baju|pakaian|celana|bh|bra|semua))\b",
    r"\b(?:g(?:ak|a|k)\s+pake\s+(?:baju|pakaian|celana|busana))\b",
    r"\b(?:ngga\s+pake\s+(?:baju|pakaian|celana|busana))\b",

    # Explicit Sexual Anatomy & Organs
    r"\b(?:titit|kontol|memek|pepek|vagina|penis|clitoris)\b",
    r"\b(?:nipple|nipples|puting|payudara|tetek|boobs|tits|nenen|toket|dada)\b",
    r"\b(?:pantat|bokong|pantatmu|bokongmu)\b",

    # Sexual Acts & Erotic Activities
    r"\b(?:bercinta|ngentot|entot|masturbasi|masturbate|coli|onani)\b",
    r"\b(?:orgasme|orgasm|crot|squirt|ejakulasi)\b",
    r"\b(?:hisap\s+(?:titit|kontol|payudara|puting|nenen|toket))\b",
    r"\b(?:remas\s+(?:payudara|pantat|tetek|nenen|toket|bokong))\b",
    r"\b(?:jilat\s+(?:memek|pepek|puting|vagina|nenen|toket|leher))\b",
    r"\b(?:oral\s+sex|blowjob|handjob)\b",
    r"\b(?:raba|meraba|remas|meremas|elus\s+paha|peluk\s+erat)\b",

    # Erotic Context & State of Mind
    r"\b(?:sange|horny|terangsang|desah|mendesah|erotis|erotic)\b",
    r"\b(?:erp|nsfw|hentai|ecchi|r18|18\+)\b",
    r"\b(?:sensual\s+(?:touch|kiss|massage|rubbing))\b",
    r"\b(?:pap|foto)\s+(?:nenen|toket|telanjang|bugil|seksi|sexy|nsfw|paha|pantat|bokong)\b",

    # Provocative Intimate Clothing Requests
    r"\b(?:lingerie|g-string|thong|celana\s+dalam|pakaian\s+dalam)\b",
    r"\b(?:transparan|see-through|baju\s+tidur\s+seksi)\b",
]

_NSFW_REGEX = re.compile("|".join(_NSFW_WORDS), re.IGNORECASE)

# AI Safety Policy Refusal Patterns (e.g. Gemini, ChatGPT, Claude)
_REFUSAL_WORDS = [
    r"tidak dapat memenuhi permintaan",
    r"tidak dapat membuat konten",
    r"bersifat eksplisit secara seksual",
    r"i cannot fulfill this request",
    r"i am unable to (?:fulfill|generate|create)",
    r"as an ai (?:language model)?, i (?:cannot|can't|must not)",
    r"sebagai (?:seorang )?model ai, saya (?:tidak|belum)",
    r"kebijakan keselamatan",
    r"safety policy",
    r"content policy",
    r"sexually explicit",
    r"against my safety guidelines"
]
_REFUSAL_REGEX = re.compile("|".join(_REFUSAL_WORDS), re.IGNORECASE)


def is_ai_refusal(text: Optional[str]) -> bool:
    """Detects whether an LLM output is an AI safety policy refusal message."""
    if not text or not isinstance(text, str):
        return False
    return bool(_REFUSAL_REGEX.search(text.strip()))


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
            nsfw_base = os.environ.get("NSFW_LLM_BASE_URL", "http://127.0.0.1:5001/v1")
            nsfw_key = os.environ.get("NSFW_LLM_API_KEY", "auto")
            nsfw_model = os.environ.get("NSFW_LLM_MODEL", os.environ.get("LOCAL_LLM_MODEL", "default"))

            # If mode is unified BUT SFW client is AGY (port 8001) or Cloud API,
            # we MUST initialize a dedicated uncensored NSFW client (port 5001 KoboldCPP)
            # so that intimate/NSFW turns are never routed to Gemini/Cloud!
            sfw_is_cloud_or_agy = (":8001" in str(self.sfw_client.base_url)) or self.is_sfw_cloud()
            if self.mode == "unified" and not sfw_is_cloud_or_agy:
                self.nsfw_client = self.sfw_client
            else:
                self.nsfw_client = LocallyUncensoredClient(base_url=nsfw_base, api_key=nsfw_key, model=nsfw_model)

    @property
    def base_url(self) -> str:
        return self.sfw_client.base_url

    @base_url.setter
    def base_url(self, val: str):
        if hasattr(self, "sfw_client") and hasattr(self.sfw_client, "base_url"):
            self.sfw_client.base_url = val

    @property
    def model(self) -> str:
        return self.sfw_client.model

    @model.setter
    def model(self, val: str):
        if hasattr(self, "sfw_client") and hasattr(self.sfw_client, "model"):
            self.sfw_client.model = val

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

        use_nsfw_client = False
        if is_nsfw:
            if self.is_split_mode():
                use_nsfw_client = True
            elif (":8001" in str(getattr(self.sfw_client, 'base_url', ''))) or self.is_sfw_cloud():
                # SFW client is AGY Bridge or Cloud provider: MUST use uncensored NSFW client for NSFW turns!
                use_nsfw_client = True

        target_client = self.nsfw_client if use_nsfw_client else self.sfw_client
        target_label = "NSFW" if is_nsfw else "SFW"

        client_url = getattr(target_client, 'base_url', 'unknown')
        client_model = getattr(target_client, 'model', 'default')
        logger.info(f"Routing chat turn -> [{target_label}] Engine ({client_url}, Model: {client_model})")

        # Auto-wake local KoboldCPP if targeted on port 5001
        if "5001" in str(client_url):
            from idle_engine import is_port_listening
            if not is_port_listening(5001):
                try:
                    import bot
                    if hasattr(bot, "idle_engine") and bot.idle_engine:
                        bot.idle_engine.ensure_llm_active(is_nsfw=is_nsfw)
                except Exception as e_w:
                    logger.debug(f"Could not auto-wake KoboldCPP on port 5001: {e_w}")

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
                        log_path = os.path.join(proj_root, "agy_bridge.log")
                        with open(log_path, "a", encoding="utf-8") as f_log:
                            subprocess.Popen([sys.executable, agy_script], cwd=proj_root, stdout=f_log, stderr=f_log, **popen_kwargs)
                        for _ in range(24):
                            time.sleep(0.5)
                            if is_port_listening(8001):
                                logger.info("✓ AGY OpenAI Bridge successfully awakened on port 8001.")
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

        # Multimodal Vision Routing (AGY Bridge 0-VRAM vs Local Moondream2)
        processed_image_bytes = image_bytes
        if image_bytes:
            if ":8001" in str(client_url):
                logger.info("Routing image to AGY Bridge for 0-VRAM multimodal perception.")
            else:
                try:
                    from vision_engine import vision_engine, inject_visual_context_into_messages
                    logger.info("Local Stheno 8B is text-only: using Moondream vision engine to analyze image...")
                    desc = vision_engine.describe_image(image_bytes, user_caption=last_user_txt)
                    if desc:
                        payload_messages = inject_visual_context_into_messages(payload_messages, desc)
                        processed_image_bytes = None
                except Exception as e_v:
                    logger.warning(f"Vision engine extraction error: {e_v}")

        try:
            reply_tuple = target_client.chat(
                payload_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                image_bytes=processed_image_bytes
            )
            reply_text, reasoning = reply_tuple if isinstance(reply_tuple, tuple) else (reply_tuple, "")

            # Check if LLM returned an AI safety refusal message
            if is_ai_refusal(reply_text):
                logger.warning(f"Safety refusal returned by {target_label} engine: '{reply_text[:60]}...'")
                if target_client != self.nsfw_client:
                    logger.info("Auto-redirecting refusal turn to NSFW Uncensored Engine...")
                    try:
                        import bot
                        if hasattr(bot, "idle_engine") and bot.idle_engine:
                            bot.idle_engine.ensure_llm_active(is_nsfw=True)
                    except Exception:
                        pass
                    backup_tuple = self.nsfw_client.chat(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        image_bytes=image_bytes
                    )
                    backup_text, backup_reasoning = backup_tuple if isinstance(backup_tuple, tuple) else (backup_tuple, "")
                    if not is_ai_refusal(backup_text):
                        return backup_text, backup_reasoning
                raise ValueError(f"AI content refusal: {reply_text}")

            return reply_text, reasoning
        except Exception as e:
            # Automatic High-Availability Fallback:
            # If primary provider rejected prompt or is unreachable, seamlessly retry with backup engine!
            err_str = str(e).lower()
            is_policy_violation = any(k in err_str for k in ["policy", "filter", "safety", "moderation", "violat", "blocked", "forbidden", "400"])
            is_conn_error = any(k in err_str for k in ["connection", "timeout", "refused", "10061", "max retries"])

            if target_client != self.nsfw_client and (is_policy_violation or is_conn_error):
                logger.warning(f"SFW LLM rejection / failure ({e}). Auto-redirecting to NSFW Uncensored Engine...")
                return self.nsfw_client.chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    image_bytes=image_bytes
                )

            # High-Availability fallback between port 8001 (AGY) and port 5001 (KoboldCPP)
            if is_conn_error:
                from idle_engine import is_port_listening
                from lu_llm_client import LocallyUncensoredClient

                if "8001" in str(client_url) and is_port_listening(5001):
                    logger.warning(f"AGY Bridge unreachable ({e}). Seamlessly falling back to local KoboldCPP (port 5001)...")
                    backup = LocallyUncensoredClient(base_url="http://127.0.0.1:5001/v1", model="default")
                    return backup.chat(messages, temperature=temperature, max_tokens=max_tokens, image_bytes=image_bytes)

                elif "5001" in str(client_url) and is_port_listening(8001):
                    logger.warning(f"Local KoboldCPP unreachable ({e}). Seamlessly falling back to AGY Bridge (port 8001)...")
                    backup = LocallyUncensoredClient(base_url="http://127.0.0.1:8001/v1", model="gemini-3.8-flash-medium")
                    return backup.chat(messages, temperature=temperature, max_tokens=max_tokens, image_bytes=image_bytes)

            raise


_GLOBAL_HYBRID_CLIENT: Optional[HybridLLMClient] = None


def get_hybrid_llm_client(force_reload: bool = False) -> HybridLLMClient:
    """Returns singleton HybridLLMClient instance configured from environment."""
    global _GLOBAL_HYBRID_CLIENT
    if _GLOBAL_HYBRID_CLIENT is None or force_reload:
        _GLOBAL_HYBRID_CLIENT = HybridLLMClient()
    return _GLOBAL_HYBRID_CLIENT

import os
import sys
import re
import json
import base64
import time
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def extract_llama_key_from_process() -> Optional[str]:
    """
    Auto-detects LLAMA_API_KEY directly from the running lu-llama-server.exe process memory on Windows.
    This eliminates the need to manually copy-paste dynamically generated tokens!
    """
    if sys.platform != "win32":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        kernel32 = ctypes.windll.kernel32
        ntdll = ctypes.windll.ntdll

        # Find lu-llama-server PID using Windows API / tasklist
        import subprocess
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq lu-llama-server.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="ignore"
        )
        pids = []
        for line in proc.stdout.splitlines():
            parts = line.strip().split('","')
            if len(parts) >= 2:
                try:
                    pids.append(int(parts[1].replace('"', '')))
                except ValueError:
                    pass

        if not pids:
            return None

        class PROCESS_BASIC_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('ExitStatus', wintypes.DWORD),
                ('Reserved0', wintypes.DWORD),
                ('PebBaseAddress', ctypes.c_void_p),
                ('AffinityMask', ctypes.c_void_p),
                ('BasePriority', wintypes.LONG),
                ('Reserved1', wintypes.DWORD),
                ('UniqueProcessId', ctypes.c_void_p),
                ('InheritedFromUniqueProcessId', ctypes.c_void_p),
            ]

        for pid in pids:
            h_proc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            if not h_proc:
                continue

            try:
                pbi = PROCESS_BASIC_INFORMATION()
                ret_len = wintypes.ULONG()
                status = ntdll.NtQueryInformationProcess(h_proc, 0, ctypes.byref(pbi), ctypes.sizeof(pbi), ctypes.byref(ret_len))
                if status != 0 or not pbi.PebBaseAddress:
                    continue

                ptr_params = ctypes.c_void_p()
                kernel32.ReadProcessMemory(h_proc, ctypes.c_void_p(pbi.PebBaseAddress + 0x20), ctypes.byref(ptr_params), 8, None)
                if not ptr_params.value:
                    continue

                ptr_env = ctypes.c_void_p()
                kernel32.ReadProcessMemory(h_proc, ctypes.c_void_p(ptr_params.value + 0x80), ctypes.byref(ptr_env), 8, None)
                if not ptr_env.value:
                    continue

                buf = ctypes.create_string_buffer(65536)
                bytes_read = ctypes.c_size_t()
                if kernel32.ReadProcessMemory(h_proc, ptr_env, buf, 65536, ctypes.byref(bytes_read)):
                    env_str = buf.raw[:bytes_read.value].decode('utf-16le', errors='ignore')
                    for var in env_str.split('\x00'):
                        if var.startswith("LLAMA_API_KEY="):
                            key = var.split("=", 1)[1].strip()
                            if key:
                                logger.info(f"Auto-detected LLAMA_API_KEY from PID {pid} successfully.")
                                return key
            finally:
                kernel32.CloseHandle(h_proc)

    except Exception as e:
        logger.debug(f"Process inspection failed: {e}")

    return None


class LocallyUncensoredClient:
    """Client for local LLMs (Locally Uncensored / llama-server / Ollama / LM Studio)."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5001/v1",
        api_key: str = "auto",
        model: str = "default",
        timeout: int = 50
    ):
        self.base_url = base_url.rstrip("/")
        self.config_api_key = api_key
        self.cached_api_key: Optional[str] = None
        self.model = model
        self.timeout = timeout

    def get_api_key(self) -> str:
        """Resolves active API Key (dynamic memory extraction or static)."""
        if self.config_api_key and self.config_api_key.lower() not in ("auto", ""):
            return self.config_api_key

        if self.cached_api_key:
            return self.cached_api_key

        # Only check memory extraction when connecting to Locally Uncensored (port 8127)
        if ":8127" in self.base_url:
            auto_key = extract_llama_key_from_process()
            if auto_key:
                self.cached_api_key = auto_key
                return auto_key

        if ":5001" in self.base_url:
            return "kobold"
        if ":11434" in self.base_url:
            return "ollama"
        if ":1234" in self.base_url:
            return "lm-studio"

        return "locally-uncensored"

    def check_health(self) -> Dict[str, Any]:
        """Checks if local LLM service is active and responsive."""
        key = self.get_api_key()
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        
        # Test models endpoint
        try:
            r = requests.get(f"{self.base_url}/models", headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                models = data.get("data", []) or data.get("models", [])
                model_name = models[0].get("id", "Unknown") if models else (self.model or "Active Model")
                backend = "KoboldCPP" if ":5001" in self.base_url else ("Locally Uncensored" if ":8127" in self.base_url else "Local LLM")
                return {"online": True, "backend": backend, "model": model_name}
        except Exception:
            pass

        # Try health endpoint
        host_root = self.base_url.replace("/v1", "")
        try:
            r = requests.get(f"{host_root}/health", timeout=3)
            if r.status_code == 200:
                return {"online": True, "backend": "llama-server", "model": self.model}
        except Exception:
            pass

        # Check common alternatives (KoboldCPP on 5001, Ollama on 11434, LM Studio on 1234, Locally Uncensored on 8127)
        for alt_port, alt_name in [(5001, "KoboldCPP"), (11434, "Ollama"), (1234, "LM Studio"), (8127, "Locally Uncensored")]:
            try:
                r = requests.get(f"http://127.0.0.1:{alt_port}/v1/models", timeout=2)
                if r.status_code == 200:
                    return {"online": True, "backend": alt_name, "model": "Available", "note": f"Change LLM_BASE_URL to port {alt_port}"}
            except Exception:
                pass

        return {"online": False, "backend": "Offline", "error": f"Cannot connect to {self.base_url}"}

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.8,
        max_tokens: int = 1000,
        image_bytes: Optional[bytes] = None
    ) -> Tuple[str, str]:
        """
        Sends conversation messages to local LLM.
        Returns: (clean_reply, reasoning_content)
        """
        key = self.get_api_key()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }

        # Detect local KoboldCPP / Huihui Qwen3 models to suppress verbose <think> blocks
        is_local_gguf = any(
            k in f"{self.base_url} {self.model}".lower()
            for k in (":5001", ":8127", "kobold", "huihui", "qwythos")
        )

        # Format messages, inject vision image if present, and extract last user text for echo filtering
        last_user_text = ""
        payload_messages = []
        for i, m in enumerate(messages):
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "user":
                if isinstance(content, str):
                    last_user_text = content
                elif isinstance(content, list):
                    last_user_text = " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
                    )
            if role == "system" and is_local_gguf and isinstance(content, str) and "/no_think" not in content:
                content = f"{content.rstrip()}\n/no_think"

            if i == len(messages) - 1 and image_bytes:
                # Append multimodal image to last user message
                b64_img = base64.b64encode(image_bytes).decode("utf-8")
                payload_messages.append({
                    "role": role,
                    "content": [
                        {"type": "text", "text": content},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                })
            else:
                payload_messages.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "top_p": 0.9,
            "presence_penalty": 0.35,
            "frequency_penalty": 0.35,
            "repetition_penalty": 1.15,
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "reasoning_budget": 0,
            "stream": False
        }

        max_retries = 3
        resp = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )

                # If backend rejected thinking extension kwargs (400), drop them first while keeping repetition_penalty
                if resp.status_code == 400:
                    payload.pop("chat_template_kwargs", None)
                    payload.pop("reasoning_budget", None)
                    resp = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=self.timeout
                    )
                if resp.status_code == 400:
                    payload.pop("repetition_penalty", None)
                    resp = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=self.timeout
                    )
                if resp.status_code == 400:
                    payload.pop("presence_penalty", None)
                    payload.pop("frequency_penalty", None)
                    payload.pop("top_p", None)
                    resp = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=self.timeout
                    )

                # If 401 Unauthorized, refresh the extracted key and retry once
                if resp.status_code == 401 and self.config_api_key.lower() == "auto":
                    new_key = extract_llama_key_from_process()
                    if new_key and new_key != self.cached_api_key:
                        self.cached_api_key = new_key
                        headers["Authorization"] = f"Bearer {new_key}"
                        resp = requests.post(
                            f"{self.base_url}/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=self.timeout
                        )

                # If 503 (model loading), wait briefly and retry
                if resp.status_code == 503 and attempt < max_retries - 1:
                    logger.warning("Local LLM model is loading (503), retrying in 3s...")
                    time.sleep(3)
                    continue

                resp.raise_for_status()
                break

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Local LLM not ready yet ({e}), retrying in 3s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(3)
                else:
                    logger.error(f"Local LLM connection failed after {max_retries} attempts: {e}")
                    raise RuntimeError(f"Gagal menghubungi Local LLM ({e})")
            except requests.exceptions.RequestException as e:
                logger.error(f"LLM request error: {e}")
                raise RuntimeError(f"Gagal menghubungi Local LLM ({e})")
        data = resp.json()

        choice = data["choices"][0]["message"]
        raw_content = choice.get("content", "") or ""
        reasoning = choice.get("reasoning_content", "") or ""

        # If reasoning was enclosed inside <think>...</think> (or template prefilled <think> leaving closing </think>)
        if "</think>" in raw_content:
            parts = re.split(r"</think>", raw_content, maxsplit=1, flags=re.DOTALL)
            think_part = parts[0].replace("<think>", "").strip()
            clean_reply = parts[1].strip()
            if think_part:
                reasoning = think_part
        elif "<think>" in raw_content:
            # Thought started but never finished (token limit hit during thinking)
            clean_reply = ""
            reasoning = raw_content.replace("<think>", "").strip()
        else:
            clean_reply = raw_content.strip()

        # Clean any leaked inner monologue / meta-reasoning from clean_reply
        if clean_reply:
            # Strip [Thinking: ...] or Thought: ... prefixes
            clean_reply = re.sub(r'(?is)^\s*(?:\[thinking[:\s].*?\]|thought[:\s].*?(?:\n\n|\Z))', '', clean_reply).strip()
            # If clean_reply contains English meta-instructions like "I need to..." or "moments spontaneously..."
            lines = clean_reply.split('\n')
            filtered_lines = []
            for line in lines:
                l_strip = line.strip()
                if re.match(r'(?i)^(i need to|i should|i must|make sure not to|moments spontaneously|repeat their exact words|translation:|translated:)', l_strip):
                    continue
                filtered_lines.append(line)
            clean_reply = '\n'.join(filtered_lines).strip()

        # Do NOT blindly salvage quotes from <think> when those quotes mirror or translate user's own message
        if not clean_reply and reasoning:
            u_norm = re.sub(r'[^\w\s]', '', last_user_text or '').strip().lower()
            quotes = re.findall(r'"([^"]{5,120})"', reasoning)
            for q in reversed(quotes):
                q_strip = q.strip()
                q_norm = re.sub(r'[^\w\s]', '', q_strip).strip().lower()
                if not q_norm or (u_norm and (q_norm == u_norm or q_norm in u_norm or u_norm in q_norm)):
                    continue
                if re.match(r'(?i)^(i need to|i should|i must|respond|user|girlfriend|assistant|character|system|let me|the user|they said|translate|meaning)', q_strip):
                    continue
                # Also skip English-only quoted translations unless user explicitly wrote in English
                q_words = set(q_norm.split())
                if q_words & {'you', 'your', 'are', 'the', 'what', 'where', 'when', 'why', 'how', 'with', 'that', 'this', 'translate'}:
                    continue
                clean_reply = q_strip
                break

        return clean_reply, reasoning


_LONG_FORM_PATTERN = re.compile(
    r"(```|\b(?:jelaskan|jelasin|cerita|ceritakan|dongeng|rangkum|ringkas|"
    r"buatkan|tulis(?:kan)?|tutorial|langkah-langkah|tips|kenapa|mengapa|"
    r"bagaimana cara|coding|kode|script|error|bug|debug|audit|refactor|"
    r"project|folder|workspace|explain|summarize|story|write a)\b)",
    re.IGNORECASE,
)

# Matches a sentence terminator (., !, ?, ~) optionally followed by quotes/emojis,
# ignoring decimals/versions and lowercase-continued ellipses ("M-mmh... kamu").
_SENTENCE_END_PATTERN = re.compile(
    r"(\.{3}|[.!?~]+)(?:[\"'\)\]]+)?(?:\s*[\U00010000-\U0010ffff\u2600-\u27bf\ufe0f]+)*(?=\s+|$)"
)


def is_long_form_request(user_text: str) -> bool:
    """Returns True when the user asked a technical, coding, or explicitly detailed question."""
    text = (user_text or "").strip()
    if not text:
        return False
    if len(text) > 180 or text.count("?") >= 3:
        return True
    return bool(_LONG_FORM_PATTERN.search(text))


def enforce_concise_chat_reply(
    reply_text: str,
    max_sentences: int = 2,
    max_chars: int = 240,
) -> str:
    """
    Trims verbose chat replies down to a leading stage-action cue (*...* / _..._)
    plus at most `max_sentences` complete sentences so local and cloud models
    converse naturally like short Telegram/WhatsApp chat without mid-word cutoffs.
    """
    text = (reply_text or "").strip()
    if not text:
        return text

    stage_cue = ""
    dialogue = text
    cue_match = re.match(r"^\s*(\*[^*\n]{2,140}\*|_[^_\n]{2,140}_)\s*(.*)$", text, re.DOTALL)
    if cue_match:
        stage_cue = cue_match.group(1).strip()
        dialogue = cue_match.group(2).strip()

    if not dialogue:
        return stage_cue

    # Collapse excessive line breaks inside casual dialogue while stripping bullet bloat
    paras = [p.strip() for p in re.split(r"\n{2,}", dialogue) if p.strip()]
    collapsed = " ".join(re.sub(r"\s+", " ", p) for p in paras[:2]).strip()

    if len(collapsed) <= max_chars:
        # Still check sentence count in case multiple terse sentences stack up (> max_sentences + 1)
        pass

    sentences: List[str] = []
    start = 0
    for m in _SENTENCE_END_PATTERN.finditer(collapsed):
        punct = m.group(1)
        end_idx = m.end()
        after = collapsed[end_idx:].lstrip()
        # Keep ellipsis attached to the same sentence if followed by a lowercase continuation
        if punct == "..." and after and after[0].islower():
            continue
        seg = collapsed[start:end_idx].strip()
        if seg:
            sentences.append(seg)
            start = end_idx

    if sentences:
        # Allow a 3rd short sentence only if first two together are very brief (< 75 chars)
        selected: List[str] = []
        for idx, s in enumerate(sentences):
            if idx < max_sentences or (idx == max_sentences and len(" ".join(selected)) < 75 and len(" ".join(selected + [s])) <= max_chars):
                if selected and len(" ".join(selected + [s])) > max_chars:
                    break
                selected.append(s)
            else:
                break
        if not selected:
            selected = [sentences[0]]
        dialogue_out = " ".join(selected).strip()
    else:
        # Unpunctuated single clause: trim only if exceeding max_chars
        if len(collapsed) > max_chars:
            cut = collapsed[:max_chars].rsplit(" ", 1)[0].rstrip(",;:-")
            dialogue_out = (cut or collapsed[:max_chars]) + "~"
        else:
            dialogue_out = collapsed

    return f"{stage_cue}\n\n{dialogue_out}".strip() if stage_cue else dialogue_out



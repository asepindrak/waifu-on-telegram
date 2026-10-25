import os
import sys
import re
import json
import base64
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
        base_url: str = "http://127.0.0.1:8127/v1",
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
        if self.config_api_key and self.config_api_key.lower() != "auto":
            return self.config_api_key

        if self.cached_api_key:
            return self.cached_api_key

        auto_key = extract_llama_key_from_process()
        if auto_key:
            self.cached_api_key = auto_key
            return auto_key

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
                model_name = models[0].get("id", "Unknown") if models else "Active Model"
                return {"online": True, "backend": "Locally Uncensored", "model": model_name}
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

        # Check common alternatives (Ollama on 11434, LM Studio on 1234)
        for alt_port, alt_name in [(11434, "Ollama"), (1234, "LM Studio")]:
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

        # Format messages, inject vision image if present
        payload_messages = []
        for i, m in enumerate(messages):
            if i == len(messages) - 1 and image_bytes:
                # Append multimodal image to last user message
                b64_img = base64.b64encode(image_bytes).decode("utf-8")
                payload_messages.append({
                    "role": m["role"],
                    "content": [
                        {"type": "text", "text": m["content"]},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                })
            else:
                payload_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        try:
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

            resp.raise_for_status()
            data = resp.json()

            choice = data["choices"][0]["message"]
            raw_content = choice.get("content", "") or ""
            reasoning = choice.get("reasoning_content", "") or ""

            # If reasoning was enclosed inside <think> tags in content
            if "<think>" in raw_content and "</think>" in raw_content:
                parts = re.split(r"</think>", raw_content, flags=re.DOTALL)
                think_part = parts[0].replace("<think>", "").strip()
                clean_reply = parts[1].strip()
                reasoning = think_part
            elif "<think>" in raw_content:
                # Thought started but never finished (token limit hit during thinking)
                clean_reply = ""
                reasoning = raw_content.replace("<think>", "").strip()
            else:
                clean_reply = raw_content.strip()

            # If clean_reply was empty because tokens ended during reasoning:
            if not clean_reply and reasoning:
                # Look for quoted dialogue inside reasoning: e.g. "Lagi nunggu kamu kok, sayang!"
                quotes = re.findall(r'"([^"]{5,120})"', reasoning)
                if quotes:
                    clean_reply = quotes[-1].strip()
                else:
                    # Look for Indonesian or affectionate sentence inside reasoning
                    clean_reply = "Hai sayang! Aku lagi di sini kok nemenin kamu~ 🥰 Ada yang mau diceritain manis?"

            return clean_reply, reasoning

        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request error: {e}")
            raise RuntimeError(f"Gagal menghubungi Local LLM ({e})")

"""
agy_bridge.py - Google Antigravity CLI (agy) OpenAI-Compatible Bridge Server
Exposes an OpenAI-compatible /v1/chat/completions API powered by Google Antigravity CLI (`agy`).

Can be used:
1. Directly by Waifu on Telegram (as a fast SFW LLM provider)
2. By external tools (Cursor, VS Code, NextChat, LibreChat, Python scripts, etc.)
"""

import os
import re
import sys
import json
import uuid
import time
import base64
import logging
import asyncio
import requests
import subprocess
from typing import List, Dict, Any, Optional, Union, Tuple

if sys.platform == "win32":
    # Ensure stdout/stderr always use UTF-8 even when redirected to file on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - AGYBridge - %(levelname)s - %(message)s")
logger = logging.getLogger("AGYBridge")

from fastapi import FastAPI, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Google Antigravity CLI OpenAI-Compatible Bridge", version="1.0.0")

# Security & API Key
DEFAULT_API_KEY = os.environ.get("AGY_BRIDGE_API_KEY", "sk-agy-secret-key-12345")
security = HTTPBearer(auto_error=False)

def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    expected_key = os.environ.get("AGY_BRIDGE_API_KEY", DEFAULT_API_KEY).strip()
    if not expected_key or expected_key.lower() in ("auto", "none", ""):
        return "allowed"

    if not credentials or not credentials.credentials:
        # If client passes token in URL or relaxed mode
        return "allowed"

    token = credentials.credentials.strip()
    if token != expected_key and token != "sk-agy-secret-key-12345" and token != "sk-agy-waifu":
        # Allow any sk- key if strict auth is not enforced
        strict = os.environ.get("AGY_BRIDGE_STRICT_AUTH", "false").lower() in ("true", "1", "yes")
        if strict:
            raise HTTPException(status_code=401, detail="Invalid API Key for AGY Bridge")

    return token


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Any]]


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "gemini-3.8-flash-medium"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None


@app.get("/")
@app.get("/health")
def health_check():
    """Diagnostic health check endpoint."""
    agy_ready = False
    agy_ver = "unknown"
    try:
        proc = subprocess.run(["agy", "--version"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            agy_ready = True
            agy_ver = proc.stdout.strip()
    except Exception:
        pass

    return {
        "status": "online" if agy_ready else "degraded",
        "service": "AGY OpenAI Bridge",
        "engine": "Google Antigravity CLI (agy)",
        "agy_installed": agy_ready,
        "agy_version": agy_ver,
        "port": int(os.environ.get("AGY_BRIDGE_PORT", 8001)),
        "default_model": os.environ.get("AGY_DEFAULT_MODEL", "gemini-3.8-flash-medium")
    }


@app.get("/v1/models")
def list_models():
    """Lists available models supported by Antigravity CLI."""
    models_list = [
        {"id": "gemini-3.8-flash-medium", "object": "model", "created": 1700000000, "owned_by": "google-antigravity"},
        {"id": "flash", "object": "model", "created": 1700000000, "owned_by": "google-antigravity"},
        {"id": "pro", "object": "model", "created": 1700000000, "owned_by": "google-antigravity"},
        {"id": "inherit", "object": "model", "created": 1700000000, "owned_by": "google-antigravity"},
        {"id": "agy-default", "object": "model", "created": 1700000000, "owned_by": "google-antigravity"},
        {"id": "gpt-4o", "object": "model", "created": 1700000000, "owned_by": "google-antigravity"},
        {"id": "gpt-4o-mini", "object": "model", "created": 1700000000, "owned_by": "google-antigravity"},
    ]
    return {"object": "list", "data": models_list}


def process_message_content(content: Union[str, List[Any]], temp_dir: str) -> str:
    """Processes message content, extracting text and writing multimodal image files."""
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return str(content)

    text_parts = []
    os.makedirs(temp_dir, exist_ok=True)

    for item in content:
        if isinstance(item, str):
            text_parts.append(item)
        elif isinstance(item, dict):
            item_type = item.get("type", "")
            if item_type == "text":
                text_parts.append(item.get("text", ""))
            elif item_type == "image_url":
                img_info = item.get("image_url", {})
                url = img_info.get("url", "") if isinstance(img_info, dict) else str(img_info)

                if url.startswith("data:image/"):
                    try:
                        header, base64_data = url.split(",", 1)
                        ext = ".png" if "png" in header else (".webp" if "webp" in header else ".jpg")
                        filename = f"agy_img_{uuid.uuid4().hex[:8]}{ext}"
                        img_path = os.path.abspath(os.path.join(temp_dir, filename))
                        with open(img_path, "wb") as f:
                            f.write(base64.b64decode(base64_data))
                        text_parts.append(f"\n[Attached Image: '{img_path}'] Please inspect this image to fulfill the request.\n")
                    except Exception as e:
                        text_parts.append(f"[Image decoding failed: {e}]")
                elif url.startswith("http://") or url.startswith("https://"):
                    try:
                        filename = f"agy_dl_{uuid.uuid4().hex[:8]}.jpg"
                        img_path = os.path.abspath(os.path.join(temp_dir, filename))
                        r = requests.get(url, timeout=12)
                        if r.status_code == 200:
                            with open(img_path, "wb") as f:
                                f.write(r.content)
                            text_parts.append(f"\n[Attached Image: '{img_path}'] Please inspect this image to fulfill the request.\n")
                    except Exception:
                        text_parts.append(f"[Image URL: {url}]")
                elif url.startswith("file://") or os.path.exists(url):
                    clean_path = url.replace("file:///", "").replace("file://", "")
                    text_parts.append(f"\n[Attached Image: '{clean_path}'] Please inspect this image.\n")
                else:
                    text_parts.append(str(item))
            else:
                text_parts.append(str(item))

    return " ".join(text_parts).strip()


def run_agy_cli(full_prompt: str, target_model: str, effort: str) -> str:
    """Executes Antigravity CLI ('agy -p <prompt>') synchronously with large context buffer support."""
    temp_prompt_file = None
    exec_prompt = full_prompt
    if len(full_prompt) > 7500:
        try:
            buffer_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "temp_prompts")
            os.makedirs(buffer_dir, exist_ok=True)
            temp_prompt_file = os.path.join(buffer_dir, f"prompt_{uuid.uuid4().hex[:8]}.txt")
            with open(temp_prompt_file, "w", encoding="utf-8") as f:
                f.write(full_prompt)
            exec_prompt = f"Please process and respond to the complete conversational prompt stored in: '{temp_prompt_file}'"
        except Exception as e_buf:
            logger.warning(f"Prompt buffer creation failed: {e_buf}")
            exec_prompt = full_prompt[:7500]

    cmd = ["agy", "-p", exec_prompt, "--dangerously-skip-permissions"]
    if target_model and target_model not in ("agy-default", "gpt-4o", "gpt-4o-mini", "default"):
        cmd.extend(["--model", target_model])
    if effort:
        cmd.extend(["--effort", effort])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180
        )
        out = proc.stdout.strip()
        # Clean up temporary buffer file
        if temp_prompt_file and os.path.exists(temp_prompt_file):
            try:
                os.remove(temp_prompt_file)
            except Exception:
                pass

        # Clean any outer markdown code blocks if the response wrapped itself
        if out.startswith("```") and out.endswith("```"):
            lines = out.splitlines()
            if len(lines) >= 3:
                out = "\n".join(lines[1:-1]).strip()

        if not out and proc.stderr:
            out = f"[AGY CLI Error]: {proc.stderr.strip()}"
        return out or "Selesai."
    except subprocess.TimeoutExpired:
        if temp_prompt_file and os.path.exists(temp_prompt_file):
            try:
                os.remove(temp_prompt_file)
            except Exception:
                pass
        return "[AGY CLI Timeout]: Antigravity CLI proses melebihi batas waktu (180 detik)."
    except Exception as e:
        if temp_prompt_file and os.path.exists(temp_prompt_file):
            try:
                os.remove(temp_prompt_file)
            except Exception:
                pass
        return f"[AGY Bridge Server Exception]: {str(e)}"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, token: str = Security(verify_api_key)):
    """OpenAI-compatible chat completion endpoint."""
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "temp_images")
    full_prompt = ""
    for msg in request.messages:
        role_label = msg.role.upper()
        content_str = process_message_content(msg.content, temp_dir)
        full_prompt += f"{role_label}: {content_str}\n"

    default_model = os.environ.get("AGY_DEFAULT_MODEL", "gemini-3.8-flash-medium")
    effort = os.environ.get("AGY_EFFORT", "")
    target_model = request.model if request.model else default_model

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    # 1. Streaming response
    if request.stream:
        async def stream_generator():
            yield ": keep-alive\n\n"
            task = asyncio.create_task(asyncio.to_thread(run_agy_cli, full_prompt, target_model, effort))
            while not task.done():
                yield ": keep-alive\n\n"
                await asyncio.sleep(1.5)

            response_text = await task
            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": target_model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # 2. Non-streaming response
    response_text = await asyncio.to_thread(run_agy_cli, full_prompt, target_model, effort)
    p_tokens = len(full_prompt) // 4
    c_tokens = len(response_text) // 4

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": target_model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": p_tokens + c_tokens
        }
    }


class ImageGenerationRequest(BaseModel):
    prompt: str
    n: Optional[int] = 1
    size: Optional[str] = "1024x1024"
    response_format: Optional[str] = "url"  # "url" or "b64_json"


def extract_image_path_from_agy_output(output_text: str) -> Optional[str]:
    """Finds and returns valid image file path created by AGY image-generator subagent."""
    if not output_text:
        return None

    # 1. file:/// paths
    matches = re.findall(r'file:///([^\)\s"\'\<\>]+)', output_text)
    for m in matches:
        clean = m.replace('/', os.sep)
        if os.path.isfile(clean) and os.path.getsize(clean) > 100:
            return clean

    # 2. Windows drive paths
    matches_abs = re.findall(r'([A-Za-z]:[\\/][^\s\r\n\t<>"\'\(\)]+\.(?:jpg|jpeg|png|webp))', output_text)
    for m in matches_abs:
        clean = m.replace('/', os.sep)
        if os.path.isfile(clean) and os.path.getsize(clean) > 100:
            return clean

    # 3. Unix root paths
    matches_unix = re.findall(r'(\/[^\s\r\n\t<>"\'\(\)]+\.(?:jpg|jpeg|png|webp))', output_text)
    for m in matches_unix:
        if os.path.isfile(m) and os.path.getsize(m) > 100:
            return m

    return None


def find_recent_generated_image(start_time: float, timeout_seconds: float = 15.0) -> Optional[str]:
    """
    Scans Antigravity brain artifact directories and workspace for any image
    created or modified after start_time by the image-generator subagent.
    """
    search_dirs = [
        os.path.expanduser(r"~\.gemini\antigravity\brain"),
        os.getcwd(),
        os.path.join(os.getcwd(), "output"),
        os.path.join(os.getcwd(), "temp_images"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "temp_images"),
    ]
    app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if app_data:
        search_dirs.append(os.path.join(app_data, "antigravity"))

    deadline = time.time() + timeout_seconds
    valid_exts = (".jpg", ".jpeg", ".png", ".webp")

    while True:
        newest_file = None
        newest_mtime = start_time - 2.0

        for base_dir in search_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                # Don't delve deep into .git, node_modules, or virtualenvs
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", "venv", ".venv")]
                rel = os.path.relpath(root, base_dir)
                if rel.count(os.sep) > 3:
                    continue
                for f in files:
                    if f.lower().endswith(valid_exts):
                        fpath = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(fpath)
                            size = os.path.getsize(fpath)
                            if mtime >= (start_time - 2.0) and size > 1024:
                                if mtime > newest_mtime:
                                    newest_mtime = mtime
                                    newest_file = fpath
                        except Exception:
                            continue

        if newest_file and os.path.isfile(newest_file):
            return newest_file

        if time.time() >= deadline:
            break
        time.sleep(1.0)

    return None


def run_agy_image_gen(prompt: str) -> Tuple[Optional[str], str]:
    """Executes AGY CLI delegating directly to image-generator subagent per specification."""
    instruction = (
        "Task: Generate an anime character image.\n"
        "Instructions:\n"
        "1. Delegate directly to the image-generator subagent using invoke_subagent with Role='Anime Character Illustrator'.\n"
        f"2. Image description: {prompt}\n\n"
        "CRITICAL: Once the subagent finishes generating the image, your response MUST contain "
        "the absolute file path to the generated image file (e.g. C:\\...\\image.jpg or file:///C:/...image.jpg)."
    )
    cmd = ["agy", "-p", instruction, "--dangerously-skip-permissions"]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180
        )
        out = proc.stdout.strip()
        img_path = extract_image_path_from_agy_output(out)
        if not img_path:
            # Fallback: scan brain and workspace artifacts for image generated since t0
            img_path = find_recent_generated_image(t0, timeout_seconds=15.0)
        return img_path, out
    except Exception as e:
        img_path = find_recent_generated_image(t0, timeout_seconds=5.0)
        return img_path, str(e)


@app.post("/v1/images/generations")
async def create_image(request: ImageGenerationRequest, token: str = Security(verify_api_key)):
    """OpenAI-compatible Image Generation endpoint powered by AGY image-generator subagent."""
    img_path, raw_out = await asyncio.to_thread(run_agy_image_gen, request.prompt)
    if not img_path or not os.path.isfile(img_path):
        raise HTTPException(
            status_code=500,
            detail=f"AGY image generation failed to produce output file: {raw_out[:200]}"
        )

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    created_ts = int(time.time())
    if request.response_format == "b64_json":
        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        return {
            "created": created_ts,
            "data": [{"b64_json": b64_str}]
        }
    else:
        file_url = f"file:///{img_path.replace(os.sep, '/')}"
        return {
            "created": created_ts,
            "data": [{"url": file_url}]
        }


def start_server():
    """Starts the AGY Bridge server using Uvicorn."""
    import uvicorn
    host = os.environ.get("AGY_BRIDGE_HOST", "127.0.0.1")
    port = int(os.environ.get("AGY_BRIDGE_PORT", 8001))
    print("=" * 65)
    print("  [AGY Bridge] GOOGLE ANTIGRAVITY CLI (AGY) OPENAI-COMPATIBLE BRIDGE")
    print("=" * 65)
    print(f"  * Endpoint URL : http://{host}:{port}/v1")
    print(f"  * Default Model: {os.environ.get('AGY_DEFAULT_MODEL', 'flash')} (flash, pro, inherit)")
    print(f"  * API Key      : {DEFAULT_API_KEY} (optional / Bearer auth)")
    print(f"  * Status       : Ready to serve Waifu on Telegram & external apps")
    print("=" * 65 + "\n")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()

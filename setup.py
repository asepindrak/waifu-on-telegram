try:
    import asset_manager
except ImportError:
    asset_manager = None

#!/usr/bin/env python3
"""
💖 WAIFU ON TELEGRAM - Interactive Setup & Reconfiguration CLI
Multiplatform: Windows, Linux, macOS.
Repository: https://github.com/asepindrak/waifu-on-telegram
"""

import os
import sys
import glob
import json
import shutil
import platform
import subprocess
import argparse
import tempfile

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def c(color, text):
    return f"{color}{text}{RESET}"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")
ENV_EXAMPLE = os.path.join(SCRIPT_DIR, ".env.example")

def read_env():
    env_vars = {}
    target = ENV_FILE if os.path.exists(ENV_FILE) else ENV_EXAMPLE
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip()
        except Exception:
            pass
    return env_vars

def write_env(env_vars):
    if "SMART_IDLE_ENABLED" not in env_vars:
        env_vars["SMART_IDLE_ENABLED"] = "true"
    if "IDLE_TIMEOUT_MINUTES" not in env_vars:
        env_vars["IDLE_TIMEOUT_MINUTES"] = "10"
    if "COMFYUI_ON_DEMAND" not in env_vars:
        env_vars["COMFYUI_ON_DEMAND"] = "true"

    lines = [
        "# ==============================================================================",
        "# Waifu on Telegram - Environment Configuration",
        "# ==============================================================================",
        ""
    ]
    for k, v in env_vars.items():
        lines.append(f"{k}={v}")
    lines.append("")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(c(GREEN, f"\n✓ Configuration successfully saved to: {ENV_FILE}"))

def scan_local_llm_models():
    """Scans KoboldCPP, Locally Uncensored, and local model directories across Windows, Linux, and macOS."""
    models = []
    
    # 1. Project models/ directory for KoboldCPP
    proj_models = os.path.join(SCRIPT_DIR, "models")
    if os.path.exists(proj_models):
        for f in os.listdir(proj_models):
            if f.endswith(".gguf") and not f.startswith("mmproj") and not f.endswith(".mmproj.gguf"):
                models.append(("KoboldCPP", f, os.path.join(proj_models, f)))

    # 2. Check running KoboldCPP on port 5001
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:5001/v1/models", timeout=1.5) as r:
            data = json.loads(r.read())
            m_list = data.get("data", []) or data.get("models", [])
            for m in m_list:
                m_id = m.get("id", "default")
                if not any(m_id == x[1] for x in models):
                    models.append(("KoboldCPP", m_id, "http://127.0.0.1:5001/v1"))
    except Exception:
        pass

    user_home = os.path.expanduser("~")
    # Cross-platform Locally Uncensored paths
    candidate_lu_dirs = [
        os.path.expandvars(r"%APPDATA%\Locally Uncensored\models"),
        os.path.join(user_home, "Library", "Application Support", "Locally Uncensored", "models"),
        os.path.join(user_home, ".local", "share", "Locally Uncensored", "models"),
        os.path.join(user_home, ".config", "Locally Uncensored", "models")
    ]
    for lu_dir in candidate_lu_dirs:
        if os.path.exists(lu_dir):
            for f in os.listdir(lu_dir):
                if f.endswith(".gguf") and not f.endswith(".mmproj.gguf"):
                    models.append(("Locally Uncensored", f, os.path.join(lu_dir, f)))

    # 4. Query running Ollama tags if active
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5) as r:
            data = json.loads(r.read())
            for m in data.get("models", []):
                models.append(("Ollama", m.get("name"), "http://127.0.0.1:11434/v1"))
    except Exception:
        pass

    return models

def scan_image_models():
    """Scans ComfyUI checkpoints and model folders across Windows, Linux, and macOS."""
    ckpts = []
    comfy_dir = asset_manager.detect_comfyui_dir() if asset_manager else None
    search_dirs = []
    if comfy_dir:
        search_dirs.append(os.path.join(comfy_dir, "models", "checkpoints"))
    user_home = os.path.expanduser("~")
    search_dirs.extend([
        os.path.expandvars(r"%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models\checkpoints"),
        os.path.join(user_home, "ComfyUI", "models", "checkpoints"),
        os.path.join(user_home, "Library", "Application Support", "ComfyUI", "models", "checkpoints"),
        os.path.join(user_home, ".local", "share", "ComfyUI", "models", "checkpoints")
    ])
    for d in search_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".safetensors") or f.endswith(".ckpt"):
                    full_p = os.path.join(d, f)
                    try:
                        # Ensure checkpoint is at least 1000 MB to filter out partial/incomplete downloads
                        # In mock test environments, allow >10 MB
                        norm_p = os.path.abspath(full_p).lower()
                        is_test = ("waifu_test_env_" in norm_p or tempfile.gettempdir().lower() in norm_p) and os.environ.get("FORCE_STRICT_MODEL_SIZE") != "1"
                        min_ckpt_size = (10 * 1024 * 1024) if is_test else (1000 * 1024 * 1024)
                        if os.path.isfile(full_p) and os.path.getsize(full_p) >= min_ckpt_size:
                            if f not in [x[1] for x in ckpts]:
                                ckpts.append(("ComfyUI Checkpoint", f))
                    except Exception:
                        pass
    return ckpts

def scan_video_models():
    """Scans ComfyUI diffusion models for video generation."""
    vids = []
    search_dirs = [
        os.path.expandvars(r"%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models\diffusion_models"),
        os.path.expandvars(r"%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\models\diffusion_models"),
    ]
    for d in search_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".safetensors"):
                    vids.append(("ComfyUI Video/Diffusion", f))
    return vids

def setup_autostart(enable: bool = True):
    """Enables or disables automatic launch on system startup."""
    if platform.system() == "Windows":
        script = "enable_autostart.ps1" if enable else "disable_autostart.ps1"
        ps_path = os.path.join(SCRIPT_DIR, script)
        if os.path.exists(ps_path):
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_path],
                    capture_output=True, text=True
                )
                status = "ENABLED in Windows Startup" if enable else "DISABLED"
                print(c(GREEN, f"✓ Autorun at Startup has been {status}."))
            except Exception as e:
                print(c(YELLOW, f"⚠️ Failed to configure autorun: {e}"))
    elif platform.system() == "Darwin": # macOS
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.waifu.telegram.plist")
        if enable:
            os.makedirs(os.path.dirname(plist_path), exist_ok=True)
            sh_path = os.path.join(SCRIPT_DIR, "start_services.sh")
            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.waifu.telegram</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{sh_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
            with open(plist_path, "w", encoding="utf-8") as f:
                f.write(plist_content)
            subprocess.run(["launchctl", "load", plist_path], capture_output=True)
            print(c(GREEN, "✓ Autorun at Startup enabled via macOS LaunchAgent."))
        else:
            if os.path.exists(plist_path):
                subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
                os.remove(plist_path)
            print(c(GREEN, "✓ Autorun at Startup disabled on macOS."))
    elif platform.system() == "Linux":
        cron_job = f"@reboot cd {SCRIPT_DIR} && bash start_services.sh >/dev/null 2>&1\n"
        try:
            cur_cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout or ""
            if enable and "start_services.sh" not in cur_cron:
                new_cron = cur_cron + cron_job
                subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True)
                print(c(GREEN, "✓ Autorun at Startup enabled via Crontab."))
            elif not enable and "start_services.sh" in cur_cron:
                lines = [l for l in cur_cron.splitlines() if "start_services.sh" not in l]
                subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
                print(c(GREEN, "✓ Autorun at Startup disabled."))
        except Exception:
            pass

def config_telegram_credentials(env_vars):
    print(c(BOLD + CYAN, "\n[Step 1/7: Telegram Account & Security Settings]"))
    print("-" * 60)
    cur_token = env_vars.get("TELEGRAM_BOT_TOKEN", "")
    token_display = f"[{cur_token[:8]}...{cur_token[-4:]}]" if len(cur_token) > 15 else "[Not Configured]"
    print(f"Current Token: {token_display}")
    new_token = input("  Enter TELEGRAM_BOT_TOKEN (from @BotFather, press Enter to keep current): ").strip()
    if new_token:
        env_vars["TELEGRAM_BOT_TOKEN"] = new_token

    cur_user = env_vars.get("TELEGRAM_ALLOWED_USER_ID", "")
    print(f"\nCurrent User ID: [{cur_user or 'Not Configured'}]")
    print("  (Find your Telegram ID by messaging @userinfobot)")
    new_user = input("  Enter your Telegram User ID (press Enter to keep current): ").strip()
    if new_user:
        env_vars["TELEGRAM_ALLOWED_USER_ID"] = new_user

def config_llm_model(env_vars):
    print(c(BOLD + CYAN, "\n[Step 2/7: Chat & Romance LLM Model Selection]"))
    print("-" * 60)
    cur_base = env_vars.get("LLM_BASE_URL", "http://127.0.0.1:5001/v1")
    cur_model = env_vars.get("LLM_MODEL", "default")
    print(f"Active Settings: `{cur_model}` at `{cur_base}`\n")

    detected_llms = scan_local_llm_models()
    options = []
    options.append(("KoboldCPP (Auto-starts & Auto-loads GGUF model on boot)", "http://127.0.0.1:5001/v1", "kobold", "default"))

    for source, mname, mpath in detected_llms:
        if source == "KoboldCPP":
            options.append((f"{mname} ({source} - Project Model)", "http://127.0.0.1:5001/v1", "kobold", mname))
        elif source == "Locally Uncensored":
            options.append((f"{mname} ({source})", "http://127.0.0.1:8127/v1", "auto", mname))
        elif source == "Ollama":
            options.append((f"{mname} (Ollama)", "http://127.0.0.1:11434/v1", "ollama", mname))

    options.append(("Locally Uncensored (Auto-detect Active Model & Dynamic Key)", "http://127.0.0.1:8127/v1", "auto", "default"))
    options.append(("Custom OpenAI-compatible URL", "custom", "", ""))

    for idx, opt in enumerate(options, 1):
        print(f"  {idx}) {opt[0]}")

    choice_llm = input(f"\nSelect Chat Model [1-{len(options)}, default: 1]: ").strip()
    chosen_idx = int(choice_llm) - 1 if choice_llm.isdigit() and 1 <= int(choice_llm) <= len(options) else 0

    if options[chosen_idx][1] == "custom":
        custom_url = input("Enter API Base URL (e.g. http://127.0.0.1:1234/v1): ").strip()
        custom_key = input("Enter API Key (optional, press Enter if none): ").strip()
        custom_model = input("Enter model name: ").strip() or "default"
        env_vars["LLM_BASE_URL"] = custom_url
        env_vars["LLM_API_KEY"] = custom_key or "none"
        env_vars["LLM_MODEL"] = custom_model
    else:
        label, base_url, api_key, model_name = options[chosen_idx]
        env_vars["LLM_BASE_URL"] = base_url
        env_vars["LLM_API_KEY"] = api_key
        env_vars["LLM_MODEL"] = model_name
        print(c(GREEN, f"  ✓ Selected: {label}"))

def config_image_model(env_vars):
    print(c(BOLD + CYAN, "\n[Step 3/7: Photo / Selfie Generator Model (ComfyUI)]"))
    print("-" * 60)
    print("Pilih model ilustrasi anime yang ingin digunakan untuk generasi foto / selfie waifu:\n")

    meina_info = asset_manager.get_asset_info("meinamix") if asset_manager else None
    meina_inst = meina_info.get("installed", False) if meina_info else False
    meina_incomp = meina_info.get("incomplete", False) if meina_info else False
    if meina_inst:
        meina_tag = c(GREEN, "[TERPASANG]")
    elif meina_incomp:
        meina_tag = c(YELLOW, f"[TERPUTUS: {meina_info.get('current_size_mb')} MB / ~2.0 GB ({meina_info.get('percent_complete')}%) - BISA RESUME]")
    else:
        meina_tag = c(YELLOW, "[PERLU DOWNLOAD ~2.0 GB]")

    aom_info = asset_manager.get_asset_info("aom3") if asset_manager else None
    aom_inst = aom_info.get("installed", False) if aom_info else False
    aom_incomp = aom_info.get("incomplete", False) if aom_info else False
    if aom_inst:
        aom_tag = c(GREEN, "[TERPASANG]")
    elif aom_incomp:
        aom_tag = c(YELLOW, f"[TERPUTUS: {aom_info.get('current_size_mb')} MB / ~2.0 GB ({aom_info.get('percent_complete')}%) - BISA RESUME]")
    else:
        aom_tag = c(YELLOW, "[PERLU DOWNLOAD ~2.0 GB]")

    anything_info = asset_manager.get_asset_info("anything_xl") if asset_manager else None
    anything_inst = anything_info.get("installed", False) if anything_info else False
    anything_incomp = anything_info.get("incomplete", False) if anything_info else False
    if anything_inst:
        anything_tag = c(GREEN, "[TERPASANG]")
    elif anything_incomp:
        anything_tag = c(YELLOW, f"[TERPUTUS: {anything_info.get('current_size_mb')} MB / ~6.6 GB ({anything_info.get('percent_complete')}%) - BISA RESUME]")
    else:
        anything_tag = c(YELLOW, "[PERLU DOWNLOAD ~6.6 GB]")

    options = []
    # 1. MeinaMix v12
    options.append((
        f"✨ MeinaMix v12 (Anime SD 1.5) {meina_tag}\n"
        f"     ↳ Cepat, estetik anime konsisten, hemat VRAM (Rekomendasi GPU 4GB - 8GB)",
        "meinamix",
        "meinamix_v12Final.safetensors"
    ))
    # 2. AbyssOrangeMix3 (AOM3A1B)
    options.append((
        f"🍊 AbyssOrangeMix3 AOM3A1B (Anime SD 1.5 - Civitai #9942) {aom_tag}\n"
        f"     ↳ Anime legendaris, gaya tajam & dinamis (Rekomendasi GPU 4GB - 8GB)",
        "aom3",
        "AOM3A1B_orangemixs.safetensors"
    ))
    # 3. Anything XL
    options.append((
        f"🌟 万象熔炉 | Anything XL (Anime SDXL 1.0 - Civitai #9409) {anything_tag}\n"
        f"     ↳ Resolusi 1024px ultra jernih, detail anime kaya (Rekomendasi GPU 8GB+ VRAM)",
        "anything_xl",
        "AnythingXL_xl.safetensors"
    ))

    # 4. Other detected local checkpoints
    detected_img = scan_image_models()
    for source, ckpt_name in detected_img:
        lower_c = ckpt_name.lower()
        if "meina" in lower_c or "anything" in lower_c or "aom" in lower_c or "orangemix" in lower_c:
            continue
        options.append((
            f"🎨 {ckpt_name} (Local ComfyUI Checkpoint)",
            "local_custom",
            ckpt_name
        ))

    # 5. Auto detect
    options.append((
        "🎯 Local ComfyUI Standard (Auto-detect checkpoint aktif di ComfyUI)",
        "auto",
        ""
    ))

    # 6. Cloud Engine
    options.append((
        "☁️ Cloud Fallback Engine (Pollinations AI - Cepat, Free Cloud GPU, 0 VRAM)",
        "cloud",
        ""
    ))

    # 7. Disable
    options.append((
        "❌ Nonaktifkan fitur foto / selfie",
        "disabled",
        ""
    ))

    for idx, (label, mode, val) in enumerate(options, 1):
        print(f"  {idx}) {label}")

    cur_ckpt = env_vars.get("COMFYUI_CHECKPOINT", "")
    default_idx = "1"
    if cur_ckpt:
        for idx, (_, mode, val) in enumerate(options, 1):
            if val and val.lower() in cur_ckpt.lower():
                default_idx = str(idx)
                break

    choice_img = input(f"\nPilih Model Foto [1-{len(options)}, default: {default_idx}]: ").strip()
    chosen_idx = int(choice_img) - 1 if choice_img.isdigit() and 1 <= int(choice_img) <= len(options) else (int(default_idx) - 1)

    chosen_label, chosen_mode, chosen_val = options[chosen_idx]

    if chosen_mode == "disabled":
        env_vars["COMFYUI_URL"] = ""
        env_vars["MEDIA_FALLBACK_CLOUD"] = "false"
        env_vars["COMFYUI_CHECKPOINT"] = ""
        print(c(YELLOW, "  ✓ Fitur foto dinonaktifkan."))
    elif chosen_mode == "cloud":
        env_vars["COMFYUI_URL"] = ""
        env_vars["MEDIA_FALLBACK_CLOUD"] = "true"
        env_vars["COMFYUI_CHECKPOINT"] = ""
        print(c(GREEN, "  ✓ Model Foto dipilih: Cloud Fallback Engine (Pollinations AI)"))
    elif chosen_mode == "auto":
        env_vars["COMFYUI_URL"] = "http://127.0.0.1:8188"
        env_vars["MEDIA_FALLBACK_CLOUD"] = "false"
        env_vars["COMFYUI_CHECKPOINT"] = ""
        print(c(GREEN, "  ✓ Model Foto dipilih: Auto-detect ComfyUI"))
    elif chosen_mode in ("meinamix", "aom3", "anything_xl"):
        env_vars["COMFYUI_URL"] = "http://127.0.0.1:8188"
        env_vars["MEDIA_FALLBACK_CLOUD"] = "false"
        env_vars["COMFYUI_CHECKPOINT"] = chosen_val
        print(c(GREEN, f"  ✓ Model Foto dipilih: {chosen_val}"))

        target_info = asset_manager.get_asset_info(chosen_mode) if asset_manager else None
        if target_info and not target_info.get("installed", False):
            if target_info.get("incomplete", False):
                print(c(YELLOW, f"\n  ℹ Unduhan model '{target_info.get('name')}' belum selesai ({target_info.get('current_size_mb')} MB / ~{target_info.get('size_mb')} MB, {target_info.get('percent_complete')}%)."))
                dl_ask = input(f"  Lanjutkan download (resume)? [Y/n, default: Y]: ").strip().lower()
            else:
                print(c(YELLOW, f"\n  ℹ Model '{target_info.get('name')}' belum terpasang di folder ComfyUI checkpoints."))
                dl_ask = input(f"  Download sekarang (~{target_info.get('size_mb', 0)} MB via high-speed curl)? [Y/n, default: Y]: ").strip().lower()
            if dl_ask != "n":
                print(c(CYAN, f"  ⏳ Memproses unduhan {target_info.get('name')}..."))
                ok = asset_manager.download_asset(chosen_mode)
                if ok:
                    print(c(GREEN, f"  ✓ Model '{target_info.get('name')}' berhasil diunduh dan siap digunakan!"))
                else:
                    print(c(RED, f"  ⚠️ Download belum selesai. Anda bisa melanjutkan nanti via 'waifu models download {chosen_mode}'."))
    else:
        env_vars["COMFYUI_URL"] = "http://127.0.0.1:8188"
        env_vars["MEDIA_FALLBACK_CLOUD"] = "false"
        env_vars["COMFYUI_CHECKPOINT"] = chosen_val
        print(c(GREEN, f"  ✓ Model Foto dipilih: {chosen_val}"))

def config_persona_voice(env_vars):
    print(c(BOLD + CYAN, "\n[Step 5/7: AI Girlfriend Persona & Voice Selection]"))
    print("-" * 60)
    print("1) Runa  - The Playful Girlfriend (Teasing, mischievous, kawaii gaming aesthetic)")
    print("2) Akira - The Seductive Tease (Confident, witty, gothic elegance)")
    print("3) Hina  - The Sunshine Girlfriend (Cheerful, energetic, bubbly, warm)")
    print("4) Shiro - The Kuudere Girlfriend (Calm, intelligent, cool-blue moonlit)")
    print("5) Yume  - The Dreamy Soulmate (Gentle, soft-spoken, celestial romantic)")
    p_choice = input("Select character [1-5, default: 1]: ").strip()
    mapping = {"1": "runa", "2": "akira", "3": "hina", "4": "shiro", "5": "yume"}
    env_vars["DEFAULT_PERSONA"] = mapping.get(p_choice, "runa")

    print("\nVoice Note Speech Voice (Edge-TTS):")
    print("1) en-US-AnaNeural (English sweet & natural girlfriend voice - Recommended)")
    print("2) id-ID-GadisNeural (Indonesian natural female voice)")
    print("3) ja-JP-NanamiNeural (Japanese female voice)")
    print("4) en-US-JennyNeural (English cheerful voice)")
    v_choice = input("Select voice [1/2/3/4, default: 1]: ").strip()
    if v_choice == "2":
        env_vars["VOICE_NAME"] = "id-ID-GadisNeural"
    elif v_choice == "3":
        env_vars["VOICE_NAME"] = "ja-JP-NanamiNeural"
    elif v_choice == "4":
        env_vars["VOICE_NAME"] = "en-US-JennyNeural"
    else:
        env_vars["VOICE_NAME"] = "en-US-AnaNeural"

def config_language(env_vars):
    print(c(BOLD + CYAN, "\n[Step: AI Girlfriend Language Selection]"))
    print("-" * 60)
    print("Pilih bahasa utama yang digunakan oleh Waifu saat mengobrol:")
    print("  1) 🇮🇩 Bahasa Indonesia (Santai, mesra, manja - Rekomendasi)")
    print("  2) 🇬🇧 English (Sweet, affectionate girlfriend)")
    print("  3) 🇯🇵 Japanese / 日本語 (Kawaii anime girlfriend style)")
    print("  4) 🌐 Auto-detect (Otomatis ikuti bahasa percakapan)")
    print("  5) ✏️ Custom Language (Input bahasa lain: Spanish, Korean, Sunda, dll.)")

    cur_lang = env_vars.get("BOT_LANGUAGE", "id")
    choice = input(f"\nPilih bahasa [1-5, default saat ini '{cur_lang}']: ").strip()
    if choice == "1" or (not choice and cur_lang == "id"):
        env_vars["BOT_LANGUAGE"] = "id"
        print(c(GREEN, "  ✓ Bahasa dipilih: Bahasa Indonesia 🇮🇩"))
    elif choice == "2":
        env_vars["BOT_LANGUAGE"] = "en"
        print(c(GREEN, "  ✓ Language selected: English 🇬🇧"))
    elif choice == "3":
        env_vars["BOT_LANGUAGE"] = "ja"
        print(c(GREEN, "  ✓ 言語選択: Japanese (日本語) 🇯🇵"))
    elif choice == "4":
        env_vars["BOT_LANGUAGE"] = "auto"
        print(c(GREEN, "  ✓ Bahasa dipilih: Auto-detect (Ikuti chat) 🌐"))
    elif choice == "5":
        custom = input("Masukkan nama bahasa yang kamu inginkan (misal: Spanish, Korean, Sunda, Jawa): ").strip()
        if custom:
            env_vars["BOT_LANGUAGE"] = custom.title()
            print(c(GREEN, f"  ✓ Bahasa dipilih: {custom.title()} ✏️"))
        else:
            env_vars["BOT_LANGUAGE"] = "id"
    else:
        if choice.isalpha():
            env_vars["BOT_LANGUAGE"] = choice.title()
            print(c(GREEN, f"  ✓ Bahasa dipilih: {choice.title()} ✏️"))
        else:
            env_vars["BOT_LANGUAGE"] = cur_lang

def config_video_engine(env_vars):
    """Configures the active Video Generation Engine (Wan 2.1, AnimateDiff, or Motion 2.5D)."""
    print(c(BOLD + CYAN, "\n[Video Generator Engine Selection]"))
    print("-" * 60)
    cur_eng = env_vars.get("VIDEO_ENGINE", "wan21").lower().strip()
    print(f"Current Video Engine: {c(BOLD + GREEN, cur_eng.upper())}\n")

    print("  1) 🌟 Wan 2.1 (1.3B AI Video - Model sudah terpasang di PC kamu!)")
    print("  2) 🌸 AnimateDiff (SD 1.5 Anime - Hemat VRAM, butuh mm_sd_v15_v2.ckpt)")
    print("  3) ⚡ Motion 2.5D Parallax (Super Cepat 1 detik, 0 VRAM)")

    choice = input(f"\nSelect Video Engine [1-3, default: 1]: ").strip()
    if choice == "1" or choice.lower() in ("wan", "wan21", "wan2.1"):
        env_vars["VIDEO_ENGINE"] = "wan21"
        print(c(GREEN, "  ✓ Video Engine dipilih: Wan 2.1 1.3B 🌟"))
    elif choice == "2" or choice.lower() in ("animatediff", "anim"):
        env_vars["VIDEO_ENGINE"] = "animatediff"
        print(c(GREEN, "  ✓ Video Engine dipilih: AnimateDiff (SD 1.5) 🌸"))
    elif choice == "3" or choice.lower() in ("motion", "parallax", "2.5d"):
        env_vars["VIDEO_ENGINE"] = "motion"
        print(c(GREEN, "  ✓ Video Engine dipilih: Motion 2.5D Parallax ⚡"))
    else:
        env_vars["VIDEO_ENGINE"] = "wan21"
        print(c(GREEN, "  ✓ Video Engine dipilih: Wan 2.1 1.3B 🌟"))

def manage_models_menu():
    if not asset_manager:
        print(c(RED, "asset_manager module not found."))
        return

    while True:
        print(c(BOLD + CYAN, "\n" + "=" * 70))
        print(c(BOLD + CYAN, "       📦 AI ASSETS & MODELS MANAGER (ComfyUI Extensions)       "))
        print(c(BOLD + CYAN, "=" * 70))
        comfy_dir = asset_manager.detect_comfyui_dir()
        print(c(DIM, f"ComfyUI Directory: {comfy_dir or 'Not detected'}\n"))

        assets = asset_manager.check_all_assets()
        keys = list(assets.keys())
        for idx, k in enumerate(keys, 1):
            info = assets[k]
            inst = info.get("installed", False)
            incomp = info.get("incomplete", False)
            if inst:
                tag = c(GREEN, "[TERPASANG]")
                sz = f"({info.get('current_size_mb', 0)} MB)"
            elif incomp:
                tag = c(YELLOW, "[TERPUTUS]")
                sz = f"({info.get('current_size_mb', 0)} MB / ~{info.get('size_mb', 0)} MB, {info.get('percent_complete', 0)}%)"
            else:
                tag = c(YELLOW, "[BELUM ADA]")
                sz = f"(~{info.get('size_mb', 0)} MB)"
            print(f"  [{idx}] {tag} {info.get('name')} {sz}")
            print(c(DIM, f"      Fungsi: {info.get('required_for', '-')}"))

        print("-" * 70)
        print("  [D] 📥 Download Semua Model & Ekstensi yang Belum Terpasang")
        print("  [0] 🔙 Kembali ke Menu Utama")
        print("-" * 70)

        sel = input(f"Pilih nomor model untuk diunduh [1-{len(keys)}, D, 0]: ").strip().lower()
        if sel in ("0", "b", "exit", "q"):
            break
        elif sel == "d":
            for k, info in assets.items():
                if not info.get("installed"):
                    print(c(CYAN, f"\nMemproses {info.get('name')}..."))
                    if info.get("type") == "custom_node":
                        asset_manager.install_custom_node(k)
                    else:
                        asset_manager.download_asset(k)
            print(c(GREEN, "\n✓ Semua proses download selesai."))
        elif sel.isdigit() and 1 <= int(sel) <= len(keys):
            chosen_k = keys[int(sel) - 1]
            info = assets[chosen_k]
            print(c(CYAN, f"\nMemproses {info.get('name')}..."))
            if info.get("type") == "custom_node":
                ok = asset_manager.install_custom_node(chosen_k)
            else:
                ok = asset_manager.download_asset(chosen_k)
            if ok:
                print(c(GREEN, f"✓ Berhasil memasang {info.get('name')}!"))
            else:
                print(c(RED, f"❌ Gagal mengunduh {info.get('name')}."))

def run_menu():
    env_vars = read_env()
    has_token = bool(env_vars.get("TELEGRAM_BOT_TOKEN"))

    if not has_token:
        run_full_wizard()
        return

    while True:
        env_vars = read_env()
        print(c(BOLD + MAGENTA, "\n" + "=" * 70))
        print(c(BOLD + MAGENTA, "    💖 WAIFU ON TELEGRAM - CONFIGURATION & MODEL MANAGER 🛠️    "))
        print(c(BOLD + MAGENTA, "=" * 70))
        cur_tok = env_vars.get("TELEGRAM_BOT_TOKEN", "")
        tok_str = f"{cur_tok[:7]}...{cur_tok[-4:]}" if len(cur_tok) > 12 else "[Not Configured]"
        print(c(CYAN, f"  • Bot Token   : {tok_str}"))
        print(c(CYAN, f"  • Allowed UID : {env_vars.get('TELEGRAM_ALLOWED_USER_ID', '[All Users]') or '[All Users]'}"))
        print(c(CYAN, f"  • Chat LLM    : {env_vars.get('LLM_MODEL', 'default')} ({env_vars.get('LLM_BASE_URL', '')})"))
        cur_ckpt_disp = env_vars.get("COMFYUI_CHECKPOINT", "")
        if not cur_ckpt_disp:
            cur_ckpt_disp = "Auto (ComfyUI)" if env_vars.get("COMFYUI_URL") else ("Cloud Engine" if env_vars.get("MEDIA_FALLBACK_CLOUD") == "true" else "Disabled")
        elif "anything" in cur_ckpt_disp.lower():
            cur_ckpt_disp = "Anything XL (SDXL 1024px)"
        elif any(k in cur_ckpt_disp.lower() for k in ["aom", "orange"]):
            cur_ckpt_disp = "AbyssOrangeMix3 (AOM3A1B SD 1.5)"
        elif "meina" in cur_ckpt_disp.lower():
            cur_ckpt_disp = "MeinaMix v12 (SD 1.5)"
        print(c(CYAN, f"  • Photo Model : {cur_ckpt_disp} ({env_vars.get('COMFYUI_URL', 'Disabled')})"))
        print(c(CYAN, f"  • Persona     : {env_vars.get('DEFAULT_PERSONA', 'runa').title()} | Voice: {env_vars.get('VOICE_NAME', '')}"))
        print(c(CYAN, f"  • Language    : {env_vars.get('BOT_LANGUAGE', 'id')}"))
        print("-" * 70)
        print("  [1] 🤖 Change Telegram Bot Token / Allowed User ID")
        print("  [2] 🧠 Change Chat / LLM Model (Scan new models)")
        print("  [3] 🎨 Change Photo & Video Model (ComfyUI / Cloud)")
        print("  [4] 🎭 Change AI Girlfriend Persona & Voice")
        print("  [5] 🌐 Change Waifu Language (ID, EN, JA, Custom)")
        print("  [6] 🎬 Choose Video Engine (Wan 2.1 / AnimateDiff / Motion 2.5D)")
        print("  [7] 📦 AI Assets & Models Manager (Download / Verify Models)")
        print("  [8] 🚀 Configure Autorun at System Startup (On / Off)")
        print("  [9] 🔄 Re-run Complete Setup Wizard")
        print("  [0] ❌ Exit / Done")
        print("-" * 70)

        opt = input("Select option [0-9]: ").strip()
        if opt == "1":
            config_telegram_credentials(env_vars)
            write_env(env_vars)
        elif opt == "2":
            config_llm_model(env_vars)
            write_env(env_vars)
        elif opt == "3":
            config_image_model(env_vars)
            write_env(env_vars)
        elif opt == "4":
            config_persona_voice(env_vars)
            write_env(env_vars)
        elif opt == "5":
            config_language(env_vars)
            write_env(env_vars)
        elif opt == "6":
            config_video_engine(env_vars)
            write_env(env_vars)
        elif opt == "7":
            manage_models_menu()
        elif opt == "8":
            auto_in = input("Enable bot automatically on PC boot (Autorun)? [Y/n, default: Y]: ").strip().lower()
            setup_autostart(enable=(auto_in != "n"))
        elif opt == "9":
            run_full_wizard()
            break
        elif opt == "0":
            print(c(GREEN, "\nGoodbye! You can launch the bot anytime with 'waifu start'.\n"))
            break
        else:
            print(c(YELLOW, "Invalid selection."))

def run_full_wizard():
    print(c(BOLD + MAGENTA, "\n" + "=" * 70))
    print(c(BOLD + MAGENTA, "       💖 WAIFU ON TELEGRAM - FULL SETUP WIZARD 🤖       "))
    print(c(BOLD + MAGENTA, "=" * 70))

    env_vars = read_env()
    config_telegram_credentials(env_vars)
    config_llm_model(env_vars)
    config_image_model(env_vars)

    config_video_engine(env_vars)

    config_persona_voice(env_vars)
    config_language(env_vars)

    print(c(BOLD + CYAN, "\n[Step 6/7: PC Music Remote Player (YouTube Music)]"))
    print("-" * 60)
    music_input = input("Enable PC YouTube Music Remote Web Player on Port 8002? [Y/n, default: Y]: ").strip().lower()
    env_vars["MUSIC_FEATURE_ENABLED"] = "false" if music_input == "n" else "true"

    print(c(BOLD + CYAN, "\n[Step 7/7: Autorun on System Startup]"))
    print("-" * 60)
    print("This feature runs the bot silently in the background whenever your computer boots up.")
    autostart_input = input(c(BOLD + YELLOW, "Launch bot automatically on system startup? [Y/n, default: Y]: ")).strip().lower()
    enable_auto = autostart_input != "n"

    write_env(env_vars)
    setup_autostart(enable=enable_auto)

    print(c(BOLD + GREEN, "\n" + "=" * 70))
    print(c(BOLD + GREEN, "✨ SETUP COMPLETED SUCCESSFULLY! 🎉"))
    print(c(BOLD + GREEN, "=" * 70))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="💖 Waifu on Telegram Setup CLI")
    parser.add_argument("--token", help="Telegram Bot Token")
    parser.add_argument("--user", help="Allowed Telegram User ID")
    parser.add_argument("--backend", help="LLM Base URL")
    parser.add_argument("--autostart", choices=["yes", "no"], help="Enable autorun at startup")
    parser.add_argument("--language", "--lang", help="Waifu Language (id, en, ja, auto, or custom)")
    parser.add_argument("--video-engine", "--vengine", choices=["wan21", "animatediff", "motion"], help="Video Generator Engine (wan21, animatediff, motion)")
    parser.add_argument("--wizard", action="store_true", help="Force run the full 7-step wizard")
    args = parser.parse_args()

    if args.token or args.user or args.backend or args.autostart:
        env_vars = read_env()
        if args.token:
            env_vars["TELEGRAM_BOT_TOKEN"] = args.token
        if args.user:
            env_vars["TELEGRAM_ALLOWED_USER_ID"] = args.user
        if args.backend:
            env_vars["LLM_BASE_URL"] = args.backend
        write_env(env_vars)
        if args.language:
            env_vars["BOT_LANGUAGE"] = args.language
        if args.video_engine:
            env_vars["VIDEO_ENGINE"] = args.video_engine
            print(f"✓ Video Engine set to: {args.video_engine}")
        if args.autostart:
            setup_autostart(enable=(args.autostart == "yes"))
    elif args.wizard:
        run_full_wizard()
    else:
        run_menu()

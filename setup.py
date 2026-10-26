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

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
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
    """Scans Locally Uncensored and local model directories."""
    models = []
    # 1. Locally Uncensored AppData models folder
    lu_dir = os.path.expandvars(r"%APPDATA%\Locally Uncensored\models")
    if os.path.exists(lu_dir):
        for f in os.listdir(lu_dir):
            if f.endswith(".gguf") and not f.endswith(".mmproj.gguf"):
                models.append(("Locally Uncensored", f, os.path.join(lu_dir, f)))

    # 2. Query running Ollama tags if active
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
    """Scans ComfyUI checkpoints and model folders."""
    ckpts = []
    search_dirs = [
        os.path.expandvars(r"%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models\checkpoints"),
        os.path.expandvars(r"%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\models\checkpoints"),
        os.path.expandvars(r"%USERPROFILE%\OneDrive\Documents\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\checkpoints"),
    ]
    for d in search_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".safetensors") or f.endswith(".ckpt"):
                    if f not in [x[1] for x in ckpts]:
                        ckpts.append(("ComfyUI Checkpoint", f))
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
    cur_base = env_vars.get("LLM_BASE_URL", "http://127.0.0.1:8127/v1")
    cur_model = env_vars.get("LLM_MODEL", "default")
    print(f"Active Settings: `{cur_model}` at `{cur_base}`\n")

    detected_llms = scan_local_llm_models()
    options = []
    options.append(("Locally Uncensored (Auto-detect Active Model & Dynamic Key)", "http://127.0.0.1:8127/v1", "auto", "default"))

    for source, mname, mpath in detected_llms:
        if source == "Locally Uncensored":
            options.append((f"{mname} ({source})", "http://127.0.0.1:8127/v1", "auto", mname))
        elif source == "Ollama":
            options.append((f"{mname} (Ollama)", "http://127.0.0.1:11434/v1", "ollama", mname))

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
    detected_img = scan_image_models()

    img_options = []
    for source, ckpt_name in detected_img:
        img_options.append((f"{ckpt_name} (Local GPU via ComfyUI)", ckpt_name, True))

    img_options.append(("Cloud Fallback Engine (Pollinations AI - Fast, Free GPU, 0 VRAM)", "cloud", True))
    img_options.append(("Disable photo generation", "disabled", False))

    for idx, opt in enumerate(img_options, 1):
        print(f"  {idx}) {opt[0]}")

    choice_img = input(f"\nSelect Photo Model [1-{len(img_options)}, default: 1]: ").strip()
    chosen_img_idx = int(choice_img) - 1 if choice_img.isdigit() and 1 <= int(choice_img) <= len(img_options) else 0

    _, img_val, allow_fallback = img_options[chosen_img_idx]
    if img_val == "disabled":
        env_vars["COMFYUI_URL"] = ""
        env_vars["MEDIA_FALLBACK_CLOUD"] = "false"
    else:
        env_vars["COMFYUI_URL"] = "http://127.0.0.1:8188"
        env_vars["MEDIA_FALLBACK_CLOUD"] = "true" if allow_fallback else "false"

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
        print(c(CYAN, f"  • Photo Engine: {env_vars.get('COMFYUI_URL', 'Disabled')} (Fallback: {env_vars.get('MEDIA_FALLBACK_CLOUD')})"))
        print(c(CYAN, f"  • Persona     : {env_vars.get('DEFAULT_PERSONA', 'runa').title()} | Voice: {env_vars.get('VOICE_NAME', '')}"))
        print(c(CYAN, f"  • Language    : {env_vars.get('BOT_LANGUAGE', 'id')}"))
        print("-" * 70)
        print("  [1] 🤖 Change Telegram Bot Token / Allowed User ID")
        print("  [2] 🧠 Change Chat / LLM Model (Scan new models)")
        print("  [3] 🎨 Change Photo & Video Model (ComfyUI / Cloud)")
        print("  [4] 🎭 Change AI Girlfriend Persona & Voice")
        print("  [5] 🌐 Change Waifu Language (ID, EN, JA, Custom)")
        print("  [6] 🚀 Configure Autorun at System Startup (On / Off)")
        print("  [7] 🔄 Re-run Complete Setup Wizard")
        print("  [0] ❌ Exit / Done")
        print("-" * 70)

        opt = input("Select option [0-6]: ").strip()
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
            auto_in = input("Enable bot automatically on PC boot (Autorun)? [Y/n, default: Y]: ").strip().lower()
            setup_autostart(enable=(auto_in != "n"))
        elif opt == "7":
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

    print(c(BOLD + CYAN, "\n[Step 4/7: Video Generator Model Selection (Wan 2.2 / ComfyUI)]"))
    print("-" * 60)
    detected_vids = scan_video_models()
    vid_options = []
    for source, vname in detected_vids:
        vid_options.append((f"{vname} (Local via ComfyUI)", vname))
    vid_options.append(("Auto-detect / Cloud Fallback", "auto"))

    for idx, opt in enumerate(vid_options, 1):
        print(f"  {idx}) {opt[0]}")

    choice_vid = input(f"\nSelect Video Model [1-{len(vid_options)}, default: 1]: ").strip()
    chosen_vid_idx = int(choice_vid) - 1 if choice_vid.isdigit() and 1 <= int(choice_vid) <= len(vid_options) else 0

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
        if args.autostart:
            setup_autostart(enable=(args.autostart == "yes"))
    elif args.wizard:
        run_full_wizard()
    else:
        run_menu()

#!/usr/bin/env python3
"""
💖 WAIFU ON TELEGRAM - AUTONOMOUS AI ROMANCE COMPANION CLI 🌸
Repository: https://github.com/asepindrak/waifu-on-telegram
Usage:
  waifu start [--daemon]
  waifu stop
  waifu restart
  waifu status
  waifu setup
  waifu persona [runa|akira|hina|shiro|yume]
  waifu autorun [on|off]
  waifu logs
"""

import os
import sys
import time
import subprocess
import argparse
import platform
import json
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass



# Terminal Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def c(color, text):
    return f"{color}{text}{RESET}"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PID_FILE = os.path.join(PROJECT_ROOT, "bot.pid")
LOG_FILE = os.path.join(PROJECT_ROOT, "bot.log")

try:
    import asset_manager
except ImportError:
    asset_manager = None

def get_version() -> str:
    v_file = os.path.join(PROJECT_ROOT, "VERSION")
    if os.path.exists(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "1.1.0"

def print_banner():
    v = get_version()
    banner = f"""
{c(BOLD + MAGENTA, "  ██╗    ██╗ █████╗ ██╗███████╗██╗   ██╗    ██████╗  ██████╗ ████████╗")}
{c(BOLD + MAGENTA, "  ██║    ██║██╔══██╗██║██╔════╝██║   ██║    ██╔══██╗██╔═══██╗╚══██╔══╝")}
{c(BOLD + MAGENTA, "  ██║ █╗ ██║███████║██║█████╗  ██║   ██║    ██████╔╝██║   ██║   ██║   ")}
{c(BOLD + MAGENTA, "  ██║███╗██║██╔══██║██║██╔══╝  ██║   ██║    ██╔══██╗██║   ██║   ██║   ")}
{c(BOLD + MAGENTA, "  ╚███╔███╔╝██║  ██║██║██║     ╚██████╔╝    ██████╔╝╚██████╔╝   ██║   ")}
{c(BOLD + MAGENTA, "   ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝╚═╝      ╚═════╝     ╚═════╝  ╚═════╝    ╚═╝   ")}
  {c(CYAN, f"💖 WAIFU ON TELEGRAM v{v} - Autonomous AI Romance Companion 🌸")}
  {c(DIM, "Project Root: " + PROJECT_ROOT + " | Repo: asepindrak/waifu-on-telegram")}
"""
    print(banner)

def get_running_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if platform.system() == "Windows":
                res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
                if str(pid) in res.stdout:
                    return pid
            else:
                os.kill(pid, 0)
                return pid
        except Exception:
            pass
    return None

def cmd_start(daemon: bool = False):
    print_banner()
    existing_pid = get_running_pid()
    if existing_pid:
        print(c(YELLOW, f"⚠️ Bot is already running with PID {existing_pid}."))
        return

    env_path = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_path):
        print(c(YELLOW, "⚠️ File .env not configured yet. Launching setup wizard..."))
        subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, "setup.py")])

    print(c(CYAN, "🚀 Launching Waifu on Telegram..."))

    # Auto start background auxiliary servers (KoboldCPP, ComfyUI, Music)
    start_auxiliary_services()

    bot_script = os.path.join(PROJECT_ROOT, "bot.py")

    if daemon:
        if platform.system() == "Windows":
            vbs_script = os.path.join(PROJECT_ROOT, "start_services_silent.vbs")
            if os.path.exists(vbs_script):
                subprocess.Popen(["wscript.exe", vbs_script], cwd=PROJECT_ROOT)
                print(c(GREEN, "✓ Waifu is running silently in the background (Daemon Mode)!"))
                print(c(DIM, "  Use 'waifu status' to inspect or 'waifu stop' to terminate."))
                return
        else:
            sh_script = os.path.join(PROJECT_ROOT, "start_services.sh")
            if os.path.exists(sh_script):
                subprocess.run(["bash", sh_script])
                print(c(GREEN, "✓ Waifu is running in background (Daemon Mode via start_services.sh)!"))
                print(c(DIM, "  Use 'waifu status' to inspect or 'waifu stop' to terminate."))
                return

        with open(LOG_FILE, "a", encoding="utf-8") as log_out:
            p = subprocess.Popen(
                [sys.executable, bot_script],
                cwd=PROJECT_ROOT,
                stdout=log_out,
                stderr=log_out,
                start_new_session=True
            )
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
            print(c(GREEN, f"✓ Waifu is running in background (PID {p.pid})!"))
            print(c(DIM, f"  Log file: {LOG_FILE}"))
    else:
        print(c(GREEN, "✓ Waifu running in foreground terminal. Press Ctrl+C to stop."))
        try:
            subprocess.run([sys.executable, bot_script], cwd=PROJECT_ROOT)
        except KeyboardInterrupt:
            print(c(YELLOW, "\nBot stopped by user."))

def is_port_listening(port: int) -> bool:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except Exception:
        return False

def start_auxiliary_services():
    """Starts KoboldCPP, ComfyUI, and Music Remote if installed and not yet running."""
    popen_kwargs = {}
    if platform.system() == "Windows":
        popen_kwargs = {"creationflags": 0x08000000 | 0x00000200}
    else:
        popen_kwargs = {"start_new_session": True}

    # 1. KoboldCPP (Port 5001)
    if not is_port_listening(5001):
        kcpp_exe = os.path.join(PROJECT_ROOT, "tools", "koboldcpp.exe" if platform.system() == "Windows" else "koboldcpp")
        if os.path.isfile(kcpp_exe):
            models_dir = os.path.join(PROJECT_ROOT, "models")
            model_path = None
            mmproj_path = None
            if os.path.isdir(models_dir):
                for f in os.listdir(models_dir):
                    if f.endswith(".gguf") and "mmproj" not in f.lower():
                        model_path = os.path.join(models_dir, f)
                        break
                for f in os.listdir(models_dir):
                    if f.endswith(".gguf") and "mmproj" in f.lower():
                        mmproj_path = os.path.join(models_dir, f)
                        break
            if model_path:
                mm_args = ["--mmproj", mmproj_path] if mmproj_path else []
                cmd = [
                    kcpp_exe, "--model", model_path,
                    "--port", "5001",
                    "--gpulayers", "99",
                    "--contextsize", "4096",
                    "--smartcontext",
                    "--threads", "4"
                ] + mm_args
                if platform.system() == "Windows":
                    cmd += ["--usecublas", "normal", "--quiet"]
                else:
                    cmd += ["--quiet"]
                try:
                    subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)
                    print(c(GREEN, "  ✓ KoboldCPP LLM Server active on port 5001"))
                except Exception:
                    pass

    # 2. ComfyUI (Port 8188)
    comfyui_on_demand = os.environ.get("COMFYUI_ON_DEMAND", "true").lower() in ("true", "1", "yes")
    media_cloud = os.environ.get("MEDIA_FALLBACK_CLOUD", "false").lower() in ("true", "1", "yes")
    if comfyui_on_demand and not media_cloud:
        print(c(CYAN, "  💤 ComfyUI on standby (On-Demand Mode: otomatis aktif saat ada request foto/video)"))
    elif not is_port_listening(8188) and asset_manager and not media_cloud:
        spec = asset_manager.get_comfyui_launch_spec()
        if spec:
            try:
                comfy_log = os.path.join(PROJECT_ROOT, "comfyui.log")
                f_comfy = open(comfy_log, "a", encoding="utf-8")
                subprocess.Popen(spec["cmd"], cwd=spec["cwd"], stdout=f_comfy, stderr=f_comfy, **popen_kwargs)
                print(c(GREEN, "  ✓ ComfyUI Photo Generator active on port 8188"))
            except Exception:
                pass

    # 3. YouTube Music Server (Port 8002)
    if not is_port_listening(8002):
        music_js = os.path.join(PROJECT_ROOT, "music_player_server.js")
        if os.path.exists(music_js):
            node_bin = "node"
            local_node = os.path.join(PROJECT_ROOT, "tools", "nodejs", "node.exe" if platform.system() == "Windows" else "bin/node")
            if not shutil.which("node") and os.path.isfile(local_node):
                node_bin = local_node
            if shutil.which(node_bin) or os.path.isfile(node_bin):
                try:
                    subprocess.Popen([node_bin, music_js], cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)
                    print(c(GREEN, "  ✓ YouTube Music Server active on port 8002"))
                except Exception:
                    pass

def cmd_stop():
    print_banner()
    print(c(YELLOW, "🛑 Terminating Waifu on Telegram services..."))

    if platform.system() == "Windows":
        ps_cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*bot.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq Waifu Music Server*"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq KoboldCPP*"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "koboldcpp.exe"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq ComfyUI*"], capture_output=True)
        ps_comfy = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.py*" -and $_.CommandLine -like "*8188*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_comfy], capture_output=True)
    else:
        stop_sh = os.path.join(PROJECT_ROOT, "stop_services.sh")
        if os.path.exists(stop_sh):
            subprocess.run(["bash", stop_sh], capture_output=True)
        else:
            pid = get_running_pid()
            if pid:
                try:
                    os.kill(pid, 15)
                except Exception:
                    pass
            subprocess.run(["pkill", "-f", "python.*bot.py"], capture_output=True)
            subprocess.run(["pkill", "-f", "node.*music_player_server.js"], capture_output=True)
            subprocess.run(["pkill", "-f", "koboldcpp"], capture_output=True)
            subprocess.run(["pkill", "-f", "main.py.*8188"], capture_output=True)

    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

    print(c(GREEN, "✓ All bot services have been stopped."))

def cmd_restart(daemon: bool = True):
    cmd_stop()
    time.sleep(1.5)
    cmd_start(daemon=daemon)

def cmd_status():
    print_banner()
    status_ps1 = os.path.join(PROJECT_ROOT, "status_services.ps1")
    if platform.system() == "Windows" and os.path.exists(status_ps1):
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", status_ps1])
    else:
        import urllib.request
        print(c(BOLD + CYAN, f"System Status Diagnostics (v{get_version()}):"))
        smart_idle = os.environ.get("SMART_IDLE_ENABLED", "true").lower() in ("true", "1", "yes")
        on_demand = os.environ.get("COMFYUI_ON_DEMAND", "true").lower() in ("true", "1", "yes")
        for name, url, is_idle in [("Local LLM (KoboldCPP 5001)", "http://127.0.0.1:5001/v1/models", smart_idle), ("ComfyUI (8188)", "http://127.0.0.1:8188/system_stats", on_demand)]:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    print(f"  ✓ {name}: " + c(GREEN, "ONLINE"))
            except Exception:
                if is_idle:
                    print(f"  💤 {name}: " + c(CYAN, "STANDBY / TIDUR (Smart Idle)"))
                else:
                    print(f"  🔴 {name}: " + c(RED, "OFFLINE"))

def cmd_setup():
    setup_py = os.path.join(PROJECT_ROOT, "setup.py")
    subprocess.run([sys.executable, setup_py])

def cmd_autorun(action: str):
    enable = (action.lower() in ("on", "enable", "yes", "true"))
    script = "enable_autostart.ps1" if enable else "disable_autostart.ps1"
    target = os.path.join(PROJECT_ROOT, script)
    if platform.system() == "Windows" and os.path.exists(target):
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", target])
    else:
        print(c(YELLOW, f"Autorun set to: {'ENABLED' if enable else 'DISABLED'}"))

def cmd_language(lang_arg: str = None):
    print_banner()
    env_file = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_file):
        print(c(RED, "File .env not found. Please run 'waifu setup' first."))
        return

    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()

    target_lang = None
    display = ""
    if lang_arg:
        low = lang_arg.strip().lower()
        if low in ("id", "indonesia", "indonesian", "bahasa"):
            target_lang = "id"
            display = "Bahasa Indonesia 🇮🇩"
        elif low in ("en", "english"):
            target_lang = "en"
            display = "English 🇬🇧"
        elif low in ("ja", "jp", "japan", "japanese", "nihongo"):
            target_lang = "ja"
            display = "Japanese (日本語) 🇯🇵"
        elif low in ("auto", "adaptive"):
            target_lang = "auto"
            display = "Auto-detect (Ikuti Bahasa Chat) 🌐"
        else:
            target_lang = lang_arg.strip().title()
            display = f"{target_lang} ✏️"
    else:
        print(c(BOLD + CYAN, "🌐 WAIFU LANGUAGE CONFIGURATION"))
        print("-" * 55)
        print("Pilih bahasa utama yang digunakan oleh Waifu:")
        print("  1) 🇮🇩 Bahasa Indonesia (id)")
        print("  2) 🇬🇧 English (en)")
        print("  3) 🇯🇵 Japanese / 日本語 (ja)")
        print("  4) 🌐 Auto-detect / Ikuti chat (auto)")
        print("  5) ✏️ Custom Language (input bahasa lain)")
        choice = input(c(BOLD + YELLOW, "\nPilih bahasa [1-5]: ")).strip()
        if choice == "1":
            target_lang = "id"
            display = "Bahasa Indonesia 🇮🇩"
        elif choice == "2":
            target_lang = "en"
            display = "English 🇬🇧"
        elif choice == "3":
            target_lang = "ja"
            display = "Japanese (日本語) 🇯🇵"
        elif choice == "4":
            target_lang = "auto"
            display = "Auto-detect (Ikuti Bahasa Chat) 🌐"
        elif choice == "5":
            c_input = input("Masukkan nama bahasa (misal: Spanish, Korean, Sunda, Jawa): ").strip()
            if c_input:
                target_lang = c_input.title()
                display = f"{target_lang} ✏️"
            else:
                target_lang = "id"
                display = "Bahasa Indonesia 🇮🇩"
        else:
            if choice.isalpha():
                target_lang = choice.title()
                display = f"{target_lang} ✏️"
            else:
                target_lang = "id"
                display = "Bahasa Indonesia 🇮🇩"

    import re
    if re.search(r"^BOT_LANGUAGE=.*", content, re.M):
        new_content = re.sub(r"^BOT_LANGUAGE=.*", f"BOT_LANGUAGE={target_lang}", content, flags=re.M)
    else:
        new_content = content + f"\nBOT_LANGUAGE={target_lang}\n"

    with open(env_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(c(BOLD + GREEN, f"\n✓ Waifu Language successfully set to: {display}"))
    is_running = get_running_pid() is not None
    if is_running:
        print(c(CYAN, "Restarting bot to apply changes..."))
        cmd_restart(daemon=True)
    else:
        print(c(DIM, "Run 'waifu start' to begin chatting in your chosen language!\n"))

def cmd_persona(name: str):
    env_file = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_file):
        print(c(RED, "File .env not found."))
        return
    name = name.lower()
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
    import re
    if re.search(r"^DEFAULT_PERSONA=.*", content, re.M):
        new_content = re.sub(r"^DEFAULT_PERSONA=.*", f"DEFAULT_PERSONA={name}", content, flags=re.M)
    else:
        new_content = content + f"\nDEFAULT_PERSONA={name}\n"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(c(GREEN, f"✓ Active character switched to: {name.title()}"))
    print(c(CYAN, "  Run 'waifu restart' to apply changes."))

def cmd_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for l in lines[-40:]:
                print(l, end="")
    else:
        print(c(YELLOW, "No log file found yet."))

def cmd_uninstall():
    print_banner()
    if platform.system() == "Windows":
        ps1_script = os.path.join(PROJECT_ROOT, "uninstall.ps1")
        if os.path.exists(ps1_script):
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1_script])
        else:
            print(c(RED, "uninstall.ps1 script not found."))
    else:
        sh_script = os.path.join(PROJECT_ROOT, "uninstall.sh")
        if os.path.exists(sh_script):
            subprocess.run(["bash", sh_script])
        else:
            print(c(RED, "uninstall.sh script not found."))

def cmd_release(version_arg: str = None):
    print_banner()
    if not version_arg:
        cur = get_version()
        print(c(YELLOW, f"Current version: v{cur}"))
        version_arg = input(c(BOLD + CYAN, "Enter new release version (e.g. 1.1.0): ")).strip()
        if not version_arg:
            print(c(RED, "Aborted: Version cannot be empty."))
            return
    rel_script = os.path.join(PROJECT_ROOT, "scripts", "release.py")
    if os.path.exists(rel_script):
        subprocess.run([sys.executable, rel_script, version_arg], cwd=PROJECT_ROOT)
    else:
        print(c(RED, "scripts/release.py not found."))

def cmd_models(subcmd=None, target=None):
    print_banner()
    if not asset_manager:
        print(c(RED, "asset_manager module not found."))
        return

    comfy_dir = asset_manager.detect_comfyui_dir()
    print(c(BOLD + CYAN, "📦 WAIFU ON TELEGRAM - AI ASSETS & MODELS MANAGER"))
    print(c(DIM, f"ComfyUI Directory: {comfy_dir or 'Not Detected (Please start ComfyUI)'}\n"))

    if subcmd in ("download", "dl", "get"):
        if not target:
            print(c(YELLOW, "Please specify which model to download."))
            print("Available keys: " + ", ".join(asset_manager.ASSET_REGISTRY.keys()))
            return
        target = target.lower().strip()
        info = asset_manager.get_asset_info(target)
        if not info:
            print(c(RED, f"Unknown asset key: '{target}'. Available: {list(asset_manager.ASSET_REGISTRY.keys())}"))
            return
        if info.get("type") == "custom_node":
            print(c(CYAN, f"Cloning custom node: {info.get('name')}..."))
            ok = asset_manager.install_custom_node(target)
            if ok:
                print(c(GREEN, f"✓ Custom node '{info.get('name')}' successfully installed!"))
            else:
                print(c(RED, f"❌ Failed to install custom node '{info.get('name')}'. Check Git installation."))
        else:
            if info.get("installed", False):
                print(c(GREEN, f"  ✓ Model '{info.get('name')}' is already complete and verified ({info.get('current_size_mb')} MB)."))
                return
            if info.get("incomplete", False):
                print(c(CYAN, f"⏳ Resuming download for model: {info.get('name')} ({info.get('current_size_mb')} MB / ~{info.get('size_mb')} MB, {info.get('percent_complete')}%)..."))
            else:
                print(c(CYAN, f"⏳ Downloading model: {info.get('name')} (~{info.get('size_mb')} MB)..."))
            print(c(DIM, f"Target: {info.get('target_path')}"))
            ok = asset_manager.download_asset(target)
            if ok:
                print(c(GREEN, f"✓ Model '{info.get('name')}' downloaded and verified successfully!"))
            else:
                print(c(RED, f"❌ Download failed for '{info.get('name')}'. Please check your internet connection."))
        return

    # List all assets
    assets = asset_manager.check_all_assets()
    for key, info in assets.items():
        installed = info.get("installed", False)
        incomplete = info.get("incomplete", False)
        if installed:
            status_tag = c(GREEN, "[INSTALLED] ")
            size_str = f"({info.get('current_size_mb', 0)} MB)"
        elif incomplete:
            status_tag = c(YELLOW, "[INCOMPLETE]")
            size_str = f"({info.get('current_size_mb', 0)} MB / ~{info.get('size_mb', 0)} MB, {info.get('percent_complete', 0)}% downloaded)"
        else:
            status_tag = c(YELLOW, "[MISSING]   ")
            size_str = f"(~{info.get('size_mb', 0)} MB required)"
        print(f"  {status_tag} {c(BOLD, key)}: {info.get('name')} {size_str}")
        print(c(DIM, f"             Target: {info.get('target_path') or info.get('target_dir')}"))
        print(c(DIM, f"             Used for: {info.get('required_for', '-')}\n"))

    print(c(CYAN, "Commands:"))
    print(c(DIM, "  waifu models download <key>  - Download specific model/extension"))
    print(c(DIM, "  Example: waifu models download animatediff_v2\n"))

def cmd_update():
    print_banner()
    cur_v = get_version()
    print(c(CYAN, f"🔄 Checking updates and verifying AI models (Current Version: v{cur_v})..."))
    is_running = get_running_pid() is not None

    # Step 1: Git pull latest changes
    git_dir = os.path.join(PROJECT_ROOT, ".git")
    if os.path.exists(git_dir):
        print(c(CYAN, "\n📥 [1/5] Pulling latest repository updates from GitHub..."))
        try:
            res = subprocess.run(["git", "pull", "--tags"], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if res.returncode == 0:
                print(c(GREEN, "  ✓ Latest source code pulled successfully from GitHub."))
                if res.stdout.strip():
                    print(c(DIM, "    " + res.stdout.strip().replace("\n", "\n    ")))
            else:
                notice = res.stderr.strip() or res.stdout.strip()
                # If git pull is blocked by local changes or untracked conflicts
                if any(x in notice for x in ["overwritten by merge", "stash them before you merge", "Aborting"]):
                    print(c(YELLOW, "  ⚠️ Local code modifications detected. Auto-resolving and synchronizing with official GitHub release..."))
                    subprocess.run(["git", "stash"], cwd=PROJECT_ROOT, capture_output=True)
                    subprocess.run(["git", "fetch", "--tags", "origin", "main"], cwd=PROJECT_ROOT, capture_output=True)
                    res_reset = subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=PROJECT_ROOT, capture_output=True, text=True)
                    if res_reset.returncode == 0:
                        print(c(GREEN, "  ✓ Source code successfully synchronized with official release!"))
                    else:
                        print(c(YELLOW, f"  ℹ Git notice: {notice}"))
                else:
                    print(c(YELLOW, f"  ℹ Git notice: {notice}"))
        except Exception as e:
            print(c(YELLOW, f"  ⚠️ Git pull error: {e}"))
    else:
        print(c(YELLOW, "  Project directory is not a Git clone. Skipping git pull."))

    # Step 2: Auto check and install Python dependencies
    req_txt = os.path.join(PROJECT_ROOT, "requirements.txt")
    if os.path.exists(req_txt):
        print(c(CYAN, "\n📦 [2/5] Checking and updating Python libraries (pip install -r requirements.txt)..."))
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req_txt, "--disable-pip-version-check"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                print(c(GREEN, "  ✓ All Python libraries verified and up to date."))
            else:
                notice = res.stderr.strip() or res.stdout.strip()[-200:]
                print(c(YELLOW, f"  ⚠️ pip notice: {notice}"))
        except Exception as e:
            print(c(RED, f"  ❌ Error updating Python libraries: {e}"))

    # Step 3: Auto check Node.js environment & dependencies for music remote
    print(c(CYAN, "\n🎵 [3/5] Checking Node.js environment & YouTube music remote..."))
    if asset_manager:
        asset_manager.ensure_nodejs()

    pkg_json = os.path.join(PROJECT_ROOT, "package.json")
    if os.path.exists(pkg_json):
        npm_cmd = shutil.which("npm")
        if npm_cmd:
            try:
                res = subprocess.run(
                    [npm_cmd, "install", "--no-audit", "--no-fund", "--silent"],
                    cwd=PROJECT_ROOT,
                    shell=(platform.system() == "Windows"),
                    capture_output=True,
                    text=True
                )
                if res.returncode == 0:
                    print(c(GREEN, "  ✓ Node.js dependencies (ytmusic-api, etc.) verified and up to date."))
                else:
                    print(c(YELLOW, f"  ⚠️ npm notice: {res.stderr.strip()}"))
            except Exception as e:
                print(c(YELLOW, f"  ⚠️ npm error: {e}"))
        else:
            print(c(DIM, "  ℹ Node.js not detected. (Music remote feature will be inactive)."))

    # Step 4: Check Standalone KoboldCPP Engine
    print(c(CYAN, "\n🧠 [4/5] Checking Standalone KoboldCPP LLM Engine..."))
    if asset_manager:
        if asset_manager.ensure_koboldcpp():
            print(c(GREEN, "  ✓ KoboldCPP standalone binary is ready in tools/."))
        else:
            print(c(YELLOW, "  ⚠️ KoboldCPP binary could not be verified. Check internet connection."))

    # Step 5: Check & Auto-Download Core AI Models (Chat Brain, Vision, and Image Generation)
    print(c(CYAN, "\n📦 [5/5] Checking and auto-downloading AI Models & Vision mmproj..."))
    if asset_manager:
        # 1. Main Chat Brain: Huihui-Qwythos-9B
        info_9b = asset_manager.get_asset_info("qwythos_9b")
        if info_9b and not info_9b.get("installed"):
            print(c(YELLOW, f"  ⏳ Core Brain '{info_9b['name']}' missing. Auto-downloading (~{info_9b['size_mb']} MB)..."))
            ok = asset_manager.download_asset("qwythos_9b")
            if ok:
                print(c(GREEN, f"  ✓ '{info_9b['name']}' downloaded successfully!"))
            else:
                print(c(RED, f"  ❌ Download failed for '{info_9b['name']}'. Run 'waifu models download qwythos_9b'."))
        else:
            sz = info_9b.get("current_size_mb", 0) if info_9b else 0
            print(c(GREEN, f"  ✓ Core Chat Brain '{info_9b['name']}' is ready ({sz} MB)."))

        # 2. Vision Adapter: Huihui-Qwythos Vision mmproj
        info_vis = asset_manager.get_asset_info("qwythos_vision")
        if info_vis and not info_vis.get("installed"):
            print(c(YELLOW, f"  ⏳ Vision Adapter '{info_vis['name']}' missing. Auto-downloading (~{info_vis['size_mb']} MB)..."))
            ok = asset_manager.download_asset("qwythos_vision")
            if ok:
                print(c(GREEN, f"  ✓ '{info_vis['name']}' downloaded successfully!"))
            else:
                print(c(RED, f"  ❌ Download failed for '{info_vis['name']}'. Run 'waifu models download qwythos_vision'."))
        else:
            sz = info_vis.get("current_size_mb", 0) if info_vis else 0
            print(c(GREEN, f"  ✓ Vision Adapter '{info_vis['name']}' is ready ({sz} MB)."))

        # 3. ComfyUI Models (if ComfyUI is detected or auto-installed)
        comfy_dir = asset_manager.detect_comfyui_dir()
        if not comfy_dir and platform.system() == "Windows":
            print(c(YELLOW, "  ⏳ ComfyUI not detected locally. Auto-installing official ComfyUI Portable (~1.4 GB)..."))
            if asset_manager.ensure_comfyui():
                comfy_dir = asset_manager.detect_comfyui_dir()
                print(c(GREEN, f"  ✓ ComfyUI Portable ready at: {comfy_dir}"))

        if comfy_dir:
            print(c(CYAN, f"  🧩 ComfyUI detected at: {comfy_dir}"))
            configured_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "").lower()
            target_asset = "anything_xl" if "anything" in configured_ckpt else "meinamix"
            info_target = asset_manager.get_asset_info(target_asset)
            if info_target and not info_target.get("installed"):
                print(c(YELLOW, f"  ⏳ Anime Checkpoint '{info_target['name']}' missing. Auto-downloading (~{info_target['size_mb']} MB)..."))
                ok = asset_manager.download_asset(target_asset)
                if ok:
                    print(c(GREEN, f"  ✓ '{info_target['name']}' downloaded successfully!"))
            else:
                sz = info_target.get("current_size_mb", 0) if info_target else 0
                name = info_target.get("name", target_asset) if info_target else target_asset
                print(c(GREEN, f"  ✓ Anime Checkpoint '{name}' is ready ({sz} MB)."))
        else:
            print(c(DIM, "  ℹ ComfyUI not detected locally. Photo Vault album will be used for photos."))

    # Auto-ensure Windows Startup Autorun is enabled
    if platform.system() == "Windows":
        startup_folder = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        shortcut = os.path.join(startup_folder, "Start_Waifu_on_Telegram.lnk")
        if not os.path.exists(shortcut):
            print(c(CYAN, "\n⚙️ Auto-enabling Windows Startup Autorun (Runs on PC boot)..."))
            cmd_autorun("on")

    new_v = get_version()
    if new_v != cur_v:
        print(c(BOLD + GREEN, f"\n🎉 Successfully updated Waifu on Telegram from v{cur_v} to v{new_v}!"))
    else:
        print(c(BOLD + GREEN, f"\n🎉 Waifu on Telegram is fully up to date (v{new_v})!"))

    if is_running:
        print(c(CYAN, "\n🔄 Restarting bot daemon to apply all changes cleanly..."))
        cmd_restart(daemon=True)
    else:
        print(c(DIM, "\nStart your bot anytime with: waifu start --daemon\n"))

def print_cli_help(unknown_cmd: str = None):
    print_banner()
    if unknown_cmd:
        import difflib
        valid_cmds = [
            "start", "stop", "restart", "status", "setup", "config",
            "update", "models", "persona", "language", "autorun",
            "logs", "version", "uninstall", "help"
        ]
        matches = difflib.get_close_matches(unknown_cmd.lower(), valid_cmds, n=1, cutoff=0.4)
        if matches:
            print(c(BOLD + YELLOW, f"\n⚠️  Perintah '{unknown_cmd}' tidak dikenali. Mungkin maksud kamu: 'waifu {matches[0]}'?\n"))
        else:
            print(c(BOLD + RED, f"\n❌ Perintah '{unknown_cmd}' tidak dikenali.\n"))

    print(c(BOLD + CYAN, "📋 DAFTAR PERINTAH RESMI ('waifu <command>'):"))
    print(c(DIM, "─" * 70))
    print(c(BOLD + MAGENTA, "  🚀 Kontrol Layanan & Status:"))
    print(f"    {c(GREEN, 'waifu start')} [--daemon]       Mulai bot & AI engines (foreground / background)")
    print(f"    {c(GREEN, 'waifu stop')}                  Hentikan bot & semua background services")
    print(f"    {c(GREEN, 'waifu restart')}               Restart bot & daemon secara bersih")
    print(f"    {c(GREEN, 'waifu status')}                Diagnostik kesehatan LLM, ComfyUI, Music & RAM/VRAM")
    print(f"    {c(GREEN, 'waifu logs')}                  Pantau log aktivitas bot secara real-time")

    print(c(BOLD + MAGENTA, "\n  ⚙️ Konfigurasi & Model AI:"))
    print(f"    {c(GREEN, 'waifu setup')}                 Wizard konfigurasi interaktif (Token, Model, Voice)")
    print(f"    {c(GREEN, 'waifu models')} [dl <nama>]    Kelola & download model (MeinaMix, Anything XL, dll.)")
    print(f"    {c(GREEN, 'waifu persona')} <nama>        Ganti waifu (runa, akira, hina, shiro, yume)")
    print(f"    {c(GREEN, 'waifu language')} [id|en|ja]   Ganti bahasa percakapan waifu (ID, EN, JA)")
    print(f"    {c(GREEN, 'waifu autorun')} [on|off]      Atur bot berjalan otomatis saat PC boot")

    print(c(BOLD + MAGENTA, "\n  🔄 Pemeliharaan & Info:"))
    print(f"    {c(GREEN, 'waifu update')}                Update repository, dependensi, dan model AI")
    print(f"    {c(GREEN, 'waifu version')}               Tampilkan versi Waifu on Telegram saat ini")
    print(f"    {c(GREEN, 'waifu uninstall')}             Wizard uninstalasi lengkap & pembersihan sistem")

    print(c(DIM, "─" * 70))
    print(c(DIM, "💡 Contoh penggunaan:"))
    print(c(DIM, "    waifu start --daemon"))
    print(c(DIM, "    waifu models download anything_xl"))
    print(c(DIM, "    waifu persona akira\n"))

def main():
    if any(a in sys.argv[1:] for a in ("-v", "--version", "version")):
        print(c(BOLD + CYAN, f"💖 Waifu on Telegram v{get_version()}"))
        return

    if any(a in sys.argv[1:] for a in ("-h", "--help", "help")):
        print_cli_help()
        return

    if len(sys.argv) > 1 and sys.argv[1] in ("--daemon", "-d"):
        cmd_start(daemon=True)
        return

    parser = argparse.ArgumentParser(description="💖 Waifu on Telegram CLI", add_help=False)
    parser.add_argument("command", nargs="?", default=None)
    parser.add_argument("arg", nargs="?", default=None)
    parser.add_argument("extra_args", nargs="*", default=[])
    parser.add_argument("--daemon", "-d", action="store_true", help="Run bot silently in background")
    args, unknown = parser.parse_known_args()

    cmd = args.command.lower() if args.command else "status"
    if cmd == "start":
        cmd_start(daemon=args.daemon)
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "restart":
        cmd_restart(daemon=True)
    elif cmd == "status":
        cmd_status()
    elif cmd in ("setup", "config"):
        cmd_setup()
    elif cmd == "autorun":
        action = args.arg or "on"
        cmd_autorun(action)
    elif cmd == "persona":
        p_name = args.arg or "runa"
        cmd_persona(p_name)
    elif cmd in ("language", "lang"):
        cmd_language(args.arg)
    elif cmd == "logs":
        cmd_logs()
    elif cmd in ("models", "model", "assets"):
        sub = args.arg
        remaining = args.extra_args[0] if args.extra_args else (sys.argv[3] if len(sys.argv) > 3 else None)
        cmd_models(sub, remaining)
    elif cmd == "update":
        cmd_update()
    elif cmd == "release":
        cmd_release(args.arg)
    elif cmd == "uninstall":
        cmd_uninstall()
    else:
        print_cli_help(unknown_cmd=args.command)

if __name__ == "__main__":
    main()

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

    # Start optional music server in background
    music_js = os.path.join(PROJECT_ROOT, "music_player_server.js")
    if os.path.exists(music_js):
        try:
            subprocess.Popen(["node", music_js], cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(c(GREEN, "  ✓ YouTube Music Server active on port 8002"))
        except Exception:
            pass

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

def cmd_stop():
    print_banner()
    print(c(YELLOW, "🛑 Terminating Waifu on Telegram services..."))

    if platform.system() == "Windows":
        ps_cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*bot.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq Waifu Music Server*"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq KoboldCPP*"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "koboldcpp.exe"], capture_output=True)
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
        for name, url in [("Local LLM (8127)", "http://127.0.0.1:8127/health"), ("ComfyUI (8188)", "http://127.0.0.1:8188/system_stats")]:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    print(f"  ✓ {name}: " + c(GREEN, "ONLINE"))
            except Exception:
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
        status_tag = c(GREEN, "[INSTALLED]") if installed else c(YELLOW, "[MISSING]  ")
        size_str = f"({info.get('current_size_mb', 0)} MB)" if installed else f"(~{info.get('size_mb', 0)} MB required)"
        print(f"  {status_tag} {c(BOLD, key)}: {info.get('name')} {size_str}")
        print(c(DIM, f"             Target: {info.get('target_path') or info.get('target_dir')}"))
        print(c(DIM, f"             Used for: {info.get('required_for', '-')}\n"))

    print(c(CYAN, "Commands:"))
    print(c(DIM, "  waifu models download <key>  - Download specific model/extension"))
    print(c(DIM, "  Example: waifu models download animatediff_v2\n"))

def cmd_update():
    print_banner()
    cur_v = get_version()
    print(c(CYAN, f"🔄 Checking updates (Current Version: v{cur_v})..."))
    is_running = get_running_pid() is not None

    # Step 1: Git pull latest changes
    git_dir = os.path.join(PROJECT_ROOT, ".git")
    if os.path.exists(git_dir):
        print(c(CYAN, "📥 [1/4] Pulling latest repository updates from GitHub..."))
        try:
            res = subprocess.run(["git", "pull", "--tags"], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if res.returncode == 0:
                print(c(GREEN, "  ✓ Latest source code pulled successfully from GitHub."))
                if res.stdout.strip():
                    print(c(DIM, "    " + res.stdout.strip().replace("\n", "\n    ")))
            else:
                notice = res.stderr.strip() or "Already up to date"
                print(c(YELLOW, f"  ℹ Git notice: {notice}"))
        except Exception as e:
            print(c(YELLOW, f"  ⚠️ Git pull error: {e}"))
    else:
        print(c(YELLOW, "  Project directory is not a Git clone. Please run the 1-click installer to update."))

    # Step 2: Auto check and install Python dependencies
    req_txt = os.path.join(PROJECT_ROOT, "requirements.txt")
    if os.path.exists(req_txt):
        print(c(CYAN, "📦 [2/4] Checking and updating Python libraries (pip install -r requirements.txt)..."))
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

    # Step 3: Auto check Node.js dependencies for music remote
    pkg_json = os.path.join(PROJECT_ROOT, "package.json")
    if os.path.exists(pkg_json):
        print(c(CYAN, "🎵 [3/4] Checking Node.js dependencies for YouTube music remote..."))
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
            print(c(DIM, "  ℹ Node.js/npm not installed. (Optional: only needed for YouTube music playback)"))

    # Step 4: Auto check ComfyUI extensions & AI models
    if asset_manager:
        print(c(CYAN, "🧩 [4/4] Checking ComfyUI extensions & AI models..."))
        comfy_dir = asset_manager.detect_comfyui_dir()
        if comfy_dir:
            assets = asset_manager.check_all_assets()
            missing = [k for k, v in assets.items() if not v.get("installed")]
            if missing:
                print(c(YELLOW, f"  ℹ ComfyUI detected at: {comfy_dir}"))
                print(c(YELLOW, f"  ℹ Optional models available for download: {', '.join(missing)}"))
                print(c(DIM, "    (Run 'waifu models' to view details or 'waifu models download <key>' to install)"))
            else:
                print(c(GREEN, "  ✓ All core AI models & ComfyUI extensions are verified."))
        else:
            print(c(DIM, "  ℹ ComfyUI directory not detected yet (will auto-check when ComfyUI is launched)."))

    new_v = get_version()
    if new_v != cur_v:
        print(c(BOLD + GREEN, f"\n🎉 Successfully updated Waifu on Telegram from v{cur_v} to v{new_v}!"))
    else:
        print(c(BOLD + GREEN, f"\n🎉 Waifu on Telegram is already at latest version (v{new_v})!"))

    if is_running:
        print(c(CYAN, "\n🔄 Restarting bot daemon to apply all changes cleanly..."))
        cmd_restart(daemon=True)
    else:
        print(c(DIM, "\nStart your bot anytime with: waifu start --daemon\n"))

def main():
    if any(a in sys.argv[1:] for a in ("-v", "--version", "version")):
        print(c(BOLD + CYAN, f"💖 Waifu on Telegram v{get_version()}"))
        return

    parser = argparse.ArgumentParser(description="💖 Waifu on Telegram CLI", add_help=False)
    parser.add_argument("command", nargs="?", default="status", choices=["start", "stop", "restart", "status", "setup", "config", "autorun", "persona", "language", "lang", "logs", "models", "model", "assets", "update", "uninstall", "release", "version", "--version", "-v", "help"])
    parser.add_argument("arg", nargs="?", default=None)
    parser.add_argument("extra_args", nargs="*", default=[])
    parser.add_argument("--daemon", "-d", action="store_true", help="Run bot silently in background")
    args = parser.parse_args()

    cmd = args.command
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
    elif cmd in ("version", "--version", "-v"):
        print(c(BOLD + CYAN, f"💖 Waifu on Telegram v{get_version()}"))
    elif cmd == "uninstall":
        cmd_uninstall()
    elif cmd == "help":
        print_banner()
        print("Available CLI Commands:")
        print("  waifu start [--daemon]   - Start bot (foreground or background daemon)")
        print("  waifu stop               - Stop bot & services")
        print("  waifu restart            - Restart bot in background")
        print("  waifu status             - Check diagnostics for LLM, ComfyUI, & process")
        print("  waifu setup              - Open interactive configuration manager")
        print("  waifu update             - Pull latest updates & restart services")
        print("  waifu models [dl <name>] - Manage AI models & ComfyUI extensions")
        print("  waifu persona <name>     - Switch persona (runa, akira, hina, shiro, yume)")
        print("  waifu language [id|en|ja] - Change waifu language (ID, EN, JA, or Custom)")
        print("  waifu autorun [on|off]   - Configure autorun on system startup")
        print("  waifu logs               - Inspect recent log activity")
        print("  waifu uninstall          - Complete uninstallation and cleanup wizard")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
💖 WAIFU ON TELEGRAM - AUTONOMOUS AI ROMANCE COMPANION CLI 🤖
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
PID_FILE = os.path.join(PROJECT_ROOT, "bot.pid")
LOG_FILE = os.path.join(PROJECT_ROOT, "bot.log")

def print_banner():
    banner = f"""
{c(BOLD + MAGENTA, "  ██╗    ██╗ █████╗ ██╗███████╗██╗   ██╗    ██████╗  ██████╗ ████████╗")}
{c(BOLD + MAGENTA, "  ██║    ██║██╔══██╗██║██╔════╝██║   ██║    ██╔══██╗██╔═══██╗╚══██╔══╝")}
{c(BOLD + MAGENTA, "  ██║ █╗ ██║███████║██║█████╗  ██║   ██║    ██████╔╝██║   ██║   ██║   ")}
{c(BOLD + MAGENTA, "  ██║███╗██║██╔══██║██║██╔══╝  ██║   ██║    ██╔══██╗██║   ██║   ██║   ")}
{c(BOLD + MAGENTA, "  ╚███╔███╔╝██║  ██║██║██║     ╚██████╔╝    ██████╔╝╚██████╔╝   ██║   ")}
{c(BOLD + MAGENTA, "   ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝╚═╝      ╚═════╝     ╚═════╝  ╚═════╝    ╚═╝   ")}
  {c(CYAN, "💖 WAIFU ON TELEGRAM - Autonomous AI Romance Companion 🤖")}
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
    else:
        pid = get_running_pid()
        if pid:
            try:
                os.kill(pid, 15)
            except Exception:
                pass

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
        print(c(BOLD + CYAN, "System Status Diagnostics:"))
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

def cmd_update():
    print_banner()
    print(c(CYAN, "🔄 Checking and pulling latest updates from GitHub..."))
    is_running = get_running_pid() is not None

    git_dir = os.path.join(PROJECT_ROOT, ".git")
    if os.path.exists(git_dir):
        try:
            res = subprocess.run(["git", "pull"], cwd=PROJECT_ROOT, capture_output=True, text=True)
            if res.returncode == 0:
                print(c(GREEN, "  ✓ Latest source code pulled successfully from GitHub."))
                if res.stdout.strip():
                    print(c(DIM, "    " + res.stdout.strip().replace("\n", "\n    ")))
            else:
                print(c(YELLOW, f"  ℹ Git notice: {res.stderr.strip() or 'Already up to date'}"))
        except Exception as e:
            print(c(YELLOW, f"  ⚠️ Git pull error: {e}"))
    else:
        print(c(YELLOW, "  Project directory is not a Git clone. Using 1-line installer to update..."))

    req_txt = os.path.join(PROJECT_ROOT, "requirements.txt")
    if os.path.exists(req_txt):
        print(c(CYAN, "📦 Verifying dependencies..."))
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_txt, "--quiet", "--disable-pip-version-check"], cwd=PROJECT_ROOT)
            print(c(GREEN, "  ✓ Python dependencies are up to date."))
        except Exception:
            pass

    print(c(BOLD + GREEN, "\n🎉 Waifu on Telegram has been successfully updated!"))
    if is_running:
        print(c(CYAN, "Restarting bot to apply all updates..."))
        cmd_restart(daemon=True)
    else:
        print(c(DIM, "Start your bot anytime with: waifu start --daemon\n"))

def main():
    parser = argparse.ArgumentParser(description="💖 Waifu on Telegram CLI", add_help=False)
    parser.add_argument("command", nargs="?", default="status", choices=["start", "stop", "restart", "status", "setup", "config", "autorun", "persona", "logs", "update", "uninstall", "help"])
    parser.add_argument("arg", nargs="?", default=None)
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
    elif cmd == "logs":
        cmd_logs()
    elif cmd == "update":
        cmd_update()
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
        print("  waifu persona <name>     - Switch persona (runa, akira, hina, shiro, yume)")
        print("  waifu autorun [on|off]   - Configure autorun on system startup")
        print("  waifu logs               - Inspect recent log activity")
        print("  waifu uninstall          - Complete uninstallation and cleanup wizard")

if __name__ == "__main__":
    main()

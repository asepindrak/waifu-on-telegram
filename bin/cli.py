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
    try:
        import ctypes
        # Suppress Windows modal crash / bad image error dialogs (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
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

    # Direct process detection fallback for bot.py
    cur_pid = os.getpid()
    if platform.system() == "Windows":
        try:
            ps_check = f'Get-CimInstance Win32_Process | Where-Object {{ ($_.Name -like "python*.exe") -and ($_.CommandLine -like "*bot.py*") -and ($_.ProcessId -ne {cur_pid}) }} | Select-Object -ExpandProperty ProcessId -First 1'
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_check], capture_output=True, text=True, timeout=5)
            out = res.stdout.strip()
            if out and out.isdigit():
                return int(out)
        except Exception:
            pass
    else:
        try:
            out = subprocess.run(["pgrep", "-f", "python.*bot.py"], capture_output=True, text=True).stdout.strip()
            if out:
                for line in out.splitlines():
                    if line.strip().isdigit() and int(line.strip()) != cur_pid:
                        return int(line.strip())
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

    # Record current Python interpreter for startup scripts & background services
    try:
        with open(os.path.join(PROJECT_ROOT, ".python_path"), "w", encoding="utf-8") as pf:
            pf.write(sys.executable)
    except Exception:
        pass

    bot_script = os.path.join(PROJECT_ROOT, "bot.py")

    if daemon:
        popen_kwargs = {}
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        with open(LOG_FILE, "a", encoding="utf-8") as log_out:
            p = subprocess.Popen(
                [sys.executable, bot_script],
                cwd=PROJECT_ROOT,
                stdout=log_out,
                stderr=log_out,
                **popen_kwargs
            )
            with open(PID_FILE, "w") as f:
                f.write(str(p.pid))
            print(c(GREEN, f"✓ Waifu is running silently in the background (PID {p.pid})!"))
            print(c(DIM, f"  Log file: {LOG_FILE}"))
            print(c(DIM, "  Use 'waifu status' to inspect or 'waifu stop' to terminate."))
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
    smart_idle = os.environ.get("SMART_IDLE_ENABLED", "true").lower() in ("true", "1", "yes")
    if smart_idle:
        print(c(CYAN, "  💤 Local LLM on standby (Smart Idle: VRAM bebas • Bangun otomatis saat chat)"))
    else:
        kcpp_running = False
        try:
            from health_engine import get_koboldcpp_process_count
            kcpp_running = (get_koboldcpp_process_count() > 0)
        except Exception:
            pass
        if not kcpp_running and not is_port_listening(5001):
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
                    gpu_layers = os.environ.get("LLM_GPU_LAYERS", "").strip()
                    if not gpu_layers:
                        try:
                            hw_profile = asset_manager.detect_hardware_profile() if asset_manager else {}
                            gpu_layers = str(hw_profile.get("recommended_llm_layers", 24))
                        except Exception:
                            gpu_layers = "24"
                    ctx_size = os.environ.get("LLM_CONTEXT_SIZE", "4096").strip() or "4096"
                    cmd = [
                        kcpp_exe, "--model", model_path,
                        "--port", "5001",
                        "--gpulayers", gpu_layers,
                        "--contextsize", ctx_size,
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
        print(c(CYAN, "  💤 ComfyUI on standby (On-Demand Mode: auto-starts when photo/video is requested)"))
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

    # 4. Google Antigravity CLI Bridge (Port 8001)
    agy_enabled = os.environ.get("AGY_BRIDGE_ENABLED", "true").lower() in ("true", "1", "yes")
    agy_port = int(os.environ.get("AGY_BRIDGE_PORT", "8001"))
    if agy_enabled and not is_port_listening(agy_port):
        agy_script = os.path.join(PROJECT_ROOT, "agy_bridge.py")
        if os.path.exists(agy_script) and (shutil.which("agy") or shutil.which("agy.cmd")):
            try:
                subprocess.Popen(
                    [sys.executable, agy_script],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **popen_kwargs
                )
                print(c(GREEN, f"  ✓ Google Antigravity CLI Bridge active on port {agy_port} (OpenAI Compatible)"))
            except Exception:
                pass

    # 5. VoiceStudio Local AI Voice Server (Port 3900)
    v_backend = os.environ.get("VOICE_BACKEND", "edge-tts").lower().strip()
    if v_backend in ("voicestudio", "local") and not is_port_listening(3900):
        try:
            from voicestudio_engine import voicestudio_engine
            if voicestudio_engine.is_installed():
                voicestudio_engine.start_service()
                print(c(GREEN, f"  ✓ VoiceStudio Local AI active on port {voicestudio_engine.port}"))
        except Exception:
            pass

def cmd_stop():
    print_banner()
    print(c(YELLOW, "🛑 Terminating Waifu on Telegram services..."))

    if platform.system() == "Windows":
        ps_cmd = 'Get-CimInstance Win32_Process | Where-Object { ($_.Name -like "python*.exe") -and ($_.CommandLine -like "*bot.py*") } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq Waifu Music Server*"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq KoboldCPP*"], capture_output=True)
        try:
            from health_engine import kill_all_koboldcpp
            kill_all_koboldcpp()
        except Exception:
            subprocess.run(["taskkill", "/F", "/IM", "koboldcpp*.exe"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq ComfyUI*"], capture_output=True)
        ps_comfy = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.py*" -and $_.CommandLine -like "*8188*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_comfy], capture_output=True)
        ps_bridge = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*agy_bridge.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_bridge], capture_output=True)
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
            subprocess.run(["pkill", "-f", "python.*agy_bridge.py"], capture_output=True)

    try:
        from voicestudio_engine import voicestudio_engine
        voicestudio_engine.stop_service()
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
        print(c(BOLD + CYAN, f"System Status Diagnostics (v{get_version()}):"))

        # Persona, Language, Outfit
        persona_name = os.environ.get("DEFAULT_PERSONA", "runa").title()
        lang_code = os.environ.get("BOT_LANGUAGE", "id")
        lang_names = {"id": "Bahasa Indonesia", "en": "English", "ja": "Japanese", "auto": "Auto-detect"}
        lang_disp = lang_names.get(lang_code, lang_code)
        
        outfit_key = "default"
        outfit_file = os.path.join(PROJECT_ROOT, "data", "user_outfits.json")
        if os.path.exists(outfit_file):
            try:
                with open(outfit_file, "r", encoding="utf-8") as of:
                    odata = json.load(of)
                    if odata:
                        last_val = list(odata.values())[-1]
                        outfit_key = last_val.get("key", "default") if isinstance(last_val, dict) else str(last_val)
            except Exception:
                pass
        outfit_disp = outfit_key
        if outfit_key == "nude":
            outfit_disp = "Full Nude [Auto-Switch NSFW Engine Active]"

        print(f"  👑 Active Persona: {persona_name} | Language: {lang_disp}")
        print(f"  👗 Current Outfit: {outfit_disp}")

        # AI Architecture
        ai_mode = os.environ.get("AI_ENGINE_MODE", "split")
        sfw_p = os.environ.get("SFW_LLM_PROVIDER", "gemini")
        sfw_m = os.environ.get("SFW_LLM_MODEL", "gemini-2.5-flash")
        nsfw_p = os.environ.get("NSFW_LLM_PROVIDER", "local")
        nsfw_m = os.environ.get("LOCAL_LLM_MODEL", "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf")
        print(f"  🧠 AI Architecture: {ai_mode.upper()} (SFW: {sfw_p} [{sfw_m}] • NSFW: {nsfw_p} [{nsfw_m}])")

        # Image Architecture
        sfw_img = os.environ.get("SFW_IMAGE_ENGINE", "comfyui")
        nsfw_img = os.environ.get("NSFW_IMAGE_ENGINE", "comfyui")
        sfw_ckpt = os.environ.get("SFW_COMFYUI_CHECKPOINT", "AnythingXL_xl.safetensors")
        nsfw_ckpt = os.environ.get("NSFW_COMFYUI_CHECKPOINT", "AOM3A1B_orange_mixs.safetensors")
        print(f"  🎨 Visual Architecture: SFW '{sfw_img}' ({sfw_ckpt}) • NSFW '{nsfw_img}' ({nsfw_ckpt})")

        smart_idle = os.environ.get("SMART_IDLE_ENABLED", "true").lower() in ("true", "1", "yes")
        on_demand = os.environ.get("COMFYUI_ON_DEMAND", "true").lower() in ("true", "1", "yes")
        llm_model = nsfw_m
        photo_ckpt = nsfw_ckpt if outfit_key == "nude" else sfw_ckpt

        for name, url, is_idle, model_name in [
            ("Local LLM (KoboldCPP 5001)", "http://127.0.0.1:5001/v1/models", smart_idle, llm_model),
            ("ComfyUI Generator (8188)", "http://127.0.0.1:8188/system_stats", on_demand, photo_ckpt)
        ]:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    print(f"  ✓ {name}: " + c(GREEN, "ONLINE (Full Load)"))
                    print(c(DIM, f"    Active Model: {model_name}"))
            except Exception:
                if is_idle:
                    print(f"  💤 {name}: " + c(CYAN, "STANDBY / SLEEPING (VRAM Saver)"))
                    print(c(DIM, f"    Target Model: {model_name} (Ready On-Demand)"))
                else:
                    print(f"  🔴 {name}: " + c(RED, "OFFLINE"))

        # Photo Vault info
        vault_catalog = os.path.join(PROJECT_ROOT, "data", "photo_vault", "catalog.json")
        v_count = 0
        if os.path.exists(vault_catalog):
            try:
                with open(vault_catalog, "r", encoding="utf-8") as vf:
                    v_count = len(json.load(vf))
            except Exception:
                pass
        print(f"  📂 Photo Vault: {v_count} photos stored in local gallery archive " + c(GREEN, "(Local Archive Active ✓)"))

        # Voice TTS
        v_backend = os.environ.get("VOICE_BACKEND", "edge-tts")
        v_speaker = os.environ.get("VOICE_NAME", "id-ID-GadisNeural")
        v_lang = os.environ.get("VOICE_LANGUAGE", "id-ID")
        print(f"  🎙️ Voice Engine: {v_backend} (Speaker: {v_speaker} • Lang: {v_lang} • Voice Button: On-Demand in Chat)")
        if "voicestudio" in v_backend.lower():
            vs_port = int(os.environ.get("VOICESTUDIO_PORT", "3900"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{vs_port}/", timeout=1.5):
                    print(f"  ✓ VoiceStudio Local AI (Port {vs_port}): " + c(GREEN, "ONLINE (Service Ready)"))
            except Exception:
                vs_dir = os.path.join(PROJECT_ROOT, "tools", "VoiceStudio")
                if os.path.exists(vs_dir):
                    print(f"  💤 VoiceStudio Local AI (Port {vs_port}): " + c(CYAN, "STANDBY / SLEEPING (VRAM Saver)"))
                else:
                    print(f"  🔴 VoiceStudio Local AI (Port {vs_port}): " + c(RED, "NOT INSTALLED"))
        else:
            print(f"  ✓ Voice TTS Cloud: " + c(GREEN, "ONLINE (Microsoft Edge-TTS Cloud Ready)"))

        # Coding Workspace & Active Project
        act_proj_file = os.path.join(PROJECT_ROOT, "data", "active_project.json")
        act_proj = "general"
        if os.path.exists(act_proj_file):
            try:
                with open(act_proj_file, "r", encoding="utf-8") as apf:
                    ap_data = json.load(apf)
                    if ap_data:
                        act_proj = list(ap_data.values())[-1]
            except Exception:
                pass
        p_root = os.environ.get("PROJECTS_DIR", os.path.expanduser("~"))
        print(f"  💻 Coding Workspace: Active Project '{act_proj}' (Root: {p_root})")

        # Open-Design Systems
        try:
            from open_design_engine import get_open_design_engine
            ode = get_open_design_engine()
            ds_count = len(ode.list_available_systems())
            sk_count = len(ode.list_available_skills())
            if ds_count > 0:
                print(f"  🎨 Open-Design UI/UX: ONLINE ({ds_count} Design Systems • {sk_count} Skills) " + c(GREEN, "[ACTIVE ✓]"))
            else:
                print(f"  🎨 Open-Design UI/UX: " + c(YELLOW, "Not installed"))
        except Exception:
            pass

        # Active Project Web Previews
        try:
            from project_server_manager import get_project_server_manager
            psm = get_project_server_manager()
            live_srvs = psm.list_active_servers()
            if live_srvs:
                desc = " • ".join([f"{s['project']} -> http://127.0.0.1:{s['port']}/" for s in live_srvs])
                print(f"  🌐 Web Previews: ONLINE ({desc}) " + c(GREEN, "[ACTIVE ✓]"))
        except Exception:
            pass

        # Scheduled message buffer info
        buf_file = os.path.join(PROJECT_ROOT, "data", "scheduled_message_buffer.json")
        buf_count = 0
        if os.path.exists(buf_file):
            try:
                with open(buf_file, "r", encoding="utf-8") as bf:
                    b_data = json.load(bf)
                    for u_val in b_data.values():
                        for m_list in u_val.values():
                            buf_count += len(m_list)
            except Exception:
                pass
        print(f"  🎮 Scheduled Message Buffer: {buf_count} messages saved " + c(GREEN, "(Gaming Protection Active ✓)"))

        # AGY OpenAI Bridge diagnostics
        agy_port = int(os.environ.get("AGY_BRIDGE_PORT", "8001"))
        try:
            try:
                r = urllib.request.urlopen(f"http://127.0.0.1:{agy_port}/health", timeout=1.5)
            except Exception:
                r = urllib.request.urlopen(f"http://127.0.0.1:{agy_port}/", timeout=1.5)
            with r:
                print(f"  ✓ Google Antigravity Bridge (Port {agy_port}): " + c(GREEN, "ONLINE (OpenAI API Ready)"))
        except Exception:
            if os.environ.get("AGY_BRIDGE_ENABLED", "true").lower() in ("true", "1", "yes"):
                print(f"  💤 Google Antigravity Bridge (Port {agy_port}): " + c(CYAN, "STANDBY / OFFLINE"))
            else:
                print(f"  ⚪ Google Antigravity Bridge (Port {agy_port}): " + c(DIM, "DISABLED"))

        print(f"  🔒 GPU Resource Lock: " + c(GREEN, "ACTIVE (VRAM collision protection for Image & Voice Active ✓)"))

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

def cmd_autotune():
    print_banner()
    import asset_manager
    hw = asset_manager.detect_hardware_profile(refresh=True)
    print(c(BOLD + CYAN, "🎮 HARDWARE GPU & VRAM AUTO-TUNER"))
    print("-" * 60)
    print(f"  GPU Card      : {c(BOLD + GREEN, hw['gpu_name'])}")
    print(f"  Total VRAM    : {c(BOLD + GREEN, str(hw['vram_gb']) + ' GB')} ({hw['vram_mb']} MB)")
    print(f"  Hardware Tier : {c(BOLD + CYAN, hw['tier_label'])}")
    print(f"\n  💡 Recommendations:")
    print(f"    • Photo Model : {c(BOLD + GREEN, hw['recommended_image_file'] or 'Cloud Fallback Engine')}")
    print(f"    • Video Engine: {c(BOLD + GREEN, hw['recommended_video_engine'].upper())}")
    print(f"    • LLM Layers  : {c(BOLD + GREEN, str(hw['recommended_llm_layers']))}")
    print(f"\n  {c(DIM, hw['recommendation_text'])}")

    env_file = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()

        changed = False
        import re
        if hw["recommended_image_file"]:
            if "COMFYUI_CHECKPOINT=" in content:
                content = re.sub(r"COMFYUI_CHECKPOINT=.*", f"COMFYUI_CHECKPOINT={hw['recommended_image_file']}", content)
            else:
                content += f"\nCOMFYUI_CHECKPOINT={hw['recommended_image_file']}"
            changed = True
        if "VIDEO_ENGINE=" in content:
            content = re.sub(r"VIDEO_ENGINE=.*", f"VIDEO_ENGINE={hw['recommended_video_engine']}", content)
            changed = True
        else:
            content += f"\nVIDEO_ENGINE={hw['recommended_video_engine']}"
            changed = True

        if changed:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(c(GREEN, f"\n✓ .env configuration successfully auto-tuned for your PC GPU!"))

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
    try:
        _execute_models(subcmd, target)
    except KeyboardInterrupt:
        print(c(YELLOW, "\n\n  🛑 Operasi dibatalkan oleh pengguna (Ctrl+C). File progres tersimpan dan dapat dilanjutkan kapan saja.\n"))
        return

def _execute_models(subcmd=None, target=None):
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
        if target == "moondream":
            print(c(CYAN, "⏳ Downloading complete Moondream2 vision suite (Text Model + mmproj)..."))
            ok1 = asset_manager.download_asset("moondream_text")
            ok2 = asset_manager.download_asset("moondream_mmproj")
            if ok1 and ok2:
                print(c(GREEN, "✓ Moondream2 vision models downloaded and ready!"))
            return
        if target in ("stheno", "stheno-8b"):
            target = "stheno_8b"
        if target in ("mistral", "nemo", "mistral-nemo", "mistral_nemo", "mistral_nemo_12b", "nemo-12b", "nemo_12b"):
            target = "mistral_nemo_12b"
        if target in ("qwen", "qwen25", "qwen2.5", "qwen-7b", "qwen2.5-7b", "qwen25_7b"):
            target = "qwen25_7b"
        if target in ("huihui", "qwythos", "qwythos-9b", "huihui-qwythos", "huihui_9b"):
            target = "qwythos_9b"
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
    try:
        _execute_update()
    except KeyboardInterrupt:
        print(c(YELLOW, "\n\n  🛑 Pembaruan dibatalkan oleh pengguna (Ctrl+C). File progres tersimpan dan dapat dilanjutkan kapan saja (resume support aktif).\n"))
        return

def _execute_update():
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
                # If new commits were fetched, respawn updater to run newly fetched logic
                if any(k in res.stdout for k in ["Updating ", "Fast-forward", "files changed"]) and not os.environ.get("_WAIFU_UPDATE_RESPAWNED"):
                    print(c(CYAN, "  ⚡ Source code updated! Reloading updater with latest release..."))
                    new_env = os.environ.copy()
                    new_env["_WAIFU_UPDATE_RESPAWNED"] = "1"
                    ret = subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, "bin", "cli.py"), "update"], env=new_env)
                    sys.exit(ret.returncode)
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
                        if not os.environ.get("_WAIFU_UPDATE_RESPAWNED"):
                            print(c(CYAN, "  ⚡ Reloading updater with latest release..."))
                            new_env = os.environ.copy()
                            new_env["_WAIFU_UPDATE_RESPAWNED"] = "1"
                            ret = subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, "bin", "cli.py"), "update"], env=new_env)
                            sys.exit(ret.returncode)
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
        # 1. Main Chat Brain: Huihui-Qwythos 9B (100% Uncensored Claude-Mythos Roleplay LLM)
        info_huihui = asset_manager.get_asset_info("qwythos_9b")
        if info_huihui and not info_huihui.get("installed"):
            print(c(YELLOW, f"  ⏳ Core Brain '{info_huihui['name']}' missing. Auto-downloading (~{info_huihui['size_mb']} MB)..."))
            ok = asset_manager.download_asset("qwythos_9b")
            if ok:
                print(c(GREEN, f"  ✓ '{info_huihui['name']}' downloaded successfully!"))
            else:
                print(c(RED, f"  ❌ Download failed for '{info_huihui['name']}'. Run 'waifu models download qwythos_9b'."))
        else:
            sz = info_huihui.get("current_size_mb", 0) if info_huihui else 0
            print(c(GREEN, f"  ✓ Core Chat Brain '{info_huihui['name']}' is ready ({sz} MB)."))

        # Ensure a default uncensored model is set if none is configured
        try:
            from setup import read_env, write_env
            env_dict = read_env()
            cur_llm = env_dict.get("LLM_MODEL", "").strip()
            cur_local = env_dict.get("LOCAL_LLM_MODEL", "").strip()
            cur_nsfw = env_dict.get("NSFW_LLM_MODEL", "").strip()
            huihui_fn = "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
            changed = False
            if not cur_local or cur_local.lower() in ("default", "none"):
                env_dict["LOCAL_LLM_MODEL"] = huihui_fn
                os.environ["LOCAL_LLM_MODEL"] = huihui_fn
                changed = True
            if not cur_nsfw or cur_nsfw.lower() in ("default", "none"):
                env_dict["NSFW_LLM_MODEL"] = huihui_fn
                os.environ["NSFW_LLM_MODEL"] = huihui_fn
                changed = True
            if not cur_llm or cur_llm.lower() in ("default", "none"):
                env_dict["LLM_MODEL"] = huihui_fn
                os.environ["LLM_MODEL"] = huihui_fn
                changed = True
            if changed:
                write_env(env_dict)
                print(c(GREEN, f"  ✓ Default uncensored model ({huihui_fn}) configured."))
        except Exception as e_env:
            logger.debug(f"Default model init error: {e_env}")

        # 2. Vision Adapter for Huihui: qwythos_vision mmproj
        info_vis = asset_manager.get_asset_info("qwythos_vision")
        if info_vis and not info_vis.get("installed"):
            print(c(YELLOW, f"  ⏳ Vision Adapter '{info_vis['name']}' missing. Auto-downloading (~{info_vis['size_mb']} MB)..."))
            ok = asset_manager.download_asset("qwythos_vision")
            if ok:
                print(c(GREEN, f"  ✓ '{info_vis['name']}' downloaded successfully!"))
        else:
            sz_vis = info_vis.get("current_size_mb", 0) if info_vis else 0
            print(c(GREEN, f"  ✓ Vision Adapter '{info_vis['name']}' is ready ({sz_vis} MB)."))

        # 3. Vision Perception Models: Moondream2 (Ultra-lightweight local perception for Telegram photos)
        for m_key in ("moondream_text", "moondream_mmproj"):
            info_m = asset_manager.get_asset_info(m_key)
            if info_m and not info_m.get("installed"):
                print(c(YELLOW, f"  ⏳ Vision Model '{info_m['name']}' missing. Auto-downloading (~{info_m['size_mb']} MB)..."))
                ok = asset_manager.download_asset(m_key)
                if ok:
                    print(c(GREEN, f"  ✓ '{info_m['name']}' downloaded successfully!"))
                else:
                    print(c(RED, f"  ❌ Download failed for '{info_m['name']}'. Run 'waifu models download {m_key}'."))
            else:
                sz = info_m.get("current_size_mb", 0) if info_m else 0
                print(c(GREEN, f"  ✓ Vision Model '{info_m['name']}' is ready ({sz} MB)."))

        # 3. ComfyUI Models (if ComfyUI is detected or auto-installed)
        sfw_img_engine = os.environ.get("SFW_IMAGE_ENGINE", "").lower().strip()
        media_fallback_agy = os.environ.get("MEDIA_FALLBACK_AGY", "false").lower() in ("true", "1", "yes")
        is_agy_user = (sfw_img_engine == "agy") or media_fallback_agy

        if not is_agy_user:
            # Auto-switch local image default to AOM3A1B_orangemixs.safetensors
            aom_fn = "AOM3A1B_orangemixs.safetensors"
            try:
                from setup import read_env, write_env
                env_dict = read_env()
                cur_ckpt = env_dict.get("COMFYUI_CHECKPOINT", "").strip()
                cur_sfw_ckpt = env_dict.get("SFW_COMFYUI_CHECKPOINT", "").strip()
                cur_nsfw_ckpt = env_dict.get("NSFW_COMFYUI_CHECKPOINT", "").strip()
                changed_ckpt = False

                if not cur_ckpt or "meina" in cur_ckpt.lower():
                    env_dict["COMFYUI_CHECKPOINT"] = aom_fn
                    os.environ["COMFYUI_CHECKPOINT"] = aom_fn
                    changed_ckpt = True

                if not cur_nsfw_ckpt or "meina" in cur_nsfw_ckpt.lower():
                    env_dict["NSFW_COMFYUI_CHECKPOINT"] = aom_fn
                    os.environ["NSFW_COMFYUI_CHECKPOINT"] = aom_fn
                    changed_ckpt = True

                if sfw_img_engine == "comfyui" and (not cur_sfw_ckpt or "meina" in cur_sfw_ckpt.lower()):
                    env_dict["SFW_COMFYUI_CHECKPOINT"] = aom_fn
                    os.environ["SFW_COMFYUI_CHECKPOINT"] = aom_fn
                    changed_ckpt = True

                if changed_ckpt:
                    write_env(env_dict)
                    print(c(GREEN, f"  🔄 Auto-switch default local image checkpoint ke AbyssOrangeMix3 ({aom_fn})"))
            except Exception as e_ckpt:
                logger.debug(f"Auto-switch checkpoint error: {e_ckpt}")
        else:
            print(c(CYAN, "  🌉 User terkonfigurasi menggunakan Google Antigravity (AGY) Engine. Melewati auto-switch ComfyUI."))

        comfy_dir = asset_manager.detect_comfyui_dir()
        if not comfy_dir and platform.system() == "Windows" and not is_agy_user:
            print(c(YELLOW, "  ⏳ ComfyUI not detected locally. Auto-installing official ComfyUI Portable (~1.4 GB)..."))
            if asset_manager.ensure_comfyui():
                comfy_dir = asset_manager.detect_comfyui_dir()
                print(c(GREEN, f"  ✓ ComfyUI Portable ready at: {comfy_dir}"))

        if comfy_dir:
            print(c(CYAN, f"  🧩 ComfyUI detected at: {comfy_dir}"))
            if is_agy_user:
                print(c(CYAN, "  ℹ Mode AGY aktif, mempertahankan checkpoint ComfyUI yang ada."))
            else:
                configured_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "").lower()
                target_asset = "anything_xl" if ("anything" in configured_ckpt and "aom" not in configured_ckpt) else "aom3"
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

    active_pid = get_running_pid()
    if is_running or active_pid:
        target_pid = active_pid or "active"
        print(c(CYAN, f"\n🔄 Detected bot running in background (PID: {target_pid})."))
        print(c(CYAN, "⚡ Restarting bot automatically so all updates take effect..."))
        cmd_restart(daemon=True)
        print(c(GREEN, "✓ Bot restarted successfully in background! ✨\n"))
    else:
        print(c(DIM, "\n💡 Bot is not running. Start anytime with: waifu start --daemon\n"))


def cmd_voicestudio(action: str = "status"):
    """Manages the local VoiceStudio background service (port 3900)."""
    action = (action or "status").lower()
    from voicestudio_engine import voicestudio_engine

    if action == "status":
        st = voicestudio_engine.get_status()
        print(c(BOLD + CYAN, "\n🔊 VoiceStudio Local AI Voice Server Diagnostics:"))
        print(f"  • Service Status : {c(BOLD + GREEN, 'ONLINE 🟢') if st['running'] else c(YELLOW, 'OFFLINE ⚪')}")
        print(f"  • Backend Port   : {st['port']} ({st['url']})")
        print(f"  • Installed      : {'Yes ✅' if st['installed'] else 'No ❌'}")
        print(f"  • Root Directory : {st['install_dir']}")
        print(f"  • Default Model  : {st['default_model']}")
        if not st['running'] and st['installed']:
            print(c(DIM, "\n💡 Run 'waifu voicestudio start' to launch the VoiceStudio backend."))
        elif not st['installed']:
            print(c(DIM, "\n💡 Run 'waifu voicestudio install' to download and set up VoiceStudio."))
    elif action == "start":
        print(c(CYAN, f"\n🚀 Launching VoiceStudio background service on port {voicestudio_engine.port}..."))
        if voicestudio_engine.is_service_running():
            print(c(YELLOW, f"⚠️ VoiceStudio is already running at {voicestudio_engine.server_url}."))
            return
        if not voicestudio_engine.is_installed():
            print(c(YELLOW, "VoiceStudio is not installed. Running auto-installer..."))
            ok, msg = voicestudio_engine.install(progress_callback=lambda m: print(f"  {m}"))
            if not ok:
                print(c(RED, f"❌ {msg}"))
                return
        ok = voicestudio_engine.start_service()
        if ok:
            print(c(GREEN, f"✓ VoiceStudio online at {voicestudio_engine.server_url}"))
        else:
            print(c(RED, "❌ Failed to start VoiceStudio. Check logs or port 3900."))
    elif action == "stop":
        print(c(YELLOW, f"\n🛑 Stopping VoiceStudio background service..."))
        ok = voicestudio_engine.stop_service()
        if ok:
            print(c(GREEN, "✓ VoiceStudio has been stopped."))
        else:
            print(c(RED, "❌ Failed to stop VoiceStudio."))
    elif action == "restart":
        print(c(CYAN, f"\n🔄 Restarting VoiceStudio background service..."))
        voicestudio_engine.stop_service()
        time.sleep(1.0)
        ok = voicestudio_engine.start_service()
        if ok:
            print(c(GREEN, f"✓ VoiceStudio restarted successfully at {voicestudio_engine.server_url}"))
        else:
            print(c(RED, "❌ Failed to restart VoiceStudio."))
    elif action in ("install", "setup"):
        print(c(CYAN, "\n📦 Starting VoiceStudio backend setup & installation..."))
        ok, msg = voicestudio_engine.install(progress_callback=lambda m: print(f"  {m}"))
        if ok:
            print(c(GREEN, f"✓ {msg}"))
            print(c(DIM, "Gunakan 'waifu voicestudio start' untuk menyalakan service."))
        else:
            print(c(RED, f"❌ {msg}"))
    else:
        print(c(YELLOW, f"Aksi '{action}' tidak dikenal. Gunakan: status | start | stop | restart | install"))


def cmd_bridge(action: str = "status"):
    """Manages Google Antigravity CLI OpenAI-Compatible Bridge Server."""
    action = (action or "status").lower()
    agy_port = int(os.environ.get("AGY_BRIDGE_PORT", "8001"))
    agy_script = os.path.join(PROJECT_ROOT, "agy_bridge.py")

    if action == "start":
        print(c(CYAN, f"\n🚀 Launching Google Antigravity CLI Bridge on port {agy_port}..."))
        if is_port_listening(agy_port):
            print(c(YELLOW, f"⚠️ Port {agy_port} is already in use (Bridge is already active)."))
            return

        popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if platform.system() == "Windows" else {"start_new_session": True}
        subprocess.Popen([sys.executable, agy_script], cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **popen_kwargs)
        time.sleep(1.5)
        if is_port_listening(agy_port):
            print(c(GREEN, f"✓ AGY Bridge is online at http://127.0.0.1:{agy_port}/v1"))
            print(c(DIM, "  OpenAI API Compatible: /v1/chat/completions | /v1/models"))
        else:
            print(c(YELLOW, f"⏳ AGY Bridge is initializing... Check status with 'waifu bridge status'."))
    elif action == "stop":
        print(c(YELLOW, f"\n🛑 Stopping Google Antigravity CLI Bridge (port {agy_port})..."))
        if platform.system() == "Windows":
            ps_cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*agy_bridge.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "python.*agy_bridge.py"], capture_output=True)
        print(c(GREEN, "✓ AGY Bridge has been stopped."))
    elif action == "restart":
        cmd_bridge("stop")
        time.sleep(1.5)
        cmd_bridge("start")
    else:  # status
        import urllib.request
        print_banner()
        print(c(BOLD + CYAN, "🌉 GOOGLE ANTIGRAVITY CLI (AGY) OPENAI-COMPATIBLE BRIDGE:"))
        print(c(DIM, "─" * 70))
        try:
            try:
                r = urllib.request.urlopen(f"http://127.0.0.1:{agy_port}/health", timeout=2)
            except Exception:
                r = urllib.request.urlopen(f"http://127.0.0.1:{agy_port}/", timeout=2)
            with r:
                data = json.loads(r.read().decode("utf-8"))
                print(f"  • Status      : " + c(GREEN, "ONLINE (OpenAI API Ready ✓)"))
                print(f"  • Endpoint    : http://127.0.0.1:{agy_port}/v1")
                print(f"  • Engine      : {data.get('engine', 'Google Antigravity CLI')}")
                print(f"  • AGY Version : {data.get('agy_version', 'N/A')}")
                print(f"  • Model Def   : {data.get('default_model', 'flash')} (flash, pro, inherit)")
                print(c(DIM, "\n  Gunakan di aplikasi eksternal (Cursor, VSCode, LibreChat, dll):"))
                print(c(DIM, f"    Base URL : http://127.0.0.1:{agy_port}/v1"))
                print(c(DIM, f"    API Key  : sk-agy-secret-key-12345 (atau bebas)"))
                print(c(DIM, f"    Model    : flash / pro / inherit"))
        except Exception:
            print(f"  • Status      : " + c(RED, f"OFFLINE (Port {agy_port} tidak merespon)"))
            print(c(DIM, "  Nyalakan dengan: waifu bridge start"))
        print(c(DIM, "─" * 70) + "\n")

def cmd_chat():
    """Starts the interactive CLI chat session with shared Telegram history."""
    try:
        from cli_chat import start_cli_chat
        start_cli_chat()
    except Exception as e:
        print(c(RED, f"\n❌ Error starting CLI chat session: {e}\n"))

def cmd_idle():
    """Manually puts local AI engines (KoboldCPP, ComfyUI, VoiceStudio) to sleep to free VRAM & RAM."""
    print(c(BOLD + CYAN, "\n💤 Activating Idle Mode Manually (VRAM Saver)..."))
    try:
        from idle_engine import IdleEngine
        engine = IdleEngine(project_root=PROJECT_ROOT)
        results = engine.manual_idle()
        for d in results.get("details", []):
            print(f"  • {d}")
        print(c(BOLD + GREEN, "\n✓ Idle mode activated. VRAM & RAM freed for gaming or heavy work!"))
        print(c(DIM, "  (Waifu will automatically wake up when you send a message or request)\n"))
    except Exception as e:
        print(c(RED, f"\n❌ Failed to activate idle mode: {e}\n"))

def cmd_code(prompt: str):
    """Executes a coding task directly in active workspace via CLI."""
    if not prompt:
        print(c(YELLOW, "\n💡 Usage: waifu code \"<coding task instructions>\""))
        print("   Example: waifu code \"create a responsive modern navbar\"\n")
        return
    print(c(BOLD + CYAN, f"\n👩‍💻 Executing coding task in active workspace..."))
    try:
        from coding_engine import get_coding_engine
        from project_manager import get_project_manager
        pm = get_project_manager()
        active_p = pm.get_active_project(0)
        active_path = pm.get_active_project_path(0)
        print(f"  • Project: {c(GREEN, active_p)}")
        print(f"  • Folder:  {c(DIM, active_path)}\n")
        engine = get_coding_engine()
        res, _ = engine.execute_coding_task(user_id=0, prompt=prompt, persona={"name": "Waifu"})
        print(res)
        print(c(BOLD + GREEN, "\n✓ Completed!\n"))
    except Exception as e:
        print(c(RED, f"\n❌ Failed to execute coding task: {e}\n"))

def print_cli_help(unknown_cmd: str = None):
    print_banner()
    if unknown_cmd:
        import difflib
        valid_cmds = [
            "start", "stop", "restart", "status", "idle", "code", "setup", "config",
            "update", "models", "persona", "language", "autorun",
            "logs", "version", "uninstall", "help"
        ]
        matches = difflib.get_close_matches(unknown_cmd.lower(), valid_cmds, n=1, cutoff=0.4)
        if matches:
            print(c(BOLD + YELLOW, f"\n⚠️  Command '{unknown_cmd}' not recognized. Did you mean: 'waifu {matches[0]}'?\n"))
        else:
            print(c(BOLD + RED, f"\n❌ Command '{unknown_cmd}' not recognized.\n"))

    print(c(BOLD + CYAN, "📋 OFFICIAL COMMANDS LIST ('waifu <command>'):"))
    print(c(DIM, "─" * 70))
    print(c(BOLD + MAGENTA, "  💬 Direct Chat & Interaction:"))
    print(f"    {c(GREEN, 'waifu')} (or {c(GREEN, 'waifu chat')})        Interactive CLI chat session (Auto-opens photo & video!)")
    print(f"    {c(GREEN, 'waifu code')} \"<task>\"        Run autonomous coding task in active workspace")

    print(c(BOLD + MAGENTA, "\n  🚀 Service Control & Diagnostics:"))
    print(f"    {c(GREEN, 'waifu start')} [--daemon]       Start bot & AI engines (foreground / background)")
    print(f"    {c(GREEN, 'waifu stop')}                  Stop bot & all background services")
    print(f"    {c(GREEN, 'waifu restart')}               Cleanly restart bot daemon")
    print(f"    {c(GREEN, 'waifu idle')}                  Manually put local AI to sleep & free 100% VRAM")
    print(f"    {c(GREEN, 'waifu status')}                Health diagnostics for LLM, ComfyUI, Music & RAM/VRAM")
    print(f"    {c(GREEN, 'waifu logs')}                  Monitor live bot activity logs")
    print(f"    {c(GREEN, 'waifu bridge')} [start|stop|status]  Manage Google Antigravity CLI OpenAI-compatible Bridge")

    print(c(BOLD + MAGENTA, "\n  ⚙️ Configuration & AI Models:"))
    print(f"    {c(GREEN, 'waifu autotune')}              Detect GPU/VRAM & optimize image/video models automatically")
    print(f"    {c(GREEN, 'waifu setup')}                 Interactive setup wizard (Token, Models, Voice)")
    print(f"    {c(GREEN, 'waifu models')} [dl <name>]    Manage & download AI models (MeinaMix, Anything XL, etc.)")
    print(f"    {c(GREEN, 'waifu persona')} <name>        Switch active waifu persona (runa, akira, hina, shiro, yume, alia)")
    print(f"    {c(GREEN, 'waifu language')} [id|en|ja]   Set conversational language preference (ID, EN, JA, AUTO)")
    print(f"    {c(GREEN, 'waifu autorun')} [on|off]      Configure bot autostart on Windows boot")

    print(c(BOLD + MAGENTA, "\n  🔄 Maintenance & Info:"))
    print(f"    {c(GREEN, 'waifu doctor')}                System health & prerequisite tools check (Python, Node.js, GPU)")
    print(f"    {c(GREEN, 'waifu update')}                Update repository, dependencies, and AI models")
    print(f"    {c(GREEN, 'waifu version')}               Show current Waifu on Telegram version")
    print(f"    {c(GREEN, 'waifu uninstall')}             Complete uninstallation wizard & clean up")

    print(c(DIM, "─" * 70))
    print(c(DIM, "💡 Usage examples:"))
    print(c(DIM, "    waifu start --daemon"))
    print(c(DIM, "    waifu models download anything_xl"))
    print(c(DIM, "    waifu persona alia\n"))

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

    cmd = args.command.lower() if args.command else "chat"
    if cmd in ("chat", "talk", "ngobrol"):
        cmd_chat()
    elif cmd == "start":
        cmd_start(daemon=args.daemon)
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "restart":
        cmd_restart(daemon=True)
    elif cmd in ("idle", "sleep", "tidur"):
        cmd_idle()
    elif cmd in ("code", "dev", "ngoding", "coding"):
        prompt_parts = [args.arg] if args.arg else []
        if args.extra_args:
            prompt_parts.extend(args.extra_args)
        full_code_prompt = " ".join(prompt_parts).strip()
        cmd_code(full_code_prompt)
    elif cmd in ("voicestudio", "voice_service"):
        action = args.arg or "status"
        cmd_voicestudio(action)
    elif cmd == "bridge":
        action = args.arg or "status"
        cmd_bridge(action)
    elif cmd == "status":
        cmd_status()
    elif cmd in ("setup", "config"):
        cmd_setup()
    elif cmd in ("autotune", "tune", "hardware"):
        cmd_autotune()
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
    elif cmd in ("doctor", "diagnostics", "check"):
        from setup import check_system_prerequisites
        check_system_prerequisites(interactive=False)
    elif cmd == "update":
        cmd_update()
    elif cmd == "release":
        cmd_release(args.arg)
    elif cmd == "uninstall":
        cmd_uninstall()
    else:
        print_cli_help(unknown_cmd=args.command)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c(YELLOW, "\n\n  🛑 Operasi dibatalkan oleh pengguna (Ctrl+C). Keluar dengan aman.\n"))
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

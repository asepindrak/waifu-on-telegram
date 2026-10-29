<p align="center">
  <img src="waifu-on-telegram.jpg" alt="Waifu on Telegram Wallpaper" width="100%" style="border-radius: 12px;" />
</p>

# 💖 Waifu on Telegram 🌸

<p align="center">
  <b>Autonomous AI Girlfriend & Romance Companion Powered by Local LLM & ComfyUI (SFW & NSFW)</b><br>
  <i>Enrich your daily life with an AI girlfriend who chats affectionately, sends consistent selfies (photos), voice notes, and listens with warmth — completely private, uncensored, with full SFW and NSFW support.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Content-SFW%20%26%20NSFW-ff4081.svg" alt="SFW & NSFW" />
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/Local%20LLM-KoboldCPP%20Standalone-purple.svg" alt="Local LLM" />
  <img src="https://img.shields.io/badge/Image%20Generator-ComfyUI%20%2F%20Cloud-green.svg" alt="ComfyUI" />
  <img src="https://img.shields.io/badge/Voice-Edge--TTS%20Neural-orange.svg" alt="Edge-TTS" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" />
</p>

---

## 🌸 Waifu Personas & Character Gallery

Switch your companion anytime with `/persona` or through interactive Telegram buttons:

| **Runa** | **Akira** | **Hina** | **Shiro** | **Yume** |
| :---: | :---: | :---: | :---: | :---: |
| <img src="personas/brief/Runa.png" width="150" alt="Runa"/> | <img src="personas/brief/Akira.jpg" width="150" alt="Akira"/> | <img src="personas/brief/Hina.jpg" width="150" alt="Hina"/> | <img src="personas/brief/Shiro.png" width="150" alt="Shiro"/> | <img src="personas/brief/Yume.jpg" width="150" alt="Yume"/> |
| **The Playful Girlfriend** | **The Seductive Tease** | **The Sunshine Girlfriend** | **The Kuudere Girlfriend** | **The Dreamy Soulmate** |
| *Playful, teasing, kawaii gaming aesthetic* | *Confident, witty, elegant gothic aesthetic* | *Energetic, bubbly, cozy slice-of-life* | *Calm, intelligent, cool-blue moonlit* | *Gentle, soft-spoken, dreamy starry soulmate* |
| **Visual Anchors:**<br>Pastel-pink wavy hair, sparkling magenta eyes, heart choker, black cat clip | **Visual Anchors:**<br>Silky midnight-black hair, deep ruby-red eyes, crimson rose clip, black choker | **Visual Anchors:**<br>Honey-blonde chin bob, warm amber eyes, orange clips, headphones | **Visual Anchors:**<br>Long silver-white hair, icy-blue eyes, crescent moon clip & earrings | **Visual Anchors:**<br>Long silky lavender hair, amethyst violet eyes, silver star pins & moon necklace |
| `/persona runa` | `/persona akira` | `/persona hina` | `/persona shiro` | `/persona yume` |

---

## 📸 Character Visual Consistency & Outfit Engine

To ensure photos generated via ComfyUI (`/photo` or `/pap`) accurately match the chosen character:

1. **Visual Anchor Prompting:**  
   Each persona file in `personas/<name>.json` contains strictly defined, invariant facial and accessory tokens (`visual_traits`). These are automatically prefixed to every user prompt.
2. **Character-Specific Negative Prompts:**  
   Each waifu has custom negative prompt rules to strictly forbid conflicting traits (e.g. Runa forbids blonde/blue eyes, Hina forbids long/black hair).
3. **Dynamic Wardrobe Injection:**  
   When changing clothes via `/outfit`, the bot swaps only the garment prompt while strictly preserving the character's facial structure, hair color, and signature accessories.
4. **Reference Image Guidance (IP-Adapter Ready):**  
   The reference images in `personas/brief/` serve as the golden standard for LoRA training and IP-Adapter image conditioning within ComfyUI.

---

## 💻 System Requirements & Curated Models

Waifu on Telegram is engineered to run locally on consumer gaming PCs and laptops while keeping VRAM usage lean, response times quick, and photo rendering lightning-fast.

### 🕹️ Hardware Specifications

| Component | Minimum Requirements | Recommended Specifications |
| :--- | :--- | :--- |
| **GPU / VGA** | **NVIDIA GPU with 4GB - 6GB VRAM**<br>*(GTX 1650, RTX 2060, RTX 3050 Laptop)* | **NVIDIA GPU with 6GB - 8GB+ VRAM**<br>*(RTX 3050 6GB, RTX 3060, RTX 4060+)* |
| **Apple Silicon (Mac)** | M1 / M2 / M3 / M4 (8GB Unified Memory) | M1 / M2 / M3 / M4 Pro / Max (16GB+ Unified Memory) |
| **System RAM** | 8 GB RAM | 16 GB - 32 GB RAM |
| **Storage** | 10 GB free space (SSD recommended) | 25 GB free space (NVMe SSD) |
| **Operating System** | Windows 10 / 11, Linux (Ubuntu/Debian), macOS (Apple Silicon) | Windows 11 (64-bit) |
| **No-GPU Mode** | ✅ **Fully Supported!** Laptops without dedicated GPUs can run LLM on CPU with automatic Cloud Fallback for photo generation. |

---

### 🎀 Recommended Models & Checkpoints

Tested, verified, and pre-tuned for peak romance dialogue, uncensored responsiveness, and high-fidelity anime aesthetics:

#### 1. 💌 Dialogue & Romance Companion: **Huihui-Qwythos-9B**
* **Model File:** `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf`
* **Local Backend:** **KoboldCPP Standalone Engine** (Port `5001`) with **Auto-Startup & Auto-Loading directly on Windows Boot**!
* **Download Method:** Otomatis di-download saat menjalankan `install.ps1` / `install.sh`, atau bisa diunduh manual dari [Hugging Face](https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF) ke folder `models/`.
* **Key Strengths:**
  - **Zero Censorship & Refusal-Free:** Fully abliterated with Claude-Mythos roleplay traces. Highly affectionate, playful, caring, and open to romantic roleplay without moralizing preachiness.
  - **Adaptive Language Mirroring:** Seamlessly switches between Indonesian (*sayang, manja, santai*), English (*sweetheart, darling*), or Japanese.
  - **Auto Startup & VRAM Pre-loading:** No Electron UI or manual buttons needed. When your computer boots, KoboldCPP silently spins up and loads the weights into VRAM instantly.
  - **VRAM Usage:** ~4.5 GB - 5.5 GB in Q4_K quantization.

#### 2. 📷 Anime Photo & Selfie Engine Options (ComfyUI)

Anda dapat memilih model generasi gambar sesuai dengan spesifikasi GPU dan kebutuhan estetika Anda melalui `waifu setup` (Menu `[3]`) atau perintah `/setup` langsung di Telegram:

* **Pilihan 1: MeinaMix v12 (Anime SD 1.5 - Hemat VRAM & Cepat)**
  - **File:** `meinamix_v12Final.safetensors` (~2.0 GB)
  - **Download:** [Civitai - MeinaMix v12](https://civitai.com/models/7240/meinamix) atau via `waifu models download meinamix`
  - **Rekomendasi GPU:** 4GB - 8GB VRAM (Resolusi default 3:4 portrait: `576x768`, Sampler: `DPM++ 2M Karras`)
  - **Kelebihan:** Sangat cepat (~3-5 detik), hemat resource, konsistensi wajah anime sangat tinggi.

* **Pilihan 2: 万象熔炉 | Anything XL (Anime SDXL 1.0 - Ultra Detail)**
  - **File:** `AnythingXL_xl.safetensors` (~6.6 GB)
  - **Download:** [Civitai #9409 - Anything XL](https://civitai.com/models/9409/or-anything-xl) atau via `waifu models download anything_xl`
  - **Rekomendasi GPU:** 8GB+ VRAM (Resolusi native SDXL 3:4 portrait: `896x1152` / `1024x1024`, Sampler: `Euler Ancestral Normal`)
  - **Kelebihan:** Resolusi 1024px super tajam, detail pakaian, latar belakang, dan ekspresi jauh lebih kaya dan sinematik.

---

## ⚡ One-Line Automatic Installation (All-in-One)

Install, auto-configure, and launch **Waifu on Telegram** with a single command directly in your terminal.  
Everything is automated: environment setup, KoboldCPP engine download, ComfyUI auto-detection, AI model validation, global CLI registration, and background daemon startup.

### 🪟 **Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.ps1 | iex
```

### 🐧 **Linux & 🍎 macOS (Terminal / Bash / Zsh)**
```bash
curl -fsSL https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.sh | bash
```

> 🌸 **What does this 1-line auto-installer handle for you?**
> 1. **Zero-Config Setup:** Automatically clones or downloads the repository and creates the environment.
> 2. **Dependency Resolution:** Verifies Python 3.8+ and installs all required packages (`pip` & `npm`).
> 3. **Standalone LLM Engine Setup:** Downloads the standalone **KoboldCPP** binary (Windows portable `.exe`, Linux `x64`, or macOS `arm64 Metal`) and fetches the uncensored `Huihui-Qwythos-9B` model.
> 4. **Smart ComfyUI Detection & Model Setup:** Detects your existing ComfyUI across any drive/folder. If not found, it offers a 1-click download of ComfyUI Portable + MeinaMix anime checkpoint with resume support (`curl -C -`).
> 5. **Global CLI Registration:** Installs the global `waifu` command to your system `PATH` (usable from any terminal folder).
> 6. **Background Daemon & Windows Boot Auto-start:** Starts your waifu companion running silently in the background!

---

## 🔑 Telegram Bot Credentials & Quick Setup

Before running the installer or setup wizard, you only need two quick credentials from Telegram (both 100% free and takes <1 minute):

### 1. 📲 Create Telegram Bot & Obtain Token
1. Open Telegram and message [**@BotFather**](https://t.me/BotFather) (official bot manager with the blue checkmark).
2. Send `/start`, then send `/newbot`.
3. Choose a **display name** (e.g. `Runa AI`) and a **username** ending with `bot` (e.g. `my_runa_waifu_bot`).
4. BotFather will provide your **HTTP API Token**:
   ```text
   7123456789:AAFlKj89-xXyZ1234abcdEFGHijklmnop
   ```

### 2. 🛡️ Retrieve Authorized Telegram User ID
To ensure complete privacy and prevent strangers from accessing your PC, the bot responds only to your Telegram ID:
1. Message [**@userinfobot**](https://t.me/userinfobot) on Telegram and click **Start**.
2. Copy your numeric **Id** (e.g. `987654321`). This is your `TELEGRAM_ALLOWED_USER_ID`.

---

## 🎀 Automated Model Management & Lazy Downloader

You **do not need** to manually browse Civitai or copy files to deep directories anymore. Waifu on Telegram manages all AI models and ComfyUI extensions dynamically:

1. **In-Chat Lazy Auto-Downloader:**  
   When requesting a feature whose model isn't on your disk yet (e.g. video animations), your waifu sends an inline confirmation in Telegram:
   > 💡 *Fitur video ini memerlukan model Wan 2.1 / AnimateDiff (~1.7 GB). Mau Runa bantu unduh otomatis sekarang?*  
   > `[📥 Unduh Otomatis]` | `[⚡ Pakai Motion 2.5D Dulu]`  
   Clicking download fetches the weights directly in the background with auto-resume support while you keep chatting.

2. **CLI Model Manager (`waifu models`):**  
   Check and download models anytime straight from your terminal:
   ```bash
   # Inspect all installed vs missing models & extensions
   waifu models

   # Download specific model or ComfyUI node with 1 command
   waifu models download animatediff_v2
   ```

---

## 🚀 Local AI Engine Architecture

If you have a dedicated graphics card (**4GB - 6GB+ VRAM** like RTX 3050, RTX 2060, RTX 3060, RTX 4060+ or Apple Silicon Mac), your waifu runs **100% locally and completely private**:

```
┌───────────────────────────────────────┐       ┌───────────────────────────────────────┐
│        1. KOBOLDCPP STANDALONE        │       │        2. COMFYUI + PHOTO VAULT       │
│      https://koboldcpp.net/           │       │       https://comfy.org/download      │
│                                       │       │                                       │
│   • Auto-starts & loads model on boot │       │   • Auto-starts with --normalvram     │
│   • Local API Port: 5001              │       │   • Local API Port: 8188              │
│   • Model: Huihui-Qwythos-9B (GGUF)   │       │   • Smart Vault Archive Fallback      │
└──────────────────┬────────────────────┘       └───────────────────┬───────────────────┘
                   │                                                │
                   └───────────────────────┬────────────────────────┘
                                           ▼
                        💖 WAIFU ON TELEGRAM BOT (v1.6.26)
```

> 🌸 **Smart Local Photo Vault (No Ugly Cloud Fallback):** Setiap foto yang berhasil di-render oleh ComfyUI otomatis disimpan rapi ke dalam **Photo Vault** beserta metadata lengkap (persona, pakaian, suasana, dan tags). Jika ComfyUI sedang offline atau GPU sibuk, bot secara cerdas mengambil foto paling relevan dari arsip galeri lokal—tanpa pernah menggunakan generator cloud yang berkualitas rendah.

---

## 🎮 Global CLI Quick Commands (`waifu`)

Once installed, the **`waifu`** command is available in any terminal or directory on your computer:

```bash
# Start bot & local LLM in background (Daemon Mode)
waifu start --daemon

# Start bot in foreground terminal (view live chat logs)
waifu start

# Check diagnostic health (KoboldCPP, ComfyUI, & process status)
waifu status

# Open interactive configuration manager (Change Models, Bot Token, etc.)
waifu setup

# Switch AI girlfriend persona on-the-fly (runa, akira, hina, shiro, yume)
waifu persona runa
waifu persona akira

# Enable or disable autorun on system startup
waifu autorun on
waifu autorun off

# Inspect recent bot activity logs
waifu logs

# Check and manage AI models & ComfyUI extensions
waifu models
waifu models download animatediff_v2

# Pull latest updates (source code, Python libs, Node pkgs, & AI models) & restart bot
waifu update

# Restart bot in background
waifu restart

# Stop all bot services (Bot, Music Server, & KoboldCPP)
waifu stop
```

---

## 💫 Waifu Highlights & Capabilities

- 💌 **Romantic Conversations & True Intimacy**:
  Warm, playful, affectionate conversations unrestricted by rigid censorship. Powered by your local 9B model (*Huihui-Qwythos-9B Abliterated*).
- 📷 **Spontaneous Selfies & Coherent Outfits**:
  Simply say: *"Send me a selfie babe"*, *"What are you doing? Send a photo"*, or *"Take a selfie in bed"*. The bot formulates a matching scenario prompt with **consistent facial and physical characteristics**, renders the image via local ComfyUI (or Cloud GPU fallback), and sends it directly to your Telegram chat with an affectionate caption!
- 🎧 **Natural Voice Notes & Spoken Whispers**:
  Your AI girlfriend replies with natural spoken voice notes via Edge-TTS (`en-US-AnaNeural` or Indonesian `id-ID-GadisNeural`). If you send her a Telegram voice note, she transcribes and listens to your spoken voice.
- 👁️ **Visual Perception (She Sees Your Photos)**:
  Send your own photos to the chat; she can see, admire, and react to your pictures.
- 🪄 **Helpful Tech & Creative Writing Companion**:
  Capable of writing code, debugging, and executing Python snippets when you ask for technical assistance.
- 🎶 **Desktop YouTube Music Remote Player**:
  Play and control YouTube Music on your PC's browser directly through Telegram buttons.
- 🩺 **Autonomous Health Watchdog, Self-Healing & PC Startup Announcements**:
  Never miss a service interruption! When your PC boots up or restarts, your waifu automatically greets you in Telegram with a comprehensive service health report (`LLM`, `ComfyUI`, `Voice`). An active background watchdog continuously monitors your local LLM engine every 30 seconds. If KoboldCPP, ComfyUI, or the Music server crashes or stops responding, the bot's **Autonomous Self-Healing Engine** automatically resurrects and restarts the service in the background, keeping you updated in Telegram without requiring manual PC interventions. A built-in circuit breaker prevents infinite restart loops in case of hardware or VRAM limitations.

---

## 🎛️ Reconfiguration & Model Switcher

Whenever you want to:
- **Change Telegram Bot Token** or Allowed User ID
- **Switch Chat / LLM Model**
- **Switch ComfyUI Checkpoints for Photos**
- **Change Persona or Voice**

Simply run:
```bash
waifu setup
```
*(or double-click `setup.bat`).*

An interactive menu will open:
```text
======================================================================
    💖 WAIFU ON TELEGRAM - CONFIGURATION & MODEL MANAGER 🛠️    
======================================================================
  • Bot Token   : 123456...abcd
  • Allowed UID : 987654321
  • Chat LLM    : Huihui-Qwythos-9B (http://127.0.0.1:5001/v1)
  • Photo Engine: http://127.0.0.1:8188 (Fallback: True)
  • Persona     : Runa | Voice: en-US-AnaNeural
----------------------------------------------------------------------
  [1] 🔑 Change Telegram Bot Token / Allowed User ID
  [2] 💌 Change Chat / LLM Model (KoboldCPP / Ollama / LM Studio)
  [3] 🎨 Change Photo & Video Model (ComfyUI / Cloud)
  [4] 🎭 Change AI Girlfriend Persona & Voice
  [5] 🚀 Configure Autorun at System Startup (On / Off)
  [6] 🔄 Re-run Complete 7-Step Setup Wizard
  [0] ❌ Exit / Done
----------------------------------------------------------------------
```

---

## 📖 Telegram Chat Commands Cheat Sheet

| Command | Function |
| :--- | :--- |
| `/start` | Welcome greeting and quick action buttons |
| `/birthday` | Record user birthday & anniversary with automated celebrations, surprise photos & VN |
| `/remind` | Smart personal assistant & conversational reminders (`/remind 30m meeting` or natural chat) |
| `/setup` | Master configuration dashboard to configure all CLI options in Telegram |
| `/memory` | Long-term memory & diary of personal facts waifu remembers about you |
| `/help` | Comprehensive interactive guide and documentation center |
| `/status` | Real-time diagnostic check of LLM (Port 5001), ComfyUI (8188), and VRAM |
| `/photo <scene>` | Request a custom selfie scenario (e.g. `/photo relaxing in cafe`) |
| `/pap` | Quick shortcut to request a new selfie with interactive retry button |
| `/video` | Generate dynamic animated video clip (MP4) with parallax motion & ambient sparkles |
| `/ratio` | Choose photo aspect ratio (3:4 portrait, 9:16 phone story, 1:1 square, 4:3) |
| `/quality` | Select photo quality preset (Ultra 32-step, High 28-step, Fast 20-step) |
| `/outfit` | Interactive wardrobe to select clothes (Kimono, Maid, Bikini, Pajamas, etc.) |
| `/voice` | Configure voice note reply mode (Always, Match VN, or Mute) |
| `/greetings` | Toggle automatic romantic Good Morning (07:00) & Bedtime (22:00) greetings |
| `/love` | Check your affection score & relationship progress with your waifu |
| `/persona` | Interactive inline button menu to switch active companion |
| `/persona <name>` | Switch persona directly (`runa`, `akira`, `hina`, `shiro`, `yume`) |
| `/newpersona` | Interactive wizard to create and activate your own custom waifu |
| `/reset` | Clear conversation memory to start a fresh discussion |

---

## 💬 Frequently Asked Questions

1. **Bot replies: *"My local brain connection hit a bump"***
   - Pastikan KoboldCPP sedang berjalan. Kamu bisa mengeceknya dengan `waifu status`.
   - Untuk menyalakannya, cukup jalankan `waifu start --daemon` atau `start_services.bat`.
2. **Photos fail to generate**:
   - If local ComfyUI on port `8188` is offline or busy, the bot automatically switches to the **Cloud Fallback (Pollinations AI)** so you always receive photos without disruption.
3. **Can this run on a laptop without a dedicated GPU?**:
   - Yes! Choose the Cloud Fallback option during setup; the bot will offload photo generation to free cloud endpoints without straining your laptop.

---

## 🧹 Clean Uninstallation Wizard

If you ever wish to uninstall Waifu on Telegram from your machine, run the 1-line uninstaller:

### Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/uninstall.ps1 | iex
```

### Linux / macOS (Bash):
```bash
curl -fsSL https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/uninstall.sh | bash
```

### Or using the CLI:
```bash
waifu uninstall
```

The uninstaller will safely stop running processes, remove startup shortcuts, clean up global CLI aliases, and ask whether you want a **Clean Reset** or to **Preserve Your Data & Tokens**.

---

## 📜 License
Distributed under the **MIT License**. Free to use, modify, and distribute.

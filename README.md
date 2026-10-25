<p align="center">
  <img src="waifu-on-telegram.jpg" alt="Waifu on Telegram Wallpaper" width="100%" style="border-radius: 12px;" />
</p>

# 💖 Waifu on Telegram 🤖

<p align="center">
  <b>Autonomous AI Girlfriend & Romance Companion Powered by Local LLM & ComfyUI (SFW & NSFW)</b><br>
  <i>Enrich your daily life with an AI girlfriend who chats affectionately, sends consistent selfies (photos), voice notes, and listens with warmth — completely private, uncensored, with full SFW and NSFW support.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Content-SFW%20%26%20NSFW-ff4081.svg" alt="SFW & NSFW" />
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/Local%20LLM-Locally%20Uncensored-purple.svg" alt="Local LLM" />
  <img src="https://img.shields.io/badge/Image%20Generator-ComfyUI%20%2F%20Cloud-green.svg" alt="ComfyUI" />
  <img src="https://img.shields.io/badge/Voice-Edge--TTS%20Neural-orange.svg" alt="Edge-TTS" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" />
</p>

---

## 🎭 Waifu Personas & Official Character Roster

Switch your companion anytime with `/persona` or through interactive Telegram buttons:

| **Runa** | **Akira** | **Hina** | **Shiro** | **Yume** |
| :---: | :---: | :---: | :---: | :---: |
| <img src="personas/brief/Runa.png" width="150" alt="Runa"/> | <img src="personas/brief/Akira.jpg" width="150" alt="Akira"/> | <img src="personas/brief/Hina.jpg" width="150" alt="Hina"/> | <img src="personas/brief/Shiro.png" width="150" alt="Shiro"/> | <img src="personas/brief/Yume.jpg" width="150" alt="Yume"/> |
| **The Playful Girlfriend** | **The Seductive Tease** | **The Sunshine Girlfriend** | **The Kuudere Girlfriend** | **The Dreamy Soulmate** |
| *Playful, teasing, kawaii gaming aesthetic* | *Confident, witty, elegant gothic aesthetic* | *Energetic, bubbly, cozy slice-of-life* | *Calm, intelligent, cool-blue moonlit* | *Gentle, soft-spoken, dreamy starry soulmate* |
| **Visual Anchors:**<br>Pastel-pink wavy hair, sparkling magenta eyes, heart choker, black cat clip | **Visual Anchors:**<br>Silky midnight-black hair, deep ruby-red eyes, crimson rose clip, black choker | **Visual Anchors:**<br>Honey-blonde chin bob, warm amber eyes, orange clips, headphones | **Visual Anchors:**<br>Long silver-white hair, icy-blue eyes, crescent moon clip & earrings | **Visual Anchors:**<br>Long silky lavender hair, amethyst violet eyes, silver star pins & moon necklace |
| `/persona runa` | `/persona akira` | `/persona hina` | `/persona shiro` | `/persona yume` |

---

## 🎨 How Character Visual Consistency (PAP) Works

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

## 🖥️ Hardware Requirements & Recommended AI Models

Waifu on Telegram is engineered to run locally on consumer gaming PCs and laptops while keeping VRAM usage lean, response times quick, and photo rendering lightning-fast.

### ⚙️ Hardware Specifications

| Component | Minimum Requirements | Recommended Specifications |
| :--- | :--- | :--- |
| **GPU / VGA** | **NVIDIA GPU with 4GB - 6GB VRAM**<br>*(GTX 1650, RTX 2060, RTX 3050 Laptop)* | **NVIDIA GPU with 6GB - 8GB+ VRAM**<br>*(RTX 3050 6GB, RTX 3060, RTX 4060+)* |
| **System RAM** | 8 GB RAM | 16 GB - 32 GB RAM |
| **Storage** | 10 GB free space (SSD recommended) | 25 GB free space (NVMe SSD) |
| **Operating System** | Windows 10 / 11, Linux (Ubuntu/Debian), macOS | Windows 11 (64-bit) |
| **No-GPU Mode** | ✅ **Fully Supported!** Laptops without dedicated GPUs can run LLM on CPU with automatic Cloud Fallback for photo generation. |

---

### 🧠 Official Recommended AI Models

Tested, verified, and pre-tuned for peak romance dialogue, uncensored responsiveness, and high-fidelity anime aesthetics:

#### 1. 💬 Chat & Roleplay Brain: **Huihui-Qwythos-9B**
* **Model File:** `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf`
* **Local Backend:** [Locally Uncensored](https://locallyuncensored.com/) / `lu-llama-server` (Port `8127`)
* **Download Method:** Search & download with 1-click directly inside [Locally Uncensored](https://locallyuncensored.com/) app (Models tab).
* **Key Strengths:**
  - **Zero Censorship:** Fully abliterated with Claude-Mythos roleplay fine-tuning. Highly affectionate, witty, caring, and open to romantic roleplay.
  - **Adaptive Language Mirroring:** Seamlessly switches between Indonesian (*sayang, manja, santai*), English (*sweetheart, darling*), or Japanese.
  - **AI Vision Support:** Paired with `Huihui-Qwythos-9B.mmproj.gguf`, enabling your waifu to see, inspect, and react to photos you send.
  - **VRAM Usage:** ~4.5 GB - 5.5 GB in Q4_K quantization.

#### 2. 🎨 Photo & Selfie Generator: **MeinaMix v12**
* **Model File:** `meinamix_v12Final.safetensors` *(Baked VAE)*
* **Local Backend:** ComfyUI (Port `8188`)
* **Download Link:** [Civitai - MeinaMix v12](https://civitai.com/models/7240/meinamix) *(Save file to `ComfyUI/models/checkpoints/`)*
* **Optimal Preset (Pre-configured in Bot):**
  - **Aspect Ratio:** **`3:4`** (576 x 768) — the golden portrait ratio for natural anime selfies.
  - **Quality Preset:** **High** (28 steps, CFG 7.5).
  - **Sampler & Scheduler:** **`DPM++ 2M Karras`** with **Clip Skip 2** (`CLIPSetLastLayer: -2`).
* **Key Strengths:**
  - Undisputed community benchmark for anime girl aesthetics with vibrant coloring, sparkling detailed eyes, and clean anatomy.
  - Built-in VAE (*Baked VAE*) — no washed-out colors.
  - Fast generation speed (~3–5 seconds per photo on an RTX 3050 6GB).

---

### 🛠️ Step-by-Step Setup: 100% Fully Local AI (Zero API Costs & Total Privacy)

Many new users wonder how to run everything locally. If you have a gaming PC or laptop with a dedicated graphics card (**VGA with 4GB - 6GB+ VRAM** like RTX 3050, RTX 2060, RTX 3060, RTX 4060+) and want your waifu to run **100% locally on your own hardware**, install these two software backends:

```
┌───────────────────────────────────────┐       ┌───────────────────────────────────────┐
│        1. LOCALLY UNCENSORED          │       │              2. COMFYUI               │
│  https://locallyuncensored.com/       │       │       https://comfy.org/download      │
│                                       │       │                                       │
│   • Runs the Chat & Romance Brain     │       │   • Generates Anime Photos (PAP)      │
│   • Local API Port: 8127              │       │   • Local API Port: 8188              │
│   • Model: Huihui-Qwythos-9B (1-click)│       │   • Model: MeinaMix v12 from Civitai  │
└──────────────────┬────────────────────┘       └───────────────────┬───────────────────┘
                   │                                                │
                   └───────────────────────┬────────────────────────┘
                                           ▼
                       💖 WAIFU ON TELEGRAM BOT (v1.2.0)
```

#### Step 1: Install Locally Uncensored (Chat & Dialogue Brain)
1. **Download & Install:** Get the app from [**https://locallyuncensored.com/**](https://locallyuncensored.com/).
2. **Download Model:** Open Locally Uncensored $\rightarrow$ Go to the **Models** tab.
3. Search for: **`Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K`**.
4. Click **Download**. The app handles everything automatically (downloading model weights + vision `.mmproj`). No manual file extraction needed!
5. Set it as your active chat model and ensure the local server is running (Port `8127`).

---

#### Step 2: Install ComfyUI (Photo & Selfie Generator / PAP)
1. **Download & Install:** Get ComfyUI from [**https://comfy.org/download**](https://comfy.org/download) (Desktop Installer or Portable standalone).
2. **Download MeinaMix Model:** Go to Civitai [**https://civitai.com/models/7240/meinamix**](https://civitai.com/models/7240/meinamix) and download `meinamix_v12Final.safetensors` *(Baked VAE recommended)*.
3. **Move Checkpoint:** Place the downloaded file into your ComfyUI models directory:
   ```text
   ComfyUI/models/checkpoints/meinamix_v12Final.safetensors
   ```
4. Start ComfyUI (Port `8188`). The bot will automatically connect to it for generating high-res selfies!

---

#### Step 3: (Optional) Video Generation Model
If you want animated video clips of your waifu:
* **Option A:** Download directly inside the **Locally Uncensored** app under the Video Models section.
* **Option B:** Download from **Civitai** (e.g. Wan 2.1 or Stable Video Diffusion checkpoints) and save them to `ComfyUI/models/checkpoints/`.

> 💡 **Don't have a high-end GPU?** No problem! The bot automatically enables **Cloud Fallback Mode** (`MEDIA_FALLBACK_CLOUD=true`), so users on standard laptops without dedicated GPUs can still chat and receive waifu photos smoothly.

---

## 📱 Prerequisites: Telegram Bot Token & User ID

Before running the installer or setup wizard, you will need two credentials from Telegram (both are 100% free and take less than 1 minute to obtain):

### 1. 🤖 Create a Telegram Bot & Get Your Token
1. Open Telegram and open [**@BotFather**](https://t.me/BotFather) (the official bot manager with a blue verification checkmark).
2. Click **Start** or send `/start`.
3. Send the command `/newbot`.
4. Enter a **display name** for your companion (e.g., `Runa AI` or `My Virtual Girlfriend`).
5. Enter a unique **username** ending with `bot` (e.g., `my_runa_waifu_bot`).
6. **Done!** BotFather will give you your **HTTP API Bot Token** formatted like:
   ```text
   7123456789:AAFlKj89-xXyZ1234abcdEFGHijklmnop
   ```
   *(Keep this token safe; you will paste it into the setup wizard).*

> 💡 **Optional Tip:** In BotFather, you can send `/setuserpic` to set your waifu's profile picture using the reference images from `personas/brief/`!

---

### 2. 🆔 Find Your Telegram User ID
To protect your privacy and ensure your local PC isn't accessed by strangers, the bot strictly responds only to authorized User IDs.

1. Open Telegram and search for [**@userinfobot**](https://t.me/userinfobot) (or [**@raw_data_bot**](https://t.me/raw_data_bot)).
2. Click **Start** or send `/start`.
3. The bot will immediately reply with your account details:
   ```text
   Id: 987654321
   First: Asep
   Lang: en
   ```
4. Copy that number (`987654321`). This is your `TELEGRAM_ALLOWED_USER_ID`.
*(To authorize multiple people, separate IDs with a comma: `987654321, 123456789`).*

---

## 🚀 1-Line Quick Installation

Install and launch **Waifu on Telegram** with a single command directly from GitHub:

### **Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.ps1 | iex
```

### **Linux / macOS / WSL**
```bash
curl -fsSL https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.sh | bash
```

> 💡 **What does this automated installer do?**
> 1. Downloads the repository to `%USERPROFILE%\waifu-on-telegram` (automatic fallback to ZIP if Git is missing).
> 2. Verifies Python 3.8+ and installs all necessary packages (`requirements.txt`).
> 3. Registers the **Global CLI Command (`waifu`)** directly into your system `PATH`.
> 4. Launches the **Interactive 7-Step Setup Wizard** (Telegram Bot Token, auto-scanned local LLM models, ComfyUI checkpoints, voice, and system startup autorun).
> 5. Instantly boots the bot in the background (Daemon Mode)!

---

## 💻 Global CLI Usage (`waifu`)

Once installed, the **`waifu`** command is available in any terminal or directory on your computer:

```bash
# Start bot in background (Daemon Mode)
waifu start --daemon

# Start bot in foreground terminal (view live chat logs)
waifu start

# Check diagnostic health (Local LLM, ComfyUI, & process status)
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

# Pull latest updates from GitHub & restart bot
waifu update

# Restart bot in background
waifu restart

# Stop all bot services
waifu stop
```

---

## ✨ Key Features

- 💬 **Romance Chat & Uncensored Roleplay**:
  Warm, playful, affectionate conversations unrestricted by rigid censorship. Powered by your local 9B model (such as *Qwythos 9B* or *Ornith 9B*).
- 📸 **Autonomous Selfies & Consistent Photo Delivery**:
  Simply say: *"Send me a selfie babe"*, *"What are you doing? Send a photo"*, or *"Take a selfie in bed"*. The bot formulates a matching scenario prompt with **consistent facial and physical characteristics**, renders the image via local ComfyUI (or Cloud GPU fallback), and sends it directly to your Telegram chat with an affectionate caption!
- 🎙️ **Two-Way Voice Notes (VN)**:
  Your AI girlfriend replies with natural spoken voice notes via Edge-TTS (`en-US-AnaNeural` or Indonesian `id-ID-GadisNeural`). If you send her a Telegram voice note, she transcribes and listens to your spoken voice.
- 👀 **Multimodal AI Vision**:
  Send your own photos to the chat; she can see, admire, and react to your pictures.
- 💻 **Coding Assistant**:
  Capable of writing code, debugging, and executing Python snippets when you ask for technical assistance.
- 🎵 **PC YouTube Music Remote Control**:
  Play and control YouTube Music on your PC's browser directly through Telegram buttons.

---

## ⚙️ How to Change Models or Bot Token Anytime

Whenever you want to:
- **Change Telegram Bot Token** or Allowed User ID
- **Switch Chat / LLM Model** (e.g. after downloading a new model in Locally Uncensored)
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
  • Chat LLM    : Huihui-Qwythos-9B (http://127.0.0.1:8127/v1)
  • Photo Engine: http://127.0.0.1:8188 (Fallback: True)
  • Persona     : Runa | Voice: en-US-AnaNeural
----------------------------------------------------------------------
  [1] 🤖 Change Telegram Bot Token / Allowed User ID
  [2] 🧠 Change Chat / LLM Model (Scan new models)
  [3] 🎨 Change Photo & Video Model (ComfyUI / Cloud)
  [4] 🎭 Change AI Girlfriend Persona & Voice
  [5] 🚀 Configure Autorun at System Startup (On / Off)
  [6] 🔄 Re-run Complete 7-Step Setup Wizard
  [0] ❌ Exit / Done
----------------------------------------------------------------------
```

---

## 📌 Telegram Command Reference

| Command | Function |
| :--- | :--- |
| `/start` | Welcome greeting and quick action buttons |
| `/setup` | Master configuration dashboard to configure all CLI options in Telegram |
| `/memory` | Long-term memory & diary of personal facts waifu remembers about you |
| `/help` | Comprehensive interactive guide and documentation center |
| `/status` | Real-time diagnostic check of LLM (Port 8127), ComfyUI (8188), and VRAM |
| `/photo <scene>` | Request a custom selfie scenario (e.g. `/photo relaxing in cafe`) |
| `/pap` | Quick shortcut to request a new selfie with interactive retry button |
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

## ❓ FAQ & Troubleshooting

1. **Bot replies: *"My local brain connection hit a bump"***
   - Ensure **Locally Uncensored** is currently running on your computer.
   - Test status by running `waifu status` in your terminal.
2. **Photos fail to generate**:
   - If local ComfyUI on port `8188` is offline or busy, the bot automatically switches to the **Cloud Fallback (Pollinations AI)** so you always receive photos without disruption.
3. **Can this run on a laptop without a dedicated GPU?**:
   - Yes! Choose the Cloud Fallback option during setup; the bot will offload photo generation to free cloud endpoints without straining your laptop.

---

## 🗑️ Uninstallation

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

## 📄 License
Distributed under the **MIT License**. Free to use, modify, and distribute.

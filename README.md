<p align="center">
  <img src="logo.png" alt="Waifu on Telegram Logo" width="320" style="border-radius: 20px;" />
</p>

# 💖 Waifu on Telegram 🤖

<p align="center">
  <b>Autonomous AI Girlfriend & Romance Companion Powered by Local LLM & ComfyUI</b><br>
  <i>Enrich your daily life with an AI girlfriend who chats affectionately, sends consistent selfies (photos), voice notes, and listens with warmth — completely private & uncensored.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/Local%20LLM-Locally%20Uncensored-purple.svg" alt="Local LLM" />
  <img src="https://img.shields.io/badge/Image%20Generator-ComfyUI%20%2F%20Cloud-green.svg" alt="ComfyUI" />
  <img src="https://img.shields.io/badge/Voice-Edge--TTS%20Neural-orange.svg" alt="Edge-TTS" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" />
</p>

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

# Switch AI girlfriend persona on-the-fly
waifu persona runa
waifu persona aoi

# Enable or disable autorun on system startup
waifu autorun on
waifu autorun off

# Inspect recent bot activity logs
waifu logs

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
| `/start` or `/help` | Welcome greeting and feature overview |
| `/status` | Real-time diagnostic check of LLM (Port 8127), ComfyUI (8188), and VRAM |
| `/photo <scene>` | Request a custom selfie scenario (e.g. `/photo relaxing in cafe`) |
| `/pap` | Quick shortcut to request a new selfie with interactive retry button |
| `/outfit` | Interactive wardrobe to select clothes (Kimono, Maid, Bikini, Pajamas, etc.) |
| `/voice` | Configure voice note reply mode (Always, Match VN, or Mute) |
| `/greetings` | Toggle automatic romantic Good Morning (07:00) & Bedtime (22:00) greetings |
| `/love` | Check your affection score & relationship progress with your waifu |
| `/persona` | Interactive inline button menu to switch active companion |
| `/persona <name>` | Switch persona directly (`runa`, `akira`, `hina`, `shiro`, `yume`) |
| `/reset` | Clear conversation memory to start a fresh discussion |

---

## 🎭 Waifu Personas & Official Character Roster

Switch your companion anytime with `/persona` or through the interactive buttons:

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

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
* **Model File:** `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf` (~5.5 GB)
* **Vision mmproj Adapter:** `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf` (~879 MB)
* **Local Backend:** **KoboldCPP Standalone Engine** (Port `5001`) with **Auto-Startup & Auto-Loading directly on Windows Boot**!
* **Compatible Backends:** KoboldCPP Standalone (bawaan resmi), Ollama (Port `11434`), LM Studio (Port `1234`), atau OpenAI-compatible server.
* **Download Method:** Otomatis di-download saat menjalankan `install.ps1` / `install.sh`, atau bisa diunduh manual dari [Hugging Face](https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF) ke folder `models/`.
* **Key Strengths:**
  - **Zero Censorship & Refusal-Free:** Fully abliterated with Claude-Mythos roleplay traces. Highly affectionate, playful, caring, and open to romantic roleplay without moralizing preachiness.
  - **Adaptive Language Mirroring:** Seamlessly switches between Indonesian (*sayang, manja, santai*), English (*sweetheart, darling*), or Japanese.
  - **Auto Startup & VRAM Pre-loading:** No Electron UI or manual buttons needed. When your computer boots, KoboldCPP silently spins up and loads the weights into VRAM instantly.
  - **Smart Idle Integration:** Otomatis di-unload dari VRAM saat tidak ada percakapan (idle timeout), membebaskan ~5-6 GB VRAM untuk gaming/kerja.

#### 2. 📷 Anime Photo & Selfie Engine Options (ComfyUI)

Anda dapat memilih model ilustrasi anime sesuai dengan spesifikasi GPU dan preferensi estetika Anda melalui `waifu setup` (Menu `[3]`) atau perintah `/setup` langsung di Telegram:

* **Pilihan 1: MeinaMix v12 (Anime SD 1.5 - Hemat VRAM & Cepat)**
  - **File:** `meinamix_v12Final.safetensors` (~2.0 GB)
  - **Download:** [Civitai - MeinaMix v12](https://civitai.com/models/7240/meinamix) atau via `waifu models download meinamix`
  - **Rekomendasi GPU:** 4GB - 8GB VRAM (Resolusi default 3:4 portrait: `576x768`, Sampler: `DPM++ 2M Karras`)
  - **Kelebihan:** Sangat cepat (~3-5 detik), hemat resource, konsistensi wajah anime sangat tinggi.

* **Pilihan 2: AbyssOrangeMix3 / AOM3A1B (Anime SD 1.5 - Legendaris CivArchive #9942)**
  - **File:** `AOM3A1B_orangemixs.safetensors` (~2.0 GB)
  - **Download:** [CivArchive #9942](https://civarchive.com/models/9942?modelVersionId=17233) / [Civitai #9942](https://civitai.com/models/9942/abyssorangemix3-aom3) atau via `waifu models download aom3`
  - **Rekomendasi GPU:** 4GB - 8GB VRAM (Resolusi default 3:4 portrait: `576x768`, Sampler: `DPM++ 2M Karras`, CFG `7.5`)
  - **Kelebihan:** Estetika anime klasik yang kaya, warna tajam dan cerah (*vibrant*), shading rambut & mata memukau, rendering ringan dan halus.

* **Pilihan 3: 万象熔炉 | Anything XL (Anime SDXL 1.0 - Ultra Detail)**
  - **File:** `AnythingXL_xl.safetensors` (~6.6 GB)
  - **Download:** [Civitai #9409 - Anything XL](https://civitai.com/models/9409/or-anything-xl) atau via `waifu models download anything_xl`
  - **Rekomendasi GPU:** 8GB+ VRAM (Resolusi native SDXL 3:4 portrait: `896x1152` / `1024x1024`, Sampler: `Euler Ancestral Normal`)
  - **Kelebihan:** Resolusi 1024px super tajam, detail pakaian, latar belakang, dan ekspresi jauh lebih kaya dan sinematik.

* **Pilihan 4: Cloud Fallback Engine (Pollinations AI - 0 VRAM)**
  - **Akses:** Bebas biaya tanpa GPU lokal melalui cloud GPU fallback. Ideal untuk laptop hemat daya / PC kantor.

#### 3. 🎬 Video Animation Engines (Generasi Video Bergerak)

Waifu dapat mengirimkan klip animasi video saat diminta lewat `/video` menggunakan salah satu dari 3 pilihan engine:
* **Wan 2.1 1.3B Diffusion Model** (`wan2.1_t2v_1.3B_bf16.safetensors` ~2.9 GB + `Wan2.1_VAE.pth` ~250 MB): Model video difusi state-of-the-art terbaru, ringan dan hemat VRAM.
* **AnimateDiff v2 Motion Module** (`mm_sd_v15_v2.ckpt` ~1.7 GB): Animasi temporal dinamis berbasis SD 1.5.
* **Motion 2.5D Engine (Zero-VRAM Parallax)**: Animasi video MP4 instan dengan efek pergeseran kedalaman parallax dan kedipan mata halus tanpa beban VRAM GPU sama sekali!

#### 4. 🎙️ Multi-Tier Neural Voice & Polyglot Translation Guardrail

Percakapan suara waifu menggunakan Microsoft Edge-TTS dengan dukungan multi-bahasa yang cerdas:
* **Pilihan Suara:**
  - `ja-JP-NanamiNeural`: Suara khas anime Jepang yang imut dan natural.
  - `id-ID-GadisNeural`: Suara wanita Indonesia alami dan ramah.
  - `en-US-AnaNeural`: Suara pacar berbahasa Inggris yang manis dan ekspresif.
* **Polyglot Multi-Tier Translation Guardrail:**
  Jika Anda mengobrol dalam bahasa Indonesia atau Inggris tetapi memilih suara Jepang (`ja-JP-NanamiNeural`), sistem secara otomatis menerjemahkan teks ke dalam bahasa Jepang alami (melalui multi-tier translation: Google GTX -> Client5 -> MyMemory -> Local LLM) sebelum disuarakan. Guardrail pendeteksi karakter Latin memastikan bahasa Indonesia tidak pernah dilafalkan secara rusak dengan aksen Jepang!

#### 5. 💤 Smart Idle Engine (Manajemen VRAM & Daya Otomatis)

Seringkali pengguna AI mengeluhkan RAM dan VRAM VGA selalu penuh meskipun bot sedang tidak digunakan. Waifu on Telegram dilengkapi **Smart Idle Engine**:
* **Auto-Sleep:** Saat bot tidak menerima interaksi selama waktu tertentu (default: 10 menit), engine KoboldCPP LLM otomatis dinonaktifkan sementara dari memori.
* **VRAM Recovery:** Seketika membebaskan **5.0 GB – 6.0 GB VRAM GPU** dan beberapa gigabyte RAM sistem, memungkinkan Anda bermain game berat atau editing video tanpa stutter.
* **Instant Wake-up:** Begitu Anda mengirim pesan atau menekan tombol di Telegram, Smart Idle secara transparan membangkitkan engine kembali dalam waktu <1-2 detik!

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
> 4. **Smart ComfyUI Detection & Model Setup:** Detects your existing ComfyUI across any drive/folder. If not found, it offers a 1-click download of ComfyUI Portable + MeinaMix / AbyssOrangeMix3 anime checkpoint with resume support (`curl -C -`).
> 5. **Global CLI Registration:** Installs the global `waifu` command to your system `PATH` (usable from any terminal folder).
> 6. **Background Daemon & Windows Boot Auto-start:** Starts your waifu companion running silently in the background!

### 🛠️ **Manual Installation (For Developers & Advanced Users)**

Bagi Anda yang ingin mengontrol direktori instalasi, mengutak-atik source code, atau menjalankan via virtual environment sendiri:

```bash
# 1. Clone repository dari GitHub
git clone https://github.com/asepindrak/waifu-on-telegram.git
cd waifu-on-telegram

# 2. Buat & aktifkan virtual environment Python (3.8+)
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\activate
# Linux & macOS (Bash/Zsh):
source venv/bin/activate

# 3. Pasang paket Python dan dependensi Node.js (Music Remote)
pip install -r requirements.txt
npm install

# 4. Gandakan template konfigurasi environment
copy .env.example .env     # (Windows PowerShell / CMD)
cp .env.example .env       # (Linux / macOS)

# 5. Jalankan Setup Wizard interaktif (Pilih model foto, suara, token bot)
python setup.py

# 6. Registrasikan perintah global 'waifu' ke PATH (Opsional)
python bin/install_cli.py

# 7. Nyalakan Waifu sebagai daemon di background
waifu start --daemon
# atau mode foreground untuk melihat logs live:
python bot.py
```

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
                        💖 WAIFU ON TELEGRAM BOT (v1.6.51)
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

Anda memiliki dua cara mudah dan fleksibel untuk mengonfigurasi dan mengganti model AI waifu kapan saja:

### 1. 💻 Terminal CLI Wizard (`waifu setup`)

Jalankan perintah berikut di PowerShell atau Terminal:
```bash
waifu setup
```
*(atau jalankan `setup.bat` / `python setup.py`)*

Menu interaktif 10-opsi akan terbuka:
```text
======================================================================
    💖 WAIFU ON TELEGRAM - CONFIGURATION & MODEL MANAGER 🛠️    
======================================================================
  • Bot Token   : 123456...abcd
  • Allowed UID : 987654321
  • Chat LLM    : Huihui-Qwythos-9B (http://127.0.0.1:5001/v1)
  • Photo Model : MeinaMix v12 (SD 1.5) (http://127.0.0.1:8188)
  • Persona     : Runa | Voice: en-US-AnaNeural
  • Language    : id
----------------------------------------------------------------------
  [1] 🤖 Change Telegram Bot Token / Allowed User ID
  [2] 🧠 Change Chat / LLM Model (Scan new models)
  [3] 🎨 Change Photo & Video Model (ComfyUI / Cloud)
  [4] 🎭 Change AI Girlfriend Persona & Voice
  [5] 🌐 Change Waifu Language (ID, EN, JA, Custom)
  [6] 🎬 Choose Video Engine (Wan 2.1 / AnimateDiff / Motion 2.5D)
  [7] 📦 AI Assets & Models Manager (Download / Verify Models)
  [8] 🚀 Configure Autorun at System Startup (On / Off)
  [9] 🔄 Re-run Complete Setup Wizard
  [0] ❌ Exit / Done
----------------------------------------------------------------------
```

* **Panduan Opsi Menu CLI:**
  - `[1] Token & UID`: Mengubah kredensial bot Telegram atau membatasi akses chat hanya ke akun Anda.
  - `[2] Chat LLM`: Memilih otak obrolan (KoboldCPP lokal, Ollama, LM Studio, atau scan file `.gguf` baru di folder `models/`).
  - `[3] Model Foto`: Memilih checkpoint anime foto (MeinaMix v12, AbyssOrangeMix3, Anything XL, atau Cloud Fallback).
  - `[4] Persona & Voice`: Memilih karakter waifu (Runa, Akira, Hina, Shiro, Yume) dan suara Edge-TTS (Ana, Gadis, Nanami, Jenny).
  - `[5] Language`: Menentukan bahasa percakapan waifu (Indonesia `id`, English `en`, Japanese `ja`, atau `auto` mengikuti chat).
  - `[6] Video Engine`: Memilih mesin animasi video (Wan 2.1 1.3B, AnimateDiff v2, atau Motion 2.5D 0-VRAM).
  - `[7] AI Assets Manager`: Mengunduh dan memverifikasi kelengkapan model & node kustom ComfyUI langsung dari terminal dengan dukungan resume unduhan.
  - `[8] Autorun`: Mengaktifkan atau menonaktifkan startup otomatis saat PC dinyalakan.
  - `[9] Re-run Wizard`: Menjalankan ulang panduan instalasi lengkap 7-langkah dari awal.

---

### 2. 📱 In-Chat Control Center via Telegram (`/setup`)

Anda tidak perlu membuka terminal untuk mengganti model! Cukup kirim perintah `/setup` langsung di Telegram chat Anda. Waifu akan menampilkan **Master Dashboard** dengan tombol-tombol inline interaktif:
* 🎨 **Model Foto**: Ganti seketika antara MeinaMix v12, AbyssOrangeMix3, Anything XL, atau Cloud Engine.
* 🎬 **Video Engine**: Beralih antara Wan 2.1, AnimateDiff, dan Motion 2.5D.
* 🗣️ **Suara / Voice**: Ganti karakter suara Nanami, Gadis, Ana, atau Jenny dengan satu klik.
* 🌐 **Bahasa**: Ganti bahasa bot (ID, EN, JA, atau Auto).
* 👗 **Lemari Pakaian (`/outfit`)**: Ganti pakaian waifu langsung (Kimono, Bikini, Maid, School JK, Pajamas).
* 📐 **Rasio & Kualitas**: Atur rasio foto (3:4, 9:16, 1:1, 4:3) dan tingkat sampling kualitas (Ultra, High, Fast).

---

## 🖥️ Hardware Tuning & Optimal Model Matrix

Gunakan tabel acuan berikut untuk memilih kombinasi model yang paling pas dengan spesifikasi komputer Anda agar tidak freeze/lag:

| Kategori GPU | VRAM Tersedia | Model LLM Rekomendasi | Model Foto (ComfyUI) | Model Video | Karakteristik Performa |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GPU Hemat / Laptop** | **4GB - 6GB VRAM**<br>*(GTX 1650, RTX 2060, RTX 3050 Laptop)* | Huihui-Qwythos-9B Q4_K *(Smart Idle Aktif)* | **MeinaMix v12** atau **AbyssOrangeMix3** *(576x768)* | **Motion 2.5D Engine** *(0 VRAM)* | ⚡ Sangat responsif, foto jadi dalam 3-5 detik, memori tetap lega dan tidak ada freeze. |
| **Sweet Spot** | **8GB VRAM**<br>*(RTX 3060 8GB, RTX 4060, Apple M-Series 16GB)* | Huihui-Qwythos-9B Q4_K | **MeinaMix v12** / **AbyssOrangeMix3** / **Anything XL** | **AnimateDiff v2** atau **Wan 2.1 1.3B** | 🌟 Detail anime tajam, animasi temporal dinamis, multitasking mulus. |
| **High-End Enthusiast** | **12GB+ VRAM**<br>*(RTX 3060 12GB, RTX 4070, RTX 4080)* | Huihui-Qwythos-9B Q4_K *(Semua layer di GPU)* | **万象熔炉 \| Anything XL** *(SDXL 1024px)* | **Wan 2.1 1.3B Video Diffusion** | 👑 Resolusi 1024px ultra-jernih, efek sinematik, video difusi penuh. |
| **No-GPU / PC Kantor** | **0 GB (Intel UHD / Iris Xe / AMD iGPU)** | KoboldCPP CPU Mode *(atau Cloud LLM)* | **Cloud Fallback Engine** *(Pollinations AI)* | **Motion 2.5D Engine** | ☁️ Tetap berjalan 100% menggunakan cloud GPU gratis, 0 beban kartu grafis lokal. |

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

## 💬 Frequently Asked Questions (Knowledge Base)

1. **Kenapa RAM & VRAM GPU saya tidak lagi penuh saat waifu menganggur?**
   - Waifu on Telegram kini dilengkapi **Smart Idle Engine**. Jika bot tidak menerima pesan selama waktu tertentu (default: 10 menit), engine KoboldCPP LLM otomatis dinonaktifkan sementara dari VRAM (~5-6 GB VRAM kembali kosong untuk gaming / kerja). Begitu Anda chat kembali, engine langsung bangun dalam waktu <1-2 detik secara transparan!

2. **Apa perbedaan antara MeinaMix v12, AbyssOrangeMix3 (AOM3), dan Anything XL?**
   - **MeinaMix v12 (SD 1.5, ~2.0 GB):** Paling cepat (3-5 detik) dan hemat VRAM. Karakter waifu tampak imut (*kawaii*), proporsional, dan sangat konsisten.
   - **AbyssOrangeMix3 / AOM3A1B (SD 1.5, ~2.0 GB):** Model anime klasik legendaris dari CivArchive/Civitai #9942. Memiliki saturasi warna yang cerah (*vibrant*), pencahayaan lembut (*soft lighting*), dan shading mata/rambut yang artistik.
   - **万象熔炉 | Anything XL (SDXL, ~6.6 GB):** Model resolusi native 1024px super tajam. Memiliki pemahaman prompt yang mendalam untuk latar belakang kompleks, kostum mendetail, dan efek sinematik (memerlukan GPU 8GB+ VRAM).

3. **Kenapa unduhan model sempat terputus atau tidak selesai?**
   - Koneksi internet yang lambat atau terputus dapat menghentikan unduhan model AI besar. Waifu on Telegram menggunakan protokol `curl` dengan fitur **Auto-Resume** (`-C -`). Jika terputus, cukup jalankan `waifu models download <nama_model>` (contoh: `waifu models download anything_xl` atau `aom3`), dan unduhan akan melanjutkan dari persentase terakhir tanpa mengulang dari 0%.

4. **Bagaimana jika saya memilih suara Jepang tetapi berbicara dalam bahasa Indonesia?**
   - Sistem memiliki **Multi-Tier Translation Guardrail**. Bot secara otomatis menerjemahkan balasan ke bahasa Jepang alami sebelum diucapkan oleh Edge-TTS (`ja-JP-NanamiNeural`). Jika penerjemahan offline gagal, sistem otomatis beralih ke suara Indonesia (`id-ID-GadisNeural`) sehingga suara tidak pernah terdengar rusak atau melafalkan bahasa Indonesia dengan aksen asing yang ngaco.

5. **Bagaimana cara memeriksa apakah semua service (LLM, ComfyUI, Musik) sedang aktif?**
   - Dari terminal: jalankan `waifu status`.
   - Dari Telegram: ketik perintah `/status`. Waifu akan melaporkan status port 5001 (LLM), port 8188 (ComfyUI), port 8002 (Musik), dan penggunaan VRAM kartu grafis Anda.

6. **Bot membalas: *"My local brain connection hit a bump"***
   - Pastikan KoboldCPP sedang berjalan. Kamu bisa mengeceknya dengan `waifu status`.
   - Untuk menyalakannya, cukup jalankan `waifu start --daemon` atau `waifu start`.

7. **Apakah bot bisa berjalan di laptop tanpa GPU diskrit?**
   - Ya, 100%! Cukup pilih **Cloud Fallback Engine (Pollinations AI)** pada pengaturan foto. Bot akan mengalihkan generasi foto ke cloud GPU gratis tanpa membebani laptop Anda.

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

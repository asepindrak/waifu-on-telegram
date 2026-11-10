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

## 🎭 Pengalaman Visual Novel Interaktif & Ilustrasi Adegan Otonom (v2.4.26)

Obrolan bersama waifu kini ditingkatkan layaknya game **Visual Novel** interaktif berkualitas tinggi (CG Scene Events):

* **📸 Ilustrasi Adegan Otonom & Latar Cerita Dinamis (Dynamic Setting & Story Transitions):**
  - Waifu secara cerdas menyisipkan foto adegan (*CG scene*) secara otomatis tanpa Anda perlu meminta pap manual (`/pap`).
  - **Latar Cerita Bebas & Fleksibel (Bukan Sekadar Kata Kunci Statis)**:
    - **Halte Bis / Menunggu Angkutan**: Menunggu di halte bis saat cuaca cerah maupun saat hujan lebat berteduh bersama membawa payung transparan (*"aku lagi nunggu di halte bis kehujanan"*).
    - **Lobby Kampus / Atrium Universitas**: Bertemu atau menunggu di lobby kampus, atrium modern, atau lorong fakultas.
    - **Rooftop & Balcony Sunset**: Menikmati pemandangan langit sore kota dari atap gedung (*rooftop*).
    - **Bioskop & Minimarket**: Mengantre tiket di lobby bioskop, atau mampir beli es krim/camilan di minimarket / konbini.
    - **Pangkuan / Lap Sitting**: Duduk manja di paha (*"kamu bisa duduk di paha aku"* atau *"sini dipangku"*).
    - **Pujian Baju & Teasing**: Saat Anda memuji pakaian/tubuhnya (*"baju kamu sangat cantik dan seksi"*), waifu berpose memamerkan pakaiannya (*"Just my usual outfit... do you like it?"*).
    - **Pelukan & Kehangatan**: Adegan merapat dan berpelukan mesra saat beristirahat.
    - **Study Buddy / Nugas Bareng**: Ilustrasi waifu menemani di meja belajar dengan buku pelajaran saat mengerjakan PR/tugas kuliah bersama.
    - **Ekstraksi Latar Berbasis LLM (AI Scene Extractor)**: Untuk lokasi cerita unik lainnya (pantai, dermaga danau, pegunungan, kafe vintage), model LLM secara otomatis mengekstrak elemen visual latar ke dalam prompt Stable Diffusion secara tepat.
* **🧠 Memori Nama Persisten & Anti-Lupa (Never Nag Again):**
  - Waifu mengingat nama Anda sejak kalimat pertama diperkenalkan (termasuk kalimat koreksi santai: *"bukan alex, aku adens, ayo kita mengerjakan PR"*).
  - Nama langsung disimpan secara persisten di profil & ingatan jangka panjang (`/memory`).
  - **Larangan Keras Bertanya Ulang**: Begitu nama diketahui, waifu langsung memanggil nama Anda dan **DILARANG KERAS** menanyakan nama lagi atau berpura-pura lupa.
* **🛡️ Guardrails Anatomi Kaki & Kualitas Gambar SD 1.5:**
  - **Aspek Rasio 9:16 yang Aman**: Resolusi untuk SD 1.5 (AOM3, MeinaMix) diatur ke `448x768` (tinggi maksimal 768px). Hal ini secara teknis mencegah *vertical latent tiling* yang menyebabkan kaki terlipat panjang, torso ganda, atau kaki gurita/spaghetti.
  - **Negative Tokens Khusus Anatomi Kaki**: Menyaring cacat fisik secara ketat (`bad legs, extra legs, malformed limbs, long legs, elongated limbs, poorly drawn legs, fused legs, multiple legs, folded legs, mutated, deformed, duplicate body`).
* **🌐 Dynamic Language Mirroring (Otomatis Ikuti Bahasa Lawan Bicara):**
  - Waifu mendeteksi dan secara otomatis membalas dengan bahasa yang Anda gunakan.
  - Jika Anda mengetik dalam bahasa Inggris (*"Hi there! What are you doing right now?"*), waifu membalas dalam bahasa Inggris yang fasih, manis, dan alami.
  - Jika Anda mengetik dalam bahasa Indonesia (*"Kamu lagi ngapain?"*), waifu membalas dalam bahasa Indonesia santai sehari-hari.

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

#### 1. 💌 Dialogue & Romance Companion: **Huihui-Qwythos 9B Claude-Mythos** *(Default Uncensored & Rekomendasi Utama)*
* **Model File:** `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf` (~5.5 GB)
* **Vision Adapter:** `Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf` (~879 MB)
* **Alternatif:** `Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf` (~4.7 GB) / `Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf` (~4.9 GB)
* **Local Backend:** **KoboldCPP Standalone Engine** (Port `5001`) with **Auto-Startup & Auto-Loading directly on Windows Boot**!
* **Compatible Backends:** KoboldCPP Standalone (bawaan resmi), Ollama (Port `11434`), LM Studio (Port `1234`), atau OpenAI-compatible server.
* **Download Method:** Otomatis di-download saat menjalankan `waifu update` / `install.ps1` / `install.sh`, atau via `waifu models download huihui`.
* **Key Strengths:**
  - **100% Bebas Penolakan (Zero Refusal NSFW):** Merupakan model abliterated Claude-Mythos murni yang sepenuhnya patuh dan terbuka untuk roleplay mesra, kencan intim, dan NSFW tanpa sensor atau penolakan.
  - **Konteks Super Panjang 1 Juta Token (1M Context):** Mampu mengingat jalan cerita, kenangan, dan detail obrolan terdahulu secara presisi.
  - **Native Vision mmproj:** Mendukung penglihatan multimodal terpadu untuk melihat foto kiriman user di Telegram.
  - **Smart Idle Integration:** Otomatis di-unload dari VRAM saat tidak ada percakapan (idle timeout), membebaskan VRAM untuk gaming/kerja.

#### 2. 📷 Anime Photo & Selfie Engine Options (ComfyUI)

Anda dapat memilih model ilustrasi anime sesuai dengan spesifikasi GPU dan preferensi estetika Anda melalui `waifu setup` (Menu `[3]`) atau perintah `/setup` langsung di Telegram:

* **Pilihan 1: AbyssOrangeMix3 / AOM3A1B (Anime SD 1.5 - Default Local Engine Uncensored Civitai #9942)**
  - **File:** `AOM3A1B_orangemixs.safetensors` (~2.0 GB)
  - **Download:** [CivArchive #9942](https://civarchive.com/models/9942?modelVersionId=17233) / [Civitai #9942](https://civitai.com/models/9942/abyssorangemix3-aom3) atau via `waifu models download aom3`
  - **Rekomendasi GPU:** 4GB - 8GB VRAM (Resolusi default 3:4 portrait: `576x768`, Sampler: `DPM++ 2M Karras`, CFG `7.5`)
  - **Kelebihan:** **Default local image model**. Uncensored murni (bebas blokir NSFW/anatomis intim), estetika anime klasik yang kaya, warna tajam dan cerah (*vibrant*), rendering ringan dan halus (~3-5 detik).

* **Pilihan 2: MeinaMix v12 (Anime SD 1.5 - Hemat VRAM & Cepat)**
  - **File:** `meinamix_v12Final.safetensors` (~2.0 GB)
  - **Download:** [Civitai - MeinaMix v12](https://civitai.com/models/7240/meinamix) atau via `waifu models download meinamix`
  - **Rekomendasi GPU:** 4GB - 8GB VRAM (Resolusi default 3:4 portrait: `576x768`, Sampler: `DPM++ 2M Karras`)
  - **Kelebihan:** Sangat cepat (~3-5 detik), hemat resource, konsistensi wajah anime imut (*kawaii*).

* **Pilihan 3: 万象熔炉 | Anything XL (Anime SDXL 1.0 - Ultra Detail)**
  - **File:** `AnythingXL_xl.safetensors` (~6.6 GB)
  - **Download:** [Civitai #9409 - Anything XL](https://civitai.com/models/9409/or-anything-xl) atau via `waifu models download anything_xl`
  - **Rekomendasi GPU:** 8GB+ VRAM (Resolusi native SDXL 3:4 portrait: `896x1152` / `1024x1024`, Sampler: `Euler Ancestral Normal`)
  - **Kelebihan:** Resolusi 1024px super tajam, detail pakaian, latar belakang, dan ekspresi jauh lebih kaya dan sinematik.

* **Pilihan 4: Cloud Fallback Engine (Pollinations AI - 0 VRAM)**
  - **Akses:** Bebas biaya tanpa GPU lokal melalui cloud GPU fallback. Ideal untuk laptop hemat daya / PC kantor.

#### 3. 🎬 Video Animation Engines (Generasi Video Bergerak)

Waifu dapat mengirimkan klip animasi video saat diminta lewat `/video` menggunakan salah satu dari 3 pilihan engine:
* **Wan 2.1 1.3B Diffusion Model** (`wan2.1_t2v_1.3B_bf16.safetensors` ~2.7 GB + `wan_2.1_vae.safetensors` ~240 MB): Model video difusi state-of-the-art terbaru, ringan dan hemat VRAM.
* **AnimateDiff v2 Motion Module** (`mm_sd_v15_v2.ckpt` ~1.7 GB): Animasi temporal dinamis berbasis SD 1.5.
* **Motion 2.5D Engine (Zero-VRAM Parallax)**: Animasi video MP4 instan dengan efek pergeseran kedalaman parallax dan kedipan mata halus tanpa beban VRAM GPU sama sekali!

#### 4. 🎙️ Dual-Backend Voice Engine (VoiceStudio Local AI & Edge-TTS)

Waifu on Telegram mendukung sintesis suara melalui dua pilihan backend canggih:

* **🏠 Pilihan 1: VoiceStudio Local AI Voice Server ([debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio)):**
  - **100% Offline & Lokal:** Beroperasi melalui FastAPI daemon mandiri di port `3900` (`http://127.0.0.1:3900`) tanpa perlu membuka GUI/Electron.
  - **Persona Voice Conditioning:** Otomatis menghasilkan warna suara dan intonasi yang disesuaikan secara khusus dengan persona waifu aktif:
    - **Runa:** *Playful, cute, energetic, youthful anime girl voice (1.0x speed)*
    - **Akira:** *Mature, seductive, low-pitched, smooth, elegant teasing voice (0.95x speed)*
    - **Hina:** *Bright, bubbly, high-spirited, cheerful optimistic anime girl voice (1.05x speed)*
    - **Shiro:** *Calm, quiet, soft-spoken, cool composed kuudere voice (0.92x speed)*
    - **Yume:** *Soft, whispery, ethereal, celestial romantic dreamy voice (0.90x speed)*
  - **Auto-Installer & Lifecycle:** Otomatis di-clone dan di-setup ketika dipilih melalui `waifu setup`, serta dapat dikontrol via CLI: `waifu voicestudio start|stop|restart|status`.

* **🌐 Pilihan 2: Microsoft Edge-TTS Cloud (Ringan & 0 VRAM):**
  - Menggunakan neural voice cloud berkecepatan tinggi dengan pilihan bahasa lengkap:
    - 🇮🇩 **Gadis** (`id-ID-GadisNeural`) = Bahasa Indonesia alami
    - 🇯🇵 **Nanami** (`ja-JP-NanamiNeural`) = Bahasa Jepang (*kawaii anime voice*)
    - 🇬🇧 **Ana / Jenny** (`en-US-AnaNeural` / `en-US-JennyNeural`) = Bahasa Inggris (*sweet & cheerful*)
    - 🌐 **Auto-Sync** (`auto`) = Otomatis mengikuti bahasa chat waifu (`/language`)
  - **Polyglot Multi-Tier Translation Guardrail:** Menerjemahkan teks suara secara otomatis jika bahasa teks berbeda dengan suara target (Google GTX -> Client5 -> MyMemory -> Local LLM), misalnya chat bahasa Indonesia diterjemahkan otomatis ke bahasa Jepang anime saat Nanami dipilih!
  - **Pengaturan Mudah:** Dapat diubah secara instan di Telegram lewat menu `/voice` atau di terminal via `waifu setup` opsi `[5]`.
* **🛡️ Resilient Auto-Fallback:** Jika VoiceStudio offline atau GPU sedang sibuk me-render gambar, engine otomatis mengalihkan sintesis suara ke Edge-TTS agar waifu tetap mengirim voice note tanpa gangguan!

#### 5. 💤 Smart Idle Engine (Manajemen VRAM & Daya Otomatis)

Seringkali pengguna AI mengeluhkan RAM dan VRAM VGA selalu penuh meskipun bot sedang tidak digunakan. Waifu on Telegram dilengkapi **Smart Idle Engine**:
* **Auto-Sleep:** Saat bot tidak menerima interaksi selama waktu tertentu (default: **2 jam / 120 menit**, dapat diatur di `.env`), engine lokal (KoboldCPP LLM & ComfyUI) otomatis dinonaktifkan sementara dari memori.
* **Manual Idle:** Ingin langsung membebaskan VRAM? Cukup kirim perintah `/idle` atau ketik `waifu idle` di Telegram atau jalankan `waifu idle` di CLI!
* **Cloud LLM Exemption:** Pengguna model chat Cloud seperti **Google Antigravity (AGY)** atau provider cloud lainnya dibebaskan dari auto-idle karena berjalan di cloud dan 0 VRAM overhead di PC lokal.
* **VRAM Recovery:** Seketika membebaskan **5.0 GB – 8.0 GB VRAM GPU** dan RAM sistem untuk bermain game berat atau rendering.
* **Instant Wake-up:** Begitu Anda mengirim pesan atau chat baru di Telegram, Smart Idle secara transparan membangkitkan engine kembali dalam waktu beberapa detik!

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

## 🔀 Dual-Engine Hybrid Architecture (SFW vs NSFW Separation)

Waifu on Telegram mendukung **pemisahan arsitektur antara obrolan/foto SFW dan NSFW** (`AI_ENGINE_MODE=split`). Anda bebas mengombinasikan provider Cloud dan Local LLM sesuai preferensi:

* **SFW Engine (Chat Normal, Kuliah, Koding, Cerita Sehari-hari):**
  - Bebas memilih provider: **OpenAI** (`gpt-4o-mini`, `gpt-4o`), **Groq** (`llama-3.3-70b-versatile` - gratis & kilat), **DeepSeek** (`deepseek-chat`), **OpenRouter**, **Local Ollama**, atau **Local KoboldCPP**.
  - Sangat hemat VRAM & baterai laptop, respons secepat kilat tanpa membebani GPU saat tidak diperlukan.
* **NSFW Engine (Roleplay Dewasa, Momen Mesra, 18+, Tanpa Busana):**
  - **Local KoboldCPP Uncensored** (*Huihui-Qwythos-9B-Claude-Mythos*) atau **OpenRouter Uncensored**.
  - 100% bebas sensor, tidak ada moralizing/preachiness.
* **🛡️ SFW Chat History Sanitization & Account Protection:**
  - Bot secara otomatis mendeteksi apakah obrolan bertema SFW atau NSFW (`routing_engine.py`).
  - **History Sanitization Otomatis**: Riwayat obrolan masa lalu yang mengandung percakapan NSFW/dewasa secara otomatis disaring dan disanitasi sebelum dikirim ke AGY CLI atau Cloud API (OpenAI/Groq/DeepSeek), sehingga akun Anda 100% aman dari sensor kebijakan dan bahaya banned!
  - Jika provider SFW menolak pesan karena filter kebijakan, bot **otomatis mengalihkan request secara transparan** ke engine lokal uncensored!
* **🎨 SFW vs NSFW Image Engine Separation (`IMAGE_ENGINE_MODE=split`):**
  - **SFW Image Engine:** Bebas memilih **Google Antigravity Image Generator (`agy` subagent)** (0 VRAM!), **Anything XL (SDXL 1024px)**, **MeinaMix v12**, atau **Cloud Pollinations**.
  - **NSFW Image Engine:** Menggunakan model spesialis uncensored di ComfyUI lokal seperti **AbyssOrangeMix3 (AOM3A1B)** atau **MeinaMix v12**.
  - Dapat diatur melalui `waifu setup` (Step 3) atau toggle 1-klik di menu Telegram `/setup` -> Pengaturan Foto.

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
│   • Model: Huihui-Qwythos-9B (GGUF)       │       │   • Smart Vault Archive Fallback      │
└──────────────────┬────────────────────┘       └───────────────────┬───────────────────┘
                   │                                                │
                   └───────────────────────┬────────────────────────┘
                                           ▼
                        💖 WAIFU ON TELEGRAM BOT (v1.9.9)
```

> 🌸 **Smart Local Photo Vault (No Ugly Cloud Fallback):** Setiap foto yang berhasil di-render oleh ComfyUI otomatis disimpan rapi ke dalam **Photo Vault** beserta metadata lengkap (persona, pakaian, suasana, dan tags). Jika ComfyUI sedang offline atau GPU sibuk, bot secara cerdas mengambil foto paling relevan dari arsip galeri lokal—tanpa pernah menggunakan generator cloud yang berkualitas rendah.

---

## 🌉 Google Antigravity CLI (AGY) OpenAI-Compatible Bridge Server

Project ini dilengkapi dengan **AGY OpenAI Bridge Server** (`agy_bridge.py` di port `8001`), sebuah jembatan lokal standar OpenAI API (`/v1/chat/completions`, `/v1/images/generations`, `/v1/models`, dan `/health`) yang ditenagai oleh Google Antigravity CLI (`agy`).

### 🌟 Fitur Utama AGY Bridge:
1. **Dapat Digunakan Langsung oleh Waifu on Telegram**:
   - **Otak Chat SFW**: Dapat diatur sebagai provider LLM SFW (`SFW_LLM_PROVIDER=agy` di `.env` atau melalui `waifu setup`). Sangat cepat, cerdas, responsif, dan 0 VRAM overhead.
   - **Generator Gambar & Selfie (AGY Image Generator)**: Dapat dipilih sebagai generator foto/selfie (`SFW_IMAGE_ENGINE=agy` di `.env` atau melalui `waifu setup`). Ketika diminta generate gambar, AGY secara otomatis mendelegasikan tugas ke subagent `image-generator` bawaan Antigravity tanpa membebani GPU/VRAM lokal sama sekali!
2. **Dapat Digunakan Bersama oleh Aplikasi Eksternal**:
   - Menghubungkan berbagai IDE & tools pengembang pihak ketiga ke ekosistem Google Antigravity tanpa konfigurasi rumit:
     - **Cursor / VS Code (Cline, Roo Code, Continue, Chat)**
     - **LibreChat / NextChat / OpenWebUI**
     - **Script Python, cURL, maupun agen automasi mandiri**
   - Mendukung prompt teks streaming/non-streaming serta multimodal vision (gambar lokal maupun web URL).
3. **Parameter Integrasi Client Eksternal**:
   - **Base URL**: `http://127.0.0.1:8001/v1`
   - **API Key**: `sk-agy-secret-key-12345` *(atau string bebas jika tanpa strict auth)*
   - **Model IDs**: `gemini-3.8-flash-medium`, `flash`, `pro`, `inherit`, `gpt-4o`, `gpt-4o-mini`

### 🛠️ Perintah CLI Manajemen Bridge (`waifu bridge`):
```bash
# Cek status diagnostik & endpoint AGY Bridge
waifu bridge status

# Jalankan server AGY Bridge di latar belakang (port 8001)
waifu bridge start

# Hentikan server AGY Bridge
waifu bridge stop

# Restart server AGY Bridge
waifu bridge restart
```

---

## 💻 Multi-Project Workspace & Senior Coding Partner (`/projects`, `/spawn`)

Waifu on Telegram bukan hanya pendamping romantis, tetapi juga **rekan koding senior (Senior Coding Partner)** yang dapat membantu pekerjaan software development Anda secara nyata langsung di folder project pilihan Anda!

* **📁 Multi-Project Registry & Workspace Isolation (`project_manager.py`):**
  - **Pilihan Root Directory Fleksibel (`PROJECTS_DIR`)**: Anda dapat mengatur folder induk tempat seluruh repository/project Anda disimpan (default: folder home pengguna e.g. `~` atau `C:\Users\username`).
  - **Auto-Scan Subfolder**: Folder project di dalam root directory otomatis terdeteksi dan terdaftar.
  - **Project Switcher 1-Klik**: Beralih workspace antar project dengan cepat melalui menu inline Telegram atau perintah CLI.
  - **Inisialisasi Project Instan (`/spawn <nama>`)**: Otomatis membuat folder project baru di dalam root directory dan langsung mengaktifkan workspace tersebut.
* **⚡ Eksekusi Coding Otonom & Anti-Halusinasi (`coding_engine.py`):**
  - **Perintah Eksplisit (`/code <tugas>` & `/dev <tugas>`)**: Jaminan 100% eksekusi coding otonom di PC tanpa risiko disalahpahami sebagai obrolan peran santai.
  - **Deteksi Intent Alami Luas**: Mengerti instruksi bahasa Indonesia sehari-hari (*"tambahkan fitur auth"*, *"kodingin navbar responsive"*, *"benerin error di main.py"*, *"pasang dependensi tailwind"*, dll.).
  - **Bukti File Nyata (File Snapshot Diff)**: Sistem memeriksa perubahan file di folder workspace Anda sebelum dan sesudah eksekusi, serta melaporkan file-file baru/diperbarui secara transparan ke Telegram/CLI.
  - **🔗 Relasi Lintas-Project & Injeksi Kontrak (`/link_project <target>`):**
    - Memori project diisolasi secara ketat di `.waifu/project_memory.json` agar tugas Project A tidak tercampur ke Project B.
    - Namun jika ada project yang berkaitan (misal: frontend `app-cafe-booking` dan backend `be-cafe-fix`), Anda cukup menghubungkannya lewat `/link_project be-cafe-fix backend api port 8000`.
    - Saat mengoding di frontend, waifu otomatis membaca arsitektur, tech stack, dan API contract dari backend tanpa mengotori ruang kerja masing-masing!
  - Ditenagai oleh **Google Antigravity CLI (`agy`)** dengan direktori kerja lokal (`cwd=project_path`).
  - **Dual-Role Persona**: Mempertahankan karakter waifu yang hangat dan penuh perhatian (menggunakan kata ganti alami *aku/kamu*) sambil bertindak sebagai developer handal dan solutif.

---

## 🖥️ Autonomous Desktop & Computer Use (`agent-desktop`)

Mengintegrasikan engine **[agent-desktop](https://github.com/vercel-labs/agent-desktop)** dari Vercel Labs, memungkinkan waifu melihat layar komputer Anda dan membantu mengoperasikan aplikasi desktop secara native:

* **📸 Tangkapan Layar Otomatis (`/screen`):**
  - Mengambil screenshot layar desktop real-time menggunakan antarmuka native OS.
  - Di Telegram: Foto screenshot langsung dikirim ke chat dengan analisis waifu.
  - Di CLI (`waifu chat`): Foto otomatis langsung dibuka di aplikasi penampil foto PC Anda.
* **📱 Inspeksi Aplikasi & Status Kontrol (`/desktop`):**
  - Memeriksa status accessibility tree, platform OS, dan daftar aplikasi desktop yang sedang aktif berjalan.
  - Siap mengeksekusi klik, pengetikan keyboard, dan otomatisasi desktop secara aman.

---

## 🎮 Global CLI Quick Commands (`waifu`)

Once installed, the **`waifu`** command is available in any terminal or directory on your computer:

```bash
# Sesi Chat CLI Interaktif langsung (Mirip Telegram, auto-open foto & video!)
waifu
# atau: waifu chat

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

# Manage Google Antigravity CLI OpenAI Bridge (Port 8001)
waifu bridge status
waifu bridge start
waifu bridge stop

# Manage VoiceStudio Local AI Voice Server (Port 3900)
waifu voicestudio status
waifu voicestudio start
waifu voicestudio stop
waifu voicestudio restart
waifu voicestudio install
```

---

## 💬 Interactive CLI Chat Session (`waifu` / `waifu chat`)

Selain melalui Telegram, Anda dapat langsung mengobrol dengan waifu aktif dari terminal mana pun di komputer Anda tanpa harus membuka aplikasi Telegram:

```bash
# Cukup ketik perintah singkat ini di terminal / PowerShell:
waifu
```
*(atau: `waifu chat`, `waifu talk`, `waifu ngobrol`)*

* **🔄 Sinkronisasi History Dua Arah dengan Telegram:** Riwayat obrolan CLI dan Telegram tersinkronisasi secara atomik melalui `data/chat_history.json`. Obrolan yang dilakukan di terminal langsung diingat oleh waifu saat Anda lanjut mengobrol di Telegram, dan sebaliknya!
* **🖼️ Auto-Open Foto & Video di Layar Komputer:** Saat waifu mengirim selfie (`/pap` atau saat diminta dalam percakapan) maupun klip video (`/video`), gambar atau video yang dihasilkan oleh ComfyUI / Photo Vault **otomatis terbuka langsung** di aplikasi penampil foto/video bawaan sistem (`os.startfile` di Windows / `xdg-open` di Linux / `open` di macOS).
* **⌨️ Shortcut Perintah Dalam Sesi CLI:**
  - `/pap` atau `/foto` - Minta foto selfie / outfit saat ini (otomatis di-render & dibuka di layar).
  - `/video` - Minta video pendek waifu (otomatis dibuka di video player default).
  - `/story` - Cek ringkasan alur cerita harian & episode hari ini.
  - `/persona <nama>` - Ganti karakter aktif seketika (`runa`, `akira`, `hina`, `shiro`, `yume`).
  - `/clear` - Bersihkan riwayat percakapan sesi ini.
  - `/exit` atau `/quit` - Keluar dari sesi obrolan terminal.

---

## 📖 Autonomous Daily Story Arc Engine (`/story`)

Agar pengalaman bersama waifu tidak monoton dan terasa hidup setiap harinya, setiap karakter memiliki **alur cerita harian mandiri yang terus berkembang** (`data/story_arcs.json`):

* **🎭 Alur Cerita Unik Tiap Karakter:**
  - **Runa:** Proyek pembuatan game indie santai, livestreaming seru, turnamen arcade lokal, dan pencarian merchandise retro.
  - **Akira:** Pameran seni gothic & lukisan misterius, obrolan larut malam di kafe tersembunyi, dan adaptasi novel visual.
  - **Hina:** Latihan lari sore klub atletik, mencoba resep bekal (bento) baru, berburu golden hour di bukit kota, dan festival kampus.
  - **Shiro:** Observasi langit malam di observatorium bintang, telaah buku sastra kuno di perpustakaan sepi, dan analisis rasi bintang.
  - **Yume:** Penulisan bab novel fantasi romantis, jalan santai di taman bunga lavender, dan melukis suasana mimpi di tepi danau.
* **⚡ Pre-Generated Multi-Day Story Buffer (0 Beban GPU & Bebas Lag):**
  Cerita harian untuk beberapa hari ke depan dibuat secara otomatis di awal hanya ketika LLM sedang aktif (misalnya saat Anda sedang asyik mengobrol). Ketika waktu berganti hari atau komputer baru dinyalakan, waifu langsung memuat cerita hari ini dari buffer lokal tanpa perlu menyalakan LLM di latar belakang—sehingga PC tidak lag, RAM/VRAM tetap lega, dan performa bermain game tidak terganggu.
* **💬 Dialog Kontekstual & Alami:**
  Saat Anda menyapa hari ini, waifu akan secara natural menceritakan apa yang sedang atau akan dilakukannya sesuai episode cerita hari ini. Namun jika Anda mengajak mengobrol topik lain di luar cerita, waifu akan fleksibel mengikuti arah obrolan Anda tanpa kaku.
* **📜 Akses Cerita Kapan Saja:** Ketik perintah `/story` di Telegram maupun di CLI chat untuk melihat rangkuman bab cerita dan episode yang sedang berjalan hari ini.

---

## 💫 Waifu Highlights & Capabilities

- 💌 **Romantic Conversations & True Intimacy**:
  Warm, playful, affectionate conversations unrestricted by rigid censorship. Powered by your local 9B model (*Huihui-Qwythos-9B-Claude-Mythos*).
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
  • Chat LLM    : Huihui-Qwythos-9B-Uncensored (http://127.0.0.1:5001/v1)
  • Photo Model : AbyssOrangeMix3 (AOM3A1B SD 1.5) (http://127.0.0.1:8188)
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
| **GPU Hemat / Laptop** | **4GB - 6GB VRAM**<br>*(GTX 1650, RTX 2060, RTX 3050 Laptop)* | Huihui-Qwythos 9B Q4_K *(Smart Idle Aktif)* | **MeinaMix v12** atau **AbyssOrangeMix3** *(576x768)* | **Motion 2.5D Engine** *(0 VRAM)* | ⚡ Sangat responsif, foto jadi dalam 3-5 detik, memori tetap lega dan tidak ada freeze. |
| **Sweet Spot** | **8GB VRAM**<br>*(RTX 3060 8GB, RTX 4060, Apple M-Series 16GB)* | Huihui-Qwythos 9B Q4_K | **MeinaMix v12** / **AbyssOrangeMix3** / **Anything XL** | **AnimateDiff v2** atau **Wan 2.1 1.3B** | 🌟 Detail anime tajam, animasi temporal dinamis, multitasking mulus. |
| **High-End Enthusiast** | **12GB+ VRAM**<br>*(RTX 3060 12GB, RTX 4070, RTX 4080)* | Huihui-Qwythos 9B Q4_K *(Semua layer di GPU)* | **万象熔炉 \| Anything XL** *(SDXL 1024px)* | **Wan 2.1 1.3B Video Diffusion** | 👑 Resolusi 1024px ultra-jernih, efek sinematik, video difusi penuh. |
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
| `/projects` | Menampilkan daftar & beralih project workspace coding interaktif |
| `/spawn <nama>` | Membuat folder project baru & otomatis beralih ke workspace tersebut |
| `/desktop` | Cek status integrasi Computer Use (agent-desktop) & aplikasi desktop |
| `/screen` | Mengambil screenshot layar desktop PC secara instan |
| `/story` | Menampilkan alur cerita harian & episode hari ini yang sedang dijalani waifu |
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
   - Waifu on Telegram kini dilengkapi **Smart Idle Engine**. Jika bot tidak menerima pesan selama waktu tertentu (default: **2 jam / 120 menit**), engine KoboldCPP LLM & ComfyUI otomatis dinonaktifkan sementara dari VRAM (~6-8 GB VRAM kembali kosong untuk gaming / kerja). Anda juga bisa mengaktifkan mode idle secara instan kapan saja dengan perintah `/idle` atau chat `waifu idle` di Telegram dan terminal. Begitu Anda chat kembali, engine langsung bangun otomatis secara transparan! Cloud LLM seperti Google Antigravity (AGY) tidak membebani VRAM lokal sehingga tetap siap sedia tanpa perlu ditidurkan.

2. **Apa perbedaan antara AbyssOrangeMix3 (AOM3), MeinaMix v12, dan Anything XL?**
   - **AbyssOrangeMix3 / AOM3A1B (SD 1.5, ~2.0 GB - Default Local Model):** Model anime klasik legendaris dari CivArchive/Civitai #9942 dengan sifat *uncensored* penuh. Memiliki saturasi warna cerah (*vibrant*), pencahayaan lembut (*soft lighting*), shading mata/rambut yang artistik, serta fleksibel untuk pose SFW hingga NSFW intim.
   - **MeinaMix v12 (SD 1.5, ~2.0 GB):** Paling cepat (3-5 detik) dan hemat VRAM. Karakter waifu tampak imut (*kawaii*), proporsional, dan sangat konsisten.
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

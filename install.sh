#!/usr/bin/env bash
# ==============================================================================
# Waifu on Telegram - 1-Line Universal Linux/macOS Auto-Installer
# Compatible with: curl -fsSL https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.sh | bash
# ==============================================================================
set -e

echo "===================================================================="
VER=$(cat VERSION 2>/dev/null || echo "1.6.8")
echo "       💖 WAIFU ON TELEGRAM v$VER - Linux/macOS 1-Line Installer 🌸       "
echo "===================================================================="
echo ""

REPO_URL="https://github.com/asepindrak/waifu-on-telegram.git"
DEFAULT_INSTALL_DIR="$HOME/waifu-on-telegram"

# 1. Target Directory & Clone
if [ -f "bot.py" ] && [ -f "setup.py" ]; then
    INSTALL_DIR="$(pwd)"
    echo "[1/6] Running inside project folder: $INSTALL_DIR"
else
    INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    echo "[1/6] Target directory: $INSTALL_DIR"
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "  Updating repository..."
        cd "$INSTALL_DIR"
        git pull --quiet || true
    elif [ -f "$INSTALL_DIR/bot.py" ]; then
        echo "  Project folder exists. Using existing files..."
        cd "$INSTALL_DIR"
    else
        echo "  Cloning repository via Git..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
fi

# 2. Check Python
echo "[2/6] Checking Python environment..."
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo "[ERROR] Python 3 is required. Please install Python 3.8+ first."
    exit 1
fi
echo "  ✓ Python: $($PY --version)"

# 3. Install dependencies
echo "[3/7] Installing Python dependencies..."
$PY -m pip install -r requirements.txt --quiet --disable-pip-version-check

# 4. Check & Setup Local LLM Engine (KoboldCPP)
echo "[4/7] Checking Local LLM Engine (Chat & Romance Brain)..."
mkdir -p "$INSTALL_DIR/tools" "$INSTALL_DIR/models"

if [ ! -f "$INSTALL_DIR/tools/koboldcpp" ]; then
    echo "  ℹ Standalone LLM engine (KoboldCPP) not installed."
    read -p "  Download KoboldCPP standalone engine (~150 MB)? [Y/n, default: Y]: " DL_KCPP
    DL_KCPP=${DL_KCPP:-Y}
    if [[ "$DL_KCPP" =~ ^[Yy]$ ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  >> Downloading KoboldCPP for macOS (Apple Silicon Metal)..."
            curl -fL -o "$INSTALL_DIR/tools/koboldcpp" "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp-mac-arm64"
        else
            echo "  >> Downloading KoboldCPP for Linux (CUDA/Vulkan)..."
            curl -fL -o "$INSTALL_DIR/tools/koboldcpp" "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp-linux-x64"
        fi
        chmod +x "$INSTALL_DIR/tools/koboldcpp"
        echo "  ✓ KoboldCPP downloaded and made executable."
    fi
else
    echo "  ✓ KoboldCPP detected at: $INSTALL_DIR/tools/koboldcpp"
fi

# Check for GGUF model in models/
GGUF_COUNT=$(ls "$INSTALL_DIR/models/"*.gguf 2>/dev/null | grep -v "mmproj" | wc -l)
if [ "$GGUF_COUNT" -eq 0 ]; then
    echo "  ℹ No GGUF chat model found in '$INSTALL_DIR/models'."
    read -p "  Auto-download uncensored 'Huihui-Qwythos-9B-Claude-Mythos-5-1M' Q4_K model (~5.5 GB)? [Y/n, default: Y]: " DL_MODEL
    DL_MODEL=${DL_MODEL:-Y}
    if [[ "$DL_MODEL" =~ ^[Yy]$ ]]; then
        curl -fL -C - -o "$INSTALL_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf" \
          "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
        echo "  ✓ Model downloaded successfully."
    fi
else
    echo "  ✓ Local GGUF chat model found."
fi

# 5. Check Node.js for PC Music Remote
echo "[5/7] Checking Node.js for Music Remote..."
if command -v node &>/dev/null; then
    echo "  ✓ Node.js found: $(node -v). Installing npm packages..."
    npm install --silent
else
    echo "  ℹ Node.js not detected. Music remote feature will be disabled (chat & photos remain functional)."
fi

# 6. Register global CLI script
echo "[6/7] Registering global CLI 'waifu' in ~/.local/bin..."
mkdir -p "$HOME/.local/bin"
cat <<EOF > "$HOME/.local/bin/waifu"
#!/usr/bin/env bash
$PY "$INSTALL_DIR/bin/cli.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/waifu"
cp -f "$HOME/.local/bin/waifu" "$HOME/.local/bin/pacar-ai"

# Ensure ~/.local/bin is in PATH for current & future shell sessions
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile"; do
        if [ -f "$rc" ] && ! grep -q ".local/bin" "$rc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
    done
fi

# 7. Launch interactive setup wizard (Models, Language, Video Engine & Autorun)
echo "[7/7] Launching Interactive Setup Wizard..."
$PY setup.py --wizard

echo ""
echo "===================================================================="
echo "  🎉 Installation complete! Waifu on Telegram is ready."
echo "  Global CLI: waifu start / waifu status / waifu setup"
echo "  Installation folder: $INSTALL_DIR"
echo "===================================================================="
read -p "Would you like to start the bot right now? [Y/n, default: Y]: " START_NOW
START_NOW=${START_NOW:-Y}
if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    waifu start --daemon
fi

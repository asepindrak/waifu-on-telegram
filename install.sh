#!/usr/bin/env bash
# ==============================================================================
# Waifu on Telegram - 1-Line Universal Linux/macOS Auto-Installer
# Compatible with: curl -fsSL https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.sh | bash
# ==============================================================================
set -e

echo "===================================================================="
VER=$(cat VERSION 2>/dev/null || echo "1.6.8")
echo "       💖 WAIFU ON TELEGRAM v$VER - Linux/macOS 1-Line Installer 🤖       "
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
echo "[3/6] Installing Python dependencies..."
$PY -m pip install -r requirements.txt --quiet --disable-pip-version-check

# 4. Check Node.js for PC Music Remote
echo "[4/6] Checking Node.js for Music Remote..."
if command -v node &>/dev/null; then
    echo "  ✓ Node.js found: $(node -v). Installing npm packages..."
    npm install --silent
else
    echo "  ℹ Node.js not detected. Music remote feature will be disabled (chat & photos remain functional)."
fi

# 5. Register global CLI script
echo "[5/6] Registering global CLI 'waifu' in ~/.local/bin..."
mkdir -p "$HOME/.local/bin"
cat <<EOF > "$HOME/.local/bin/waifu"
#!/usr/bin/env bash
$PY "$INSTALL_DIR/bin/cli.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/waifu"
cp -f "$HOME/.local/bin/waifu" "$HOME/.local/bin/pacar-ai"

# 6. Launch interactive setup wizard (Models, Language, Video Engine & Autorun)
echo "[6/6] Launching Interactive Setup Wizard..."
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

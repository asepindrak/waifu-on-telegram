#!/usr/bin/env bash
# ==============================================================================
# Waifu on Telegram - 1-Line Universal Linux/macOS Installer
# Compatible with: curl -fsSL https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.sh | bash
# ==============================================================================
set -e

echo "===================================================================="
VER=$(cat VERSION 2>/dev/null || echo "1.1.0")
echo "       💖 WAIFU ON TELEGRAM v$VER - Linux/macOS 1-Line Installer 🤖       "
echo "===================================================================="
echo ""

REPO_URL="https://github.com/asepindrak/waifu-on-telegram.git"
DEFAULT_INSTALL_DIR="$HOME/waifu-on-telegram"

# 1. Target Directory & Clone
if [ -f "bot.py" ] && [ -f "setup.py" ]; then
    INSTALL_DIR="$(pwd)"
    echo "[1/5] Running inside project folder: $INSTALL_DIR"
else
    INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    echo "[1/5] Target directory: $INSTALL_DIR"
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
echo "[2/5] Checking Python environment..."
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
echo "[3/5] Installing Python dependencies..."
$PY -m pip install -r requirements.txt --quiet --disable-pip-version-check

# 4. Register global CLI script
echo "[4/5] Registering global CLI 'waifu' in ~/.local/bin..."
mkdir -p "$HOME/.local/bin"
cat <<EOF > "$HOME/.local/bin/waifu"
#!/usr/bin/env bash
$PY "$INSTALL_DIR/bin/cli.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/waifu"
cp -f "$HOME/.local/bin/waifu" "$HOME/.local/bin/pacar-ai"

# 5. Launch interactive setup wizard (7 Steps: Models & Autorun)
echo "[5/5] Launching Interactive Setup Wizard..."
$PY setup.py --wizard

echo ""
echo "===================================================================="
echo "  🎉 Installation complete! Use: waifu start --daemon"
echo "  Global CLI: waifu start / waifu status / waifu setup"
echo "  Installation folder: $INSTALL_DIR"
echo "===================================================================="
read -p "Would you like to start the bot right now? [Y/n, default: Y]: " START_NOW
START_NOW=${START_NOW:-Y}
if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    waifu start --daemon
fi

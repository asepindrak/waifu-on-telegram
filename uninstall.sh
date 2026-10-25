#!/usr/bin/env bash
# ==============================================================================
# WAIFU ON TELEGRAM - Uninstaller (Linux/macOS)
# Repository: https://github.com/asepindrak/waifu-on-telegram
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/uninstall.sh | bash
# ==============================================================================
set -e

echo "========================================================"
echo "        💖 WAIFU ON TELEGRAM - UNINSTALLER 🤖           "
echo "========================================================"
echo ""
echo "Starting Waifu on Telegram uninstallation process..."
echo ""

# 1. Stop running processes
echo "> [1/3] Terminating any running bot processes..."
pkill -f "bot.py" 2>/dev/null || true
pkill -f "music_player_server.js" 2>/dev/null || true
echo "  [OK] Processes stopped."

# 2. Remove Global CLI executables
echo "> [2/3] Removing global CLI executables from ~/.local/bin..."
rm -f "$HOME/.local/bin/waifu"
rm -f "$HOME/.local/bin/pacar-ai"
rm -f "$HOME/.local/bin/lu-bot"
echo "  [OK] CLI shortcuts removed."

# 3. Interactive Data Removal
DEFAULT_INSTALL_DIR="$HOME/waifu-on-telegram"
if [ -f "bot.py" ] && [ -f "setup.py" ]; then
    INSTALL_DIR="$(pwd)"
else
    INSTALL_DIR="$DEFAULT_INSTALL_DIR"
fi

echo ""
echo "--------------------------------------------------------"
echo "DATA RETENTION & PERSISTENCE CHOICES:"
echo "Detected Project Directory: $INSTALL_DIR"
echo "--------------------------------------------------------"
echo " [1] REMOVE ALL DATA (Clean Reset / Fresh Install)"
echo "     Deletes bot folder, .env tokens, chat memory, and temporary media."
echo ""
echo " [2] KEEP DATA (Preserve Tokens & Personas - Default)"
echo "     Only removes CLI executables. Your .env configurations stay safe."
echo "--------------------------------------------------------"
echo ""

read -p "Your choice [1 = Remove All / 2 = Keep Data] (Default: 2): " CHOICE
CHOICE=${CHOICE:-2}

if [[ "$CHOICE" =~ ^(1|y|yes|clean|all|remove|delete)$ ]]; then
    echo ""
    echo "> [CLEAN UNINSTALL] Removing project directory ($INSTALL_DIR)..."
    cd "$HOME"
    rm -rf "$INSTALL_DIR"
    echo "  [OK] Project folder removed cleanly."
else
    echo ""
    echo "> [SAFE OPTION] Bot configurations & tokens KEPT at:"
    echo "  $INSTALL_DIR"
fi

echo ""
echo "========================================================"
echo "  🎉 WAIFU ON TELEGRAM SUCCESSFULLY UNINSTALLED!"
echo "========================================================"
echo ""

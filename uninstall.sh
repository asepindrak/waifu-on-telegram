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
echo "> [1/4] Stopping all running Waifu services (Bot, KoboldCPP, ComfyUI, Music Server)..."
pkill -f "python.*bot.py" 2>/dev/null || true
pkill -f "bot.py" 2>/dev/null || true
pkill -f "koboldcpp" 2>/dev/null || true
pkill -f "main.py.*8188" 2>/dev/null || true
pkill -f "node.*music_player_server.js" 2>/dev/null || true
pkill -f "music_player_server.js" 2>/dev/null || true

# Kill any processes holding ports 5001, 8188, 8002 if lsof is available
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    lsof -ti:8188 | xargs kill -9 2>/dev/null || true
    lsof -ti:8002 | xargs kill -9 2>/dev/null || true
fi
echo "  [OK] All active background processes stopped."

# 2. Remove Autorun configurations (Crontab / macOS LaunchAgent / Systemd)
echo "> [2/4] Removing autorun configurations..."
# Linux crontab cleanup
if command -v crontab >/dev/null 2>&1; then
    if crontab -l 2>/dev/null | grep -q "start_services.sh"; then
        crontab -l 2>/dev/null | grep -v "start_services.sh" | crontab - 2>/dev/null || true
        echo "  [OK] Crontab autorun entry removed."
    fi
fi

# macOS LaunchAgent cleanup
MACOS_PLIST="$HOME/Library/LaunchAgents/com.waifu.telegram.plist"
if [ -f "$MACOS_PLIST" ]; then
    launchctl unload "$MACOS_PLIST" 2>/dev/null || true
    rm -f "$MACOS_PLIST"
    echo "  [OK] macOS LaunchAgent removed."
fi

# Systemd user service cleanup
SYSTEMD_USER_SERVICE="$HOME/.config/systemd/user/waifu.service"
if [ -f "$SYSTEMD_USER_SERVICE" ]; then
    systemctl --user stop waifu.service 2>/dev/null || true
    systemctl --user disable waifu.service 2>/dev/null || true
    rm -f "$SYSTEMD_USER_SERVICE"
    systemctl --user daemon-reload 2>/dev/null || true
    echo "  [OK] Systemd user service removed."
fi
echo "  [OK] Autorun cleanup completed."

# 3. Remove Global CLI executables
echo "> [3/4] Removing global CLI executables from ~/.local/bin..."
rm -f "$HOME/.local/bin/waifu"
rm -f "$HOME/.local/bin/pacar-ai"
rm -f "$HOME/.local/bin/lu-bot"
echo "  [OK] CLI shortcuts removed."

# 4. Interactive Data Removal
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
echo " [1] 🗑️  FULL UNINSTALL (Clean Reset / Wipe Everything)"
echo "     - Deletes entire project folder ($INSTALL_DIR)"
echo "     - Deletes 5.5GB Local LLM model (models/) & ComfyUI (tools/)"
echo "     - Deletes Telegram bot token & credentials (.env)"
echo "     - Deletes chat memory, affinity data, and Photo Vault album"
echo "     SELECT THIS if you want a complete removal or fresh install."
echo ""
echo " [2] 💾 KEEP DATA (Preserve Models, Tokens & Photos - Default)"
echo "     - Stops all background processes (Bot, KoboldCPP, ComfyUI, Music)"
echo "     - Removes autorun entries and global CLI shortcuts"
echo "     - PRESERVES your 5.5GB AI model in models/ (no need to redownload!)"
echo "     - PRESERVES your Telegram bot token (.env) and personas/"
echo "     - PRESERVES your chat memory, affinity, and Photo Vault (data/)"
echo "--------------------------------------------------------"
echo ""

read -p "Your choice [1 = Full Uninstall / 2 = Keep Data] (Default: 2): " CHOICE
CHOICE=${CHOICE:-2}

if [[ "$CHOICE" =~ ^(1|y|yes|clean|all|remove|delete)$ ]]; then
    echo ""
    echo "> [CLEAN UNINSTALL] Removing project directory ($INSTALL_DIR)..."
    cd "$HOME"
    rm -rf "$INSTALL_DIR"
    echo "  [OK] Project folder removed cleanly."
    echo "  [OK] All models, data, tokens, and temporary files wiped cleanly!"
else
    echo ""
    echo "> [SAFE OPTION] Bot configurations, models & data KEPT at:"
    echo "  $INSTALL_DIR"
    echo "  ✓ Models preserved:       $INSTALL_DIR/models"
    echo "  ✓ Photo Vault preserved:  $INSTALL_DIR/data/photo_vault"
    echo "  ✓ Credentials preserved:  $INSTALL_DIR/.env"
    echo "  ✓ Personas preserved:     $INSTALL_DIR/personas"
    echo ""
    echo "  (If you reinstall in the future, your models, tokens, and photos will be immediately available)."
fi

echo ""
echo "========================================================"
echo "  🎉 WAIFU ON TELEGRAM SUCCESSFULLY UNINSTALLED!"
echo "========================================================"
echo ""

#!/usr/bin/env bash
# ==============================================================================
# Waifu on Telegram - Universal Background Services Stopper (Linux / macOS)
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/bot.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi

# Fallback kill all related processes
pkill -f "python.*bot.py" 2>/dev/null || true
pkill -f "node.*music_player_server.js" 2>/dev/null || true
pkill -f "koboldcpp" 2>/dev/null || true
pkill -f "main.py.*8188" 2>/dev/null || true

echo "All Waifu on Telegram services stopped."

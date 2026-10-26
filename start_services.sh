#!/usr/bin/env bash
# ==============================================================================
# Waifu on Telegram - Universal Background Services Launcher (Linux / macOS)
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="$SCRIPT_DIR/bot.pid"
LOG_FILE="$SCRIPT_DIR/bot.log"

PY="python3"
if ! command -v python3 &>/dev/null; then
    PY="python"
fi

# 1. Start Music Server if node is available
if command -v node &>/dev/null && [ -f "$SCRIPT_DIR/music_player_server.js" ]; then
    nohup node "$SCRIPT_DIR/music_player_server.js" >/dev/null 2>&1 &
fi

# 2. Start Python Telegram Bot
nohup $PY "$SCRIPT_DIR/bot.py" >> "$LOG_FILE" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$PID_FILE"

echo "Waifu on Telegram started with PID $BOT_PID"

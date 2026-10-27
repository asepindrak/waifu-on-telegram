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

# 1. Start KoboldCPP LLM Engine if present & not already active
if [ -f "$SCRIPT_DIR/tools/koboldcpp" ]; then
    MODEL_PATH=""
    if [ -f "$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf" ]; then
        MODEL_PATH="$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
    elif [ -d "$SCRIPT_DIR/models" ]; then
        MODEL_PATH=$(ls "$SCRIPT_DIR/models/"*.gguf 2>/dev/null | grep -v "mmproj" | head -n 1)
    fi

    MMPROJ_PATH=""
    if [ -f "$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf" ]; then
        MMPROJ_PATH="$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf"
    elif [ -d "$SCRIPT_DIR/models" ]; then
        MMPROJ_PATH=$(ls "$SCRIPT_DIR/models/"*mmproj*.gguf 2>/dev/null | head -n 1)
    fi

    MMPROJ_ARG=""
    if [ -n "$MMPROJ_PATH" ]; then
        MMPROJ_ARG="--mmproj $MMPROJ_PATH"
    fi

    if [ -n "$MODEL_PATH" ]; then
        if ! nc -z 127.0.0.1 5001 2>/dev/null && ! (echo >/dev/tcp/127.0.0.1/5001) 2>/dev/null; then
            echo "Starting KoboldCPP LLM Engine with model: $MODEL_PATH ${MMPROJ_ARG:+(Vision enabled)}..."
            nohup "$SCRIPT_DIR/tools/koboldcpp" --model "$MODEL_PATH" $MMPROJ_ARG --gpulayers 99 --port 5001 --quiet >/dev/null 2>&1 &
            sleep 3
        fi
    fi
fi

# 2. Start ComfyUI Generator if present & port 8188 not active
if ! nc -z 127.0.0.1 8188 2>/dev/null && ! (echo >/dev/tcp/127.0.0.1/8188) 2>/dev/null; then
    $PY -c "import asset_manager, subprocess; spec = asset_manager.get_comfyui_launch_spec(); subprocess.run(spec['cmd'], cwd=spec['cwd']) if spec else exit(1)" >/dev/null 2>&1 &
    sleep 3
fi

# 3. Start Music Server if node is available
if command -v node &>/dev/null && [ -f "$SCRIPT_DIR/music_player_server.js" ]; then
    nohup node "$SCRIPT_DIR/music_player_server.js" >/dev/null 2>&1 &
fi

# 4. Start Python Telegram Bot
nohup $PY "$SCRIPT_DIR/bot.py" >> "$LOG_FILE" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$PID_FILE"

echo "Waifu on Telegram started with PID $BOT_PID"

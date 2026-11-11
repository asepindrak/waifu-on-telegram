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

# Load Smart Idle & On-Demand settings from .env (matching start_services.bat)
read_env_flag() {
    local key="$1"
    local default_val="$2"
    $PY -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.environ.get('$key', '$default_val').strip().lower())" 2>/dev/null || echo "$default_val"
}

SMART_IDLE=$(read_env_flag "SMART_IDLE_ENABLED" "true")
COMFY_ON_DEMAND=$(read_env_flag "COMFYUI_ON_DEMAND" "true")
AGY_BRIDGE_FLAG=$(read_env_flag "AGY_BRIDGE_ENABLED" "")
SFW_LLM_PROV=$(read_env_flag "SFW_LLM_PROVIDER" "")
NSFW_LLM_PROV=$(read_env_flag "NSFW_LLM_PROVIDER" "")
SFW_IMG_ENG=$(read_env_flag "SFW_IMAGE_ENGINE" "")
NSFW_IMG_ENG=$(read_env_flag "NSFW_IMAGE_ENGINE" "")

# 1. Start KoboldCPP LLM Engine ONLY if Smart Idle is explicitly disabled
if [[ "$SMART_IDLE" == "false" || "$SMART_IDLE" == "0" || "$SMART_IDLE" == "no" ]]; then
    if [ -f "$SCRIPT_DIR/tools/koboldcpp" ]; then
        MODEL_PATH=""
        if [ -f "$SCRIPT_DIR/models/Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf" ]; then
            MODEL_PATH="$SCRIPT_DIR/models/Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf"
        elif [ -f "$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf" ]; then
            MODEL_PATH="$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
        elif [ -d "$SCRIPT_DIR/models" ]; then
            MODEL_PATH=$(ls "$SCRIPT_DIR/models/"*.gguf 2>/dev/null | grep -v "mmproj" | head -n 1)
        fi

        MMPROJ_PATH=""
        if ! echo "$MODEL_PATH" | grep -iq "stheno\|llama"; then
            if [ -f "$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf" ]; then
                MMPROJ_PATH="$SCRIPT_DIR/models/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf"
            elif [ -d "$SCRIPT_DIR/models" ]; then
                MMPROJ_PATH=$(ls "$SCRIPT_DIR/models/"*mmproj*.gguf 2>/dev/null | head -n 1)
            fi
        fi

        MMPROJ_ARG=""
        if [ -n "$MMPROJ_PATH" ]; then
            MMPROJ_ARG="--mmproj $MMPROJ_PATH"
        fi

        if [ -n "$MODEL_PATH" ]; then
            if ! nc -z 127.0.0.1 5001 2>/dev/null && ! (echo >/dev/tcp/127.0.0.1/5001) 2>/dev/null; then
                GPU_LAYERS=$($PY -c "import os, asset_manager; from dotenv import load_dotenv; load_dotenv(); hw = asset_manager.detect_hardware_profile(); print(os.environ.get('LLM_GPU_LAYERS') or hw.get('recommended_llm_layers', 24))" 2>/dev/null)
                [ -z "$GPU_LAYERS" ] && GPU_LAYERS=24
                CTX_SIZE=$($PY -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.environ.get('LLM_CONTEXT_SIZE', '4096'))" 2>/dev/null)
                [ -z "$CTX_SIZE" ] && CTX_SIZE=4096
                echo "Starting KoboldCPP LLM Engine with model: $MODEL_PATH ($GPU_LAYERS GPU layers, ctx $CTX_SIZE) ${MMPROJ_ARG:+(Vision enabled)}..."
                nohup "$SCRIPT_DIR/tools/koboldcpp" --model "$MODEL_PATH" $MMPROJ_ARG --gpulayers "$GPU_LAYERS" --contextsize "$CTX_SIZE" --smartcontext --port 5001 --quiet >/dev/null 2>&1 &
                sleep 3
            fi
        fi
    fi
else
    echo "Smart Idle Active: KoboldCPP will wake automatically on-demand."
fi

# 2. Start ComfyUI Generator ONLY if On-Demand is disabled & port 8188 not active
if [[ "$COMFY_ON_DEMAND" == "false" || "$COMFY_ON_DEMAND" == "0" || "$COMFY_ON_DEMAND" == "no" ]]; then
    if ! nc -z 127.0.0.1 8188 2>/dev/null && ! (echo >/dev/tcp/127.0.0.1/8188) 2>/dev/null; then
        $PY -c "import asset_manager, subprocess; spec = asset_manager.get_comfyui_launch_spec(); subprocess.run(spec['cmd'], cwd=spec['cwd']) if spec else exit(1)" >/dev/null 2>&1 &
        sleep 3
    fi
else
    echo "ComfyUI On-Demand Active: generator will wake only for photo/video requests."
fi

# 3. Start Music Server if node is available
if command -v node &>/dev/null && [ -f "$SCRIPT_DIR/music_player_server.js" ]; then
    nohup node "$SCRIPT_DIR/music_player_server.js" >/dev/null 2>&1 &
fi

# 4. Start Google Antigravity CLI Bridge if enabled or configured as active provider
SHOULD_START_AGY=false
if [[ "$AGY_BRIDGE_FLAG" == "true" || "$AGY_BRIDGE_FLAG" == "1" || "$AGY_BRIDGE_FLAG" == "yes" ]]; then
    SHOULD_START_AGY=true
elif [[ "$AGY_BRIDGE_FLAG" != "false" && "$AGY_BRIDGE_FLAG" != "0" && "$AGY_BRIDGE_FLAG" != "no" ]]; then
    if [[ "$SFW_LLM_PROV" == "agy" || "$NSFW_LLM_PROV" == "agy" || "$SFW_IMG_ENG" == "agy" || "$NSFW_IMG_ENG" == "agy" ]]; then
        SHOULD_START_AGY=true
    fi
fi

if [[ "$SHOULD_START_AGY" == "true" ]] && command -v agy &>/dev/null && [ -f "$SCRIPT_DIR/agy_bridge.py" ]; then
    if ! nc -z 127.0.0.1 8001 2>/dev/null && ! (echo >/dev/tcp/127.0.0.1/8001) 2>/dev/null; then
        echo "Starting Google Antigravity CLI Bridge on port 8001..."
        nohup $PY "$SCRIPT_DIR/agy_bridge.py" >/dev/null 2>&1 &
    fi
fi

# 5. Start Python Telegram Bot
nohup $PY "$SCRIPT_DIR/bot.py" >> "$LOG_FILE" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$PID_FILE"

echo "Waifu on Telegram started with PID $BOT_PID"

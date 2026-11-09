@echo off
title Waifu on Telegram Services
cd /d "%~dp0"

echo ============================================================
echo   Starting Waifu on Telegram Services...
echo ============================================================

:: 1. Start KoboldCPP LLM Engine if available & Smart Idle is explicitly disabled & not already running
set "KOBOLD_STANDBY=1"
if exist "%~dp0.env" (
    findstr /i /c:"SMART_IDLE_ENABLED=false" "%~dp0.env" >nul 2>&1 && set "KOBOLD_STANDBY=0"
    findstr /i /c:"SMART_IDLE_ENABLED=0" "%~dp0.env" >nul 2>&1 && set "KOBOLD_STANDBY=0"
    findstr /i /c:"SMART_IDLE_ENABLED=no" "%~dp0.env" >nul 2>&1 && set "KOBOLD_STANDBY=0"
)
if "%KOBOLD_STANDBY%"=="1" (
    echo [1/4] Local LLM on standby (Smart Idle: VRAM bebas ^• Bangun otomatis saat chat)
) else (
    set KOBOLD_EXE=%~dp0tools\koboldcpp.exe
    set KOBOLD_MODEL=
    if exist "%~dp0models\Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf" (
        set "KOBOLD_MODEL=%~dp0models\Llama-3.1-8B-Stheno-v3.4-Q4_K_M.gguf"
    ) else if exist "%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf" (
        set "KOBOLD_MODEL=%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
    ) else (
        for /f "delims=" %%F in ('dir /b /s "%~dp0models\*.gguf" 2^>nul ^| findstr /v /i "mmproj"') do (
            if not defined KOBOLD_MODEL set "KOBOLD_MODEL=%%F"
        )
    )

    :: Auto-detect mmproj vision adapter (only if compatible, skip for Llama/Stheno models)
    set KOBOLD_MMPROJ=
    echo "%KOBOLD_MODEL%" | findstr /i "stheno llama" >nul 2>&1
    if errorlevel 1 (
        if exist "%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf" (
            set "KOBOLD_MMPROJ=%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf"
        ) else if exist "%~dp0models\mmproj-model-bf16.gguf" (
            set "KOBOLD_MMPROJ=%~dp0models\mmproj-model-bf16.gguf"
        ) else (
            for /f "delims=" %%F in ('dir /b /s "%~dp0models\*mmproj*.gguf" 2^>nul') do (
                if not defined KOBOLD_MMPROJ set "KOBOLD_MMPROJ=%%F"
            )
        )
    )

    set MMPROJ_ARG=
    if defined KOBOLD_MMPROJ (
        set "MMPROJ_ARG=--mmproj \"%KOBOLD_MMPROJ%\""
    )

    if exist "%KOBOLD_EXE%" (
        if defined KOBOLD_MODEL (
            powershell -NoProfile -Command "if (Get-Process koboldcpp -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
            if not errorlevel 1 (
                echo [1/4] KoboldCPP LLM is already running in background.
            ) else (
                powershell -NoProfile -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 5001); $tcp.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
                if errorlevel 1 (
                    if defined KOBOLD_MMPROJ (
                        echo [1/4] Starting KoboldCPP LLM Server with auto-loaded model and Vision mmproj...
                    ) else (
                        echo [1/4] Starting KoboldCPP LLM Server with auto-loaded model...
                    )
                    start "KoboldCPP Brain" /b "%KOBOLD_EXE%" --model "%KOBOLD_MODEL%" %MMPROJ_ARG% --gpulayers 99 --port 5001 --contextsize 4096 --smartcontext --threads 4 --usecublas normal --quiet
                    timeout /t 3 >nul
                ) else (
                    echo [1/4] KoboldCPP LLM is already running on port 5001.
                )
            )
        )
    )
)

:: 2. Start ComfyUI Photo Generator on port 8188 if not already running and not on-demand
python -c "import os, asset_manager; from dotenv import load_dotenv; load_dotenv(); exit(1 if os.environ.get('COMFYUI_ON_DEMAND','true').lower() in ('1','true','yes') else (0 if asset_manager.get_comfyui_launch_spec() else 1))" >nul 2>&1
if not errorlevel 1 (
    powershell -NoProfile -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 8188); $tcp.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
    if errorlevel 1 (
        echo [2/4] Starting ComfyUI Photo Generator (safe VRAM mode)...
        start "ComfyUI Generator" /b python -c "import asset_manager, subprocess; spec = asset_manager.get_comfyui_launch_spec(); subprocess.run(spec['cmd'], cwd=spec['cwd'])" >nul 2>&1
        timeout /t 3 >nul
    ) else (
        echo [2/4] ComfyUI Generator is already active on port 8188.
    )
) else (
    echo [2/4] ComfyUI on standby (On-Demand Mode: auto-starts on photo/video request).
)

:: 3. Start Music Remote Server if node exists
set "NODE_CMD="
where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "NODE_CMD=node"
) else if exist "%~dp0tools\nodejs\node.exe" (
    set "NODE_CMD=%~dp0tools\nodejs\node.exe"
)

if defined NODE_CMD (
    if exist music_player_server.js (
        echo [3/4] Starting YouTube Music Remote Server on port 8002...
        start "Waifu Music Server" /b "%NODE_CMD%" music_player_server.js > nul 2>&1
    )
)

:: 4. Start Google Antigravity CLI Bridge if enabled & port 8001 not active
set "AGY_BRIDGE_ENABLED=1"
if exist "%~dp0.env" (
    findstr /i /c:"AGY_BRIDGE_ENABLED=false" "%~dp0.env" >nul 2>&1 && set "AGY_BRIDGE_ENABLED=0"
    findstr /i /c:"AGY_BRIDGE_ENABLED=0" "%~dp0.env" >nul 2>&1 && set "AGY_BRIDGE_ENABLED=0"
    findstr /i /c:"AGY_BRIDGE_ENABLED=no" "%~dp0.env" >nul 2>&1 && set "AGY_BRIDGE_ENABLED=0"
)

if "%AGY_BRIDGE_ENABLED%"=="1" (
    powershell -NoProfile -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 8001); $tcp.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
    if errorlevel 1 (
        where agy >nul 2>nul
        if %ERRORLEVEL% EQU 0 (
            echo [4/5] Starting Google Antigravity CLI Bridge on port 8001...
            start "AGY OpenAI Bridge" /b python agy_bridge.py > nul 2>&1
        )
    ) else (
        echo [4/5] Google Antigravity CLI Bridge is already active on port 8001.
    )
)

:: 5. Start Telegram Bot
echo [5/5] Starting Telegram Bot...
python bot.py

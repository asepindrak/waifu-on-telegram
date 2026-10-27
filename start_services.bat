@echo off
title Waifu on Telegram Services
cd /d "%~dp0"

echo ============================================================
echo   Starting Waifu on Telegram Services...
echo ============================================================

:: 1. Start KoboldCPP LLM Engine if available & not already running
set KOBOLD_EXE=%~dp0tools\koboldcpp.exe
set KOBOLD_MODEL=
if exist "%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf" (
    set "KOBOLD_MODEL=%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
) else (
    for /f "delims=" %%F in ('dir /b /s "%~dp0models\*.gguf" 2^>nul ^| findstr /v /i "mmproj"') do (
        if not defined KOBOLD_MODEL set "KOBOLD_MODEL=%%F"
    )
)

:: Auto-detect mmproj vision adapter
set KOBOLD_MMPROJ=
if exist "%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf" (
    set "KOBOLD_MMPROJ=%~dp0models\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf"
) else if exist "%~dp0models\mmproj-model-bf16.gguf" (
    set "KOBOLD_MMPROJ=%~dp0models\mmproj-model-bf16.gguf"
) else (
    for /f "delims=" %%F in ('dir /b /s "%~dp0models\*mmproj*.gguf" 2^>nul') do (
        if not defined KOBOLD_MMPROJ set "KOBOLD_MMPROJ=%%F"
    )
)

set MMPROJ_ARG=
if defined KOBOLD_MMPROJ (
    set "MMPROJ_ARG=--mmproj \"%KOBOLD_MMPROJ%\""
)

if exist "%KOBOLD_EXE%" (
    if defined KOBOLD_MODEL (
        powershell -NoProfile -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 5001); $tcp.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
        if errorlevel 1 (
            if defined KOBOLD_MMPROJ (
                echo [1/4] Starting KoboldCPP LLM Server with auto-loaded model and Vision mmproj...
            ) else (
                echo [1/4] Starting KoboldCPP LLM Server with auto-loaded model...
            )
            start "KoboldCPP Brain" /b "%KOBOLD_EXE%" --model "%KOBOLD_MODEL%" %MMPROJ_ARG% --gpulayers 99 --port 5001 --usecublas normal --quiet
            timeout /t 3 >nul
        ) else (
            echo [1/4] KoboldCPP LLM is already running on port 5001.
        )
    )
)

:: 2. Start ComfyUI Photo Generator on port 8188 if not already running
powershell -NoProfile -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 8188); $tcp.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    python -c "import asset_manager; spec = asset_manager.get_comfyui_launch_spec(); exit(0 if spec else 1)" >nul 2>&1
    if not errorlevel 1 (
        echo [2/4] Starting ComfyUI Photo Generator (safe VRAM mode)...
        start "ComfyUI Generator" /b python -c "import asset_manager, subprocess; spec = asset_manager.get_comfyui_launch_spec(); subprocess.run(spec['cmd'], cwd=spec['cwd'])" >nul 2>&1
        timeout /t 3 >nul
    ) else (
        echo [2/4] ComfyUI not detected locally. Photo Vault album will be used for photos.
    )
) else (
    echo [2/4] ComfyUI Generator is already active on port 8188.
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

:: 4. Start Telegram Bot
echo [4/4] Starting Telegram Bot...
python bot.py

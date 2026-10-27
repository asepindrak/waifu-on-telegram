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

if exist "%KOBOLD_EXE%" (
    if defined KOBOLD_MODEL (
        powershell -NoProfile -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 5001); $tcp.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
        if errorlevel 1 (
            echo [1/3] Starting KoboldCPP LLM Server with auto-loaded model...
            start "KoboldCPP Brain" /b "%KOBOLD_EXE%" --model "%KOBOLD_MODEL%" --gpulayers 99 --port 5001 --usecublas normal --quiet
            timeout /t 3 >nul
        ) else (
            echo [1/3] KoboldCPP LLM is already running on port 5001.
        )
    )
)

:: 2. Start Music Remote Server if node exists
where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    if exist music_player_server.js (
        echo [2/3] Starting YouTube Music Remote Server on port 8002...
        start "Waifu Music Server" /b node music_player_server.js > nul 2>&1
    )
)

:: 3. Start Telegram Bot
echo [3/3] Starting Telegram Bot...
python bot.py

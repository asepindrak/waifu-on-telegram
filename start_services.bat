@echo off
title Waifu on Telegram Services
cd /d "%~dp0"

echo ============================================================
echo   Starting Waifu on Telegram Services...
echo ============================================================

:: Start Music Remote Server if node exists
where node >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    if exist music_player_server.js (
        echo [1/2] Starting YouTube Music Remote Server on port 8002...
        start "Waifu Music Server" /b node music_player_server.js > nul 2>&1
    )
)

:: Start Telegram Bot
echo [2/2] Starting Telegram Bot...
python bot.py

@echo off
title Waifu on Telegram
cd /d "%~dp0"

echo ============================================================
echo   Starting Waifu on Telegram...
echo ============================================================

python bot.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot stopped with an error code %ERRORLEVEL%.
    pause
)

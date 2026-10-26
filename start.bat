@echo off
chcp 65001 >nul
title Waifu on Telegram
cd /d "%~dp0"
echo ====================================================================
echo                 💖 Starting Waifu on Telegram... 🤖                 
echo ====================================================================
echo.
python bot.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Bot stopped with an error code: %ERRORLEVEL%
    pause
)

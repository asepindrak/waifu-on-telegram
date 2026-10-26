@echo off
chcp 65001 >nul
title Waifu on Telegram - Auto Installer
echo ====================================================================
echo        💖 WAIFU ON TELEGRAM - Windows One-Click Installer 🤖        
echo ====================================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0install.ps1'"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Installation failed or was interrupted.
    pause
    exit /b %ERRORLEVEL%
)
pause

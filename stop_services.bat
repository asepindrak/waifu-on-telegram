@echo off
title Stop Waifu on Telegram
cd /d "%~dp0"

echo Stopping Waifu on Telegram Services...

taskkill /F /FI "WINDOWTITLE eq Waifu on Telegram*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Waifu Music Server*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq KoboldCPP*" >nul 2>&1
taskkill /F /IM koboldcpp.exe >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq ComfyUI*" >nul 2>&1
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' -and $_.CommandLine -like '*8188*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bot.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo Services stopped.
timeout /t 2 >nul

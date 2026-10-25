@echo off
title AI Girlfriend Bot - Reconfiguration Wizard
cd /d "%~dp0"

python setup.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Configuration closed.
    pause
)

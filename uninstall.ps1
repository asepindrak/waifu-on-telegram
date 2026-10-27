# ==============================================================================
# WAIFU ON TELEGRAM - Uninstaller (Windows PowerShell)
# Repository: https://github.com/asepindrak/waifu-on-telegram
# Usage:
#   irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/uninstall.ps1 | iex
# ==============================================================================

Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "        💖 WAIFU ON TELEGRAM - UNINSTALLER 🤖           " -ForegroundColor Magenta
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "`nStarting Waifu on Telegram uninstallation process...`n" -ForegroundColor Cyan

# 1. Stop all running bot, KoboldCPP, ComfyUI, and music player processes
Write-Host "> [1/4] Stopping all running Waifu services (Bot, KoboldCPP, ComfyUI, Music Server)..." -ForegroundColor Cyan

# Stop bot.py processes
try {
    $botProcs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*bot.py*" }
    if ($botProcs) {
        foreach ($p in $botProcs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  [OK] Waifu Telegram bot processes terminated." -ForegroundColor Green
    } else {
        Write-Host "  [OK] No active bot process found." -ForegroundColor Gray
    }
} catch {
    Write-Host "  [OK] Bot process inspection completed." -ForegroundColor Gray
}

# Stop KoboldCPP processes (process name, window title, or port 5001)
try {
    Get-Process -Name "koboldcpp*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    $koboldConns = Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue
    if ($koboldConns) {
        foreach ($c in $koboldConns) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    
    $koboldProcs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*koboldcpp*" -or $_.CommandLine -like "*Huihui-Qwythos*" }
    if ($koboldProcs) {
        foreach ($p in $koboldProcs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  [OK] KoboldCPP local LLM server terminated." -ForegroundColor Green
} catch {
    Write-Host "  [OK] KoboldCPP inspection completed." -ForegroundColor Gray
}

# Stop ComfyUI processes (port 8188 or main.py)
try {
    $comfyConns = Get-NetTCPConnection -LocalPort 8188 -ErrorAction SilentlyContinue
    if ($comfyConns) {
        foreach ($c in $comfyConns) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    $comfyProcs = Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -like "*main.py*" -and $_.CommandLine -like "*8188*") -or $_.CommandLine -like "*tools\ComfyUI*" }
    if ($comfyProcs) {
        foreach ($p in $comfyProcs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  [OK] ComfyUI image generator server terminated." -ForegroundColor Green
} catch {
    Write-Host "  [OK] ComfyUI inspection completed." -ForegroundColor Gray
}

# Stop YouTube Music server on port 8002
$MusicPort = 8002
try {
    $conns = Get-NetTCPConnection -LocalPort $MusicPort -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($conn in $conns) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  [OK] Music server process on port $MusicPort terminated." -ForegroundColor Green
    } else {
        Write-Host "  [OK] No active music server on port $MusicPort." -ForegroundColor Gray
    }
} catch {
    Write-Host "  [OK] Music server inspection completed." -ForegroundColor Gray
}

# Wait for process exit and file handles to be cleanly released
Start-Sleep -Seconds 1

# 2. Remove Windows Startup Autorun Shortcuts & Scheduled Tasks
Write-Host "> [2/4] Removing Windows Startup autorun configuration..." -ForegroundColor Cyan
$StartupFolder = [Environment]::GetFolderPath('Startup')
$ShortcutsToRemove = @(
    "Start_Waifu_on_Telegram.lnk",
    "Start_AI_Girlfriend_Telegram_Bot.lnk",
    "Start_Locally_Uncensored_Bot.lnk",
    "WaifuOnTelegram.bat",
    "WaifuOnTelegram.vbs"
)

$removedAutorun = $false
foreach ($sc in $ShortcutsToRemove) {
    $scPath = Join-Path $StartupFolder $sc
    if (Test-Path $scPath) {
        Remove-Item -Path $scPath -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Removed autorun shortcut: $sc" -ForegroundColor Green
        $removedAutorun = $true
    }
}

try {
    $schTask = Get-ScheduledTask -TaskName "WaifuOnTelegram" -ErrorAction SilentlyContinue
    if ($schTask) {
        Unregister-ScheduledTask -TaskName "WaifuOnTelegram" -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "  [OK] Removed scheduled task: WaifuOnTelegram" -ForegroundColor Green
        $removedAutorun = $true
    }
} catch { }

if (-not $removedAutorun) {
    Write-Host "  [OK] No autorun configuration found in Windows Startup." -ForegroundColor Gray
}

# 3. Remove Global CLI Executables from ~/.local/bin
Write-Host "> [3/4] Cleaning up global CLI wrappers (waifu, pacar-ai, lu-bot)..." -ForegroundColor Cyan
$UserBin = Join-Path $HOME ".local\bin"
$WaifuCmd = Join-Path $UserBin "waifu.cmd"
$PacarCmd = Join-Path $UserBin "pacar-ai.cmd"
$LuBotCmd = Join-Path $UserBin "lu-bot.cmd"
$WaifuBash = Join-Path $UserBin "waifu"

try {
    # Delayed removal so if uninstaller is invoked from waifu.cmd itself, CMD wrapper exits cleanly
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -Command Start-Sleep -Seconds 3; if (Test-Path '$WaifuCmd') { Remove-Item -Path '$WaifuCmd' -Force -ErrorAction SilentlyContinue }; if (Test-Path '$PacarCmd') { Remove-Item -Path '$PacarCmd' -Force -ErrorAction SilentlyContinue }; if (Test-Path '$LuBotCmd') { Remove-Item -Path '$LuBotCmd' -Force -ErrorAction SilentlyContinue }; if (Test-Path '$WaifuBash') { Remove-Item -Path '$WaifuBash' -Force -ErrorAction SilentlyContinue }"
    Write-Host "  [OK] Global CLI wrappers scheduled for clean removal." -ForegroundColor Green
} catch {
    if (Test-Path $WaifuCmd) { Remove-Item -Path $WaifuCmd -Force -ErrorAction SilentlyContinue }
    if (Test-Path $PacarCmd) { Remove-Item -Path $PacarCmd -Force -ErrorAction SilentlyContinue }
    if (Test-Path $LuBotCmd) { Remove-Item -Path $LuBotCmd -Force -ErrorAction SilentlyContinue }
    if (Test-Path $WaifuBash) { Remove-Item -Path $WaifuBash -Force -ErrorAction SilentlyContinue }
    Write-Host "  [OK] Global CLI wrappers removed directly." -ForegroundColor Green
}

# 4. Interactive Choice: Data Retention & Persistence
$candidateDirs = @(
    (Join-Path $HOME "waifu-on-telegram"),
    (Join-Path $HOME "locally-uncensored-telegram-bot"),
    (Get-Location).Path
)

$targetInstallDir = $null
foreach ($dir in $candidateDirs) {
    if ((Test-Path (Join-Path $dir "bot.py")) -and (Test-Path (Join-Path $dir "setup.py"))) {
        $targetInstallDir = $dir
        break
    }
}

if (-not $targetInstallDir) {
    $targetInstallDir = Join-Path $HOME "waifu-on-telegram"
}

Write-Host "`n--------------------------------------------------------" -ForegroundColor Gray
Write-Host "DATA RETENTION & PERSISTENCE CHOICES:" -ForegroundColor Yellow
Write-Host "Detected Project Directory: $targetInstallDir" -ForegroundColor White
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host " [1] 🗑️  FULL UNINSTALL (Clean Reset / Wipe Everything)" -ForegroundColor Red
Write-Host "     - Deletes entire project folder ($targetInstallDir)"
Write-Host "     - Deletes 5.5GB Local LLM model (models/) & ComfyUI (tools/)"
Write-Host "     - Deletes Telegram bot token & credentials (.env)"
Write-Host "     - Deletes chat memory, affinity data, and Photo Vault album"
Write-Host "     SELECT THIS if you want a complete removal or fresh install." -ForegroundColor Gray
Write-Host "`n [2] 💾 KEEP DATA (Preserve Models, Tokens & Photos - Default)" -ForegroundColor Green
Write-Host "     - Stops all background processes (Bot, KoboldCPP, ComfyUI, Music)"
Write-Host "     - Removes Startup autorun shortcuts & global CLI commands"
Write-Host "     - PRESERVES your 5.5GB AI model in models/ (no need to redownload!)"
Write-Host "     - PRESERVES your Telegram bot token (.env) and custom personas/"
Write-Host "     - PRESERVES your chat memory, affinity, and Photo Vault album (data/)"
Write-Host "--------------------------------------------------------`n" -ForegroundColor Gray

$choice = $null
try {
    $choice = Read-Host "Your choice [1 = Full Uninstall / 2 = Keep Data] (Default: 2)"
} catch {
    $choice = "2"
}

if ($choice -eq '1' -or $choice -match '^(1|y|yes|clean|all|remove|delete)$') {
    Write-Host "`n> [CLEAN UNINSTALL] Removing project directory ($targetInstallDir)..." -ForegroundColor Red
    if (Test-Path $targetInstallDir) {
        # Check if running inside directory
        $currentLoc = (Get-Location).Path
        if ($currentLoc -like "$targetInstallDir*") {
            Set-Location $HOME
        }
        
        # Ensure any file locks are released
        Start-Sleep -Seconds 1
        
        $deleted = $false
        for ($i = 1; $i -le 3; $i++) {
            try {
                Remove-Item -Path $targetInstallDir -Recurse -Force -ErrorAction Stop
                $deleted = $true
                break
            } catch {
                Start-Sleep -Seconds 1
            }
        }
        
        if ($deleted) {
            Write-Host "  [OK] Project folder $targetInstallDir completely deleted." -ForegroundColor Green
        } else {
            Remove-Item -Path $targetInstallDir -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  [OK] Project folder deletion completed." -ForegroundColor Green
        }
    }
    Write-Host "  [OK] All models, data, tokens, and temporary files wiped cleanly!" -ForegroundColor Green
} else {
    Write-Host "`n> [SAFE OPTION] Bot configurations, models & data KEPT at:" -ForegroundColor Green
    Write-Host "  $targetInstallDir" -ForegroundColor Cyan
    Write-Host "  ✓ Models preserved:       $targetInstallDir\models" -ForegroundColor Gray
    Write-Host "  ✓ Photo Vault preserved:  $targetInstallDir\data\photo_vault" -ForegroundColor Gray
    Write-Host "  ✓ Credentials preserved:  $targetInstallDir\.env" -ForegroundColor Gray
    Write-Host "  ✓ Personas preserved:     $targetInstallDir\personas" -ForegroundColor Gray
    Write-Host "`n  (If you reinstall in the future, your models, tokens, and photos will be immediately available)." -ForegroundColor Gray
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "  🎉 WAIFU ON TELEGRAM SUCCESSFULLY UNINSTALLED!" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green

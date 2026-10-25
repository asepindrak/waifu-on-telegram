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

# 1. Stop any running bot and music player processes
Write-Host "> [1/4] Stopping running bot & music player processes..." -ForegroundColor Cyan

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
    Write-Host "  [OK] Process inspection completed." -ForegroundColor Gray
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
    Write-Host "  [OK] Port inspection completed." -ForegroundColor Gray
}

# 2. Remove Windows Startup Autorun Shortcuts
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
if (-not $removedAutorun) {
    Write-Host "  [OK] No autorun shortcut found in Windows Startup folder." -ForegroundColor Gray
}

# 3. Remove Global CLI Executables from ~/.local/bin
Write-Host "> [3/4] Cleaning up global CLI wrappers (waifu, pacar-ai, lu-bot)..." -ForegroundColor Cyan
$UserBin = Join-Path $HOME ".local\bin"
$WaifuCmd = Join-Path $UserBin "waifu.cmd"
$PacarCmd = Join-Path $UserBin "pacar-ai.cmd"
$LuBotCmd = Join-Path $UserBin "lu-bot.cmd"

try {
    # Delayed removal so if uninstaller is invoked from waifu.cmd itself, CMD wrapper exits cleanly
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -Command Start-Sleep -Seconds 3; if (Test-Path '$WaifuCmd') { Remove-Item -Path '$WaifuCmd' -Force -ErrorAction SilentlyContinue }; if (Test-Path '$PacarCmd') { Remove-Item -Path '$PacarCmd' -Force -ErrorAction SilentlyContinue }; if (Test-Path '$LuBotCmd') { Remove-Item -Path '$LuBotCmd' -Force -ErrorAction SilentlyContinue }"
    Write-Host "  [OK] Global CLI wrappers scheduled for clean removal." -ForegroundColor Green
} catch {
    if (Test-Path $WaifuCmd) { Remove-Item -Path $WaifuCmd -Force -ErrorAction SilentlyContinue }
    if (Test-Path $PacarCmd) { Remove-Item -Path $PacarCmd -Force -ErrorAction SilentlyContinue }
    if (Test-Path $LuBotCmd) { Remove-Item -Path $LuBotCmd -Force -ErrorAction SilentlyContinue }
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
Write-Host " [1] 🗑️  REMOVE ALL DATA (Clean Reset / Fresh Install)" -ForegroundColor Red
Write-Host "     Deletes bot folder, .env tokens, chat memory, and downloaded media."
Write-Host "     SELECT THIS if you want a complete removal or fresh install." -ForegroundColor Gray
Write-Host "`n [2] 💾 KEEP DATA (Preserve Tokens & Personas - Default)" -ForegroundColor Green
Write-Host "     Only removes CLI executables and autorun. Your .env and models remain safe." -ForegroundColor Gray
Write-Host "--------------------------------------------------------`n" -ForegroundColor Gray

$choice = $null
try {
    $choice = Read-Host "Your choice [1 = Remove All / 2 = Keep Data] (Default: 2)"
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
        Remove-Item -Path $targetInstallDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Project folder $targetInstallDir completely deleted." -ForegroundColor Green
    }
    Write-Host "  [OK] All data, tokens, and temporary files wiped cleanly!" -ForegroundColor Green
} else {
    Write-Host "`n> [SAFE OPTION] Bot configurations & tokens KEPT at:" -ForegroundColor Green
    Write-Host "  $targetInstallDir" -ForegroundColor Cyan
    Write-Host "  (If you reinstall in the future, your tokens and custom personas will be preserved)." -ForegroundColor Gray
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "  🎉 WAIFU ON TELEGRAM SUCCESSFULLY UNINSTALLED!" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green

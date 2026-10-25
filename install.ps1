# ==============================================================================
# Waifu on Telegram - 1-Line Universal Windows Installer
# Compatible with: irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.ps1 | iex
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "====================================================================" -ForegroundColor Magenta
$ver = if (Test-Path "VERSION") { (Get-Content "VERSION").Trim() } else { "1.1.0" }
Write-Host "       💖 WAIFU ON TELEGRAM v$ver - Windows 1-Line Auto Installer 🤖       " -ForegroundColor Magenta
Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host ""

# 1. Target Directory & Clone / Download
$repoUrl = "https://github.com/asepindrak/waifu-on-telegram.git"
$zipUrl = "https://github.com/asepindrak/waifu-on-telegram/archive/refs/heads/main.zip"
$defaultInstallDir = Join-Path $env:USERPROFILE "waifu-on-telegram"

if ((Test-Path "bot.py") -and (Test-Path "setup.py")) {
    $installDir = (Get-Location).Path
    Write-Host "[1/6] Running inside project folder: $installDir" -ForegroundColor Cyan
} else {
    $installDir = $defaultInstallDir
    Write-Host "[1/6] Target installation directory: $installDir" -ForegroundColor Cyan

    if (Test-Path (Join-Path $installDir ".git")) {
        Write-Host "  Updating existing Git repository..." -ForegroundColor Yellow
        Set-Location $installDir
        try { git pull --quiet } catch {}
    } elseif (Test-Path (Join-Path $installDir "bot.py")) {
        Write-Host "  Project folder exists. Using existing files..." -ForegroundColor Green
        Set-Location $installDir
    } else {
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Write-Host "  Cloning repository via Git..." -ForegroundColor Yellow
            git clone $repoUrl $installDir
            Set-Location $installDir
        } else {
            Write-Host "  Git not found. Downloading project ZIP archive..." -ForegroundColor Yellow
            $tempZip = Join-Path $env:TEMP "waifu-on-telegram-main.zip"
            Invoke-RestMethod -Uri $zipUrl -OutFile $tempZip
            $tempExtract = Join-Path $env:TEMP "waifu-on-telegram-extract"
            if (Test-Path $tempExtract) { Remove-Item -Path $tempExtract -Recurse -Force }
            Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
            $extractedRoot = Join-Path $tempExtract "waifu-on-telegram-main"
            if (Test-Path $extractedRoot) {
                Move-Item -Path $extractedRoot -Destination $installDir -Force
            }
            Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
            Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
            Set-Location $installDir
        }
    }
}

# 2. Check Python Environment
Write-Host "[2/6] Checking Python environment..." -ForegroundColor Cyan
$py = "python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $py = "py"
    } else {
        Write-Host "[ERROR] Python 3.8+ was not found on your system." -ForegroundColor Red
        Write-Host "Please install Python from https://www.python.org/ and check 'Add to PATH'." -ForegroundColor Yellow
        exit 1
    }
}
$pyVer = & $py --version 2>&1
Write-Host "  ✓ Python: $pyVer" -ForegroundColor Green

# 3. Install Python Dependencies
Write-Host "[3/6] Installing Python requirements..." -ForegroundColor Cyan
& $py -m pip install -r requirements.txt --quiet --disable-pip-version-check
Write-Host "  ✓ Dependencies installed successfully." -ForegroundColor Green

# 4. Check Node.js for Music Remote (Optional)
Write-Host "[4/6] Checking Node.js for Music Remote..." -ForegroundColor Cyan
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ Node.js found: $(node -v). Installing npm packages..." -ForegroundColor Green
    npm install --silent
} else {
    Write-Host "  ℹ Node.js not detected. Music remote feature will be disabled (chat & photos remain functional)." -ForegroundColor Yellow
}

# 5. Register Global CLI Commands (waifu, pacar-ai) in User PATH
Write-Host "[5/6] Registering global CLI commands (waifu, pacar-ai)..." -ForegroundColor Cyan
$userBin = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Force -Path $userBin | Out-Null

$cliPy = Join-Path $installDir "bin\cli.py"
$cmdScript = "@echo off`r`npython `"$cliPy`" %*"
Set-Content -Path (Join-Path $userBin "waifu.cmd") -Value $cmdScript -Force
Set-Content -Path (Join-Path $userBin "pacar-ai.cmd") -Value $cmdScript -Force

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$userBin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$userBin", "User")
    $env:Path = "$env:Path;$userBin"
    Write-Host "  ✓ Added $userBin to system PATH." -ForegroundColor Green
}
Write-Host "  ✓ Global CLI registered: 'waifu', 'pacar-ai'" -ForegroundColor Green

# 6. Run Configuration Wizard (Interactive 7-Step Model & Autorun Setup)
Write-Host "[6/6] Launching Interactive Setup Wizard..." -ForegroundColor Cyan
& $py setup.py --wizard

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "  🎉 INSTALLATION COMPLETE! Waifu on Telegram is ready." -ForegroundColor Green
Write-Host "  Global CLI : waifu start / waifu status / waifu setup" -ForegroundColor Cyan
Write-Host "  Folder Root: $installDir" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""
$startNow = Read-Host "Would you like to start the bot right now? [Y/n, default: Y]"
if ($startNow.Trim().ToLower() -ne "n") {
    Write-Host "Starting bot in background (Daemon Mode)..." -ForegroundColor Cyan
    & (Join-Path $userBin "waifu.cmd") start --daemon
}

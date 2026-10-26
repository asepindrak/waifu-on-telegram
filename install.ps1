# ==============================================================================
# Waifu on Telegram - 1-Line Universal Windows Auto-Installer
# Compatible with: irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.ps1 | iex
# ==============================================================================
$ErrorActionPreference = "Stop"

function Write-GradientHeader {
    Write-Host "====================================================================" -ForegroundColor Magenta
    $ver = if (Test-Path "VERSION") { (Get-Content "VERSION").Trim() } else { "1.6.8" }
    Write-Host "   💖 WAIFU ON TELEGRAM v$ver - Windows One-Click All-in-One Installer 🌸   " -ForegroundColor Magenta
    Write-Host "====================================================================" -ForegroundColor Magenta
    Write-Host ""
}

function Download-FileWithProgress {
    param(
        [string]$Url,
        [string]$DestinationPath,
        [string]$Description
    )
    if (Test-Path $DestinationPath) {
        $size = (Get-Item $DestinationPath).Length
        if ($size -gt 1024*1024) {
            Write-Host "  ✓ $Description already downloaded: $DestinationPath ($([math]::Round($size / 1MB, 1)) MB)" -ForegroundColor Green
            return $true
        }
    }
    Write-Host "  ⏳ Downloading $Description..." -ForegroundColor Yellow
    Write-Host "     Source: $Url" -ForegroundColor DarkGray
    Write-Host "     Dest  : $DestinationPath" -ForegroundColor DarkGray

    $destDir = Split-Path -Parent $DestinationPath
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }

    try {
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            & curl.exe -L -C - --retry 3 --progress-bar -o "$DestinationPath" "$Url"
        } else {
            Import-Module BitsTransfer -ErrorAction SilentlyContinue
            if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
                Start-BitsTransfer -Source $Url -Destination $DestinationPath -DisplayName $Description
            } else {
                $wc = New-Object System.Net.WebClient
                $wc.DownloadFile($Url, $DestinationPath)
            }
        }
        if (Test-Path $DestinationPath) {
            $fSize = (Get-Item $DestinationPath).Length
            Write-Host "  ✓ $Description downloaded successfully ($([math]::Round($fSize / 1MB, 1)) MB)" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "  ⚠️ Download failed: $_" -ForegroundColor Red
        return $false
    }
    return $false
}

Write-GradientHeader

# 1. Target Directory & Clone / Download
$repoUrl = "https://github.com/asepindrak/waifu-on-telegram.git"
$zipUrl = "https://github.com/asepindrak/waifu-on-telegram/archive/refs/heads/main.zip"
$defaultInstallDir = Join-Path $env:USERPROFILE "waifu-on-telegram"

if ((Test-Path "bot.py") -and (Test-Path "setup.py")) {
    $installDir = (Get-Location).Path
    Write-Host "[1/8] Running inside project folder: $installDir" -ForegroundColor Cyan
} else {
    $installDir = $defaultInstallDir
    Write-Host "[1/8] Target installation directory: $installDir" -ForegroundColor Cyan

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
Write-Host "`n[2/8] Checking Python environment..." -ForegroundColor Cyan
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
Write-Host "`n[3/8] Installing Python requirements..." -ForegroundColor Cyan
& $py -m pip install -r requirements.txt --quiet --disable-pip-version-check
Write-Host "  ✓ Dependencies installed successfully." -ForegroundColor Green

# 4. Check & Setup Local LLM (Locally Uncensored / llama-server)
Write-Host "`n[4/8] Checking Local LLM Backend (Chat Engine)..." -ForegroundColor Cyan
$llmOnline = $false
foreach ($port in @(8127, 11434, 1234)) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $port)
        $tcp.Close()
        $llmOnline = $true
        Write-Host "  ✓ Local LLM Server detected active on port $port!" -ForegroundColor Green
        break
    } catch {}
}

if (-not $llmOnline) {
    # Check if Locally Uncensored models exist
    $luDir = Join-Path $env:APPDATA "Locally Uncensored\models"
    $localGguf = @()
    if (Test-Path $luDir) {
        $localGguf = Get-ChildItem -Path $luDir -Filter "*.gguf" -ErrorAction SilentlyContinue
    }
    if ($localGguf.Count -gt 0) {
        Write-Host "  ✓ Locally Uncensored model found: $($localGguf[0].Name)" -ForegroundColor Green
    } else {
        Write-Host "  ℹ No local LLM currently running on ports 8127/11434/1234." -ForegroundColor Yellow
        $dlLlm = Read-Host "  Would you like to auto-download Portable llama-server + Uncensored GGUF Model (~4.5 GB)? [Y/n, default: Y]"
        if ($dlLlm.Trim().ToLower() -ne "n") {
            $llmToolsDir = Join-Path $installDir "tools\llama-server"
            $llmModelDir = Join-Path $installDir "models\llm"
            New-Item -ItemType Directory -Force -Path $llmToolsDir | Out-Null
            New-Item -ItemType Directory -Force -Path $llmModelDir | Out-Null

            # 1. Download portable llama-server binary
            $llamaZipUrl = "https://github.com/ggerganov/llama.cpp/releases/download/b4800/llama-b4800-bin-win-cuda-cu12.4-x64.zip"
            $llamaZipDest = Join-Path $llmToolsDir "llama-server.zip"
            $ok = Download-FileWithProgress -Url $llamaZipUrl -DestinationPath $llamaZipDest -Description "Portable llama-server (CUDA GPU Accelerated)"
            if ($ok) {
                Expand-Archive -Path $llamaZipDest -DestinationPath $llmToolsDir -Force
                Remove-Item -Path $llamaZipDest -Force -ErrorAction SilentlyContinue
            }

            # 2. Download Uncensored Qwen2.5-7B
            $ggufUrl = "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf"
            $ggufDest = Join-Path $llmModelDir "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
            Download-FileWithProgress -Url $ggufUrl -DestinationPath $ggufDest -Description "Uncensored LLM GGUF Model (~4.5 GB)"

            # Create quick start script for LLM server
            $startLlmScript = "@echo off`r`ncd /d `"%~dp0`"`r`ntools\\llama-server\\llama-server.exe -m models\\llm\\Qwen2.5-7B-Instruct-Q4_K_M.gguf --port 8127 -ngl 99 -c 8192`r`npause"
            Set-Content -Path (Join-Path $installDir "start_llm.bat") -Value $startLlmScript -Force
            Write-Host "  ✓ Created 'start_llm.bat' launcher for Local LLM." -ForegroundColor Green
        }
    }
}

# 5. Check & Setup ComfyUI & Models (MeinaMix & AnimateDiff)
Write-Host "`n[5/8] Checking ComfyUI & Generative Models (Photos & Videos)..." -ForegroundColor Cyan
$comfyDirs = @(
    Join-Path $env:LOCALAPPDATA "Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI",
    Join-Path $env:LOCALAPPDATA "Comfy-Desktop\ComfyUI-Shared",
    "C:\ComfyUI",
    (Join-Path $env:USERPROFILE "ComfyUI"),
    (Join-Path $installDir "tools\ComfyUI")
)
$foundComfy = $null
foreach ($cd in $comfyDirs) {
    if (Test-Path (Join-Path $cd "models")) {
        $foundComfy = $cd
        break
    }
}

if ($foundComfy) {
    Write-Host "  ✓ ComfyUI installation detected at: $foundComfy" -ForegroundColor Green

    # Check Anime Checkpoint (MeinaMix)
    $ckptDir = Join-Path $foundComfy "models\checkpoints"
    $hasCkpt = $false
    if (Test-Path $ckptDir) {
        $ckpts = Get-ChildItem -Path $ckptDir -Include "*.safetensors", "*.ckpt" -Recurse -ErrorAction SilentlyContinue
        if ($ckpts.Count -gt 0) {
            $hasCkpt = $true
            Write-Host "  ✓ Checkpoints detected ($($ckpts.Count) models found, e.g. $($ckpts[0].Name))" -ForegroundColor Green
        }
    }
    if (-not $hasCkpt) {
        $dlCkpt = Read-Host "  Anime Checkpoint model not found. Auto-download MeinaMix SD 1.5 (~2 GB)? [Y/n, default: Y]"
        if ($dlCkpt.Trim().ToLower() -ne "n") {
            $meinaUrl = "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors"
            $meinaDest = Join-Path $ckptDir "MeinaMix_v11.safetensors"
            Download-FileWithProgress -Url $meinaUrl -DestinationPath $meinaDest -Description "MeinaMix v11 Anime SD 1.5 (~2 GB)"
        }
    }

    # Check AnimateDiff Motion Module (mm_sd_v15_v2.ckpt)
    $animDir = Join-Path $foundComfy "custom_nodes\ComfyUI-AnimateDiff-Evolved\models"
    $animDirAlt = Join-Path $foundComfy "models\animatediff_models"
    $hasAnim = (Test-Path (Join-Path $animDir "mm_sd_v15_v2.ckpt")) -or (Test-Path (Join-Path $animDirAlt "mm_sd_v15_v2.ckpt"))
    if ($hasAnim) {
        Write-Host "  ✓ AnimateDiff motion module detected (mm_sd_v15_v2.ckpt)" -ForegroundColor Green
    } else {
        $dlAnim = Read-Host "  AnimateDiff motion module missing. Auto-download mm_sd_v15_v2.ckpt (~1.8 GB)? [Y/n, default: Y]"
        if ($dlAnim.Trim().ToLower() -ne "n") {
            $targetAnimDir = if (Test-Path (Join-Path $foundComfy "custom_nodes\ComfyUI-AnimateDiff-Evolved")) { $animDir } else { $animDirAlt }
            $animUrl = "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt"
            $animDest = Join-Path $targetAnimDir "mm_sd_v15_v2.ckpt"
            Download-FileWithProgress -Url $animUrl -DestinationPath $animDest -Description "AnimateDiff Motion Module mm_sd_v15_v2.ckpt (~1.8 GB)"
        }
    }
} else {
    Write-Host "  ℹ ComfyUI not detected locally." -ForegroundColor Yellow
    $dlComfy = Read-Host "  Would you like to auto-download official ComfyUI Windows Portable (~1.4 GB)? [Y/n, default: Y]"
    if ($dlComfy.Trim().ToLower() -ne "n") {
        $comfyToolDir = Join-Path $installDir "tools\ComfyUI"
        New-Item -ItemType Directory -Force -Path $comfyToolDir | Out-Null
        $comfyZipUrl = "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z"
        $comfyZipDest = Join-Path $installDir "tools\ComfyUI_portable.7z"
        $ok = Download-FileWithProgress -Url $comfyZipUrl -DestinationPath $comfyZipDest -Description "ComfyUI Windows Portable (~1.4 GB)"
        if ($ok) {
            Write-Host "  Extracting ComfyUI Portable..." -ForegroundColor Yellow
            if (Get-Command 7z -ErrorAction SilentlyContinue) {
                & 7z x "$comfyZipDest" -o"$comfyToolDir" -y
            } else {
                Expand-Archive -Path $comfyZipDest -DestinationPath $comfyToolDir -Force
            }
            Remove-Item -Path $comfyZipDest -Force -ErrorAction SilentlyContinue

            # Download MeinaMix anime checkpoint
            $ckptDir = Join-Path $comfyToolDir "ComfyUI\models\checkpoints"
            $meinaUrl = "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors"
            $meinaDest = Join-Path $ckptDir "MeinaMix_v11.safetensors"
            Download-FileWithProgress -Url $meinaUrl -DestinationPath $meinaDest -Description "MeinaMix v11 Anime SD 1.5 (~2 GB)"
        }
    }
}

# 6. Check Node.js for Music Remote (Optional)
Write-Host "`n[6/8] Checking Node.js for PC Music Remote..." -ForegroundColor Cyan
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ Node.js found: $(node -v). Installing npm packages..." -ForegroundColor Green
    npm install --silent
} else {
    Write-Host "  ℹ Node.js not detected. Music remote feature will be disabled (chat & photos remain functional)." -ForegroundColor Yellow
}

# 7. Register Global CLI Commands (waifu, pacar-ai) in User PATH
Write-Host "`n[7/8] Registering global CLI commands (waifu, pacar-ai)..." -ForegroundColor Cyan
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

# 8. Run Configuration Wizard (Interactive Model & Autorun Setup)
Write-Host "`n[8/8] Launching Interactive Setup Wizard..." -ForegroundColor Cyan
& $py setup.py --wizard

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "  🎉 INSTALLATION COMPLETE! Waifu on Telegram is ready to run." -ForegroundColor Green
Write-Host "  Global CLI : waifu start / waifu status / waifu setup" -ForegroundColor Cyan
Write-Host "  Quick Run  : Double-click 'start.bat' or run 'waifu start'" -ForegroundColor Cyan
Write-Host "  Folder Root: $installDir" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""
$startNow = Read-Host "Would you like to start the bot right now? [Y/n, default: Y]"
if ($startNow.Trim().ToLower() -ne "n") {
    Write-Host "Starting bot in background (Daemon Mode)..." -ForegroundColor Cyan
    & (Join-Path $userBin "waifu.cmd") start --daemon
}

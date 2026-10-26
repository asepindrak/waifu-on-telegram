# ==============================================================================
# Waifu on Telegram - 1-Line Universal Windows Auto-Installer
# Compatible with: irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.ps1 | iex
# ==============================================================================
$ErrorActionPreference = "Stop"

function Write-GradientHeader {
    Write-Host "====================================================================" -ForegroundColor Magenta
    $ver = if (Test-Path "VERSION") { (Get-Content "VERSION").Trim() } else { "1.6.17" }
    Write-Host "   WAIFU ON TELEGRAM v$ver - Windows One-Click All-in-One Installer   " -ForegroundColor Magenta
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
            $sizeMb = [math]::Round($size / 1MB, 1)
            Write-Host "  [OK] $Description already downloaded: $DestinationPath ($sizeMb MB)" -ForegroundColor Green
            return $true
        }
    }
    Write-Host "  >> Downloading $Description..." -ForegroundColor Yellow
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
            $fSizeMb = [math]::Round($fSize / 1MB, 1)
            Write-Host "  [OK] $Description downloaded successfully ($fSizeMb MB)" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "  [!] Download failed: $_" -ForegroundColor Red
        return $false
    }
    return $false
}

Write-GradientHeader

# 1. Target Directory & Clone / Download
$repoUrl = "https://github.com/asepindrak/waifu-on-telegram.git"
$zipUrl = "https://github.com/asepindrak/waifu-on-telegram/archive/refs/heads/main.zip"
$defaultInstallDir = "$env:USERPROFILE\waifu-on-telegram"

if ((Test-Path "bot.py") -and (Test-Path "setup.py")) {
    $installDir = (Get-Location).Path
    Write-Host "[1/8] Running inside project folder: $installDir" -ForegroundColor Cyan
} else {
    $installDir = $defaultInstallDir
    Write-Host "[1/8] Target installation directory: $installDir" -ForegroundColor Cyan

    if (Test-Path "$installDir\.git") {
        Write-Host "  Updating existing Git repository..." -ForegroundColor Yellow
        Set-Location $installDir
        try { git pull --quiet } catch {}
    } elseif (Test-Path "$installDir\bot.py") {
        Write-Host "  Project folder exists. Using existing files..." -ForegroundColor Green
        Set-Location $installDir
    } else {
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Write-Host "  Cloning repository via Git..." -ForegroundColor Yellow
            git clone $repoUrl $installDir
            Set-Location $installDir
        } else {
            Write-Host "  Git not found. Downloading project ZIP archive..." -ForegroundColor Yellow
            $tempZip = "$env:TEMP\waifu-on-telegram-main.zip"
            Invoke-RestMethod -Uri $zipUrl -OutFile $tempZip
            $tempExtract = "$env:TEMP\waifu-on-telegram-extract"
            if (Test-Path $tempExtract) { Remove-Item -Path $tempExtract -Recurse -Force }
            Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
            $extractedRoot = "$tempExtract\waifu-on-telegram-main"
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
Write-Host "  [OK] Python: $pyVer" -ForegroundColor Green

# 3. Install Python Requirements
Write-Host "`n[3/8] Installing Python requirements..." -ForegroundColor Cyan
& $py -m pip install -r requirements.txt --quiet --disable-pip-version-check
Write-Host "  [OK] Dependencies installed successfully." -ForegroundColor Green

# 4. Check Local LLM Backend (Locally Uncensored / Ollama / llama-server)
Write-Host "`n[4/8] Checking Local LLM Backend (Chat Engine)..." -ForegroundColor Cyan
$llmOnline = $false
foreach ($port in @(8127, 11434, 1234)) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $port)
        $tcp.Close()
        $llmOnline = $true
        Write-Host "  [OK] Local LLM Server detected active on port $port!" -ForegroundColor Green
        break
    } catch {}
}

if (-not $llmOnline) {
    $luDir = "$env:APPDATA\Locally Uncensored\models"
    $localGguf = @()
    if (Test-Path $luDir) {
        $localGguf = Get-ChildItem -Path $luDir -Filter "*.gguf" -ErrorAction SilentlyContinue
    }
    if ($localGguf.Count -gt 0) {
        $sampleGguf = $localGguf[0].Name
        Write-Host "  [OK] Locally Uncensored model found: $sampleGguf" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] No local LLM currently active on port 8127. (Will connect when Locally Uncensored is launched)." -ForegroundColor DarkGray
    }
}

# 5. Check & Setup ComfyUI & Models (MeinaMix & AnimateDiff)
Write-Host "`n[5/8] Checking ComfyUI & Generative Models (Photos & Videos)..." -ForegroundColor Cyan
$foundComfy = $null

# 5.1 Check running process on port 8188 first
try {
    $procCmd = Get-NetTCPConnection -LocalPort 8188 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1 | ForEach-Object { (Get-CimInstance Win32_Process -Filter "ProcessId = $_" -ErrorAction SilentlyContinue).CommandLine }
    if ($procCmd) {
        foreach ($part in ($procCmd -split '"')) {
            $part = $part.Trim()
            if ($part -like "*main.py*" -or $part -like "*ComfyUI*" -or $part -like "*.venv*") {
                $p = Split-Path -Parent $part
                for ($lvl = 0; $lvl -lt 3; $lvl++) {
                    if (Test-Path "$p\models") {
                        $foundComfy = $p
                        break
                    }
                    $p = Split-Path -Parent $p
                }
                if ($foundComfy) { break }
            }
        }
    }
} catch {}

# 5.2 Check candidate folders across drives
if (-not $foundComfy) {
    $comfyDirs = @(
        "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI",
        "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Shared",
        "C:\ComfyUI",
        "D:\ComfyUI",
        "E:\ComfyUI",
        "$env:USERPROFILE\ComfyUI",
        "$env:USERPROFILE\ComfyUI_windows_portable\ComfyUI",
        "$installDir\tools\ComfyUI"
    )
    foreach ($cd in $comfyDirs) {
        if ($cd -and (Test-Path "$cd\models")) {
            $foundComfy = $cd
            break
        }
    }
}

if ($foundComfy) {
    Write-Host "  [OK] ComfyUI installation detected at: $foundComfy" -ForegroundColor Green

    # Check Anime Checkpoint (MeinaMix or similar)
    $ckptDir = "$foundComfy\models\checkpoints"
    $hasCkpt = $false
    if (Test-Path $ckptDir) {
        $ckpts = Get-ChildItem -Path $ckptDir -Filter "*.safetensors" -Recurse -ErrorAction SilentlyContinue
        if ($ckpts.Count -gt 0) {
            $hasCkpt = $true
            $ckptCount = $ckpts.Count
            $sampleName = $ckpts[0].Name
            Write-Host "  [OK] Anime Checkpoints detected: $ckptCount models found (e.g. $sampleName)" -ForegroundColor Green
        }
    }
    if (-not $hasCkpt) {
        $dlCkpt = Read-Host "  Anime Checkpoint model not found. Auto-download MeinaMix SD 1.5 (~2 GB)? [Y/n, default: Y]"
        if ($dlCkpt.Trim().ToLower() -ne "n") {
            $meinaUrl = "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors"
            $meinaDest = "$ckptDir\MeinaMix_v11.safetensors"
            Download-FileWithProgress -Url $meinaUrl -DestinationPath $meinaDest -Description "MeinaMix v11 Anime SD 1.5 (~2 GB)"
        }
    }

    # Check AnimateDiff Motion Module (mm_sd_v15_v2.ckpt)
    $animDir = "$foundComfy\custom_nodes\ComfyUI-AnimateDiff-Evolved\models"
    $animDirAlt = "$foundComfy\models\animatediff_models"
    $hasAnim = (Test-Path "$animDir\mm_sd_v15_v2.ckpt") -or (Test-Path "$animDirAlt\mm_sd_v15_v2.ckpt")
    if ($hasAnim) {
        Write-Host "  [OK] AnimateDiff motion module detected (mm_sd_v15_v2.ckpt)" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] AnimateDiff motion module is optional (Lazy Auto-Downloader will handle it on demand)." -ForegroundColor DarkGray
    }
} else {
    Write-Host "  [INFO] ComfyUI not detected locally." -ForegroundColor Yellow
    $dlComfy = Read-Host "  Would you like to auto-download official ComfyUI Windows Portable (~1.4 GB)? [Y/n, default: Y]"
    if ($dlComfy.Trim().ToLower() -ne "n") {
        $comfyToolDir = "$installDir\tools\ComfyUI"
        New-Item -ItemType Directory -Force -Path $comfyToolDir | Out-Null
        $comfyZipUrl = "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z"
        $comfyZipDest = "$installDir\tools\ComfyUI_portable.7z"
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
            $ckptDir = "$comfyToolDir\ComfyUI\models\checkpoints"
            $meinaUrl = "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V11%20-%20baked%20VAE.safetensors"
            $meinaDest = "$ckptDir\MeinaMix_v11.safetensors"
            Download-FileWithProgress -Url $meinaUrl -DestinationPath $meinaDest -Description "MeinaMix v11 Anime SD 1.5 (~2 GB)"
        }
    }
}

# 6. Check Node.js for Music Remote (Optional)
Write-Host "`n[6/8] Checking Node.js for PC Music Remote..." -ForegroundColor Cyan
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = & node -v
    Write-Host "  [OK] Node.js found: $nodeVer. Installing npm dependencies..." -ForegroundColor Green
    & npm install --no-audit --no-fund --silent
} else {
    Write-Host "  [INFO] Node.js not detected. PC Music remote feature disabled (all other features 100% active)." -ForegroundColor DarkGray
}

# 7. Register Global CLI Commands ('waifu')
Write-Host "`n[7/8] Registering Global CLI Command 'waifu'..." -ForegroundColor Cyan
$userBin = "$env:USERPROFILE\.local\bin"
if (-not (Test-Path $userBin)) { New-Item -ItemType Directory -Force -Path $userBin | Out-Null }

$cliPy = "$installDir\bin\cli.py"
$cmdScript = "@echo off`r`npython `"$cliPy`" %*"
Set-Content -Path "$userBin\waifu.cmd" -Value $cmdScript -Force
Set-Content -Path "$userBin\pacar-ai.cmd" -Value $cmdScript -Force

# Add to User PATH if not present
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$userBin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userBin;$userPath", "User")
    $env:Path = "$userBin;$env:Path"
    Write-Host "  [OK] Added '$userBin' to User PATH." -ForegroundColor Green
}
Write-Host "  [OK] Global CLI 'waifu' registered successfully." -ForegroundColor Green

# 8. Interactive Configuration Wizard
Write-Host "`n[8/8] Starting Interactive Configuration Manager..." -ForegroundColor Cyan
& $py setup.py

Write-Host "`n====================================================================" -ForegroundColor Green
Write-Host "  Installation completed successfully!" -ForegroundColor Green
Write-Host "  You can start your bot anytime using the command:" -ForegroundColor Cyan
Write-Host "    waifu start --daemon" -ForegroundColor Yellow
Write-Host "  To inspect system status: waifu status" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Green

$startNow = Read-Host "`nWould you like to start the bot right now? [Y/n, default: Y]"
if ($startNow.Trim().ToLower() -ne "n") {
    & "$userBin\waifu.cmd" start --daemon
}

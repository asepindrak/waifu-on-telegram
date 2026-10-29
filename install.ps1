# ==============================================================================
# Waifu on Telegram - 1-Line Universal Windows Auto-Installer
# Compatible with: irm https://raw.githubusercontent.com/asepindrak/waifu-on-telegram/main/install.ps1 | iex
# ==============================================================================
$ErrorActionPreference = "Stop"

function Write-GradientHeader {
    Write-Host "====================================================================" -ForegroundColor Magenta
    $ver = if (Test-Path "VERSION") { (Get-Content "VERSION").Trim() } else { "1.6.26" }
    Write-Host "   WAIFU ON TELEGRAM v$ver - Windows One-Click All-in-One Installer   " -ForegroundColor Magenta
    Write-Host "====================================================================" -ForegroundColor Magenta
    Write-Host ""
}

function Download-FileWithProgress {
    param(
        [string]$Url,
        [string]$DestinationPath,
        [string]$Description,
        [string]$FallbackUrl = ""
    )
    if (Test-Path $DestinationPath) {
        $size = (Get-Item $DestinationPath).Length
        if ($size -gt 1024*1024) {
            $sizeMb = [math]::Round($size / 1MB, 1)
            Write-Host "  [OK] $Description already downloaded: $DestinationPath ($sizeMb MB)" -ForegroundColor Green
            return $true
        }
    }

    $destDir = Split-Path -Parent $DestinationPath
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }

    $urlsToTry = @($Url)
    if ($FallbackUrl) { $urlsToTry += $FallbackUrl }

    foreach ($dlUrl in $urlsToTry) {
        Write-Host "  >> Downloading $Description..." -ForegroundColor Yellow
        Write-Host "     Source: $dlUrl" -ForegroundColor DarkGray
        Write-Host "     Dest  : $DestinationPath" -ForegroundColor DarkGray

        try {
            if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
                & curl.exe -fL -C - --retry 3 --progress-bar -o "$DestinationPath" "$dlUrl"
            } else {
                Import-Module BitsTransfer -ErrorAction SilentlyContinue
                if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
                    Start-BitsTransfer -Source $dlUrl -Destination $DestinationPath -DisplayName $Description
                } else {
                    $wc = New-Object System.Net.WebClient
                    $wc.DownloadFile($dlUrl, $DestinationPath)
                }
            }
            if (Test-Path $DestinationPath) {
                $fSize = (Get-Item $DestinationPath).Length
                if ($fSize -gt 1024*1024) {
                    $fSizeMb = [math]::Round($fSize / 1MB, 1)
                    Write-Host "  [OK] $Description downloaded successfully ($fSizeMb MB)" -ForegroundColor Green
                    return $true
                } else {
                    Remove-Item -Path $DestinationPath -Force -ErrorAction SilentlyContinue
                    Write-Host "  [!] Download resulted in invalid/empty file ($fSize bytes). Retrying fallback..." -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "  [!] Attempt failed: $_" -ForegroundColor Yellow
            Remove-Item -Path $DestinationPath -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  [!] All download attempts failed for $Description." -ForegroundColor Red
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

# 4. Check & Setup Local LLM Engine (KoboldCPP / Auto-loading Engine)
Write-Host "`n[4/8] Checking Local LLM Engine (Chat & Romance Brain)..." -ForegroundColor Cyan
$llmOnline = $false
foreach ($port in @(5001, 8127, 11434, 1234)) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $port)
        $tcp.Close()
        $llmOnline = $true
        Write-Host "  [OK] Local LLM Server detected active on port $port!" -ForegroundColor Green
        break
    } catch {}
}

$toolsDir = "$installDir\tools"
$modelsDir = "$installDir\models"
if (-not (Test-Path $toolsDir)) { New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null }
if (-not (Test-Path $modelsDir)) { New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null }

$kcppExe = "$toolsDir\koboldcpp.exe"
if (-not (Test-Path $kcppExe)) {
    Write-Host "  [INFO] Standalone auto-starting LLM engine (KoboldCPP) not installed." -ForegroundColor Yellow
    $dlKcpp = Read-Host "  Would you like to auto-download KoboldCPP Windows Portable (~150 MB)? [Y/n, default: Y]"
    if ($dlKcpp.Trim().ToLower() -ne "n") {
        $kcppUrl = "https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp.exe"
        Download-FileWithProgress -Url $kcppUrl -DestinationPath $kcppExe -Description "KoboldCPP Standalone LLM Server (~150 MB)"
    }
} else {
    Write-Host "  [OK] KoboldCPP LLM Engine detected: $kcppExe" -ForegroundColor Green
}

# Check for GGUF Brain Model
$existingGgufs = @(Get-ChildItem -Path $modelsDir -Filter "*.gguf" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*mmproj*" })
if ($existingGgufs.Count -eq 0) {
    # Check if user has GGUF files in Locally Uncensored or Downloads
    $luDir = "$env:APPDATA\Locally Uncensored\models"
    $foundCandidate = $null
    if (Test-Path $luDir) {
        $luGgufs = @(Get-ChildItem -Path $luDir -Filter "*.gguf" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*mmproj*" -and $_.Length -gt 500*1024*1024 })
        if ($luGgufs.Count -gt 0) {
            $foundCandidate = $luGgufs[0].FullName
        }
    }
    
    if ($foundCandidate) {
        $candName = Split-Path -Leaf $foundCandidate
        Write-Host "  [DETECTED] Found existing GGUF model in Locally Uncensored: $candName" -ForegroundColor Cyan
        $copyCand = Read-Host "  Copy this model to project for auto-start with KoboldCPP? [Y/n, default: Y]"
        if ($copyCand.Trim().ToLower() -ne "n") {
            Copy-Item -Path $foundCandidate -Destination "$modelsDir\$candName" -Force
            Write-Host "  [OK] Model copied successfully." -ForegroundColor Green
        }
    } else {
        Write-Host "  [INFO] No GGUF chat model found in '$modelsDir'." -ForegroundColor Yellow
        $dlModel = Read-Host "  Auto-download uncensored 'Huihui-Qwythos-9B-Claude-Mythos-5-1M' Q4_K model (~5.5 GB)? [Y/n, default: Y]"
        if ($dlModel.Trim().ToLower() -ne "n") {
            $qwythosUrl = "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
            $destGguf = "$modelsDir\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
            Download-FileWithProgress -Url $qwythosUrl -DestinationPath $destGguf -Description "Huihui-Qwythos 9B Abliterated Q4_K (~5.5 GB)"
        }
    }
} else {
    $activeGguf = $existingGgufs[0].Name
    Write-Host "  [OK] Local Chat & Romance GGUF Model detected: $activeGguf" -ForegroundColor Green
}

# Check for Vision Adapter (mmproj)
$existingMmproj = @(Get-ChildItem -Path $modelsDir -Filter "*mmproj*.gguf" -ErrorAction SilentlyContinue)
if ($existingMmproj.Count -eq 0) {
    # Check if user has mmproj in Locally Uncensored
    $luDir = "$env:APPDATA\Locally Uncensored\models"
    $foundMmprojCandidate = $null
    if (Test-Path $luDir) {
        $luMmprojs = @(Get-ChildItem -Path $luDir -Filter "*mmproj*.gguf" -ErrorAction SilentlyContinue)
        if ($luMmprojs.Count -gt 0) {
            $foundMmprojCandidate = $luMmprojs[0].FullName
        }
    }

    if ($foundMmprojCandidate) {
        $candMmprojName = Split-Path -Leaf $foundMmprojCandidate
        Write-Host "  [DETECTED] Found existing Vision Adapter in Locally Uncensored: $candMmprojName" -ForegroundColor Cyan
        Copy-Item -Path $foundMmprojCandidate -Destination "$modelsDir\$candMmprojName" -Force
        Write-Host "  [OK] Vision adapter copied successfully." -ForegroundColor Green
    } else {
        Write-Host "  [INFO] Vision adapter (mmproj) not found in '$modelsDir'." -ForegroundColor Yellow
        $dlVision = Read-Host "  Auto-download Huihui-Qwythos Vision Adapter (~879 MB) so waifu can see photos? [Y/n, default: Y]"
        if ($dlVision.Trim().ToLower() -ne "n") {
            $visionUrl = "https://huggingface.co/huihui-ai/Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-GGUF/resolve/main/mmproj-model-bf16.gguf"
            $destMmproj = "$modelsDir\Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.mmproj.gguf"
            Download-FileWithProgress -Url $visionUrl -DestinationPath $destMmproj -Description "Huihui-Qwythos Vision Adapter (~879 MB)"
        }
    }
} else {
    $activeMmproj = $existingMmproj[0].Name
    Write-Host "  [OK] Vision Adapter detected: $activeMmproj" -ForegroundColor Green
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
    # Clean up obsolete phantom directory if created by older installer
    $phantomComfy = "$installDir\tools\ComfyUI\ComfyUI"
    if ((Test-Path $phantomComfy) -and (-not (Test-Path "$phantomComfy\main.py"))) {
        Remove-Item -Path $phantomComfy -Recurse -Force -ErrorAction SilentlyContinue
    }
    $comfyDirs = @(
        "$installDir\tools\ComfyUI\ComfyUI_windows_portable\ComfyUI",
        "$installDir\tools\ComfyUI",
        "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI",
        "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Shared",
        "C:\ComfyUI",
        "D:\ComfyUI",
        "E:\ComfyUI",
        "$env:USERPROFILE\ComfyUI",
        "$env:USERPROFILE\ComfyUI_windows_portable\ComfyUI"
    )
    foreach ($cd in $comfyDirs) {
        if ($cd -and (Test-Path "$cd\main.py") -and (Test-Path "$cd\models")) {
            $foundComfy = $cd
            break
        } elseif ($cd -and (Test-Path "$cd\ComfyUI\main.py") -and (Test-Path "$cd\ComfyUI\models")) {
            $foundComfy = "$cd\ComfyUI"
            break
        } elseif ($cd -and (Test-Path "$cd\ComfyUI_windows_portable\ComfyUI\main.py")) {
            $foundComfy = "$cd\ComfyUI_windows_portable\ComfyUI"
            break
        }
    }
}

function Select-And-Download-AnimeCheckpoint {
    param (
        [string]$targetComfyDir
    )
    $ckptDir = "$targetComfyDir\models\checkpoints"
    if (-not (Test-Path $ckptDir)) { New-Item -ItemType Directory -Force -Path $ckptDir | Out-Null }

    Write-Host "`n  🎨 Pilih Model Ilustrasi Anime untuk Generasi Foto Waifu (ComfyUI):" -ForegroundColor Cyan
    Write-Host "    [1] ✨ MeinaMix v12 (Anime SD 1.5 - ~2.0 GB) [Rekomendasi GPU 4GB-8GB VRAM: Cepat & Ringan]" -ForegroundColor White
    Write-Host "    [2] 🌟 万象熔炉 | Anything XL (Anime SDXL 1.0 - ~6.6 GB) [Rekomendasi GPU 8GB+ VRAM: 1024px Ultra Jernih]" -ForegroundColor White
    Write-Host "    [3] ☁️ Lewati download model sekarang (Gunakan Cloud Fallback Engine / Unduh nanti)" -ForegroundColor White
    $imgChoice = Read-Host "  Pilih model foto [1/2/3, default: 1]"
    $imgChoice = $imgChoice.Trim()

    $selectedCkpt = "meinamix_v12Final.safetensors"
    if ($imgChoice -eq "2") {
        $xlUrl = "https://huggingface.co/artificialguybr/Anything-XL/resolve/main/AnythingXL_xl.safetensors"
        $xlFallback = "https://hf-mirror.com/artificialguybr/Anything-XL/resolve/main/AnythingXL_xl.safetensors"
        $xlDest = "$ckptDir\AnythingXL_xl.safetensors"
        Download-FileWithProgress -Url $xlUrl -DestinationPath $xlDest -Description "万象熔炉 | Anything XL SDXL (~6.6 GB)" -FallbackUrl $xlFallback
        $selectedCkpt = "AnythingXL_xl.safetensors"
    } elseif ($imgChoice -eq "3") {
        Write-Host "  [INFO] Melewati unduhan model lokal. Foto waifu dapat menggunakan Cloud Fallback Engine." -ForegroundColor DarkGray
        $selectedCkpt = ""
    } else {
        $meinaUrl = "https://civitai.com/api/download/models/119057?type=Model&format=SafeTensor&size=pruned&fp=fp16"
        $meinaDest = "$ckptDir\meinamix_v12Final.safetensors"
        $meinaFallback = "https://huggingface.co/Meina/MeinaMix/resolve/main/Meina%20V10%20-%20baked%20VAE.safetensors"
        Download-FileWithProgress -Url $meinaUrl -DestinationPath $meinaDest -Description "MeinaMix v12 Anime SD 1.5 (~2 GB)" -FallbackUrl $meinaFallback
        $selectedCkpt = "meinamix_v12Final.safetensors"
    }

    if ($selectedCkpt) {
        $envFile = "$installDir\.env"
        if (Test-Path $envFile) {
            $content = Get-Content $envFile -Raw
            if ($content -match "COMFYUI_CHECKPOINT=") {
                $content = $content -replace "COMFYUI_CHECKPOINT=.*", "COMFYUI_CHECKPOINT=$selectedCkpt"
            } else {
                $content += "`nCOMFYUI_CHECKPOINT=$selectedCkpt"
            }
            Set-Content -Path $envFile -Value $content -Force
        }
    }
}

if ($foundComfy) {
    Write-Host "  [OK] ComfyUI installation detected at: $foundComfy" -ForegroundColor Green

    # Check Anime Checkpoint (MeinaMix or similar)
    $ckptDir = "$foundComfy\models\checkpoints"
    $hasCkpt = $false
    if (Test-Path $ckptDir) {
        $ckpts = Get-ChildItem -Path $ckptDir -Filter "*.safetensors" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 10*1024*1024 }
        if ($ckpts.Count -gt 0) {
            $hasCkpt = $true
            $ckptCount = $ckpts.Count
            $sampleName = $ckpts[0].Name
            Write-Host "  [OK] Anime Checkpoints detected: $ckptCount models found (e.g. $sampleName)" -ForegroundColor Green
        }
    }
    if (-not $hasCkpt) {
        Select-And-Download-AnimeCheckpoint -targetComfyDir $foundComfy
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
            } elseif (Get-Command tar.exe -ErrorAction SilentlyContinue) {
                & tar.exe -xf "$comfyZipDest" -C "$comfyToolDir"
            } else {
                Write-Host "  >> Downloading 7-Zip standalone extractor..." -ForegroundColor Yellow
                $sevenZipUrl = "https://www.7-zip.org/a/7zr.exe"
                $sevenZipExe = "$env:TEMP\7zr.exe"
                Invoke-WebRequest -Uri $sevenZipUrl -OutFile $sevenZipExe
                & $sevenZipExe x "$comfyZipDest" -o"$comfyToolDir" -y
                Remove-Item -Path $sevenZipExe -Force -ErrorAction SilentlyContinue
            }
            Remove-Item -Path $comfyZipDest -Force -ErrorAction SilentlyContinue

            # Dynamically locate extracted ComfyUI directory
            $detectedComfy = $null
            $candidatesAfterExtract = @(
                "$comfyToolDir\ComfyUI_windows_portable\ComfyUI",
                "$comfyToolDir\ComfyUI",
                "$comfyToolDir"
            )
            foreach ($c in $candidatesAfterExtract) {
                if ((Test-Path "$c\main.py") -and (Test-Path "$c\models")) {
                    $detectedComfy = $c
                    break
                }
            }
            if (-not $detectedComfy) {
                $foundMain = Get-ChildItem -Path $comfyToolDir -Filter "main.py" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($foundMain) {
                    $detectedComfy = Split-Path -Parent $foundMain.FullName
                }
            }

            if ($detectedComfy) {
                $foundComfy = $detectedComfy
                Write-Host "  [OK] ComfyUI Portable ready at: $foundComfy" -ForegroundColor Green
                Select-And-Download-AnimeCheckpoint -targetComfyDir $foundComfy
            }
        }
    }
}

# 6. Check & Auto-Install Node.js for PC Music Remote
Write-Host "`n[6/8] Checking Node.js for PC Music Remote..." -ForegroundColor Cyan

$hasNode = $false
if (Get-Command node -ErrorAction SilentlyContinue) {
    $hasNode = $true
} else {
    $localNode = "$installDir\tools\nodejs\node.exe"
    if (Test-Path $localNode) {
        $nodeDir = Split-Path -Parent $localNode
        $env:Path = "$nodeDir;$env:Path"
        $hasNode = $true
    }
}

if (-not $hasNode) {
    Write-Host "  >> Node.js not found. Auto-installing Node.js for Music Remote..." -ForegroundColor Yellow
    $installedViaWinget = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        try {
            Write-Host "     Attempting install via winget..." -ForegroundColor DarkGray
            & winget install OpenJS.NodeJS.LTS -e --silent --accept-package-agreements --accept-source-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            if (Get-Command node -ErrorAction SilentlyContinue) {
                $installedViaWinget = $true
                $hasNode = $true
            }
        } catch {}
    }

    if (-not $installedViaWinget) {
        # Portable Node.js fallback (Zero admin required, 100% standalone)
        $nodeToolDir = "$installDir\tools\nodejs"
        New-Item -ItemType Directory -Force -Path $nodeToolDir | Out-Null
        $nodeZipUrl = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-win-x64.zip"
        $nodeZipDest = "$installDir\tools\nodejs_portable.zip"
        $ok = Download-FileWithProgress -Url $nodeZipUrl -DestinationPath $nodeZipDest -Description "Node.js LTS Standalone (~30 MB)"
        if ($ok) {
            Write-Host "  Extracting Node.js Portable..." -ForegroundColor Yellow
            $tempExtract = "$env:TEMP\node_extract"
            if (Test-Path $tempExtract) { Remove-Item -Path $tempExtract -Recurse -Force }
            Expand-Archive -Path $nodeZipDest -DestinationPath $tempExtract -Force
            $extractedFolder = Get-ChildItem -Path $tempExtract -Directory | Select-Object -First 1
            if ($extractedFolder) {
                Copy-Item -Path "$($extractedFolder.FullName)\*" -Destination $nodeToolDir -Recurse -Force
            }
            Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item -Path $nodeZipDest -Force -ErrorAction SilentlyContinue

            $env:Path = "$nodeToolDir;$env:Path"
            $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($userPath -notlike "*$nodeToolDir*") {
                [Environment]::SetEnvironmentVariable("Path", "$nodeToolDir;$userPath", "User")
            }
            $hasNode = $true
        }
    }
}

if ($hasNode -or (Get-Command node -ErrorAction SilentlyContinue)) {
    $nodeVer = & node -v
    Write-Host "  [OK] Node.js active: $nodeVer. Installing npm dependencies..." -ForegroundColor Green
    & npm install --no-audit --no-fund --silent
    Write-Host "  [OK] YouTube Music Remote dependencies installed successfully." -ForegroundColor Green
} else {
    Write-Host "  [WARNING] Could not auto-install Node.js. PC Music remote feature disabled." -ForegroundColor Yellow
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

# 8. Configure Windows Startup Autorun (Auto-start on PC boot)
Write-Host "`n[8/9] Enabling Windows Startup Autorun (Runs automatically on PC boot)..." -ForegroundColor Cyan
$enableAutostartPs1 = "$installDir\enable_autostart.ps1"
if (Test-Path $enableAutostartPs1) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $enableAutostartPs1
}

# 9. Interactive Configuration Wizard
Write-Host "`n[9/9] Starting Interactive Configuration Manager..." -ForegroundColor Cyan
& $py setup.py

Write-Host "`n====================================================================" -ForegroundColor Green
Write-Host "  Installation completed successfully!" -ForegroundColor Green
Write-Host "  You can manage your bot anytime using the command:" -ForegroundColor Cyan
Write-Host "    waifu start --daemon" -ForegroundColor Yellow
Write-Host "  To inspect system status: waifu status" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Green

$startNow = Read-Host "`nWould you like to start the bot right now? [Y/n, default: Y]"
if ($startNow.Trim().ToLower() -ne "n") {
    & "$userBin\waifu.cmd" start --daemon
    Start-Sleep -Seconds 3
    & "$userBin\waifu.cmd" status
}

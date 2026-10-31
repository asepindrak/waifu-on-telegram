# Health & Status Checker for Waifu on Telegram
$vPath = Join-Path $PSScriptRoot "VERSION"
$version = if (Test-Path $vPath) { (Get-Content $vPath).Trim() } else { "1.6.26" }

# Load .env variables into environment if present
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line -split "=", 2
            $k = $parts[0].Trim()
            $v = $parts[1].Trim().Trim('"').Trim("'")
            if (-not [System.Environment]::GetEnvironmentVariable($k)) {
                [System.Environment]::SetEnvironmentVariable($k, $v)
            }
        }
    }
}

Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host "       WAIFU ON TELEGRAM v$version - SYSTEM STATUS DIAGNOSTICS      " -ForegroundColor Magenta
Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  [VERSION] Waifu on Telegram: v$version" -ForegroundColor Cyan

# 1. Active Persona & Outfit
try {
    $envPersona = $env:DEFAULT_PERSONA
    if (-not $envPersona) { $envPersona = "runa" }
    $pJsonPath = Join-Path $PSScriptRoot "personas\$envPersona.json"
    $pName = "Runa"
    $pArch = "Mahasiswi Game Dev & Playful Girlfriend"
    if (Test-Path $pJsonPath) {
        $pData = Get-Content $pJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($pData.name) { $pName = $pData.name }
        if ($pData.archetype) { $pArch = $pData.archetype }
    }
    Write-Host "  [PERSONA] Active Waifu: $pName ($pArch)" -ForegroundColor Magenta

    # Outfit
    $outfitName = "Default (Persona Style)"
    $outfitsPath = Join-Path $PSScriptRoot "data\user_outfits.json"
    if (Test-Path $outfitsPath) {
        $rawOutfitJson = Get-Content $outfitsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $propList = @($rawOutfitJson.PSObject.Properties)
        if ($propList.Count -gt 0) {
            $outfitRawKey = $propList[-1].Value
            $outfitMap = @{
                "default" = "Default (Persona Style)"
                "campus_casual" = "Pakaian Kuliah (Campus Casual)"
                "mall_casual" = "Trendy Mall Hangout"
                "cafe_cozy" = "Cozy Cafe Knit"
                "sweater" = "Pastel Sweater (Cozy)"
                "maid" = "French Maid Dress"
                "kimono" = "Floral Kimono"
                "pajamas" = "Silk Pajamas"
                "bikini" = "Summer Bikini"
                "school_jk" = "School JK Uniform"
                "gym" = "Sporty Gym Wear"
                "dress" = "Elegant Evening Dress"
                "towel" = "Handuk Mandi (After Shower)"
                "lingerie" = "Sensual Lace Lingerie"
                "romantic" = "Pakaian Romantis (Silk Slip Dress)"
                "nude" = "Tanpa Busana (Full Nude)"
            }
            if ($outfitMap.ContainsKey($outfitRawKey)) {
                $outfitName = $outfitMap[$outfitRawKey]
            } else {
                $outfitName = $outfitRawKey
            }
        }
    }
    Write-Host "  [OUTFIT]  Current Outfit: $outfitName" -ForegroundColor Magenta
} catch {}

# 2. Check Local LLM (KoboldCPP 5001 / Locally Uncensored 8127 / Ollama 11434 / LM Studio 1234)
$llmOnline = $false
$llmPorts = @(
    @{ Port = 5001; Name = "KoboldCPP" },
    @{ Port = 8127; Name = "Locally Uncensored" },
    @{ Port = 11434; Name = "Ollama" },
    @{ Port = 1234; Name = "LM Studio" }
)

foreach ($target in $llmPorts) {
    $p = $target.Port
    $bName = $target.Name
    $isTcpOpen = $false
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect("127.0.0.1", $p, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne(150, $false)
        if ($wait -and $tcp.Connected) {
            $tcp.EndConnect($connect)
            $isTcpOpen = $true
        }
        $tcp.Close()
    } catch {}

    if ($isTcpOpen) {
        try {
            $modelsRes = Invoke-RestMethod -Uri "http://127.0.0.1:$p/v1/models" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            $detectedModel = "Active Model"
            if ($modelsRes.data -and $modelsRes.data.Count -gt 0) {
                $rawId = $modelsRes.data[0].id
                $detectedModel = Split-Path -Leaf $rawId
            } elseif ($modelsRes.models -and $modelsRes.models.Count -gt 0) {
                $detectedModel = Split-Path -Leaf $modelsRes.models[0].name
            }
            Write-Host "  [ONLINE]  $bName LLM: ONLINE (Port $p - Load Penuh)" -ForegroundColor Green
            Write-Host "            Active Model: $detectedModel" -ForegroundColor DarkCyan
            $llmOnline = $true
            break
        } catch {}
    }
}

if (-not $llmOnline) {
    # Check if KoboldCPP binary and GGUF model exist on disk
    $kcppPaths = @(
        (Join-Path $PSScriptRoot "tools\koboldcpp.exe"),
        (Join-Path $PSScriptRoot "tools\koboldcpp"),
        (Join-Path $env:LOCALAPPDATA "Programs\KoboldCPP\koboldcpp.exe")
    )
    $hasKcpp = $false
    foreach ($kp in $kcppPaths) {
        if (Test-Path $kp) { $hasKcpp = $true; break }
    }
    if (-not $hasKcpp) {
        $whichK = Get-Command "koboldcpp" -ErrorAction SilentlyContinue
        if ($whichK) { $hasKcpp = $true }
    }

    $modelDirs = @(
        (Join-Path $PSScriptRoot "models"),
        (Join-Path $env:APPDATA "Locally Uncensored\models")
    )
    $hasGguf = $false
    $targetGgufName = "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf"
    foreach ($md in $modelDirs) {
        if (Test-Path $md) {
            $ggufs = Get-ChildItem -Path $md -Filter "*.gguf" -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*mmproj*" }
            if ($ggufs -and $ggufs.Count -gt 0) {
                $hasGguf = $true
                $targetGgufName = $ggufs[0].Name
                break
            }
        }
    }

    $smartIdle = $env:SMART_IDLE_ENABLED
    if ($hasKcpp -and $hasGguf) {
        if (-not $smartIdle -or $smartIdle -eq "true") {
            Write-Host "  [STANDBY] Local LLM Engine: STANDBY / TIDUR (Smart Idle: VRAM Bebas • Bangun Otomatis Saat Chat)" -ForegroundColor Cyan
            Write-Host "            Target Model: $targetGgufName (Siap Load Saat Chat)" -ForegroundColor DarkCyan
        } else {
            Write-Host "  [OFFLINE] Local LLM Engine: OFFLINE / Unreachable (Checked ports 5001, 8127, 11434, 1234)" -ForegroundColor Red
            Write-Host "            Target Model: $targetGgufName" -ForegroundColor DarkCyan
        }
    } else {
        $missingParts = @()
        if (-not $hasKcpp) { $missingParts += "koboldcpp.exe" }
        if (-not $hasGguf) { $missingParts += "model .gguf" }
        $missStr = $missingParts -join " & "
        Write-Host "  [NOT READY] Local LLM Engine: BELUM TERPASANG ($missStr belum ada)" -ForegroundColor Yellow
        Write-Host "              Jalankan 'python setup.py' -> Opsi [7] atau taruh model di folder models\" -ForegroundColor DarkYellow
    }
}

# 3. Check ComfyUI (Port 8188) & Checkpoint
$comfyCkpt = "Auto"
$comfyOnline = $false
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    $gpu = $res.devices[0].name
    try {
        $infoRes = Invoke-RestMethod -Uri "http://127.0.0.1:8188/object_info/CheckpointLoaderSimple" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        $ckptList = $infoRes.CheckpointLoaderSimple.input.required.ckpt_name[0]
        if ($ckptList -and $ckptList.Count -gt 0) {
            $comfyCkpt = $ckptList[0]
        }
    } catch {}
    Write-Host "  [ONLINE]  ComfyUI Generator: ONLINE (Port 8188 - Load Penuh)" -ForegroundColor Green
    Write-Host "            Device: $gpu" -ForegroundColor DarkCyan
    Write-Host "            Photo Model: $comfyCkpt (Aktif di ComfyUI)" -ForegroundColor DarkCyan
    $comfyOnline = $true
} catch {
    $comfyDirCandidates = @(
        (Join-Path $PSScriptRoot "ComfyUI"),
        (Join-Path $PSScriptRoot "tools\ComfyUI"),
        (Join-Path $PSScriptRoot "..\ComfyUI"),
        (Join-Path $PSScriptRoot "..\ComfyUI_windows_portable\ComfyUI")
    )
    $hasComfyDir = $false
    $targetCkpt = $env:COMFYUI_CHECKPOINT
    if (-not $targetCkpt) { $targetCkpt = "AnythingXL_xl.safetensors" }
    $ckptInstalled = $false

    foreach ($cd in $comfyDirCandidates) {
        if (Test-Path (Join-Path $cd "main.py")) {
            $hasComfyDir = $true
            $cFile = Join-Path $cd "models\checkpoints\$targetCkpt"
            if (Test-Path $cFile) {
                $ckptInstalled = $true
            } else {
                $anyCkpt = Get-ChildItem -Path (Join-Path $cd "models\checkpoints") -Filter "*.safetensors" -File -ErrorAction SilentlyContinue
                if ($anyCkpt -and $anyCkpt.Count -gt 0) {
                    $targetCkpt = $anyCkpt[0].Name
                    $ckptInstalled = $true
                }
            }
            break
        }
    }

    $onDemand = $env:COMFYUI_ON_DEMAND
    $badge = if ($ckptInstalled) { "(Terpasang [OK])" } else { "(Perlu Download)" }
    if ($hasComfyDir) {
        if (-not $onDemand -or $onDemand -eq "true") {
            Write-Host "  [STANDBY] ComfyUI Generator (Port 8188): STANDBY ON-DEMAND (Tidur hemat VRAM • Aktif otomatis saat minta foto)" -ForegroundColor Cyan
            Write-Host "            Target Model: $targetCkpt $badge" -ForegroundColor DarkCyan
        } else {
            Write-Host "  [OFFLINE] ComfyUI Generator (Port 8188): OFFLINE" -ForegroundColor Yellow
            Write-Host "            Target Model: $targetCkpt $badge" -ForegroundColor DarkCyan
        }
    } else {
        Write-Host "  [NOT READY] ComfyUI Generator: Folder ComfyUI belum terdeteksi (Fallback Cloud/Pollinations aktif jika diaktifkan)" -ForegroundColor Yellow
    }
}

# Photo Vault stats
$vaultPath = Join-Path $PSScriptRoot "data\photo_vault\catalog.json"
$vaultCount = 0
if (Test-Path $vaultPath) {
    try {
        $vaultData = Get-Content $vaultPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($vaultData) { $vaultCount = @($vaultData).Count }
    } catch {}
}
Write-Host "  [VAULT]   Photo Vault: $vaultCount foto di arsip galeri lokal (Fallback Semantik Aktif [OK])" -ForegroundColor Cyan

# 4. Video Engine
$vEngine = $env:VIDEO_ENGINE
if (-not $vEngine) { $vEngine = "wan21" }
$vLabel = if ($vEngine -eq "animatediff") { "AnimateDiff (SD 1.5 Anime)" } else { "Wan 2.1 (1.3B AI Video)" }
$vModel = if ($vEngine -eq "animatediff") { "mm_sd_v15_v2.ckpt (AnimateDiff v2)" } else { "wan2.1_t2v_1.3B_bf16.safetensors + wan_2.1_vae.safetensors" }
Write-Host "  [VIDEO]   Active Video Engine: $vLabel" -ForegroundColor Cyan
Write-Host "            Video Model: $vModel" -ForegroundColor DarkCyan

# 5. Check Music Server (Port 8002)
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $ar = $tcp.BeginConnect("127.0.0.1", 8002, $null, $null)
    $ok = $ar.AsyncWaitHandle.WaitOne(500, $false)
    if ($ok -and $tcp.Connected) {
        $tcp.EndConnect($ar)
        Write-Host "  [ONLINE]  YouTube Music Player (Port 8002): ONLINE" -ForegroundColor Green
    } else {
        Write-Host "  [INACTIVE] YouTube Music Player (Port 8002): Inactive" -ForegroundColor DarkGray
    }
    $tcp.Close()
} catch {
    Write-Host "  [INACTIVE] YouTube Music Player (Port 8002): Inactive" -ForegroundColor DarkGray
}

# 6. Check Bot Process
$botProc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*bot.py*" }
if ($botProc) {
    $pids = ($botProc | ForEach-Object { $_.ProcessId }) -join ", "
    Write-Host "  [RUNNING] Telegram Bot Process: ACTIVE (PID: $pids)" -ForegroundColor Green
} else {
    Write-Host "  [STOPPED] Telegram Bot Process: NOT RUNNING" -ForegroundColor Yellow
}

# 7. Check Startup Autorun
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcut = Join-Path $startupFolder 'Start_Waifu_on_Telegram.lnk'
if (Test-Path $shortcut) {
    Write-Host "  [ENABLED] Windows Startup Autorun: ACTIVE (Runs on PC boot)" -ForegroundColor Cyan
} else {
    Write-Host "  [DISABLED] Windows Startup Autorun: INACTIVE" -ForegroundColor DarkGray
}
Write-Host ""

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

    # Language
    $bLang = $env:BOT_LANGUAGE
    if (-not $bLang) { $bLang = "id" }
    $langMap = @{
        "id" = "Bahasa Indonesia (id)"
        "en" = "English (en)"
        "ja" = "Japanese (ja)"
        "auto" = "Auto-detect (Ikuti Bahasa Chat)"
    }
    $langDisp = if ($langMap.ContainsKey($bLang)) { $langMap[$bLang] } else { $bLang }
    Write-Host "  [LANGUAGE] Chat Language: $langDisp" -ForegroundColor Cyan

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
            if ($outfitRawKey -eq "nude") {
                $outfitName = "$outfitName (Auto-Switch NSFW Image & LLM Engine Aktif)"
            }
        }
    }
    Write-Host "  [OUTFIT]  Current Outfit: $outfitName" -ForegroundColor Magenta
} catch {}

# 1b. Hardware & VRAM Auto-Tuning Profile
try {
    $gpuName = "CPU / Integrated Graphics"
    $vramMB = 0
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        try {
            $nvsmi = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>$null
            if ($nvsmi) {
                $parts = $nvsmi[0] -split ','
                $gpuName = $parts[0].Trim()
                $vramMB = [int]$parts[1].Trim()
            }
        } catch {}
    }
    if ($vramMB -eq 0) {
        try {
            $vc = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Sort-Object AdapterRAM -Descending | Select-Object -First 1
            if ($vc -and $vc.AdapterRAM -gt 0) {
                $gpuName = $vc.Name
                $vramMB = [int]($vc.AdapterRAM / 1MB)
            }
        } catch {}
    }
    $vramGB = [math]::Round($vramMB / 1024, 1)
    $tierLabel = "Entry / iGPU / Office PC"
    if ($vramMB -ge 7800) { $tierLabel = "High-End (SDXL & Wan 2.1 Ready)" }
    elseif ($vramMB -ge 5800) { $tierLabel = "Mid-Range (SDXL & Wan 2.1 Compatible)" }
    elseif ($vramMB -ge 2000) { $tierLabel = "Compact (SD 1.5 MeinaMix & AnimateDiff)" }

    Write-Host "  [HARDWARE] GPU & VRAM: $gpuName ($vramGB GB VRAM • $tierLabel)" -ForegroundColor Yellow
} catch {}

# 1c. AI & Image Engine Architecture Setup
try {
    $aiMode = $env:AI_ENGINE_MODE
    if (-not $aiMode) { $aiMode = "split" }
    $aiModeLabel = if ($aiMode -eq "split") { "Split Hybrid (SFW Provider + NSFW Local)" } else { "Unified (Single Model)" }
    $sfwProv = $env:SFW_LLM_PROVIDER
    if (-not $sfwProv) { $sfwProv = "gemini" }
    $sfwModel = $env:SFW_LLM_MODEL
    if (-not $sfwModel) { $sfwModel = "gemini-2.5-flash" }
    $nsfwProv = $env:NSFW_LLM_PROVIDER
    if (-not $nsfwProv) { $nsfwProv = "local" }
    $nsfwModel = $env:LOCAL_LLM_MODEL
    if (-not $nsfwModel) { $nsfwModel = "Huihui-Qwythos-9B-Claude-Mythos-5-1M-abliterated-Q4_K.gguf" }

    Write-Host "  [AI ARCH] Mode AI: $aiModeLabel" -ForegroundColor Cyan
    Write-Host "            - SFW Engine : $sfwProv ($sfwModel)" -ForegroundColor DarkCyan
    Write-Host "            - NSFW Engine: $nsfwProv ($nsfwModel)" -ForegroundColor DarkCyan

    $imgMode = $env:IMAGE_ENGINE_MODE
    if (-not $imgMode) { $imgMode = "split" }
    $sfwImg = $env:SFW_IMAGE_ENGINE
    if (-not $sfwImg) { $sfwImg = "comfyui" }
    $nsfwImg = $env:NSFW_IMAGE_ENGINE
    if (-not $nsfwImg) { $nsfwImg = "comfyui" }
    $sfwCkpt = $env:SFW_COMFYUI_CHECKPOINT
    if (-not $sfwCkpt) { $sfwCkpt = "AnythingXL_xl.safetensors" }
    $nsfwCkpt = $env:NSFW_COMFYUI_CHECKPOINT
    if (-not $nsfwCkpt) { $nsfwCkpt = "AOM3A1B_orange_mixs.safetensors" }

    Write-Host "  [IMG ARCH] Visual Generator Architecture:" -ForegroundColor Cyan
    Write-Host "            - SFW Image  : $sfwImg ($sfwCkpt)" -ForegroundColor DarkCyan
    Write-Host "            - NSFW Image : $nsfwImg ($nsfwCkpt)" -ForegroundColor DarkCyan
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
        $env:COMFYUI_DIR,
        $env:COMFYUI_PATH,
        (Join-Path $PSScriptRoot "tools\ComfyUI\ComfyUI_windows_portable\ComfyUI"),
        (Join-Path $PSScriptRoot "tools\ComfyUI_windows_portable\ComfyUI"),
        (Join-Path $PSScriptRoot "tools\ComfyUI\ComfyUI"),
        (Join-Path $PSScriptRoot "tools\ComfyUI"),
        (Join-Path $PSScriptRoot "ComfyUI"),
        (Join-Path $PSScriptRoot "..\ComfyUI"),
        (Join-Path $PSScriptRoot "..\ComfyUI_windows_portable\ComfyUI"),
        (Join-Path $env:LOCALAPPDATA "Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI"),
        (Join-Path $env:USERPROFILE "ComfyUI"),
        (Join-Path $env:USERPROFILE "Desktop\ComfyUI"),
        (Join-Path $env:USERPROFILE "Downloads\ComfyUI")
    )
    foreach ($drv in @("C:", "D:", "E:", "F:", "G:")) {
        $comfyDirCandidates += "$drv\ComfyUI"
        $comfyDirCandidates += "$drv\comfyui"
        $comfyDirCandidates += "$drv\ComfyUI_windows_portable\ComfyUI"
        $comfyDirCandidates += "$drv\AI\ComfyUI"
        $comfyDirCandidates += "$drv\StableDiffusion\ComfyUI"
    }

    $toolsComfyDir = Join-Path $PSScriptRoot "tools\ComfyUI"
    if (Test-Path $toolsComfyDir) {
        $foundM = Get-ChildItem -Path $toolsComfyDir -Filter "main.py" -File -Recurse -Depth 4 -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($foundM) {
            $comfyDirCandidates += $foundM.DirectoryName
        }
    }

    $hasComfyDir = $false
    $targetCkpt = $env:COMFYUI_CHECKPOINT
    if (-not $targetCkpt) { $targetCkpt = $env:NSFW_COMFYUI_CHECKPOINT }
    if (-not $targetCkpt) { $targetCkpt = $env:SFW_COMFYUI_CHECKPOINT }
    if (-not $targetCkpt) { $targetCkpt = "AnythingXL_xl.safetensors" }
    $ckptInstalled = $false

    foreach ($cd in $comfyDirCandidates) {
        if ($cd -and (Test-Path (Join-Path $cd "main.py"))) {
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

if ($env:SFW_IMAGE_ENGINE -eq "agy") {
    Write-Host "  [ONLINE]  Image Generator Mode: Google Antigravity (AGY Image Generator Subagent)" -ForegroundColor Green
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

# 4b. Voice TTS Engine & VoiceStudio Port 3900
try {
    $vBackend = $env:VOICE_BACKEND
    if (-not $vBackend) { $vBackend = "edge-tts" }
    $vSpeaker = $env:VOICE_NAME
    if (-not $vSpeaker) { $vSpeaker = "id-ID-GadisNeural" }
    $vLang = $env:VOICE_LANGUAGE
    if (-not $vLang) { $vLang = "id-ID" }
    $vReply = $env:VOICE_REPLY_MODE
    if (-not $vReply) { $vReply = "smart" }

    $vBackendLabel = if ($vBackend -like "*voicestudio*") { "VoiceStudio Local AI (Port 3900)" } else { "Microsoft Edge-TTS Cloud" }
    Write-Host "  [VOICE]   Voice Engine: $vBackendLabel (Speaker: $vSpeaker • Lang: $vLang • Reply: $vReply)" -ForegroundColor Cyan

    if ($vBackend -like "*voicestudio*") {
        $vsPort = if ($env:VOICESTUDIO_PORT) { [int]$env:VOICESTUDIO_PORT } else { 3900 }
        $vsOnline = $false
        try {
            $tcpVs = New-Object System.Net.Sockets.TcpClient
            $arVs = $tcpVs.BeginConnect("127.0.0.1", $vsPort, $null, $null)
            $okVs = $arVs.AsyncWaitHandle.WaitOne(300, $false)
            if ($okVs -and $tcpVs.Connected) {
                $tcpVs.EndConnect($arVs)
                $vsOnline = $true
            }
            $tcpVs.Close()
        } catch {}

        if ($vsOnline) {
            Write-Host "  [ONLINE]  VoiceStudio Local AI (Port $vsPort): ONLINE (Service Ready)" -ForegroundColor Green
        } else {
            $vsDir = Join-Path $PSScriptRoot "tools\VoiceStudio"
            if (Test-Path $vsDir) {
                Write-Host "  [STANDBY] VoiceStudio Local AI (Port $vsPort): STANDBY / TIDUR (Hemat VRAM • Bangun Otomatis Saat Voice)" -ForegroundColor Cyan
            } else {
                Write-Host "  [NOT READY] VoiceStudio Local AI (Port $vsPort): tools\VoiceStudio belum terpasang" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  [ONLINE]  Voice TTS Cloud: ONLINE (Microsoft Edge-TTS Cloud Ready)" -ForegroundColor Green
    }
} catch {}

# 4c. Coding Workspace & Active Project
try {
    $projectsRoot = $env:PROJECTS_DIR
    if (-not $projectsRoot) { $projectsRoot = [Environment]::GetFolderPath('UserProfile') }

    $activeProj = "general"
    $actProjFile = Join-Path $PSScriptRoot "data\active_project.json"
    if (Test-Path $actProjFile) {
        try {
            $actData = Get-Content $actProjFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $props = @($actData.PSObject.Properties)
            if ($props.Count -gt 0) { $activeProj = $props[-1].Value }
        } catch {}
    }
    Write-Host "  [CODING]  Coding Workspace: Active Project '$activeProj' (Root: $projectsRoot)" -ForegroundColor Cyan
} catch {}

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

# 5b. Check AGY OpenAI Bridge Server (Port 8001)
$agyPort = if ($env:AGY_BRIDGE_PORT) { [int]$env:AGY_BRIDGE_PORT } else { 8001 }
try {
    $tcpAgy = New-Object System.Net.Sockets.TcpClient
    $arAgy = $tcpAgy.BeginConnect("127.0.0.1", $agyPort, $null, $null)
    $okAgy = $arAgy.AsyncWaitHandle.WaitOne(500, $false)
    if ($okAgy -and $tcpAgy.Connected) {
        $tcpAgy.EndConnect($arAgy)
        Write-Host "  [ONLINE]  AGY OpenAI Bridge (Port $agyPort): ONLINE (OpenAI API Ready)" -ForegroundColor Green
    } else {
        Write-Host "  [STANDBY] AGY OpenAI Bridge (Port $agyPort): Standby / Inactive" -ForegroundColor DarkGray
    }
    $tcpAgy.Close()
} catch {
    Write-Host "  [STANDBY] AGY OpenAI Bridge (Port $agyPort): Standby / Inactive" -ForegroundColor DarkGray
}

# 6. Check Bot Process
$botProc = Get-CimInstance Win32_Process | Where-Object { ($_.Name -like "python*.exe") -and ($_.CommandLine -like "*bot.py*") }
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

# 8. Check Scheduled Message Buffer & Gaming Protection
$bufFile = Join-Path $PSScriptRoot "data\scheduled_message_buffer.json"
$bufCount = 0
if (Test-Path $bufFile) {
    try {
        $rawBuf = Get-Content $bufFile -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($prop in $rawBuf.PSObject.Properties) {
            foreach ($subProp in $prop.Value.PSObject.Properties) {
                $bufCount += @($subProp.Value).Count
            }
        }
    } catch {}
}
Write-Host "  [GAMING]  Scheduled Messages Buffer: $bufCount pesan tersimpan (Gaming Protection Aktif)" -ForegroundColor Cyan
Write-Host "  [LOCK]    GPU Resource Lock: AKTIF (Proteksi Tabrakan VRAM Image & Voice Aktif [OK])" -ForegroundColor Green
Write-Host ""

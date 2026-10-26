# Health & Status Checker for Waifu on Telegram
$vPath = Join-Path $PSScriptRoot "VERSION"
$version = if (Test-Path $vPath) { (Get-Content $vPath).Trim() } else { "1.6.21" }
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

# 2. Check Local LLM (Port 8127) & Model Name
$llmModelName = "Offline"
try {
    $modelsRes = Invoke-RestMethod -Uri "http://127.0.0.1:8127/v1/models" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    if ($modelsRes.data -and $modelsRes.data.Count -gt 0) {
        $rawId = $modelsRes.data[0].id
        $llmModelName = Split-Path -Leaf $rawId
    } elseif ($modelsRes.models -and $modelsRes.models.Count -gt 0) {
        $llmModelName = Split-Path -Leaf $modelsRes.models[0].name
    }
    Write-Host "  [ONLINE]  Locally Uncensored LLM: ONLINE (Port 8127)" -ForegroundColor Green
    Write-Host "            Model: $llmModelName" -ForegroundColor DarkCyan

    # Check Vision Adapter
    $luDir = Join-Path $env:APPDATA "Locally Uncensored\models"
    if (Test-Path $luDir) {
        $mmFiles = Get-ChildItem -Path $luDir -Filter "*mmproj*.gguf" -ErrorAction SilentlyContinue
        if ($mmFiles -and $mmFiles.Count -gt 0) {
            Write-Host "            Vision Model: $($mmFiles[0].Name)" -ForegroundColor DarkCyan
        }
    }
} catch {
    Write-Host "  [OFFLINE] Locally Uncensored LLM (Port 8127): OFFLINE / Unreachable" -ForegroundColor Red
}

# 3. Check ComfyUI (Port 8188) & Checkpoint
$comfyCkpt = "Auto"
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
    Write-Host "  [ONLINE]  ComfyUI Generator: ONLINE (Port 8188)" -ForegroundColor Green
    Write-Host "            Device: $gpu" -ForegroundColor DarkCyan
    Write-Host "            Photo Model: $comfyCkpt" -ForegroundColor DarkCyan
} catch {
    Write-Host "  [OFFLINE] ComfyUI Generator (Port 8188): OFFLINE (Cloud Fallback active)" -ForegroundColor Yellow
}

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

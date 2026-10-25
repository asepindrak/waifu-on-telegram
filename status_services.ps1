# Health & Status Checker for Waifu on Telegram
$vPath = Join-Path $PSScriptRoot "VERSION"
$version = if (Test-Path $vPath) { (Get-Content $vPath).Trim() } else { "1.2.0" }
Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host "       WAIFU ON TELEGRAM v$version - SYSTEM STATUS DIAGNOSTICS      " -ForegroundColor Magenta
Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  [VERSION] Waifu on Telegram: v$version" -ForegroundColor Cyan

# Check Local LLM (Port 8127)
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8127/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "  [ONLINE]  Locally Uncensored LLM (Port 8127): ONLINE" -ForegroundColor Green
} catch {
    Write-Host "  [OFFLINE] Locally Uncensored LLM (Port 8127): OFFLINE / Unreachable" -ForegroundColor Red
}

# Check ComfyUI (Port 8188)
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 2 -UseBasicParsing
    $gpu = $res.devices[0].name
    Write-Host "  [ONLINE]  ComfyUI Generator (Port 8188): ONLINE ($gpu)" -ForegroundColor Green
} catch {
    Write-Host "  [OFFLINE] ComfyUI Generator (Port 8188): OFFLINE (Cloud Fallback active)" -ForegroundColor Yellow
}

# Check Music Server (Port 8002) using quick TCP
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

# Check Bot Process
$botProc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*bot.py*" }
if ($botProc) {
    $pids = ($botProc | ForEach-Object { $_.ProcessId }) -join ", "
    Write-Host "  [RUNNING] Telegram Bot Process: ACTIVE (PID: $pids)" -ForegroundColor Green
} else {
    Write-Host "  [STOPPED] Telegram Bot Process: NOT RUNNING" -ForegroundColor Yellow
}

# Check Startup Autorun
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcut = Join-Path $startupFolder 'Start_Waifu_on_Telegram.lnk'
if (Test-Path $shortcut) {
    Write-Host "  [ENABLED] Windows Startup Autorun: ACTIVE (Runs on PC boot)" -ForegroundColor Cyan
} else {
    Write-Host "  [DISABLED] Windows Startup Autorun: INACTIVE" -ForegroundColor DarkGray
}
Write-Host ""

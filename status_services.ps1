# Health & Status Checker for Waifu on Telegram
Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host "       💖 WAIFU ON TELEGRAM - SYSTEM STATUS DIAGNOSTICS 🤖           " -ForegroundColor Magenta
Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host ""

# Check Local LLM (Port 8127)
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8127/health" -TimeoutSec 2
    Write-Host "  ✓ Locally Uncensored LLM (Port 8127): ONLINE" -ForegroundColor Green
} catch {
    Write-Host "  🔴 Locally Uncensored LLM (Port 8127): OFFLINE / Unreachable" -ForegroundColor Red
}

# Check ComfyUI (Port 8188)
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 2
    $gpu = $res.devices[0].name
    Write-Host "  ✓ ComfyUI Generator (Port 8188): ONLINE ($gpu)" -ForegroundColor Green
} catch {
    Write-Host "  🟡 ComfyUI Generator (Port 8188): OFFLINE (Bot will use Cloud Fallback)" -ForegroundColor Yellow
}

# Check Music Server (Port 8002)
try {
    $res = Invoke-WebRequest -Uri "http://127.0.0.1:8002/player" -TimeoutSec 2
    Write-Host "  ✓ YouTube Music Player (Port 8002): ONLINE" -ForegroundColor Green
} catch {
    Write-Host "  ℹ YouTube Music Player (Port 8002): Inactive" -ForegroundColor DarkGray
}

# Check Bot Process
$botProc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*bot.py*" }
if ($botProc) {
    Write-Host "  ✓ Telegram Bot Process: RUNNING (PID $($botProc.ProcessId))" -ForegroundColor Green
} else {
    Write-Host "  ℹ Telegram Bot Process: NOT RUNNING" -ForegroundColor Yellow
}
Write-Host ""

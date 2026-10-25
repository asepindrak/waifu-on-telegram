$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder 'Start_Waifu_on_Telegram.lnk'
$legacyPath = Join-Path $startupFolder 'Start_AI_Girlfriend_Telegram_Bot.lnk'

Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "     Removing Waifu on Telegram from Windows Startup    " -ForegroundColor Magenta
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host ""

$removed = $false
if (Test-Path $shortcutPath) {
    Remove-Item -Path $shortcutPath -Force
    Write-Host "[SUCCESS] Auto-start shortcut removed: $shortcutPath" -ForegroundColor Green
    $removed = $true
}
if (Test-Path $legacyPath) {
    Remove-Item -Path $legacyPath -Force
    $removed = $true
}

if (-not $removed) {
    Write-Host "[INFO] Auto-start shortcut was not found in Startup folder." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Auto-start has been disabled." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Magenta

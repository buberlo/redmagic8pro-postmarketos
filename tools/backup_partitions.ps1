# Stock Partition Backup Utility
$platformTools = "C:\Users\kernk\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools"
$adb = "$platformTools\adb.exe"
$fastboot = "$platformTools\fastboot.exe"
$backupDir = "C:\Users\kernk\Redmagic8Pro\backups"

Write-Host "=== Partition Backup Utility ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

Write-Host "Querying fastboot partition information..."
& $fastboot getvar all 2>&1 | Out-File "$backupDir\fastboot_vars.txt" -Encoding utf8
Write-Host "Saved fastboot variables to $backupDir\fastboot_vars.txt"

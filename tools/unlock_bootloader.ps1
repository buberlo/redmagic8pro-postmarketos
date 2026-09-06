# Interactive Bootloader Unlock Script for Red Magic 8 Pro (NX729J)
$platformTools = "C:\Users\kernk\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools"
$adb = "$platformTools\adb.exe"
$fastboot = "$platformTools\fastboot.exe"

Write-Host "=== Red Magic 8 Pro (NX729J) Bootloader Unlock Utility ===" -ForegroundColor Cyan

# Check ADB
Write-Host "Checking connected ADB devices..."
$devices = & $adb devices
Write-Host $devices

if ($devices -notmatch 'device\s*$') {
    Write-Host "[!] No authorized ADB device detected." -ForegroundColor Yellow
    Write-Host "Please ensure:"
    Write-Host "  1. Phone is plugged into USB-C and passed through to VMware"
    Write-Host "  2. Developer options > USB debugging is turned ON"
    Write-Host "  3. Phone screen lock is removed (PIN/Password/Fingerprint)"
    Write-Host "  4. 'Always allow from this computer' is accepted on phone"
    exit 1
}

Write-Host "[+] ADB device detected and authorized!" -ForegroundColor Green
Write-Host "[*] Rebooting phone to bootloader / fastboot mode..."
& $adb reboot bootloader
Start-Sleep -Seconds 6

# Check Fastboot
$fbDevices = & $fastboot devices
if (-not $fbDevices) {
    Write-Host "[!] Device not detected in fastboot mode. Please check VMware USB passthrough." -ForegroundColor Red
    exit 1
}
Write-Host "[+] Device detected in Fastboot mode: $fbDevices" -ForegroundColor Green

Write-Host "[*] Sending 'fastboot flashing unlock'..."
& $fastboot flashing unlock

Write-Host ">>> PLEASE LOOK AT YOUR PHONE SCREEN NOW <<<" -ForegroundColor Yellow
Write-Host "Use the VOLUME DOWN button to select 'UNLOCK THE BOOTLOADER', then press POWER to confirm."
Write-Host "After the phone reboots and completes factory reset, run this script again for 'unlock_critical'."

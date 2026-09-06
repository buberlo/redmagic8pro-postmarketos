# Red Magic 8 Pro (NX729J) Bootloader Unlocking Guide

## Prerequisites & Safety Warnings
> [!WARNING]
> Unlocking the bootloader will **trigger a complete factory reset** of your device.
> Back up all photos, contacts, and personal data before continuing.

> [!IMPORTANT]
> Remove all device screen locks (PIN, pattern, password, fingerprint) in Android Settings before unlocking to prevent encryption locking.

## Step-by-Step Procedure

### 1. Developer Options Configuration
1. Open **Settings** > **About phone**.
2. Tap **Build number** 7 times until a toast message displays: *"You are now a developer!"*
3. Go back to **Settings** > **System** > **Developer options**.
4. Enable **OEM unlocking**.
5. Enable **USB debugging**.

### 2. Verify ADB Connectivity
Connect the device to your PC via USB-C. When prompted on the phone screen:
- Check *"Always allow from this computer"*
- Tap **Allow**

Run:
```powershell
adb devices
```
The device should be listed with status `device`.

### 3. Reboot to Bootloader
```powershell
adb reboot bootloader
```
Verify fastboot detects the phone:
```powershell
fastboot devices
```

### 4. Flashing Unlock
Execute:
```powershell
fastboot flashing unlock
```
**Action on Phone Screen:**
Use the **Volume Down** button to highlight **"UNLOCK THE BOOTLOADER"**.
Press the **Power** button to confirm.
The phone will wipe data and reboot automatically.

### 5. Critical Partition Unlock
1. Complete the initial Android setup (skip Wi-Fi and account logins).
2. Re-enable **Developer options** and **USB debugging**.
3. Reboot to fastboot:
   ```powershell
   adb reboot bootloader
   ```
4. Unlock critical partitions:
   ```powershell
   fastboot flashing unlock_critical
   ```
5. Confirm on screen again if prompted.
6. Verify status:
   ```powershell
   fastboot getvar unlocked
   ```
   Output must show: `unlocked: yes`.

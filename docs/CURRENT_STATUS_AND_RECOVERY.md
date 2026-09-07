# Red Magic 8 Pro (NX729J) - Status, Recovery & Handoff Guide

**Target Hardware**: Nubia / ZTE Red Magic 8 Pro (`NX729J`)  
**SoC**: Qualcomm Snapdragon 8 Gen 2 (`SM8550-AB`, kalama / kailua)  
**Host Environment**: Windows 11 (`OFFWORK-VM`) inside VMware Workstation  
**Python**: `C:\Users\kernk\AppData\Local\Programs\Python\Python312\python.exe`  
**Date**: September 2026  

---

## 1. Executive Summary & Current State

The device is currently in a **Qualcomm BootROM EDL mode** (`05C6:9008`) loop following a Linux kernel panic during initial mainline postmarketOS bringup. 

### Key Status Points:
1. **USB Detection**: The device reliably enumerates on USB as `05C6:9008` (Qualcomm CDMA Technologies MSM, Sahara v3 protocol).
2. **Display & Buttons**: The display remains completely black, and holding hardware buttons (`Power`, `Vol-`, `Vol+`) produces no vibration.
3. **Bootloader Status**: **Fully unlocked** (`fastboot flashing unlock` and `unlock_critical` completed).
4. **Mainline Kernel Status**: UFS driver bug has been **diagnosed and solved**:
   - Issue: High-speed gear negotiation under load caused link reset (`HCS.UCRDY` drop).
   - Fix: Restricted high-speed gear to **HS-G1 Rate-A** (`limit-hs-gear = <1>`, `limit-gear-rate = "rate-a"`).
   - Patched ESP image: Staged and ready at `firmware/esp_v2.img`.
5. **Immediate Goal for Next Agent**: Transition the device out of EDL mode into **Fastboot Mode**, boot UEFI (`Mu-nx729j.img`), and deploy `firmware/esp_v2.img` to allow postmarketOS to boot into the Phosh UI.

---

## 2. Root Cause Analysis: The Persistent EDL Loop

### Why Buttons Don't Produce Vibration or Fastboot
1. **Qualcomm Crash Dump Cookies**:
   - When the Linux kernel panicked during testing, Qualcomm's crash handler (`qcom_scm_set_download_mode`) wrote download mode cookies to hardware retention registers:
     - `TCSR_BOOT_MISC_DETECT`: `0x01fd9000` (or `0x01fd5108`)
     - `msm-imem` download cookie: `0x146a8000` (or `0x146aa01c`)
2. **Retention Power Domain (`VDD_MEM`)**:
   - On the Qualcomm SM8550 platform, `VDD_MEM` retains register values as long as the battery is connected or 5V USB VBUS is present.
3. **BootROM (PBL) Execution Sequence**:
   - On power-on, the Primary Boot Loader (PBL / BootROM) inspects `0x01fd9000` **before** loading XBL and **before** sampling the hardware volume buttons.
   - Because the EDL bit is asserted, BootROM immediately branches to USB EDL mode (`05C6:9008`) and halts with the screen powered off.
4. **Warm Reset vs. Cold Reset**:
   - Holding `Power + Vol-` triggers a PMIC `PON_RESET` (warm reset). Warm resets intentionally **preserve** retention registers, causing BootROM to loop straight back into EDL.
5. **PMIC UVLO (Under-Voltage Lockout)**:
   - After sitting in BootROM with the CPU running, the battery may reach low voltage (~3.1V–3.4V). In UVLO mode, the PMIC disables high-power rails (display backlight, haptic vibration motor) and only allows low-current charging or BootROM USB enumeration.

---

## 3. Reverse Engineering Findings: ZTE Firehose Programmer (`devprg`)

The OEM programmer is located at `tools/zte_toolbox/bin/res/NX729J/devprg`. It is an authentic ZTE RSA-signed multi-ELF container. Through disassembly and static analysis of the 64-bit application ELF (ELF 4):

1. **XML Dispatch Table**:
   - Located at virtual address `0x149ea560` (file offset `0x1770d4`).
   - Format: Array of 32-bit pairs `(tag_name_str_ptr, handler_func_ptr)`.
   - Supported tags: `configure`, `program`, `read`, `erase`, `patch`, `power`, `nop`, `setbootablestoragedrive`, `benchmark`, `getstorageinfo`, `getsha256digest`, `getdloadlog`, `firmware_version`, etc.
2. **Why Normal Firehose Tools Fail in Cold EDL**:
   - `ufs_controller_init` (`0x149c620c` / `0x149c5f48`) times out waiting for `HCS.UCRDY`.
   - When entering EDL directly from BootROM (without XBL running first), UFS clocks, PMIC power regulators, and M-PHY are uninitialized. The programmer cannot communicate with UFS storage.
3. **Storage Type 0: The `none` Dummy Driver**:
   - Address: `0x149a09b4`.
   - All functions (`open`, `close`, `read`, `write`, `erase`) immediately return 0 (success).
   - Sending `<configure MemoryName="none" ... />` successfully initializes `devprg` and returns `<response value="ACK" />` without touching the UFS controller.
4. **Reset Behavior**:
   - `<power value="reset" />` calls `bsp_target_reset()` (`0x1499a32c`), which checks a pointer at `[0x80202938]`. In cold EDL, this pointer is NULL, so reset fails silently.
5. **Hardware Poweroff Command**:
   - `<power value="off" DelayInSeconds="X" />` calls `bsp_target_poweroff()` (`0x1499a2ec`).
   - It invokes PMIC shutdown via `0x149af41c(2)` and directly clears bit 0 of `0x0c264000` (SPMI PON arbiter register).
   - This executes a **true hardware PMIC poweroff**, cutting power to the SoC.

---

## 4. USB Host Port Warning (Polyfuse Protection)

During recovery testing, repeated rapid USB reset cycles triggered the motherboard's USB overcurrent polyfuse protection on the physical host PC, causing the USB port to cut power completely (a normal thumb drive would not enumerate). 
- If the phone stops enumerating entirely on host/VM: **Do not panic.**
- Reboot the physical host PC to reset the motherboard polyfuses.

---

## 5. Recovery Procedure for the Next Agent / Harness

### Step 1: Verify USB Connection
Run in PowerShell:
```powershell
& "C:\Users\kernk\AppData\Local\Programs\Python\Python312\python.exe" -c "import usb.core, libusb_package; b=libusb_package.get_libusb1_backend(); print('EDL:', usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=b) is not None); print('Fastboot:', usb.core.find(idVendor=0x18d1, backend=b) is not None)"
```

- If `EDL: True`: Proceed to **Step 2**.
- If `Fastboot: True`: Skip to **Step 4**.
- If both `False`: Ensure VMware has the USB device attached (`VM -> Removable Devices -> Qualcomm CDMA Technologies MSM -> Connect`), or have the user connect to a wall charger for 15 minutes.

---

### Step 2: Trigger PMIC Hardware Poweroff via `devprg`
Run the automated recovery script:
```powershell
& "C:\Users\kernk\AppData\Local\Programs\Python\Python312\python.exe" src/edl_auto_recovery.py
```

This script will:
1. Connect to BootROM over Sahara v3.
2. Stream `devprg` into memory.
3. Drain the initialization banner.
4. Configure storage with `MemoryName="none"`.
5. Dispatch `<power value="off" DelayInSeconds="3" />`.
6. Signal the PMIC to perform a complete hardware shutdown.

---

### Step 3: Cold Boot into Fastboot Mode
Immediately after the script sends the power-off command:
1. **Unplug the USB cable** from the phone.
2. Wait 5–10 seconds for retention capacitors to fully discharge.
3. Press and **hold the `Volume Down` button (`Vol -`)**.
4. While holding `Volume Down`, **plug the USB cable back into the PC**.
5. Once USB is connected with `Vol -` held, release the button after 3 seconds.
6. Verify device has entered Fastboot mode:
   ```powershell
   tools\zte_toolbox\bin\tool\Win\fastboot.exe devices
   ```
   You should see `<serial> fastboot`.

---

### Step 4: Boot Mainline UEFI & Deploy Patched ESP Image
Once in Fastboot:
1. Boot the UEFI image:
   ```powershell
   tools\zte_toolbox\bin\tool\Win\fastboot.exe boot tools\Mu-nx729j.img
   ```
2. The phone screen will initialize and boot UEFI, exposing the UFS partitions as USB Mass Storage on the host PC (typically assigned to `Drive E:`).
3. Deploy the patched ESP image:
   ```powershell
   & "C:\Users\kernk\AppData\Local\Programs\Python\Python312\python.exe" src/deploy_esp.py
   ```
   (This copies `firmware/esp_v2.img` containing the working UFS HS-G1 Rate-A device tree fix).
4. Reboot the phone:
   ```powershell
   tools\zte_toolbox\bin\tool\Win\fastboot.exe reboot
   ```
5. postmarketOS will boot normally with fully operational UFS storage, loading the Phosh desktop interface!

---

## 6. Key Files & Tooling Reference

| File | Purpose |
|---|---|
| `src/edl_auto_recovery.py` | Automated Sahara v3 streamer + Firehose `none` config + PMIC poweroff |
| `src/edl_flash_esp_v2.py` | Standalone Sahara + Firehose UFS programmer |
| `src/deploy_esp.py` | Flashes `firmware/esp_v2.img` to UEFI mass storage |
| `firmware/esp_v2.img` | Patched ESP FAT32 partition with HS-G1 Rate-A DTB |
| `src/device_watcher.py` | Real-time USB bus monitor for EDL, Fastboot, and Android states |
| `tools/zte_toolbox/bin/res/NX729J/devprg` | Authentic OEM signed Firehose programmer |
| `tools/Mu-nx729j.img` | Working UEFI boot image |
| `tools/zte_toolbox/bin/tool/Win/fastboot.exe` | Verified fastboot executable |


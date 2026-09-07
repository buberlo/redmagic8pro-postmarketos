# Red Magic 8 Pro (NX729J) - postmarketOS Bringup & Linux Port

This repository tracks the bringup, mainline Linux kernel enablement, hardware driver configuration, and postmarketOS porting for the **Nubia / ZTE Red Magic 8 Pro** (Model: `NX729J`).

## Device Hardware Overview
- **Codename**: `nx729j`
- **SoC**: Qualcomm Snapdragon 8 Gen 2 (`SM8550-AB`, kalama / kailua)
- **CPU**: Octa-core (1x 3.19 GHz Cortex-X3 + 2x 2.8 GHz Cortex-A715 + 2x 2.8 GHz Cortex-A710 + 3x 2.0 GHz Cortex-A510)
- **GPU**: Qualcomm Adreno 740 (`turnip` / `freedreno` / `drm msm`)
- **Display**: 6.8" AMOLED, 1116 x 2480 @ 120Hz (BOE Q9+)
- **Storage**: UFS 4.0 (256GB / 512GB / 1TB)
- **RAM**: LPDDR5X (12GB / 16GB)
- **WLAN / BT**: Qualcomm FastConnect 7800 (WCN7850 Wi-Fi 7 / Bluetooth 5.3, `ath12k`)
- **Audio**: Qualcomm WCD9385 Codec + Awinic AW88399 smart power amplifiers
- **Cooling**: Built-in 20,000 RPM high-speed centrifugal cooling fan

---

## Repository Structure
```
├── docs/
│   ├── NX729J_HARDWARE_SPECS.md    # Detailed component and pinout specifications
│   ├── BOOTLOADER_UNLOCK_GUIDE.md  # Step-by-step unlock and recovery procedures
│   └── POSTMARKETOS_PORTING.md     # Kernel, DTS, initramfs, and rootfs architecture
├── tools/
│   ├── unlock_bootloader.ps1       # Interactive automated bootloader unlocking script
│   ├── backup_partitions.ps1       # Safe stock partition dump utility
│   ├── build_boot_img.py           # Android boot.img v3/v4 pack/unpack tool
│   └── fetch_prerequisites.py      # Automated downloader for kernel, UEFI & firmware
├── src/
│   ├── dts/                        # Device tree sources and overlays for nx729j
│   └── fan_daemon/                 # Active thermal fan controller service for Linux
├── firmware/                       # Firmware manifests and blob staging
└── backups/                        # Pre-flash stock partition backups (gitignored)
```

---

## Status & Progress Checklist
- [x] Host environment preparation (Android SDK tools, Python 3.12, GitHub CLI)
- [x] Git repository initialization & remote tracking setup
- [x] Bootloader unlocking (`fastboot flashing unlock` & `unlock_critical` completed via patched ABL)
- [x] Stock partition dump & firmware safety backup (`abl_a`, `abl_b`, `devinfo` dumped & verified)
- [x] UEFI (`Mu-nx729j.img`) & Mainline kernel boot image staging
- [x] Kernel & Device Tree bug fixes:
  - [x] GCC clock unfreezing
  - [x] RPMH clock binding
  - [x] UFS 300MHz UniPro DME timer clock configuration
  - [x] UFS link reset fix: restricted high-speed gear to **HS-G1 Rate-A** (`firmware/esp_v2.img`)
- [ ] **Current Blocker / In-Progress**: Device recovery from BootROM EDL crash dump cookie loop
  - *Detailed instructions, reverse-engineering findings & recovery scripts:* See **[docs/CURRENT_STATUS_AND_RECOVERY.md](docs/CURRENT_STATUS_AND_RECOVERY.md)**
- [ ] PostmarketOS rootfs verification & Phosh desktop launch
- [ ] Hardware driver bringup:
  - [ ] SimpleFB / DRM display framebuffer
  - [ ] Touchscreen input (`evtest` / `libinput`)
  - [ ] GPU 3D acceleration (Vulkan Turnip / Adreno 740)
  - [ ] Qualcomm WCN7850 Wi-Fi (`ath12k`)
  - [ ] Centrifugal cooling fan daemon


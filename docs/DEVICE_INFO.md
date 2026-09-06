# Red Magic 8 Pro (NX729J) Live Hardware & Software Profile

Extracted directly from connected device via ADB on **2026-09-07**.

## System Properties
- **Model**: `NX729J` (ZTE Nubia Red Magic 8 Pro)
- **Brand**: `nubia`
- **SoC**: Qualcomm Snapdragon 8 Gen 2 (`SM8550-AB`, kalama)
- **Software Build**: `RedMagicOS10.0.9_EU`
- **Android Version**: `15` (SDK 35)
- **Active Boot Slot**: Slot `_a`
- **Bootloader Locked Status**: `1` (Locked, ready for fastboot unlock)
- **OEM Unlocking Allowed**: `1` (Enabled in Developer Options)
- **Stock Kernel**: `Linux localhost 5.15.167-android13-8-00017-gb1f32b310a30-ab12826353 #1 SMP PREEMPT Thu Dec 19 08:57:20 UTC 2024 aarch64`

---

## Partition Block Map (UFS Storage)

| Partition Name | Target Block Device | Purpose |
| :--- | :--- | :--- |
| `boot_a` / `boot_b` | `/dev/block/sde13` / `/dev/block/sde43` | Generic Android Kernel (`Image`) |
| `init_boot_a` / `init_boot_b` | `/dev/block/sde30` / `/dev/block/sde59` | Generic Ramdisk / initramfs |
| `vendor_boot_a` / `vendor_boot_b` | `/dev/block/sde24` / `/dev/block/sde54` | Vendor Ramdisk, DTB, Bootconfig |
| `dtbo_a` / `dtbo_b` | `/dev/block/sde17` / `/dev/block/sde47` | Device Tree Blob Overlay |
| `recovery_a` / `recovery_b` | `/dev/block/sde27` / `/dev/block/sde56` | Recovery partition |
| `uefi_a` / `uefi_b` | `/dev/block/sde1` / `/dev/block/sde31` | Qualcomm UEFI Firmware |
| `vbmeta_a` / `vbmeta_b` | `/dev/block/sde16` / `/dev/block/sde46` | Verified Boot Metadata |
| `modem_a` / `modem_b` | `/dev/block/sde6` / `/dev/block/sde36` | Snapdragon X70 Baseband Firmware |
| `dsp_a` / `dsp_b` | `/dev/block/sde11` / `/dev/block/sde41` | Hexagon Audio / Compute DSP |
| `bluetooth_a` / `bluetooth_b` | `/dev/block/sde7` / `/dev/block/sde37` | WCN7850 Bluetooth Firmware |
| `super` | `/dev/block/sda7` | Dynamic Partitions (System, Vendor, Product, ODM) |
| `userdata` | `/dev/block/sda12` | User Data & postmarketOS Rootfs Target |

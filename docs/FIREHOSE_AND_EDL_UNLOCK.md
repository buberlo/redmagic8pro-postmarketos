# Qualcomm SM8550 (NX729J) EDL & Firehose Bootloader Unlock

## Overview
The ZTE Nubia Red Magic 8 Pro (`NX729J`) on RedMagicOS 10 (Android 15) stripped the fastboot unlock command handler in stock ABL (`flashing unlock` returns unknown command). This document outlines the confirmed, verified Firehose programmer upload and bootloader unlock method via Qualcomm Sahara v3 and Firehose UFS protocol.

---

## 1. Hardware Identifiers
- **SoC**: Qualcomm Snapdragon 8 Gen 2 (`SM8550-AB`, codename `kalama` / `kailua`)
- **Sahara Protocol Version**: `3`
- **Device MSM HWID**: `0x1ca0e1`
- **OEM ID**: `0x0004` (ZTE)
- **Model ID**: `0x0000`
- **PK_HASH**: `50d3b24d34a27a404a13caf708b235a6db6ec2143f4c4bd1f44ac2f0fd2c4fadf36f5619fea2a370ca0cf98c908ef06d`
- **Storage**: Kioxia 256GB/512GB UFS 4.0 (`THGJFJT1E45BATPC0300`), Sector Size 4096 bytes (4KB)

---

## 2. Partition Layout (UFS LUN 4)
The primary OS boot partitions reside on UFS LUN 4:

| Partition | Start Sector | End Sector | Total Sectors | Size |
|---|---|---|---|---|
| `abl_a` | 97286 | 97541 | 256 | 1,048,576 bytes (1 MB) |
| `abl_b` | 441459 | 441714 | 256 | 1,048,576 bytes (1 MB) |
| `boot_a` | 114054 | 138629 | 24576 | 98,304 KB (96 MB) |
| `boot_b` | 458227 | 482802 | 24576 | 98,304 KB (96 MB) |
| `init_boot_a` | 342131 | 344178 | 2048 | 8,192 KB (8 MB) |
| `init_boot_b` | 678624 | 680671 | 2048 | 8,192 KB (8 MB) |
| `vendor_boot_a`| 283686 | 308261 | 24576 | 98,304 KB (96 MB) |
| `vendor_boot_b`| 627859 | 652434 | 24576 | 98,304 KB (96 MB) |
| `dtbo_a` | 138698 | 144841 | 6144 | 24,576 KB (24 MB) |
| `vbmeta_a` | 138682 | 138697 | 16 | 64 KB |
| `devinfo` | 680672 | 680672 | 1 | 4,096 bytes (4 KB) |

---

## 3. Stock Backups & Checksums
The factory partitions were dumped directly over Firehose and verified:
- **`abl_a_stock.elf`**: `afef8c505163981107548105a4b28c116f0e3e3ac0ac977fe6801969b84c0edc`
- **`abl_b_stock.elf`**: `5c291f690145937d72c2aaea818fc9ee14baa151359e222f4272ebabc2ea932f`
- **`devinfo_stock.bin`**: `143869c499a7e878fbeab756e9c53074195770cc41d6d0d10e45c043141389a3`

---

## 4. Execution Workflow
1. **EDL Handshake (Sahara v3)**:
   - Target sends `SAHARA_HELLO_REQ` (0x01) with version 3.
   - Host replies with `SAHARA_HELLO_RSP` (0x02) accepting version 3 with zeroed padding.
   - Device requests Firehose chunks (`SAHARA_READ_DATA_64`).
   - Host sends ZTE signed Firehose programmer (`devprg`) in 4KB chunks.
   - Host receives `SAHARA_DONE_RSP` (0x06); loader executes.

2. **Firehose UFS Configuration**:
   - Host sends configure XML:
     `<configure MemoryName="ufs" TargetName="SM8550" verbose="0" AlwaysValidate="0" MaxPayloadSizeToTargetInBytes="1048576" Oem="ZTE" ZlpAwareHost="1" />`
   - UFS initialized with sector size 4096.

3. **Partition Backup**:
   - Stock `abl_a`, `abl_b`, `devinfo`, and GPT binaries dumped to disk.

4. **Patched ABL Flashing**:
   - `abl_unlock.elf` padded to exactly 256 sectors (1,048,576 bytes).
   - Programmed to LUN 4 sector 97286.
   - Zero-Length Packet (ZLP) sent to signal completion.
   - Bit-for-bit readback verification confirmed identical SHA256 checksum (`ace02063...`).

5. **Fastboot Unlock**:
   - Device rebooted into Fastboot.
   - Executed `fastboot flashing unlock` and `fastboot flashing unlock_critical`.

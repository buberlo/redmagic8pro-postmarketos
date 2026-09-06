# PostmarketOS Porting & Driver Enablement Architecture

## Target SoC: Qualcomm Snapdragon 8 Gen 2 (SM8550)

PostmarketOS on modern Qualcomm SoCs utilizes two distinct execution pathways:

### Method 1: UEFI-Assisted Boot (Mu-Silicium EDK2)
- **Bootloader**: `Project-Silicium/Mu-Silicium` UEFI for `nx729j`.
- **Display**: SimpleFB / EFI Framebuffer provides display output immediately at 1116x2480.
- **Storage**: UFS storage is initialized by UEFI and passed via standard EFI block I/O.
- **Kernel**: Standard arm64 EFI kernel image with postmarketOS initramfs.

### Method 2: Android Boot Image (boot.img v4 / GKI)
- **Kernel Image**: Mainline 6.10+ / 6.14 kernel built for SM8550.
- **Device Tree**: `sm8550-nubia-nx729j.dtb`.
- **Partitions**:
  - `boot`: Contains kernel `Image.gz`
  - `vendor_boot`: Contains vendor ramdisk and DTB
  - `init_boot`: Contains postmarketOS initramfs
  - `userdata`: Formatted as ext4 or f2fs containing root filesystem.

---

## Hardware Driver Mapping

| Subsystem | Linux Kernel Driver | Firmware / Userspace Requirement |
| :--- | :--- | :--- |
| **CPU / Sched** | `arm64`, `cpufreq-qcom-hw` | In-kernel |
| **Interconnect** | `qcom-icc`, `sm8550-icc` | Device tree interconnect nodes |
| **Display** | `simpledrm` / `msm_drm` (DPU) | Panel timing configuration |
| **GPU** | `drm/msm`, `freedreno` | Mesa `turnip` (Vulkan) |
| **Wi-Fi** | `ath12k` (PCI) | Qualcomm WCN7850 firmware blobs |
| **Bluetooth** | `hci_qca` | Qualcomm Bluetooth patchram firmware |
| **Touchscreen** | `goodix_ts` / `synaptics_dsx` | I2C / SPI device tree node |
| **Audio** | Qualcomm SoundWire / WCD9385 | ALSA UCM profile + DSP firmware |
| **Turbofan** | PWM / GPIO (`redmagic-fan`) | Systemd daemon monitoring `/sys/class/thermal` |

# Nubia Red Magic 8 Pro (NX729J) Hardware Specifications

## System on Chip (SoC)
- **Model**: Qualcomm SM8550-AB (Snapdragon 8 Gen 2)
- **Process**: TSMC 4nm (N4)
- **Architecture**: 64-bit ARMv9-A
- **Cores**:
  - 1x 3.19 GHz Cortex-X3 (Prime core, 1MB L2 cache)
  - 2x 2.80 GHz Cortex-A715 (Performance cores, 512KB L2 cache each)
  - 2x 2.80 GHz Cortex-A710 (Performance cores, 512KB L2 cache each)
  - 3x 2.02 GHz Cortex-A510 (Efficiency cores)
- **Cache**: 8MB Shared L3 Cache, 6MB System Level Cache (SLC)

## Graphics & Multimedia
- **GPU**: Qualcomm Adreno 740 @ 680 MHz
  - Vulkan 1.3, OpenGL ES 3.2, OpenCL 3.0 FP
  - Driver in Linux: Mesa `turnip` (Vulkan) + `freedreno` / DRM `msm`
- **Display**:
  - Resolution: 1116 x 2480 pixels (~400 ppi, 20:9 aspect ratio)
  - Refresh Rate: 120 Hz, Touch sampling: 960 Hz
  - Panel: BOE Q9+ AMOLED, 10-bit color, 1300 nits peak brightness
  - Under-Display Camera (UDC) 16MP

## Memory & Storage
- **RAM**: 12 GB / 16 GB LPDDR5X @ 4200 MHz (8533 Mbps)
- **Storage**: 256 GB / 512 GB / 1 TB UFS 4.0

## Connectivity
- **Wi-Fi / Bluetooth Chip**: Qualcomm FastConnect 7800 (WCN7850)
  - Wi-Fi 7 (802.11be), 2.4/5/6 GHz, 320 MHz channels, 4K QAM
  - Bluetooth 5.3, LE Audio, Snapdragon Sound
  - Linux Kernel Driver: `ath12k` (PCI ID `17cb:1107`), `hci_qca`
- **Modem**: Snapdragon X70 5G Modem-RF System
- **USB**: USB 3.2 Gen 1 (5 Gbps) Type-C with DisplayPort Alternate Mode

## Audio & Sensors
- **Audio Codec**: Qualcomm WCD9385
- **Smart Amplifiers**: Dual Awinic AW88399
- **Sensors**:
  - In-display optical fingerprint scanner (Goodix)
  - Accelerometer, Gyroscope, Magnetometer (I2C/SPI)
  - Dual 520Hz capacitive touch shoulder triggers

## Thermal Subsystem
- **Internal Fan**: 20,000 RPM centrifugal brushless turbofan
  - Centrifugal air intake on back panel, exhaust on side rail
  - Controllable via PWM / GPIO register

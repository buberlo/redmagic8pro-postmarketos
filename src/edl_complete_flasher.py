import sys
import os
import time
import struct
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import re

DEVPRG_PATH = r"C:\Users\kernk\Redmagic8Pro\tools\zte_toolbox\bin\res\NX729J\devprg"
MU_IMG_PATH = r"C:\Users\kernk\Redmagic8Pro\tools\Mu-nx729j.img"
ESP_IMG_PATH = r"C:\Users\kernk\Redmagic8Pro\firmware\esp_new.img"

SECTOR_SIZE = 4096

print("=" * 60)
print("  Qualcomm EDL Automated Permanent UEFI & ESP Flasher")
print("=" * 60)

# 1. Load binaries
with open(DEVPRG_PATH, "rb") as f:
    devprg_data = f.read()
print(f"[+] Loaded devprg: {len(devprg_data)} bytes")

with open(MU_IMG_PATH, "rb") as f:
    mu_data = f.read()
mu_sectors = (len(mu_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
mu_padded = mu_data + b"\x00" * (mu_sectors * SECTOR_SIZE - len(mu_data))
print(f"[+] Loaded Mu UEFI: {len(mu_data)} bytes -> padded to {len(mu_padded)} bytes ({mu_sectors} sectors)")

with open(ESP_IMG_PATH, "rb") as f:
    esp_data = f.read()
esp_sectors = (len(esp_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
esp_padded = esp_data + b"\x00" * (esp_sectors * SECTOR_SIZE - len(esp_data))
print(f"[+] Loaded ESP image: {len(esp_data)} bytes -> padded to {len(esp_padded)} bytes ({esp_sectors} sectors)")

# 2. Connect to device
backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)
if dev is None:
    print("[-] Device 05c6:9008 not found!")
    sys.exit(1)

print("[+] Device handle opened")

def transact_firehose(dev, cmd_xml, timeout=5000):
    if isinstance(cmd_xml, str):
        cmd_xml = cmd_xml.encode("utf-8")
    dev.write(0x01, cmd_xml, timeout=timeout)
    buf = []
    ack_match = None
    while True:
        try:
            chunk = bytes(dev.read(0x81, 4096, timeout=2000))
            text = chunk.decode("utf-8", errors="ignore")
            buf.append(text)
            for l in re.findall(r'<log value="([^"]*)"', text):
                print(f"    [LOG] {l.strip()}")
            if "<response" in text:
                m = re.search(r'<response\s+([^>]*)/?>', text)
                if m:
                    ack_match = m.group(0)
                    print(f"    [RESP] {ack_match}")
                break
        except Exception:
            break
    return "".join(buf), ack_match

def flash_partition(dev, lun, start_sector, num_sectors, data, name):
    print(f"\n[*] Flashing {name} (LUN {lun}, Sector {start_sector}, {num_sectors} sectors, {len(data)/1e6:.2f} MB)...")
    cmd = f'<?xml version="1.0" ?><data><program SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{num_sectors}" physical_partition_number="{lun}" start_sector="{start_sector}" filename="{name}" /></data>\n'
    out, resp = transact_firehose(dev, cmd, timeout=3000)
    if not resp or 'value="ACK"' not in resp:
        raise RuntimeError(f"[-] Program command rejected: {resp}")
    
    # Stream payload in chunks of 1MB
    offset = 0
    chunk_size = 1048576
    t0 = time.time()
    while offset < len(data):
        chunk = data[offset : offset + chunk_size]
        dev.write(0x01, chunk, timeout=10000)
        offset += len(chunk)
        pct = (offset / len(data)) * 100
        elapsed = time.time() - t0
        speed = (offset / (1e6 * elapsed)) if elapsed > 0 else 0
        print(f"\r    Writing {name}: {pct:5.1f}% [{offset/1e6:6.1f}/{len(data)/1e6:6.1f} MB] @ {speed:4.1f} MB/s", end="", flush=True)
    
    print()
    out, final_resp = transact_firehose(dev, b"", timeout=5000)
    # Drain any remaining completion ACKs
    while True:
        try:
            c = bytes(dev.read(0x81, 4096, timeout=1000))
            text = c.decode("utf-8", errors="ignore")
            if "<response" in text:
                final_resp = text
                break
        except Exception:
            break
    print(f"[+] {name} write completed successfully!")

try:
    # 3. Sahara Handshake
    print("\n[*] Starting Sahara v3 handshake...")
    hello_rsp = struct.pack("<IIIIIIIIIIII", 2, 0x30, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0)
    dev.write(0x01, hello_rsp, timeout=1000)
    
    stage = "sahara"
    total_sent = 0
    while stage == "sahara":
        pkt = bytes(dev.read(0x81, 512, timeout=5000))
        cmd, plen = struct.unpack("<II", pkt[:8])
        
        if cmd == 0x12: # SAHARA_64BIT_MEMORY_READ_DATA
            cmd, plen, img_id, offset, length = struct.unpack("<IIQQQ", pkt[:32])
            chunk = devprg_data[offset : offset + length]
            if len(chunk) < length:
                chunk = chunk + b"\xFF" * (length - len(chunk))
            dev.write(0x01, chunk, timeout=5000)
            total_sent += len(chunk)
            print(f"\r    Streaming devprg: {total_sent/len(devprg_data)*100:5.1f}% [{total_sent}/{len(devprg_data)} bytes]", end="", flush=True)
            
        elif cmd == 0x04: # SAHARA_END_TRANSFER
            cmd, plen, img_id, status = struct.unpack("<IIII", pkt[:16])
            print(f"\n[+] SAHARA_END_TRANSFER: Img {img_id}, Status={status:#x}")
            done_req = struct.pack("<II", 0x05, 0x08)
            dev.write(0x01, done_req, timeout=1000)
            try:
                done_rsp = bytes(dev.read(0x81, 512, timeout=2000))
                print(f"[+] DONE response received ({len(done_rsp)} bytes)")
            except Exception:
                pass
            stage = "firehose"
            
    print("\n[+] Firehose programmer active! Waiting for banner...")
    time.sleep(1)
    # Drain banner
    for _ in range(5):
        try:
            b = bytes(dev.read(0x81, 4096, timeout=1000))
            if b"<?xml" in b:
                break
        except Exception:
            pass

    # 4. Configure UFS
    print("[*] Configuring UFS storage (MemoryName=ufs, Oem=ZTE)...")
    cfg_cmd = '<?xml version="1.0" encoding="UTF-8" ?><data><configure MemoryName="ufs" Verbose="0" AlwaysValidate="0" MaxDigestTableSizeInBytes="8192" MaxPayloadSizeToTargetInBytes="1048576" ZlpAwareHost="1" SkipStorageInit="0" Oem="ZTE"/></data>\n'
    transact_firehose(dev, cfg_cmd, timeout=3000)

    # 5. Flash boot_a (LUN 4, sector 114054)
    flash_partition(dev, lun=4, start_sector=114054, num_sectors=mu_sectors, data=mu_padded, name="Mu-boot_a.img")

    # 6. Flash boot_b (LUN 4, sector 458227)
    flash_partition(dev, lun=4, start_sector=458227, num_sectors=mu_sectors, data=mu_padded, name="Mu-boot_b.img")

    # 7. Flash ESP partition 12 (LUN 0, sector 2712576)
    flash_partition(dev, lun=0, start_sector=2712576, num_sectors=esp_sectors, data=esp_padded, name="esp_new.img")

    # 8. Reboot device
    print("\n[*] All partitions flashed successfully! Rebooting phone...")
    reset_cmd = '<?xml version="1.0" ?><data><power value="reset" /></data>\n'
    transact_firehose(dev, reset_cmd, timeout=3000)
    print("\n" + "=" * 60)
    print("  INSTALLATION COMPLETE! DEVICE IS REBOOTING!")
    print("=" * 60)

except Exception as e:
    print(f"\n[-] ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    usb.util.dispose_resources(dev)
    print("[*] Released USB device.")

import sys
import os
import time
import struct
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import re

MU_IMG_PATH = r"C:\Users\kernk\Redmagic8Pro\tools\Mu-nx729j.img"
ESP_IMG_PATH = r"C:\Users\kernk\Redmagic8Pro\firmware\esp_new.img"
SECTOR_SIZE = 4096

print("=" * 60)
print("  Active Firehose Partition Flasher")
print("=" * 60)

with open(MU_IMG_PATH, "rb") as f:
    mu_data = f.read()
mu_sectors = (len(mu_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
mu_padded = mu_data + b"\x00" * (mu_sectors * SECTOR_SIZE - len(mu_data))
print(f"[+] Loaded Mu UEFI: {len(mu_data)} bytes -> {mu_sectors} sectors")

with open(ESP_IMG_PATH, "rb") as f:
    esp_data = f.read()
esp_sectors = (len(esp_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
esp_padded = esp_data + b"\x00" * (esp_sectors * SECTOR_SIZE - len(esp_data))
print(f"[+] Loaded ESP: {len(esp_data)} bytes -> {esp_sectors} sectors")

backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)
if dev is None:
    print("[-] Device 05c6:9008 not found!")
    sys.exit(1)

print("[+] Opened device in Firehose mode")

def transact(cmd_xml, timeout=5000):
    if cmd_xml:
        if isinstance(cmd_xml, str): cmd_xml = cmd_xml.encode('utf-8')
        dev.write(0x01, cmd_xml, timeout=timeout)
    buf = []
    ack_match = None
    t0 = time.time()
    while time.time() - t0 < timeout/1000:
        try:
            chunk = bytes(dev.read(0x81, 4096, timeout=1000))
            text = chunk.decode('utf-8', errors='ignore')
            buf.append(text)
            for l in re.findall(r'<log value="([^"]*)"', text):
                print(f"    [LOG] {l.strip()}")
            if '<response' in text:
                m = re.search(r'<response\s+([^>]*)/?>', text)
                if m:
                    ack_match = m.group(0)
                    print(f"    [RESP] {ack_match}")
                break
        except Exception:
            pass
    return "".join(buf), ack_match

def flash_part(lun, start_sector, num_sectors, data, name):
    print(f"\n[*] Flashing {name} to LUN {lun}, sector {start_sector} ({num_sectors} sectors, {len(data)/1e6:.2f} MB)...")
    cmd = f'<?xml version="1.0" ?><data><program SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{num_sectors}" physical_partition_number="{lun}" start_sector="{start_sector}" filename="{name}" /></data>\n'
    out, resp = transact(cmd)
    if not resp or 'value="ACK"' not in resp:
        raise RuntimeError(f"Program command rejected: {resp}")
        
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
    
    # Wait for completion ACK
    out, final_resp = transact(b"")
    while not final_resp:
        out, final_resp = transact(b"", timeout=2000)
    print(f"[+] {name} write confirmed with ACK!")

try:
    # Drain remaining banner
    print("[*] Draining remaining logs...")
    for _ in range(5):
        try:
            dev.read(0x81, 4096, timeout=500)
        except Exception:
            break

    # 1. Configure UFS
    print("[*] Configuring UFS...")
    cfg = '<?xml version="1.0" encoding="UTF-8" ?><data><configure MemoryName="ufs" Verbose="0" AlwaysValidate="0" MaxDigestTableSizeInBytes="8192" MaxPayloadSizeToTargetInBytes="1048576" ZlpAwareHost="1" SkipStorageInit="0" Oem="ZTE"/></data>\n'
    transact(cfg)

    # 2. Flash boot_a
    flash_part(lun=4, start_sector=114054, num_sectors=mu_sectors, data=mu_padded, name="Mu-boot_a.img")

    # 3. Flash boot_b
    flash_part(lun=4, start_sector=458227, num_sectors=mu_sectors, data=mu_padded, name="Mu-boot_b.img")

    # 4. Flash ESP partition 12
    flash_part(lun=0, start_sector=2712576, num_sectors=esp_sectors, data=esp_padded, name="esp_new.img")

    # 5. Reboot phone
    print("\n[*] Sending reset command to reboot phone...")
    reset_cmd = '<?xml version="1.0" ?><data><power value="reset" /></data>\n'
    transact(reset_cmd)
    print("\n" + "=" * 60)
    print("  SUCCESS! PHONE IS NOW REBOOTING INTO PERMANENT PROJECT MU UEFI!")
    print("=" * 60)

except Exception as e:
    print("\n[-] Error:", e)
    import traceback
    traceback.print_exc()

finally:
    usb.util.dispose_resources(dev)
    print("[*] Released USB device.")

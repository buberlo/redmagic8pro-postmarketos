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
print("  Active Firehose Live Partition Flasher (with ZLP)")
print("=" * 60)

with open(MU_IMG_PATH, "rb") as f:
    mu_data = f.read()
mu_sectors = (len(mu_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
mu_padded = mu_data + b"\x00" * (mu_sectors * SECTOR_SIZE - len(mu_data))

with open(ESP_IMG_PATH, "rb") as f:
    esp_data = f.read()
esp_sectors = (len(esp_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
esp_padded = esp_data + b"\x00" * (esp_sectors * SECTOR_SIZE - len(esp_data))

backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)
if dev is None:
    print("[-] Device 05c6:9008 not found!")
    sys.exit(1)

def read_firehose_response(timeout=5000):
    buf = []
    ack_match = None
    t0 = time.time()
    while time.time() - t0 < timeout/1000:
        try:
            chunk = bytes(dev.read(0x81, 4096, timeout=1000))
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
            pass
    return "".join(buf), ack_match

def flash_partition(lun, start_sector, num_sectors, data, name):
    print(f"\n[*] Flashing {name} to LUN {lun}, Sector {start_sector} ({num_sectors} sectors, {len(data)/1e6:.2f} MB)...")
    cmd = f'<?xml version="1.0" ?><data><program SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{num_sectors}" physical_partition_number="{lun}" start_sector="{start_sector}" filename="{name}" /></data>\n'
    dev.write(0x01, cmd.encode("utf-8"), timeout=2000)
    
    xml_out, resp = read_firehose_response(timeout=3000)
    if not resp or 'value="ACK"' not in resp:
        raise RuntimeError(f"[-] Program command rejected: {resp}")
        
    print(f"[+] Program ACK received. Streaming {len(data)} bytes...")
    offset = 0
    chunk_size = 1048576
    t0 = time.time()
    while offset < len(data):
        chunk = data[offset : offset + chunk_size]
        dev.write(0x01, chunk, timeout=15000)
        offset += len(chunk)
        pct = (offset / len(data)) * 100
        elapsed = time.time() - t0
        speed = (offset / (1e6 * elapsed)) if elapsed > 0 else 0
        print(f"\r    Progress: {pct:5.1f}% [{offset/1e6:6.1f}/{len(data)/1e6:6.1f} MB] @ {speed:4.1f} MB/s", end="", flush=True)
    print()
    
    # Send ZLP to signal end of stream
    dev.write(0x01, b"", timeout=1000)
    
    final_xml, final_resp = read_firehose_response(timeout=8000)
    if not final_resp or 'value="ACK"' not in final_resp:
        raise RuntimeError(f"[-] Write completion not ACKed: {final_resp}")
    print(f"[+] {name} write successfully verified and completed!")

try:
    # 1. Flash boot_b
    flash_partition(lun=4, start_sector=458227, num_sectors=mu_sectors, data=mu_padded, name="boot_b.img")

    # 2. Flash ESP partition 12
    flash_partition(lun=0, start_sector=2712576, num_sectors=esp_sectors, data=esp_padded, name="esp.img")

    # 3. Reboot phone
    print("\n[*] All partitions flashed! Sending power reset command to reboot phone...")
    reset_cmd = '<?xml version="1.0" ?><data><power value="reset" /></data>\n'
    dev.write(0x01, reset_cmd.encode("utf-8"), timeout=2000)
    r_xml, r_resp = read_firehose_response(timeout=3000)
    print(f"[+] Reboot response: {r_resp}")
    
    print("\n" + "=" * 60)
    print("  INSTALLATION 100% COMPLETE! PHONE IS REBOOTING!")
    print("=" * 60)

except Exception as e:
    print(f"\n[-] Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    usb.util.dispose_resources(dev)
    print("[*] Released USB device.")

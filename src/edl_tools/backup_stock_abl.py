import sys
import os
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import hashlib
import time
import re

backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)
if dev is None:
    print("Device not found")
    sys.exit(1)

def read_firehose_response(dev, timeout=3000):
    buf = []
    ack_match = None
    t0 = time.time()
    while True:
        try:
            chunk = bytes(dev.read(0x81, 4096, timeout=1000))
            text = chunk.decode('utf-8', errors='ignore')
            buf.append(text)
            logs = re.findall(r'<log value="([^"]*)"', text)
            for l in logs:
                print(f"    [LOG] {l.strip()}")
            if '<response' in text:
                m = re.search(r'<response\s+([^>]*)/?>', text)
                if m:
                    ack_match = m.group(0)
                    print(f"    [RESP] {ack_match}")
                break
        except Exception:
            break
    return "".join(buf), ack_match

def read_partition(lun, start_sector, num_sectors, out_path):
    print(f"\n[*] Reading LUN {lun}, Sector {start_sector} ({num_sectors} sectors = {num_sectors*4096} bytes)...")
    cmd = f'<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" num_partition_sectors="{num_sectors}" physical_partition_number="{lun}" start_sector="{start_sector}" filename="{os.path.basename(out_path)}" /></data>\n'
    dev.write(0x01, cmd.encode('utf-8'), timeout=2000)
    
    xml_out, resp = read_firehose_response(dev, timeout=3000)
    if not resp or 'value="ACK"' not in resp:
        raise RuntimeError(f"Read command failed: {resp}")
    
    payload = bytearray()
    total_bytes = num_sectors * 4096
    while len(payload) < total_bytes:
        chunk = bytes(dev.read(0x81, min(total_bytes - len(payload), 1048576), timeout=5000))
        if len(chunk) == 0:
            break
        payload.extend(chunk)
    
    final_xml, final_resp = read_firehose_response(dev, timeout=3000)
    if len(payload) != total_bytes:
        raise RuntimeError(f"Read payload size mismatch: {len(payload)} vs {total_bytes}")
    
    with open(out_path, "wb") as f:
        f.write(payload)
    
    sha = hashlib.sha256(payload).hexdigest()
    print(f"[+] Saved {len(payload)} bytes to {out_path}")
    print(f"    SHA256: {sha}")
    return payload

os.makedirs("backups", exist_ok=True)

# 1. Backup abl_a (LUN 4, start 97286, count 256)
abl_a_data = read_partition(4, 97286, 256, "backups/abl_a_stock.elf")

# 2. Backup abl_b (LUN 4, start 441459, count 256)
abl_b_data = read_partition(4, 441459, 256, "backups/abl_b_stock.elf")

# 3. Backup devinfo (LUN 4, start 680672, count 1)
devinfo_data = read_partition(4, 680672, 1, "backups/devinfo_stock.bin")

usb.util.dispose_resources(dev)
print("\n[+] ALL CRITICAL STOCK PARTITIONS BACKED UP SUCCESSFULLY!")

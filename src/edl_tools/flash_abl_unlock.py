import sys
import os
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import hashlib
import time
import re

ABL_UNLOCK_PATH = r"C:\Users\kernk\Redmagic8Pro\tools\zte_toolbox\bin\res\NX729J\abl_unlock.elf"
SECTOR_SIZE = 4096
LUN = 4
START_SECTOR = 97286
NUM_SECTORS = 256
TOTAL_BYTES = NUM_SECTORS * SECTOR_SIZE # 1048576 bytes

# 1. Load and pad abl_unlock.elf
with open(ABL_UNLOCK_PATH, "rb") as f:
    unlock_raw = f.read()

print(f"[+] Loaded abl_unlock.elf: {len(unlock_raw)} bytes")
padded_unlock_data = unlock_raw + b"\x00" * (TOTAL_BYTES - len(unlock_raw))
print(f"[+] Padded to {len(padded_unlock_data)} bytes ({NUM_SECTORS} sectors)")
target_sha = hashlib.sha256(padded_unlock_data).hexdigest()
print(f"    Target SHA256: {target_sha}")

# 2. Connect to device
backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)
if dev is None:
    print("[-] Device not found")
    sys.exit(1)

def read_firehose_response(dev, timeout=5000):
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

# 3. Flash abl_unlock to abl_a
print(f"\n[*] Flashing unlocked ABL to LUN {LUN}, Sector {START_SECTOR} ({NUM_SECTORS} sectors)...")
cmd = f'<?xml version="1.0" ?><data><program SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{NUM_SECTORS}" physical_partition_number="{LUN}" start_sector="{START_SECTOR}" filename="abl_unlock.elf" /></data>\n'
dev.write(0x01, cmd.encode('utf-8'), timeout=2000)

xml_out, resp = read_firehose_response(dev, timeout=3000)
if not resp or 'value="ACK"' not in resp:
    print(f"[-] Program command failed to ACK: {resp}")
    sys.exit(1)

print("[+] Program ACK received! Streaming payload...")
offset = 0
chunk_size = 1048576
while offset < len(padded_unlock_data):
    chunk = padded_unlock_data[offset : offset + chunk_size]
    dev.write(0x01, chunk, timeout=10000)
    offset += len(chunk)
    print(f"    Streamed {offset}/{len(padded_unlock_data)} bytes...")

# Read completion ACK
final_xml, final_resp = read_firehose_response(dev, timeout=5000)
print(f"[+] Write final response: {final_resp}")
if not final_resp or 'value="ACK"' not in final_resp:
    print("[-] Write failed to complete with ACK!")
    sys.exit(1)

print("[+] Write completed successfully! Verifying readback...")

# 4. Readback verification
read_cmd = f'<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{NUM_SECTORS}" physical_partition_number="{LUN}" start_sector="{START_SECTOR}" filename="abl_a_verify.bin" /></data>\n'
dev.write(0x01, read_cmd.encode('utf-8'), timeout=2000)

r_xml, r_resp = read_firehose_response(dev, timeout=3000)
if not r_resp or 'value="ACK"' not in r_resp:
    print("[-] Verification read command failed to ACK!")
    sys.exit(1)

readback_payload = bytearray()
while len(readback_payload) < TOTAL_BYTES:
    c = bytes(dev.read(0x81, min(TOTAL_BYTES - len(readback_payload), 1048576), timeout=5000))
    if len(c) == 0:
        break
    readback_payload.extend(c)

r_final_xml, r_final_resp = read_firehose_response(dev, timeout=3000)
readback_sha = hashlib.sha256(readback_payload).hexdigest()
print(f"[+] Readback SHA256: {readback_sha}")

if readback_sha == target_sha:
    print("[SUCCESS] VERIFICATION PASSED: abl_a matches target bit-for-bit!")
else:
    print("[-] FATAL: Verification mismatch!")
    sys.exit(1)

# 5. Reboot device to Fastboot
print("\n[*] Sending Firehose power reset to reboot device...")
reset_cmd = '<?xml version="1.0" ?><data><power value="reset" /></data>\n'
dev.write(0x01, reset_cmd.encode('utf-8'), timeout=2000)
p_xml, p_resp = read_firehose_response(dev, timeout=3000)
print(f"[+] Reset response: {p_resp}")

usb.util.dispose_resources(dev)
print("[+] Device is now rebooting into system/fastboot!")

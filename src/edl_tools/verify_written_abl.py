import sys
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

# 1. Target SHA
ABL_UNLOCK_PATH = r"C:\Users\kernk\Redmagic8Pro\tools\zte_toolbox\bin\res\NX729J\abl_unlock.elf"
with open(ABL_UNLOCK_PATH, "rb") as f:
    unlock_raw = f.read()
padded_unlock = unlock_raw + b"\x00" * (1048576 - len(unlock_raw))
target_sha = hashlib.sha256(padded_unlock).hexdigest()
print(f"[+] Target SHA256: {target_sha}")

# 2. Read back abl_a
print("[*] Reading back LUN 4, Sector 97286 (256 sectors)...")
read_cmd = '<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="4096" num_partition_sectors="256" physical_partition_number="4" start_sector="97286" filename="verify_abl_a.bin" /></data>\n'
dev.write(0x01, read_cmd.encode('utf-8'), timeout=2000)

xml_out, resp = read_firehose_response(dev, timeout=3000)
if not resp or 'value="ACK"' not in resp:
    print("[-] Read request failed!")
    sys.exit(1)

readback_payload = bytearray()
while len(readback_payload) < 1048576:
    c = bytes(dev.read(0x81, min(1048576 - len(readback_payload), 1048576), timeout=5000))
    if len(c) == 0:
        break
    readback_payload.extend(c)

f_xml, f_resp = read_firehose_response(dev, timeout=3000)
readback_sha = hashlib.sha256(readback_payload).hexdigest()
print(f"[+] Readback SHA256: {readback_sha}")

if readback_sha == target_sha:
    print("[SUCCESS] VERIFICATION 100% CONFIRMED: abl_a matches abl_unlock.elf bit-for-bit!")
else:
    print("[-] Verification failed!")
    sys.exit(1)

usb.util.dispose_resources(dev)
print("[+] Ready for reset.")

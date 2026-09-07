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
ESP_IMG_PATH = r"C:\Users\kernk\Redmagic8Pro\firmware\esp_v2.img"
SECTOR_SIZE = 4096
LUN = 0
START_SECTOR = 2712576

print("=" * 60)
print("  EDL Flasher - Native SM8550 DTB & ESP v2")
print("=" * 60)

with open(DEVPRG_PATH, "rb") as f:
    devprg_data = f.read()

with open(ESP_IMG_PATH, "rb") as f:
    esp_data = f.read()

esp_sectors = (len(esp_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
esp_padded = esp_data + b"\x00" * (esp_sectors * SECTOR_SIZE - len(esp_data))
print(f"[+] Loaded ESP v2: {len(esp_data)} bytes -> {esp_sectors} sectors ({len(esp_padded)} bytes)")

backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)
if dev is None:
    print("[-] Device 05c6:9008 not found!")
    sys.exit(1)

print("[+] Device handle opened")

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

try:
    # 1. Sahara handshake
    print("[*] Starting Sahara v3 handshake...")
    stage = "sahara"
    total_sent = 0
    
    # Try reading first to check if device sent HELLO (cmd=1) or is already requesting data (cmd=0x12)
    try:
        pkt = bytes(dev.read(0x81, 512, timeout=1000))
        cmd, plen = struct.unpack("<II", pkt[:8])
        print(f"[+] Initial packet from device: cmd={cmd:#x}, len={plen}")
        if cmd == 1: # SAHARA_HELLO
            hello_rsp = struct.pack("<IIIIIIIIIIII", 2, 0x30, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0)
            dev.write(0x01, hello_rsp, timeout=1000)
            pkt = bytes(dev.read(0x81, 512, timeout=2000))
            cmd, plen = struct.unpack("<II", pkt[:8])
    except Exception as e:
        print("[-] Initial read exception, attempting hello_rsp:", e)
        hello_rsp = struct.pack("<IIIIIIIIIIII", 2, 0x30, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0)
        dev.write(0x01, hello_rsp, timeout=1000)
        pkt = bytes(dev.read(0x81, 512, timeout=5000))
        cmd, plen = struct.unpack("<II", pkt[:8])
    
    while stage == "sahara":
        if cmd == 0x12: # 64-bit read
            cmd_id, plen, img_id, offset, length = struct.unpack("<IIQQQ", pkt[:32])
            chunk = devprg_data[offset : offset + length]
            if len(chunk) < length:
                chunk = chunk + b"\xFF" * (length - len(chunk))
            dev.write(0x01, chunk, timeout=5000)
            total_sent += len(chunk)
            print(f"\r    Streaming devprg: {total_sent/len(devprg_data)*100:5.1f}% [{total_sent}/{len(devprg_data)} bytes]", end="", flush=True)
            
        elif cmd == 0x04: # End transfer
            cmd_id, plen, img_id, status = struct.unpack("<IIII", pkt[:16])
            print(f"\n[+] SAHARA_END_TRANSFER: Status={status:#x}")
            done_req = struct.pack("<II", 0x05, 0x08)
            dev.write(0x01, done_req, timeout=1000)
            try:
                done_rsp = bytes(dev.read(0x81, 512, timeout=2000))
                print(f"[+] DONE response received ({len(done_rsp)} bytes)")
            except Exception:
                pass
            stage = "firehose"
            break

        pkt = bytes(dev.read(0x81, 512, timeout=5000))
        cmd, plen = struct.unpack("<II", pkt[:8])

    print("\n[+] Firehose programmer active! Waiting for banner...")
    time.sleep(1)
    
    # Drain initial banner
    count = 0
    while True:
        try:
            b = bytes(dev.read(0x81, 4096, timeout=500))
            text = b.decode("utf-8", errors="ignore")
            if "End of supported functions" in text:
                print(f"    [BANNER] End of supported functions reached!")
                break
        except Exception:
            break

    # 2. Configure UFS
    print("[*] Configuring UFS storage (MemoryName=ufs, Oem=ZTE)...")
    cfg_cmd = '<?xml version="1.0" encoding="UTF-8" ?><data><configure MemoryName="ufs" Verbose="0" AlwaysValidate="0" MaxDigestTableSizeInBytes="8192" MaxPayloadSizeToTargetInBytes="1048576" ZlpAwareHost="1" SkipStorageInit="0" Oem="ZTE"/></data>\n'
    dev.write(0x01, cfg_cmd.encode("utf-8"), timeout=2000)
    out, resp = read_firehose_response(timeout=5000)
    if not resp or 'value="ACK"' not in resp:
        print("[*] Retrying configure with NOP handshake...")
        dev.write(0x01, b'<?xml version="1.0" ?><data><nop /></data>\n', timeout=1000)
        read_firehose_response(timeout=2000)
        dev.write(0x01, cfg_cmd.encode("utf-8"), timeout=2000)
        out, resp = read_firehose_response(timeout=5000)
        if not resp or 'value="ACK"' not in resp:
            raise RuntimeError(f"[-] Configure failed: {resp}")

    # 3. Flash ESP v2 to Partition 12 on LUN 0
    print(f"\n[*] Flashing updated ESP (LUN {LUN}, Sector {START_SECTOR}, {esp_sectors} sectors, {len(esp_padded)/1e6:.2f} MB)...")
    prog_cmd = f'<?xml version="1.0" ?><data><program SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{esp_sectors}" physical_partition_number="{LUN}" start_sector="{START_SECTOR}" filename="esp_v2.img" /></data>\n'
    dev.write(0x01, prog_cmd.encode("utf-8"), timeout=2000)
    out, resp = read_firehose_response(timeout=3000)
    if not resp or 'value="ACK"' not in resp:
        raise RuntimeError(f"[-] Program command rejected: {resp}")

    print(f"[+] Program ACK received. Streaming {len(esp_padded)} bytes...")
    offset = 0
    chunk_size = 1048576
    t0 = time.time()
    while offset < len(esp_padded):
        chunk = esp_padded[offset : offset + chunk_size]
        dev.write(0x01, chunk, timeout=15000)
        offset += len(chunk)
        pct = (offset / len(esp_padded)) * 100
        elapsed = time.time() - t0
        speed = (offset / (1e6 * elapsed)) if elapsed > 0 else 0
        print(f"\r    Progress: {pct:5.1f}% [{offset/1e6:6.1f}/{len(esp_padded)/1e6:6.1f} MB] @ {speed:4.1f} MB/s", end="", flush=True)
    print()

    # Send ZLP
    dev.write(0x01, b"", timeout=1000)
    final_xml, final_resp = read_firehose_response(timeout=8000)
    if not final_resp or 'value="ACK"' not in final_resp:
        raise RuntimeError(f"[-] Write completion not ACKed: {final_resp}")
    print(f"[+] ESP v2 successfully flashed and verified!")

    # 4. Reboot phone
    print("\n[*] Sending reset command to reboot phone...")
    reset_cmd = '<?xml version="1.0" ?><data><power value="reset" /></data>\n'
    dev.write(0x01, reset_cmd.encode("utf-8"), timeout=2000)
    r_xml, r_resp = read_firehose_response(timeout=3000)
    print(f"[+] Reboot command confirmed: {r_resp}")

    print("\n" + "=" * 60)
    print("  ESP UPDATE COMPLETE! PHONE IS REBOOTING INTO POSTMARKETOS!")
    print("=" * 60)

except Exception as e:
    print(f"\n[-] Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    usb.util.dispose_resources(dev)
    print("[*] Released USB device.")

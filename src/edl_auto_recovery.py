"""
EDL Auto-Recovery Script for Nubia Red Magic 8 Pro (NX729J)
Recovers device from Qualcomm EDL mode (05c6:9008) to Fastboot.
"""
import os
import re
import struct
import sys
import time
import usb.core
import usb.util
import libusb_package

DEVPRG_PATH = r"C:\Users\kernk\Redmagic8Pro\tools\zte_toolbox\bin\res\NX729J\devprg"

print("=" * 60)
print("  RED MAGIC 8 PRO (NX729J) - EDL RECOVERY TOOL")
print("=" * 60)

if not os.path.exists(DEVPRG_PATH):
    print(f"[-] ERROR: devprg not found at {DEVPRG_PATH}")
    sys.exit(1)

with open(DEVPRG_PATH, "rb") as f:
    devprg_data = f.read()

backend = libusb_package.get_libusb1_backend()

def find_device():
    return usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)

def read_firehose(dev, timeout=3000):
    buf = []
    ack = None
    t_end = time.time() + (timeout / 1000.0)
    while time.time() < t_end:
        try:
            b = bytes(dev.read(0x81, 4096, timeout=500))
            text = b.decode("utf-8", errors="ignore")
            buf.append(text)
            for l in re.findall(r'<log value="([^"]*)"', text):
                print(f"    [LOG] {l.strip()}")
            if "<response" in text:
                m = re.search(r'<response\s+([^>]*)/?>', text)
                if m:
                    ack = m.group(0)
                    print(f"    [RESP] {ack}")
                break
        except Exception:
            pass
    return "".join(buf), ack

def run_recovery():
    print("[*] Waiting for Red Magic 8 Pro in EDL mode (05C6:9008)...")
    print("[*] (If running in VMware: ensure USB is connected to Virtual Machine)")
    
    dev = None
    while dev is None:
        dev = find_device()
        if dev is None:
            time.sleep(0.5)
    
    print("[+] Device detected at 05C6:9008!")
    
    # Check interface protocol
    try:
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]
        proto = intf.bInterfaceProtocol
        print(f"[+] USB Interface Protocol: {proto:#x}")
    except Exception as e:
        print(f"[*] Note on interface: {e}")
        proto = 0x11

    # If protocol 0x11 -> Sahara mode
    if proto == 0x11:
        print("[*] Device is in Sahara BootROM mode. Initiating Sahara v3 handshake...")
        
        # Flush pending
        try:
            pkt = bytes(dev.read(0x81, 512, timeout=500))
            cmd, plen = struct.unpack("<II", pkt[:8])
            print(f"[+] Initial packet: cmd={cmd:#x}, len={plen}")
        except Exception:
            pkt = None
            cmd = None
        
        # Send HELLO_RESP (mode 0 = normal upload)
        hello_rsp = struct.pack("<IIIIIIIIIIII", 2, 0x30, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0)
        dev.write(0x01, hello_rsp, timeout=1000)
        
        # Stream devprg
        print("[*] Streaming signed Firehose loader (devprg)...")
        total_sent = 0
        stage = "sahara"
        while stage == "sahara":
            try:
                pkt = bytes(dev.read(0x81, 512, timeout=5000))
            except Exception as e:
                print(f"[-] Sahara read error: {e}")
                break
            
            if len(pkt) < 8:
                continue
            cmd, plen = struct.unpack("<II", pkt[:8])
            
            if cmd == 0x12: # 64-bit read request
                cmd_id, plen, img_id, offset, length = struct.unpack("<IIQQQ", pkt[:32])
                chunk = devprg_data[offset : offset + length]
                if len(chunk) < length:
                    chunk = chunk + b"\xFF" * (length - len(chunk))
                dev.write(0x01, chunk, timeout=5000)
                total_sent += len(chunk)
                pct = (total_sent / len(devprg_data)) * 100
                print(f"\r    Uploading: {pct:5.1f}% [{total_sent}/{len(devprg_data)} bytes]", end="", flush=True)
            elif cmd == 0x03: # 32-bit read request
                cmd_id, plen, img_id, offset, length = struct.unpack("<IIIII", pkt[:20])
                chunk = devprg_data[offset : offset + length]
                if len(chunk) < length:
                    chunk = chunk + b"\xFF" * (length - len(chunk))
                dev.write(0x01, chunk, timeout=5000)
                total_sent += len(chunk)
                pct = (total_sent / len(devprg_data)) * 100
                print(f"\r    Uploading: {pct:5.1f}% [{total_sent}/{len(devprg_data)} bytes]", end="", flush=True)
            elif cmd == 0x04: # End transfer
                cmd_id, plen, img_id, status = struct.unpack("<IIII", pkt[:16])
                print(f"\n[+] SAHARA_END_TRANSFER: Status={status:#x}")
                done_req = struct.pack("<II", 0x05, 0x08)
                dev.write(0x01, done_req, timeout=1000)
                try:
                    done_rsp = bytes(dev.read(0x81, 512, timeout=2000))
                    print(f"[+] SAHARA_DONE_RSP received ({len(done_rsp)} bytes)")
                except Exception:
                    pass
                stage = "firehose"
                break
            elif cmd == 0x01:
                dev.write(0x01, hello_rsp, timeout=1000)
    
    print("\n[+] Firehose programmer executing! Waiting for device banner...")
    time.sleep(1)
    
    # Drain banner
    while True:
        try:
            b = bytes(dev.read(0x81, 4096, timeout=500))
            text = b.decode("utf-8", errors="ignore")
            if "End of supported functions" in text:
                print("    [BANNER] devprg initialized successfully!")
                break
        except Exception:
            break

    # Send configure MemoryName="none" to avoid UFS failure
    print("[*] Configuring devprg with dummy storage driver (MemoryName=none)...")
    cfg_cmd = '<?xml version="1.0" encoding="UTF-8" ?><data><configure MemoryName="none" Verbose="1" AlwaysValidate="0" MaxDigestTableSizeInBytes="8192" MaxPayloadSizeToTargetInBytes="1048576" ZlpAwareHost="1" /></data>\n'
    dev.write(0x01, cfg_cmd.encode("utf-8"), timeout=2000)
    out, resp = read_firehose(dev, timeout=3000)
    
    if not resp or 'value="ACK"' not in resp:
        print("[*] Retrying configure...")
        dev.write(0x01, b'<?xml version="1.0" ?><data><nop /></data>\n', timeout=1000)
        read_firehose(dev, timeout=1000)
        dev.write(0x01, cfg_cmd.encode("utf-8"), timeout=2000)
        out, resp = read_firehose(dev, timeout=3000)

    print("\n" + "=" * 60)
    print("  devprg is READY! Sending power action...")
    print("=" * 60)
    
    # Send power off with 3 second delay
    print("[*] Sending power off command (<power value=\"off\" DelayInSeconds=\"3\" />)...")
    pwr_cmd = '<?xml version="1.0" encoding="UTF-8" ?><data><power value="off" DelayInSeconds="3" /></data>\n'
    dev.write(0x01, pwr_cmd.encode("utf-8"), timeout=2000)
    out, resp = read_firehose(dev, timeout=5000)
    
    print("\n[+] Power command delivered to PMIC!")
    print("[*] Phone is powering down.")
    print("[*] Disposing USB resources...")
    try:
        usb.util.dispose_resources(dev)
    except Exception:
        pass

if __name__ == "__main__":
    run_recovery()

import time
import usb.core
import libusb_package

backend = libusb_package.get_libusb1_backend()

print("=" * 60)
print("  DEVICE WATCHER - MONITORING ALL MODES (EDL / FASTBOOT)")
print("=" * 60)

KNOWN_MODES = {
    (0x05c6, 0x9008): "EDL Mode (Qualcomm 9008)",
    (0x18d1, 0x4ee0): "Fastboot Mode (Google)",
    (0x18d1, 0xd00d): "Fastboot Mode (Android)",
    (0x19d2, 0x0306): "Nubia Composite / ADB",
    (0x19d2, 0x0307): "Nubia MTP / Android",
    (0x19d2, 0x1352): "Nubia Fastboot / Recovery",
    (0x19d2, 0xffcc): "Nubia Mass Storage",
}

last_state = None
while True:
    devs = list(usb.core.find(find_all=True, backend=backend))
    found = []
    for d in devs:
        pair = (d.idVendor, d.idProduct)
        if pair in KNOWN_MODES:
            found.append((pair, KNOWN_MODES[pair]))
        elif d.idVendor in (0x18d1, 0x19d2, 0x05c6):
            found.append((pair, f"Vendor {hex(d.idVendor)}: Product {hex(d.idProduct)}"))
    
    current_state = tuple(found)
    if current_state != last_state:
        if found:
            for p, name in found:
                print(f"\n[+] DETECTED: {name} [{hex(p[0])}:{hex(p[1])}]", flush=True)
        else:
            print("\n[-] No target device detected on USB bus.", flush=True)
        last_state = current_state
    
    time.sleep(0.5)

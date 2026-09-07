import sys
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import time

backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)
if dev is None:
    print("Device not found")
    sys.exit(1)

print("[*] Sending Firehose reset command...")
reset_cmd = b'<?xml version="1.0" ?><data><power value="reset" /></data>\n'
try:
    dev.write(0x01, reset_cmd, timeout=2000)
    print("[+] Reset command sent!")
    res = dev.read(0x81, 4096, timeout=2000)
    print("[+] Response:", bytes(res).decode('utf-8', errors='ignore'))
except Exception as e:
    print("[-] Result:", e)

usb.util.dispose_resources(dev)
print("[+] Device reboot initiated.")

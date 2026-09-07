import usb.core, usb.backend.libusb1, libusb_package
backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=backend)

cfg = '<?xml version="1.0" encoding="UTF-8" ?><data><configure MemoryName="ufs" Verbose="0" AlwaysValidate="0" MaxDigestTableSizeInBytes="8192" MaxPayloadSizeToTargetInBytes="1048576" ZlpAwareHost="1" SkipStorageInit="0" Oem="ZTE"/></data>\n'
dev.write(0x01, cfg.encode('utf-8'), timeout=2000)

for _ in range(10):
    try:
        data = bytes(dev.read(0x81, 4096, timeout=1000))
        text = data.decode('utf-8', errors='ignore').strip()
        print(text)
        if '<response' in text:
            break
    except Exception as e:
        print('Timeout/err:', e)
        break
usb.util.dispose_resources(dev)

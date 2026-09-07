import sys
import os
import time
import struct
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import xml.etree.ElementTree as ET

DEVPRG_PATH = r"C:\Users\kernk\Redmagic8Pro\tools\zte_toolbox\bin\res\NX729J\devprg"
SECTOR_SIZE = 4096

class FirehoseClient:
    def __init__(self):
        self.backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        self.dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=self.backend)
        if self.dev is None:
            raise RuntimeError("Qualcomm 9008 device not found.")
        self.max_payload = 1048576

    def close(self):
        if self.dev:
            try:
                usb.util.dispose_resources(self.dev)
            except Exception:
                pass
            self.dev = None

    def reopen(self, retries=10):
        self.close()
        for _ in range(retries):
            time.sleep(0.5)
            self.dev = usb.core.find(idVendor=0x05c6, idProduct=0x9008, backend=self.backend)
            if self.dev is not None:
                return True
        return False

    def send_raw(self, data, timeout=5000):
        self.dev.write(0x01, data, timeout=timeout)

    def send_xml(self, xml_str, timeout=5000):
        if isinstance(xml_str, str):
            data = xml_str.encode('utf-8')
        else:
            data = xml_str
        if len(data) % SECTOR_SIZE != 0:
            data = data + b"\x00" * (SECTOR_SIZE - (len(data) % SECTOR_SIZE))
        self.dev.write(0x01, data, timeout=timeout)

    def read_raw(self, length, timeout=5000):
        return bytes(self.dev.read(0x81, length, timeout=timeout))

    def read_xml(self, timeout=3000):
        buf = bytearray()
        t0 = time.time()
        while time.time() - t0 < (timeout / 1000.0):
            try:
                chunk = bytes(self.dev.read(0x81, 4096, timeout=1000))
                buf.extend(chunk)
                if b"<response" in buf and (b"/>" in buf or b"</response>" in buf):
                    break
            except Exception:
                pass
        return buf.decode('utf-8', errors='ignore')

    def check_mode(self):
        """Returns 'firehose', 'sahara', or 'unknown'."""
        try:
            self.send_xml('<?xml version="1.0" ?><data><nop /></data>\n', timeout=1000)
            res = self.read_xml(timeout=1000)
            if "response" in res or "log" in res:
                return "firehose"
        except Exception:
            pass

        try:
            pkt = self.read_raw(512, timeout=1000)
            if len(pkt) >= 4:
                cmd = struct.unpack("<I", pkt[:4])[0]
                if cmd == 0x01: # SAHARA_HELLO_REQ
                    return "sahara_hello"
                elif cmd == 0x08: # RESET_RSP
                    return "sahara_reset_rsp"
            if b"<?xml" in pkt:
                return "firehose"
        except Exception:
            pass

        return "unknown"

    def enter_firehose(self):
        mode = self.check_mode()
        print(f"[*] Initial mode detected: {mode}")

        if mode == "firehose":
            print("[+] Firehose is already running.")
            return True

        if mode in ["sahara_hello", "unknown", "sahara_reset_rsp"]:
            print("[*] Performing Sahara upload of devprg...")
            with open(DEVPRG_PATH, "rb") as f:
                devprg_data = f.read()

            # If reset rsp or unknown, try reading hello or sending reset
            hello_data = None
            for _ in range(3):
                try:
                    p = self.read_raw(512, timeout=1000)
                    if len(p) >= 4 and struct.unpack("<I", p[:4])[0] == 1:
                        hello_data = p
                        break
                except Exception:
                    pass
                if not hello_data:
                    print("[*] Sending Sahara reset to wake PBL...")
                    try:
                        self.send_raw(struct.pack("<II", 7, 8), timeout=1000)
                    except Exception:
                        pass
                    self.reopen()
                    time.sleep(1)

            if not hello_data:
                raise RuntimeError("Failed to obtain SAHARA_HELLO_REQ from PBL.")

            cmd, plen, version, min_version, max_cmd_len, smode = struct.unpack("<IIIIII", hello_data[:24])
            print(f"[+] Sahara Hello: Version {version}, Mode {smode}")

            # Send Hello response (mode 0 = IMAGE_TX_PENDING)
            hello_rsp = struct.pack("<IIIIIIIIIIII", 2, 0x30, version, 1, 0, 0, 0, 0, 0, 0, 0, 0)
            self.send_raw(hello_rsp, timeout=1000)

            # Stream devprg
            while True:
                pkt = self.read_raw(512, timeout=5000)
                cmd, plen = struct.unpack("<II", pkt[:8])
                if cmd == 0x12: # 64-bit read
                    cmd, plen, img_id, offset, length = struct.unpack("<IIQQQ", pkt[:32])
                    chunk = devprg_data[offset : offset + length]
                    if len(chunk) < length:
                        chunk = chunk + b"\xFF" * (length - len(chunk))
                    self.send_raw(chunk, timeout=5000)
                elif cmd == 0x03: # 32-bit read
                    cmd, plen, img_id, offset, length = struct.unpack("<IIIII", pkt[:20])
                    chunk = devprg_data[offset : offset + length]
                    if len(chunk) < length:
                        chunk = chunk + b"\xFF" * (length - len(chunk))
                    self.send_raw(chunk, timeout=5000)
                elif cmd == 0x04: # SAHARA_END_TRANSFER
                    cmd, plen, img_id, status = struct.unpack("<IIII", pkt[:16])
                    if status != 0:
                        raise RuntimeError(f"Sahara transfer failed with status {status:#x}")
                    # Send DONE_REQ
                    self.send_raw(struct.pack("<II", 0x05, 0x08), timeout=1000)
                    try:
                        self.read_raw(512, timeout=2000)
                    except Exception:
                        pass
                    break
                elif cmd == 0x01:
                    self.send_raw(hello_rsp, timeout=1000)

            print("[+] devprg successfully uploaded!")
            time.sleep(1)

        # Configure Firehose
        print("[*] Configuring Firehose for UFS...")
        # Drain banner
        for _ in range(5):
            try:
                self.read_raw(4096, timeout=500)
            except Exception:
                break

        cfg_xml = b'<?xml version="1.0" encoding="UTF-8" ?><data><configure MemoryName="ufs" Verbose="0" AlwaysValidate="0" MaxDigestTableSizeInBytes="8192" MaxPayloadSizeToTargetInBytes="1048576" ZlpAwareHost="1" SkipStorageInit="0" Oem="ZTE"/></data>\n'
        self.send_xml(cfg_xml, timeout=2000)
        cfg_resp = self.read_xml(timeout=3000)
        print("[+] Firehose configure output:\n", cfg_resp.strip())
        if 'value="ACK"' in cfg_resp:
            print("[+] Firehose UFS configured successfully!")
            return True
        else:
            print("[-] Warning: Firehose configure did not ACK immediately, checking NOP...")
            self.send_xml('<?xml version="1.0" ?><data><nop /></data>\n', timeout=1000)
            nop_resp = self.read_xml(timeout=1000)
            print("NOP resp:", nop_resp.strip())
            return 'value="ACK"' in nop_resp

    def read_sectors(self, lun, start_sector, num_sectors):
        """Reads num_sectors from LUN starting at start_sector (4096 bytes per sector)."""
        cmd_xml = f'<?xml version="1.0" ?><data><read SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{num_sectors}" physical_partition_number="{lun}" start_sector="{start_sector}" /></data>\n'
        self.send_xml(cmd_xml, timeout=5000)

        # Read ACK
        ack_xml = self.read_xml(timeout=3000)
        if 'value="ACK"' not in ack_xml:
            raise RuntimeError(f"Read request NAKed by Firehose: {ack_xml}")

        # Read binary payload
        total_bytes = num_sectors * SECTOR_SIZE
        payload = bytearray()
        while len(payload) < total_bytes:
            chunk = self.read_raw(min(total_bytes - len(payload), self.max_payload), timeout=5000)
            if len(chunk) == 0:
                raise RuntimeError(f"Premature EOF while reading payload ({len(payload)}/{total_bytes} bytes)")
            payload.extend(chunk)

        # Read completion ACK
        comp_xml = self.read_xml(timeout=3000)
        return bytes(payload)

    def write_sectors(self, lun, start_sector, data):
        """Writes byte data to LUN starting at start_sector."""
        num_sectors = (len(data) + SECTOR_SIZE - 1) // SECTOR_SIZE
        padded_data = data + b"\x00" * (num_sectors * SECTOR_SIZE - len(data))

        cmd_xml = f'<?xml version="1.0" ?><data><program SECTOR_SIZE_IN_BYTES="{SECTOR_SIZE}" num_partition_sectors="{num_sectors}" physical_partition_number="{lun}" start_sector="{start_sector}" /></data>\n'
        self.send_xml(cmd_xml, timeout=5000)

        ack_xml = self.read_xml(timeout=3000)
        if 'value="ACK"' not in ack_xml:
            raise RuntimeError(f"Program request NAKed by Firehose: {ack_xml}")

        # Stream payload
        offset = 0
        while offset < len(padded_data):
            chunk = padded_data[offset : offset + self.max_payload]
            self.send_raw(chunk, timeout=10000)
            offset += len(chunk)

        comp_xml = self.read_xml(timeout=5000)
        if 'value="ACK"' not in comp_xml:
            raise RuntimeError(f"Write failed to complete with ACK: {comp_xml}")
        return True

    def parse_gpt(self, lun):
        """Reads and parses GPT on the given LUN. Returns dict of partition_name -> (start_sector, num_sectors)."""
        try:
            # Read first 6 sectors (MBR + GPT Header + Entries)
            gpt_raw = self.read_sectors(lun, 0, 6)
        except Exception as e:
            print(f"[-] LUN {lun} read error: {e}")
            return None

        # Check GPT header at Sector 1 (offset 4096)
        hdr = gpt_raw[SECTOR_SIZE : SECTOR_SIZE + 92]
        sig, rev, hdr_size, crc, reserved, cur_lba, backup_lba, first_lba, last_lba = struct.unpack("<8sIIIIQQQQ", hdr[:56])
        if sig != b"EFI PART":
            return None

        part_entry_lba, num_entries, entry_size, part_crc = struct.unpack("<QIII", hdr[72:88])

        # If entries exceed the sectors we read, read more
        entries_offset = (part_entry_lba * SECTOR_SIZE)
        total_entries_bytes = num_entries * entry_size
        needed_sectors = (entries_offset + total_entries_bytes + SECTOR_SIZE - 1) // SECTOR_SIZE

        if needed_sectors > 6:
            gpt_raw = self.read_sectors(lun, 0, needed_sectors)

        entries_data = gpt_raw[entries_offset : entries_offset + total_entries_bytes]
        partitions = {}
        for i in range(num_entries):
            entry = entries_data[i * entry_size : (i + 1) * entry_size]
            type_guid = entry[:16]
            if type_guid == b"\x00" * 16:
                continue
            first_sec, last_sec, flags = struct.unpack("<QQQ", entry[32:56])
            name_raw = entry[56:128]
            name = name_raw.decode('utf-16-le').rstrip('\x00')
            partitions[name] = {
                "lun": lun,
                "start_sector": first_sec,
                "num_sectors": last_sec - first_sec + 1,
                "size_bytes": (last_sec - first_sec + 1) * SECTOR_SIZE
            }
        return partitions

    def reset_to_system(self):
        print("[*] Sending Firehose reset command...")
        try:
            self.send_xml('<?xml version="1.0" ?><data><power value="reset" /></data>\n', timeout=2000)
            resp = self.read_xml(timeout=2000)
            print("[+] Reset response:", resp.strip())
        except Exception as e:
            print("[-] Reset sent (device disconnecting):", e)

if __name__ == "__main__":
    fh = FirehoseClient()
    try:
        fh.enter_firehose()
        print("\n" + "="*50)
        print("[*] Scanning all LUNs for partitions...")
        all_parts = {}
        for lun in range(8):
            parts = fh.parse_gpt(lun)
            if parts:
                print(f"[+] LUN {lun}: Found {len(parts)} partitions")
                for name, info in parts.items():
                    all_parts[name] = info
                    if "abl" in name.lower() or "boot" in name.lower() or "vbmeta" in name.lower():
                        print(f"    - {name:<20}: Sector {info['start_sector']:<10} Count {info['num_sectors']:<8} ({info['size_bytes']//1024} KB)")
        
        print("\n" + "="*50)
        if "abl_a" in all_parts:
            print("[✓] TARGET PARTITIONS LOCATED:")
            print(f"    abl_a: LUN {all_parts['abl_a']['lun']}, Start {all_parts['abl_a']['start_sector']}, Count {all_parts['abl_a']['num_sectors']}")
            if "abl_b" in all_parts:
                print(f"    abl_b: LUN {all_parts['abl_b']['lun']}, Start {all_parts['abl_b']['start_sector']}, Count {all_parts['abl_b']['num_sectors']}")
    finally:
        fh.close()

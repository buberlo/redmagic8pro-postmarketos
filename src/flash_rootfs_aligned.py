#!/usr/bin/env python3
"""
Flash postmarketOS rootfs (pmOS_root) aligned to Partition 13 on UFS (\\.\PhysicalDrive1).
Chunk 18 in postmarketos-phosh.img.xz marks the exact start of pmOS_root at block 124928.
Writing chunk 18 onwards directly to Partition 13 places the ext4 superblock at offset 1024.
"""
import os
import sys
import time
import lzma
import struct

IMG_XZ_PATH = r"firmware\postmarketos-phosh.img.xz"
DISK_PATH = r"\\.\PhysicalDrive1"
PARTITION_13_OFFSET = 12184453120  # LUN 0 Partition 13 (pmos_root)
ROOTFS_START_BLK = 124928

CHUNK_TYPE_RAW       = 0xCAC1
CHUNK_TYPE_FILL      = 0xCAC2
CHUNK_TYPE_DONT_CARE = 0xCAC3
CHUNK_TYPE_CRC32     = 0xCAC4

def flash_aligned_rootfs():
    if not os.path.exists(IMG_XZ_PATH):
        raise FileNotFoundError(f"{IMG_XZ_PATH} does not exist!")

    print(f"[*] Opening {IMG_XZ_PATH} and target {DISK_PATH} at {PARTITION_13_OFFSET}...")
    
    decompressor = lzma.LZMADecompressor()
    class LzmaStreamReader:
        def __init__(self, f_in):
            self.f_in = f_in
            self.buf = bytearray()
            self.eof = False
            
        def read(self, n):
            while len(self.buf) < n and not self.eof:
                raw = self.f_in.read(512 * 1024)
                if not raw:
                    self.eof = True
                    break
                self.buf.extend(decompressor.decompress(raw))
            res = bytes(self.buf[:n])
            del self.buf[:n]
            return res

    with open(IMG_XZ_PATH, "rb") as xz_f, open(DISK_PATH, "r+b") as disk:
        reader = LzmaStreamReader(xz_f)
        disk.seek(PARTITION_13_OFFSET)
        
        hdr = reader.read(28)
        magic, maj, minv, fhdr_sz, chdr_sz, blk_sz, total_blks, total_chunks, crc = struct.unpack("<I4H4I", hdr[:28])
        if magic != 0xED26FF3A:
            raise ValueError(f"Invalid sparse magic: {hex(magic)}")
            
        print(f"[+] Sparse Header: blk_sz={blk_sz}, total_blks={total_blks}, total_chunks={total_chunks}")
        if fhdr_sz > 28:
            reader.read(fhdr_sz - 28)
            
        cur_blk = 0
        written_bytes = 0
        t0 = time.time()
        last_log = 0
        
        for c_idx in range(total_chunks):
            chdr = reader.read(chdr_sz)
            c_type, reserved, c_sz_blks, total_sz_bytes = struct.unpack("<2H2I", chdr[:12])
            data_bytes = c_sz_blks * blk_sz
            
            if cur_blk < ROOTFS_START_BLK:
                # Discard chunks before the rootfs
                if c_type == CHUNK_TYPE_RAW:
                    rem = data_bytes
                    while rem > 0:
                        b = reader.read(min(rem, 1024 * 1024))
                        rem -= len(b)
                elif c_type == CHUNK_TYPE_FILL:
                    reader.read(4)
                elif c_type == CHUNK_TYPE_DONT_CARE:
                    pass
                elif c_type == CHUNK_TYPE_CRC32:
                    reader.read(4)
            else:
                # We are in pmOS_root partition!
                if c_type == CHUNK_TYPE_RAW:
                    rem = data_bytes
                    while rem > 0:
                        b = reader.read(min(rem, 1024 * 1024))
                        disk.write(b)
                        rem -= len(b)
                    written_bytes += data_bytes
                elif c_type == CHUNK_TYPE_FILL:
                    fill_val = reader.read(4)
                    fill_pattern = fill_val * (blk_sz // 4)
                    chunk_blks = min(c_sz_blks, 256)
                    pattern_buf = fill_pattern * chunk_blks
                    blks_left = c_sz_blks
                    while blks_left > 0:
                        to_write = min(blks_left, chunk_blks)
                        disk.write(pattern_buf[:to_write * blk_sz])
                        blks_left -= to_write
                    written_bytes += data_bytes
                elif c_type == CHUNK_TYPE_DONT_CARE:
                    disk.seek(data_bytes, os.SEEK_CUR)
                elif c_type == CHUNK_TYPE_CRC32:
                    reader.read(4)
                    
            cur_blk += c_sz_blks
            
            now = time.time()
            if now - last_log >= 5 or c_idx == total_chunks - 1:
                elapsed = now - t0
                pct = ((c_idx + 1) / total_chunks) * 100
                speed = (written_bytes / (1e6 * elapsed)) if elapsed > 0 else 0
                print(f"\rFlashing rootfs: {pct:5.1f}% [Chunk {c_idx+1}/{total_chunks}] Written: {written_bytes/1e6:6.1f} MB @ {speed:4.1f} MB/s", end="", flush=True)
                last_log = now
                
        disk.flush()
        total_time = time.time() - t0
        print(f"\n[+] Flashing complete! Wrote {written_bytes / (1024**2):.2f} MB in {total_time:.1f}s ({written_bytes / (1e6 * total_time):.1f} MB/s)")

    # Verify ext4 superblock at offset 1024 of Partition 13
    with open(DISK_PATH, "rb") as disk:
        disk.seek(PARTITION_13_OFFSET)
        first_sector = disk.read(4096)
        sb = first_sector[1024:2048]
        magic = struct.unpack("<H", sb[56:58])[0]
        uuid = sb[104:120]
        uuid_str = f"{uuid[0:4].hex()}-{uuid[4:6].hex()}-{uuid[6:8].hex()}-{uuid[8:10].hex()}-{uuid[10:16].hex()}"
        vol_name = sb[120:136].decode("latin1").rstrip("\x00")
        
        print("\n" + "=" * 50)
        print("  ROOTFS VERIFICATION RESULTS:")
        print("=" * 50)
        print(f"  Partition Offset:    {PARTITION_13_OFFSET}")
        print(f"  Superblock Magic:    {hex(magic)} (Expected: 0xef53)")
        print(f"  Volume Name:         {vol_name} (Expected: pmOS_root)")
        print(f"  Filesystem UUID:     {uuid_str}")
        print("=" * 50)
        
        if magic == 0xEF53 and vol_name == "pmOS_root":
            print("[+] SUCCESS! Partition 13 is a valid, aligned EXT4 root filesystem!")
            return True
        else:
            raise RuntimeError(f"Superblock verification failed: magic={hex(magic)}, vol={vol_name}")

if __name__ == "__main__":
    flash_aligned_rootfs()

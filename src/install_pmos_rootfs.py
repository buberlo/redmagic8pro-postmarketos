#!/usr/bin/env python3
"""
Stream postmarketOS rootfs directly into Partition 13 of UFS LUN 0.
"""
import os
import sys
import time
import lzma

DISK_PATH = r"\\.\PhysicalDrive1"
PARTITION_OFFSET = 12184453120  # Offset of partition 13 (pmos_root)
IMAGE_PATH = r"firmware\postmarketos-phosh.img.xz"

def stream_rootfs():
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: {IMAGE_PATH} does not exist!")
        return False
    
    compressed_size = os.path.getsize(IMAGE_PATH)
    print(f"Starting stream of {IMAGE_PATH} ({compressed_size / 1e6:.1f} MB)")
    print(f"Target: {DISK_PATH} at offset {PARTITION_OFFSET}")
    
    t0 = time.time()
    bytes_read = 0
    bytes_written = 0
    
    decompressor = lzma.LZMADecompressor()
    
    with open(DISK_PATH, "r+b") as disk:
        disk.seek(PARTITION_OFFSET)
        with open(IMAGE_PATH, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                bytes_read += len(chunk)
                data = decompressor.decompress(chunk)
                if data:
                    disk.write(data)
                    bytes_written += len(data)
                
                elapsed = time.time() - t0
                speed_mb = (bytes_written / 1e6) / elapsed if elapsed > 0 else 0
                pct = (bytes_read / compressed_size) * 100
                print(f"\rProgress: {pct:5.1f}% | In: {bytes_read / 1e6:6.1f}MB | Out: {bytes_written / 1e6:6.1f}MB | Speed: {speed_mb:5.1f} MB/s", end="", flush=True)
        
        disk.flush()
    total_time = time.time() - t0
    print(f"\nComplete! Flashed {bytes_written / 1e6:.1f} MB in {total_time:.1f}s ({bytes_written / (1e6 * total_time):.1f} MB/s)")
    return True

if __name__ == "__main__":
    stream_rootfs()

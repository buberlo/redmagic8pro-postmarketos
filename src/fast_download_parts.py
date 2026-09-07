#!/usr/bin/env python3
"""
Parallel curl downloader that downloads 8 parts simultaneously and merges them.
"""
import os
import sys
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "https://images.postmarketos.org/bpo/edge/fairphone-fp5/phosh/20260904-1343/20260904-1343-postmarketOS-edge-phosh-33-fairphone-fp5.img.xz"
TOTAL_SIZE = 774012792
PARTS_DIR = r"firmware\parts"
FINAL_FILE = r"firmware\postmarketos-phosh.img.xz"
NUM_PARTS = 8

def download_part(part_idx, start_byte, end_byte):
    part_file = os.path.join(PARTS_DIR, f"part_{part_idx}.bin")
    expected_size = end_byte - start_byte + 1
    
    # Check if already fully downloaded
    if os.path.exists(part_file) and os.path.getsize(part_file) == expected_size:
        print(f"[Part {part_idx}] Already complete ({expected_size / 1e6:.1f} MB)")
        return part_idx, True

    cmd = [
        "curl.exe", "-L", "-s",
        "-r", f"{start_byte}-{end_byte}",
        "--retry", "5",
        "--retry-delay", "2",
        URL,
        "-o", part_file
    ]
    t0 = time.time()
    res = subprocess.run(cmd)
    elapsed = time.time() - t0
    actual_size = os.path.getsize(part_file) if os.path.exists(part_file) else 0
    success = (actual_size == expected_size)
    print(f"[Part {part_idx}] Finished in {elapsed:.1f}s ({actual_size/1e6:.1f}MB, success={success})")
    return part_idx, success

def main():
    os.makedirs(PARTS_DIR, exist_ok=True)
    part_size = TOTAL_SIZE // NUM_PARTS
    chunks = []
    
    for i in range(NUM_PARTS):
        start = i * part_size
        end = (start + part_size - 1) if i < NUM_PARTS - 1 else (TOTAL_SIZE - 1)
        chunks.append((i, start, end))
        
    print(f"Launching {NUM_PARTS} parallel curl downloaders...")
    t_start = time.time()
    
    with ThreadPoolExecutor(max_workers=NUM_PARTS) as executor:
        futures = [executor.submit(download_part, i, s, e) for i, s, e in chunks]
        results = [f.result() for f in as_completed(futures)]
        
    all_success = all(r[1] for r in results)
    if not all_success:
        print("Some parts failed to download! Please re-run.")
        sys.exit(1)
        
    print(f"All {NUM_PARTS} parts downloaded in {time.time() - t_start:.1f}s! Merging into {FINAL_FILE}...")
    with open(FINAL_FILE, "wb") as out_f:
        for i in range(NUM_PARTS):
            part_file = os.path.join(PARTS_DIR, f"part_{i}.bin")
            with open(part_file, "rb") as in_f:
                while chunk := in_f.read(4 * 1024 * 1024):
                    out_f.write(chunk)
            print(f"Merged part {i}")
            
    print(f"Merge complete! File size: {os.path.getsize(FINAL_FILE)} bytes")

if __name__ == "__main__":
    main()

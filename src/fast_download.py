#!/usr/bin/env python3
"""
High-speed multithreaded chunk downloader for postmarketOS images.
"""
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "https://images.postmarketos.org/bpo/edge/fairphone-fp5/phosh/20260904-1343/20260904-1343-postmarketOS-edge-phosh-33-fairphone-fp5.img.xz"
OUT_PATH = r"firmware\postmarketos-phosh.img.xz"
NUM_THREADS = 16

def get_file_size(url):
    req = urllib.request.Request(url, method='HEAD')
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req) as resp:
        return int(resp.headers.get('Content-Length', 0))

def download_chunk(url, start_byte, end_byte, part_num, out_file_path, progress_dict):
    req = urllib.request.Request(url)
    req.add_header('Range', f'bytes={start_byte}-{end_byte}')
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    with urllib.request.urlopen(req) as resp:
        with open(out_file_path, "r+b") as f:
            f.seek(start_byte)
            curr = start_byte
            while curr <= end_byte:
                chunk = resp.read(min(65536, end_byte - curr + 1))
                if not chunk:
                    break
                f.write(chunk)
                curr += len(chunk)
                progress_dict[part_num] = curr - start_byte

def main():
    total_size = get_file_size(URL)
    print(f"Total file size: {total_size / (1024*1024):.2f} MB")
    
    # Pre-allocate output file
    if not os.path.exists(OUT_PATH) or os.path.getsize(OUT_PATH) != total_size:
        with open(OUT_PATH, "wb") as f:
            f.seek(total_size - 1)
            f.write(b'\0')
    
    chunk_size = total_size // NUM_THREADS
    chunks = []
    progress_dict = {}
    
    for i in range(NUM_THREADS):
        start = i * chunk_size
        end = (start + chunk_size - 1) if i < NUM_THREADS - 1 else (total_size - 1)
        chunks.append((start, end, i))
        progress_dict[i] = 0
        
    print(f"Spawning {NUM_THREADS} download workers...")
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = [executor.submit(download_chunk, URL, start, end, idx, OUT_PATH, progress_dict) for start, end, idx in chunks]
        
        while not all(f.done() for f in futures):
            downloaded = sum(progress_dict.values())
            elapsed = time.time() - t0
            speed = (downloaded / (1024*1024)) / elapsed if elapsed > 0 else 0
            pct = (downloaded / total_size) * 100
            print(f"\rProgress: {pct:5.1f}% [{downloaded / (1024*1024):6.1f} / {total_size / (1024*1024):.1f} MB] Speed: {speed:5.2f} MB/s", end="", flush=True)
            time.sleep(0.5)
            
        for f in as_completed(futures):
            f.result()
            
    total_time = time.time() - t0
    final_speed = (total_size / (1024*1024)) / total_time
    print(f"\nDownload finished in {total_time:.1f}s at {final_speed:.2f} MB/s!")

if __name__ == "__main__":
    main()

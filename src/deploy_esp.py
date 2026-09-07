import os
import sys
import time
import shutil

STAGING = "staging_esp"
TARGET_DRIVE = "E:\\"

print("[*] Waiting for phone Mass Storage mode (Drive E:)...")
while not os.path.exists(TARGET_DRIVE):
    time.sleep(1)

print("[+] Drive E: detected! Copying updated UEFI boot assets...")

# Clean existing EFI and boot directories on Drive E:
for d in ["EFI", "boot", "loader"]:
    dest_dir = os.path.join(TARGET_DRIVE, d)
    src_dir = os.path.join(STAGING, d)
    if os.path.exists(src_dir):
        os.makedirs(dest_dir, exist_ok=True)
        for root, dirs, files in os.walk(src_dir):
            rel_root = os.path.relpath(root, src_dir)
            target_sub = os.path.join(dest_dir, rel_root) if rel_root != "." else dest_dir
            os.makedirs(target_sub, exist_ok=True)
            for f in files:
                src_file = os.path.join(root, f)
                dst_file = os.path.join(target_sub, f)
                print(f"  Copying {f} ({os.path.getsize(src_file)} bytes)...")
                shutil.copy2(src_file, dst_file)

# Copy root files (fan daemon scripts)
for f in os.listdir(STAGING):
    src_f = os.path.join(STAGING, f)
    if os.path.isfile(src_f):
        dst_f = os.path.join(TARGET_DRIVE, f)
        print(f"  Copying {f}...")
        shutil.copy2(src_f, dst_f)

print("[+] All UEFI boot assets deployed successfully to Drive E:!")

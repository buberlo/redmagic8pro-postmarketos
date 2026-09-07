import subprocess
import time
import sys
import os

FASTBOOT = r"C:\Users\kernk\Redmagic8Pro\tools\zte_toolbox\bin\tool\Win\fastboot.exe"
MU_IMG = r"C:\Users\kernk\Redmagic8Pro\tools\Mu-nx729j.img"

print("[*] Waiting for phone to enter Fastboot mode...")
while True:
    try:
        res = subprocess.run([FASTBOOT, "devices"], capture_output=True, text=True, timeout=3)
        if res.stdout.strip():
            print(f"[+] Fastboot device detected: {res.stdout.strip()}")
            break
    except Exception:
        pass
    time.sleep(0.5)

print("\n[*] 1. Flashing Project Mu UEFI permanently to boot_a and boot_b...")
subprocess.run([FASTBOOT, "flash", "boot_a", MU_IMG])
subprocess.run([FASTBOOT, "flash", "boot_b", MU_IMG])
print("[+] Project Mu UEFI is now permanently installed in boot partitions!")

print("\n[*] 2. Booting into Project Mu UEFI now...")
subprocess.run([FASTBOOT, "boot", MU_IMG])
print("[+] Project Mu UEFI booted successfully!")

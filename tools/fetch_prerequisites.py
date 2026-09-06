import os
import sys
import base64
import urllib.request
from pathlib import Path

WORKSPACE = Path(r"C:/Users/kernk/Redmagic8Pro")
TOOLS_DIR = WORKSPACE / "tools"
FIRMWARE_DIR = WORKSPACE / "firmware"

TOOLS_DIR.mkdir(exist_ok=True)
FIRMWARE_DIR.mkdir(exist_ok=True)

print("=== Fetching Red Magic 8 Pro Prerequisites & Tooling ===")

headers = {'User-Agent': 'Mozilla/5.0'}

# 1. Download Mu-nx729j.img
mu_target = TOOLS_DIR / "Mu-nx729j.img"
if not mu_target.exists():
    mu_url = "https://github.com/Project-Silicium/Mu-Silicium/releases/download/v3.0.8/Mu-nx729j.img"
    print(f"[*] Downloading {mu_url}...")
    try:
        req = urllib.request.Request(mu_url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(mu_target, 'wb') as f:
            f.write(resp.read())
        print(f"[OK] Saved Mu-nx729j.img ({mu_target.stat().st_size / 1024 / 1024:.2f} MB)")
    except Exception as e:
        print(f"[!] Error downloading Mu-nx729j.img: {e}")
else:
    print(f"[OK] Mu-nx729j.img already present ({mu_target.stat().st_size / 1024 / 1024:.2f} MB)")

# 2. Download AOSP mkbootimg & unpack_bootimg tools (base64 from googlesource)
aosp_tools = [
    ("mkbootimg.py", "https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/mkbootimg.py?format=TEXT"),
    ("unpack_bootimg.py", "https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/unpack_bootimg.py?format=TEXT"),
]

for tool_name, url in aosp_tools:
    tool_target = TOOLS_DIR / tool_name
    if not tool_target.exists():
        print(f"[*] Downloading {tool_name} from AOSP...")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as resp:
                b64_content = resp.read()
                raw_code = base64.b64decode(b64_content)
                tool_target.write_bytes(raw_code)
            print(f"[OK] Saved {tool_name}")
        except Exception as e:
            print(f"[!] Error downloading {tool_name}: {e}")
    else:
        print(f"[OK] {tool_name} already present")

print("Prerequisites staging completed.")

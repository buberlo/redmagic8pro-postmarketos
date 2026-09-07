import io, struct
# Read FAT32 boot sector at offset
BOOT_OFFSET = 12184453120 + 2048 * 4096
with open(r"\\.\PhysicalDrive1", "rb") as disk:
    disk.seek(BOOT_OFFSET)
    bs = disk.read(4096)
bytes_per_sec, sec_per_clus, rsvd_sec, num_fats = struct.unpack("<HBHB", bs[11:17])
fat_sz32 = struct.unpack("<I", bs[36:40])[0]
root_clus = struct.unpack("<I", bs[44:48])[0]
print(f"FAT32: bps={bytes_per_sec}, spc={sec_per_clus}, rsvd={rsvd_sec}, fats={num_fats}, fat_sz={fat_sz32}, root_clus={root_clus}")
root_offset = BOOT_OFFSET + (rsvd_sec + num_fats * fat_sz32) * bytes_per_sec
print(f"Root dir offset: {root_offset}")
with open(r"\\.\PhysicalDrive1", "rb") as disk:
    disk.seek(root_offset)
    dir_data = disk.read(sec_per_clus * bytes_per_sec)
for i in range(0, len(dir_data), 32):
    entry = dir_data[i:i+32]
    if entry[0] == 0 or entry[0] == 0xe5: continue
    if entry[11] == 0x0f: continue # LFN
    name = entry[:8].decode('latin1').strip()
    ext = entry[8:11].decode('latin1').strip()
    size = struct.unpack("<I", entry[28:32])[0]
    print(f"File: {name}.{ext} ({size} bytes)")

import struct
PARTITION_13_OFFSET = 12184453120
ROOTFS_OFFSET_IN_IMG = 124928 * 4096
with open(r"\\.\PhysicalDrive1", "rb") as disk:
    disk.seek(PARTITION_13_OFFSET + ROOTFS_OFFSET_IN_IMG)
    sector = disk.read(4096)
sb = sector[1024:2048]
magic = struct.unpack("<H", sb[0x38:0x3A])[0]
print(f"Superblock Magic at Part 2: {hex(magic)} (Expected 0xef53 for EXT4)")
vol_name = sb[0x78:0x88].decode('latin1').rstrip('\x00')
print(f"Volume Label: '{vol_name}'")

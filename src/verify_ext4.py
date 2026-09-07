import struct
PARTITION_13_OFFSET = 12184453120
with open(r"\\.\PhysicalDrive1", "rb") as disk:
    disk.seek(PARTITION_13_OFFSET)
    sector = disk.read(4096)
sb = sector[1024:2048]
magic = struct.unpack("<H", sb[0x38:0x3A])[0]
print(f"Superblock Magic: {hex(magic)} (Expected 0xef53 for EXT4)")
inodes_count, blocks_count, r_blocks_count, free_blocks, free_inodes = struct.unpack("<5I", sb[:20])
print(f"Total Blocks: {blocks_count}, Free Blocks: {free_blocks}")
print(f"Total Inodes: {inodes_count}, Free Inodes: {free_inodes}")
vol_name = sb[0x78:0x88].decode('latin1').rstrip('\x00')
print(f"Volume Label: '{vol_name}'")

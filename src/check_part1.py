PARTITION_13_OFFSET = 12184453120
BOOT_OFFSET = 2048 * 4096
with open(r"\\.\PhysicalDrive1", "rb") as disk:
    disk.seek(PARTITION_13_OFFSET + BOOT_OFFSET)
    sector = disk.read(4096)
print("Part 1 Boot Jump Code:", sector[:3].hex())
print("Part 1 OEM Name:", sector[3:11])
print("Part 1 Volume Label:", sector[0x47:0x52])

import uuid
PARTITION_13_OFFSET = 12184453120
ROOTFS_OFFSET_IN_IMG = 124928 * 4096
with open(r"\\.\PhysicalDrive1", "rb") as disk:
    disk.seek(PARTITION_13_OFFSET + ROOTFS_OFFSET_IN_IMG)
    sector = disk.read(4096)
sb = sector[1024:2048]
fs_uuid = uuid.UUID(bytes=sb[0x68:0x78])
print(f"Ext4 Filesystem UUID: {fs_uuid}")

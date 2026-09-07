import lzma, struct
CHUNK_NAMES = {0xCAC1: "RAW", 0xCAC2: "FILL", 0xCAC3: "DONT_CARE", 0xCAC4: "CRC32"}
with open(r"firmware\postmarketos-phosh.img.xz", "rb") as xz_f:
    decompressor = lzma.LZMADecompressor()
    data = b""
    while len(data) < 28 + 12 * 20:
        data += decompressor.decompress(xz_f.read(65536))

offset = 28
curr_block = 0
for i in range(15):
    c_type, reserved, c_sz_blks, total_sz_bytes = struct.unpack("<2H2I", data[offset:offset+12])
    print(f"Chunk {i:2d}: {CHUNK_NAMES.get(c_type, hex(c_type)):10s} blks={c_sz_blks:<6d} total_sz={total_sz_bytes:<8d} at block {curr_block}")
    curr_block += c_sz_blks
    offset += 12
    if c_type == 0xCAC1:
        pass

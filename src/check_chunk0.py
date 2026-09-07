import lzma, struct
with open(r"firmware\postmarketos-phosh.img.xz", "rb") as xz_f:
    decompressor = lzma.LZMADecompressor()
    data = b""
    while len(data) < 28 + 12 + 12288:
        data += decompressor.decompress(xz_f.read(65536))

chunk0_data = data[28+12 : 28+12+12288]
print("Chunk 0 len:", len(chunk0_data))
sb = chunk0_data[1024:2048]
magic = struct.unpack("<H", sb[0x38:0x3A])[0]
print(f"Extracted Magic from chunk 0: {hex(magic)}")
vol_name = sb[0x78:0x88].decode('latin1').rstrip('\x00')
print(f"Volume Label: '{vol_name}'")

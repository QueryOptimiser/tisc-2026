import struct
import pefile
import subprocess
import json

with open("challenge.exe", "rb") as f:
    data = bytearray(f.read())

def rol32(v, n):
    n &= 31
    v &= 0xFFFFFFFF
    return ((v << n) | (v >> (32 - n))) & 0xFFFFFFFF

rich_off = data.find(b"Rich")
old_key = struct.unpack_from("<I", data, rich_off + 4)[0]

dans_target = struct.unpack("<I", b"DanS")[0] ^ old_key
dans_off = None
for off in range(0x80, rich_off):
    if struct.unpack_from("<I", data, off)[0] == dans_target:
        dans_off = off
        break

enc = data[dans_off:rich_off]
clear = bytearray()
for i in range(0, len(enc), 4):
    val = struct.unpack_from("<I", enc, i)[0]
    clear += struct.pack("<I", val ^ old_key)

pairs = []
for i in range(16, len(clear), 8):
    compid, count = struct.unpack_from("<II", clear, i)
    pairs.append([compid, count])

def rich_checksum(data, dans_off, pairs):
    chk = dans_off
    for i in range(dans_off):
        b = 0 if 0x3C <= i < 0x40 else data[i]
        chk = (chk + rol32(b, i)) & 0xFFFFFFFF
    for compid, count in pairs:
        chk = (chk + rol32(compid, count)) & 0xFFFFFFFF
    return chk

assert rich_checksum(data, dans_off, pairs) == old_key
print("original checksum verified OK")

OLD_BUILD, NEW_BUILD = 25017, 35207
new_pairs = [
    [(compid & 0xFFFF0000) | NEW_BUILD, count] if (compid & 0xFFFF) == OLD_BUILD
    else [compid, count]
    for compid, count in pairs
]

new_key = rich_checksum(data, dans_off, new_pairs)

new_clear = bytearray(b"DanS" + b"\x00" * 12)
for compid, count in new_pairs:
    new_clear += struct.pack("<II", compid, count)

new_enc = bytearray()
for i in range(0, len(new_clear), 4):
    val = struct.unpack_from("<I", new_clear, i)[0]
    new_enc += struct.pack("<I", val ^ new_key)

data[dans_off:rich_off] = new_enc
struct.pack_into("<I", data, rich_off + 4, new_key)

pe = pefile.PE(data=bytes(data))
oh_off = pe.OPTIONAL_HEADER.get_file_offset()
data[oh_off + 2] = 14
data[oh_off + 3] = 44

with open("challenge_repaired.exe", "wb") as f:
    f.write(data)

with open("challenge.exe", "rb") as f:
    orig = f.read()
diff = sum(1 for a, b in zip(orig, data) if a != b)
print("bytes different from original:", diff, "(orig len", len(orig), "new len", len(data), ")")

# submit via curl (avoids requests/proxy edge cases per skill guidance)
r = subprocess.run(
    ["curl", "-s", "-m", "20", "-F", "file=@challenge_repaired.exe",
     "http://chals.tisc26.ctf.sg:53219/submit"],
    capture_output=True, text=True
)
print("HTTP raw response:")
print(r.stdout)
print("stderr:", r.stderr)

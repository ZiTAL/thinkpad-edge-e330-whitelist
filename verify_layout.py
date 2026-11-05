#!/usr/bin/env python3
"""Validate the patched E330 BIOS region against the original dump.

Checks:
  * the inner PE32 module is byte-identical to LenovoWmaPolicyDxe.bin
  * the 8-byte code patch is present at PE offset 0xc58
  * the GUIDed-section CRC32 is correct
  * the inner and outer FFS header/data checksums are correct
  * the decompressed volume differs from the original only in the patch,
    the inner data checksum and the GUIDed CRC32
  * the 12 MB flash image carries the same patched BIOS region
Exit code 0 on success, 1 on any inconsistency.
"""
import hashlib
import lzma
import struct
import sys
import zlib

SRC = "bios_region.bin"
PATCHED = "bios_region_patched.bin"
FLASH12 = "flash_image_12m.bin"
MODULE = "LenovoWmaPolicyDxe.bin"

SEC_OFF = 0x20060
SEC_SIZE = 0x1E38E1
SEC_HDR = 9
VOL = 0x10
INNER_FILE = VOL + 0x525520
INNER_SEC = INNER_FILE + 0x18
INNER_CRC = INNER_SEC + 0x18
INNER_DATA = INNER_SEC + 0x1C   # PE32 section header (size/type)
PE = INNER_DATA + 4
PE_SIZE = 8576
PATCH_OFF = 0xC58
PATCH = bytes.fromhex("31c0e92600000090")
OUTER_FILE = 0x20048

ok = True


def check(name, cond, detail=""):
    global ok
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    if not cond:
        ok = False


def u8sum(data):
    return (0x100 - (sum(data) & 0xFF)) & 0xFF


def ffs_checksums(buf, start, size):
    body = buf[start + 0x18:start + size]
    hdr = bytearray(buf[start:start + 0x18])
    data_ck = u8sum(body)
    tmp = bytearray(buf[start:start + 0x18])
    tmp[0x10] = 0
    tmp[0x11] = 0
    tmp[0x17] = 0
    return hdr[0x10], hdr[0x11], u8sum(tmp), data_ck


def decompress(raw):
    return lzma.decompress(raw[SEC_OFF + SEC_HDR:SEC_OFF + SEC_SIZE], format=lzma.FORMAT_ALONE)


raw_o = open(SRC, "rb").read()
raw_p = open(PATCHED, "rb").read()
check("original region size", len(raw_o) == 0x400000, hex(len(raw_o)))
check("patched region size", len(raw_p) == 0x400000, hex(len(raw_p)))
check("sha256 original", hashlib.sha256(raw_o).hexdigest() == "8e3719c61c651a7bc78868b5cca90191e685e38407badf00f48a5a53d471f43d")
check("sha256 patched", hashlib.sha256(raw_p).hexdigest() == "a5bdf564340cc7805c23621464d9f8f39ca856371a1d89e8aa2871877a8003c2")

dec_o = decompress(raw_o)
dec_p = decompress(raw_p)
check("decompressed sizes", len(dec_o) == len(dec_p) == 0x780010, f"{len(dec_o):#x}/{len(dec_p):#x}")

orig_pe = open(MODULE, "rb").read()
pe_o = bytes(dec_o[PE:PE + PE_SIZE])
pe_p = bytes(dec_p[PE:PE + PE_SIZE])
check("original PE32 matches extracted module", pe_o == orig_pe)
check("patched PE32 differs only in the 8 patch bytes",
      pe_p[:PATCH_OFF] == orig_pe[:PATCH_OFF] and
      pe_p[PATCH_OFF + len(PATCH):] == orig_pe[PATCH_OFF + len(PATCH):])
check("PE32 patched bytes", pe_p[PATCH_OFF:PATCH_OFF + len(PATCH)] == PATCH, pe_p[PATCH_OFF:PATCH_OFF + len(PATCH)].hex())

crc_stored = struct.unpack_from("<I", dec_p, INNER_CRC)[0]
crc_calc = zlib.crc32(dec_p[INNER_DATA:INNER_SEC + 0x21DC]) & 0xFFFFFFFF
check("GUIDed section CRC32", crc_stored == crc_calc, f"stored {crc_stored:#010x}, calc {crc_calc:#010x}")

h_ok, d_ok, h_calc, d_calc = ffs_checksums(dec_p, INNER_FILE, 0x21F4)
check("inner FFS header checksum", h_ok == h_calc, f"stored {h_ok:#04x}, calc {h_calc:#04x}")
check("inner FFS data checksum", d_ok == d_calc, f"stored {d_ok:#04x}, calc {d_calc:#04x}")

h_ok, d_ok, h_calc, d_calc = ffs_checksums(raw_p, OUTER_FILE, 0x1E38F9)
check("outer FFS header checksum", h_ok == h_calc, f"stored {h_ok:#04x}, calc {h_calc:#04x}")
check("outer FFS data checksum", d_ok == d_calc, f"stored {d_ok:#04x}, calc {d_calc:#04x}")

diffs = [(i, a, b) for i, (a, b) in enumerate(zip(dec_o, dec_p)) if a != b]
groups = []
for i, a, b in diffs:
    if groups and i == groups[-1][1] + 1:
        groups[-1] = (groups[-1][0], i, groups[-1][2] + [(i, a, b)])
    else:
        groups.append((i, i, [(i, a, b)]))
expected = [
    (0x525541, 0x525541),
    (0x525560, 0x525563),
    (0x5261C0, 0x5261C7),
]
actual = [(g[0], g[1]) for g in groups]
check("decompressed diff ranges", actual == expected, str([(hex(a), hex(b)) for a, b in actual]))
for a, b, items in groups:
    print(f"       {a:#x}-{b:#x}: " + ", ".join(f"{x:#04x}->{y:#04x}" for _, x, y in items))

# The 12 MB flash image must carry exactly the patched BIOS region.
if __import__("os").path.exists(FLASH12):
    f12 = open(FLASH12, "rb").read()
    check("flash image size", len(f12) == 0xC00000, hex(len(f12)))
    check("flash image BIOS region", f12[0x800000:0xC00000] == raw_p)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""Build a whitelist-bypassed BIOS region for the ThinkPad Edge E330 (H3ET72WW 1.09).

Patch: LenovoWmaPolicyDxe!FUN_00000bd0, unauthorized-card path at PE offset 0xc58:
  48 8b ce e8 5c fe ff ff   mov rcx,rsi ; call FUN_00000abc
  ->
  31 c0 e9 26 00 00 00      xor eax,eax ; jmp 0xc85 (return EFI_SUCCESS)

Rebuilds the nested LZMA compressed volume in place (same size, 0xFF padded)
and fixes both CRC32 fields plus the FFS header/data checksums.
"""
import hashlib
import lzma
import struct
import sys
import zlib

SRC = "bios_region.bin"
OUT = "bios_region_patched.bin"

SEC_OFF = 0x20060           # compressed section start in bios_region.bin
SEC_SIZE = 0x1E38E1
SEC_HDR = 9
OUTER_FILE = 0x20048        # FFS file containing the compressed section
OUTER_SIZE = 0x1E38F9
VOL = 0x10                  # volume image start inside decompressed stream
INNER_FILE = VOL + 0x525520
INNER_SEC = INNER_FILE + 0x18
INNER_CRC1 = INNER_SEC + 0x18
INNER_DATA = INNER_SEC + 0x1C
PE = INNER_DATA + 4
PE_SIZE = 8576
PATCH_OFF = 0xC58
PATCH = bytes.fromhex("31c0e92600000090")


def u8sum(data):
    return (0x100 - (sum(data) & 0xFF)) & 0xFF


def fix_ffs(buf, start, size):
    body = buf[start + 0x18:start + size]
    hdr = bytearray(buf[start:start + 0x18])
    hdr[0x11] = u8sum(body)          # FFS data checksum
    tmp = bytearray(buf[start:start + 0x18])
    tmp[0x10] = 0                    # header checksum field
    tmp[0x11] = 0                    # file checksum field is zeroed too
    tmp[0x17] = 0                    # State is zeroed
    hdr[0x10] = u8sum(tmp)           # FFS header checksum
    buf[start:start + 0x18] = hdr


raw = bytearray(open(SRC, "rb").read())
assert len(raw) == 0x400000, len(raw)

body = bytes(raw[SEC_OFF + SEC_HDR:SEC_OFF + SEC_SIZE])
dec = bytearray(lzma.decompress(body, format=lzma.FORMAT_ALONE))
assert len(dec) == 0x780010, hex(len(dec))

# sanity: the inner module and its two CRC32 fields
orig_pe = open("LenovoWmaPolicyDxe.bin", "rb").read()
assert bytes(dec[PE:PE + PE_SIZE]) == orig_pe, "PE32 mismatch"
assert struct.unpack_from("<I", dec, INNER_CRC1)[0] == zlib.crc32(dec[INNER_DATA:INNER_SEC + 0x21DC]) & 0xFFFFFFFF

old = bytes(dec[PE + PATCH_OFF:PE + PATCH_OFF + len(PATCH)])
assert old == bytes.fromhex("488bcee85cfeffff"), old.hex()
dec[PE + PATCH_OFF:PE + PATCH_OFF + len(PATCH)] = PATCH

# inner CRC32 (GUIDed CRC32 section covers the PE32 section, header included)
struct.pack_into("<I", dec, INNER_CRC1, zlib.crc32(dec[INNER_DATA:INNER_SEC + 0x21DC]) & 0xFFFFFFFF)
fix_ffs(dec, INNER_FILE, 0x21F4)

# recompress with the same LZMA-alone parameters, pad to the original size
filters = [{
    "id": lzma.FILTER_LZMA1, "dict_size": 0x800000, "lc": 3, "lp": 0, "pb": 2,
    "mode": lzma.MODE_NORMAL, "nice_len": 273, "mf": lzma.MF_BT4, "depth": 0,
}]
comp = lzma.compress(bytes(dec), format=lzma.FORMAT_ALONE, filters=filters)
print("recompressed:", len(comp), "original:", len(body))
assert len(comp) <= len(body), "recompressed data does not fit"
assert comp[:5] == body[:5], "LZMA properties mismatch"
# liblzma writes an unknown-size header; keep the original 13-byte .lzma header
comp = body[:13] + comp[13:]
assert len(comp) <= len(body), "recompressed data does not fit"

# verify the new stream round-trips before touching the image
assert lzma.decompress(comp + b"\xff" * (len(body) - len(comp)), format=lzma.FORMAT_ALONE) == bytes(dec)

raw[SEC_OFF + SEC_HDR:SEC_OFF + SEC_SIZE] = comp + b"\xff" * (len(body) - len(comp))
fix_ffs(raw, OUTER_FILE, OUTER_SIZE)

open(OUT, "wb").write(raw)
print("wrote", OUT, "sha256:", hashlib.sha256(raw).hexdigest())
print("inner PE sha256:", hashlib.sha256(bytes(dec[PE:PE + PE_SIZE])).hexdigest())
print("patch bytes at PE+0x%x: %s" % (PATCH_OFF, bytes(dec[PE + PATCH_OFF:PE + PATCH_OFF + len(PATCH)]).hex()))

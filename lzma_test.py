#!/usr/bin/env python3
import lzma

DATA = open("bios_region.bin", "rb").read()
SEC_OFF = 0x20060
SEC_SIZE = 0x1E38E1
HDR = 9
BODY = DATA[SEC_OFF + HDR:SEC_OFF + SEC_SIZE]
print("compressed body size:", len(BODY), hex(len(BODY)))
print("lzma hdr:", BODY[:13].hex())

dec = lzma.decompress(BODY, format=lzma.FORMAT_ALONE)
print("decompressed size:", len(dec), hex(len(dec)))
print("first 32 bytes:", dec[:32].hex())
print("last 16 bytes:", dec[-16:].hex())

for preset in (6, 9):
    for mf in (lzma.MF_BT4, lzma.MF_BT3):
        filters = [{
            "id": lzma.FILTER_LZMA1,
            "dict_size": 0x800000,
            "lc": 3, "lp": 0, "pb": 2,
            "mode": lzma.MODE_NORMAL,
            "nice_len": 64 if preset == 6 else 273,
            "mf": mf,
            "depth": 0,
        }]
        try:
            enc = lzma.compress(dec, format=lzma.FORMAT_ALONE, filters=filters)
            print(f"preset={preset} mf={mf}: {len(enc)} ({len(enc)-len(BODY):+d}) identical={enc==BODY}")
        except Exception as e:
            print("err", preset, mf, e)

#!/usr/bin/env python3
"""Search UEFI extraction tree for whitelist-related strings (ASCII and UTF-16LE)."""
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "bios_region.bin.dump"

NEEDLES = [
    "1802",
    "Unauthorized",
    "unauthorized",
    "network card",
    "Network card",
    "whitelist",
    "Whitelist",
    "WLAN",
    "Wireless",
    "MiniPCI",
    "Mini PCI",
]

hits = {}
for dirpath, _dirnames, filenames in os.walk(ROOT):
    for name in filenames:
        path = os.path.join(dirpath, name)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        for needle in NEEDLES:
            for enc, blob in (("ascii", needle.encode()), ("utf16", needle.encode("utf-16le"))):
                pos = data.find(blob)
                if pos != -1:
                    hits.setdefault(path, []).append((needle, enc, pos))

for path in sorted(hits):
    print(path)
    for needle, enc, pos in hits[path]:
        print(f"    {needle!r} {enc} @0x{pos:x}")
print(f"\nfiles with hits: {len(hits)}")

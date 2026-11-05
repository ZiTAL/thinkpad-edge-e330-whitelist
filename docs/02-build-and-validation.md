# 02 — Image build and validation

## 1. Goal

Starting from the original BIOS region (`bios_region.bin`, 4 MB), produce a
patched region (`bios_region_patched.bin`) that:

1. contains the 8-byte patch in `LenovoWmaPolicyDxe.efi`;
2. keeps **exactly** the same sizes and UEFI structure;
3. has valid CRC32 and FFS checksums;
4. can be written to the flash without touching descriptor, ME or boot block.

## 2. Container chain

```
bios_region.bin (4 MB)
└─ FV 7A9354D9...
   └─ FFS 4A538818...                    offset 0x20048, size 0x1E38F9
      └─ Compressed section (LZMA)       offset 0x20060, size 0x1E38E1
         └─ (uncompressed 0x780010)
            └─ Volume image section      offset 0x0C, size 0x780004
               └─ Volume                  offset 0x10, size 0x780000
                  └─ FFS LenovoWmaPolicyDxe.efi
                                             offset 0x525530, size 0x21F4
                     └─ GUIDed CRC32 section
                                             offset 0x525548, size 0x21DC
                        └─ CRC32             offset 0x525560
                        └─ PE32 section      offset 0x525564, size 0x2184
                           └─ PE32+ image    offset 0x525568, size 0x2180
```

## 3. Patch offsets and bytes

| Item | Value |
|---|---|
| Patch offset in the PE | `0xC58` |
| Patch offset in the decompressed volume | `0x5261C0` (`0x525568 + 0xC58`) |
| Original bytes | `48 8b ce e8 5c fe ff ff` |
| Patched bytes | `31 c0 e9 26 00 00 00 90` |
| Meaning | `xor eax,eax; jmp 0xc85` (return 0) |

The relative jump is `0x26`: from the end of the `jmp` (`0xc5f`) to the
epilogue (`0xc85`) there are `0x26` bytes.

## 4. Checksums that must be rebuilt

### 4.1 GUIDed section CRC32

The GUIDed section (`FC1BCDB0-7D31-49AA-936A-A4600D9DD083`) uses CRC32. The CRC
is stored at `0x525560` and covers from the next byte (`0x525564`) to the end of
the section (`0x525548 + 0x21DC = 0x527724`), i.e. `0x21C0` bytes:

```python
crc = zlib.crc32(dec[0x525564:0x527724]) & 0xFFFFFFFF
struct.pack_into("<I", dec, 0x525560, crc)
```

Original value: `0x9724A531`. Patched value: `0x9C728A34`.

### 4.2 Inner FFS checksums

File `LenovoWmaPolicyDxe.efi`, offset `0x525530`, size `0x21F4`:

- **Data checksum** (byte at `header+0x11`):
  `(0x100 - sum(body)) & 0xFF`, with `body = file[0x18 : 0x21F4]`.
- **Header checksum** (byte at `header+0x10`):
  `(0x100 - sum(header_with_fields_zeroed)) & 0xFF`, where `Header` (`0x10`),
  `File` (`0x11`) and `State` (`0x17`) are zeroed.

Patched values: header `0xCB`, data `0x8B`.

### 4.3 Outer FFS checksums

File `4A538818-5AE0-4EB2-B2EB-488B23657022`, offset `0x20048`, size `0x1E38F9`.
They are recalculated the same way because the body contains the recompressed
LZMA section.

Patched values: header `0x65`, data `0xD6`.

### 4.4 PE checksum

The PE has `CheckSum = 0` and no security directory. It is not recalculated;
UEFI does not verify it.

## 5. LZMA recompression

The compressed section uses LZMA "alone" (13-byte header inside the body):

```
5d 00 00 80 00   props = 0x5D, dict = 0x00800000
10 00 78 00 00 00 00 00   uncompressed size = 0x780010
```

Recompressed with the same properties:

- Filter `LZMA1`, `dict_size = 0x800000`, `lc=3`, `lp=0`, `pb=2`
- `mode = NORMAL`, `nice_len = 273`, `mf = BT4`, `depth = 0`
- Original `.lzma` header preserved (liblzma writes unknown size)
- Result: **1,978,758 bytes** (original: 1,980,632)
- Padded with `0xFF` up to `0x1E38D8` so **no size changes**
- The EDK2 decoder reads `0x780010` bytes and ignores the padding

## 6. Scripts

### `patch_bios.py`

Builds `bios_region_patched.bin`. Steps:

1. Read `bios_region.bin`.
2. Extract the compressed body at `0x20069`, length `0x1E38D8`.
3. Decompress with `lzma.decompress(..., format=lzma.FORMAT_ALONE)`.
4. Verify that the PE32 at `0x525568` matches `LenovoWmaPolicyDxe.bin`.
5. Apply the 8 bytes at `0x5261C0`.
6. Recompute CRC32 and inner FFS checksums.
7. Recompress and pad to the original size.
8. Write the compressed body back at `0x20069`.
9. Recompute outer FFS checksums.
10. Save `bios_region_patched.bin`.

The script asserts the original bytes, the PE size and the CRC32; if run against
a different BIOS version it fails instead of producing a corrupt image.

### `verify_layout.py`

Validates the generated image against the original. It checks:

- sizes and SHA-256 of original and patched images;
- the original PE32 matches the extracted module;
- the patched PE32 differs only in the 8 patch bytes;
- the GUIDed section CRC32;
- inner and outer FFS checksums;
- the decompressed volume differs in exactly 3 ranges;
- `flash_image_12m.bin` carries the patched region at `0x800000`.

Current result: **PASS**.

### `lzma_test.py`

Exploratory script that decompresses and tries several LZMA presets to confirm
the recompressed data fits the original size. Kept as process evidence; not part
of the build.

### `search_strings.py`

Searches ASCII/UTF-16 strings in the UEFIExtract tree. Used to locate `1802`,
`Unauthorized`, `WLAN`, etc.

## 7. Building the 12 MB image

flashrom with `--ifd -i bios` requires a file the size of the whole chip
(12 MB), not just the region. Build it with:

```bash
cp orig_bios_region.bin flash_image_12m.bin
dd if=bios_region_patched.bin of=flash_image_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none
```

- `0x800000 = 8,388,608`
- Only the BIOS region matters; the rest stays as in `orig_bios_region.bin`
  (zeros).

## 8. Validation

### 8.1 Structural validation

`python3 verify_layout.py` → **PASS**. Full output in
`docs/evidence/verify_patched.txt`. Decompressed-volume diff:

```
0x525541-0x525541: 0x75 -> 0x8b          (inner FFS data checksum)
0x525560-0x525563: 31 a5 24 97 -> 34 8a 72 9c   (CRC32)
0x5261C0-0x5261C7: 48 8b ce e8 5c fe ff ff
                   -> 31 c0 e9 26 00 00 00 90   (patch)
```

No other byte differs across the 7,864,336 bytes of the volume.

### 8.2 UEFI re-parse

UEFIExtract re-parses the patched image. Module info:

```
Full size: 21F4h (8692)
Header checksum: CBh, valid
Data checksum: 8Bh, valid
```

GUIDed section info:

```
Checksum type: CRC32
Checksum: 9C728A34h, valid
```

Output in `docs/evidence/uefiextract.txt` and `docs/evidence/module_info.txt`.

### 8.3 Disassembly

`objdump` of the patched PE at `0xc58`:

```
c58: xor    eax,eax
c5a: jmp    0xc85
c5f: nop
c60: test   rax,rax
...
c85: lea    r11,[rsp+0x70]   ; epilogue
```

Output in `docs/evidence/objdump_patch.txt`.

### 8.4 flashrom check (no write)

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod -v flash_image_12m.bin
```

Expected result (the flash still holds the original firmware):

```
Verifying flash... FAILED at 0x00820059!
Expected=0xd6, Found=0x1f,
failed byte count from 0x00820000-0x00a03fff: 0x1e1a36
```

This confirms that:

- the layout and file size are correct;
- flashrom reads exactly the block that will be written;
- the differences are the expected ones (the whole compressed block, because
  LZMA changes the entire stream).

Output in `docs/evidence/flashrom_layout_verify.txt`.

## 9. Reproducing from scratch

```bash
# 1. Dump the BIOS region (read-only)
sudo flashrom -p internal --ifd -i bios -r orig_bios_region.bin

# 2. Extract the 4 MB region
dd if=orig_bios_region.bin of=bios_region.bin bs=1 skip=8388608 count=4194304

# 3. Extract the module with UEFIExtract (optional, for verification)
uefiextract bios_region.bin

# 4. Build the patched image
python3 patch_bios.py

# 5. Validate
python3 verify_layout.py

# 6. Build the 12 MB image
cp orig_bios_region.bin flash_image_12m.bin
dd if=bios_region_patched.bin of=flash_image_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none
```

Dependencies: Python 3.12 with `lzma` and `zlib` (stdlib). UEFIExtract is only
needed for UEFI inspection/validation.

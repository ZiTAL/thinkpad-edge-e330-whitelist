# 04 — Flashing risks

## 1. Scope of the write

With the recommended option (`biosmod.layout`):

```
0x00820000 - 0x00A03FFF   (~1.98 MB)
```

Left untouched:

- descriptor (`0x000000-0x000FFF`)
- ME (`0x001000-0x7FFFFF`)
- boot block (high end of the BIOS region, around `0xBE0000+`)
- EC

The boot block is **far** from the written block, so an interrupted write there
does not damage it. That is the main software safety net.

## 2. Risk matrix

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Power loss / hang / suspend during erase-write | Low with AC + battery and no interference | High: corrupt volume, possible no-POST | AC + battery, suspend disabled, do not touch the machine |
| `flashrom` fails midway (ME/SMM, write-protect, chip) | Low; FREG1 BIOS is read-write | High: partial write | Use the 2 MB layout; `-N`; do not rewrite the 4 MB region |
| BIOS rejects the patched module (CRC/checksum/signature) | Very low: CRC32 and FFS checksums validated; known H3ET72WW mods exist | Medium: no-POST or whitelist still active | Structural validation; boot block untouched |
| Side effect of the patch | Low | Low: card not initialized or setup shows odd data | The patch only changes the error branch; it does not touch the table |
| AX210 does not work due to hardware | Medium | None for the laptop; goal not achieved | Check adapter, power, MHF4 antennas, USB cable |
| Brick with no software recovery | Derived from the first failure | Very high: laptop out of service | CH341A + SOIC-8 clip before writing |

## 3. Detailed scenarios

### 3.1 Power loss or hang

This is the main risk. If it happens during erase or write, the block is
incomplete. The boot block remains intact, but the main volume may fail to load
and the machine may not reach POST.

Mitigation:

- laptop on AC and with battery;
- suspend disabled;
- no updates or heavy load;
- do not close the lid or disconnect anything;
- optionally boot a minimal live USB to reduce running processes.

### 3.2 flashrom or chipset failure

flashrom already reported:

```
FREG1: BIOS region (0x00800000-0x00bfffff) is read-write.
```

But the ME region is locked and the chipset uses hardware sequencing. `-N` is
required. If erase/write fails midway, flashrom may abort with a partially
written block.

Mitigation: use the 2 MB layout (not the 4 MB full region) and do not blindly
retry after an error; restore the original image first if the machine still
boots.

### 3.3 BIOS rejects the image

Validated:

- GUIDed section CRC32: `0x9C728A34`, valid;
- inner FFS checksums: `CB`/`8B`, valid;
- outer FFS checksums: `65`/`D6`, valid;
- the decompressed volume differs in exactly 3 ranges.

No full-region checksum or BIOS signature was found. Known `H3ET72WW` mods work,
which supports the conclusion that the boot block does not verify a signature of
the volume.

Residual risk: Phoenix's LZMA decoder could be stricter than Python/UEFIExtract.
The original `.lzma` header and uncompressed size were preserved; the stream is
standard LZMA1. The risk is low.

### 3.4 Side effects of the patch

The patch skips the error branch of `FUN_00000bd0`. On the "not found" path it
does not update `LenovoScratchData`. This is an auxiliary record; it should not
affect boot or PCIe initialization. The worst reasonable case is that the card
is not initialized or setup shows odd data; it is not a brick.

### 3.5 Card hardware

Independent of brick risk:

- the NFHK N-30U V4 adapter must be fully seated in the full-size WLAN slot;
- the AX210 needs MHF4 antennas;
- Bluetooth needs the adapter's USB cable;
- 6 GHz Wi-Fi 6E may perform poorly with 2012-era antennas; 2.4/5 GHz should
  work.

If any of this fails, the laptop still works; the goal is simply not achieved.

### 3.6 Recovery

- **If the machine still boots:** reflash the original region
  (`docs/03-flashing-and-recovery.md`, section 6).
- **If it does not boot but the boot block is intact:** Phoenix crisis recovery
  (Fn+B / Win+B, USB with `.FL1`, `PHLASH16` under DOS). Not guaranteed.
- **If the boot block or chip is damaged:** an SPI programmer is required.
  `orig_bios_region.bin` is not a full dump (descriptor/ME zero); dump the full
  chip with the programmer.

## 4. Overall assessment

- **Brick probability:** low under normal conditions (AC + battery, no
  interruption, 2 MB write). There is no official number; it depends on machine
  and chip stability.
- **Impact:** high, because without an SPI programmer recovery is not
  guaranteed.
- **Risk that the image is malformed:** very low; structurally validated with
  correct CRC/checksums.
- **Risk that the card does not work:** medium, but it does not affect the
  laptop's integrity.

## 5. Options

### A. Wait for the CH341A (recommended)

Buy a CH341A + SOIC-8 clip (5–10 €), dump the full chip before writing and keep
a backup. This turns a possible brick into a recoverable incident.

### B. Flash over software with the layout

Accept the residual risk. Use the 2 MB command, on AC and battery, without
interruptions. If it fails and the machine does not boot, try crisis recovery.

### C. Do not flash

Use a card that is already in the table, for example the **Intel Centrino
Wireless-N 2230** (`8086:0888`), which works without modifying the BIOS. This is
the safest option if the goal is simply better WiFi than the BCM43228.

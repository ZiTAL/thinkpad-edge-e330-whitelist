# 06 — Flash log

## Summary

- **Date:** 2026-11-05, 16:07 local time
- **Action:** wrote the modified 2 MB block (not the full BIOS region)
- **Result:** `Erase/write done.` and `Verifying flash... VERIFIED.`
- **Independent readback:** full BIOS region matches `bios_region_patched.bin`
  byte for byte (0 differing bytes)
- **Power state at write time:** charger offline (`ADP1 online=0`), battery
  `BAT0` discharging at **76%**
- **Reboot:** not performed by the automation; boot/card test is pending

## Command

```bash
sudo systemd-inhibit --what=idle:sleep --why="ThinkPad E330 BIOS whitelist patch" \
  flashrom -p internal -l biosmod.layout -i biosmod -w flash_image_12m.bin -N
```

`biosmod.layout`:

```
00820000:00a03fff biosmod
```

## Output (abridged)

```text
Using region: "biosmod".
Found chipset "Intel HM77".
FREG0: Flash Descriptor region (0x00000000-0x00000fff) is read-only.
FREG1: BIOS region (0x00800000-0x00bfffff) is read-write.
FREG2: Management Engine region (0x00001000-0x007fffff) is locked.
...
Reading old flash chip contents... done.
Erasing and writing flash chip... Erase/write done.
Verifying flash... VERIFIED.
```

Full log: `docs/evidence/flash_write.txt`.

## Independent readback

Read the full BIOS region with the Intel descriptor layout:

```bash
sudo flashrom -p internal --ifd -i bios -r /tmp/opencode/readback_bios.bin
```

Comparison against the patched region:

```text
full BIOS region matches patched: True
diff bytes: 0
```

Full log and comparison: `docs/evidence/flash_readback.txt`.

## Recovery image

Before writing, the original region was prepared for an immediate rollback:

```bash
cp orig_bios_region.bin flash_image_original_12m.bin
dd if=bios_region.bin of=flash_image_original_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none
```

If a rollback is needed and the machine still boots:

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod \
  -w flash_image_original_12m.bin -N
```

`flash_image_original_12m.bin` is local only (it is a firmware image and is
excluded from the public repository).

## Pending

1. Install the AX210 in the full-size WLAN slot.
2. Connect the adapter's USB cable for Bluetooth.
3. Reboot and check `lspci` (`8086:2725`), `lsusb` (`8087:0032`) and `dmesg`.
4. Confirm the 1802 no longer appears.
5. Update this log with the boot/card result.

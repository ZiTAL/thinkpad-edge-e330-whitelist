# 06 — Flash log

## Summary

- **Date:** 2026-11-05, 16:07 local time
- **Action:** wrote the modified 2 MB block (not the full BIOS region)
- **Result:** `Erase/write done.` and `Verifying flash... VERIFIED.`
- **Independent readback:** full BIOS region matches `bios_region_patched.bin`
  byte for byte (0 differing bytes)
- **Power state at write time:** charger offline (`ADP1 online=0`), battery
  `BAT0` discharging at **76%**
- **Reboot:** performed at **16:11** (after the write); machine booted normally
- **Patch still in place after reboot:** `flashrom -v` re-verified the patched
  block against `flash_image_12m.bin` → `Verifying flash... VERIFIED.`
- **Card test:** passed on **2026-11-06** — the AX210 is detected as Wi-Fi
  (`8086:2725`) and Bluetooth (`8087:0032`), Wi-Fi connects and no 1802 appears

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

## Post-reboot check (2026-11-05, 16:11 boot)

The machine was rebooted after the write and came up normally. Full capture:
[`evidence/post_reboot_check.txt`](evidence/post_reboot_check.txt).

| Check | Observed |
| --- | --- |
| Boot | OK, kernel `6.17.0-42-generic`, BIOS `H3ET72WW(1.09)` |
| Patch persisted | `flashrom -v` on the `biosmod` range → `VERIFIED` |
| Boot errors (`journalctl -b -p err`) | none |
| 1802 / "unauthorized network card" | not present in this boot |
| WLAN PCIe | `02:00.0` **Broadcom BCM43228** `[14e4:4359]` (`wl` driver) |
| WLAN USB | `0a5c:21f3` **Broadcom BCM20702A0** (BT of the original combo) |
| `8086:2725` (AX210 Wi-Fi) in `lspci` | **not present** |
| `8087:0032` (AX210 BT) in `lsusb` | **not present** |
| `iwlwifi` loaded / firmware errors | not loaded, no errors (card absent) |
| Interfaces | `wlp2s0` up (Broadcom), `enp8s0`, `lo`, `tun0` |

**Interpretation.** The firmware patch is confirmed live: the laptop boots
cleanly from the modified block and the block re-verifies after reboot. At the
time of this check (2026-11-05) the wireless module in the slot was still the
**original Broadcom BCM43228 combo card**, so that boot did not test the
whitelist bypass — a stock, authorized card produces no 1802 either way. The
AX210 was installed the next day; see the card test below.

## Card test (2026-11-06, 09:32 boot)

The AX210HMW was installed in the full-size WLAN slot (with the adapter's USB
cable for Bluetooth) and the machine was booted on the patched firmware. Full
capture: [`evidence/ax210_card_test.txt`](evidence/ax210_card_test.txt).

| Check | Observed |
| --- | --- |
| Boot | OK, kernel `6.17.0-42-generic`, BIOS `H3ET72WW(1.09)` |
| Patch persisted | `flashrom -v` on the `biosmod` range → `VERIFIED` |
| WLAN PCIe | `02:00.0` **Intel Wi-Fi 6E AX210** `[8086:2725]` (rev 1a) |
| WLAN USB / Bluetooth | `8087:0032` **Intel Corp. AX210 Bluetooth** |
| `iwlwifi` | loaded, `Detected Intel(R) Wi-Fi 6E AX210 160MHz`, firmware `89.123cf747.0` |
| `iwlwifi` errors | none |
| 1802 / "unauthorized network card" | **not present** |
| Interface | `wlp2s0` **UP**, associated (`connected`) with an access point |
| Bluetooth | `hci0` **UP RUNNING**, HCI 5.3, manufacturer Intel |

**Result: the whitelist bypass works.** The previously unauthorized AX210 is
accepted by the patched firmware, both halves of the card (PCIe Wi-Fi and USB
Bluetooth) enumerate and work, and the machine shows no 1802 error. The
original Broadcom BCM43228 is no longer present.

## Checklist

1. ~~Install the AX210 in the full-size WLAN slot.~~ Done on 2026-11-06.
2. ~~Connect the adapter's USB cable for Bluetooth.~~ Done; `8087:0032` enumerates.
3. ~~Reboot and check `lspci`, `lsusb` and `dmesg`.~~ Done; see the table above.
4. ~~Confirm the 1802 no longer appears.~~ Confirmed absent.
5. ~~Record the card test result in this log.~~ This section.

Remaining optional task: keep a copy of `flash_image_original_12m.bin` for
rollback, and re-run `flashrom -v` after any future BIOS/EC update.


# 03 — Flashing, verification and recovery

## 0. Status

**The modified block was written and verified on 2026-11-05.** The exact
command, power state and readback are in [`06-flash-log.md`](06-flash-log.md).
The machine was rebooted at 16:11 and boots normally from the patched block; a
post-reboot `flashrom -v` re-verifies it (`VERIFIED`). The AX210 was then
installed and tested on 2026-11-06: it is detected, `iwlwifi` loads, Wi-Fi
connects, Bluetooth is up and **no 1802 appears** — see
[`06-flash-log.md`](06-flash-log.md#card-test-2026-11-06-0932-boot). This
document is kept as the procedure reference and for re-flashing/rollback.

## 1. Before you start

- Connect the **charger** and keep the **battery installed and charged**. The
  laptop acts as a UPS if mains power is lost.
- Close browsers, updates and any heavy process.
- Disable automatic suspend.
- Do not touch the machine, close the lid or disconnect anything during the
  process.
- Have `bios_region.bin` and `flash_image_12m.bin` available.
- Ideally, have a **CH341A + SOIC-8 clip** and a full chip dump before writing.

Estimated write time: **1–2 minutes** (erase + write + verify of ~2 MB).

## 2. What gets written

The recommended option writes only this block:

```
0x00820000 - 0x00A03FFF   (~1.98 MB)
```

It contains the compressed volume with `LenovoWmaPolicyDxe`. It does **not**
touch:

- descriptor (`0x000000-0x000FFF`)
- ME region (`0x001000-0x7FFFFF`)
- boot block (high end of the BIOS region, around `0xBE0000+`)
- EC

The alternative option rewrites the full 4 MB BIOS region. It has more failure
surface and adds nothing here.

## 3. Recommended command (modified block only)

```bash
cd /home/projects/thinkpad-edge-firmware
sudo flashrom -p internal -l biosmod.layout -i biosmod -w flash_image_12m.bin -N
```

`biosmod.layout`:

```
00820000:00a03fff biosmod
```

### Why this form

- `-l biosmod.layout -i biosmod`: use a custom layout and write only that range.
- `-w flash_image_12m.bin`: 12 MB image; flashrom takes the included range from
  the file.
- `-N` (`--noverify-all`): required with a locked ME region; it skips verifying
  regions that are not included. The included region is still verified.

### What you should see

```
Found chipset "Intel HM77".
...
Using region: "biosmod".
Erasing and writing flash chip... Erase/write done.
Verifying flash... VERIFIED.
```

If it says `VERIFIED`, the write and verification succeeded.

## 4. Alternative (full BIOS region)

```bash
sudo flashrom -p internal --ifd -i bios -w flash_image_12m.bin -N
```

This rewrites the whole 4 MB BIOS region (including the boot block). It is the
classic option but riskier if interrupted.

## 5. After flashing

1. Power off (`sudo poweroff`); do not warm-reboot.
2. Power on and enter the BIOS if you want to confirm the 1802 is gone.
3. Boot Linux and check:

```bash
# AX210 WiFi
lspci -nn | grep -i 8086:2725
dmesg | grep -i iwlwifi

# AX210 Bluetooth
lsusb | grep -i 8087:0032
dmesg | grep -i bluetooth
```

Expected:

- `02:00.0 Network controller: Intel ... Wi-Fi 6E AX210 [8086:2725]`
- `Bus ... ID 8087:0032 Intel Corp. AX210 Bluetooth`
- No `1802` at POST.

If WiFi appears but Bluetooth does not:

- check the adapter's USB cable is connected to a USB port;
- check the adapter is fully seated in the slot;
- check that `btusb`/`btintel` is loaded (kernel 5.8+).

If WiFi does not appear:

- confirm the adapter is in the **full-size WLAN slot**, not the half-size
  WWAN/mSATA slot;
- check the MHF4 antennas;
- check `dmesg` for PCIe/enumeration errors.

## 6. Rollback (if the machine still boots)

Build a 12 MB image with the original region:

```bash
cd /home/projects/thinkpad-edge-firmware
cp orig_bios_region.bin flash_image_original_12m.bin
dd if=bios_region.bin of=flash_image_original_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none
```

Then write it the same way:

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod \
  -w flash_image_original_12m.bin -N
```

or, for the full region:

```bash
sudo flashrom -p internal --ifd -i bios \
  -w flash_image_original_12m.bin -N
```

`flash_image_original_12m.bin` is not included in the repository; generate it
with the two commands above.

## 7. Recovery if it does not boot

### 7.1 Phoenix crisis recovery (software)

The boot block is not touched by the recommended option. If the main volume is
corrupt, the boot block may still recover from USB.

Documented Phoenix/ThinkPad methods:

- hold **Fn+B** (or **Win+B**) while connecting power;
- USB prepared with the official BIOS (`.FL1` / `.WPH`) and, depending on the
  method, `PHLASH16.EXE` + `MINIDOS.SYS` under DOS;
- the official E330 package is `h3uj54ww.exe` (Lenovo), which contains the
  firmware and flasher; an older package is `h3uj05ww.exe`.

Notes:

- Not guaranteed on the E330; it depends on the boot block and the media.
- Do not remove the battery before attempting recovery (Lenovo's flasher checks
  power).
- The exact filename and key combo may vary; check the E330 bios-mods thread and
  the Phoenix crisis recovery documentation.

### 7.2 SPI programmer (hardware)

This is the reliable recovery:

1. Open the bottom cover and locate the SPI chip (SOIC-8).
2. With a **CH341A** + SOIC-8 clip, dump the full chip (12 MB) **before**
   writing.
3. Keep that dump as a backup.
4. If the machine does not boot, write the full dump back.
5. Alternatively, build a full image with the descriptor/ME from the dump and
   the original or patched BIOS region.

Important: `orig_bios_region.bin` **is not** a full dump (descriptor and ME are
zero). For the programmer, use a full chip dump.

## 8. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `flashrom` says `BIOS region is write-protected` | ME/SMM or descriptor | Use layout/`-N`; if it persists, use a programmer |
| `Verifying flash... FAILED` after writing | Incomplete write or chip issue | Retry once; if it fails, restore the original |
| Machine does not boot | Corrupt volume | Crisis recovery / programmer |
| 1802 still appears | Patch not applied, wrong region, or BIOS updated afterwards | Verify `bios_region_patched.bin` and reflash |
| WiFi appears, BT does not | Adapter USB cable, antennas, driver | Check the USB cable and `dmesg` |
| WiFi does not appear | Adapter not seated, wrong slot, antennas | Check hardware and `lspci` |

## 9. Pre-write check already performed

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod -v flash_image_12m.bin
```

Expected output (fails only on the patched bytes because the flash is not
written yet): see `docs/evidence/flashrom_layout_verify.txt`.

The probe was also checked:

```bash
sudo flashrom -p internal
```

`FREG1: BIOS region (0x00800000-0x00bfffff) is read-write` — the BIOS region is
software-writable according to the descriptor.

# ThinkPad Edge E330 — WiFi/WWAN whitelist removal

**Status: firmware written and verified on 2026-11-05. Boot/card test pending.**
The flash now contains the patched BIOS region; the running OS still uses the
old code in RAM until the next reboot.

---

## Summary

- Machine: **Lenovo ThinkPad Edge E330**, machine type **3354DVG**
- BIOS: **H3ET72WW (1.09)**, 2013-02-25, Phoenix SecureCore Tiano
- Chipset: Intel HM77 (Ivy Bridge), 12 MB SPI flash
- Factory WiFi: Broadcom **BCM43228** (`14e4:4359`, subsystem `14e4:0607`)
- Factory Bluetooth: Broadcom **BCM20702A0** (`0a5c:21f3`)
- Target card: **Intel AX210HMW** (Wi-Fi 6E, BT 5.3) on an **NFHK N-30U V4**
  M.2-to-mini-PCIe adapter
- Removed message: `1802: Unauthorized network card is plugged in`
- Patched module: `LenovoWmaPolicyDxe.efi`
  (FFS `79E0EDD7-9D1D-4F41-AE1A-F896169E5216`)
- Patch: 8 bytes at PE offset `0xc58`; the "unauthorized card" branch returns
  `EFI_SUCCESS` instead of reporting 1802.

## Documentation

| Document | Content |
|---|---|
| [`docs/01-firmware-analysis.md`](docs/01-firmware-analysis.md) | Machine, dump, UEFI layout, module, ID table, `0xbd0` logic, patch rationale |
| [`docs/02-build-and-validation.md`](docs/02-build-and-validation.md) | LZMA layout, exact offsets, CRC/checksums, scripts, validation results |
| [`docs/03-flashing-and-recovery.md`](docs/03-flashing-and-recovery.md) | Write commands, post-flash checks, rollback, crisis recovery, SPI programmer |
| [`docs/04-risks.md`](docs/04-risks.md) | Risk matrix, probability/impact, mitigations and recommendation |
| [`docs/05-inventory-and-environment.md`](docs/05-inventory-and-environment.md) | File inventory and hashes, tools, versions, environment, commands used |
| [`docs/06-flash-log.md`](docs/06-flash-log.md) | What was written, when, power state, verification and readback |
| [`docs/evidence/README.md`](docs/evidence/README.md) | Evidence logs and raw validation output |
| [`docs/es/README.md`](docs/es/README.md) | Original Spanish documentation (historical) |

## Local artifacts (not published)

The public repository **does not include the firmware dumps**. They contain
machine-specific data (Windows OEM key, serial number, MAC addresses), so they
stay local and are regenerated with the documented commands.

| File | Content | SHA-256 |
|---|---|---|
| `bios_region.bin` | Original BIOS region (4 MB, `0x800000..0xBFFFFF`) | `8e3719c61c651a7bc78868b5cca90191e685e38407badf00f48a5a53d471f43d` |
| `bios_region_patched.bin` | Patched BIOS region (4 MB) | `a5bdf564340cc7805c23621464d9f8f39ca856371a1d89e8aa2871877a8003c2` |
| `flash_image_12m.bin` | 12 MB image for `flashrom` (only the BIOS region is meaningful) | `e4b4a6537a130ab04fad87c494b8e1078173dcc7947a6f987b1b1604b19664c3` |
| `orig_bios_region.bin` | flashrom 12 MB dump (BIOS region read; rest zero) | `356096115bcb09db373805da3f15a60121d4f2abb52faade6e5af1d8a9227c94` |
| `LenovoWmaPolicyDxe.bin` | Original module | `2ccf44433c5fe63cb0ac2abe83344af865017aa34946eabe4c8024ae2431ebff` |

Scripts: `patch_bios.py` (builds the patched image), `verify_layout.py`
(validates everything), `lzma_test.py` (LZMA recompression probe),
`search_strings.py` (UEFI string search).

## Next step

The write **was performed and verified on 2026-11-05**. The exact command and
output are in [`docs/06-flash-log.md`](docs/06-flash-log.md). The independent
full BIOS-region readback matches `bios_region_patched.bin` byte for byte.

The next step is to install the AX210 in the full-size WLAN slot, reconnect the
adapter's USB cable for Bluetooth, reboot, and check:

```bash
lspci -nn | grep -i 8086:2725
lsusb | grep -i 8087:0032
dmesg | grep -iE 'iwlwifi|bluetooth'
```

The command used, for reference:

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod -w flash_image_12m.bin -N
```

If anything goes wrong, see [`docs/03-flashing-and-recovery.md`](docs/03-flashing-and-recovery.md)
and [`docs/04-risks.md`](docs/04-risks.md).

## Scope of the patch

The patch **does not add a specific card**: it removes the check for any
PCIe WLAN/WWAN card. Bluetooth over USB is not validated on this model (type 2
returns success when the device is absent from the table), so the BT half of a
combo card needs no patch.

## Disclaimer

This is a personal hardware modification for a machine you own. It is not
affiliated with or endorsed by Lenovo or Intel. Flashing modified firmware can
brick the machine. Use at your own risk; see [`DISCLAIMER.md`](DISCLAIMER.md).

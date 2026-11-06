# 05 — Inventory, environment and reproduction

## 1. File inventory

### 1.1 Images and modules (local only — not in the public repo)

These files contain machine-specific data (Windows OEM key, serial number, MAC
addresses) and are intentionally excluded from the public repository. They are
regenerated with the commands in `docs/02-build-and-validation.md`.

| File | Size | SHA-256 | Role |
|---|---:|---|---|
| `bios_region.bin` | 4 MB | `8e3719c61c651a7bc78868b5cca90191e685e38407badf00f48a5a53d471f43d` | Original BIOS region extracted from the dump |
| `bios_region_patched.bin` | 4 MB | `a5bdf564340cc7805c23621464d9f8f39ca856371a1d89e8aa2871877a8003c2` | Patched BIOS region |
| `flash_image_12m.bin` | 12 MB | `e4b4a6537a130ab04fad87c494b8e1078173dcc7947a6f987b1b1604b19664c3` | Image for `flashrom` (patched BIOS region at `0x800000`) |
| `orig_bios_region.bin` | 12 MB | `356096115bcb09db373805da3f15a60121d4f2abb52faade6e5af1d8a9227c94` | flashrom dump (BIOS region only; rest zero) |
| `LenovoWmaPolicyDxe.bin` | 8576 B | `2ccf44433c5fe63cb0ac2abe83344af865017aa34946eabe4c8024ae2431ebff` | Original PE32+ module |
| `LenovoWmaPciDxe.bin` | 3168 B | `8f273718e25255b33c730ace91965267d54bd88801f29a8832154e451b28b82c` | Auxiliary PCI driver |
| `LenovoWmaUsbDxe.bin` | 3616 B | `3b40d75cad4a0d5bdab9767a5f1f1ebeabcf3b239f374a7bb48e9675d6a81f33` | Auxiliary USB driver |

### 1.2 Scripts and layout (included in the public repo)

| File | Size | SHA-256 | Role |
|---|---:|---|---|
| `patch_bios.py` | 3833 B | `f1930f5f64ec76a1c3963e9e793f0500700b37208a410fc73772f4e2e98afd0e` | Builds the patched region |
| `verify_layout.py` | 4604 B | `9eb2e785e017c804c10d3e8010c0af13a124cded72702315df3cabdf58678fee` | Validates the full image |
| `lzma_test.py` | 1070 B | `be9249652a215a5100a959e72501b332c20146303836928b73085741828a4c6a` | LZMA recompression probe |
| `search_strings.py` | 1107 B | `af4e2404c38eb23b441acd81a54a03a6a94d4fc435a22d39c9e06b7f25ba1f7a` | UEFI string search |
| `biosmod.layout` | 26 B | `a4d8932b7ac3573ca0f7332a8acecb46f442dc24331d1edca0576945db55ebae` | 2 MB write layout |
| `wma_disasm.txt` | 69 KB | `96ffbe1104f8cb04cfa64755742929364cf3fa0ee7885a2d4e501f0e2199ce29` | Full module disassembly |

### 1.3 Analysis artifacts

| Path | Content | In public repo? |
|---|---|---|
| `bios_region.bin.dump/` | UEFI tree extracted from the original | No (regenerate) |
| `bios_region_patched.bin.dump/` | UEFI tree extracted from the patched image | No (regenerate) |
| `bios_region.bin.report.txt` | UEFIExtract report (original) | No (contains firmware strings) |
| `bios_region_patched.bin.report.txt` | UEFIExtract report (patched) | No (contains firmware strings) |
| `bios_region.bin.guids.csv` | GUID database (original) | No |
| `bios_region_patched.bin.guids.csv` | GUID database (patched) | No |
| `wma_0xbd0.json` | Failed REA decompile attempt (Ghidra did not create `0xbd0`) | Yes |
| `wma_procs.json` | Procedure list detected by Ghidra | Yes |
| `model.jpg` | Photo of the AX210HMW label (EXIF stripped) | Yes |
| `docs/evidence/` | Validation and environment logs | Yes (except `patched_pe.bin`) |

## 2. Tools and versions

| Tool | Version / path | Use |
|---|---|---|
| Linux Mint | 22.3 (Zena), kernel 6.17.0-42-generic | Environment |
| Python | 3.12.3 | Patching/validation scripts |
| flashrom | 1.3.0-2.1ubuntu2 | Dump, probe and write |
| UEFIExtract | NE alpha 76 (A76); temporary path `/tmp/opencode/uefi/uefiextract` (download: `https://github.com/LongSoft/UEFITool/releases/tag/A76`) | UEFI parsing |
| Java | OpenJDK 21.0.12.1 | Ghidra |
| Ghidra | 12.1.4, `/opt/ghidra` | Native analysis (REA) |
| REA | 6.8.0 (`npx -y rea-agents@6.8.0`) | Analysis MCP/CLI |
| binutils | system `objdump` | Disassembly |

## 3. REA environment

- The REA MCP is registered in `~/.config/opencode/opencode.json`:

```json
{
  "type": "local",
  "command": ["npx", "-y", "rea-agents@6.8.0", "mcp"],
  "disabled": false
}
```

- Ghidra was installed at `/opt/ghidra` and validated with:

```bash
GHIDRA_INSTALL_DIR=/opt/ghidra npx -y rea-agents@6.8.0 doctor --client opencode --json
```

Summary (`docs/evidence/rea_doctor_summary.txt`):

```
healthy=True environment_healthy=True
cli=6.8.0 skill=aligned
ghidra                     ok=True  healthy /opt/ghidra
ghidra-version             ok=True  healthy 12.1.4
ghidra-headless            ok=True  healthy /opt/ghidra/support/analyzeHeadless
ghidra-native_decompiler   ok=True  healthy .../decompile reports elf x86_64
ghidra-java                ok=True  healthy 21.0.12.1; 64-bit; JDK
```

Note: the MCP was launched without `GHIDRA_INSTALL_DIR`; the CLI was used with
the variable exported. To make the MCP use Ghidra in future sessions, add
`GHIDRA_INSTALL_DIR=/opt/ghidra` to the REA server environment or restart the
client with that variable.

## 4. Commands used (chronological)

```bash
# Identification
cat /sys/class/dmi/id/*
lspci -nn
lsusb

# BIOS region dump (read-only)
sudo flashrom -p internal --ifd -i bios -r orig_bios_region.bin
dd if=orig_bios_region.bin of=bios_region.bin bs=1 skip=8388608 count=4194304

# UEFI parsing
/tmp/opencode/uefi/uefiextract bios_region.bin

# String search
python3 search_strings.py bios_region.bin.dump

# Module extraction
# (path .../289 LenovoWmaPolicyDxe.efi/0 FC1BCDB0.../0 PE32 image section/body.bin)

# Disassembly
objdump -d -M intel --no-show-raw-insn LenovoWmaPolicyDxe.bin > wma_disasm.txt
objdump -d -M intel --no-show-raw-insn \
  --start-address=0xbd0 --stop-address=0xd20 LenovoWmaPolicyDxe.bin

# Build and validate
python3 patch_bios.py
python3 verify_layout.py

# 12 MB image
cp orig_bios_region.bin flash_image_12m.bin
dd if=bios_region_patched.bin of=flash_image_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none

# Pre-write checks
sudo flashrom -p internal
sudo flashrom -p internal -l biosmod.layout -i biosmod -v flash_image_12m.bin

# Rollback image
cp orig_bios_region.bin flash_image_original_12m.bin
dd if=bios_region.bin of=flash_image_original_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none

# Write (2026-11-05)
sudo systemd-inhibit --what=idle:sleep \
  --why="ThinkPad E330 BIOS whitelist patch" \
  flashrom -p internal -l biosmod.layout -i biosmod \
  -w flash_image_12m.bin -N

# Independent full-region readback
sudo flashrom -p internal --ifd -i bios -r /tmp/opencode/readback_bios.bin
# → full BIOS region matches patched: True / diff bytes: 0

# Post-reboot and AX210 card test (2026-11-06)
lspci -nn | grep -i network
lsusb
dmesg | grep -iE 'iwlwifi|1802|unauthorized|ax210|2725'
rfkill list
ip -br addr show wlp2s0
hciconfig -a
sudo flashrom -p internal -l biosmod.layout -i biosmod -v flash_image_12m.bin -N

# REA / Ghidra
GHIDRA_INSTALL_DIR=/opt/ghidra npx -y rea-agents@6.8.0 doctor --client opencode --json
```

## 5. Limitations and notes

- `orig_bios_region.bin` **is not a full dump**: descriptor and ME are zero
  because flashrom only read the BIOS region. For an SPI programmer, dump the
  full chip.
- `bios_region.bin.dump/` and `bios_region_patched.bin.dump/` are reproducible
  with UEFIExtract; they can be deleted if not needed.
- `wma_0xbd0.json` is a failed decompile attempt: Ghidra did not recognize
  `0xbd0` as a function (no direct xrefs). The analysis was completed with
  `objdump` and the table logic; `wma_procs.json` documents what Ghidra did
  detect.
- The module PE checksum is 0 and there is no security directory; it is not
  recalculated.
- The patch does not touch the table or Bluetooth; only the error branch.
- The modified block **was written and verified on 2026-11-05**, and the AX210
  card test **passed on 2026-11-06** (Wi-Fi + Bluetooth working, no 1802); see
  `docs/06-flash-log.md`.
- The public repository excludes the firmware dumps because they contain the
  Windows OEM key, the serial number and the MAC addresses.

## 6. Task history

1. ~~Decide whether to flash over software or wait for an SPI programmer.~~
   Done: software write on 2026-11-05.
2. ~~Write the patched block and verify it.~~ Done: `Erase/write done` +
   `Verifying flash... VERIFIED.` and a full-region readback with 0 differences.
3. ~~Install the AX210 in the full-size WLAN slot, with MHF4 antennas and the
   adapter's USB cable.~~ Done on 2026-11-06.
4. ~~Reboot and verify `lspci` (`8086:2725`), `lsusb` (`8087:0032`) and the
   absence of 1802.~~ Done: both halves detected, Wi-Fi connected, no 1802.
5. ~~Update `docs/06-flash-log.md` with the boot/card result.~~ Done; see the
   card test section.
6. To roll back: reflash `bios_region.bin` (see doc 03).

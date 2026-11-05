# 01 — Firmware analysis

## 1. Machine and firmware

DMI and system data collected during the analysis:

```
sys_vendor      LENOVO
product_name    3354DVG
product_version ThinkPad Edge E330
board_name      3354DVG
board_version   0B98401 Pro
bios_vendor     LENOVO
bios_version    H3ET72WW(1.09)
bios_date       02/25/2013
chassis_type    10 (Notebook)
```

- Chipset: **Intel HM77** (Ivy Bridge, 3rd-gen Core)
- SPI flash: 12 MB; flashrom reports an `Opaque flash chip` via hardware
  sequencing (multiple chips behind the descriptor)
- Factory WiFi: **Broadcom BCM43228** `14e4:4359`, subsystem `14e4:0607`
- Factory Bluetooth: **Broadcom BCM20702A0** `0a5c:21f3`, internal USB
- Ethernet: Realtek RTL8111/8168
- Card reader: Realtek RTS5209

## 2. BIOS region dump

The Intel descriptor splits the 12 MB flash as follows:

| Region | Range | Observed access |
|---|---|---|
| Descriptor | `0x000000-0x000FFF` | read-only |
| ME | `0x001000-0x7FFFFF` | locked |
| BIOS | `0x800000-0xBFFFFF` | read/write |

Read-only dump command:

```bash
sudo flashrom -p internal --ifd -i bios -r orig_bios_region.bin
```

flashrom writes a file the size of the whole chip (12 MB): the BIOS region is
read and the rest is zero-filled. Therefore `orig_bios_region.bin` **is not a
full dump** and cannot restore descriptor/ME with an SPI programmer. The actual
BIOS region was extracted to `bios_region.bin`:

```bash
dd if=orig_bios_region.bin of=bios_region.bin bs=1 skip=8388608 count=4194304
```

- `bios_region.bin`: 4 MB, SHA-256
  `8e3719c61c651a7bc78868b5cca90191e685e38407badf00f48a5a53d471f43d`

## 3. UEFI layout

The BIOS region was parsed with UEFIExtract (NE alpha 76):

```bash
/tmp/opencode/uefi/uefiextract bios_region.bin
```

The temporary path above is where the tool was available; the binary can be
obtained from `https://github.com/LongSoft/UEFITool/releases/tag/A76`
(`UEFIExtract_NE_A76_x64_linux.zip`).

Relevant hierarchy:

```
BIOS region (4 MB)
├─ FV 7A9354D9-0468-444A-81CE-0BF617D890DF   (starts at 0x1FF40)
│  └─ FFS 4A538818-5AE0-4EB2-B2EB-488B23657022   (0x20048, size 0x1E38F9)
│     └─ Compressed section (LZMA, 0x20060, uncompressed 0x780010)
│        └─ Volume image section (0x780004)
│           └─ Volume (0x780000)
│              └─ ... 289 LenovoWmaPolicyDxe.efi ...
```

### 3.1 Compressed section

At `0x20060` in `bios_region.bin`:

```
e1 38 1e 01   size 0x1E38E1, type 0x01 (compression)
10 00 78 00   uncompressed length 0x780010
02            compression type (LZMA)
5d 00 00 80 00 10 00 78 00 00 00 00 00
              .lzma header: props 0x5D, dictionary 0x800000,
              size 0x780010
```

- Compressed body: `0x1E38D8` bytes (1,980,632)
- Uncompressed content: `0x780010` bytes (7,864,336)

### 3.2 Inner file and section

Inside the decompressed volume:

| Element | Decompressed offset | Detail |
|---|---|---|
| Volume start | `0x10` | FV header of `0x780000` |
| FFS `LenovoWmaPolicyDxe.efi` | `0x525530` | GUID `79E0EDD7-9D1D-4F41-AE1A-F896169E5216`, size `0x21F4` |
| GUIDed CRC32 section | `0x525548` | GUID `FC1BCDB0-7D31-49AA-936A-A4600D9DD083`, size `0x21DC` |
| CRC32 | `0x525560` | covers `0x525564` to the end of the section |
| PE32 section header | `0x525564` | size `0x2184`, type `0x10` |
| PE32+ image | `0x525568` | 8576 bytes (`0x2180`) |

The PE32+ module has:

- Entry point: `0x10d8`
- `.text`: VMA `0x240`, size `0x1E30`
- Data section: VMA `0x2080`, size `0xD8`
- No security/certificate directory
- PE checksum: `0`

## 4. Locating the whitelist

The error string is stored as UTF-16LE inside the module:

```
1802: Unauthorized network card is plugged in - Power off and remove the miniPCI network card (%s).
```

There are also `%04x/%04x/%04x/%04x` and `%04x/%04x` format strings, plus the
variable names `LenovoScratchData` and `LenovoConfig`.

Only `LenovoWmaPolicyDxe.efi` contains the `1802` string. `LenovoWmaPciDxe.efi`
and `LenovoWmaUsbDxe.efi` are device-path drivers that invoke the policy.
`LenovoSetupSecurityDxe.efi` contains generic setup text ("Wireless LAN",
"unauthorized") but not the 1802 check.

## 5. Card validation function

### 5.1 ID table

At PE offset `0x270` there is a table of 16-byte entries:

```
u32 type; u16 vendor; u16 device; u16 subvendor; u16 subdevice; u32 reserved?
```

It ends with `type == 6`. Original contents:

| # | type | vendor:device | subvendor:subdevice | Meaning |
|---|---|---|---|---|
| 0 | 0 | `10ec:8176` | `10ec:8195` | Realtek RTL8188CE |
| 1 | 0 | `8086:0888` | `8086:4262` | Intel Centrino Wireless-N 2230 |
| 2 | 0 | `14e4:4359` | `14e4:0607` | Broadcom BCM43228 (factory) |
| 3 | 0 | `14e4:4727` | `14e4:0608` | Broadcom BCM4313 |
| 4 | 0 | `14e4:4365` | `17aa:0611` | Broadcom BCM43142 |
| 5 | 1 | `0bdb:191a` | — | Ericsson WWAN |
| 6 | 1 | `0bdb:1919` | — | Ericsson WWAN |
| 7 | 1 | `0bdb:1927` | — | Ericsson WWAN |
| 8 | 1 | `0bdb:1926` | — | Ericsson WWAN |
| 9 | 2 | `0a5c:21f3` | — | Broadcom BCM20702 (BT) |
| 10 | 2 | `0a5c:21f4` | — | Broadcom BCM20702 (BT) |
| 11 | 2 | `04ca:2007` | — | Lite-On BT |
| 12 | 2 | `105b:e065` | — | Foxconn BT |
| 13 | 6 | — | — | end |

### 5.2 `FUN_00000bd0` logic

The function receives `(rcx, edx, r8)`; `edx` selects the check type:

- `edx == 0`: walk `type == 0` entries and compare `[rsi]` with
  `vendor | (device << 16)`.
- `edx == 1` or `edx == 3`: walk `type == 1` or `type == 5`.
- `edx == 2`: walk `type == 2`; if not found, **return 0** (does not block).
- Other values: return 0.

On a match it jumps to `0xdd7` and follows the normal path (including updating
`LenovoScratchData`).

If **no** entry matches, execution falls to `0xc58`:

```
0xc58: mov rcx,rsi
0xc5b: call 0xabc              ; format IDs and report 1802
0xc60: test rax,rax
0xc63: jns 0xc7b
0xc65: ...                     ; wait loop
0xc7b: movabs rax,0x8000000000000007
0xc85: ... epilogue; ret
```

`FUN_00000abc` builds the message with `%04x/%04x...` and reports it through
the status-code protocol. In practice, the 1802 report plus the error return is
what stops the machine.

### 5.3 Callers of `0xbd0`

Function `0xe00` is the WMA protocol handler. Depending on `edx`:

| `edx` | Action | Validates? |
|---|---|---|
| 0 | WLAN PCI | yes, `0xbd0` with `edx=0` |
| 1 | WWAN PCI | yes, `0xbd0` with `edx=1` |
| 2 | Bluetooth USB | yes, `0xbd0` with `edx=2` (does not block if absent) |
| 3 | — | no; records only |
| 4 | — | no; records only |
| 5 | — | yes, `0xbd0` with `edx=5` |

After a successful validation the handler stores the ID in the global structure
(`[0x2058]+0x800...`) and returns the status from `0xbd0`.

## 6. Patch

At PE offset `0xc58` (8 bytes):

```
original:  48 8b ce e8 5c fe ff ff   mov rcx,rsi ; call FUN_00000abc
patched:   31 c0 e9 26 00 00 00 90   xor eax,eax ; jmp 0xc85 (return EFI_SUCCESS)
```

- `xor eax,eax` sets the return value to 0.
- `jmp 0xc85` jumps to the epilogue, skipping the 1802 report and the
  `0x8000000000000007` error return.
- The `0x90` byte is padding; the jump does not execute it.

Effect: **any** PCIe WLAN/WWAN card passes the check. The table is not modified,
so the "card found" path remains available for cards that were already listed;
only the "not found" path changes.

Behavior difference: the patched path does not update `LenovoScratchData` for
the new card. This is an auxiliary record; it does not affect PCIe
initialization or boot.

## 7. Alternatives considered

- **A (applied): bypass the error branch.** `0xc58` returns `EFI_SUCCESS`.
  Allows any WLAN/WWAN card. This is the one that matches "use any card".
- **B: replace a table entry** with the exact ID of the new card. Preserves the
  original logic and updates `LenovoScratchData`, but only allows that card.
  Not used because the goal is to allow any card.
- **C: force the jump to the "found" path.** This would use the data of an
  entry that does not match the real card; rejected as risky.

## 8. Target card

The card is an **Intel AX210HMW** (label: Wi-Fi 6E, Bluetooth 5.3, bus
`WifiPCIeBTUSB`, interface Mini PCI-Express) mounted on an **NFHK N-30U V4**
M.2-to-mini-PCIe adapter.

- WiFi: PCIe, expected ID **`8086:2725`** (AX210). Not in the original table.
- Bluetooth: USB, expected ID **`8087:0032`**. Not validated by the whitelist.
- The AX210 is native PCIe, not CNVi (unlike AX201/AX211).
- The adapter is full-size mini-PCIe; the E330 HMM says the WLAN slot is
  full-size (the half-size slot is for WWAN/mSATA).
- The AX210 uses **MHF4** antenna connectors.
- Bluetooth needs the adapter's USB cable; the E330 mini-PCIe slot does not
  carry USB.

With the adapter out of the slot only the internal Bluetooth (`0a5c:21f3`) is
visible; the AX210 does not enumerate because it has no PCIe power.

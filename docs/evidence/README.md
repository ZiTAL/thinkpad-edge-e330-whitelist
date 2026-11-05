# Evidence — index

Logs and artifacts generated during analysis, validation and the write itself.
All are reproducible with the commands in `docs/02-build-and-validation.md` and
`docs/03-flashing-and-recovery.md`.

| File | What it shows |
|---|---|
| `hardware.txt` | Machine identity (DMI), kernel, `lspci`, `lsusb`, USB tree, interfaces and the flashrom probe with the region map. MAC addresses are redacted. |
| `flashrom_layout_verify.txt` | Pre-write check: the `00820000:00a03fff` layout and the 12 MB file are correct; verification fails only in the block that had not been flashed yet |
| `flash_write.txt` | Actual write: `Erase/write done` and `Verifying flash... VERIFIED` |
| `flash_readback.txt` | Independent full BIOS-region readback after the write: 0 differing bytes against `bios_region_patched.bin` |
| `verify_patched.txt` | Full validation: hashes, CRC32, FFS checksums, 3-range diff and 12 MB image consistency |
| `uefiextract.txt` | UEFIExtract re-parses the patched image without new errors |
| `module_info.txt` | FFS and GUIDed section info for the patched module: CRC32 and checksums valid |
| `objdump_patch.txt` | Disassembly of the patched PE at `0xc58`: `xor eax,eax; jmp 0xc85` |
| `rea_doctor.json` | Full output of `rea doctor --client opencode --json` with Ghidra |
| `rea_doctor_summary.txt` | Readable doctor summary (Ghidra 12.1.4, Java 21, aligned skill) |
| `rea_registration.json` | `rea` entry in `opencode.json` written by `rea setup` |

`patched_pe.bin` (the patched PE32+ module) is generated locally but is a
firmware binary, so it is excluded from the public repository. Its SHA-256 is
`888cdda84922149a0471273b7a4891823de8a520b77d793fc1a803467a1bbe39`.

## Hashes

```text
125c0be42586935b7b622f881151b6bcb0f3258648b81d38fe59d32f6b684cd9  flashrom_layout_verify.txt
728727ac5167b1dd0a45761aa72771e6234be9232db43d5f45e43854e67867d0  flash_write.txt
25e2cb02f319fe7303783d21a1b668e2ff53ab2ff133c9c38c83018685a0ba74  flash_readback.txt
2b38ec7ea33c84162cd2576f402934046f673219b79224e701b422815bf6bbfa  hardware.txt
013562022c8a1a46ac4743f954558e0a880aebb35b221f617d48411b130dfcd3  module_info.txt
21c46fdf865015ae4de010d424e1684a961128628dd0bb991f76bea925a114cf  objdump_patch.txt
af6f4d7960542e3e0edc85f752241c4d033478258f94465311cd4ab2c4fbf0f0  rea_doctor.json
c5e3b8055771e7c933b3478413fda815f4f41979adb9799544616fa144f8072f  rea_doctor_summary.txt
6dc9f8dba72c6bacf9e3fcbfb6e10d60b3342c57523f1243fd13666ca18cfe91  rea_registration.json
c55117ed628d7ff33b71290773ac54729e33d684c1a7d52ccda6a07d46e7c95f  uefiextract.txt
ddda58b2ab5bcd07ad8d4f852b98db733e7d270c5256af7aacd8b63f734b079e  verify_patched.txt
```

## Note about the pre-write flashrom `FAILED`

`flashrom_layout_verify.txt` ends with:

```text
Verifying flash... FAILED at 0x00820059!
Expected=0xd6, Found=0x1f,
failed byte count from 0x00820000-0x00a03fff: 0x1e1a36
```

This is **expected for the pre-write check**: at that moment the flash still
held the original firmware and was being compared against the patched image.
The mismatch at `0x00820059` is the outer FFS data checksum (`0x1f` original →
`0xd6` patched), and the large byte count corresponds to the recompressed LZMA
stream. It does not indicate a bad image. The actual write is in
`flash_write.txt`.

## Note about `wma_0xbd0.json`

`wma_0xbd0.json` is a REA/Ghidra decompile attempt that returned
`invalid_request`: Ghidra did not create a function at `0xbd0` because it found
no direct xrefs. The analysis was completed with `objdump` (`wma_disasm.txt`)
and the ID table. It is kept as process evidence, not as a result.

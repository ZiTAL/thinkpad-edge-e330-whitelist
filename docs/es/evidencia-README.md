# Evidencia — índice

Logs y artefactos generados durante el análisis y la validación. Todos son
reproducibles con los comandos de `docs/02-construccion-y-validacion.md`.

| Fichero | Qué demuestra |
|---|---|
| `hardware.txt` | Identidad del equipo (DMI), kernel, `lspci`, `lsusb`, árbol USB, interfaces y probe de `flashrom` con el mapa de regiones |
| `flashrom_layout_verify.txt` | El layout `00820000:00a03fff` y el fichero de 12 MB son correctos; la verificación falla solo en el bloque que aún no está flasheado |
| `verify_patched.txt` | Validación completa: hashes, CRC32, checksums FFS, diff de 3 rangos y coherencia de la imagen de 12 MB |
| `uefiextract.txt` | UEFIExtract vuelve a parsear la imagen parcheada sin errores nuevos |
| `module_info.txt` | Info del FFS y de la sección GUIDed del módulo parcheado: CRC32 y checksums válidos |
| `objdump_patch.txt` | Desensamblado del PE parcheado en `0xc58`: `xor eax,eax; jmp 0xc85` |
| `patched_pe.bin` | Copia del PE32+ parcheado extraído de la imagen |
| `rea_doctor.json` | Salida completa de `rea doctor --client opencode --json` con Ghidra |
| `rea_doctor_summary.txt` | Resumen legible del doctor (Ghidra 12.1.4, Java 21, skill alineado) |
| `rea_registration.json` | Entrada `rea` del `opencode.json` registrada por `rea setup` |

## Hashes

```text
125c0be42586935b7b622f881151b6bcb0f3258648b81d38fe59d32f6b684cd9  flashrom_layout_verify.txt
0be0d2e8023d451f5fd9d7cbac1538b0090d8f4e813a00a370d08a644226a74a  hardware.txt
013562022c8a1a46ac4743f954558e0a880aebb35b221f617d48411b130dfcd3  module_info.txt
21c46fdf865015ae4de010d424e1684a961128628dd0bb991f76bea925a114cf  objdump_patch.txt
888cdda84922149a0471273b7a4891823de8a520b77d793fc1a803467a1bbe39  patched_pe.bin
af6f4d7960542e3e0edc85f752241c4d033478258f94465311cd4ab2c4fbf0f0  rea_doctor.json
c5e3b8055771e7c933b3478413fda815f4f41979adb9799544616fa144f8072f  rea_doctor_summary.txt
6dc9f8dba72c6bacf9e3fcbfb6e10d60b3342c57523f1243fd13666ca18cfe91  rea_registration.json
c55117ed628d7ff33b71290773ac54729e33d684c1a7d52ccda6a07d46e7c95f  uefiextract.txt
ddda58b2ab5bcd07ad8d4f852b98db733e7d270c5256af7aacd8b63f734b079e  verify_patched.txt
```

## Nota sobre el `FAILED` de flashrom

`flashrom_layout_verify.txt` termina con:

```text
Verifying flash... FAILED at 0x00820059!
Expected=0xd6, Found=0x1f,
failed byte count from 0x00820000-0x00a03fff: 0x1e1a36
```

Esto es **lo esperado**: la flash todavía contiene el firmware original y se
está comparando contra la imagen parcheada. El fallo en `0x00820059` es el
checksum de datos del FFS externo (`0x1f` original → `0xd6` parcheado), y el
recuento grande corresponde al stream LZMA recomprimido. No indica un error de
la imagen.

## Nota sobre `wma_0xbd0.json`

`wma_0xbd0.json` es un intento de decompilación con REA/Ghidra que devolvió
`invalid_request`: Ghidra no creó una función en `0xbd0` porque no encontró
xrefs directos. El análisis se completó con `objdump` (`wma_disasm.txt`) y con
la tabla de IDs. Se conserva como evidencia del proceso, no como resultado.

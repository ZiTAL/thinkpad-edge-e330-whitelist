# 05 — Inventario, entorno y reproducción

## 1. Inventario de ficheros

### 1.1 Imágenes y módulos

| Fichero | Tamaño | SHA-256 | Rol |
|---|---:|---|---|
| `bios_region.bin` | 4 MB | `8e3719c61c651a7bc78868b5cca90191e685e38407badf00f48a5a53d471f43d` | Región BIOS original extraída del volcado |
| `bios_region_patched.bin` | 4 MB | `a5bdf564340cc7805c23621464d9f8f39ca856371a1d89e8aa2871877a8003c2` | Región BIOS parcheada |
| `flash_image_12m.bin` | 12 MB | `e4b4a6537a130ab04fad87c494b8e1078173dcc7947a6f987b1b1604b19664c3` | Imagen para `flashrom` (región BIOS parcheada en `0x800000`) |
| `orig_bios_region.bin` | 12 MB | `356096115bcb09db373805da3f15a60121d4f2abb52faade6e5af1d8a9227c94` | Volcado flashrom (solo región BIOS; resto a cero) |
| `LenovoWmaPolicyDxe.bin` | 8576 B | `2ccf44433c5fe63cb0ac2abe83344af865017aa34946eabe4c8024ae2431ebff` | PE32+ original del módulo del whitelist |
| `LenovoWmaPciDxe.bin` | 3168 B | `8f273718e25255b33c730ace91965267d54bd88801f29a8832154e451b28b82c` | Driver PCI auxiliar |
| `LenovoWmaUsbDxe.bin` | 3616 B | `3b40d75cad4a0d5bdab9767a5f1f1ebeabcf3b239f374a7bb48e9675d6a81f33` | Driver USB auxiliar |
| `../evidence/patched_pe.bin` | 8576 B | `888cdda84922149a0471273b7a4891823de8a520b77d793fc1a803467a1bbe39` | PE32+ parcheado (copia de evidencia) |

### 1.2 Scripts y layout

| Fichero | Tamaño | SHA-256 | Rol |
|---|---:|---|---|
| `patch_bios.py` | 3833 B | `f1930f5f64ec76a1c3963e9e793f0500700b37208a410fc73772f4e2e98afd0e` | Genera la región parcheada |
| `verify_layout.py` | 4604 B | `9eb2e785e017c804c10d3e8010c0af13a124cded72702315df3cabdf58678fee` | Valida la imagen completa |
| `lzma_test.py` | 1070 B | `be9249652a215a5100a959e72501b332c20146303836928b73085741828a4c6a` | Prueba de recompresión LZMA |
| `search_strings.py` | 1107 B | `af4e2404c38eb23b441acd81a54a03a6a94d4fc435a22d39c9e06b7f25ba1f7a` | Búsqueda de cadenas en el árbol UEFI |
| `biosmod.layout` | 26 B | `a4d8932b7ac3573ca0f7332a8acecb46f442dc24331d1edca0576945db55ebae` | Layout de escritura de 2 MB |
| `wma_disasm.txt` | 69 KB | `96ffbe1104f8cb04cfa64755742929364cf3fa0ee7885a2d4e501f0e2199ce29` | Desensamblado completo del módulo |

### 1.3 Artefactos de análisis

| Ruta | Contenido |
|---|---|
| `bios_region.bin.dump/` | Árbol UEFI extraído del original (UEFIExtract) |
| `bios_region_patched.bin.dump/` | Árbol UEFI extraído del parcheado |
| `bios_region.bin.report.txt` | Informe UEFIExtract del original |
| `bios_region_patched.bin.report.txt` | Informe UEFIExtract del parcheado |
| `bios_region.bin.guids.csv` | Base de GUIDs del original |
| `bios_region_patched.bin.guids.csv` | Base de GUIDs del parcheado |
| `wma_0xbd0.json` | Intento de decompilación REA (Ghidra no creó la función `0xbd0`; se usó objdump) |
| `wma_procs.json` | Lista de procedimientos detectados por Ghidra |
| `model.jpg` | Foto de la etiqueta de la tarjeta AX210HMW |
| `../evidence/` | Logs de validación y entorno (ver índice) |

## 2. Herramientas y versiones

| Herramienta | Versión / ruta | Uso |
|---|---|---|
| Linux Mint | 22.3 (Zena), kernel 6.17.0-42-generic | Entorno |
| Python | 3.12.3 | Scripts de parcheo/validación |
| flashrom | 1.3.0-2.1ubuntu2 | Volcado, probe y escritura |
| UEFIExtract | NE alpha 76 (A76); ruta temporal `/tmp/opencode/uefi/uefiextract` (descarga: `https://github.com/LongSoft/UEFITool/releases/tag/A76`) | Parseo UEFI |
| Java | OpenJDK 21.0.12.1 | Ghidra |
| Ghidra | 12.1.4, `/opt/ghidra` | Análisis nativo (REA) |
| REA | 6.8.0 (`npx -y rea-agents@6.8.0`) | MCP/CLI de análisis |
| binutils | `objdump` del sistema | Desensamblado |

## 3. Entorno REA

- El MCP de REA está registrado en `~/.config/opencode/opencode.json`:

```json
{
  "type": "local",
  "command": ["npx", "-y", "rea-agents@6.8.0", "mcp"],
  "disabled": false
}
```

- Ghidra se instaló en `/opt/ghidra` y se validó con:

```bash
GHIDRA_INSTALL_DIR=/opt/ghidra npx -y rea-agents@6.8.0 doctor --client opencode --json
```

Resumen (`../evidence/rea_doctor_summary.txt`):

```
healthy=True environment_healthy=True
cli=6.8.0 skill=aligned
ghidra                     ok=True  healthy /opt/ghidra
ghidra-version             ok=True  healthy 12.1.4
ghidra-headless            ok=True  healthy /opt/ghidra/support/analyzeHeadless
ghidra-native_decompiler   ok=True  healthy .../decompile reports elf x86_64
ghidra-java                ok=True  healthy 21.0.12.1; 64-bit; JDK
```

Nota: el MCP se lanzó sin `GHIDRA_INSTALL_DIR`; el CLI se usó con la variable
exportada. Para que el MCP use Ghidra en futuras sesiones, hay que añadir
`GHIDRA_INSTALL_DIR=/opt/ghidra` al entorno del servidor REA o reiniciar el
cliente con esa variable.

## 4. Comandos usados (cronológico)

```bash
# Identificación
cat /sys/class/dmi/id/*
lspci -nn
lsusb

# Volcado de la región BIOS (solo lectura)
sudo flashrom -p internal --ifd -i bios -r orig_bios_region.bin
dd if=orig_bios_region.bin of=bios_region.bin bs=1 skip=8388608 count=4194304

# Parseo UEFI
/tmp/opencode/uefi/uefiextract bios_region.bin

# Búsqueda de cadenas
python3 search_strings.py bios_region.bin.dump

# Extracción del módulo
# (ruta .../289 LenovoWmaPolicyDxe.efi/0 FC1BCDB0.../0 PE32 image section/body.bin)

# Desensamblado
objdump -d -M intel --no-show-raw-insn LenovoWmaPolicyDxe.bin > wma_disasm.txt
objdump -d -M intel --no-show-raw-insn \
  --start-address=0xbd0 --stop-address=0xd20 LenovoWmaPolicyDxe.bin

# Construcción y validación
python3 patch_bios.py
python3 verify_layout.py

# Imagen de 12 MB
cp orig_bios_region.bin flash_image_12m.bin
dd if=bios_region_patched.bin of=flash_image_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none

# Comprobación sin escribir
sudo flashrom -p internal
sudo flashrom -p internal -l biosmod.layout -i biosmod -v flash_image_12m.bin

# REA / Ghidra
GHIDRA_INSTALL_DIR=/opt/ghidra npx -y rea-agents@6.8.0 doctor --client opencode --json
```

## 5. Limitaciones y notas

- `orig_bios_region.bin` **no es un volcado completo**: descriptor y ME están a
  cero porque flashrom solo leyó la región BIOS. Para un programador SPI hay
  que volcar el chip completo.
- `bios_region.bin.dump/` y `bios_region_patched.bin.dump/` son reproducibles
  con UEFIExtract; ocupan espacio y se pueden borrar si no se necesitan.
- `wma_0xbd0.json` es un intento fallido de decompilación: Ghidra no reconoció
  `0xbd0` como función (no había xrefs directos). El análisis se hizo con
  `objdump` y con la lógica de la tabla; `wma_procs.json` documenta lo que
  Ghidra sí detectó.
- El checksum PE del módulo es 0 y no hay directorio de seguridad; no se
  recalcula.
- El parche no toca la tabla ni el Bluetooth; solo la rama de error.
- La flash **no se ha escrito**. El estado del equipo es el original.

## 6. Tareas pendientes

1. Decidir si se flashea por software o se espera a un programador SPI.
2. Si se flashea: seguir `docs/03-flasheo-y-recuperacion.md` y actualizar este
   inventario con el resultado.
3. Instalar la AX210 en la ranura WLAN full-size, con antenas MHF4 y el cable
   USB del adaptador.
4. Verificar `lspci` (`8086:2725`), `lsusb` (`8087:0032`) y ausencia de 1802.
5. Si se quiere volver atrás: reflashear `bios_region.bin` (ver doc 03).

# 02 — Construcción de la imagen y validación

## 1. Objetivo

Partiendo de la región BIOS original (`bios_region.bin`, 4 MB), generar una
región parcheada (`bios_region_patched.bin`) que:

1. contenga el parche de 8 bytes en `LenovoWmaPolicyDxe.efi`;
2. conserve **exactamente** los mismos tamaños y la misma estructura UEFI;
3. tenga CRC32 y checksums FFS válidos;
4. se pueda escribir en la flash sin tocar descriptor, ME ni boot block.

## 2. Cadena de contenedores

```
bios_region.bin (4 MB)
└─ FV 7A9354D9...
   └─ FFS 4A538818...                    offset 0x20048, tamaño 0x1E38F9
      └─ Compressed section (LZMA)       offset 0x20060, tamaño 0x1E38E1
         └─ (descomprimido 0x780010)
            └─ Volume image section      offset 0x0C, tamaño 0x780004
               └─ Volume                  offset 0x10, tamaño 0x780000
                  └─ FFS LenovoWmaPolicyDxe.efi
                                             offset 0x525530, tamaño 0x21F4
                     └─ GUIDed CRC32 section
                                             offset 0x525548, tamaño 0x21DC
                        └─ CRC32             offset 0x525560
                        └─ PE32 section      offset 0x525564, tamaño 0x2184
                           └─ PE32+ image    offset 0x525568, tamaño 0x2180
```

## 3. Offsets y bytes del parche

| Dato | Valor |
|---|---|
| Offset del parche en el PE | `0xC58` |
| Offset del parche en el volumen descomprimido | `0x5261C0` (`0x525568 + 0xC58`) |
| Bytes originales | `48 8b ce e8 5c fe ff ff` |
| Bytes parcheados | `31 c0 e9 26 00 00 00 90` |
| Significado | `xor eax,eax; jmp 0xc85` (return 0) |

El salto relativo es `0x26`: desde `0xc5f` (fin del `jmp`) hasta `0xc85`
(epílogo) hay `0x26` bytes.

## 4. Checksums que hay que reconstruir

### 4.1 CRC32 de la sección GUIDed

La sección GUIDed (`FC1BCDB0-7D31-49AA-936A-A4600D9DD083`) usa CRC32. El CRC
está en `0x525560` y cubre desde el byte siguiente (`0x525564`) hasta el final
de la sección (`0x525548 + 0x21DC = 0x527724`), es decir, `0x21C0` bytes:

```python
crc = zlib.crc32(dec[0x525564:0x527724]) & 0xFFFFFFFF
struct.pack_into("<I", dec, 0x525560, crc)
```

Valor original: `0x9724A531`. Valor parcheado: `0x9C728A34`.

### 4.2 Checksums FFS internos

Fichero `LenovoWmaPolicyDxe.efi`, offset `0x525530`, tamaño `0x21F4`:

- **Data checksum** (byte en `header+0x11`):
  `(0x100 - sum(body)) & 0xFF`, con `body = file[0x18 : 0x21F4]`.
- **Header checksum** (byte en `header+0x10`):
  `(0x100 - sum(header_con_campos_cero)) & 0xFF`, donde se ponen a cero
  `Header` (`0x10`), `File` (`0x11`) y `State` (`0x17`).

Valores parcheados: header `0xCB`, data `0x8B`.

### 4.3 Checksums FFS externos

Fichero `4A538818-5AE0-4EB2-B2EB-488B23657022`, offset `0x20048`, tamaño
`0x1E38F9`. Se recalculan igual porque el cuerpo contiene la sección LZMA
recomprimida.

Valores parcheados: header `0x65`, data `0xD6`.

### 4.4 Checksum PE

El PE tiene `CheckSum = 0` y no tiene directorio de seguridad. No se recalcula;
UEFI no lo verifica.

## 5. Recompresión LZMA

La sección comprimida usa LZMA "alone" (cabecera de 13 bytes dentro del cuerpo):

```
5d 00 00 80 00   props = 0x5D, dict = 0x00800000
10 00 78 00 00 00 00 00   tamaño sin comprimir = 0x780010
```

Se recompresa con las mismas propiedades:

- Filtro `LZMA1`, `dict_size = 0x800000`, `lc=3`, `lp=0`, `pb=2`
- `mode = NORMAL`, `nice_len = 273`, `mf = BT4`, `depth = 0`
- Cabecera `.lzma` original conservada (liblzma escribe tamaño desconocido)
- Resultado: **1.978.758 bytes** (frente a 1.980.632 originales)
- Se rellena con `0xFF` hasta `0x1E38D8` para **no cambiar ningún tamaño**
- El decodificador EDK2 lee `0x780010` bytes y ignora el relleno

## 6. Scripts

### `patch_bios.py`

Genera `bios_region_patched.bin`. Pasos:

1. Lee `bios_region.bin`.
2. Extrae el cuerpo comprimido en `0x20069`, longitud `0x1E38D8`.
3. Descomprime con `lzma.decompress(..., format=lzma.FORMAT_ALONE)`.
4. Verifica que el PE32 de `0x525568` coincide con `LenovoWmaPolicyDxe.bin`.
5. Aplica los 8 bytes en `0x5261C0`.
6. Recalcula CRC32 y checksums FFS internos.
7. Recompresa y rellena a tamaño original.
8. Escribe el cuerpo comprimido en `0x20069`.
9. Recalcula checksums FFS externos.
10. Guarda `bios_region_patched.bin`.

El script incluye `assert` sobre los bytes originales, el tamaño del PE y el
CRC32; si se ejecuta sobre otra versión de BIOS, falla en vez de generar una
imagen corrupta.

### `verify_layout.py`

Valida la imagen generada contra la original. Comprueba:

- tamaños y SHA-256 de original y parcheada;
- que el PE32 original coincide con el módulo extraído;
- que el PE32 parcheado solo difiere en los 8 bytes del parche;
- CRC32 de la sección GUIDed;
- checksums FFS internos y externos;
- que el volumen descomprimido solo difiere en 3 rangos;
- que `flash_image_12m.bin` lleva la región parcheada en `0x800000`.

Salida actual: **PASS**.

### `lzma_test.py`

Script exploratorio que descomprime y prueba varios presets de LZMA para
comprobar que la recompresión cabe en el tamaño original. Se conserva como
evidencia del proceso; no forma parte del build.

### `search_strings.py`

Busca cadenas ASCII/UTF-16 en el árbol extraído por UEFIExtract. Se usó para
localizar `1802`, `Unauthorized`, `WLAN`, etc.

## 7. Construcción de la imagen de 12 MB

`flashrom` con `--ifd -i bios` exige un fichero del tamaño total del chip
(12 MB), no de la región. Se construye así:

```bash
cp orig_bios_region.bin flash_image_12m.bin
dd if=bios_region_patched.bin of=flash_image_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none
```

- `0x800000 = 8.388.608`
- Solo importa la región BIOS; el resto queda como estaba en
  `orig_bios_region.bin` (ceros).

## 8. Validación

### 8.1 Validación estructural

`python3 verify_layout.py` → **PASS**. Resultado completo en
`../evidence/verify_patched.txt`. Diff del volumen descomprimido:

```
0x525541-0x525541: 0x75 -> 0x8b          (data checksum FFS interno)
0x525560-0x525563: 31 a5 24 97 -> 34 8a 72 9c   (CRC32)
0x5261C0-0x5261C7: 48 8b ce e8 5c fe ff ff
                   -> 31 c0 e9 26 00 00 00 90   (parche)
```

No hay ningún otro byte distinto en los 7.864.336 bytes del volumen.

### 8.2 Re-parseo UEFI

UEFIExtract vuelve a parsear la imagen parcheada. Info del módulo:

```
Full size: 21F4h (8692)
Header checksum: CBh, valid
Data checksum: 8Bh, valid
```

Info de la sección GUIDed:

```
Checksum type: CRC32
Checksum: 9C728A34h, valid
```

Salida en `../evidence/uefiextract.txt` y `../evidence/module_info.txt`.

### 8.3 Desensamblado

`objdump` del PE parcheado en `0xc58`:

```
c58: xor    eax,eax
c5a: jmp    0xc85
c5f: nop
c60: test   rax,rax
...
c85: lea    r11,[rsp+0x70]   ; epílogo
```

Salida en `../evidence/objdump_patch.txt`.

### 8.4 Comprobación con flashrom (sin escribir)

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod -v flash_image_12m.bin
```

Resultado esperado (la flash aún tiene el firmware original):

```
Verifying flash... FAILED at 0x00820059!
Expected=0xd6, Found=0x1f,
failed byte count from 0x00820000-0x00a03fff: 0x1e1a36
```

Eso confirma que:

- el layout y el tamaño del fichero son correctos;
- flashrom lee exactamente el bloque que se va a escribir;
- las diferencias son las esperadas (el bloque comprimido completo, porque
  LZMA cambia todo el stream).

Salida en `../evidence/flashrom_layout_verify.txt`.

## 9. Reproducción desde cero

```bash
# 1. Volcar la región BIOS (solo lectura)
sudo flashrom -p internal --ifd -i bios -r orig_bios_region.bin

# 2. Extraer la región de 4 MB
dd if=orig_bios_region.bin of=bios_region.bin bs=1 skip=8388608 count=4194304

# 3. Extraer el módulo con UEFIExtract (opcional, para verificar)
uefiextract bios_region.bin

# 4. Generar la imagen parcheada
python3 patch_bios.py

# 5. Validar
python3 verify_layout.py

# 6. Construir la imagen de 12 MB
cp orig_bios_region.bin flash_image_12m.bin
dd if=bios_region_patched.bin of=flash_image_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none
```

Dependencias: Python 3.12 con `lzma` y `zlib` (stdlib). UEFIExtract solo es
necesario para la inspección/validación UEFI.

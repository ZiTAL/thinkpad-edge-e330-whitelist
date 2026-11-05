# 01 — Análisis del firmware

## 1. Equipo y firmware

Datos leídos de DMI y del sistema en el momento del análisis:

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

- Chipset: **Intel HM77** (Ivy Bridge, 3.ª gen Core)
- Flash SPI: 12 MB, detectada por flashrom como `Opaque flash chip` mediante
  hardware sequencing (hay varios chips detrás del descriptor)
- WiFi de serie: **Broadcom BCM43228** `14e4:4359`, subsistema `14e4:0607`
- Bluetooth de serie: **Broadcom BCM20702A0** `0a5c:21f3`, USB interno
- Ethernet: Realtek RTL8111/8168
- Lector de tarjetas: Realtek RTS5209

## 2. Volcado de la región BIOS

El descriptor Intel divide la flash de 12 MB así:

| Región | Rango | Acceso observado |
|---|---|---|
| Descriptor | `0x000000-0x000FFF` | solo lectura |
| ME | `0x001000-0x7FFFFF` | bloqueada |
| BIOS | `0x800000-0xBFFFFF` | lectura/escritura |

Comando usado (solo lectura):

```bash
sudo flashrom -p internal --ifd -i bios -r orig_bios_region.bin
```

`flashrom` genera un fichero del tamaño total del chip (12 MB) con la región
BIOS leída y el resto a cero. Por eso `orig_bios_region.bin` **no es un volcado
completo** y no sirve para restaurar descriptor/ME con un programador; solo se
usa para construir la imagen de escritura. La región BIOS real se extrajo a
`bios_region.bin`:

```bash
dd if=orig_bios_region.bin of=bios_region.bin bs=1 skip=8388608 count=4194304
```

- `bios_region.bin`: 4 MB, SHA-256 `8e3719c61c651a7bc78868b5cca90191e685e38407badf00f48a5a53d471f43d`

## 3. Estructura UEFI

La región BIOS se parseó con UEFIExtract (NE alpha 76):

```bash
/tmp/opencode/uefi/uefiextract bios_region.bin
```

Ruta temporal de la herramienta; el binario se puede obtener de
`https://github.com/LongSoft/UEFITool/releases/tag/A76`
(`UEFIExtract_NE_A76_x64_linux.zip`).

Puntos relevantes de la jerarquía:

```
BIOS region (4 MB)
├─ FV 7A9354D9-0468-444A-81CE-0BF617D890DF   (empieza en 0x1FF40)
│  └─ FFS 4A538818-5AE0-4EB2-B2EB-488B23657022   (0x20048, tamaño 0x1E38F9)
│     └─ Compressed section (LZMA, 0x20060, descomprime 0x780010)
│        └─ Volume image section (0x780004)
│           └─ Volume (0x780000)
│              └─ ... 289 LenovoWmaPolicyDxe.efi ...
```

### 3.1 Sección comprimida

En `bios_region.bin`, offset `0x20060`:

```
e1 38 1e 01   tamaño 0x1E38E1, tipo 0x01 (compresión)
10 00 78 00   longitud descomprimida 0x780010
02            tipo de compresión (LZMA)
5d 00 00 80 00 10 00 78 00 00 00 00 00
              cabecera .lzma: props 0x5D, diccionario 0x800000,
              tamaño 0x780010
```

- Cuerpo comprimido: `0x1E38D8` bytes (1.980.632)
- Contenido descomprimido: `0x780010` bytes (7.864.336)

### 3.2 Fichero y sección internos

Dentro del volumen descomprimido:

| Elemento | Offset descomprimido | Detalle |
|---|---|---|
| Inicio del volumen | `0x10` | cabecera FV de `0x780000` |
| FFS `LenovoWmaPolicyDxe.efi` | `0x525530` | GUID `79E0EDD7-9D1D-4F41-AE1A-F896169E5216`, tamaño `0x21F4` |
| Sección GUIDed CRC32 | `0x525548` | GUID `FC1BCDB0-7D31-49AA-936A-A4600D9DD083`, tamaño `0x21DC` |
| CRC32 | `0x525560` | cubre desde `0x525564` hasta el final de la sección |
| Cabecera de sección PE32 | `0x525564` | tamaño `0x2184`, tipo `0x10` |
| Imagen PE32+ | `0x525568` | 8576 bytes (`0x2180`) |

El módulo PE32+ tiene:

- Entry point: `0x10d8`
- `.text`: VMA `0x240`, tamaño `0x1E30`
- Sección de datos: VMA `0x2080`, tamaño `0xD8`
- Sin directorio de seguridad/certificado
- Checksum PE: `0`

## 4. Localización del whitelist

La cadena del error aparece en UTF-16LE dentro del módulo:

```
1802: Unauthorized network card is plugged in - Power off and remove the miniPCI network card (%s).
```

También hay formatos `%04x/%04x/%04x/%04x` y `%04x/%04x`, y los nombres de
variables `LenovoScratchData` y `LenovoConfig`.

Solo `LenovoWmaPolicyDxe.efi` contiene la cadena `1802`; `LenovoWmaPciDxe.efi` y
`LenovoWmaUsbDxe.efi` son drivers de device-path que invocan la política.
`LenovoSetupSecurityDxe.efi` contiene textos de setup ("Wireless LAN",
"unauthorized" genérico), pero no la comprobación del 1802.

## 5. Función que valida las tarjetas

### 5.1 Tabla de IDs

En el PE, offset `0x270`, hay una tabla de entradas de 16 bytes:

```
u32 type; u16 vendor; u16 device; u16 subvendor; u16 subdevice; u32 reserved?
```

Termina con `type == 6`. Contenido original:

| # | type | vendor:device | subvendor:subdevice | Interpretación |
|---|---|---|---|---|
| 0 | 0 | `10ec:8176` | `10ec:8195` | Realtek RTL8188CE |
| 1 | 0 | `8086:0888` | `8086:4262` | Intel Centrino Wireless-N 2230 |
| 2 | 0 | `14e4:4359` | `14e4:0607` | Broadcom BCM43228 (la de serie) |
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
| 13 | 6 | — | — | fin |

### 5.2 Lógica de `FUN_00000bd0`

La función recibe `(rcx, edx, r8)`; `edx` selecciona el tipo de comprobación:

- `edx == 0`: recorre las entradas `type == 0` y compara `[rsi]` con
  `vendor | (device << 16)`.
- `edx == 1` o `edx == 3`: recorre `type == 1` o `type == 5`.
- `edx == 2`: recorre `type == 2`; si no encuentra, **devuelve 0** (no bloquea).
- Otros valores: devuelve 0.

Si encuentra la entrada, salta a `0xdd7` y sigue el camino normal (incluye
actualización de `LenovoScratchData`).

Si **no** encuentra la entrada, cae en `0xc58`:

```
0xc58: mov rcx,rsi
0xc5b: call 0xabc              ; formatea IDs y reporta el 1802
0xc60: test rax,rax
0xc63: jns 0xc7b
0xc65: ...                     ; bucle de espera
0xc7b: movabs rax,0x8000000000000007
0xc85: ... epílogo; ret
```

`FUN_00000abc` construye el mensaje con `%04x/%04x...` y lo reporta mediante el
protocolo de status code. En la práctica, el 1802 y el retorno de error son la
causa de que el equipo se detenga.

### 5.3 Quién llama a `0xbd0`

La función `0xe00` es el handler del protocolo WMA. Según `edx`:

| `edx` | Acción | ¿Valida? |
|---|---|---|
| 0 | WLAN PCI | sí, `0xbd0` con `edx=0` |
| 1 | WWAN PCI | sí, `0xbd0` con `edx=1` |
| 2 | Bluetooth USB | sí, `0xbd0` con `edx=2` (no bloquea si no está) |
| 3 | — | no; solo registra |
| 4 | — | no; solo registra |
| 5 | — | sí, `0xbd0` con `edx=5` |

Tras una validación correcta, el handler guarda el ID en la estructura global
(`[0x2058]+0x800...`) y devuelve el status de `0xbd0`.

## 6. Parche

En el PE, offset `0xc58` (8 bytes):

```
original:  48 8b ce e8 5c fe ff ff   mov rcx,rsi ; call FUN_00000abc
parcheado: 31 c0 e9 26 00 00 00 90   xor eax,eax ; jmp 0xc85 (return EFI_SUCCESS)
```

- `xor eax,eax` pone el valor de retorno a 0.
- `jmp 0xc85` salta al epílogo, evitando el reporte del 1802 y el retorno
  `0x8000000000000007`.
- El byte `0x90` es relleno; el salto no lo ejecuta.

Efecto: **cualquier** tarjeta WLAN/WWAN PCIe pasa la comprobación. No se
modifica la tabla, así que la lógica de "tarjeta encontrada" sigue disponible
para las que ya estaban; solo cambia el camino de "no encontrada".

Diferencia de comportamiento: en el camino parcheado no se actualiza
`LenovoScratchData` para la tarjeta nueva. Es un registro auxiliar; no afecta a
la inicialización PCIe de la tarjeta ni al arranque.

## 7. Variantes consideradas

- **A (aplicada): bypass de la rama de error.** `0xc58` devuelve `EFI_SUCCESS`.
  Permite cualquier tarjeta WLAN/WWAN. Es la que encaja con "usar cualquiera".
- **B: sustituir una entrada de la tabla** por el ID exacto de la tarjeta nueva.
  Mantiene la lógica original y actualiza `LenovoScratchData`, pero solo permite
  esa tarjeta. No se usó porque el objetivo es permitir cualquiera.
- **C: forzar el salto al camino "encontrada"**. Implica usar los datos de una
  entrada que no corresponde a la tarjeta real; descartada por riesgo de
  comportamiento raro.

## 8. Tarjeta objetivo

La tarjeta es una **Intel AX210HMW** (etiqueta: Wi-Fi 6E, Bluetooth 5.3, bus
`WifiPCIeBTUSB`, interface Mini PCI-Express) montada en un adaptador
**NFHK N-30U V4** de M.2 a mini-PCIe.

- WiFi: PCIe, ID esperado **`8086:2725`** (AX210). No está en la tabla original.
- Bluetooth: USB, ID esperado **`8087:0032`**. No se valida en el whitelist.
- La AX210 es PCIe nativa, no CNVi (a diferencia de AX201/AX211).
- El adaptador es full-size mini-PCIe; el HMM del E330 indica que la ranura
  WLAN es full-size (la half-size es la de WWAN/mSATA).
- El AX210 usa conectores de antena **MHF4**.
- El Bluetooth necesita el cable USB del adaptador; la ranura mini-PCIe del
  E330 no lleva USB.

Con el adaptador fuera de la ranura solo se ve el Bluetooth interno
(`0a5c:21f3`); la AX210 no enumera porque no recibe alimentación PCIe.

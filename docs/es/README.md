# ThinkPad Edge E330 — eliminación del whitelist WiFi/WWAN

**Estado: firmware parcheado y validado. La flash NO se ha tocado.** El equipo
sigue arrancando con el BIOS original H3ET72WW (1.09). El siguiente paso
(escribir en la flash) queda pendiente de decisión.

---

## Resumen

- Equipo: **Lenovo ThinkPad Edge E330**, machine type **3354DVG**
- BIOS: **H3ET72WW (1.09)**, 25/02/2013, Phoenix SecureCore Tiano
- Chipset: Intel HM77 (Ivy Bridge), SPI de 12 MB
- WiFi original: Broadcom **BCM43228** (`14e4:4359`, subsistema `14e4:0607`)
- Bluetooth original: Broadcom **BCM20702A0** (`0a5c:21f3`)
- Tarjeta objetivo: **Intel AX210HMW** (Wi-Fi 6E, BT 5.3) sobre adaptador
  **NFHK N-30U V4** M.2 → mini-PCIe
- El aviso que se elimina: `1802: Unauthorized network card is plugged in`
- Módulo parcheado: `LenovoWmaPolicyDxe.efi` (FFS `79E0EDD7-9D1D-4F41-AE1A-F896169E5216`)
- Parche: 8 bytes en el PE, offset `0xc58`; la rama "tarjeta no autorizada"
  devuelve `EFI_SUCCESS` en vez de reportar el 1802.

## Documentación

| Documento | Contenido |
|---|---|
| [`01-analisis-firmware.md`](01-analisis-firmware.md) | Equipo, volcado, estructura UEFI, módulo, tabla de IDs, función `0xbd0`, justificación del parche |
| [`02-construccion-y-validacion.md`](02-construccion-y-validacion.md) | Layout LZMA, offsets exactos, CRC/checksums, scripts, resultados de validación |
| [`03-flasheo-y-recuperacion.md`](03-flasheo-y-recuperacion.md) | Comandos de escritura, verificación posterior, reversión, crisis recovery, programador SPI |
| [`04-riesgos.md`](04-riesgos.md) | Matriz de riesgos, probabilidad/impacto, mitigaciones y recomendación |
| [`05-inventario-y-entorno.md`](05-inventario-y-entorno.md) | Inventario de ficheros y hashes, herramientas, versiones, entorno, comandos usados |
| [`evidencia-README.md`](evidencia-README.md) | Índice de logs y evidencias en bruto |

## Ficheros principales

| Fichero | Contenido | SHA-256 |
|---|---|---|
| `bios_region.bin` | Región BIOS original (4 MB, `0x800000..0xBFFFFF`) | `8e3719c61c651a7bc78868b5cca90191e685e38407badf00f48a5a53d471f43d` |
| `bios_region_patched.bin` | Región BIOS parcheada (4 MB) | `a5bdf564340cc7805c23621464d9f8f39ca856371a1d89e8aa2871877a8003c2` |
| `flash_image_12m.bin` | Imagen de 12 MB para `flashrom` (solo válida la región BIOS) | `e4b4a6537a130ab04fad87c494b8e1078173dcc7947a6f987b1b1604b19664c3` |
| `orig_bios_region.bin` | Volcado flashrom de 12 MB (región BIOS leída; resto a cero) | `356096115bcb09db373805da3f15a60121d4f2abb52faade6e5af1d8a9227c94` |
| `LenovoWmaPolicyDxe.bin` | Módulo original | `2ccf44433c5fe63cb0ac2abe83344af865017aa34946eabe4c8024ae2431ebff` |
| `biosmod.layout` | Layout que cubre solo el bloque modificado | `a4d8932b7ac3573ca0f7332a8acecb46f442dc24331d1edca0576945db55ebae` |

Scripts: `patch_bios.py` (genera la imagen), `verify_layout.py` (valida todo),
`lzma_test.py` (prueba de recompresión), `search_strings.py` (búsqueda de
cadenas en el árbol UEFI).

## Siguiente paso

La escritura **no se ha realizado**. Cuando se decida, la opción menos arriesgada
por software es escribir solo el bloque modificado:

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod -w flash_image_12m.bin -N
```

Antes de hacerlo, leer [`03-flasheo-y-recuperacion.md`](03-flasheo-y-recuperacion.md)
y [`04-riesgos.md`](04-riesgos.md). Sin programador SPI, un fallo de
escritura puede dejar el portátil sin arrancar.

## Alcance del parche

El parche **no añade una tarjeta concreta**: elimina la comprobación para
cualquier tarjeta WLAN/WWAN PCIe. El Bluetooth USB de este modelo no se valida
(el tipo 2 devuelve éxito si no está en la tabla), así que la mitad BT de una
combo no necesita parche.

# 04 — Riesgos del flasheo

## 1. Alcance de la escritura

Con la opción recomendada (`biosmod.layout`):

```
0x00820000 - 0x00A03FFF   (~1,98 MB)
```

Quedan fuera:

- descriptor (`0x000000-0x000FFF`)
- ME (`0x001000-0x7FFFFF`)
- boot block (final de la región BIOS, sobre `0xBE0000+`)
- EC

El boot block está **lejos** del bloque escrito, así que una escritura
interrumpida en ese bloque no lo daña. Esa es la principal red de seguridad por
software.

## 2. Matriz de riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Corte de luz / cuelgue / suspensión durante erase-write | Baja con AC + batería y sin tocar el equipo | Alto: volumen corrupto, posible no-POST | AC + batería, suspensión desactivada, no tocar nada |
| `flashrom` falla a mitad (ME/SMM, write-protect, chip) | Baja; FREG1 BIOS es read-write | Alto: escritura parcial | Usar layout de 2 MB; `-N`; no reescribir los 4 MB |
| El BIOS rechaza el módulo parcheado (CRC/checksum/firma) | Muy baja: CRC32 y checksums validados; hay mods conocidos de H3ET72WW | Medio: no-POST o whitelist activo | Validación estructural; boot block intacto |
| Efecto secundario del parche | Baja | Bajo: la tarjeta no se inicializa o el setup muestra datos raros | El parche solo cambia la rama de error; no toca la tabla |
| El AX210 no funciona por hardware | Media | Ninguno para el portátil; no se logra el objetivo | Revisar adaptador, alimentación, antenas MHF4, cable USB |
| Brick sin recuperación por software | Deriva del primer fallo | Muy alto: portátil fuera de servicio | CH341A + clip SOIC-8 antes de escribir |

## 3. Escenarios detallados

### 3.1 Corte de luz o cuelgue

Es el riesgo principal. Si ocurre durante el erase o el write, el bloque queda
incompleto. El boot block sigue intacto, pero el volumen principal puede no
cargar y el equipo puede no llegar al POST.

Mitigación:

- portátil enchufado y con batería;
- suspensión desactivada;
- no ejecutar actualizaciones ni cargas pesadas;
- no cerrar la tapa ni desconectar nada;
- opcionalmente, arrancar desde un USB live mínimo para reducir procesos.

### 3.2 Fallo de `flashrom` o del chipset

`flashrom` ya reportó:

```
FREG1: BIOS region (0x00800000-0x00bfffff) is read-write.
```

Pero la región ME está bloqueada y el chipset usa hardware sequencing. `-N` es
necesario. Si el erase/write falla a mitad, `flashrom` puede abortar con el
bloque parcialmente escrito.

Mitigación: usar el layout de 2 MB (no el full-region de 4 MB) y no reintentar
a ciegas si hay un error; primero restaurar la imagen original si el equipo
sigue arrancando.

### 3.3 Imagen rechazada por el BIOS

Se validó:

- CRC32 de la sección GUIDed: `0x9C728A34`, válido;
- checksums FFS internos: `CB`/`8B`, válidos;
- checksums FFS externos: `65`/`D6`, válidos;
- el volumen descomprimido solo difiere en 3 rangos.

No se ha encontrado un checksum de región completa ni firma de BIOS. Los mods
conocidos para `H3ET72WW` funcionan, lo que respalda que el boot block no
verifica una firma del volumen.

Riesgo residual: que el decodificador LZMA de Phoenix sea más estricto que el
de Python/UEFIExtract. Se conservó la cabecera `.lzma` original y el tamaño
descomprimido; el stream es LZMA1 estándar. El riesgo es bajo.

### 3.4 Efectos secundarios del parche

El parche salta la rama de error de `FUN_00000bd0`. En el camino "no
encontrada" no se actualiza `LenovoScratchData`. Es un registro auxiliar; no
debería afectar al arranque ni a la inicialización PCIe. El peor caso razonable
es que la tarjeta no se inicialice o que el setup muestre datos raros; no es un
brick.

### 3.5 Hardware de la tarjeta

Independiente del brick:

- el adaptador NFHK N-30U V4 debe estar bien asentado en la ranura WLAN
  full-size;
- el AX210 necesita antenas MHF4;
- el Bluetooth necesita el cable USB del adaptador;
- la WiFi 6E de 6 GHz puede rendir poco con antenas de 2012; 2.4/5 GHz deberían
  funcionar.

Si algo de esto falla, el portátil sigue funcionando; simplemente no se logra
el objetivo.

### 3.6 Recuperación

- **Si el equipo sigue arrancando:** se puede reflashear la región original
  (`docs/03-flasheo-y-recuperacion.md`, sección 6).
- **Si no arranca pero el boot block está intacto:** crisis recovery de Phoenix
  (Fn+B / Win+B, USB con `.FL1`, `PHLASH16` en DOS). No garantizado.
- **Si el boot block o el chip quedan mal:** hace falta un programador SPI.
  `orig_bios_region.bin` no sirve como volcado completo (descriptor/ME a cero);
  hay que volcar el chip completo con el programador.

## 4. Valoración global

- **Probabilidad de brick:** baja en condiciones normales (AC + batería, sin
  interrupciones, escritura de 2 MB). No hay un número oficial; depende de la
  estabilidad del equipo y del chip.
- **Impacto:** alto, porque sin programador SPI la recuperación no está
  garantizada.
- **Riesgo de que la imagen esté mal construida:** muy bajo; validada
  estructuralmente y con CRC/checksums correctos.
- **Riesgo de que la tarjeta no funcione:** medio, pero no afecta a la
  integridad del portátil.

## 5. Opciones

### A. Esperar al CH341A (recomendado)

Comprar un CH341A + clip SOIC-8 (5-10 €), volcar el chip completo antes de
escribir y tener una copia de seguridad. Convierte un posible brick en un
contratiempo recuperable.

### B. Flashear por software con el layout

Aceptar el riesgo residual. Usar el comando de 2 MB, con AC y batería, sin
interrupciones. Si falla y el equipo no arranca, intentar crisis recovery.

### C. No flashear

Usar una tarjeta que ya esté en la tabla, por ejemplo la **Intel Centrino
Wireless-N 2230** (`8086:0888`), que funciona sin modificar el BIOS. Es la
opción más segura si el objetivo es solo tener WiFi mejor que la BCM43228.

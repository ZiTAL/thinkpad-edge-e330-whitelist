# 03 — Flasheo, verificación y recuperación

## 0. Estado

**No se ha escrito nada en la flash.** El equipo sigue con el BIOS original
H3ET72WW (1.09). Este documento describe el procedimiento para cuando se decida
flashear.

## 1. Antes de empezar

- Conectar el **cargador** y dejar la **batería puesta y cargada**. El portátil
  actúa como SAI si hay un corte de luz.
- Cerrar navegadores, actualizaciones y cualquier proceso pesado.
- Desactivar la suspensión automática.
- No tocar el equipo, no cerrar la tapa, no desconectar nada durante el proceso.
- Tener a mano `bios_region.bin` y `flash_image_12m.bin`.
- Idealmente, tener un **CH341A + clip SOIC-8** y un volcado completo del chip
  antes de escribir.

Duración estimada de la escritura: **1-2 minutos** (erase + write + verify de
~2 MB).

## 2. Qué se escribe

La opción recomendada escribe solo este bloque:

```
0x00820000 - 0x00A03FFF   (~1,98 MB)
```

Contiene el volumen comprimido con `LenovoWmaPolicyDxe`. **No toca**:

- descriptor (`0x000000-0x000FFF`)
- región ME (`0x001000-0x7FFFFF`)
- boot block (al final de la región BIOS, sobre `0xBE0000+`)
- EC

La opción alternativa reescribe los 4 MB completos de la región BIOS. Es más
superficie de fallo y no aporta nada en este caso.

## 3. Comando recomendado (solo bloque modificado)

```bash
cd /home/projects/thinkpad-edge-firmware
sudo flashrom -p internal -l biosmod.layout -i biosmod -w flash_image_12m.bin -N
```

`biosmod.layout`:

```
00820000:00a03fff biosmod
```

### Por qué así

- `-l biosmod.layout -i biosmod`: usa un layout propio y escribe solo ese rango.
- `-w flash_image_12m.bin`: la imagen de 12 MB; `flashrom` toma del fichero los
  bytes del rango incluido.
- `-N` (`--noverify-all`): imprescindible con la región ME bloqueada; evita
  verificar regiones no incluidas. La región incluida sí se verifica.

### Lo que verás

```
Found chipset "Intel HM77".
...
Using region: "biosmod".
Erasing and writing flash chip... Erase/write done.
Verifying flash... VERIFIED.
```

Si aparece `VERIFIED`, la escritura y la verificación han ido bien.

## 4. Alternativa (región BIOS completa)

```bash
sudo flashrom -p internal --ifd -i bios -w flash_image_12m.bin -N
```

Reescribe los 4 MB de la región BIOS (incluido el boot block). Es la opción
clásica, pero más arriesgada ante una interrupción.

## 5. Después de flashear

1. Apagar el equipo (`sudo poweroff`), no reiniciar en caliente.
2. Encender y entrar al BIOS si hace falta comprobar que no sale el 1802.
3. Arrancar Linux y comprobar:

```bash
# WiFi AX210
lspci -nn | grep -i 8086:2725
dmesg | grep -i iwlwifi

# Bluetooth AX210
lsusb | grep -i 8087:0032
dmesg | grep -i bluetooth
```

Resultado esperado:

- `02:00.0 Network controller: Intel ... Wi-Fi 6E AX210 [8086:2725]`
- `Bus ... ID 8087:0032 Intel Corp. AX210 Bluetooth`
- Sin `1802` en el POST.

Si la WiFi aparece pero el Bluetooth no, revisar:

- cable USB del adaptador conectado a un puerto USB;
- que el adaptador esté bien asentado en la ranura;
- que el módulo `btusb`/`btintel` esté cargado (kernel 5.8+).

Si no aparece la WiFi:

- comprobar que el adaptador está en la ranura **WLAN full-size**, no en la
  half-size de WWAN/mSATA;
- revisar antenas MHF4;
- revisar `dmesg` por errores de PCIe/enumeración.

## 6. Reversión (si el equipo sigue arrancando)

Crear una imagen de 12 MB con la región original:

```bash
cd /home/projects/thinkpad-edge-firmware
cp orig_bios_region.bin flash_image_original_12m.bin
dd if=bios_region.bin of=flash_image_original_12m.bin \
   bs=1 seek=8388608 conv=notrunc status=none
```

Y escribirla con el mismo procedimiento:

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod \
  -w flash_image_original_12m.bin -N
```

o, si se prefiere la región completa:

```bash
sudo flashrom -p internal --ifd -i bios \
  -w flash_image_original_12m.bin -N
```

`flash_image_original_12m.bin` no está incluido en el proyecto; se genera con
los dos comandos de arriba.

## 7. Recuperación si no arranca

### 7.1 Crisis recovery de Phoenix (software)

El boot block no se toca con la opción recomendada. Si el volumen principal
queda corrupto, el boot block puede intentar recuperar desde USB.

Métodos documentados para Phoenix/ThinkPad:

- **Fn+B** (o **Win+B**) mantenido mientras se conecta la alimentación.
- USB preparado con el BIOS oficial (`.FL1` / `.WPH`) y, según el método,
  `PHLASH16.EXE` + `MINIDOS.SYS` en DOS.
- El paquete oficial del E330 es `h3uj54ww.exe` (Lenovo), que contiene el
  firmware y el flasher; también existe el `h3uj05ww.exe` antiguo.

Notas:

- No está garantizado en el E330; depende del boot block y del medio.
- No quitar la batería antes de intentar la recuperación (el flasher de Lenovo
  comprueba alimentación).
- El nombre exacto del fichero y el combo de teclas pueden variar; consultar el
  hilo de bios-mods del E330 y la documentación de Phoenix crisis recovery.

### 7.2 Programador SPI (hardware)

Es la recuperación fiable:

1. Abrir la tapa inferior y localizar el chip SPI (SOIC-8).
2. Con un **CH341A** + clip SOIC-8, volcar el chip completo (12 MB) **antes**
   de escribir.
3. Guardar ese volcado como copia de seguridad.
4. Si el equipo no arranca, escribir el volcado completo de nuevo.
5. Alternativa: construir un image completa con el descriptor/ME del volcado y
   la región BIOS original o parcheada.

Importante: `orig_bios_region.bin` **no** es un volcado completo (descriptor y
ME están a cero). Para el programador hay que usar un volcado completo del chip.

## 8. Diagnóstico de fallos

| Síntoma | Causa probable | Acción |
|---|---|---|
| `flashrom` dice `BIOS region is write-protected` | ME/SMM o descriptor | Usar layout/`-N`; si persiste, programador |
| `Verifying flash... FAILED` tras escribir | Escritura incompleta o chip | Reintentar una vez; si falla, restaurar original |
| El equipo no arranca | Volumen corrupto | Crisis recovery / programador |
| Sigue saliendo 1802 | Parche no aplicado, región equivocada o BIOS actualizado después | Verificar `bios_region_patched.bin` y reflashear |
| WiFi aparece, BT no | Cable USB del adaptador, antenas, driver | Revisar cable USB y `dmesg` |
| WiFi no aparece | Adaptador mal asentado, ranura equivocada, antenas | Revisar hardware y `lspci` |

## 9. Comprobación previa sin escribir

Ya realizada:

```bash
sudo flashrom -p internal -l biosmod.layout -i biosmod -v flash_image_12m.bin
```

Salida esperada (falla solo en los bytes parcheados, porque aún no está
flasheado): ver `../evidence/flashrom_layout_verify.txt`.

También se comprobó el probe:

```bash
sudo flashrom -p internal
```

`FREG1: BIOS region (0x00800000-0x00bfffff) is read-write` — la región BIOS es
escribible por software según el descriptor.

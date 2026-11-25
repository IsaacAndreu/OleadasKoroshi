# Plan de actualización de los módulos KOROSHI (17/11/2026, v3)

v3: el servidor ya tiene instalado todo el plan v2 y algo más. Hoy solo quedan **tres módulos en dos tandas**. La v1
y la v2 de este plan se quedan como estaban.

## Estado del servidor

Leído en nath.tuctuc.com el 17/11 por la tarde (solo lectura, `ir.module.module`). En todos los módulos
`installed_version` = `latest_version`, así que no hay ninguna actualización a medias.

| Módulo | Servidor | Repo | Qué hacer |
|---|---|---|---|
| koroshi_faltantes | 1.6.1 | **1.7.0** | Tanda A |
| koroshi_preparacion | 3.32.0 | **3.33.0** | Tanda A (con faltantes) |
| koroshi_monitor | 1.32.0 | **1.33.0** | Tanda B |
| koroshi_base | 1.0.0 | 1.0.0 | Al día |
| koroshi_operarios | 2.18.1 | 2.18.1 | Al día |
| koroshi_kpi | 1.9.0 | 1.9.0 | Al día |
| koroshi_warehouse_map | 0.1.20261116.46 | .46 | Al día |
| koroshi_consumibles | 1.4.0 | 1.4.0 | Al día |
| koroshi_xpo_bultos | 1.3.0 | 1.3.0 | Al día |
| koroshi_pda_app | 1.1.0 | 1.1.0 | Al día |
| koroshi_caja_existente | 1.4.0 | 1.4.0 | Al día |
| koroshi_zonas | 1.4.0 | 1.4.0 | Al día (sigue en sombra) |
| koroshi_informe | 1.2.0 | 1.2.0 | Al día |
| koroshi_menu | 2.4.1 | 2.5.0 | **Se queda en 2.4.1: NO instalar la 2.5.0** |
| koroshi_s4t_envios | 1.3.0 | 1.3.0 | Al día |
| koroshi_s4t_sync | 1.0.0 | 1.0.0 | Al día |
| koroshi_sesiones | 1.0.0 | 1.0.0 | Al día |
| koroshi_contenedores | 1.4.0 | 1.4.0 | Al día |
| koroshi_rendiment | 1.1.0 | 1.1.0 | Al día |

**No se instalan todavía** (decidido): koroshi_actividades, koroshi_s4t_traspasos, koroshi_delegacion y
koroshi_menu 2.5.0.

Cada versión parte de la que hay en el servidor:
- faltantes 1.7.0 sale de 1.6.1;
- preparacion 3.33.0 sale de 3.32.0;
- monitor 1.33.0 sale de 1.32.0 (solo `controllers/envios.py`, el manifest y el README).

`python bin/comprobar.py` sobre los tres: 0 errores y 0 avisos.

| ZIP en `bin/` | sha256 (16 primeros) |
|---|---|
| 20261117_koroshi_faltantes_v1.7.0.zip | 290b3128cce85e40 |
| 20261117_koroshi_preparacion_v3.33.0.zip | eeb0ebf5d1c37ed3 |
| 20261117_koroshi_monitor_v1.33.0.zip | 4dae299fb56f73aa |

## Lo que no puede salir mal

1. **Una actualización cada vez.** Primero la tanda A entera y comprobada; después la B. Si se lanzan dos
   actualizaciones a la vez sale «Failed to load registry» y la PDA se queda fuera (pasó el 17/11). Si una actualización
   tarda, no se reintenta en paralelo.
2. **Tanda A, faltantes y preparacion juntas.** preparacion 3.33 llama a funciones que solo existen en faltantes 1.7.
   Si solo se instala una, la ronda falla en Lecturas.
3. **Actualizar justo después del reinicio.** faltantes 1.7.0 añade columnas a `koroshi_faltante` (`ronda_resultado`,
   `ronda_operario_id`, `ronda_fecha`, `move_cero_id`) y quita el «obligatorio» de la OUT. Mientras Odoo corre con el
   código nuevo sin actualizar, falla todo lo que lee faltantes, y eso incluye el botón Faltante de Lecturas.
   - Solo cambia la tabla propia `koroshi.faltante`. No toca `stock.picking`, `stock.picking.type` ni
     `stock.move.line`.
4. **Fuera de horario.** Al actualizar se cierran las sesiones abiertas durante unos minutos («Sesión expirada»). Hay
   que evitar los crons de las 21:30 UTC (KPI) y de las 03:50, 04:00 y 04:30 UTC (zonas). Buena ventana: de 17:30 a
   21:00, hora del almacén, sin nadie en las PDA.

## Pasos (los ejecuta el responsable; cada uno con su visto bueno)

**Tanda A: koroshi_faltantes 1.7.0 + koroshi_preparacion 3.33.0**

Subir los dos ZIP, comprobar el sha256 y después:
```bash
bash desplegar.sh check koroshi_faltantes 1.7.0 koroshi_preparacion 3.33.0
```
Si el check sale OK:
```bash
sudo AUTO_CONFIRM=1 bash desplegar.sh install koroshi_faltantes 1.7.0 koroshi_preparacion 3.33.0
```
**Nada más arrancar Odoo**, en Aplicaciones › Actualizar lista › koroshi_faltantes › **Actualizar**. Basta con un clic,
porque preparacion depende de faltantes y Odoo la actualiza en la misma pasada.

Comprobar en Aplicaciones (o por RPC) que salen `13.0.1.7.0` y `13.0.3.33.0`, con `installed_version` =
`latest_version`.

**Tanda B: koroshi_monitor 1.33.0**, solo cuando la A esté comprobada:
```bash
bash desplegar.sh check koroshi_monitor 1.33.0
```
```bash
sudo AUTO_CONFIRM=1 bash desplegar.sh install koroshi_monitor 1.33.0
```
Nada más arrancar: koroshi_monitor › **Actualizar**.

## Después

- En el log no tiene que salir «Failed to load registry», «Unmet dependencies» ni «Some modules are not loaded».
- Ctrl+F5 en los PC y en la tele, y recargar todas las PDA.
- **Faltantes**:
  - menú Faltantes › «Resultado de las rondas» (lista vacía, con el botón Imprimir);
  - en la lista de faltantes, los filtros nuevos y el estado «Ubicación no existe».
- **Puestos a 0 del picking viejo**: menú «Pasar los puestos a 0 a faltantes» (solo managers). Es una acción que
  hace la oficina cuando decida, no forma parte de la actualización.
  - La simulación de solo lectura del 17/11 daba 191 líneas (332 uds).
  - No mueve stock: solo crea faltantes de tipo «Puesto a 0».
- **Monitor 1.33.0**: en Consulta de envíos › Tiendas, descargar el Excel XPO del 17/11. K1 tiene que dar 7 bultos y
  «SÍ», y la OUT 26077 tiene que salir en «Observación».

## Qué probar en una PDA real (con «Almacén Nath»; en OUT reales solo leer y deshacer)

- Lecturas normal: leer tarjeta, sale la OUT, leer una prenda y la lectura aparece. No tiene que cambiar nada.
- Botón Faltante en una OUT normal: sigue saliendo y solo propone lineales y muelle (como en la 1.6.1).
- **Ronda pequeña de prueba** (1 o 2 faltantes, creada desde Faltantes › Crear ronda):
  - leer la INT de la ronda en Lecturas: se abre como una OUT y va a la ubicación de destino;
  - en vez de «Faltante» salen «No está» y «La ubicación no existe», y piden dos toques;
  - leer la prenda = está; «No está» = la línea desaparece y pasa a la siguiente;
  - con todo marcado, Validar: sale «Ronda X terminada» y en «Resultado de las rondas» aparecen el operario, la hora
    y el resultado de cada línea.
- Si algo falla en la ronda, las OUT normales no se ven afectadas. La ronda solo se activa con una INT cuyo origen
  empieza por «RONDA FALTANTES».

## Qué no se ha podido probar

- La ronda en una PDA real y en el servidor: faltantes 1.7.0 y preparacion 3.33.0 no están instaladas en ningún sitio.
  El JS solo se ha comprobado de sintaxis, no en un navegador con el módulo cargado.
- El Excel de monitor 1.33.0 en el servidor. Se ha probado en local y simulando con datos reales del 12 al 17/11.

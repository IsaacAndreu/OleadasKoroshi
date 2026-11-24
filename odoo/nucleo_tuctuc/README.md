# Núcleo de Odoo cambiado en tuctuc (odoo.tuctuc.com)

Archivos de `/opt/tuctuc-erp/odoo13/addons` que se han cambiado **en su propio código** (decisión de Isaac,
24/11/2026: arreglar el código, no poner módulos encima). `odoo13` es una copia de git del Odoo 13 de la comunidad que
ya tenía 12 archivos cambiados a mano por otros; estos tres estaban sin cambios locales.

**Si alguien actualiza o restaura `odoo13` con git (`git pull`, `git checkout -- .`), estos cambios se pierden.**
Volver a copiarlos desde aquí (y, para Previsto, volver a crear la vista: abajo).

Punto de partida: commit `da2223c` (copia exacta del servidor, 24/11/2026). El cambio es el commit siguiente;
`git diff da2223c -- odoo/nucleo_tuctuc` enseña exactamente qué líneas se han tocado.

| Archivo | Qué | Antes | Después | Cómo entra |
|---|---|---|---|---|
| `addons/stock/models/stock_quant.py` (`_get_quants_action`) | Botón **Stock** e Inventario > Stock ya no llaman a `_quant_tasks()` | +11,7 s por clic (9,4 + 2,3 s) y escribía en `stock_quant` | sin esos 11,7 s | reinicio |
| `addons/stock/report/report_stock_quantity.py` | **Previsto**: el CTE `WITH forecast_qty` pasa a subconsulta (mismo SQL que en nath, comprobado sin espacios) | minutos | en nath 220 s -> 0,15 s | rehacer la vista a mano (abajo) |
| `addons/stock/models/stock_move_line.py` (`product_id`) | `index=True`: **trazabilidad** / movimientos de un producto | ~1 s por consulta, tabla entera (19 M filas) | ms | índice a mano con `CONCURRENTLY` (abajo) |

### Búsqueda por stock (`qty_available = N`, `< N`, `!= 0`...) — 24/11/2026, 2.º paquete

| Archivo | Qué |
|---|---|
| `addons/stock/models/product.py` (`_search_qty_available`) | Sin fechas en el contexto, ya no va a `_search_product_quantity` (calcula el stock de los 306.743 productos uno a uno: ~19 min) sino a `_buscar_stock_por_quants`: suma de quants en SQL con el mismo dominio y reglas, redondeo por unidad de medida, servicios a 0. Gancho `_productos_stock_aparte`. «> 0» (ya rápida) no cambia |
| `addons/mrp/models/product.py` (`_productos_stock_aparte`) | Kits (bom phantom), calculados como siempre: se buscan primero las boms (0,2 s) en vez de pasar todos los productos a `_get_product2bom` (113 s). Mismos 1.510 kits |

Entra con un reinicio (solo Python). Punto de partida `a3a00be`; prueba en real:
`bin/versiones/20261124_prueba_buscar_stock_codigo_nuevo_ROLLBACK.py`.

`_quant_tasks` (fusionar quants duplicados y borrar los que quedan a cero) lo sigue haciendo el planificador
(`stock_rule.py`, `run_scheduler`) y `custom_addons/procurement_ext`. Medido el 23/11: 0 grupos duplicados y 29
quants a cero.

## Instalar (solo con el sí de Isaac)

1. Copia de seguridad de los tres archivos del servidor y copiar los nuevos (dueño `ubuntu:ubuntu`).
2. **Índice antes del reinicio**, sin bloquear la tabla (tarda unos minutos; no va dentro de una transacción):
   ```sql
   SET statement_timeout = 0;
   CREATE INDEX CONCURRENTLY IF NOT EXISTS stock_move_line_product_id_index ON stock_move_line (product_id);
   SELECT indisvalid FROM pg_index WHERE indexrelid = 'stock_move_line_product_id_index'::regclass;  -- t
   ```
   Con el nombre que usa Odoo (`<tabla>_<campo>_index`): al actualizar `stock`, Odoo lo encuentra y no lo vuelve a
   crear (sin `CONCURRENTLY` bloquearía las escrituras de la tabla durante minutos). Si se corta, queda `INVALID`:
   `DROP INDEX CONCURRENTLY stock_move_line_product_id_index;` y repetir.
3. **Vista de Previsto**: no se actualiza `stock` (arrastra a cientos de módulos). Se crea a mano con la consulta de
   `init()` del archivo nuevo (`CREATE or REPLACE VIEW report_stock_quantity AS (...)`): mismas columnas, no toca datos.
4. `sudo systemctl restart tuctuc-erp` (nunca stop + start).

## Volver atrás

Copiar los archivos de la copia de seguridad y reiniciar. Previsto: volver a crear la vista con la consulta vieja
(la de `da2223c`). El índice no cambia ningún resultado; si se quiere quitar: `DROP INDEX CONCURRENTLY
stock_move_line_product_id_index;` y quitar el `index=True` (si no, Odoo lo vuelve a crear al actualizar `stock`).

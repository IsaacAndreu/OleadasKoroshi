# TUCTUC Rendimiento (Odoo 13, odoo.tuctuc.com)

Arreglos de lentitud de **odoo.tuctuc.com** (BD `TUCTUC_PRODUCTION`), con el método de
[koroshi_rendiment](../koroshi_rendiment/README.md): medir en el log, encontrar la consulta y arreglarla dando el
mismo resultado. Todo lo medido el 23/11/2026 fue de solo lectura.

| Versión | Qué | Antes | Después |
|---|---|---|---|
| índice (a mano) | **Trazabilidad**: movimientos de un producto | 1 s por consulta, toda la tabla (19 M filas, 11 GB) | ms (sin medir: el índice aún no existe) |
| 1.0.0 | Botón **Stock** de la ficha | +11,7 s por clic (9,4 + 2,3 s) y escribe en `stock_quant` | sin esos 11,7 s |
| 1.0.0 | Botón **Previsto** | minutos (en nath 220 s, mismo SQL) | en nath 0,15 s |
| 1.0.0 | Cualquier búsqueda (multi_search_with_comma) | +1 consulta por `search()` | 0 |

## Entorno

- VM `tuctuc-erp-prod-eu-w1b`, servicio `tuctuc-erp`, config `/opt/tuctuc-erp/tuctuc-erp.conf`,
  `workers = 29`, `limit_time_real = 9999`. Addons: `/opt/tuctuc-erp/odoo13/addons`, `nath/enterprise-addons`,
  `nath/custom_addons`. PostgreSQL 11 en otro host, sin `pg_stat_statements`.
- `stock_move` 20,6 M filas, `stock_move_line` 19,1 M (11 GB), `stock_quant` 6,5 M, `stock_valuation_layer` 13,5 M,
  `product_product` 364 k.
- Log: `/var/log/odoo/tuctuc-erp.log` (rota cada día a las 06:25). El awk del ranking es el de koroshi_rendiment.

## Qué hay medido (log del 23/11/2026, 06:25-11:30)

| Ruta | Tiempo | Consultas por llamada | Quién | Causa |
|---|---|---|---|---|
| `product.product/search_read` | 480-1.237 s | 34.700-115.000 | IP distintas (tiendas): TPV al abrir | bucle de consultas; sin localizar |
| `stock.quant/web_read_group` | 301-357 s | 109.000-111.000 | una IP (84.78.198.137) | bucle; candidato: `value` (abajo) |
| `/web/action/run` | 1.089 s | 60.984 | 5.224.41.1 | sin localizar |
| `/web/dataset/search_read` | 848 s | 20.614 | 46.24.177.93 | el log no dice el modelo |
| `/web/dataset/call_button` | 145 s | 44.464 | 84.78.198.137 | sin localizar |
| `queue_job/runjob` | hasta 2.249 s | ~4.100 | trabajos | sin mirar |

Muchas consultas por llamada = un bucle que consulta fila a fila. El log no dice qué consulta; para verlo se
muestreó `pg_stat_activity` cada segundo durante una hora (solo lectura, `/tmp/tuctuc_muestras2.txt` en la VM).

## 1.0.0 — Previsto

Igual que koroshi_rendiment 1.0.0. El cuerpo del CTE de `odoo13/addons/stock/report/report_stock_quantity.py` del
servidor de tuctuc es idéntico al de nath (md5 sin espacios `19855883ff851244cbbf85d5ba07d98c` en los dos) y la vista
instalada tiene el `WITH forecast_qty`. `stock_enterprise` solo añade `read_grid` y `action_open_moves`.
**No se ha comparado el resultado en tuctuc** (la vista vieja tarda minutos y carga la BD); se apoya en la prueba de
nath (185 = 185 filas, 0 diferencias) y en que el SQL es el mismo.

## 1.0.0 — Botón Stock

`stock.quant._get_quants_action` (`stock/models/stock_quant.py:616`) llama a `_quant_tasks()`: `_merge_quants` (`:518`)
y `_unlink_zero_quants` (`:502`). Medido con los SELECT equivalentes: duplicados 9,4 s (0 grupos), quants a cero
2,3 s (29). Desde los botones se salta; el planificador (`stock_rule.py:492`) y `custom_addons/procurement_ext`
(`procurement_group.py:72`) siguen llamándolo.

## 1.0.0 — multi_search_with_comma

`custom_addons/multi_search_with_comma/models/multi_search.py:30` pregunta a `ir_module_module` si él mismo está
instalado en cada `_where_calc`, es decir, en cada búsqueda de cualquier modelo (visto en `pg_stat_activity`). Este
módulo vuelve a poner la misma función, línea por línea (sangría comprobada en el servidor), mirando
`registry._init_modules`. No se corrige nada más para no cambiar resultados.

## Índice de trazabilidad (a mano, no va en el módulo)

`stock_move_line` no tiene índice por `product_id` (sí por `move_id`, `picking_id` y `company_id`). El botón de la
ficha (`stock/models/product.py:455`, dominio `product_id = X`) y el de la plantilla (`:794`) recorren la tabla
entera: `Parallel Seq Scan`, 0,97 s y 3,3 GB leídos de memoria por consulta, con 7 núcleos. Desde el 02/09/2026,
748.684 lecturas completas o casi de `stock_move_line` (`pg_stat_user_tables`).

SQL y comprobaciones: [doc/indice_stock_move_line.sql](doc/indice_stock_move_line.sql). Con `CONCURRENTLY` y un nombre
propio (Odoo 13 borra `stock_move_line_product_id_index` al actualizar `stock` si el campo no tiene `index=True`).

## Visto y sin arreglar (siguientes versiones)

- **Stock agrupado** (`stock.quant/web_read_group`, 109.000 consultas): `stock_account/models/stock_quant.py:45`
  hace, si la vista pide `value`, un `search` por grupo y calcula `value` quant a quant (`:15`). Es el candidato, pero
  no está confirmado: hace falta saber qué pantalla y qué agrupación usa esa persona.
- **Reserva y validación**: el muestreo cazó una transacción de más de un minuto que repite
  `stock_location ... parent_path like '7/8/413465/%'` + `stock_quant ... location_id in (cientos de ids)`:
  `_gather` resuelve el `child_of` del almacén en cada movimiento.
- **TPV al abrir** (`product.product/search_read`, 34.700 consultas): `style_management` sustituye
  `product.product.name_get` (`custom_addons/style_management/models/product_template.py:145`) y escribe una línea de
  log en cada llamada (10.675 hoy).
- `stock_quant` se ha leído entera 858.992 veces desde el 02/09; falta saber qué consulta.
- `limit_time_real = 9999`: una petición lenta ocupa uno de los 29 workers sin límite.

## Instalar (solo con el sí de Isaac)

`bin/desplegar.sh` está escrito para nath; para tuctuc hay que pasarle las rutas por el entorno:

```bash
# 1. Subir bin/AAAAMMDD_tuctuc_rendimiento_v1.0.0.zip y bin/desplegar.sh a /home/it_nath_group en la VM de tuctuc
ADDONS_DIR=/opt/tuctuc-erp/nath/custom_addons ODOO_SERVICE=tuctuc-erp BACKUP_DIR=/opt/tuctuc-erp/copias_modulos \
  bash desplegar.sh check tuctuc_rendimiento 1.0.0
sudo AUTO_CONFIRM=1 ADDONS_DIR=/opt/tuctuc-erp/nath/custom_addons ODOO_SERVICE=tuctuc-erp \
  BACKUP_DIR=/opt/tuctuc-erp/copias_modulos bash desplegar.sh install tuctuc_rendimiento 1.0.0
# 2. Odoo: Aplicaciones > Actualizar lista > TUCTUC Rendimiento > Instalar (fuera de horas: reinicia el servicio)
```

El índice va aparte, cuando se quiera, con `doc/indice_stock_move_line.sql` (no necesita reinicio).

## Volver atrás

Desinstalar el módulo y reiniciar `tuctuc-erp` (la función de multi_search_with_comma vuelve con el reinicio). La
vista de Previsto se queda con esta versión (da lo mismo) hasta que se actualice `stock`. **Si alguien actualiza
`stock`, Previsto vuelve a tardar minutos: actualizar `tuctuc_rendimiento`.** El índice: `DROP INDEX CONCURRENTLY`.

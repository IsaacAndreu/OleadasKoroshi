# KOROSHI Rendimiento (Odoo 13)

Arreglos de lentitud medidos en producción. Cada arreglo da **el mismo resultado** que el
estándar (comprobado con datos reales antes de instalar) y solo cambia **cómo** se calcula.

| Versión | Qué | Antes | Después |
|---|---|---|---|
| 1.0.0 | Botón **Previsto** de la ficha de producto | 220-265 s | 0,15 s |
| 1.0.0 | Botón **Stock** (a mano) de la ficha de producto | 3,5 s | 0,4-0,7 s |
| 1.1.0 | **PDA**: productos del albarán al abrirlo (código de barras) | 5,3 s | 0,2 s |

Instalado en producción el 12/11/2026 (1.0.0 instalada, 1.1.0 actualizada).

## Entorno (lo que condiciona todo)

- Odoo 13 Enterprise **anterior** a la rama 13.0 actual de GitHub: el código del servidor no es el
  de GitHub (p. ej. no existe el parámetro `stock.skip_quant_tasks` y la vista de previsión es otra).
  **Copiar siempre el SQL/código del servidor**, nunca de GitHub.
- **PostgreSQL 11.22** en otro host (no hay usuario `postgres` local). Credenciales en
  `/opt/nath-erp/nath-erp.conf`, base `NATH_PRODUCTION`.
- `workers = 16`, `limit_time_real = 9999`: una petición lenta ocupa un worker sin límite.
- Volumen: `stock_move` 3,9 M filas, `stock_move_line` 3,7 M, `stock_quant` 1,46 M,
  `stock_location` 527 k (119.503 activas con código de barras), `product.barcode` 463 k.

## 1.0.0 — Previsto

`report.stock.quantity` es una **vista SQL** (`odoo13/addons/stock/report/report_stock_quantity.py:28`)
con `WITH forecast_qty AS (...)`. En **PostgreSQL < 12 un CTE se calcula siempre entero**: calculaba la
previsión de todos los productos de todas las compañías (≈ 4.800 M filas estimadas en el EXPLAIN) y
al final filtraba `product_id = X`.

Arreglo (`models/report_stock_quantity.py`): la misma consulta, letra por letra, como subconsulta
`FROM (...) AS forecast_qty`. PostgreSQL mete el filtro por producto dentro de cada parte del
`UNION` y usa los índices. Se mantiene `UNION` (no `UNION ALL`) para no cambiar el resultado.

Prueba en producción (solo lectura, tablas temporales) con el producto 750090: vista actual 220 s,
SQL nuevo 36 ms, 185 = 185 filas y 0 diferencias en los dos sentidos (`EXCEPT`).

## 1.0.0 — Stock

`stock.quant._get_quants_action` (`odoo13/addons/stock/models/stock_quant.py:616`) ejecuta
`_quant_tasks()` en cada clic: `_merge_quants` (`:518`, un `GROUP BY` sobre toda `stock_quant`) y
borrado de quants a cero. **Además escribe en cada clic.**

Arreglo (`models/stock_quant.py`): desde los botones se salta con una marca en el contexto. El
planificador (`odoo13/addons/stock/models/stock_rule.py:492`) llama sin la marca y sigue haciéndolo.
Comprobar que la acción planificada *Procurement: run scheduler* está activa.

## 1.1.0 — PDA, productos del albarán

La PDA pide los productos del albarán con
`stock_barcode_optimization.get_all_products_by_barcode(picking_id)` (filtro `('barcode', '!=', False)`
+ `id in [...]`). El módulo OCA `product_multi_barcode/models/product_product.py:47-64` cambia
cualquier filtro sobre `barcode` por `('barcode_ids', 'in', <ids>)`: con `!= False` carga los
**463.120** códigos y hace un `IN` gigante. 4,8 s para buscar 6 productos.

Arreglo (`models/product_product.py`): `('barcode', '!=', False)` va a la columna `barcode`
(guardada). Comprobado por SQL en producción que `barcode` no vacío ⇔ tiene algún `product.barcode`
en **todos** los productos (0 / 0 / 0). Las búsquedas por un código concreto siguen por el OCA.

Nota: el OCA devuelve **0 productos** con `('barcode', '=', False)` (debería dar ~27 k). No se toca
porque cambiaría resultados en otros sitios.

## Volver atrás

Desinstalar el módulo. Stock y la PDA vuelven al estándar al momento. La vista SQL de Previsto se
queda con esta versión (da lo mismo) hasta que se actualice el módulo `stock`, que la regenera.
**Si alguien actualiza `stock`, Previsto vuelve a tardar minutos: actualizar `koroshi_rendiment`.**

Tras instalar o actualizar, cada uno de los 16 workers tarda ~4 s la primera vez que recibe una
petición (recarga el registro). Medir después de calentar.

## Cómo se buscó (para repetirlo)

El log de Odoo (`/var/log/odoo/nath-erp.log`) termina cada petición con
`<consultas SQL> <s en SQL> <s en Python>`. Agrupar por ruta da el ranking de lo lento:

```bash
sudo cat /var/log/odoo/nath-erp.log | grep -a '" 200 - ' | awk '{p=$0; sub(/.*"(GET|POST) /,"",p); sub(/ HTTP.*/,"",p); sub(/\?.*/,"",p); gsub(/\/[0-9]+/,"/N",p); n=split($0,a," "); t=a[n-1]+a[n]; c[p]++; s[p]+=t; q[p]+=a[n-2]; if(t>m[p])m[p]=t} END{for(p in c) printf "%6d %8.2f %8.1f %8.1f %6d  %s\n", c[p], s[p]/c[p], m[p], s[p]/60, q[p]/c[p], p}' | sort -k4 -nr | head -30
```

Columnas: llamadas, media s, máx s, minutos totales, consultas SQL por llamada. Muchas consultas
por llamada = bucle que consulta fila a fila; pocas consultas pero mucho tiempo = una consulta mala
(mirar su `EXPLAIN`). Los `.gz` antiguos mezclan años: para "lo de ahora" usar solo los dos últimos logs.

Luego: medir la llamada exacta por RPC desde el navegador (`/web/dataset/call_kw`, compañía 8),
partirla en trozos hasta encontrar el que tarda y, antes de cambiar nada, **probar en producción que
el resultado nuevo es idéntico** (consultas de solo lectura, tablas temporales).

## Pendiente (medido, sin tocar)

- **PDA, ubicaciones**: `stock_barcode.get_all_locations_by_barcode` manda **119.503 ubicaciones,
  17 MB, 8-10 s** cada vez que se abre un albarán (con `sudo`: de todas las compañías). Arreglarlo
  toca el JavaScript del cliente de código de barras.
- **Validar albarán** (aparcado): las OUT de KOROSHI con venta y transportista tardan **6,9 s de
  mediana** (139 en 2 días, ~26 líneas); internas 11,4 s (86 líneas). Picos de 1-3 min por
  `SERIALIZATION_FAILURE` (Odoo repite la validación entera hasta 5 veces) en `stock_picking`,
  `stock_quant` y `sale_order`. Sospechosos sin confirmar: llamada a la API de GLS (`gls_asm`) y
  XPO (`xpo_es`, ambos `rate_and_ship`) dentro de la transacción; sincronización S4T;
  `custom_addons/stock_picking_date` (campo guardado `volume` que depende de
  `move_line_ids_without_package.product_uom_qty` y `_update_picking_related_qty`, que reescriben la
  fila del albarán en cada cambio de línea; su `end_date` no es un campo real).
- `limit_time_real = 9999`: bajarlo (p. ej. 600) evitaría workers bloqueados horas (`/web/action/run`
  llegó a 8.829 s).
- `stock_location` con 527 k filas (2,4 GB) y PostgreSQL 11 sin soporte desde 11/2023.
- Vistas con `WITH` que pueden tener el problema de Previsto: `koroshi_kpi_semana`,
  `koroshi_kpi_falta_repetida`, `purchase_report`, `report_pos_orders_custom`,
  `helpdesk_sla_report_analysis`, `x_bi_sql_view_stck_pr_ean`.
- Ficha de producto: abrirla ~2,5 s (vista 1,2 s + 185 campos 1,3 s; `public_categ_ids` 0,5 s).

`doc/prova_previsio.sh`: la prueba de solo lectura que comparó la vista actual con el SQL nuevo
(EXPLAIN ANALYZE + `EXCEPT` en los dos sentidos). Sirve de plantilla para probar otras vistas.

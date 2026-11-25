# odoo.tuctuc.com: mejoras de la noche del 24/11/2026 (19:00-20:20 hora de aquí)

Hechas con el sí de Isaac («prueba todas y si las ves bien hazlas»), sin nadie trabajando. Cada una probada antes en
real con rollback (solo lectura) y comparando el resultado antes y después.

## Resumen

| # | Qué | Cambio | Antes | Después | Resultado |
|---|---|---|---|---|---|
| 1 | Lector de códigos: escanear un producto | Código propio `stock_barcode_optimization` | ~2 s por lectura (devolvía 1.170 entradas, también para un código que no existe) | **0,01-0,06 s** | Idéntico para el código leído (producto, embalaje con su cantidad y código inexistente) |
| 2 | Buscar albaranes por número u origen | Extensión `pg_trgm` + 2 índices GIN | `OUT/0012`: 10 s; origen `S001`: 17 s | **0,06 s y 0,03 s** | Mismos registros (74 y 1.339) |
| 3 | Ficha del cliente (crédito, `partner_credit_limit`) | 1 índice en `sale_order_line.order_partner_id` | 1,5 s en caliente, hasta 45 s en frío (recorría 6,2 M de líneas) | **0,24 s** | Igual |
| 4 | Ficha del cliente («Facturado», estándar) | **Nada** (solo medido) | Cliente 14260 (8,78 M€): 50 s en frío, 5,8 s en caliente | — | Propuesta aparte |
| 5 | Abrir el lector (259.126 ubicaciones con código) | **Nada**: lo decide Isaac (185.468 están vacías) | 19 s | — | — |

Reinicio a las **19:15:13 UTC** (`sudo systemctl restart tuctuc-erp`, con la protección de no reiniciar si había
trabajos que no fueran exportaciones: había 0). `active`; en el log solo el error de siempre de `query_deluxe`. No quedó
ningún trabajo de cola en «started».

## 1. Lector: `stock_barcode_optimization` (código propio)

Archivo: `/opt/tuctuc-erp/nath/custom_addons/stock_barcode_optimization/models/product_product.py` (líneas 26, 29 y
32). Copia de antes: `/opt/tuctuc-erp/copias_modulos/stock_barcode_optimization_2026-11-24_noche`.

`get_product_by_barcode(barcode)` llamaba a `_process_product_data`, que cargaba **todos** los `product.packaging` con
código (1.843, de 1.176 productos) y leía sus productos en cada lectura. Ahora pasa el código y solo carga el embalaje
con ese código. `get_all_products_by_barcode` (al abrir un albarán) no cambia.

```diff
-            result = self._process_product_data([('barcode', '=', barcode)])
+            result = self._process_product_data([('barcode', '=', barcode)], packaging_barcode=barcode)
-    def _process_product_data(self, product_search_query):
+    def _process_product_data(self, product_search_query, packaging_barcode=False):
-            [('barcode', '!=', None), ('product_id', '!=', None)],
+            [('barcode', '=', packaging_barcode) if packaging_barcode else ('barcode', '!=', None), ('product_id', '!=', None)],
```

Por qué da lo mismo: el JS (`static/src/js/client_action/abstract_client_action.js`, `_makeProductAvailable`) solo
llama si el código leído no está en `productsByBarcode`, y mezcla lo que vuelve; el código leído sale igual. Prueba:
`/tmp/intl/medir4.py` antes y después, comparando el JSON (`/tmp/antes.json` / `/tmp/despues.json`): `True` en los 3.

Volver atrás: copiar `models/product_product.py` de la copia y reiniciar.

## 2 y 3. Índices (sin código; no los borra una actualización de módulo)

Nombres distintos de `<tabla>_<campo>_index` a propósito: Odoo 13 borra ese nombre al actualizar el módulo si el campo
no tiene `index=True`. La base es Cloud SQL (PostgreSQL 11.22); el usuario de Odoo tiene `cloudsqlsuperuser` y puede
crear la extensión. `unaccent = False` en la configuración, así que Odoo busca con `name::text ilike` y el índice sirve.

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX CONCURRENTLY IF NOT EXISTS stock_picking_name_trgm_index ON stock_picking USING gin (name gin_trgm_ops);      -- 59 MB
CREATE INDEX CONCURRENTLY IF NOT EXISTS stock_picking_origin_trgm_index ON stock_picking USING gin (origin gin_trgm_ops);  -- 50 MB
CREATE INDEX CONCURRENTLY IF NOT EXISTS sale_order_line_order_partner_id_tuctuc_idx ON sale_order_line (order_partner_id); -- 264 MB
```

Los tres `indisvalid = t`. `EXPLAIN ANALYZE`: nombre 36 ms (Bitmap Index Scan en el trigrama), origen 3,6 ms, líneas
de un cliente 0,1 ms (Index Scan; antes Parallel Seq Scan de 6,2 M filas, 6,9 s). Con el ORM (`search_read` de 80 +
`search_count`, como la pantalla): 0,06 / 0,03 / 0,03 s.

Volver atrás: `DROP INDEX CONCURRENTLY <nombre>;` (no toca datos).

Siguiente con el mismo método, si se quiere: trigrama en `product_template.name`/`default_code` (búsqueda de
productos, 2,2-2,7 s). Ojo: el nombre del producto es traducible; mirar antes la consulta real con el idioma del
usuario.

## 4. «Facturado» del cliente (sin tocar)

`total_invoiced` es estándar (`account`, sobre la vista `account_invoice_report`). Crece con lo facturado: 14260
(8,78 M€) 50 s en frío / 5,8 s en caliente; 453381 (3,75 M€) 3,5 s; un cliente sin facturas 0,09 s. Opciones: quitar
el botón de la ficha para los clientes grandes, o reescribir el cálculo (riesgo medio: es contabilidad; habría que
comparar importes cliente a cliente).

## Otras cosas vistas

- En `partner_credit_limit`, `get_partner_account_move_line_debit_credit` devuelve (0, 0) para los 4 clientes probados:
  el dominio busca tipos de cuenta por nombre (`'Receivable'`, `'Payable'`). **Sin comprobar si es lo que se quiere**:
  preguntar a contabilidad.
- El vigilante de bloqueos (`/tmp/intl/vigila.sh`) se lanzó 30 min, pero sin actividad. Repetirlo en horas de tienda
  para el TPV.
- Pendiente de limpiar en el servidor: `/tmp/intl`, `/tmp/antes.json`, `/tmp/despues.json`, `/tmp/credito_antes.json`,
  `~/trgm.log`, `~/idx_sol.log` y lo del traspaso.

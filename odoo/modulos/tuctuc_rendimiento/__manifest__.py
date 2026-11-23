# -*- coding: utf-8 -*-
{
    'name': 'TUCTUC Rendimiento (stock y trazabilidad)',
    'summary': 'Previsto, botón Stock y búsquedas más rápidos en odoo.tuctuc.com (Odoo 13 + PostgreSQL 11)',
    'description': """
Arreglos de lentitud medidos en odoo.tuctuc.com (BD TUCTUC_PRODUCTION) el 23/11/2026. Cada uno da el mismo resultado
que antes; solo cambia cómo se calcula. Detalle, medidas y cómo volver atrás: README.md.

1. Previsto (report.stock.quantity): la vista SQL usa WITH forecast_qty AS (...) y en PostgreSQL 11 el CTE se
   calcula entero para todos los productos. Misma consulta como subconsulta (igual que koroshi_rendiment 1.0.0 en
   nath, donde pasó de 220 s a 0,15 s). El SQL de tuctuc es idéntico al de nath (comprobado por huella).
2. Botón Stock (stock.quant._get_quants_action): ya no ejecuta _quant_tasks en cada clic (9,4 s + 2,3 s medidos
   en tuctuc, y escribe en stock_quant). Lo siguen haciendo el planificador y procurement_ext.
3. multi_search_with_comma: su _where_calc lanza una consulta a ir_module_module en CADA búsqueda de cualquier
   modelo. Misma función, pero mira el registro ya cargado en vez de preguntar a la base de datos.

La trazabilidad (movimientos de un producto) necesita además un índice en stock_move_line.product_id, que no va en
el módulo: se crea a mano con CREATE INDEX CONCURRENTLY (doc/indice_stock_move_line.sql), con el sí de Isaac.

v1.0.0 (23/11/2026): primera versión: Previsto, botón Stock y la consulta de más de multi_search_with_comma.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'multi_search_with_comma'],
    'data': [],
    'installable': True,
    'application': False,
}

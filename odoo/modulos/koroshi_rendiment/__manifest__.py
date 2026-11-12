# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Rendimiento ficha de producto',
    'summary': 'Botones Previsto y Stock de la ficha de producto rapidos (Odoo 13 + PostgreSQL 11)',
    'description': """
Arregla dos botones lentos de la ficha de producto, sin cambiar lo que ensenan.

1. Previsto (report.stock.quantity): tardaba 220-265 s. La vista SQL estandar usa
   WITH forecast_qty AS (...). En PostgreSQL 11 un CTE se calcula siempre entero, asi que
   se calculaba la prevision de TODOS los productos y despues se filtraba por el producto.
   Aqui la vista es la misma consulta, letra por letra, pero como subconsulta: el filtro por
   producto, almacen y compania entra dentro y solo se calculan los movimientos de ese producto.

2. Stock (stock.quant._get_quants_action): tardaba 3,5 s porque en cada clic ejecutaba
   _quant_tasks (fusion de quants duplicados sobre toda stock_quant y borrado de quants a cero).
   Desde los botones ya no se ejecuta; lo sigue haciendo el planificador
   (stock.rule._run_scheduler_tasks), igual que antes.

v1.1.0: PDA (codigo de barras). Al abrir un albaran la PDA pide sus productos con
('barcode', '!=', False). product_multi_barcode cambia ese filtro por un IN con los 463.120
codigos de product.barcode: 4,5 s por albaran para 6 productos. Ahora ese filtro va a la
columna barcode (guardada, y comprobado que coincide al 100% con product.barcode): ~0,1 s.

Para volver atras: desinstalar el modulo. El boton Stock vuelve al estandar al momento; la vista SQL
se queda con esta version (da lo mismo) hasta que se actualice el modulo stock, que la regenera.
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'product_multi_barcode'],
    'data': [],
    'installable': True,
    'application': False,
}

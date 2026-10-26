# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Delegación en albaranes',
    'summary': 'Campo Delegación en los albaranes (sale de la etiqueta "Delegación ..." de la tienda) para filtrar y agrupar',
    'description': """
Añade a los albaranes el campo "Delegación" (delegación de transporte de la tienda), para poder
agrupar y filtrar en Inventario > Transferencias: Agrupar por > Delegación.

De dónde sale: de la etiqueta de contacto "Delegación BILBAO", "Delegación CASTELLBISBAL"... de la
tienda (el contacto del albarán). Para cambiar la delegación de una tienda, se cambia su etiqueta en
la ficha del contacto y sus albaranes se actualizan solos.

Al instalar se rellenan los albaranes que ya hay con una sola consulta SQL (no se recalcula uno a uno).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'post_init_hook': 'rellenar_delegaciones',
    'installable': True,
    'application': False,
}

# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Consumibles',
    'summary': 'Control sencillo de cajas y materiales fuera del stock de prendas',
    'description': """
Control de consumibles de KOROSHI que no están dados de alta como productos de
stock. Betty puede introducir los totales iniciales conocidos y registrar cada
consumo, entrada o corrección con usuario, fecha y observaciones.

El stock actual se calcula a partir del total inicial y del histórico de
movimientos. No modifica stock.quant, albaranes ni productos de Odoo.
""",
    'version': '13.0.1.1.20261102',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['base', 'stock', 'koroshi_warehouse_map'],
    'data': [
        'security/ir.model.access.csv',
        'views/consumable_views.xml',
    ],
    'installable': True,
    'application': False,
}

# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI XPO bultos',
    'summary': 'XPO: una caja que esta en varias OUT de la misma expedicion cuenta una sola vez',
    'description': """
delivery_xpo (EFFEC, custom_addons) registra una sola expedicion para todas las OUT del envio y manda a XPO
TotalUnidadesManipulacion = suma de len(picking.package_ids) de cada OUT. Si una caja esta en dos OUT
(KOROSHI Caja existente: OUT pequena metida en la caja de la OUT grande) se contaba dos veces y XPO sacaba
una etiqueta de mas (K8 10/11/2026: 16 cajas, 17 etiquetas, expedicion 121771146).

Con este modulo se cuentan las cajas DISTINTAS de toda la expedicion. Solo cambia ese numero (y el minimo de
3 bultos se mira con las cajas distintas). No toca delivery_xpo ni cambia nada si no hay cajas repetidas o
las OUT no son de EFFEC. No anade campos.
v1.0 (10/11/2026).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['delivery_xpo'],
    'data': [],
    'installable': True,
    'application': False,
}

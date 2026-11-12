# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI XPO bultos',
    'summary': 'XPO: cajas distintas y 15 kg / 0,09 m3 por bulto en cada expedicion',
    'description': """
delivery_xpo (EFFEC, custom_addons) registra una sola expedicion para todas las OUT del envio y manda a XPO
TotalUnidadesManipulacion = suma de len(picking.package_ids) de cada OUT. Si una caja esta en dos OUT
(KOROSHI Caja existente: OUT pequena metida en la caja de la OUT grande) se contaba dos veces y XPO sacaba
una etiqueta de mas (K8 10/11/2026: 16 cajas, 17 etiquetas, expedicion 121771146).

Con este modulo se cuentan las cajas DISTINTAS de toda la expedicion. Solo cambia ese numero (y el minimo de
3 bultos se mira con las cajas distintas). No toca delivery_xpo ni cambia nada si no hay cajas repetidas o
las OUT no son de EFFEC. No anade campos.
v1.0 (10/11/2026).

v1.1 (12/11/2026): XPO factura con 15 kg y 0,09 m3 POR BULTO y recibia mal los m3 y kg (delivery_xpo mandaba
15 + 1 kg/caja y el volumen de los productos, con 0,09 m3 por UNIDAD si no tenian: K80 5 bultos = 5,63 m3, 20 kg).
Ahora en todas las expediciones de EFFEC: bultos = cajas distintas, peso = 15 x bultos, volumen = 0,09 x bultos.
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['delivery_xpo'],
    'data': [],
    'installable': True,
    'application': False,
}

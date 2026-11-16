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
v1.2.0 (14/11/2026): auditoria 13/11, fase 3. bultos_de() y valores_xpo(): una sola cuenta de bultos, peso y
volumen para la expedicion XPO y para koroshi_s4t_envios (cajas distintas de las lineas con algo leido).
v1.3.0 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). La empresa sale de koroshi_base.comun. Mismo
resultado; sin campos ni vistas nuevas. Depende de koroshi_base.
""",
    'version': '13.0.1.3.0',
    'author': 'NATH',
    'category': 'Inventory',
    'license': 'LGPL-3',
    'depends': ['delivery_xpo', 'koroshi_base'],
    'data': [],
    'installable': True,
    'application': False,
}

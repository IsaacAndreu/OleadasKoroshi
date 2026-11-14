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

v1.2.0 (13/11/2026): CAJAS PARA LA PDA. Campos nuevos en el artículo: «Es una caja», nombre en la PDA, orden y
medidas (mm). Cada caja tiene su «Tipo de paquete» de Odoo (product.packaging, se crea solo). Al instalar se
marcan/crean las cajas de KOROSHI: Grande 590x390x400 (la que ya había), 600x400x400, Mediana (sin medidas: las
pone Betty) y Online 280x280x120. La preparación en Lecturas (koroshi_preparacion 3.24) las enseña al cerrar
una caja y cada caja cerrada resta 1 (consumo con la OUT, la caja y el operario). Si no hay stock, el consumo de
la PDA se apunta igual y el artículo queda «Agotado» (no para el cierre de la caja).
v1.3.0 (13/11/2026): «Avisar por correo a» en cada consumible: correo cuando el stock baja al mínimo de aviso
y cuando se agota (también con las cajas que resta la PDA).
v1.2.1 (13/11/2026): «Se elige en Lecturas». La caja Online no sale en la PDA: lo online va por INT al SORTER y no
cierra caja en Lecturas (las OUT web no llevan caja). La 1.2.0 no se instaló.
v1.4.0 (14/11/2026): auditoría 13/11, fase 2. El stock de cada artículo se suma con una consulta agrupada en la base
(antes cada caja cerrada en la PDA leía todo el histórico de movimientos). Si dos PDA restan la misma caja a la vez, el
choque ya no se traga (la caja se cerraba sin restar): Odoo repite la petición.
""",
    'version': '13.0.1.4.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'stock', 'delivery', 'koroshi_warehouse_map'],
    'data': [
        'security/ir.model.access.csv',
        'views/consumable_views.xml',
        'data/cajas.xml',
    ],
    'installable': True,
    'application': False,
}

# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Caja existente',
    'summary': 'PDA: leer la matricula CJ de una caja de la misma OUT mete las uds en esa caja (no crea otra)',
    'description': """
En la PDA, el boton de caja (dialogo "Nombre del Paquete" de stock_barcode_optimization) llama a
stock.picking.put_in_pack(package_name=...). Ese metodo siempre crea una caja nueva y le pone el nombre:
si la matricula ya existe, salia una caja duplicada (ahora la para la accion automatica 20).

Con este modulo, si la matricula CJ ya existe:
- y la caja es de ESTA OUT (sin validar): las uds leidas sin caja entran en esa caja. No se crea ninguna
  caja nueva. Las lineas con menos uds leidas que reservadas se parten como hace Odoo. Nota en la OUT.
- y la caja es de OTRA OUT: error claro (esta caja es de la OUT X, tienda K..) y no se cambia nada.
Si la matricula no existe, o no es una OUT de EFFEC, o no es CJ + 9 numeros: igual que antes.

No anade campos a ninguna tabla. No cambia la accion automatica 20 ni las agrupaciones.
v1.0 (09/11/2026).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'stock_barcode_optimization'],
    'data': [],
    'installable': True,
    'application': False,
}

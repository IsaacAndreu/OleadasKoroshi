# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Caja existente',
    'summary': 'PDA: leer la matricula CJ de una caja ya hecha (misma OUT u otra OUT del mismo pedido) mete las uds en esa caja',
    'description': """
En la PDA, el boton de caja (dialogo "Nombre del Paquete" de stock_barcode_optimization) llama a
stock.picking.put_in_pack(package_name=...). Ese metodo siempre crea una caja nueva y le pone el nombre:
si la matricula ya existe, salia una caja duplicada (ahora la para la accion automatica 20).

Con este modulo, si la matricula CJ ya existe:
- y la caja es de ESTA OUT (sin validar): las uds leidas sin caja entran en esa caja. No se crea ninguna
  caja nueva. Las lineas con menos uds leidas que reservadas se parten como hace Odoo. Nota en la OUT.
- y la caja es de OTRA OUT de otro pedido o tienda: error claro y no se cambia nada.
Si la matricula no existe, o no es una OUT de EFFEC, o no es CJ + 9 numeros: igual que antes.

No anade campos a ninguna tabla. No cambia la accion automatica 20 ni las agrupaciones.
v1.3 (10/11/2026): con la caja de OTRA OUT del mismo pedido y tienda (validada o no) las uds leidas van a esa
  caja y la OUT pequena se VALIDA como siempre, con 0 bultos. Ya no se cancela ninguna OUT ni se pasan uds
  entre OUT (una OUT cancelada en el pedido bloquea el sync S4T). La OUT duena puede volver a leer su caja
  aunque ya tenga prendas en Clientes de una OUT pequena validada antes.
v1.2 (10/11/2026): el numero de bultos se corrige tambien cuando la PDA lo escribe despues de validar
  (prueba K8: la OUT/24181 quedo con 1 bulto en vez de 0).
v1.1 (10/11/2026, cambiado en v1.3): la caja puede ser de OTRA OUT del MISMO pedido y la MISMA tienda:
- esa OUT sin validar: las uds leidas pasan a esa OUT y a esa caja. Si esta OUT se queda vacia, queda
  CANCELADA y sale de la agrupacion (no hay que validarla ni juntar cajas).
- esa OUT ya validada: las uds van a esa caja; al validar esta OUT no cuenta esa caja como bulto suyo.
v1.0 (09/11/2026).
v1.4 (16/11/2026): auditoria 13/11, fase 6 (pasar a koroshi_base). La empresa y la expresion de la matricula CJ
salen de koroshi_base.comun (la misma: CJ + 9 cifras, sin pasar a mayusculas, igual que antes). Mismo resultado;
sin campos ni vistas nuevas. Depende de koroshi_base.
""",
    'version': '13.0.1.4.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'stock_barcode_optimization', 'koroshi_base'],
    'data': [],
    'installable': True,
    'application': False,
}

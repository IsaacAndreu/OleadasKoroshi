# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Sync S4T con OUT canceladas',
    'summary': 'Deja sincronizar con S4T los pedidos con backorders canceladas (el resto de OUT hechas)',
    'description': """
KOROSHI Sync S4T con OUT canceladas.

El módulo de Effective (api_s4t_batch_update_PROD, s4t.order.sync.action_sync_order) solo envía un pedido si TODAS
sus transferencias están en «done»: una backorder cancelada lo bloquea para siempre («El pedido no tiene
transferencias | tiene transferencias pendientes | tiene transferencias en diferentes estados»). Lo que se manda a
S4T, en cambio, sale solo de las OUT hechas, así que la cancelada no cambia nada del envío.

Este módulo hereda action_sync_order: si el pedido tiene transferencias canceladas y TODAS las demás están hechas,
llama al de Effective viendo solo las no canceladas (en la caché de Odoo, sin escribir nada en la base de datos).
Mismo servicio, misma clave, mismo envío y mismo resultado en el pedido. En cualquier otro caso, el de Effective
tal cual. No toca el módulo de Effective ni añade campos.

Vale para el cron 186 (acción 1800) y para el botón «Sincronizar S4T» del pedido.

v1.0.0 (17/11/2026): primera versión. Los pedidos de tienda con backorders canceladas el 16/11 (4250, 4252, 4253,
4254, 4256) llevaban un día sin poder enviarse.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': ['api_s4t_batch_update_PROD', 'sale_stock'],
    'data': [],
    'installable': True,
    'application': False,
}

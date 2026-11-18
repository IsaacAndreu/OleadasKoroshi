# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Agrupaciones web por corte',
    'summary': 'Cortes de pedidos web a las 06:00 y 11:00: cancela los que no tienen todo el stock (aviso a Betty) '
               'y agrupa los reservados del todo en WEB_ddmmaa_NN de hasta 100 uds',
    'description': """
Pedidos web de KOROSHI (Effective Logistics NAU-2, compania 8). Lo pidio Isaac el 13/11 y el 18/11/2026.

En cada corte (koroshi_agrupaciones_web.cortes, hora del almacen, 06:00,11:00):
1. Cancela las OUT web creadas antes del corte que no estan al 100 % reservadas, sin agrupacion y sin nada leido
   (action_cancel; no se borran). Manda a Betty (correo_canceladas) la lista con lo que falta y lo que si hay, para
   que las cancele en el TPV de KOROSHI y rehagan el pedido con el stock que hay. A S4T no se le manda nada.
2. Agrupa las OUT web 100 % reservadas y sin agrupacion, en orden de llegada, en WEB_ddmmaa_NN (siguiendo la
   numeracion del dia) de hasta tope_uds uds (100). Una OUT nunca se parte. Quedan En curso y se preparan con
   PedidosMultiples, como las que hace la oficina a mano.

OUT web = origen W-, tipo de pedido que no es MARKETPLACE ni TIENDAS, direccion que no es Zalando ni About You.
100 % reservada = Preparada y ningun movimiento En espera / Esperando otra operacion / Parcialmente disponible
(las OUT web tienen move_type 'direct': Preparada sola no basta).

Se instala APAGADO: activo = 0 (el cron no hace nada) y cancelar = 0 (un corte solo apunta cuales cancelaria).
Menu KOROSHI > Pedidos web: cortes hechos, OUT web 100 % reservadas, OUT con reserva incompleta, Simular corte ahora
y Hacer corte ahora. Filtros «Reserva incompleta» y «Web sin agrupar» en la busqueda de albaranes.
Sin campos en tablas compartidas: escribe en sus dos tablas, en stock.picking.batch, en el estado de las OUT que
cancela, en sus parametros y en mail.mail. No toca la PDA.

v1.0.0 (18/11/2026): primera version (cortes 06:00 y 11:00, tope 100 uds, cancelacion con correo a Betty).
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['mail', 'stock', 'sale_stock', 'stock_picking_batch', 'koroshi_base', 'koroshi_menu'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/cron.xml',
        'views/corte_views.xml',
        'views/picking_views.xml',
    ],
    'installable': True,
    'application': False,
}

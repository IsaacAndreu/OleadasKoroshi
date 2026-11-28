# -*- coding: utf-8 -*-
{
    'name': 'TUCTUC Operarios (Lecturas PDA)',
    'summary': 'Lecturas (PDA) de la nave de Oriola - Amposta: tarjeta del operario, cola de pedidos y productividad',
    'description': """
TUCTUC Operarios: la pantalla Lecturas (PDA) en odoo.tuctuc.com. Clon de koroshi_operarios 2.25.0 (decisión de Isaac
del 27/11/2026: módulos nuevos tuctuc_* para la nave de Oriola, los koroshi_* no se tocan).
Diseño: bin/versiones/tuctuc_pda/20261127_diseno-clon-tuctuc-pda_v1.md.

- Lecturas (acción de cliente tuctuc_operarios_pantalla, app «Lecturas (PDA)»): el operario pasa su tarjeta y la PDA
  le da lo siguiente y lo abre en la app de código de barras. Rutas /tuctuc/operarios/*.
- La misma tarjeta que en NATH: los operarios se crean aquí con el mismo código OP0001... («Crear operarios» acepta
  el código delante: «OP0007 Nombre Apellido»), sin compañía, y valen para PRIME, MODA INTIMA y UNITED.
- Qué da la PDA: las OUT directas (las que no salen del SORTER) y las INT de la estantería al SORTER (oleadas WEB,
  WEB B&B, PED. INICIAL), de todas las compañías de la PDA que tenga el usuario (tuctuc.almacen). Las OUT que salen
  del SORTER no se dan nunca: las reparte PedidosMultiples.
- Un reparto del día para toda la nave (Reparto de hoy), con «darle la siguiente sola» encendido; colas, motivos
  para saltar, pausa, preparar a dos y productividad por tarea, como en NATH.

No se clona (de koroshi_operarios): tablero del responsable y tablero por áreas, etiquetas de zona y matrículas CJ,
gestión e impresión de tarjetas (la tarjeta es la de NATH), informe y migraciones.

v1.0.0 (27/11/2026): primera versión, clon multicompañía de koroshi_operarios 2.25.0 para odoo.tuctuc.com.
v1.0.1 (28/11/2026): revisión 28/11, T1. «Siguiente pedido» quita las OUT de oleada (WEB, WEB B&B, PED. INICIAL)
con una consulta sobre las OUT abiertas, no con sale_id.s_order_type_id en el dominio: Odoo 13 cargaba los
642.340 pedidos de esos tipos en cada petición, y las OUT sin pedido de venta no salían nunca.
v1.0.2 (28/11/2026): los tipos de pedido de oleada van POR ALMACÉN (parámetro tuctuc_operarios.oleadas): en Oriola
los PED. INICIAL de MODAI y la WEB de UBRAN salen directos del stock y la PDA no los daba nunca.
""",
    'version': '13.0.1.0.2',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'tuctuc_base'],
    'data': [
        'security/grupo.xml',
        'security/ir.model.access.csv',
        'data/categoria.xml',
        'data/motivos.xml',
        'data/motivos_v2100.xml',
        'data/motivos_v2170.xml',
        'data/motivos_v221.xml',
        'data/parametros.xml',
        'data/cron.xml',
        'views/assets.xml',
        'views/tarea_views.xml',
        'views/reparto_views.xml',
        'views/wizard_views.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/operarios.xml',
    ],
    'installable': True,
    'application': False,
}

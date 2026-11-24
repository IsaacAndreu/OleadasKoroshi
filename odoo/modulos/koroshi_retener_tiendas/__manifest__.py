# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Retener pedidos de tienda',
    'summary': 'Antes de las zonas, retiene los pedidos de tienda duplicados (varios de la misma tienda en una noche) '
               'o cancelados en S4T y avisa al responsable',
    'description': """
KOROSHI (Effective Logistics NAU-2, compania 8). Lo pidio Isaac el 24/11/2026, despues de que KOROSHI mandara los
mismos 49 pedidos de tienda tres veces en una noche y el reparto de las 04:50 los metiera todos en las zonas.
Diseno: bin/versiones/diseno-retener-pedidos-tienda_2026-11-24.md.

Cada noche, sobre los pedidos S- de tienda (tipo koroshi_retener_tiendas.tipo_pedido) creados desde las
koroshi_retener_tiendas.hora_noche (14:00) del dia anterior:
- Tienda (direccion de entrega K##) con mas de un pedido: se retienen todos.
- Cancelado en S4T: se retiene. Si una tienda tiene varios y S4T dice que solo uno sigue vivo, ese pasa y se
  retienen los cancelados. A S4T solo se le pregunta con koroshi_retener_tiendas.s4t = 1: GET /orders/b2b siempre con
  viewed=true (nunca viewed=false). Si S4T no contesta, solo se miran los duplicados.
- Nunca cancela nada: decide un responsable en KOROSHI > Pedidos de tienda retenidos («Preparar este» o «Ya
  cancelado en Odoo», que solo apunta la decision y deja nota en el pedido).
- Correo a koroshi_retener_tiendas.avisar a las horas de koroshi_retener_tiendas.horas (04:40 y 05:45 hora local)
  si hay retenidos sin decidir.

Modo (koroshi_retener_tiendas.modo): aviso (de inicio: revisa y avisa, pero los pedidos SI entran en zonas y en el
reparto) o real. pickings_retenidos() da las OUT a dejar fuera; la usaran los enganches de koroshi_zonas y
koroshi_operarios (versiones aparte). En modo aviso devuelve una lista vacia.

Sin campos en tablas compartidas: escribe en su tabla, en sus parametros, en el chatter del pedido al decidir y en
mail.mail. No toca la PDA, ni reservas, ni OUT.

v1.0.0 (24/11/2026): primera version, en modo aviso y sin preguntar a S4T (falta confirmar el campo de estado de la
  API, P0 del diseno). Revision a las 04:40 y 05:45, correo y lista con las decisiones.
""",
    'version': '13.0.1.0.0',
    'author': 'Effective Logistics',
    'category': 'Inventory',
    'depends': ['mail', 'sale_stock', 'koroshi_base', 'koroshi_menu'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/cron.xml',
        'views/retenido_views.xml',
    ],
    'installable': True,
    'application': False,
}

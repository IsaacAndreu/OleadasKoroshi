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
- Tienda (direccion de entrega K##) con mas de un pedido seguido (a menos de koroshi_retener_tiendas.ventana_horas,
  3 h, uno de otro): se retienen todos los del grupo.
- Cancelado en S4T: se retiene. Si una tienda tiene varios y S4T dice que solo uno sigue vivo, ese pasa y se
  retienen los cancelados. Con koroshi_retener_tiendas.s4t = 1 se pregunta al dashboard de S4T: GET
  /dashboard/orders/data (type=B2B, almacen_id, date_from, date_to; campos numero_orden y status), que no marca nada
  como visto. Si S4T no contesta, solo se miran los duplicados.
- v1.2.0: menos de koroshi_retener_tiendas.minimo_uds (20) uds RESERVADAS en Odoo (aunque en S4T pida mas): se
  retiene y sale en un correo aparte a koroshi_retener_tiendas.avisar_pocas (Betty, Jose Luis e Isaac). Con
  koroshi_retener_tiendas.cancelar_pocas = 1 sus OUT se cancelan como las de la web (sin nada leido, sin validar, fuera
  de zonas y de la cola de un operario); de inicio 1 desde la v1.3.0 (tambien en modo aviso).
- Fuera de eso nunca cancela nada: decide un responsable en KOROSHI > Pedidos de tienda retenidos («Preparar este» o «Ya
  cancelado en Odoo», que solo apunta la decision y deja nota en el pedido).
- Correo a koroshi_retener_tiendas.avisar a las horas de koroshi_retener_tiendas.horas (04:40 y 05:45 hora local)
  si hay retenidos sin decidir.

Modo (koroshi_retener_tiendas.modo): aviso (de inicio: revisa y avisa, pero los pedidos SI entran en zonas y en el
reparto) o real. pickings_retenidos() da las OUT a dejar fuera; la usaran los enganches de koroshi_zonas y
koroshi_operarios (versiones aparte). En modo aviso devuelve una lista vacia.

Sin campos en tablas compartidas: escribe en su tabla, en sus parametros, en el chatter del pedido al decidir y en
mail.mail; con cancelar_pocas = 1, en el estado de las OUT que cancela. No toca la PDA ni las reservas.

v1.3.0 (24/11/2026): Isaac dice que si a cancelar: cancelar_pocas = 1 de inicio. Los pedidos de tienda con menos de
  20 uds reservadas se cancelan (sus OUT, como las de la web) a las 04:40, tambien en modo aviso, y el correo a Betty,
  Jose Luis e Isaac lo dice. En S4T el pedido sigue PENDING: nada se lo dice todavia.
v1.2.0 (24/11/2026): lo pide Isaac: un pedido de tienda con menos de 20 uds reservadas en Odoo no se prepara ni va
  a zonas, y se avisa por correo a betty@nath.es, j.luis@nath.es e isaac.andreu@nath.es. Cancelar sus OUT como las de
  la web queda hecho pero apagado (cancelar_pocas = 0) hasta que Isaac diga que si. Medido (35 dias): de 0 a 25
  pedidos por noche piden menos de 20 uds. Campos nuevos solo en su tabla (reservadas, aviso_pocas).
v1.1.0 (24/11/2026): comprobado en produccion (solo lectura). (1) La API /orders/b2b no sirve desde una accion de
  servidor y el estado esta en el dashboard de S4T: /dashboard/orders/data con numero_orden y status
  (PENDING/READY/CANCELLED); el 24/11 da 99 CANCELLED. Se pregunta ahi, con filtro de fecha y sin viewed, y s4t = 1
  de inicio. (2) Duplicado = pedidos de la misma tienda a menos de 3 h uno de otro (parametro ventana_horas): en 120
  dias solo saltan el 07/10 (50 tiendas) y el 24/11 (49), los dos incidentes reales; con «toda la noche desde las
  14:00» saltaban ademas 11 noches con un pedido de tarde (14:15-17:15) y el de la noche, que son pedidos distintos.
v1.0.0 (24/11/2026): primera version, en modo aviso y sin preguntar a S4T (falta confirmar el campo de estado de la
  API, P0 del diseno). Revision a las 04:40 y 05:45, correo y lista con las decisiones.
""",
    'version': '13.0.1.3.0',
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

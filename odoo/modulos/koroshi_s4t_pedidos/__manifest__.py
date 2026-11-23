# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Pedidos S4T grandes',
    'summary': 'Los pedidos S4T grandes (Zalando) entran sin «could not serialize»: crear, confirmar y reservar '
               'en jobs aparte, y nunca dos copias del mismo job a la vez',
    'description': """
KOROSHI Pedidos S4T grandes.

El job de Effective (api_s4t_batch_update_PROD, s4t.order.feed.action_create_sale_order) crea el pedido, lo
confirma y reserva sus OUT en una sola transaccion. Con un Zalando de 329 lineas son minutos, y si mientras tanto una
PDA toca un quant que tambien reserva, Postgres lo deshace todo al guardar («could not serialize access due to
concurrent update»). El 19/11 ademas corrieron dos copias del mismo job a la vez (reencolado por el cron 192 y a mano)
y se tumbaron entre ellas en cada reintento.

Este modulo, sin tocar el de Effective ni anadir campos:
- Candado por feed y por pedido (pg_advisory_lock): si otra copia del mismo job esta trabajando, esta no hace nada
  y se vuelve a mirar en 5 min. Si el feed ya tiene pedido, el job acaba bien sin hacer nada.
- Pedidos b2b con koroshi_s4t_pedidos.umbral_lineas lineas o mas (60 por defecto; 0 = apagado):
  1. el job de Effective crea y GUARDA el pedido (presupuesto) y deja el feed en 'done';
  2. «S4T Confirmar pedido S-...»: confirma sin reservar (las OUT nacen sin reserva);
  3. «S4T Reservar OUT S-...»: reserva por bloques de koroshi_s4t_pedidos.bloque_reserva (50), un commit por bloque.
  Si falla el 2, el pedido sigue en presupuesto (nunca medio confirmado). Si falla el 3, la OUT queda a medio
  reservar, como con falta de stock. Los dos quedan en «Fallido» en Cola de trabajos y el cron 192 avisa.
- Pedidos pequenos (tiendas) y web: igual que antes, en un solo job.

Todos los jobs van al canal root.s4t_sync (capacidad 1). Necesita la v7 del cron 192 «Alerta cola de S4T»
(bin/versiones/20261119_cron-alerta-cola-s4t_v7.py), que mira el candado antes de reencolar un job.

v1.0.0 (19/11/2026): primera version. S-6665004459 (K ZALANDO ZFS, 329 lineas) no entraba: serialize en
stock_quant al reservar y en queue_job por dos copias del mismo job (diseno en
bin/versiones/diseno-feed-s4t-sin-serialize_2026-11-19_v2.md).
v1.0.1 (19/11/2026): sin el decorador @job. En el servidor queue_job es la 13.0.3.10.1: @job esta obsoleto y no
hace falta para with_delay (Effective tampoco lo usa); aplicarlo podia crear registros de funcion/canal al instalar.
La 1.0.0 no llego a subirse.
v1.1.0 (23/11/2026): reserva de las tiendas por prioridad (Isaac: la misma que el Monitor, numero de pedido S4T, el
mas bajo primero). Cron 03:30 UTC (20 min antes de que zonas parta) y menu Inventario > Informes > Reserva tiendas por
prioridad (ejecuciones y «Repartir ahora»). Solo OUT de PED. TIENDAS que nadie ha empezado (sin leidas, cajas, lote
que no sea TIENDA..., puesto de operario ni SORTER); solo los articulos en disputa; quitar y volver a reservar en orden,
un savepoint por articulo. Parametro koroshi_s4t_pedidos.prioridad_modo: simular (por defecto), real o apagado.
Modelos propios koroshi.s4t.prioridad(.linea); sin campos en tablas compartidas. Depende de koroshi_base y
stock_picking_batch. Diseno: bin/versiones/diseno-reserva-tiendas-por-prioridad_2026-11-23.md.
v1.2.0 (23/11/2026): revision general del 23/11 (R15), antes de poner prioridad_modo = real. Incluye la 1.1.0 (sin
instalar). «No empezada» se vuelve a mirar dentro del savepoint de cada articulo, con lo ultimo de la base (en real hay
commit por articulo y el reparto tarda): si una OUT se ha empezado entretanto, ese articulo se salta y lo dice el
informe. «Repartir ahora» no deja en horario de trabajo (koroshi_s4t_pedidos.prioridad_horario, 06:00-17:00 si no
existe), tampoco en simular. El reparto para koroshi_s4t_pedidos.prioridad_margen_zonas min (5) antes del cron «partir
OUT» de koroshi_zonas, leyendo su siguiente hora, y no empieza si ya le toca: lo hecho hasta ahi queda. No toca
koroshi_zonas. Sigue entrando en SIMULAR. En simular la comprobacion de dentro no ve lo que pase durante el reparto
(no cambia nada, solo bloquea las lineas de cada articulo un momento).
""",
    'version': '13.0.1.2.0',
    'author': 'NATH',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': ['api_s4t_batch_update_PROD', 'sale_stock', 'queue_job', 'stock_picking_batch', 'koroshi_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/prioridad_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
}

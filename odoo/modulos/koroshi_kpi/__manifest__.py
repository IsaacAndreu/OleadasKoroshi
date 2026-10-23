# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI KPI',
    'summary': 'KPI diarios del almacen KOROSHI: uds, profundidad por SKU, peso, volumen, metros y segundos por prenda',
    'description': """
KPI diarios del picking de KOROSHI (Effective Logistics).

Una ficha por dia (Inventario > KOROSHI KPI > Dias):
- Calculado de Odoo (boton Recalcular y cada noche): uds, lineas, SKU, profundidad por SKU,
  pedidos, OUT, cajas, volumen total y por ud (volumen del producto o litros del tipo),
  peso total y por ud (tabla de pesos por tipo, estimada), metros recorridos (modelo de la nave)
  y hora de la primera y la ultima caja.
- A mano: personas y horas de picking, packing y expedicion.
- Resultado: segundos por prenda de cada fase y total, tiempo andando y leyendo dentro del
  picking (metros / velocidad), horas totales y personas.

v1.1: una ficha por dia y metodo (dia completo, tradicional, zonas, oleada) y horas y personas
estimadas por las cajas cerradas cuando no se apuntan a mano.
v1.2: uds por persona; la lista sale por dia con personas, horas totales, uds/persona y uds/hora-persona;
al actualizar se crean y recalculan solas las fichas de los dias que ya habia.
v1.3: Faltas por dia (Inventario > KOROSHI KPI > Faltas por dia): lo que piden los pedidos de tienda y no
se ha cogido, por OUT, articulo y motivo (sin stock, no cogido, en pedido pendiente, no servido). Se saca
con el boton Recalcular de la ficha del dia, cada noche y con el menu Recalcular faltas de hoy.

Solo escribe en sus propias tablas: no cambia albaranes, stock ni productos.
""",
    'version': '13.0.1.3.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/peso_tipo.xml',
        'data/cron.xml',
        'data/recalcular.xml',
        'views/kpi_views.xml',
        'views/falta_views.xml',
    ],
    'installable': True,
    'application': False,
}

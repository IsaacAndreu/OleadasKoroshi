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
v1.4: Hoja de carga XPO (Excel por delegacion con tiendas, pedidos, uds, bultos y palets): menu Inventario > Informes > Hoja de carga
XPO de hoy, o seleccionar OUT en la lista de albaranes > Accion > KOROSHI Hoja de carga XPO.
v1.5.0 (12/11/2026): Comparativa de semanas (uds, u/h = uds / horas-persona picking, faltas y cajas de cada dia de
esta semana contra el mismo dia de la semana pasada, con fila de total de lunes a hoy) y Faltas repetidas (articulos
que dan falta 3 o mas dias seguidos con actividad, con su ubicacion de mas stock: propuesta para una ronda de revision,
no crea nada). Dias del parametro koroshi_kpi.dias_falta_repetida. Las dos son vistas SQL de solo lectura.

Solo escribe en sus propias tablas: no cambia albaranes, stock ni productos.
v1.6.0 (14/11/2026): auditoria 13/11, fase 2. Horas de picking del tiempo efectivo de los operarios (koroshi_operarios 2.12)
cuando cubren el 80 % de las uds del dia (koroshi_kpi.cobertura_minima); si no, las de las cajas; la ficha dice de donde
salen («Horas de picking de»). Ratios sin media al agrupar. «No cogido» ya no desaparece al validar la OUT (se cruza
con los faltantes de la PDA) y cada noche se recalculan los dias con OUT abiertas. Al actualizar, solo se recalculan los
ultimos 7 dias (koroshi_kpi.dias_recalcular). Hoja de carga: delegacion del campo de koroshi_delegacion si esta instalado.
v1.7.0 (14/11/2026): auditoria 13/11, fase 3. La hoja de carga XPO pide el permiso de Inventario (hacia sudo()).
v1.8.0 (15/11/2026): auditoria 13/11, fase 7. Prevision de cajas por volumen: cada manana (cron 05:30) y con
«Prever cajas ahora», lo que queda por servir en las OUT abiertas / 0,084 m3 x factor (calibrado con las cajas
reales de los 20 dias anteriores; del 20/10 al 13/11 sale 1,077 y 13 de 14 dias normales quedan a +-10 %). La
ficha guarda prevista, real y desviacion. Menu «Prevision de cajas de hoy». Campos nuevos solo en
koroshi.kpi.dia. Calculo en calculo_prevision.py con tests sin Odoo (tests/).
""",
    'version': '13.0.1.8.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/peso_tipo.xml',
        'data/cron.xml',
        'data/recalcular.xml',
        'data/parametros.xml',
        'views/kpi_views.xml',
        'views/falta_views.xml',
        'views/hoja_carga.xml',
        'views/semana_views.xml',
        'views/falta_repetida_views.xml',
    ],
    'installable': True,
    'application': False,
}

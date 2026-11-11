# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Zonas',
    'summary': 'Partir los pedidos de tienda por zonas de picking buscando el maximo de cajas cerradas',
    'description': """
Sustituira a la accion de servidor 1883 "KOROSHI Partir OUT zonas v12 REAL" (v12f), que lanza el cron 202.
Objetivo: el maximo % de cajas cerradas (cajas que salen llenas a la tienda sin juntar restos de varias zonas).

El calculo (carpeta motor/) es Python puro, sin Odoo, y tiene tests (carpeta tests/, se lanzan sin Odoo:
python -m unittest discover -s tests -t .).

Fase 1 - Medir (no toca el reparto de la 1883):
- Inventario > KOROSHI Zonas > Ejecuciones: una por prefijo de agrupaciones (Z-ddmm- o Z-ddmm-R2-), con las
  cajas previstas (CAJAS n de la nota), las estimadas con lo cogido y las reales (matriculas).
- Caja cerrada real: matricula no compartida con otra OUT y que llega al 80 % de 80 L con lo que lleva
  dentro. Una caja compartida (koroshi_caja_existente) nunca es cerrada; cuenta una vez, para su OUT duena
  (parametro koroshi_zonas.regla_dueno: primera_linea, como el Monitor, o mas_uds).
- Cada hora registra las OUT de las agrupaciones Z- de hoy (para leer el CAJAS n antes de que se pise la
  nota) y cada noche mide los ultimos 7 dias. Menu "Medir desde el 22/10" para el historico.
- La ficha diaria de koroshi_kpi muestra el % real de cajas cerradas de las zonas.

Solo escribe en sus propias tablas: no cambia albaranes, movimientos, agrupaciones ni stock.

v1.0 (11/11/2026): fase 1, medir las cajas reales.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'stock_picking_batch', 'koroshi_kpi'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/cron.xml',
        'views/ejecucion_views.xml',
        'views/kpi_dia_views.xml',
    ],
    'installable': True,
    'application': False,
}

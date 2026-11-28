# -*- coding: utf-8 -*-
{
    'name': 'Monitor picking Oriola',
    'summary': 'Pantalla en directo de como va el picking del almacen Oriola - Amposta (solo lee)',
    'description': """
Monitor del picking del almacen Oriola - Amposta (odoo.tuctuc.com).

Menu Inventario > Monitor picking. Ensena, para el dia elegido (por defecto hoy):
- OUT validadas, uds servidas, cajas, personas y uds por hora-persona;
- por persona (cada PDA tiene su usuario): uds leidas, OUT validadas, cajas, primera y ultima
  lectura, horas activas (cuartos de hora con lecturas) y uds por hora;
- el almacen automatico y el sistema aparte (no cuentan como personas);
- uds leidas por hora;
- pendiente ahora por canal (APP-S, ECI, web, VP...): listas para coger y en espera;
- lotes (B-WEB, B-ECI, B-VP...) que aun tienen OUT sin hacer.

Pensado para no cargar el servidor: consultas SQL agregadas, solo de los albaranes de salida del
almacen; el resultado se guarda 90 s (10 min los dias pasados) y lo comparten todas las pantallas;
cada consulta tiene un limite de 15 s; la pantalla refresca cada 2 min y no pide nada si la pestana
no se ve.

El tipo de albaran sale del parametro del sistema oriola_monitor.picking_type_id; si no esta,
se busca el de salida del almacen con codigo WH-OR.

Solo lee: no cambia nada en Odoo.

v1.0.0 (26/10/2026): primera version (monitor del picking de Oriola - Amposta en odoo.tuctuc.com). Linea de historial
anadida el 23/11/2026 (revision general, R19) para que bin/comprobar.py no de E6; el modulo no cambia.
v1.1.0 (28/11/2026): con la PDA nueva (tuctuc_operarios y tuctuc_preparacion), seccion «Por operario y empresa»: por
tarjeta OP y por empresa del albaran (PRIME, MODA INTIMA, UNITED), uds, uds/hora efectiva, parado y albaranes
hechos; «Ahora mismo» (que hace cada uno y cuanto lleva sin leer) y «Pendiente por empresa» (OUT directas, INT al
SORTER y OUT de oleada). Lo pide Isaac el 28/11. Sin los modulos tuctuc_* la seccion no sale (no depende de ellos).
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'stock_picking_batch'],
    'data': [
        'views/assets.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}

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
""",
    'version': '13.0.1.0.0',
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

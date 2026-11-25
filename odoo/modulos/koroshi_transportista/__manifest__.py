# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Transportista',
    'summary': 'PDA (área Expediciones): leer todas las CJ de la tienda, comprobar que cuadran con Odoo y sacar la '
               'etiqueta GLS/XPO, que sale en la Zebra del portátil de Expediciones.',
    'description': """
Transportista (KOROSHI, Effective Logistics).
Diseño: bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md (visto bueno de Isaac el 25/11/2026: GLS/XPO antes o
al final; bloquear siempre si no cuadra; OUT de días distintos en la misma expedición; Zebra GK420t del portátil).

En la PDA, área Expediciones, botón «Transportista»:
1. Tarjeta del operario. GLS o XPO se puede elegir arriba antes de empezar o al final.
2. Leer todas las cajas (CJ) de la tienda. La primera fija la tienda. Odoo espera las cajas distintas de las OUT de la
   tienda validadas, sin etiqueta, de los últimos 10 días y fuera de un camión XPO cerrado. Una caja que no va se
   rechaza diciendo por qué (otra tienda, OUT sin validar, ya etiquetada, juntada dentro de otra, vacía...).
3. Con «Leídas N de N» y ninguna rechazada pendiente: «Imprimir etiquetas» -> confirmar -> lo mismo que hoy en el
   portátil (GLS: acción 1834 v5; XPO: acción 1771) y el PDF de la etiqueta a la cola de impresión (koroshi_impresion)
   de la impresora del portátil (parámetro koroshi_transportista.impresora, por defecto EXP1).
4. «Reimprimir» de las últimas expediciones de la tienda (no registra nada).
Las acciones 1834 y 1771 siguen igual en el portátil. GLS -70 (ya existía): se hace desde el portátil con la 1834.
Cada etiqueta queda en koroshi.transportista.registro (KOROSHI Operarios > Etiquetas de transportista (PDA)) y en el
chatter de cada OUT. No añade campos a tablas de Odoo.

v1.0.0 (25/11/2026): primera versión. Lógica en logica.py con tests sin Odoo (cuadre, motivos, reparto GLS de la 1834).
v1.1.0 (25/11/2026): si la etiqueta de una caja no se lee, se escriben las últimas 4-9 cifras de la CJ (Isaac, 25/11).
  Primero entre las cajas que espera la tienda de la pantalla; si no, entre las OUT pendientes de etiqueta; varias =
  pide más cifras. Una tarjeta con ese número sigue siendo tarjeta.
""",
    'version': '13.0.1.1.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'delivery', 'koroshi_base', 'koroshi_operarios',
                'koroshi_actividades', 'koroshi_impresion', 'koroshi_xpo_bultos', 'delivery_gls_asm', 'delivery_xpo'],
    'data': [
        'security/ir.model.access.csv',
        'views/transportista_views.xml',
        'data/actividad.xml',
    ],
    'qweb': ['static/src/xml/transportista.xml'],
    'installable': True,
    'application': False,
}

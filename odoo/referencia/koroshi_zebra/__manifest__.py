# -*- coding: utf-8 -*-
{
    'name': 'Koroshi Zebra',
    'version': '13.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Impresión de etiquetas secuenciales (CJ665000001...) con barcode Code128 para impresoras Zebra',
    'description': """
Módulo para generar e imprimir etiquetas secuenciales tipo CJ665000001.

- Secuencia autoincremental configurable (por defecto empieza en CJ665000001).
- Asistente para generar N etiquetas de una sola vez y mandarlas a imprimir.
- Reporte en formato de etiqueta 150 x 110 mm, listo para imprimir en
  impresoras Zebra (o cualquier impresora que reciba PDF), con:
    * Recuadro "VALIDAR ETIQUETA"
    * Código grande en texto
    * Código de barras Code128
    * Código repetido debajo del barcode
    * Leyenda "(NO TAPAR!!!)"
""",
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'wizard/print_labels_wizard_views.xml',
        'views/zebra_label_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}

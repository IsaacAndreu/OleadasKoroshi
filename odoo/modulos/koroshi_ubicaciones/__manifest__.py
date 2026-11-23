# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Crear e imprimir lineales y contenedores',
    'summary': 'Un botón crea los contenedores KO_/TT_ o los huecos de un lineal y abre sus etiquetas 4x6. '
               'Otro vuelve a imprimirlas.',
    'description': """
Crear e imprimir (Inventario > Crear e imprimir, arriba; y KOROSHI > Almacén). Lo pide Isaac el 23/11/2026: crear un
lineal o un contenedor y sacar su etiqueta era «tot un xou» (crear en Odoo, exportar, imprimir aparte). Lo usan
Recepciones y Compactación desde el PC de Recepciones.

- Contenedores: cuántos (100 por defecto) y KO_ o TT_. Crea KO_<ddmmaa>_<siguiente> dentro de EFFEC/Stock/NAVE2 con
  código de barras = nombre (como hasta ahora; el número vuelve a 001 cada día y nunca se repite, también contra los
  archivados) y abre el PDF con sus etiquetas.
- Lineal: L181 o MU-05, de qué P a qué P y de qué C a qué C. Antes de crear enseña qué va a crear y no crea nada si
  alguno de esos huecos ya existe (con o sin el número de delante, «21048 - L142 P00 C1»). Los nuevos se llaman como
  los de muelle: «L181 P00 C1», nombre y código de barras iguales (decidido con Isaac el 23/11: el número de delante
  no sirve). Abre el PDF con sus etiquetas.
- Volver a imprimir: L94, L94 P10-P20, KO_171126 (el día entero), KO_171126_001-050 o un nombre.
- Etiqueta para la Zebra 4x6 (102 x 152): hueco = lineal en grande, P y C, y el código de barras Code128; contenedor =
  su nombre y el código. Si una ubicación no tiene código de barras (hay 2.510 huecos así, L180), se imprime su nombre.
- Cada tanda queda en «Etiquetas creadas e impresas» (quién, cuándo, qué ubicaciones) con «Volver a imprimir».

Solo crea stock.location (con sudo: crear ubicaciones es de Inventario / Administrador) y escribe en sus tablas
(koroshi.ubicaciones.tanda). No añade campos a tablas de Odoo. Lógica de nombres en nombres.py (sin Odoo; prueba en
tests/test_nombres.py). Diseño: bin/versiones/diseno-crear-imprimir-lineales-contenedores_2026-11-23.md

v1.0.0 (23/11/2026): primera versión.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['stock', 'koroshi_base', 'koroshi_menu'],
    'data': [
        'security/ir.model.access.csv',
        'views/etiqueta_report.xml',
        'views/crear_views.xml',
    ],
    'installable': True,
    'application': False,
}

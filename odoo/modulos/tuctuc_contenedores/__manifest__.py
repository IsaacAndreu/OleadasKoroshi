# -*- coding: utf-8 -*-
{
    'name': 'TUCTUC Contenedores (PDA)',
    'summary': 'Contenedores en la PDA de la nave de Oriola: mover, revisar cajas a 0 y Compactar',
    'description': """
TUCTUC Contenedores (odoo.tuctuc.com). Clon de koroshi_contenedores 1.17.0 («Compactar fase 1»; decisión de Isaac del
27/11/2026: módulos nuevos tuctuc_* para la nave de Oriola, los koroshi_* no se tocan).
Diseño: bin/versiones/tuctuc_pda/20261127_diseno-clon-tuctuc-pda_v1.md.

- Pantalla Contenedores (rutas /tuctuc/contenedores/*): leer contenedor, hueco, lineal o prenda; mover contenedores
  enteros; poner a cero, añadir, cambiar cantidad, «es otro» (con tuctuc_faltantes); ronda de cajas a 0; Compactar
  (plan por lineal: vaciar columnas con pocas cajas moviendo cajas enteras, sin mezclar colores de un modelo, con su
  altura abajo/arriba).
- Multicompañía: la nave es una, pero cada hueco existe una vez por compañía (WH-OR, MODAI, UBRAN), con el mismo
  nombre y código de barras («gemelos»). Un hueco enseña los contenedores de todas sus compañías; al mover, cada
  contenedor va al hueco de SU compañía (nunca se mueve stock entre compañías). Compactar cuenta las cajas de todas
  las compañías en cada columna.
- Contenedores TT_ (PRIME), MI_ (MODA INTIMA), UB_ (UNITED) y KO_: parámetro tuctuc_base.prefijos_contenedor.
- Sin zona 0 ni outlet (Isaac, 28/11): todos los lineales y todas las temporadas (parámetros tuctuc_contenedores.
  lineales y .temporadas vacíos). Modelo-color = plantilla + atributo de color (los artículos de tuctuc no se llaman
  MODELO-COLOR-TALLA). Cajas por columna 8, vaciar < 4, ±2 lineales y muelle antes del L1: como NATH, por confirmar.
- tarjetas_revisar y tarjetas_con_prendas vacíos (nadie) hasta que se decida quién en Oriola.

v1.0.0 (28/11/2026): primera versión, clon multicompañía de koroshi_contenedores 1.17.0 para odoo.tuctuc.com.
v1.0.1 (28/11/2026): Compactar encuentra los lineales del 1 al 9 escritos con cero (L01...): «No encuentro columnas
en L1» en la primera prueba en tuctuc.
""",
    'version': '13.0.1.0.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'tuctuc_base', 'tuctuc_operarios', 'tuctuc_faltantes'],
    'data': [
        'security/grupos.xml',
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'views/assets.xml',
        'views/views.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/contenedores.xml'],
    'installable': True,
    'application': False,
}

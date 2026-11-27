# -*- coding: utf-8 -*-
{
    'name': 'TUCTUC Preparación en Lecturas (PDA)',
    'summary': 'Preparar en la PDA de la nave de Oriola: OUT con caja de Odoo e INT al SORTER, lectura a lectura',
    'description': """
TUCTUC Preparación en Lecturas (odoo.tuctuc.com). Clon de koroshi_preparacion 3.38.1 (decisión de Isaac del
27/11/2026: módulos nuevos tuctuc_* para la nave de Oriola, los koroshi_* no se tocan).
Diseño: bin/versiones/tuctuc_pda/20261127_diseno-clon-tuctuc-pda_v1.md (flujo confirmado por Isaac el 27/11).

- Desde Lecturas (tuctuc_operarios), la OUT o la INT se abre en la pantalla de preparar (acción
  tuctuc_preparacion_pantalla, rutas /tuctuc/preparacion/*): una lectura cada vez, deshacer, cantidad a mano, preparar
  a dos, Faltante (tuctuc_faltantes), alarma de parado y validar.
- Qué se prepara: las OUT de salida de los almacenes de la PDA (WH-OR, MODAI, UBRAN; tuctuc.almacen), con caja, y las
  INT de la estantería al SORTER de su almacén (oleadas WEB, WEB B&B, PED. INICIAL), sin caja. Y la ronda de faltantes.
- La caja la crea Odoo en todas las OUT («Put in pack»: BOX + 7 cifras, secuencia «Packages»); el operario elige el
  embalaje (product.packaging: los más usados en 30 días o los del parámetro tuctuc_preparacion.embalajes).
- Cada ruta trabaja con la compañía de la OUT como compañía activa (PRIME, MODA INTIMA o UNITED).

No se clona: agrupaciones Z- enteras, ruta óptima por la nave (geometría de NAU-2), «Caja llena», etiquetas CJ,
Consumibles, koroshi_caja_existente, migraciones y tests de NATH.

v1.0.0 (28/11/2026): primera versión, clon multicompañía de koroshi_preparacion 3.38.1 para odoo.tuctuc.com.
""",
    'version': '13.0.1.0.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'stock_barcode_optimization',
                'tuctuc_base', 'tuctuc_operarios', 'tuctuc_faltantes'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'views/assets.xml',
        'views/lectura_views.xml',
    ],
    'qweb': [
        'static/src/xml/preparacion.xml',
    ],
    'installable': True,
    'application': False,
}

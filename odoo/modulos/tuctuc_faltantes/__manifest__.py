# -*- coding: utf-8 -*-
{
    'name': 'TUCTUC Faltantes (PDA)',
    'summary': 'Faltante en la PDA de la nave de Oriola: la pieza que no está se coge de otro hueco o va a FALTANTE',
    'description': """
TUCTUC Faltantes (odoo.tuctuc.com). Clon de koroshi_faltantes 1.12.0 (decisión de Isaac del 27/11/2026: módulos
nuevos tuctuc_* para la nave de Oriola, los koroshi_* no se tocan). Diseño: bin/versiones/tuctuc_pda/.

- Botón «Faltante» en Lecturas y pantalla Faltante (rutas /tuctuc/faltantes/*): la línea de la OUT pasa a otro hueco
  con stock libre (el lineal más cercano) o, si no está en ningún sitio, se quita su reserva; las uds que faltan van
  de la ubicación vieja a FALTANTE. Al acabar, valida la OUT.
- FALTANTE por almacén, fuera del stock: WH-OR/FALTANTE, MODAI/FALTANTE y UBRAN/FALTANTE se crean al instalar y se
  ponen en tuctuc.almacen (decisión de Isaac del 28/11/2026). WH-OR/Stock/N1/FALTAS_001 no se toca.
- Cada operación con la compañía de la OUT como compañía activa (PRIME, MODA INTIMA o UNITED).
- Solo se coge de huecos de lineal de la zona de picking (N1).
- Oficina: revisión (Encontrado / No encontrado), rondas de revisión (INT) y resultado de las rondas.
- % de faltante (faltante ÷ recibido) por SKU, modelo (plantilla) y modelo-color (atributo «Color grouping»), por
  compañía; se recalcula una vez al día y con el menú. Correo diario a las 17:00 (tuctuc_faltantes.correo_*).

Puestos a 0: sin usuarios por defecto (parámetro tuctuc_faltantes.puestos_a_cero_usuarios vacío).

v1.0.0 (28/11/2026): primera versión, clon multicompañía de koroshi_faltantes 1.12.0 para odoo.tuctuc.com.
v1.0.1 (28/11/2026): la zona de picking es la del almacén de cada ubicación (antes, la de cualquiera) y, si está
vacía (MIECI, sin N1), vale cualquier hueco de su stock. Para MIECI en la PDA (sí de Isaac 28/11).
v1.0.2 (28/11/2026): revisión 28/11, T2. Las alternativas de Faltante (y el mejor destino) salen de una consulta
por parent_path, no de child_of del stock: Odoo 13 cargaba más de 150.000 ids de ubicación en cada búsqueda
(la PDA busca alternativas cuando se para 3 s en una línea). Mismo resultado.
""",
    'version': '13.0.1.0.2',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'mail', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'tuctuc_base', 'tuctuc_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'data/ubicacion.xml',
        'data/cron.xml',
        'data/parametros.xml',
        'data/parametros_relativo.xml',
        'data/parametros_correo.xml',
        'views/assets.xml',
        'views/faltante_views.xml',
        'views/wizard_views.xml',
        'views/relativo_views.xml',
        'data/cron_relativo.xml',
        'views/menu.xml',
    ],
    'qweb': [
        'static/src/xml/faltantes.xml',
    ],
    'installable': True,
    'application': False,
}

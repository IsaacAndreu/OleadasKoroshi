# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Mapa de almacén NAU-2',
    'summary': 'Mapa editable y mapa operativo de picking para NAU-2',
    'description': """
Mapa de almacén de KOROSHI preparado para Odoo 13.

Incluye:
- mapa editable NAU-2 basado en el plano de referencia;
- vista operativa de OUTs, personas/PDA, última ubicación y tiempos;
- capas separadas de esqueleto fijo, diseño editable y operación en vivo;
- editor tipo CAD con ajuste magnético, selección múltiple, alineación, duplicado, propiedades y deshacer/rehacer;
- vista LINEALS v43: zona Z y zona 0 antes y después con cada forma de compactar (sin el comparador v42) y panel Propiedades plegable;
- interfaz v41 con modos separados de edición, operación y análisis, panel contextual y pestañas de recorrido;
- filtros operativos por estado, incidencias y transportista, auditoría de recorridos y eventos de caja;
- capa de zonas reales del día, leídas de los pickings internos KOR-ddmm-*;
- modelos propios para guardar layouts y sesiones de picking;
- endpoint de lectura para alimentar la vista operativa sin modificar stock.

La primera versión conserva la edición local del plano y deja preparada la
persistencia en los modelos propios del módulo. La conexión de PDA debe
alimentar koroshi.pick.session y koroshi.pick.event.

v20261114.45 (14/11/2026): auditoría 13/11, fase 4. «Publicar versión» ya guarda en Odoo (fallaba siempre:
fields.Datetime.now() es un datetime y su .replace('-', '') daba error; 0 planos guardados) y enseña el error real.
Nueva ruta /koroshi_warehouse_map/layout/load y botón «Cargar de Odoo». El ?v= del plano sale de la versión del
manifest (ruta /koroshi_warehouse_map/planner). /data respeta 'since' (hora del servidor) y el inicio del día va en
UTC. Incluye la v20261106.44 del repo, que no llegó a instalarse (en el servidor está la 20261102.39).
""",
    'version': '13.0.0.1.20261114.45',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'stock_picking_batch'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/koroshi_layout_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}

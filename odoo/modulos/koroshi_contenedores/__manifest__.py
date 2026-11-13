# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Contenedores (mover de ubicación)',
    'summary': 'Escanear contenedores KO_/TT_ y la ubicación de destino: se mueven con sus prendas y reservas.',
    'description': """
Mover contenedores (sububicaciones KO_... / TT_... de un hueco) de un hueco a otro al compactar.

- Pantalla para la PDA o el portátil (Inventario > KOROSHI Operarios > Contenedores, y app «Contenedores»).
- Se escanea uno o varios contenedores (KO_240826_1327): salen su ubicación actual y sus prendas (uds y reservadas).
  Se escanea la ubicación de destino (código de barras del hueco) y los contenedores pasan allí.
- El movimiento cambia la ubicación padre del contenedor. Las prendas (quants) y las reservas de los pedidos NO se
  tocan: se conservan tal cual. No crea albaranes ni movimientos de stock.
- Cada movimiento queda apuntado en koroshi.contenedor.movimiento (quién, cuándo, de dónde a dónde, uds).
  Para deshacer: se escanea el mismo contenedor y la ubicación de origen.

Solo escribe en su propia tabla y cambia location_id de la ubicación KO_/TT_ movida. No añade campos a tablas de Odoo.
Limpiar: escanear una ubicación (sin contenedores en cola) muestra sus contenedores KO_/TT_; el botón archiva los que están a cero
(sin stock ni reservas). Los que aún tienen stock no se tocan. Cada archivado queda apuntado con quién lo hizo.

v1.2.0 (13/11/2026): icono propio en la pantalla de aplicaciones (cajas con flecha, fondo naranja); antes era el
  mismo que Lecturas (PDA). No cambia nada más.
v1.3.0 (13/11/2026): confirmación «¿está físicamente vacía?» antes de archivar, e inventario por lineal (escribir L94: huecos con
  contenedores y stock, solo lectura; tocar un hueco lo abre para limpiarlo). El lineal se lee del nombre del hueco.
v1.1.0 (13/11/2026): segunda parte (limpiar ubicación) y hay que pasar la tarjeta de operario (la misma de Actividades) antes de mover; el movimiento
  guarda quién lo hizo (campo employee_id de koroshi.contenedor.movimiento). La persona se mantiene 3 min sin actividad.
v1.0.0 (13/11/2026): primera versión (mover).
v1.4.0 (13/11/2026): auditoría del 13/11. Leer un contenedor KO_…_… ya no puede coger otro: en la búsqueda el «_» era
  «cualquier letra» (=ilike); ahora se busca el nombre tal cual. Lo que se lee mientras la pantalla espera a Odoo ya no
  se pierde sin pitido: va a una cola corta y se lee después; si la cola está llena, pita y lo dice. Incluye la 1.3.0.
""",
    'version': '13.0.1.4.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'koroshi_operarios'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/views.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/contenedores.xml'],
    'installable': True,
    'application': False,
}

# -*- coding: utf-8 -*-
{
    'name': 'KOROSHI Preparación en Lecturas',
    'summary': 'Preparar la OUT dentro de Lecturas (PDA): leer, cerrar caja con la CJ y validar sin salir a la app de código de barras',
    'description': """
Opción B (KOROSHI, Effective Logistics). Pantalla de preparación propia dentro de Lecturas (koroshi_operarios).

- Se activa por empleado (tarjeta), no por usuario: todas las PDA usan el mismo usuario de Odoo.
  Parámetros: koroshi_preparacion.activa ('1' / '0') y koroshi_preparacion.empleados (códigos de tarjeta
  separados por comas, p. ej. OP9990001,OP9980001; '*' = todos).
- Solo OUT sueltas. Las OUT de una agrupación de zona (Z-) siguen en la app de código de barras.
- Leer un EAN suma 1 ud a su línea (qty_done). Si no es de la OUT o ya está completo: aviso rojo y no cuenta.
- Caja: botón «Caja» -> «Escanea la caja» -> se lee la etiqueta CJ -> put_in_pack(package_name=CJ), igual que el
  diálogo «Nombre del Paquete» de la app (Brain Station y koroshi_caja_existente funcionan igual).
- Validar: la misma validación que koroshi_faltantes (button_validate, todo o nada). Después vuelve a Lecturas,
  que enseña «¡Hecho!» y abre la siguiente.
- Faltante (v3.2): sobre la línea que se ve. Dice dónde probar (la ubicación con stock más cercana) y se lee la
  ubicación de donde se coge, o «Tampoco está aquí». Usa las rutas de koroshi_faltantes (buscar, reubicar,
  sin_alternativa). «Marcar varias a la vez» abre la pantalla de Faltante de siempre.
- Cada lectura queda apuntada en la tabla koroshi.preparacion.lectura (quién, qué, cuándo, resultado).

Sin campos nuevos en albaranes, movimientos, agrupaciones ni tipos de operación. No toca stock_barcode, no escribe
stock.quant y nunca fuerza disponibilidad. Solo escribe lo mismo que la app: qty_done, cajas (put_in_pack) y la
validación normal.

v3.0.0 (10/11/2026): primera versión para probar con Isaac / Isaac2.
v3.0.1 (10/11/2026): foto del producto (la misma de la app) y flechas ◀ ▶ para ver la línea de antes o la siguiente;
tocar una línea de la lista la pone en grande. Al completar una línea salta sola a la siguiente.
v3.0.2 (10/11/2026): el punto del lector dice «Lector preparado» siempre (no hace falta tocar el campo); gris solo
sin conexión.
v3.1.0 (10/11/2026): tras probarla en Odoo: sin foto no sale el icono gris de Odoo; el nombre del producto una sola
vez y en grande con la talla destacada (atributo Talla o lo último del nombre); avisos cortos; «Todo en caja» solo
cuando hay algo leído; barra de progreso gruesa con el número dentro; el operario no se parte en la cabecera.
v3.2.0 (10/11/2026): «Faltante» sin lista: trabaja con la línea que se ve, enseña hasta 3 ubicaciones con stock
(la más cercana primero), se lee la ubicación de donde se coge y la línea pasa allí; «Tampoco está aquí» (dos
toques) la manda a faltantes. Sin cambios en el servidor.
""",
    'version': '13.0.3.2.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'koroshi_operarios', 'koroshi_faltantes'],
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

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
v3.2.1 (10/11/2026): en la hoja de Faltante las uds van debajo de la ubicación (las reales son largas).
v3.3.0 (11/11/2026): preparar a dos (necesita koroshi_operarios v2.4). El primero que empieza la OUT va por delante (orden
de la ruta) y el ayudante desde el final (líneas al revés). Cada uno cierra su caja solo con lo que ha leído él: lo del
compañero se aparta un momento y vuelve a su línea, sin caja. Valida cualquiera de los dos cuando todo está leído y en
caja; si no, «Falta que tu compañero cierre su caja» / «Faltan N uds por leer entre los dos». Cada 10 s se refresca lo
del compañero. Productividad: si otro ha leído la misma OUT, la tarea cuenta solo las lecturas propias. Campo nuevo
en_caja en koroshi.preparacion.lectura (tabla propia).
v3.4.0 (11/11/2026): preparar a dos, segunda parte (necesita koroshi_operarios v2.5). Cuando entra el ayudante, las líneas
pendientes se parten por la mitad en el orden de la ruta: el titular hace la primera y el ayudante la segunda; quien
acaba sigue con lo que quede de la del otro desde el extremo más lejano. Tabla nueva koroshi.preparacion.equipo (dónde
se partió y avisos). Al titular le sale una vez «X se ha unido: hace la segunda mitad (desde L..)». Si el compañero
manda algo a faltantes o lo cambia de ubicación, al otro le sale un aviso. La tarea se marca «a dos» con el compañero.
v3.5.0 (11/11/2026): más rápida en OUT grandes. Leer y Deshacer devuelven el estado ligero (solo cantidades y totales,
~4 KB en vez de ~46 KB en 141 líneas, sin leer productos ni fotos) y la PDA parchea el suyo; el refresco a dos también.
La lista de líneas se pinta solo si está abierta. La foto de la próxima línea pendiente se baja antes. Si el operario se
queda 3 s en una línea, se buscan ya las alternativas de Faltante y al pulsarlo salen al momento.
v3.6.0 (11/11/2026): no se queda colgada si Odoo va lento o se va la red. Cada lectura cuenta al momento en la PDA
(pita y +1) y Odoo la guarda detrás; si la rechaza, avisa y la quita. Lo pendiente se guarda en la memoria de la PDA y
se manda al volver (también si se cierra la app). Tiempo máximo de 20 s por petición: se vuelve a mandar con el mismo id.
«Otra PDA está guardando» ya no pierde la lectura: se vuelve a probar sola. Sin red se sigue leyendo y deshaciendo lo
no guardado; Caja y Validar dicen «Esperando conexión…» / «Guardando lecturas…».
v3.6.1 (11/11/2026): al perder la conexión, Caja y Validar cambian ya a «Esperando conexión…» (antes, a la lectura
siguiente). Probado en Odoo real: lectura al momento, Odoo lento, Deshacer sin guardar, app cerrada con pendientes,
reintento simultáneo (una sola ud) y sin red.
""",
    'version': '13.0.3.6.1',
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

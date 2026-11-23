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
v1.5.0 (18/11/2026): compactar un hueco (grabaciones del almacén del 18/11). En la lista del hueco cada contenedor
  tiene casilla: «Marcar vacíos», «Archivar marcados» (si alguno tiene prendas o reservas no se archiva ninguno: antes
  hay que ponerlo a cero) y «Mover marcados» (el siguiente hueco escaneado es el destino; prendas y reservas se
  conservan). Tocar el nombre abre el contenedor: «Poner a cero» (está vacío y Odoo dice que no; no se deja si hay
  prendas reservadas para una OUT, y dice cuál) y «Añadir prendas» (cada lectura = 1 ud; «Quitar la última»,
  «Guardar»). Estos dos son ajustes de inventario (movimiento hecho contra pérdidas de inventario, como Faltantes) y
  quedan en koroshi.contenedor.movimiento con quién, cuándo, artículo, uds y movimiento (campos nuevos producto_id y
  move_id, acciones «Poner a cero» y «Añadir prendas», solo en su tabla). Filtro «Ajustes de stock». /limpiar se
  queda para pantallas con el JS viejo en caché.
v1.6.0 (18/11/2026): pruebas del almacén con la 1.5.0. Botón «← Atrás» (un paso atrás: contenedor → hueco →
  lineal/artículo → inicio; tras «Mover marcados» vuelve al hueco; antes solo había «Empezar de nuevo»). El campo de
  lectura ya no saca el teclado de la PDA en cada lectura (inputmode=none, como Operarios); «⌨ Escribir» lo saca para
  teclear un lineal. Leer una prenda (EAN o referencia) dice dónde hay stock de ella, por hueco y contenedor, para
  devolver al sitio lo que está fuera de lugar (solo lectura). La persona se mantiene 15 min sin actividad (antes 3).
  Al mover: «Se han movido N contenedores». Añadir prendas: dos lecturas seguidas del mismo EAN cuentan dos (antes la
  segunda en menos de 0,7 s se perdía sin aviso; ahora solo se descarta la copia bus/campo de una misma lectura) y
  «Cantidad» pone N uds a la última lectura.
v1.7.0 (19/11/2026): pruebas del almacén con la 1.6.0. En el contenedor abierto, «Cambiar» al lado de cada artículo
  pone las uds reales (p. ej. 50 → 45): ajuste de inventario de la diferencia, + o −, como «Poner a cero»; no deja
  bajar de lo reservado para una OUT y dice cuál; queda en el registro como «Cambiar cantidad» (valor nuevo del campo
  acción de su propia tabla; entra en el filtro «Ajustes de stock»). Antes solo se podía poner a cero o añadir.
  Etiqueta rota: escribir un trozo del nombre (290726_44, sin KO_) lo busca: si hay uno (o el nombre entero existe)
  se abre; si hay varios, lista para elegir (20 como máximo). Con «⌨ Escribir», sugerencias desde 4 caracteres.
  Antes había que escribir el nombre entero con KO_. Los contenedores de la lista de mover tienen «Abrir».
v1.8.0 (19/11/2026): el almacén pide que el buscador sirva para todo lo que tiene código, no solo contenedores. La
  búsqueda por trozo (Intro) y las sugerencias (con «⌨ Escribir», desde 3 caracteres) dan contenedores, ubicaciones
  (código de barras o nombre: «L94 P35»), lineales (L94) y artículos (EAN, referencia o nombre: «2622JA00»), cada uno
  con su tipo. Tocar uno lo abre: el contenedor va a la lista de mover, la ubicación se abre, el lineal da su inventario
  y el artículo dice dónde está (ruta nueva /donde). Una ubicación nunca se abre sola por trozo (sería el destino de los
  contenedores en lista). «Atrás» vuelve a la lista de resultados. Leer la referencia entera de un artículo
  (2622JA00-000003-L) ya lo encuentra: 9.116 artículos no tienen referencia interna y la referencia está en el nombre.
  Solo lectura: no cambia nada del stock.
v1.8.1 (19/11/2026): solo ubicaciones de EFFECTIVE (compañía 8). UBRAN tiene los mismos huecos con el mismo código de
  barras (UBRAN/STOCK/N1/07828 - L94 P35 C1): leer «L94 P35 C1» daba «Hay 2 ubicaciones con el código… Avisa a IT»
  (fallo desde la 1.0 en los lineales que existen en las dos) y el inventario de un lineal y la búsqueda de la 1.8.0
  enseñaban huecos de las dos. Ahora toda búsqueda de ubicación (código leído, contenedor, lineal, trozo) se queda en
  la compañía 8 (o sin compañía).
v1.8.2 (19/11/2026): lineales de MU (MU-00…MU-14). Escribir «L70» ofrecía «Lineal L70» (inventario del lineal), pero
  con MU no salía: el lineal solo se reconocía como L + número, y sus huecos se llaman «MU-01 P00 C1» (el lineal al
  principio, sin «07828 - » delante), así que tampoco se encontraban. Ahora «MU-01» (o «mu1», «MU 01») abre el
  inventario de los 72 huecos de MU-01, y escribir el principio de un hueco («MU-00 P», «L70 P3») también ofrece su
  lineal arriba de la lista. Solo lectura.
v1.9.0 (20/11/2026): la tarjeta es la misma que en Lecturas y Faltante (con koroshi_operarios 2.22.0 y
  koroshi_faltantes 1.8.0). Al entrar se coge la tarjeta guardada en la PDA si tiene menos de 15 min sin actividad
  (la actividad en Lecturas también cuenta); pasar la tarjeta aquí la deja puesta en las otras pantallas. La
  inactividad de 15 min la quita solo de esta pantalla. Solo JS; nada en el servidor ni en la base de datos.
v1.9.1 (20/11/2026): la tarjeta ya no caduca a los 15 min sin actividad: dura lo que diga el parámetro
  koroshi_operarios.minutos_tarjeta (60 por defecto), que se lee al entrar. Necesita koroshi_operarios 2.22.1
  (instalarla antes); sin ella se queda en 60.
v1.9.2 (23/11/2026): con el cuadro de texto marcado, la lectura se quedaba escrita y no hacía nada (almacén,
  compactar): el campo solo leía con Intro al final y el lector puede acabar con tabulador. Ahora vale Intro o
  tabulador, como el Inicio PDA (koroshi_actividades 1.8.3). Solo JS.
v1.9.3 (23/11/2026): la 1.9.2 no lo arregló en las PDA: el lector no manda ni Intro ni tabulador al final. Odoo en
  el móvil lee cuando pasan 55 ms sin teclas, pero solo si no hay ningún campo marcado. Ahora, sin «⌨ Escribir», el
  campo lee solo cuando el lector para 150 ms. Con «⌨ Escribir» sigue igual (Intro y sugerencias). Solo JS.
v1.10.0 (23/11/2026): el almacén pide archivar un contenedor desde su ficha (abierto desde la lista de mover o del
  hueco); antes solo se podía con las casillas de la lista del hueco. Botón «Archivar» cuando no tiene prendas en el
  sistema (si tiene, antes «Poner a cero»), con la misma confirmación «¿está físicamente vacío?». Ruta nueva
  /koroshi/contenedores/archivar_uno; queda en el registro como «Archivar vacío» con quién lo hizo.
v1.11.0 (23/11/2026): «Poner a cero» con prendas reservadas para una OUT (el contenedor está vacío y Odoo las tiene
  reservadas: KO_310726_254, 23/11). Antes no se dejaba y no se podía archivar. Ahora, tras confirmar, cada línea
  reservada pasa por Faltantes como si el operario la marcara (koroshi_faltantes, sin cambiarlo): la OUT se reserva
  en el hueco con stock libre más cercano o, si no hay, sale sin ella; la unidad va a FALTANTE, queda su registro en
  Faltantes y una nota en la OUT. Si alguna línea ya tiene algo leído no se toca nada. Todo o nada. Depende ahora de
  koroshi_faltantes.
v1.12.0 (23/11/2026): «Cambiar» la cantidad de un artículo por debajo de lo reservado (KO_241026_115: 2 uds
  reservadas que no están y 18 de otro artículo que sí; «Poner a cero» se llevaría también las 18). Antes no se
  dejaba bajar de lo reservado. Ahora avisa de cuántas pasan a Faltantes y se confirma con otro «Guardar»: esas
  líneas pasan por Faltantes igual que en la 1.11.0 (solo las de ese artículo y solo las necesarias) y después se
  ajusta la diferencia. Todo o nada.
v1.13.0 (23/11/2026): correcciones de la revisión general del 23/11 (R1-R4, rastro y O6). Necesita koroshi_faltantes
  1.9.0 (se actualizan juntos). R1: «Cambiar» por debajo de lo reservado pasa a Faltantes solo la diferencia: una
  línea de 5 con 4 en el contenedor sigue con 4 reservadas aquí y solo 1 va a otro hueco (o la OUT sale sin ella) y
  a FALTANTE; antes se llevaba la línea entera, mandaba 5 a FALTANTE y volvía a crear 4 por ajuste. El hueco
  alternativo se busca entre todos, no solo en los 5 más cercanos. R2: «Cambiar» no se hace si hay prendas de ese
  artículo leídas para una OUT sin validar (el ajuste las quitaría otra vez al validar) ni si las uds de Odoo han
  cambiado desde que se abrió el contenedor: avisa y no cambia nada. R3: «Añadir prendas» lleva un id de tanda:
  reintentar tras cortarse la wifi ya no añade dos veces. R4: «Poner a cero» cierra en el acto como «No encontrado»
  lo que pasa a FALTANTE (el contenedor está vacío: ninguna ronda volverá a él); «Archivar» pasa los faltantes
  pendientes del contenedor a su hueco y no archiva si alguno está en una ronda abierta. Cada línea que pasa a
  Faltantes queda en el registro (acción «A Faltantes») y el faltante lleva la nota «Desde Contenedores (...)».
  La compañía sale de koroshi_base. Campos nuevos solo en koroshi.contenedor.movimiento (tanda, faltante_id).
v1.14.0 (23/11/2026): revisión general del 23/11 (R23), errores de talla. Botón «Es otro» al lado de «Cambiar» en el
  contenedor abierto: lo que Odoo llama A es en realidad B. Se lee una prenda de B, se ponen las uds (como mucho las de
  A) y en una sola operación sale A y entra B (dos ajustes contra pérdidas, como «Cambiar»), con UNA línea «Cambiar
  artículo» en el registro (artículo, artículo real y los dos movimientos; filtro propio). Si las uds de A reservadas no
  caben en lo que queda, pasan por Faltantes como en «Cambiar» (otro hueco o la OUT sale sin ellas). B entra libre; si
  hay OUT esperándolo, el mensaje lo dice (no se reserva nada). Mismo modelo = la referencia sin la talla final; si no
  lo es, aviso en rojo y otro «Guardar». No se hace con prendas de A o de B leídas sin validar en el contenedor ni si
  las uds de A han cambiado desde que se abrió; un reintento sin conexión no se repite (tanda). Campos nuevos solo en
  koroshi.contenedor.movimiento (producto_nuevo_id, move_nuevo_id). Diseño aprobado por Isaac:
  bin/versiones/diseno-cambiar-articulo_2026-11-23.md. Al actualizar, se actualiza también koroshi_menu.
v1.15.0 (23/11/2026): revisión general del 23/11 (O4, O5, R16). Necesita koroshi_base 1.2.0 (instalarla antes). La
  tarjeta compartida y el lector «leer al parar» de la PDA salen de koroshi_base (comun.js), igual que en Faltante,
  Devoluciones, Referencia y Prenda en el suelo: mismo comportamiento que la 1.9.3. En las rutas, el permiso, la
  tarjeta y la búsqueda de la prenda salen de koroshi_base.pda: la tarjeta tiene que ser de un operario activo de la
  compañía (antes bastaba con que existiera); la búsqueda es la misma que antes. Incluye la 1.14.0 (sin instalar).
""",
    'version': '13.0.1.15.0',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'stock', 'hr', 'barcodes', 'koroshi_base', 'koroshi_operarios', 'koroshi_faltantes'],
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

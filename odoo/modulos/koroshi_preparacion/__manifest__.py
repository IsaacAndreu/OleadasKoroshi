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
v3.7.0 (11/11/2026): leer una ubicación lleva a su línea; «Poner cantidad» (varias uds de golpe, solo tras leer una con
la pistola y sin pasar de lo que falta; Deshacer la quita entera); notas de la OUT arriba; los códigos de barras
alternativos del artículo cuentan al momento; botón «Imprimir» para volver a sacar la etiqueta de caja (OUT + matrícula,
sin reservar matrículas nuevas), la del transportista o el albarán.
v3.7.1 (11/11/2026): corrige la v3.7.0, que no se podía actualizar (el método «cantidad» tapaba el campo «cantidad» de
las lecturas); ahora se llama poner_cantidad.
v3.7.2 (11/11/2026): «Imprimir» daba 403 en la etiqueta de caja y el albarán (faltaba la empresa de la OUT en la
dirección del PDF); la etiqueta del transportista se abre en vez de descargarse.
v3.8.0 (11/11/2026): aspecto nuevo (solo CSS): cabecera oscura, tarjeta con sombra y franja de color, ubicación en un
bloque destacado, «Cogidas» en pastilla, flechas redondas, botones con relieve, líneas y avisos con franja de color.
Mismos tamaños de letra y de botón (guantes). Incluye la v3.7.2.
v3.9.0 (11/11/2026): sustituye el aspecto de la v3.8 (no instalada) por el estilo «etiqueta de estantería»: plano,
negro sobre blanco, sin sombras ni emojis. Cabecera negra, barra de progreso a todo el ancho, la ubicación pintada como
la etiqueta del rack (nave y hueco encima del código), foto de 150 px, talla en recuadro, cantidad en número grande con
una barrita por ud, botones planos y lista de líneas con separadores.
v3.9.1 (11/11/2026): las barritas por ud, la rueda de «Validando», la ✓ de las líneas y el icono de los avisos no se
veían: Odoo esconde todo lo que lleva aria-hidden="true". Ahora llevan role="presentation".
v3.9.2 (11/11/2026): ubicación con el hueco (lineal, palet, columna) y la caja KO en la misma línea y del mismo
tamaño («L44 P17 C2 | KO_110626_032»); la letra baja sola hasta que cabe (30 px en 480 de ancho, 22 px en 360).
Foto nítida (image_512 en vez de 256) y vertical 3:4, de 150 a 200 px de ancho.
v3.9.3 (11/11/2026): «Poner cantidad» se ve siempre que faltan 2 o más (antes, solo tras leer una). Antes de leer la
primera ud va en gris y al pulsarlo avisa «Lee primero una ud de X con la pistola».
v3.10.0 (11/11/2026): todo en una pantalla de PDA (360×640) sin mover arriba y abajo: sin la barra de menús de Odoo en
esta pantalla, cabecera y barra más bajas, «Sin caja» dentro de la barra, nota en 3 líneas como mucho, cantidad al lado
de la foto, Caja y Validar en la misma fila.
v3.11.0 (11/11/2026): abajo solo queda el campo «Leer producto o escribir EAN». Ver líneas e Imprimir etiqueta o
albarán pasan al menú ☰ de la cabecera. Leer con el menú abierto lo cierra y la lectura cuenta.
v3.12.0 (11/11/2026): Faltante con el mismo aspecto: «Prueba en» es una etiqueta negra grande (hueco y KO en la misma
línea) y los pasos van numerados: 1 coger la pieza, 2 leer la UBICACIÓN (no la prenda), 3 leer la prenda.
v3.13.0 (11/11/2026): RUTA ÓPTIMA por la nave (models/ruta.py: menos metros, saliendo de muelles y volviendo; en OUT
reales de 83 a 212 líneas, entre un 10 y un 22 % menos). TALLA HERMANA: si lee otra talla del mismo modelo, «Has leído
la talla L. Toca la M». AQUÍ MISMO: si la siguiente está en la misma parada lo dice. Sonido distinto para ud bien
leída, línea completa, caja cerrada y error.
v3.14.0 (11/11/2026): INT en la pantalla nueva (las que salen de EFFEC/Stock, p. ej. las de web a SORTER): mismo
picking y ruta, sin caja (sin botón Caja; se lee y se valida). La ronda de faltantes (desde FALTANTE) sigue en la app
de código de barras. Abrir más rápido: Lecturas precarga en segundo plano la pantalla y la OUT que toca (Continuar y
la siguiente tras «¡Hecho!» abren al momento y se refrescan justo después); el servidor mira las fotos de todos los
artículos de una vez.
v3.15.0 (11/11/2026): AGRUPACIONES DE ZONA (Z-) en la pantalla nueva, para los operarios de la lista: ya no se abre la
app de código de barras. La agrupación entera en UN solo recorrido (las líneas de todas sus OUT en el orden de la
ruta); cada pieza dice a qué caja de tienda va (banda amarilla «→ CAJA 05 · K34 ...», de la nota de la OUT). Si el
mismo artículo va a varias tiendas, cuenta en la línea que se ve. Leer una CJ cierra la caja de la tienda de esa
etiqueta (la reservó «Etiquetas de zona»: no hace falta pulsar «Caja»); una CJ de otra agrupación no se cierra.
Validar valida cada OUT con la validación de siempre (la agrupación se queda «En curso», como hoy). Faltante, Deshacer,
Poner cantidad e Imprimir (etiquetas y albaranes de todas las tiendas) también. «Volver» de la pantalla de Faltante
vuelve a la agrupación en la pantalla nueva. Parámetro nuevo koroshi_preparacion.agrupaciones ('1' / '0' = las Z- a
la app de siempre). Sin campos nuevos en tablas de stock; las OUT sueltas funcionan igual que en la v3.14.
v3.16.0 (12/11/2026): RUTA sin volver a los mismos pasillos. Al ordenar, cada cambio de pasillo cuenta 10 m de más
(models/ruta.py, PENAL_PASILLO): la ruta acaba lo que hay en un pasillo antes de irse y no vuelve al final por otro
tramo del mismo pasillo. En 14 OUT/INT reales grandes: +0,9 % de metros y 30 pasillos repetidos en vez de 125. Vale
para OUT, INT y agrupaciones Z-.
v3.16.1 (12/11/2026): las líneas VACÍAS (0 pedidas y 0 leídas, las deja la app de código de
barras de Odoo al leer en otra ubicación y deshacer) ya no salen ni cuentan: antes salían «0 de 0» y «la que toca»
volvía siempre a ellas (INT de web 67365). No se borran.
""",
    'version': '13.0.3.16.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'koroshi_operarios', 'koroshi_faltantes'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/parametros_v315.xml',
        'views/assets.xml',
        'views/lectura_views.xml',
    ],
    'qweb': [
        'static/src/xml/preparacion.xml',
    ],
    'installable': True,
    'application': False,
}

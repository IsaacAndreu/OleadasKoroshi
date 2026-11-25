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
v3.16.2 (12/11/2026): las ubicaciones MU- (al lado de los muelles) van al FINAL de la ruta, de vuelta a muelles, y no
al principio (el operario se las saltaba: «al principio no sigue el orden», EFFEC/OUT/24421). Se empieza igual;
solo la parada MU- pasa a la última (unos pocos metros más). (No llegó a instalarse.)
v3.17.0 (12/11/2026): ORDEN COMO LA APP DE CÓDIGO DE BARRAS por defecto: las líneas por el nombre de la ubicación
(00114 - L02..., 00221 - L03..., ..., MU-.., N1-..), igual que en la app de siempre. Parámetro nuevo
koroshi_preparacion.orden: 'ubicacion' (por defecto) o 'ruta' (la ruta optimizada de la v3.13-3.16.2, sin
desinstalar nada). Incluye lo de la v3.16.1 (sin líneas 0 de 0).
v3.18.0 (12/11/2026): LECTURA EQUIVOCADA. Si se lee un código numérico (EAN) que no es de ningún artículo y no empieza
por 8445962, la PDA dice «8410782105213 no es de ningún artículo: es otro código de la bolsa. Lee el de KOROSHI, el que
empieza por 8445962. No cuenta.» en vez de «Código desconocido». OUT, INT y agrupaciones.
v3.19.0 (12/11/2026): ZALANDO Y ABOUT YOU SIN ETIQUETA CJ. En las OUT de PED. MARKETPLACE (o cliente Zalando / About
You) «Caja» crea el paquete de Odoo (PACK0139...) sin leer nada, como «Put in pack» en la app de código de barras, y se
sigue leyendo. «Validar» mete solo en un paquete nuevo lo que el operario tenga leído fuera de caja y valida. Las OUT de
tiendas siguen con la etiqueta CJ. Incluye la v3.18.0 (no llegó a instalarse).
v3.20.0 (12/11/2026): ZALANDO / ABOUT YOU: EL NÚMERO DEL PACK. Al cerrar una caja sale una hoja con el número del
paquete en grande (PACK0139...), sus uds, «Apunta este número en la caja» y la lista de cajas de la OUT. Al validar,
la última caja (la que se cierra sola) sale igual, hasta pulsar «Hecho». Tocar «N cajas» arriba enseña la lista.
v3.21.0 (12/11/2026): CAMBIAR DE CAJA Y COLOR DE LA UBICACIÓN. En «Ver líneas», cada línea ya en caja tiene un ✎:
pasar 1 o más uds a otra caja de la OUT, a una caja nueva (Zalando / About You: PACK nuevo) o leyendo otra etiqueta
CJ (si no se mueve la línea entera se parte en dos, como hace Odoo al cerrar caja). Menú ☰ > «Color de la
ubicación»: cada operario elige entre 6 (A negra, B blanca, C amarilla, D azul, E en casillas, F amarilla grande;
por defecto F); se guarda por operario (tabla nueva koroshi.preparacion.preferencia). Incluye la v3.20.0 (no llegó a
instalarse).
v3.21.1 (12/11/2026): colores amarillos (C y F) con la letra más negra y gruesa; en F el código KO también en
negrita. Solo CSS.
v3.23.0 (12/11/2026): ALARMA DE PARADO + CAJA SIN INTERNET (la 3.22.0 no llegó a instalarse: todo va aquí, con la
v3.21.1). ALARMA DE PARADO. Con la OUT (o la agrupación) abierta y X minutos sin leer ninguna prenda, la
PDA pita sin parar (sirena aguda a volumen máximo del navegador, sin hacer caso del interruptor de sonido) y vibra, y la
pantalla parpadea en rojo con «¡LLEVAS N MIN SIN LEER!». Se para al contar una lectura (prenda, caja cerrada, Poner
cantidad, Faltante resuelto) o al salir con ← (dejar la OUT aquí). Deshacer, leer una ubicación o tocar la pantalla no
la paran. No cuenta mientras está en la pantalla de Faltante ni validando. Parámetro nuevo
koroshi_preparacion.minutos_alarma (por defecto 4; 0 = sin alarma). Solo suena en horario de trabajo: parámetro
koroshi_preparacion.horario_alarma (por defecto 06:00-10:00,10:15-13:00,14:00-17:00, hora de la PDA); en la pausa de
10:00-10:15 y la comida de 13 a 14 no suena ni cuenta. Los dos en Ajustes KOROSHI (koroshi_menu v1.3).
CAJA SIN INTERNET. Sin conexión, «Caja» (y leer la CJ) ya no espera: la caja se cierra en la PDA (lo
leído fuera de caja pasa a ella) y va a la cola de la PDA en su sitio, con las lecturas, y también a su memoria (si se
cierra la app, no se pierde). Al volver la conexión Odoo la cierra en el mismo orden (lo leído antes va a esa caja; lo de
después, fuera) con el mismo id (no se cierra dos veces). La PDA comprueba lo mismo que Odoo: etiqueta CJ, que haya algo
fuera de caja y, en una agrupación, de qué tienda es la CJ (el estado trae ahora las CJ reservadas de cada OUT, «cjs»).
Zalando / About You: sin red la caja sale como «S<n>» para apuntarla; al volver la conexión sale su PACK y en la lista
«era S<n>». Si Odoo no acepta una caja guardada así, avisa y lo leído queda fuera de caja para cerrarla otra vez.
Validar sigue necesitando conexión.
v3.24.0 (13/11/2026): TIPO DE CAJA. Al cerrar una caja el operario elige el tipo (las cajas de Consumibles
marcadas «Es una caja»: Grande 590x390x400, 60x40x40, Mediana, Online 280x280x120). Se recuerda por operario.
Odoo pone a la caja su «Tipo de paquete» y resta 1 en Consumibles (solo si la caja es nueva en la OUT; nunca para
el cierre). Zalando / About You: «Caja» enseña los tipos y tocar uno cierra la caja; la última caja al validar va
con el último tipo elegido. En la lista de cajas sale el tipo. Depende de koroshi_consumibles (v1.2).
v3.24.1 (13/11/2026): se lee la CJ y luego se toca qué caja es (también al revés). Ninguna sale marcada: la caja
no se cierra hasta que digan el tipo (también la CJ leída en una agrupación). Botones más grandes y legibles.
La 3.24.0 no se instaló.
v3.24.2 (13/11/2026): el aviso de sin conexión en una línea y más corto («Sin conexión · se guarda en la PDA»).
Las 3.24.0 y 3.24.1 no se instalaron.
v3.24.3 (13/11/2026): cerrar caja con tipo también sin conexión; la caja cerrada sin red enseña su tipo en la lista.
Ninguna 3.24.x anterior se instaló.
v3.25.0 (13/11/2026): una OUT de una zona (Z-) se prepara sola cuando se lee la OUT (koroshi_operarios 2.9). Se valida
como en la agrupación (sin el «se valida desde la agrupación» de Faltantes). La zona entera, leyendo la Z-.
v3.26.0 (13/11/2026): «⏸ Pausa (comer, café)» en el menú ☰ (dos toques): guarda lo leído, para el tiempo (motivo
pausa de koroshi_operarios 2.10+) y vuelve a Lecturas sin operario. Al volver, tarjeta y sale la misma OUT.
v3.27.0 (13/11/2026): ZALANDO / ABOUT YOU SE VALIDAN INCOMPLETAS (van por bultos). Con líneas sin leer,
«Validar» avisa de cuántas uds faltan y el botón pasa a «⚠ Validar incompleto» (8 s): con el segundo toque se
valida lo leído y lo que falta queda en una OUT pendiente (aunque pedido_pendiente sea 'no'), con una nota en las
dos para revisar si se han hecho menos cajas. El resto de pedidos, como antes (léelas o «Faltante»).
v3.27.1 (13/11/2026): línea ya cogida: la franja de la ubicación (y el KO) se queda con su color y se lee bien;
lo que se pone verde es el fondo de la tarjeta.
v3.28.0 (13/11/2026): ✎ en una línea ya en caja: «↩ Sacar de la caja (va a la siguiente)». Las uds vuelven a
fuera de caja y entran en la caja siguiente al cerrarla. Sustituye a «+ Caja nueva» (Zalando / About You), que
hacía un PACK con solo esas uds.
v3.28.1 (13/11/2026): ✎ también en la tarjeta, al lado de «En la caja X» (sin entrar en la lista).
v3.29.0 (13/11/2026): ROBUSTEZ (auditoría del 13/11). Una caja cerrada SIN CONEXIÓN que Odoo no acepta PARA la cola de
la PDA: antes seguía y la caja siguiente se llevaba sus uds. Ahora pide otra etiqueta CJ, «Probar otra vez» o «Dejar lo
leído fuera de caja». Mover de caja, Deshacer y Validar llevan id_lectura, tiempo máximo y reintentos con el mismo id:
no se hacen dos veces; Validar contesta «validada» si la OUT ya lo está y bloquea la OUT (y la agrupación) mientras
valida. Al volver la conexión, si la OUT ya está hecha, vuelta a Lecturas. Lo que la PDA manda desde su cola y Odoo no
aplica (OUT ya validada, caja rechazada, error de Odoo, más de 24 h en la PDA) queda SIEMPRE apuntado: menú
«Lecturas rechazadas de cola» para el encargado (campo nuevo «diferida» en koroshi.preparacion.lectura, tabla propia).
Restricción única (OUT, titular, ayudante) en koroshi.preparacion.equipo: la migración borra antes los repetidos
(EFFEC/OUT/24410, ids 4 y 5) y, si dos PDA lo crean a la vez, la segunda usa el de la primera. Los «except: pass»
dejan el error en el log. Estado ligero (tras cada lectura y el refresco a dos): solo líneas, totales y lo de a dos;
lo fijo (OUT, notas, tipos de caja, alarma) solo en /cargar. Agrupaciones Z-: las OUT vivas una vez por petición.
Tests: tests/test_ruta.py (sin base de datos) y tests/test_idempotencia.py (TransactionCase). Sin campos nuevos en
tablas de stock.
v3.30.0 (14/11/2026): PAUSA ARRIBA. Botón ⏸ al lado del ☰ (dos toques): para el tiempo (motivo «Pausa» de
Operarios) y la pantalla se queda tapada con «EN PAUSA»; ▶ Seguir vuelve a empezar el tiempo con la misma OUT sin
leer la tarjeta ni salir. En pausa no se lee ni suena la alarma de parado. Sale del menú ☰. A dos (ayudante),
como antes. FALTANTE: si la ubicación más cercana tiene pocas uds (menos de 3 o no llega), la segunda también
sale en grande («Si no, aquí»).
v3.31.0 (16/11/2026): auditoría 13/11, fase 6 (pasar a koroshi_base). La empresa y la expresión de la matrícula CJ
de Python salen de koroshi_base.comun (la misma: CJ + 9 cifras). La pantalla de la PDA (JS) no cambia: su expresión
lleva /i y no recorta espacios, y pasarla a koroshi_base.comun cambiaría qué se acepta. Sin campos ni vistas
nuevas. Depende de koroshi_base. Incluye la 3.30.0, sin instalar (en el servidor, la 3.29.0 desde el 16/11).
v3.32.0 (17/11/2026): botón «Sin caja (bolsa) → expediciones» en la hoja de caja (dos toques), solo en una OUT suelta
con CJ y con operario. Para OUT pequeñas (1-3 uds) que van en bolsa: la OUT NO se valida; lo leído queda fuera de
caja y la OUT pasa a expediciones con el motivo «Sin caja» (koroshi_operarios 2.17, instalarlo a la vez). Expediciones
la mete en caja con su CJ y la valida, así que a S4T no le llega nada sin caja. Vuelta a Lecturas y la siguiente.
Sin campos ni vistas nuevas.
v3.33.0 (17/11/2026): RONDA DE FALTANTES EN LECTURAS (necesita koroshi_faltantes 1.7.0, instalar a la vez). La INT de
la ronda (origen «RONDA FALTANTES») se abre aquí leyendo la INT, como una OUT. Se va a la ubicación DESTINO de cada
línea (la pieza sale de FALTANTE o, en los puestos a 0, de pérdidas). Si está, se lee la prenda; si no, «No está» o
«La ubicación no existe» (dos toques, en lugar de «Faltante»): la línea desaparece y se pasa a la siguiente. Validar:
lo leído se valida y lo demás se cancela (sin pedido pendiente); con todo marcado y nada leído, la INT se cancela. El
resultado se aplica al momento (koroshi_faltantes). Sin campos ni vistas nuevas.
v3.34.0 (23/11/2026): revisión general del 23/11, entrega 2 (R5-R8). R5: lo leído se escribe en la base de datos antes
de calcular el estado y fuera de su try; antes, si esa escritura fallaba (dos PDA a la vez), la PDA recibía «ok» y no
se guardaba nada. R6: /validar deja en el log una línea con los ms de cada tramo (comprobaciones, validar con el
asistente de pedido pendiente, cierre de tarea y estado) y el transportista, para decidir con datos si XPO/S4T van a
una cola; y al validar solo se cierran la tarea y la asignación de esa OUT (o agrupación), no cron_cerrar() de todo
el almacén dentro de la transacción (el cron de 5 min sigue haciendo el resto). R7: el estado ligero trae la
ubicación de cada línea y, si ha cambiado (Contenedores, Faltantes), la PDA carga la OUT entera; yendo solo también
se refresca cada koroshi_preparacion.refresco_solo_s segundos sin leer (30; 0 = no). R8: mientras se cierra una caja
con red, el botón Caja está apagado («Cerrando caja…») y una CJ leída no cuenta. Sin campos ni vistas nuevas; un
parámetro nuevo. No toca koroshi_operarios (usa sus métodos de tarea y asignación).
v3.35.0 (23/11/2026): revisión general del 23/11 (R16). Incluye la 3.34.0 (sin instalar). Necesita koroshi_base 1.2.1
(instalarla antes). Las rutas de Lecturas que escriben (leer, deshacer, caja, cantidad, color, mover caja, marcar de la
ronda y validar) piden permiso de Inventario y una tarjeta válida: la misma regla que Operarios (activo, con tarjeta y
de la empresa), de koroshi_base.pda. Antes aceptaban cualquier employee_id. Si no vale, rechazo normal («Pasa otra vez
tu tarjeta»), no se guarda y queda una línea WARNING en el log; sin tarjeta, como antes. Lo aprobó Isaac el 23/11.
Las rutas que solo leen (modo, cargar, rechazadas, impresos) no cambian. Sin campos nuevos.
v3.36.0 (25/11/2026): «Caja llena» por volumen (diseño del 25/11, V1-V3 aprobados por Isaac; caso K1 MAQUINISTA D2: dos
cajas físicas en una CJ). Barra con el volumen de mis uds leídas sin caja (product.product.volume; sin volumen = la media
de la OUT) frente a la capacidad de mi último tipo de caja (si no hay, la 600X400X400). Verde; naranja «Casi llena» del
90 %; al 100 % pitido y «Caja llena: cerrar» (abre Caja) / «Aún cabe más» (no vuelve a preguntar hasta el 115 %); al 115 %
aviso rojo «¿Son dos cajas?». Nunca bloquea. También en agrupaciones Z- (la caja de la tienda de lo último leído). Cada
respuesta y la CJ que se cierra después quedan en la tabla nueva koroshi.preparacion.caja_llena (menú «Respuestas "Caja
llena"») para el Monitor. Parámetros sin crear (valen los de por defecto): caja_llena_activa (1/0),
caja_llena_capacidades (600X400X400=0.090;MEDIANA=0.060) y caja_llena_umbrales (90,100,115). Volúmenes de cada OUT en
memoria 10 min: leer no vuelve a leer productos. Sin campos nuevos en tablas compartidas.
v3.36.1 (25/11/2026): capacidades por defecto de «Caja llena» a 600X400X400=0.100 y MEDIANA=0.075 (antes 0.090 y
0.060), lo pidió Isaac. Con las cajas cerradas en 7 días (Monitor: 600X400X400 p50 0,082, p90 0,102, p98 0,117; MEDIANA
p90 0,067, p98 0,088) la pregunta del 100 % sale hacia el p90 y el aviso del 115 % hacia el p98, no en 1 de cada 4 cajas.
El parámetro caja_llena_capacidades, si se crea, sigue mandando.
""",
    'version': '13.0.3.36.1',
    'author': 'NATH',
    'category': 'Warehouse',
    'license': 'LGPL-3',
    'depends': ['web', 'hr', 'stock', 'stock_picking_batch', 'stock_barcode', 'koroshi_base', 'koroshi_operarios', 'koroshi_faltantes',
                'koroshi_consumibles'],
    'data': [
        'security/ir.model.access.csv',
        'data/parametros.xml',
        'data/parametros_v315.xml',
        'data/parametros_v317.xml',
        'data/parametros_v322.xml',
        'data/parametros_v334.xml',
        'views/assets.xml',
        'views/lectura_views.xml',
        'views/caja_llena_views.xml',   # v3.36
    ],
    'qweb': [
        'static/src/xml/preparacion.xml',
    ],
    'installable': True,
    'application': False,
}

# KOROSHI Preparación en Lecturas (v3.14.0, 11/11/2026)

Pantalla de preparación propia dentro de **Lecturas (PDA)**. El operario lee su tarjeta, se abre su OUT y la prepara
entera sin salir a la app de código de barras: leer productos, cerrar cajas con la etiqueta CJ y validar.

## v3.14.0: INT y abrir más rápido (11/11/2026)

**INT.** `picking_propio` acepta también las transferencias internas de la company 8 que salen del stock del tipo
(`default_location_src_id`, EFFEC/Stock): las de web (`WEB_…`, de EFFEC/Stock a SORTER, 33–153 líneas, sin cajas).
Se preparan igual (ruta óptima, talla hermana, «Aquí mismo», Faltante) pero **sin caja**: `_con_caja` = solo OUT; en
las INT no hay botón Caja ni «Sin caja», y Validar no pide caja. Las INT que salen de otro sitio (la ronda de
faltantes, desde FALTANTE) siguen abriéndose en la app de código de barras. En Lecturas la tarea se sigue apuntando
como «Pedido (OUT)» (el modelo de tareas solo tiene OUT y agrupación).

**Abrir más rápido.** Medido antes (Odoo real): abrir una OUT eran 4 llamadas seguidas (Lecturas apunta la tarea,
`/modo` ~0,09 s, cargar la acción ~0,09 s, `/cargar` 0,2 s con 2 líneas y 0,68 s con 189 líneas).
- Lecturas precarga en segundo plano, con la OUT que toca a la vista («Estás haciendo») y con la siguiente mientras
  cuenta «¡Hecho!»: la acción de la pantalla (una vez), `/modo` y `/cargar` (válido 90 s). Al abrir, sin preguntar ni
  esperar: la pantalla se pinta con lo precargado y se refresca justo después.
- `estado()`: si cada artículo tiene foto se mira de una vez (`bin_size`), no una consulta por artículo.

## v3.13.0: ruta óptima, talla hermana, «Aquí mismo» y sonidos (11/11/2026)

**Ruta óptima** (`models/ruta.py`). Las líneas ya no van por el nombre de la ubicación sino por el camino más corto
andando, con la geometría del plano de `koroshi_warehouse_map`:
- lineales L01–L136 en parejas espalda con espalda; el pasillo de picking está entre L02|L03, L04|L05… (2 m entre
  pasillos); posiciones P01–P36 de 1,2 m; pasillos transversales delante de P01, después de P03, el central (P17|P18),
  después de P24 y al final;
- se sale de los muelles (lado de L01) y se vuelve; la altura (C1–C4) es la misma parada (se coge de abajo arriba);
- vecino más cercano + 2-opt; se guarda en memoria por OUT (0,06 s con 200 paradas).
- `MU-…` = encima de los muelles 15–18. `N1-L…` (zona N1, sitio desconocido) y lo que no es un lineal: al final,
  por nombre.

Comparado con el orden de antes en OUT validadas: 212 líneas 1905 → 1474 m; 209 líneas 1976 → 1562 m;
195 líneas 1933 → 1542 m; 171 líneas 1016 → 870 m; 124 líneas 798 → 705 m; 83 líneas 514 → 440 m.

Preparar a dos: la mitad se corta por el puesto en la ruta (la línea del corte o la primera de su ubicación).

**Talla hermana.** Si lee una talla del mismo modelo (`MODELO-COLOR-TALLA`) que no es la del pedido, o una talla ya
completa, y hay otra talla del modelo pendiente: «Has leído la talla L. Toca la M de 2621PT26-000306. No cuenta.» y se
ve la línea de la talla que toca.

**Aquí mismo.** Cada línea lleva su `parada` (pasillo y posición). Si quedan más líneas en la misma parada, la tarjeta
lo dice en amarillo («AQUÍ MISMO: 2 más») y al completar una línea, si la siguiente está en la misma parada, el aviso
dice «AQUÍ MISMO: ahora X · talla».

**Sonidos** (`_sonar`): ud bien leída = pip corto; línea completa = dos notas que suben; caja cerrada = tres notas que
suben; error = zumbido grave. La vibración también cambia.

## v3.12.0: Faltante más claro (11/11/2026)

- «Prueba en»: la ubicación más cercana en etiqueta negra grande (hueco y KO en la misma línea); las demás debajo.
- Pasos numerados: 1. Ve a la ubicación y coge la pieza. 2. Lee la etiqueta de la **UBICACIÓN** (no la prenda).
  3. Después lee la **prenda**, como siempre. (Leer la ubicación mueve la línea a esa ubicación; la prenda se lee
  después en la tarjeta normal.)

## v3.11.0: menú ☰ en la cabecera (11/11/2026)

Debajo de los botones solo queda el campo del código. «Ver líneas» e «Imprimir etiqueta o albarán» no se quitan: van
en el menú ☰ de la cabecera (hoja inferior «Más»). «Ver líneas» abre la lista debajo del campo del código y baja hasta
ella; «Imprimir» abre la hoja de imprimir de la v3.7. Si se lee un código con el menú abierto, se cierra y la lectura
cuenta (modo `menu`).

## v3.10.0: todo en una pantalla, sin mover arriba y abajo (11/11/2026)

Medido en Odoo real a 360×640 (PDA pequeña), mirando otra línea (el caso más alto, con «Ir a la que toca»): la fila de
Faltante/Deshacer acaba en 623 px (antes había que bajar unos 400 px).

- En esta pantalla no sale la barra de menús de Odoo (`body.o_kp_pantalla_pda`, se pone en `start` /
  `on_attach_callback` y se quita en `on_detach_callback` / `destroy`; las otras pantallas la siguen teniendo).
- Cabecera y barra de progreso más bajas; «Sin caja» y nº de cajas dentro de la barra.
- Nota de la OUT: «NOTA» delante y 3 líneas como mucho.
- Tarjeta: flechas más bajas; la cantidad grande, las barritas y «Poner cantidad» van a la derecha de la foto.
- Caja y Validar en la misma fila (como Faltante y Deshacer). Botones de 52 px (siguen siendo para guantes).
- PDA de 700 px de alto o menos: foto de 100 a 140 px de ancho.
- Lo que queda debajo (Ver líneas, Imprimir, campo de código) sí necesita bajar: se usa poco.

## v3.9.3: «Poner cantidad» siempre a la vista (11/11/2026)

El botón sale en toda línea a la que le faltan 2 o más uds, para que los operarios sepan que existe. Si aún no se ha
leído ninguna ud con la pistola va en gris (borde discontinuo) y al pulsarlo no abre nada: avisa «Lee primero una ud de
X con la pistola. Después pon el resto.» (se mantiene la comprobación del artículo; el servidor también la exige).

## v3.9.2: ubicación entera en una línea y foto nítida (11/11/2026)

- **Ubicación:** el hueco (lineal, palet, columna) va al lado del KO, en la misma línea y del mismo tamaño:
  `L44 P17 C2 | KO_110626_032`. Encima, pequeño, la nave y el número del hueco (`NAVE2 · 28035`). Sale de
  `ubicacion_completa` (`_partesUbicacion`: quita el «28035 - » del padre). Si el padre es la nave (perchas), solo el código.
- La letra se ajusta sola (`_ajustarUbicacion`, de 30 px hacia abajo hasta que quepa): 30 px a 480 de ancho,
  22 px a 360 (19 px con huecos largos como `N1-L12 P08 C2`). La etiqueta negra ocupa todo el ancho de la tarjeta.
- **Foto:** `image_512` (con `image_256` se veía borrosa en pantallas de alta densidad) y caja vertical 3:4 de 150 a
  200 px de ancho. Probado con vaqueros y pantalones con foto a 360×740 y 480×854.

## v3.9.1: lo que no se veía por aria-hidden (11/11/2026)

Odoo 13 trae una regla global `[aria-hidden="true"] { display: none }`. Por eso no se veían las barritas por ud (v3.9),
la rueda de «Validando…», la ✓ de las líneas hechas, el icono de los avisos (✓ ℹ ⚠ ✖) ni el ⚠ del aviso sin conexión.
Ahora llevan `role="presentation"`. No usar `aria-hidden="true"` en las pantallas de la PDA.

## v3.9.0: aspecto «etiqueta de estantería» (11/11/2026)

La v3.8 (tarjetas redondeadas con sombras y emojis) no convenció y no se instaló: el bloque v3.8 del CSS se ha quitado.
La v3.9 sigue lo que hacen las apps de picking (Zebra, Microsoft, pick-to-light): plano, alto contraste, una cosa grande.

- Cabecera negra; la barra de progreso va a todo el ancho justo debajo y, después, la nota de la OUT.
- La ubicación se pinta como la etiqueta física del rack: fondo negro, nave y hueco en pequeño encima
  (`_detalleUbicacion`, de `ubicacion_completa`), el código grande en letra de ancho fijo y una franja tipo código de
  barras. Verde cuando la línea ya está cogida.
- Foto de 150 px (antes 110), referencia y talla en un recuadro negro.
- Cantidad en número grande («1 de 5») debajo de la foto y una barrita por ud (de 2 a 20 uds).
- Botones planos sin sombra: Caja amarillo, Validar verde, Faltante naranja, Deshacer blanco con borde.
- Lista de líneas con separadores (no tarjetas); sin emojis en los textos.

Probado en Odoo real a 480×854 (tamaño PDA) aplicando el estilo en la pestaña antes de instalar.

## v3.8.0: aspecto nuevo (11/11/2026)

Solo CSS (bloque «v3.8» al final de `preparacion.css`), sin tocar la lógica: cabecera oscura (#14243b, el color del
icono de la app), tarjeta de la línea con sombra y franja a la izquierda (azul = la que toca, a rayas = otra, verde =
hecha), ubicación en un bloque destacado con 📍, «Cogidas X de Y» en pastilla, flechas redondas, botones con relieve,
notas, avisos y líneas con franja de color, hoja inferior con asa. Los tamaños de letra y botones no bajan.
Incluye la v3.7.2.

## v3.7.2: Imprimir sin 403 (11/11/2026)

La etiqueta de caja y el albarán daban 403: la dirección del PDF no llevaba la empresa de la OUT y Odoo (multiempresa)
no dejaba verla. Ahora va con `?context={"allowed_company_ids": [empresa de la OUT]}`. La etiqueta del transportista se
abre en vez de descargarse. Probado en Odoo real: los dos informes salen en PDF (200) y las etiquetas XPO también.

## v3.7.1: corrige la actualización de la v3.7.0 (11/11/2026)

La v3.7.0 fallaba al actualizar («El campo `cantidad` no existe»): el método nuevo `cantidad` tenía el mismo nombre que
el campo `cantidad` de las lecturas y lo tapaba. Ahora el método es `poner_cantidad`. Sin cambios para el operario.

## v3.7.0: más cómoda para almacén (11/11/2026)

Lo que tenía la app de código de barras y faltaba aquí:

| Qué | Cómo funciona |
|---|---|
| Leer una ubicación | Si es la de alguna línea (la caja KO_ o el hueco), se ve esa línea (la primera pendiente). Si no hay nada del pedido allí, aviso rojo. No cuenta como lectura. |
| ✎ Poner cantidad | Sale en la línea que se ve si ya tiene **al menos 1 ud leída con la pistola** (el producto está comprobado) y faltan 2 o más. Se escribe el número o «Todas las que faltan». Nunca pasa de lo que falta. Va por la misma cola que las lecturas (cuenta al momento, se guarda detrás). Deshacer la quita entera (−n). En las lecturas queda como «A MANO +n». |
| Notas de la OUT | El campo Notas de la OUT sale arriba en ámbar. |
| Códigos alternativos | Los otros EAN del mismo artículo (product_multi_barcode: EAN antiguo, de proveedor…) cuentan al momento como el principal. |
| 🖨 Imprimir | Etiqueta de caja (OUT + matrícula: las que la OUT ya tiene; no reserva nuevas), etiquetas del transportista (PDF adjuntos a la OUT) y albarán. Abre el PDF y se imprime desde ahí. |

Servidor: rutas nuevas `/koroshi/preparacion/cantidad` y `/koroshi/preparacion/impresos`.

## v3.6.1: «Esperando conexión…» al momento (11/11/2026)

Al perder la conexión, Caja y Validar cambian ya el texto (en la v3.6.0 lo hacían a la lectura siguiente).

Pruebas de la v3.6 en Odoo real (11/11, Isaac2, OUT de prueba EFFEC/OUT/24749, 10 uds, cancelada al acabar):

| Prueba | En la PDA | En Odoo |
|---|---|---|
| 6 lecturas seguidas | +1 al momento en cada una | 6 uds, 6 lecturas, ningún id repetido |
| Odoo lento (8 s por lectura) | al momento; a los 5 s «Odoo va lento…»; Validar «Guardando lecturas…» | todo guardado |
| Deshacer antes de guardar | −1 al momento | la deshecha no llega nunca |
| App cerrada con 2 pendientes | al abrir, «Guardando 2 lecturas que quedaron…» | las 2, una sola vez |
| Misma lectura dos veces a la vez | — | una guarda, la otra «ocupada» (se reintenta); reintentos «repetida»; 1 ud |
| Sin red | cuenta y queda en la memoria; al volver se manda | 1 ud, sin duplicados |
| Código de otro producto | espera a Odoo: «no es de este pedido» | no cuenta |

## v3.6.0: no se queda colgada si Odoo va lento o se va la red (11/11/2026)

- **La lectura cuenta al momento.** Si el código es de un producto de la OUT con uds pendientes, la PDA pita y suma +1
  sin esperar a Odoo, y lo manda detrás (en cola, uno a uno, con `id_lectura`). Arriba: «⏳ N guardándose». Si Odoo la
  rechaza, avisa «No se ha guardado …» y deja de contar (se pinta lo que dice Odoo). Los códigos que la PDA no conoce
  (códigos alternativos, tarjetas, otros productos) esperan a Odoo como antes.
- **Memoria de la PDA.** Las lecturas pendientes se guardan en `localStorage` (`koroshi_preparacion_cola`, por OUT).
  Si se cierra la app o se reinicia la PDA, al abrir otra vez la preparación se mandan: las de esa OUT se ven sumadas;
  las de otras OUT se mandan solas en segundo plano. Más de 24 h: no se mandan.
- **Nunca colgada.** Cada petición tiene 20 s como máximo; si Odoo no contesta (o se está reiniciando, 5xx), se vuelve
  a mandar con el mismo id (no cuenta dos veces). A los 5 s sale «Odoo va lento: lo leído se guarda igual».
  «Otra PDA está guardando» (`que: 'ocupada'`, excepción `Ocupada`) se vuelve a probar sola en 1,5 s en vez de perder
  la lectura; el bloqueo de la OUT va en un savepoint.
- **Sin red** se sigue leyendo (lo que la PDA puede comprobar) y Deshacer quita lo aún no guardado. Caja y Validar
  esperan a Odoo: «⏳ Esperando conexión…» / «⏳ Guardando lecturas…». Con lecturas por guardar y con red, «←» espera.
- Sesión caducada: avisa y no pierde nada (queda en la PDA).

## v3.5.0: más rápida en OUT grandes (11/11/2026)

Sale del plan de rendimiento del 10/11 (`bin/versiones/20261110_PLAN_preparacion_v3.3_rendimiento.md`).

- **Lectura ligera.** `leer` y `deshacer` (y el refresco de cada 10 s a dos) devuelven solo
  `[id, pedidas, leídas, caja, completa]` de cada línea, en el orden de la ruta, y los totales. Nada de nombre, talla,
  foto, EAN ni ubicación: el servidor no lee productos ni fotos. En una OUT de 141 líneas, ~4 KB en vez de ~46 KB.
  La PDA parchea su estado; si ve una línea que no conoce (la caja del compañero parte líneas), carga la OUT entera.
  `cargar`, `caja` y `validar` siguen devolviendo el estado entero.
- **Lista de líneas** («Ver líneas»): se pinta solo si está abierta, y al abrirla.
- **Foto**: se baja antes la de la próxima línea pendiente; al llegar a ella ya no hay hueco en blanco.
- **Faltante**: si el operario se queda 3 s en una línea sin leer, se buscan ya las alternativas (en segundo plano).
  Al pulsar «Faltante» salen al momento y se vuelven a pedir por si ha cambiado el stock. Valen 2 minutos.

Nada cambia en lo que se escribe en Odoo.

## v3.4.0: preparar a dos, segunda parte (11/11/2026)

Necesita **koroshi_operarios v2.5.0**.

- **Por la mitad:** al entrar el ayudante, las líneas pendientes se parten en dos en el orden de la ruta
  (`koroshi.preparacion.equipo` guarda la primera línea de la segunda mitad). Titular: su mitad hacia delante y luego
  lo que quede de la otra desde el final. Ayudante: la segunda mitad hacia delante y luego lo que quede de la primera
  desde el corte hacia atrás. Cabecera: «Nombre · 1ª mitad / 2ª mitad · con X».
- **¿Ayudarle?** (koroshi_operarios): leer la OUT de otro pregunta antes de entrar. Como mucho dos por OUT.
- **Aviso al titular** (una vez): «X se ha unido: hace la segunda mitad (desde L.. P.. C..)».
- **Faltantes del compañero:** si manda algo a faltantes o lo cambia de ubicación, al otro le sale «X ha mandado a
  faltantes Y: no lo busques» / «X ha cambiado Y a Z» (en el refresco de 10 s).
- **Reparto** (koroshi_operarios): en Colas, «A dos» para las OUT grandes (≥ `koroshi_operarios.uds_a_dos`, 150) y
  columna Ayudante: cuando el titular empieza, al ayudante le sale sola.
- **Informes:** la tarea queda «A dos» con el compañero; en Productividad, agrupar por «A dos / solo» compara uds/hora.
- **Monitor:** las uds en curso de cada operario a dos son solo las suyas (`_uds_hasta_ahora`; el cambio del monitor
  va con su próxima versión).

## v3.3.0: preparar a dos (11/11/2026)

Necesita **koroshi_operarios v2.4.0**.

- **Unirse:** un segundo operario lee con su tarjeta una OUT suelta que ya está haciendo otro. Antes salía «está asignada
  a X»; ahora entra de **ayudante**. La asignación sigue siendo del titular.
- **Orden:** el titular (el primero que empezó) ve las líneas en el orden de la ruta; el ayudante, **al revés**, y la
  pantalla le lleva a la última pendiente. Se encuentran en medio. Cabecera: «Nombre · ayudante (desde el final) · con X».
- **Cajas:** «Caja» mete **solo lo que ha leído ese operario**. Lo del compañero se aparta un momento (qty_done sin lo
  suyo), se hace el mismo `put_in_pack(package_name=CJ)` de siempre y se devuelve a su línea sin caja. Si Odoo no deja la
  línea como se espera, no se cierra nada y avisa. Cada lectura guarda en `en_caja` la caja donde ha ido.
  Titular: lo leído en la app de código de barras o sin tarjeta cuenta como suyo (como antes).
- **Validar:** cualquiera de los dos, cuando todo está leído y en caja. Si no: «Falta que tu compañero cierre su caja
  (N uds)» o «Faltan N uds por leer entre los dos».
- **Refresco:** cada 10 s se recarga la OUT para ver lo del compañero; si él valida, se vuelve a Lecturas.
- **Productividad:** si en el tiempo de la tarea otro operario ha leído la misma OUT en esta pantalla, la tarea cuenta
  solo sus lecturas (`models/tarea.py`). En la app de código de barras de siempre no hay lecturas por operario: allí,
  a dos, cada uno se sigue contando todo.
- Solo, sin compañero, todo funciona igual que la v3.2.1.

## v3.2.1

- Hoja de Faltante: las uds libres van debajo de la ubicación; con las ubicaciones reales («L87 P23 C2 · KO_130826_523»)
  la verde se partía en 4 líneas.

## v3.2.0: Faltante de la línea que se ve

- «Faltante» ya no abre la lista: trabaja con la **línea que está en pantalla** (la que toca o la elegida con ◀ ▶).
- Sale una hoja con la foto, el nombre y la talla, «No está en X» y hasta **3 ubicaciones con stock libre**, la más
  cercana primero (mismo orden que koroshi_faltantes: el lineal más cercano y después más uds).
- El operario va, coge la pieza y **lee la ubicación** (lector o campo): la línea pasa a esa ubicación
  (`/koroshi/faltantes/reubicar`) y vuelve a la pantalla con la línea en su sitio nuevo para leer el EAN.
- **«Tampoco está aquí»** (se pulsa dos veces en 4 s) manda la pieza a faltantes (`/koroshi/faltantes/sin_alternativa`):
  la OUT sale sin ella. Si no hay ninguna otra ubicación, el botón dice «Mandar a faltantes».
- «Marcar varias a la vez» abre la pantalla de Faltante de siempre. «Cancelar», tocar fuera o «←» cierran la hoja.
- Leer una CJ o una tarjeta en la hoja da aviso y no hace nada. El botón se apaga cuando ya está todo leído.
- Sin cambios en el servidor (solo JS, plantilla y CSS).

## v3.1.0 (tras la prueba en Odoo del 10/11)

- Productos sin foto: no se pinta el icono gris de Odoo; el texto ocupa todo el ancho (`tiene_foto` con `bin_size`).
- Nombre del producto una vez y en grande (`[X] X` -> `X`) y **talla** en un recuadro negro (atributo Talla o lo
  último de MODELO-COLOR-TALLA). La referencia interna solo si es distinta del nombre y del EAN.
- Avisos cortos: «2511TR12-000002-XL · 1 de 1».
- «Todo en caja» solo cuando hay algo leído. Barra de progreso gruesa con «N de M uds» dentro.
- El nombre del operario no se parte en la cabecera.

## Cuándo se usa

- Solo si el **operario** está activado: parámetro `koroshi_preparacion.empleados` con los códigos de tarjeta
  (ID de credencial) separados por comas. Al instalar: `OP9990001,OP9980001` (Isaac e Isaac2). `*` = todos.
  Se activa por empleado, no por usuario, porque todas las PDA entran con el mismo usuario de Odoo.
- Solo **OUT sueltas** de la company 8. Las OUT de una agrupación de zona **Z-** siguen en la app de siempre.
- `koroshi_preparacion.activa` = `0` apaga todo y Lecturas vuelve a abrir la app de código de barras (vuelta atrás
  sin desinstalar).
- Sin tarjeta, o con un operario que no está en la lista: todo igual que antes.

## Cómo se usa en la PDA

1. Lecturas abre la OUT en la pantalla nueva. Arriba: OUT, tienda, operario y progreso («3 de 4 uds», «Sin caja: N
   uds»). En grande: **Ve a** ubicación, referencia, producto y cuántas lleva.
2. **Leer el EAN** (o la referencia) suma 1 ud a su línea. Si no es de la OUT, si es desconocido o si esa línea ya
   está completa: aviso rojo, pitido grave y **no cuenta**.
3. **Caja**: se pulsa el botón, sale «Escanea la caja», se lee la etiqueta **CJ** (CJ + 9 cifras) y la caja se cierra
   con todo lo leído que no tenía caja. Se puede seguir con la siguiente caja. Una CJ leída sin pulsar Caja avisa.
4. **Validar** (verde) cuando todo está leído y en caja. Si falta algo: «Quedan N líneas…» → **Faltante**.
   Al validar vuelve a Lecturas, que enseña «¡Hecho!» y abre la siguiente.
5. **Deshacer** quita la última lectura del operario (si aún no está en una caja).
6. **←** vuelve a Lecturas sin validar (Continuar / Faltante / Saltar, como al volver de la app).
7. **Faltante** (v3.2): hoja sobre la línea que se ve, con dónde probar; se lee la ubicación de donde se coge o
   «Tampoco está aquí». «Marcar varias a la vez» abre la pantalla de koroshi_faltantes; al volver, regresa aquí.

No hace falta tocar el campo para leer: el lector llega por el bus de Odoo, como en la app (v3.0.2: el punto dice
siempre «Lector preparado»; gris solo sin conexión). Sin conexión: banda roja; la lectura que estaba en camino se guarda al volver la red con el mismo id (no cuenta dos
veces) y las demás no se aceptan hasta que vuelva.

## Qué escribe

Lo mismo que la app de código de barras (comprobado en su código el 10/11/2026: guarda `qty_done`, llama
`put_in_pack(package_name=CJ)` y `button_validate`):

- `stock.move.line.qty_done` (+1 / −1 por lectura).
- `put_in_pack(package_name=<CJ>)` → Brain Station + **koroshi_caja_existente** (caja de otra OUT del mismo pedido,
  etc.) funcionan igual.
- Validación de **koroshi_faltantes** (`validar_out`: `button_validate`, todo o nada; pedido pendiente según
  `koroshi_faltantes.pedido_pendiente`). Bultos, XPO, S4T y etiquetas se hacen en el servidor como siempre.
- Su propia tabla **koroshi.preparacion.lectura** (menú *KOROSHI Operarios > Lecturas de preparación*, grupo
  productividad): quién, qué OUT, código, resultado, errores.

Sin campos nuevos en albaranes, movimientos, agrupaciones ni tipos de operación. No toca stock_barcode, no escribe
stock.quant y nunca fuerza disponibilidad.

## Rutas (JSON, `auth='user'`)

| Ruta | Qué hace |
|---|---|
| `/koroshi/preparacion/modo` | ¿El operario y la OUT van a la pantalla nueva? |
| `/koroshi/preparacion/cargar` | Estado de la OUT (líneas, siguiente, sin caja, cajas, progreso) |
| `/koroshi/preparacion/leer` | +1 ud del producto leído (con `id_lectura` para no contar dos veces) |
| `/koroshi/preparacion/deshacer` | −1 de la última lectura del operario |
| `/koroshi/preparacion/caja` | Cierra la caja con la CJ leída (`put_in_pack`) |
| `/koroshi/preparacion/validar` | Valida la OUT (validación de koroshi_faltantes) |

## Depende de

`koroshi_operarios` **v2.3.0** (pantalla nueva de Lecturas) y `koroshi_faltantes` v1.3.1. Se engancha con `.include`
en `koroshi_operarios.Pantalla._abrir` y en `koroshi_faltantes.Pantalla._onVolver`; no modifica sus ficheros.

## Ficheros

- `models/lectura.py`: tabla de lecturas y toda la lógica (leer, deshacer, caja, validar, estado).
- `controllers/main.py`: rutas.
- `static/src/js/preparacion.js`: pantalla + includes en Lecturas y Faltante.
- `static/src/xml/preparacion.xml`, `static/src/css/preparacion.css`.
- `data/parametros.xml` (noupdate), `views/lectura_views.xml`, `views/assets.xml`, `security/ir.model.access.csv`.

## Pendiente (siguientes versiones)

- Lotes Z- recorriendo OUT a OUT (v3.4a del plan).
- Cerrar caja leyendo directamente la CJ sin pulsar el botón (si se quiere).
- Cantidad de golpe para líneas de muchas uds (hoy el 96 % son de 1 ud).

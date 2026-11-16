# KOROSHI Preparación en Lecturas (v3.31.0, 16/11/2026)

Pantalla de preparación propia dentro de **Lecturas (PDA)**. El operario lee su tarjeta, se abre su OUT y la prepara
entera sin salir a la app de código de barras: leer productos, cerrar cajas con la etiqueta CJ y validar.


## v3.31.0: pasa a koroshi_base (16/11/2026, auditoría 13/11, fase 6)

- La empresa y la expresión de la matrícula CJ de Python salen de `koroshi_base.comun` (instalar koroshi_base antes).
  La misma expresión: CJ + 9 cifras.
- La pantalla de la PDA (JS) no cambia: su expresión lleva `/i` y no recorta espacios; pasarla a
  `koroshi_base.comun` cambiaría qué se acepta.
- Sin campos ni vistas nuevas.

## v3.30.0: pausa arriba (⏸ / ▶) y segunda ubicación en Faltante (14/11/2026)

- **Pausa arriba**, al lado del ☰: **⏸** (dos toques: «¿Pausa?»). Odoo para el tiempo (motivo «Pausa» de Operarios) y la
  pantalla se queda tapada con **«⏸ EN PAUSA · nombre · desde las HH:MM»** y un botón grande **«▶ Seguir»**. Arriba el
  botón pasa a ▶ (verde). Al seguir, el tiempo vuelve a empezar con la misma OUT: sin salir ni leer la tarjeta.
- En pausa no se lee (avisa «pulsa ▶ Seguir») y no suena la alarma de parado.
- Si al seguir Odoo da otra OUT (la han quitado desde la oficina), vuelve a Lecturas, que enseña la que toca.
- A dos (ayudante): como antes, se para su tiempo y vuelve a Lecturas.
- Ya no está en el menú ☰ (allí salía pequeño).
- **Faltante**: si la ubicación más cercana tiene pocas uds (menos de 3, o menos de las que faltan), la segunda también
  sale en grande, en gris oscuro: «Si no, aquí · N uds».
- Si la PDA se cierra en pausa: al volver a abrir, se lee la tarjeta como siempre y sale la misma OUT.

## v3.29.0: robustez (13/11/2026)

- **Caja cerrada sin conexión que Odoo no acepta**: la cola de la PDA **se para**. Antes seguía, y lo leído después
  y la caja siguiente se llevaban las uds de la rechazada. Ahora sale la hoja «La caja X no se ha cerrado en Odoo»:
  leer **otra etiqueta CJ**, **Probar otra vez con la misma** o **Dejar lo leído fuera de caja** (entra en la caja
  siguiente que se cierre). Hasta decidirlo no se guarda nada más ni se puede validar. Se puede salir con ←: al volver
  a abrir la OUT, sale otra vez la hoja.
- **Mover de caja, Deshacer y Validar** van con id y tiempo máximo. Si Odoo tarda, la PDA vuelve a mandar lo mismo con
  el mismo id (hasta 8 veces) y Odoo no lo hace dos veces. Validar espera hasta 90 s y, si la OUT ya está validada,
  contesta «validada» en lugar de un error. Mientras valida, la OUT (o la agrupación) queda bloqueada para otra PDA.
- **Al volver la conexión**, si la OUT ya la han validado (p. ej. desde Faltantes) se vuelve a Lecturas.
- **Lecturas rechazadas de cola** (menú de Operarios, grupo Productividad): lo que la PDA mandó desde su memoria (sin
  conexión o al volver a abrir) y Odoo no aplicó: OUT ya validada o cancelada, caja rechazada, error de Odoo o más de
  24 h en la PDA (antes se tiraba sin decir nada). El operario no lo vio en el momento: lo revisa el encargado.
- **OUT a dos**: una sola fila por OUT, titular y ayudante (restricción única). La migración borra antes las repetidas
  (el 13/11 había una: EFFEC/OUT/24410). Si dos PDA la crean a la vez, la segunda usa la de la primera.
- Los errores que antes se tragaban (`except: pass`) quedan en el log de Odoo.
- **Más ligero**: tras cada lectura el estado solo trae líneas, totales y lo de a dos; lo fijo (datos de la OUT,
  notas, tipos de caja, alarma) solo al cargar. En las agrupaciones Z- las OUT vivas se calculan una vez por petición.
- **Tests**: `tests/test_ruta.py` (sin base de datos: `python tests/test_ruta.py`) y `tests/test_idempotencia.py`
  (en una base de pruebas con `--test-enable --test-tags /koroshi_preparacion`).

## v3.28.1: ✎ en la tarjeta (13/11/2026)

- Al lado de **«En la caja X»** de la prenda que se ve sale también el **✎**: abre lo mismo que el ✎ de la lista
  (sacar de la caja u otra caja) sin tener que entrar en la lista.

## v3.28.0: sacar de la caja (13/11/2026)

- En la lista de líneas, **✎** en una línea ya en caja tiene ahora **«↩ Sacar de la caja (va a la siguiente)»**: se
  elige cuántas uds y vuelven a estar fuera de caja («por poner»). Al cerrar la caja siguiente entran en ella con lo
  demás. Ejemplo: se leen 3, la caja se cierra y solo caben 2 → ✎, 1 ud, Sacar de la caja.
- Ya no sale **«+ Caja nueva»** (Zalando / About You): hacía un PACK aparte con solo esas uds.
- Siguen las otras cajas de la OUT y, en las de tienda, leer otra etiqueta CJ.
- Si la caja de la que se saca se queda vacía, lo dice (el paquete vacío no estorba).

## v3.27.1: línea cogida, en verde el fondo (13/11/2026)

- Al leer una prenda y completar la línea, la franja de la ubicación ya no se pone verde oscura (no se leía bien):
  se queda con su color (amarilla por defecto) con la ubicación y el KO. Lo que se pone **verde es el fondo de la
  tarjeta**, con un borde verde.

## v3.27.0: Zalando y About You se validan incompletas (13/11/2026)

- Van por bultos: si quedan líneas sin leer, **«Validar»** dice cuántas uds faltan y el botón pasa a
  **«⚠ Validar incompleto»** durante 8 s. Con el segundo toque se valida lo leído y **lo que falta queda en una OUT
  pendiente** (siempre, aunque «pedido pendiente» esté en «no»), para revisar si se han hecho menos cajas de las que
  tocaba. Las dos OUT llevan una nota con quién la validó y cuántas uds faltaban.
- El primer toque no cierra la última caja: si no se confirma, no cambia nada.
- El resto de pedidos, igual que antes: hay que leer las líneas o pulsar «Faltante».

## v3.26.0: pausa desde la preparación (13/11/2026)

- En el menú ☰, **«⏸ Pausa (comer, café)»**. Primer toque: «Toca otra vez para la pausa»; segundo: se guarda lo leído,
  se para el tiempo y se vuelve a Lecturas sin operario («⏸ Pausa, Nombre…»). Al volver, lee su tarjeta y sale la
  misma OUT la primera. Es la misma pausa del botón de Lecturas (koroshi_operarios 2.10 o más).
- Si prepara a dos (ayudante), solo se para su tiempo.

## v3.25.0: OUT de una zona, sola (13/11/2026)

- Si se lee una OUT que es de una zona (Z-), se prepara **solo esa OUT** en esta pantalla (con Operarios 2.9). Para la
  zona entera, se lee el nombre de la Z-.
- Se valida igual que dentro de la agrupación (la validación de Faltantes sin su «se valida desde la agrupación»).
- Arriba sale la zona de la OUT.

## v3.24.3: tipo de caja sin conexión (13/11/2026)

- Sin conexión se cierra la caja igual: «Caja», leer la CJ y tocar el tipo. La caja queda cerrada en la PDA con su
  tipo y Odoo la guarda (tipo de paquete y consumo) cuando vuelve la conexión. En la lista sale el tipo.
- La caja Online no sale en la PDA (Consumibles 1.2.1): en pedidos de tiendas y Zalando solo Grande, 60x40x40 y Mediana.

## v3.24.2: aviso de sin conexión más corto (13/11/2026)

- El aviso rojo de arriba, en una línea y más pequeño: «Sin conexión · se guarda en la PDA».
- Las 3.24.0 y 3.24.1 no se instalaron.

## v3.24.1: primero la CJ, luego el tipo (13/11/2026)

- Se lee la etiqueta CJ y la hoja dice «CJ… · ¿Qué caja es?»: la caja se cierra al tocar el tipo. También vale tocar
  primero el tipo y luego leer la CJ. Ningún tipo sale marcado: no se cierra ninguna caja con un tipo supuesto.
- En una agrupación (Z-), una CJ leída sin pulsar «Caja» también pregunta el tipo.
- Botones de tipo más grandes (letra de 26 px, borde negro grueso); el elegido en negro con letra amarilla y ✓.
- La 3.24.0 no se instaló.

## v3.24.0: tipo de caja (13/11/2026)

- Al pulsar «Caja», encima de «Escanea la caja» salen los tipos de caja de **Consumibles** (los artículos marcados «Es
  una caja»): Grande 590x390x400, 60x40x40, Mediana y Online 280x280x120. Se elige y se lee la CJ. El tipo se recuerda
  por operario (la próxima vez sale marcado).
- Zalando / About You: «Caja» enseña los tipos y **tocar uno cierra la caja** (sin CJ, como antes). La última caja que
  se cierra sola al validar va con el último tipo elegido.
- Odoo pone a la caja (`stock.quant.package`) su «Tipo de paquete» y resta 1 en Consumibles con un consumo «OUT · caja
  · operario». Si la caja ya existía en la OUT (se vuelve a abrir), no resta otra vez. Nunca para el cierre de la caja.
- También sin conexión: la caja va a la cola con su tipo.
- En la lista de cajas («N cajas») sale el tipo de cada caja.
- Depende de `koroshi_consumibles` v1.2.0, que hay que actualizar a la vez.

## v3.23.0: alarma de parado + caja sin internet (12/11/2026)

La 3.22.0 no llegó a instalarse: la caja sin internet va en esta versión, con la alarma y la v3.21.1.

### Alarma de parado

- Con la OUT (o la agrupación) abierta y X minutos sin leer ninguna prenda, la PDA suena sin parar: una sirena aguda
  al volumen máximo del navegador, aunque el sonido de Lecturas esté apagado. Además vibra, y la pantalla parpadea en
  rojo con «¡LLEVAS N MIN SIN LEER!».
- Se para cuando cuenta algo: una prenda, una caja cerrada, «Poner cantidad» o un Faltante resuelto. También se para al
  salir con ←. Deshacer, leer una ubicación o tocar la pantalla no la paran.
- No cuenta mientras el operario está en la pantalla de Faltante ni mientras valida.
- Parámetros (los dos están en Ajustes KOROSHI, `koroshi_menu` v1.3):
  - `koroshi_preparacion.minutos_alarma`: por defecto 4; 0 = sin alarma.
  - `koroshi_preparacion.horario_alarma`: por defecto `06:00-10:00,10:15-13:00,14:00-17:00`, con la hora de la PDA.
    En la pausa (10:00-10:15) y la comida (13 a 14) no suena ni cuenta. Al empezar el siguiente tramo, el tiempo
    empieza de cero.
- El volumen del sistema lo pone Android. Para que no lo bajen en las TC22: StageNow, Audio Volume UI Manager, con un
  mínimo de STREAM_MUSIC.

### Caja sin internet

- Sin conexión, «Caja» y leer la CJ ya no esperan: la caja se cierra en la PDA y lo leído fuera de caja pasa a ella.
- La caja va a la cola de la PDA en su sitio, entre las lecturas, y se guarda en la memoria de la PDA.
- Al volver la conexión, Odoo cierra las cajas en el mismo orden y con el mismo id: no se cierran dos veces.
- La PDA comprueba lo mismo que Odoo: etiqueta CJ, que haya algo fuera de caja y, en las Z-, de qué tienda es la CJ.
  Para eso el estado de una agrupación trae las CJ reservadas de cada OUT (`outs[].cjs`).
- Zalando / About You: sin red la caja sale como «S1», «S2»… para apuntarla. Al volver la conexión sale su PACK y en la
  lista de cajas «era S1».
- Si Odoo no acepta una caja guardada sin red, la PDA avisa y lo leído queda fuera de caja para cerrarla otra vez.
- Validar sigue necesitando conexión.
- Arreglado (venía de antes): al pulsar «Caja» se borraba la clase de los avisos de las otras hojas (Faltante,
  Cambiar de caja, Poner cantidad, Imprimir) y sus mensajes podían dejar de verse hasta recargar.

## v3.21.1: amarillos más en negrita (12/11/2026)

En los colores con fondo amarillo (C y F) la letra de la ubicación es más negra y gruesa, y en F el código KO
también va en negrita. Solo CSS (capturas en bin/versiones/20261112_colores_ubicacion_pda/).

## v3.21.0: cambiar de caja y color de la ubicación (12/11/2026)

- **Cambiar de caja (✎).** En ☰ › Ver líneas, cada línea que ya está en una caja tiene un ✎. Se elige cuántas uds
  (− / +) y a qué caja: otra caja de la OUT, **«+ Caja nueva»** (Zalando / About You: PACK nuevo) o, en las OUT de
  tiendas, leyendo la etiqueta CJ de otra caja (nueva o de la OUT; si es de otro pedido, no deja). Si no se mueve la
  línea entera, se parte en dos igual que hace Odoo al cerrar caja (copia con las uds movidas y la original con el
  resto). Las lecturas de esas uds pasan a la caja nueva. Queda apuntado como «Mover de caja» en las lecturas.
- **Color de la ubicación.** Menú ☰ › «Color de la ubicación»: A negra (la de antes), B blanca con borde, C
  amarilla, D azul oscuro, E en casillas (L | P | C) y F amarilla con el hueco muy grande. **Por defecto F.** Se
  guarda por operario (tabla nueva `koroshi.preparacion.preferencia`, nada en hr.employee), así sale igual en
  cualquier PDA. Una línea ya cogida sigue saliendo en verde.
- Incluye la v3.20.0 (no llegó a instalarse).

## v3.20.0: Zalando y About You, el número del PACK y la lista de cajas (12/11/2026)

- Al pulsar **Caja** sale una hoja con el **número del paquete en grande** (PACK0139…), sus uds y «Apunta este
  número en la caja», y debajo la **lista de cajas** de la OUT (la nueva en verde). «Seguir leyendo» (o leer otra
  prenda) la cierra.
- Al **Validar**, si la última caja se ha cerrado sola, sale igual («OUT validada · última caja») y no se vuelve a
  Lecturas hasta pulsar «Hecho».
- Tocar **«N cajas»** (arriba, debajo de la barra) enseña la lista de cajas en cualquier OUT.
- El 12/11 la caja de prueba PACK0139621 de la OUT 24973 se quitó a mano (las 20 uds siguen leídas, fuera de caja).

## v3.19.0: Zalando y About You sin etiqueta CJ (12/11/2026)

- Las OUT de marketplace (pedido de tipo **PED. MARKETPLACE**, o cliente con ZALANDO / ABOUT YOU en el nombre) no
  llevan etiqueta CJ: sus cajas son paquetes de Odoo con nombre automático (PACK0139568…), como hacía «Put in pack»
  en la app de código de barras.
- **Caja**: crea el paquete con lo leído fuera de caja (lo de este operario, si son dos) **sin leer nada**. Sale
  «Caja PACK0139… cerrada con N uds.» y se sigue leyendo. Si leen una CJ igualmente, también vale.
- **Validar**: si queda algo leído fuera de caja, lo mete solo en un paquete nuevo y valida (no hace falta pulsar
  «Caja» antes). Si lo que queda es del compañero, como antes: «Falta que tu compañero cierre su caja».
- Las OUT de tiendas, las INT y las agrupaciones (Z-) siguen igual.
- Incluye la v3.18.0 (no llegó a instalarse).

## v3.18.0: lectura equivocada (12/11/2026)

Si el operario lee un código numérico (EAN) que **no es de ningún artículo** y **no empieza por 8445962**, ya no sale
«Código desconocido», sino: «8410782105213 no es de ningún artículo: es otro código de la bolsa. Lee el de KOROSHI, el
que empieza por 8445962. No cuenta.» (OUT, INT y agrupaciones). El 12/11 se leyó 8410782105213, que no es de KOROSHI.
Los artículos de KOROSHI empiezan casi todos por 8445962 (1857 de 2130 en las OUT de noviembre; el resto por 8445514
y 810000x, que sí están en Odoo y se leen bien).

## v3.17.0: orden como la app de código de barras (12/11/2026)

Isaac prefiere el orden de siempre: las líneas van por el **nombre de la ubicación**, igual que en la app de código de
barras de Odoo (`_.sortBy(pages, 'location_name')`): 00114 - L02 P31, 00221 - L03 P31, ..., L.., MU-.., N1-... En la
misma ubicación, por referencia. Es el valor por defecto del parámetro nuevo `koroshi_preparacion.orden`
(`ubicacion`). Con `ruta` vuelve la ruta optimizada (v3.13-3.16.2, `models/ruta.py`), sin instalar nada.
Las líneas 0 de 0 (v3.16.1) siguen sin salir en los dos casos. Mapas de la OUT 24421 con los dos órdenes en
`bin/versiones/20261112_ruta_out_24421/` (código de barras 941 m, ruta 784 m).

## v3.16.0 / v3.16.1: la ruta no vuelve a los mismos pasillos y sin líneas «0 de 0» (12/11/2026)

«Da muchas vueltas»: la ruta de la v3.13 era la más corta en metros, pero subía por un tramo de los pasillos y al
final volvía por otro tramo de los MISMOS pasillos (EFFEC/INT/67365: 14 pasillos visitados dos o tres veces; el
operario se saltaba el orden y cogía lo de al lado). Ahora, al ordenar, cada cambio de pasillo cuenta 10 m de más
(`PENAL_PASILLO` en `models/ruta.py`): la ruta acaba un pasillo antes de irse. En 14 OUT/INT reales grandes:
10.574 m → 10.670 m (+0,9 %) y 125 → 30 pasillos repetidos. Sirve para OUT, INT y agrupaciones Z-.
Mapa de la ruta de la INT 67365 antes del cambio: `bin/versiones/20261112_ruta_int_67365/`.

**Líneas «0 de 0» (v3.16.1).** Si la OUT/INT se toca en la app de código de barras de Odoo (leer en otra ubicación y deshacer),
quedan líneas con 0 pedidas y 0 leídas. Antes salían como pendientes («0 de 0») y «Ir a la que toca» volvía siempre a
ellas. Ahora `_ordenar` las deja fuera (no salen, no cuentan, no se borran).

**MU- al final (v3.16.2).** Todas las MU- son un solo punto al lado de los muelles. Como la ruta sale de muelles, iban
las primeras y el operario se las saltaba (EFFEC/OUT/24421: 9 líneas MU- y empezó por L03). Ahora se empieza igual (lo más
cerca de los muelles) y las MU- pasan al final, de camino a muelles: unos pocos metros más. Mapa: `bin/versiones/20261112_ruta_out_24421/`.

## v3.15.0: agrupaciones de zona (Z-) en la pantalla nueva (11/11/2026)

Para los operarios de `koroshi_preparacion.empleados`, una agrupación Z- (la tarea de Lecturas es de toda la
agrupación) ya no abre la app de código de barras: se abre la pantalla nueva con la agrupación **entera**.

- **Un solo recorrido** (`models/agrupacion.py`): las líneas de todas sus OUT por hacer, en el orden de la ruta óptima.
  Cada línea lleva su OUT, su tienda y su **caja de tienda** (el «CAJA nn» de la nota de la OUT, el mismo de la
  etiqueta de zona). En la tarjeta, banda amarilla «→ CAJA 05 · K34 ...»; en la lista de líneas también.
- **Leer un EAN**: +1 ud en la línea que se ve si es de ese artículo; si no, en la primera pendiente de la ruta (la PDA
  y Odoo eligen la misma: la PDA manda `linea_id`). El aviso dice a qué caja va y no se borra solo.
- **Leer una CJ** (sin pulsar «Caja»): cierra la caja de la tienda de esa etiqueta (`zebra.label` con nota
  «ETQ ZONA <OUT>», la que reserva «Etiquetas de zona»). Si la CJ es de una OUT de otra agrupación: no se cierra. Si la
  CJ no es de ninguna OUT: la caja que ya tenga ese nombre en la agrupación, la OUT de la línea que se ve o, si solo
  hay una con algo leído, esa. `put_in_pack` solo en esa OUT (igual que en una OUT suelta).
- **Validar**: todo leído (o en faltantes) y en caja → cada OUT con la validación de siempre (`button_validate` de
  koroshi_faltantes, todo o nada por OUT), una detrás de otra. La agrupación se queda «En curso», como hoy
  (comprobado: las Z- del 11/11 tienen todas sus OUT hechas y siguen «En curso»; `batch.operation.line` vacía).
  Si alguna no se puede validar, se dice cuál y por qué; las demás quedan validadas.
- Faltante, Deshacer, Poner cantidad e Imprimir (etiquetas de caja y albaranes de todas las tiendas) igual que en una
  OUT. «Volver» de la pantalla de Faltante vuelve a la agrupación en la pantalla nueva.
- Sin preparar a dos en las agrupaciones (la tarea es de un operario).
- Parámetro nuevo `koroshi_preparacion.agrupaciones` (`1` al instalar; `0` = las Z- vuelven a la app de siempre).
- Las OUT sueltas no cambian (refactor sin cambio de resultado: `_ordenar`, `_linea_json`, `_fotos`, `_sumar`,
  `_producto_entre`, `_hermanas_en`).
- Rutas: todas aceptan `lote_id` en vez de `picking_id` (`leer` además `linea_id`, `caja` además `out_id`). La cola
  de la memoria de la PDA usa la clave `L<id>` para las agrupaciones.

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
- OUT sueltas de la company 8 y, desde la v3.15, agrupaciones de zona **Z-** enteras (parámetro
  `koroshi_preparacion.agrupaciones`).
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
- `models/agrupacion.py` (v3.15): la agrupación Z- entera (estado, leer, caja por tienda, validar cada OUT).
- `controllers/main.py`: rutas.
- `static/src/js/preparacion.js`: pantalla + includes en Lecturas y Faltante.
- `static/src/xml/preparacion.xml`, `static/src/css/preparacion.css`.
- `data/parametros.xml` y `data/parametros_v315.xml` (noupdate), `views/lectura_views.xml`, `views/assets.xml`, `security/ir.model.access.csv`.

## Pendiente (siguientes versiones)

- Cerrar caja leyendo directamente la CJ sin pulsar el botón también en las OUT sueltas (en las Z- ya, v3.15).
- Cantidad de golpe para líneas de muchas uds (hoy el 96 % son de 1 ud).

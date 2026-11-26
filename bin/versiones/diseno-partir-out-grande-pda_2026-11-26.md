# Diseño: «Demasiado grande: partir» en Lecturas (PDA), v1 (26/11/2026)

Módulo: **koroshi_preparacion** (base 3.37.0, hecha sin instalar; servidor 3.35.0). Solo este módulo: sin cambios en
koroshi_operarios, koroshi_zonas ni koroshi_faltantes, y sin campos nuevos en `stock.picking`, `stock.picking.type` ni
`stock.move.line`.

**Estado: diseño. No se ha tocado código.** Espera las respuestas de Isaac (apartado 8).

## 1. El caso (26/11, hacia las 12:58)

OUT de tienda de 516 líneas, cabecera «VE A», el operario iba por la línea 138. Al pulsar Validar, la PDA dice
«Quedan 377 líneas por coger: léelas o pulsa Faltante». La querían partir y repartir, pero:

- Lecturas solo valida con todo leído o marcado como Faltante (`models/lectura.py:1350`).
- «Faltante» no sirve: mandaría 377 líneas a faltantes.
- La salida manual de hoy (Caja → no tocar Faltante → en el ordenador, Validar → «Crear pedido pendiente») funciona,
  pero pide un ordenador y deja el resto en una sola OUT para una sola persona.

## 2. Lo que ya existe (leído en el código)

| Pieza | Dónde | Sirve para esto |
|---|---|---|
| **Preparar a dos**: un segundo operario lee la misma OUT y entra de ayudante; la OUT se parte por la mitad de la ruta y cada uno va hacia el otro | `lectura.py:390-437` y `estado()` 510-538; `koroshi_operarios/models/reparto.py:801` `ayudante_de` | Sí, pero **como mucho dos** (`MAX_POR_OUT = 2`, `reparto.py:33`) y nada sale hasta que los dos acaban |
| **Validar incompleto** (Zalando / About You): valida lo leído y lo que falta va a una OUT pendiente | `lectura.py:1189` `_validar_incompleta` | El gesto es el que queremos, pero usa el asistente de pedido pendiente de Odoo (la reserva del resto la rehace Odoo, ver 6.2) |
| **Partir OUT por zonas** (acciones 1880-1883, hoy `koroshi_zonas/models/escritor.py:12`): copia la OUT, `_split` de cada movimiento y **mueve las líneas reservadas** a la copia | `escritor.py:66-110` | Es la técnica buena: la reserva no se toca, solo cambia de OUT. Se usa cada día desde el 20/11 |
| **Reparto de trabajo**: una OUT libre (preparada, sin asignación viva, fuera de Z-) se da sola al siguiente operario que pide, la más antigua primero | `reparto.py:426` `_candidatos` | Las OUT nuevas entran solas en el reparto, sin tocar operarios |
| **Dejar este pedido** desde la pausa (3.37.0, hoy) | `reparto.py:487` `soltar` | Para soltar lo que queda sin partirlo |

Hoy, con lo instalado, la OUT de 516 líneas se podía haber hecho **a dos** (otra persona lee la OUT en su PDA y entra
de ayudante). No resuelve tres o más personas ni que la primera parte salga ya.

## 3. Propuesta: botón «✂ Partir pedido» en el menú ☰ de Lecturas

### 3.1 Lo que ve el operario

1. ☰ → **«✂ Demasiado grande: partir»**. Solo sale si la OUT se puede partir (3.4).
2. Hoja: «Quedan **377 líneas / N uds** por coger. ¿En cuántos trozos lo dejas para otros?» con botones **1 · 2 · 3 · 4**
   y, debajo, el reparto que saldría: «Trozo 1: L12–L30, 128 líneas, 260 uds», etc.
3. Si tiene uds leídas fuera de caja: «Antes cierra la caja: pulsa Caja y lee la etiqueta» (el mismo control que
   Validar, `lectura.py:1302-1312`). No se cierra la caja sola: la etiqueta CJ la tiene que leer él.
4. Dos toques (como la pausa) para confirmar. Resultado en pantalla:
   «OUT/12345 validada con 138 líneas (5 cajas). El resto, en OUT/12399 (L12–L30) y OUT/12400 (L31–L58), libres para
   otros». Lecturas abre su siguiente trabajo como al validar.

### 3.2 Lo que hace Odoo (todo o nada, en una transacción)

Orden pensado para que **la OUT original nunca pase por el asistente de pedido pendiente**:

1. Comprobaciones: OUT propia y partible (3.4), nada leído fuera de caja, nadie más con la OUT (o el compañero de
   «a dos» ya ha cerrado su caja), bloqueo de la OUT (`_bloquear`, como Validar).
2. **Lo que queda por coger** = las move.line sin leer (con la caja cerrada, lo leído ya está en su CJ: `put_in_pack`
   parte la línea leída a medias y deja el resto en una línea sin leer). Se ordenan con el orden de Lecturas
   (`_lineas`) y se cortan en N trozos seguidos por la ruta, **parejos en uds**, sin partir una ubicación entre dos
   trozos.
3. Por cada trozo, una copia de la OUT (`copy` con `move_lines`, `move_line_ids` y `package_level_ids` vacíos), como
   `escritor.py:56-67`. Por cada movimiento con algo pendiente: `_split` de lo que va a cada trozo y las move.line sin
   leer pasan al movimiento nuevo y a su OUT (`escritor.py:94-108`). **La reserva viaja con la línea: no se quita ni
   se vuelve a reservar.** Lo que el movimiento pedía y no estaba reservado va al trozo donde está la primera línea de
   ese artículo (o al trozo 1 si no tiene ninguna), y allí se queda sin reservar igual que estaba.
4. La OUT original queda con lo leído y todo en cajas: se valida con la validación de siempre
   (`Faltante.validar_out`), que ya no pregunta por pedido pendiente porque no falta nada.
5. En cada trozo: `backorder_id` = la original (sale en «Pedidos pendientes» de la OUT y la acción 1800 la trata como
   backorder, ver 5), los contadores `count_demand / count_reserve / count_done` recalculados (como `escritor.py:115`,
   que si no la lista de Transferencias enseña las uds del pedido entero) y nota «Trozo 2 de 3 de OUT/12345, partida
   en la PDA por <operario> el dd/mm a las hh:mm».
6. Nota en la original («Partida en la PDA por <operario>: validado lo leído; el resto en OUT/…») y una línea de
   registro en `koroshi.preparacion.lectura` (tipo nuevo «Partir»: es una tabla del módulo, no una de stock).
7. Cierra la tarea del operario de la original (`cerrar_tareas_de`), como al validar.
8. Comprobación al final, antes de confirmar: uds reservadas de la original + trozos = las de antes; si no cuadra,
   se deshace todo y la PDA dice «No se ha podido partir: no se ha tocado nada».

### 3.3 Quién hace los trozos

No hay que tocar koroshi_operarios: los trozos son OUT preparadas, sin asignación y sin Z-, así que **el reparto
automático las da solas al siguiente operario que pida**. Como heredan la fecha prevista de la original, salen las
primeras. El responsable las ve y las puede mover en Colas / Reparto de hoy como cualquier OUT.

Opción en la misma hoja (pregunta P4): **«Sigo yo con el trozo 1»**: el que parte se queda el primer trozo (lo lee a
mano en la PDA, como `leida_a_mano`) y los demás quedan libres.

### 3.4 Qué OUT se pueden partir

- OUT de salida de la compañía 8, sin hacer ni cancelar, **sin agrupación Z-** (las de zonas ya vienen partidas y su
  validación es la de la agrupación).
- **No** Zalando / About You: ya tienen «Validar incompleto» y un bulto de marketplace no debe acabar en dos OUT sin
  hablarlo (pregunta P6).
- **No** INT de web ni ronda de faltantes.
- Con un mínimo de lo que queda: **100 líneas o 300 uds** pendientes (pregunta P2). Por debajo, el botón no sale:
  para eso está «a dos».
- Con algo leído o sin nada leído: si no hay nada leído, no se valida nada y solo se parte (es la «alternativa:
  partir antes», ver 4).

## 4. Partir ANTES de empezar

Sale casi gratis con lo mismo: si la OUT no tiene nada leído, el botón solo parte (paso 4 no hace nada) y la original
se queda con el trozo 1. Dos sitios posibles:

- **En la PDA**, al abrir una OUT grande: «Esta OUT tiene 516 líneas. ¿Partirla en N?» (aviso, no obligatorio).
- **En la oficina**, un botón «Partir en N» en la OUT (formulario de Transferencias) para el responsable.

Propuesta v1: solo el botón del menú ☰ (vale para antes y para a medias). El aviso al abrir y el botón de oficina, si
Isaac lo quiere, después (pregunta P5).

## 5. Qué pasa con S4T (acción 1800 v6.7)

La 1800 trabaja por pedido de venta: envía cuando **todas** sus OUT están hechas (las canceladas no cuentan).

- Mientras un trozo esté sin validar y con algo reservado, **el pedido espera**. Es lo que queremos: KOROSHI recibe
  el pedido una vez, completo.
- Cuando los trozos se validan, el pedido sale en la siguiente pasada del cron 186, con las cajas de todas las OUT.
- Trozo que acaba con todo en Faltante: se valida como hoy con Faltante (no queda reservado) y no bloquea.
- Trozo que se queda con **0 reservado y sin leer** (todo se fue a faltantes de otra forma): al ser backorder de la
  original, la 1800 lo cancela **solo si es de un día anterior**. Si se parte y se deja así el mismo día, el pedido no
  sale hasta la pasada del día siguiente. Igual que hoy con cualquier pedido pendiente.
- Regla de la **caja pequeña** (CJ de 3 uds o menos con otra caja donde juntarla): cada trozo acaba con su última caja
  a medias, así que es fácil que el pedido se quede esperando a «Juntar cajas» en expediciones. Hay que saberlo
  (pregunta P7).
- Transportista y etiqueta: cada trozo es una OUT más del pedido, como las de zonas, que ya lo tienen resuelto en
  expediciones (XPO por bultos de todas las OUT del pedido). Lo confirma la sesión de expediciones antes de instalar.

## 6. Riesgos y lo que hay que comprobar

1. **La reserva.** Con el `_split` y moviendo las move.line (técnica de zonas), la reserva se mueve tal cual. Por
   eso **no** se usa el asistente «Crear pedido pendiente» de Odoo para tiendas.
2. **El asistente de Odoo (lo que se hace hoy a mano).** No he podido confirmar en el código si Odoo 13, al crear el
   pedido pendiente, conserva las mismas ubicaciones reservadas o desreserva y vuelve a reservar (puede coger otras
   ubicaciones, y entre medias otra OUT podría llevarse el stock). Para la vía manual de hoy: mirar en la próxima
   backorder hecha así si las ubicaciones reservadas son las mismas que tenía la original. Solo leer.
3. **Dos personas con la OUT («a dos»).** Partir pide que las dos cajas estén cerradas. Si el compañero tiene uds
   fuera de caja: «Falta que <compañero> cierre su caja». Después, la tarea del ayudante se cierra como al validar.
4. **Numeración.** Cada trozo gasta un número de la secuencia EFFEC/OUT/ (como zonas). No se prueba en SIMULAR contra
   la base real por eso: las pruebas van en los tests del módulo (que se deshacen) y en una OUT de prueba.
5. **Etiquetas CJ impresas para la OUT entera.** Si se imprimieron antes, las que no se usen sirven para los trozos
   (la CJ se lee, no va atada a la OUT). Confirmarlo con Isaac (pregunta P8).
6. **Tiempo.** 377 líneas: unos cuantos `_split` y escrituras; la validación de la parte leída es la de siempre. Se
   mide con el mismo log de tiempos que Validar (`_tiempos`).

## 7. Cambios previstos (cuando haya visto bueno)

- `models/lectura.py`: `partible(picking)`, `plan_partir(picking, n)` (para la hoja), `partir(picking, employee, n,
  id_lectura)`; tipo «partir» en `koroshi.preparacion.lectura`; parámetros `koroshi_preparacion.partir_min_lineas`
  (100), `partir_min_uds` (300) y `partir_max_trozos` (4).
- `controllers/main.py`: `/koroshi/preparacion/partir` (plan y hacer), con permiso y tarjeta válida como las demás
  rutas que escriben (R16).
- `static/src/js/preparacion.js`, `xml`, `css`: entrada del menú ☰, hoja con 1-4 y el reparto, dos toques.
- `tests/`: partir a medias (cuadran reservas y uds, original validada, trozos con `backorder_id`), partir sin nada
  leído, con uds fuera de caja (no deja), Zalando y Z- (no deja), reserva parcial (lo no reservado va al trozo bueno).
- Versión **3.38.0** sobre la 3.37.0, historial, commit con rutas, `python bin/empaquetar.py koroshi_preparacion`,
  línea en TABLERO.md. Sin instalar.

**Antes de tocar código**: koroshi_preparacion lo ha tenido hoy la sesión de «Caja llena / soltar pedido» (3.37.0).
Hace falta que lo suelte (regla 6).

## 8. Preguntas para Isaac

- **P1. ¿Vale la idea?** Botón en ☰ de Lecturas: valida lo leído y parte lo que queda en 1-4 OUT nuevas (backorders de
  la original) que el reparto da solas a otros operarios. Sin tocar Operarios ni Zonas.
- **P2. Mínimo para que salga el botón:** ¿100 líneas o 300 uds pendientes? ¿Otro número?
- **P3. ¿Quién puede partir?** ¿Cualquier operario, o solo con tarjeta de jefe o del responsable?
- **P4. El que parte, ¿sigue con el trozo 1** o lo suelta todo y le dan otra cosa?
- **P5. ¿También el aviso al abrir una OUT muy grande y un botón «Partir en N» en la oficina?** (propuesta: más tarde)
- **P6. Zalando y About You fuera** (ya tienen «Validar incompleto»). ¿De acuerdo?
- **P7. Caja pequeña en S4T:** cada trozo acaba con una caja a medias; el pedido puede esperar a «Juntar cajas». ¿Vale
  así, o la regla de la 1800 debería no contar las OUT partidas? (Eso sería un cambio en la 1800, aparte.)
- **P8. Etiquetas CJ:** ¿las etiquetas impresas para una OUT se pueden usar en otra de la misma tienda?
- **P9. Mientras no esté:** ¿se recuerda a los responsables que una OUT grande se puede hacer **a dos** (la otra
  persona lee la misma OUT en su PDA y entra de ayudante)?

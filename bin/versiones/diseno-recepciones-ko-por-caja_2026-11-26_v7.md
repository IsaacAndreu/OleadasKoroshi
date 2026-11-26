# Recepciones con contenedor de control por caja — diseño v7 (26/11/2026)

Sustituye el planteamiento de la v6 (cajas por nº escrito a mano, opción A). Sale de la grabación de Isaac del
26/11 (última parte: «lo que hay que dar es el número de la caixa…»). **Borrador: faltan las respuestas de la
sección 6 antes de programar.**

## 1. Idea

Cada caja física del contenedor marítimo lleva un **contenedor de control (KO_)** pegado. El KO es la matrícula de
la caja: con él se sabe qué lleva, en qué palé está y, después, sirve para ordenar y para ubicar.

## 2. Paso 1 — Recepcionar (PDA)

1. **Etiquetas KO en orden.** Se imprimen N etiquetas seguidas (1, 2, 3 … N) y se pegan en las cajas en ese orden.
2. **Leer cada caja.** «Empezar a leer» → escanear el KO → la referencia (escrita o leyendo el código de barras de
   una prenda) → la cantidad → Intro / Aceptar → siguiente. **Caja mixta**: varias líneas en el mismo KO.
3. **Asignar al palé.** Cuando se han colocado unas cuantas cajas (8, 6, las que quepan), botón «Asignar al palé» →
   se elige el palé (1A, 5B…) → los KO leídos y todavía sin palé pasan a ese palé. Varias personas a la vez, cada
   una por un lado del contenedor.
4. Al final: N cajas = N KO, cada uno con su contenido y su palé.

## 3. Comprobación

- **Cajas**: KO leídos frente a cajas esperadas (packing / PL). «Has leído 353 de 354.»
- **Stock**: por artículo (referencia + talla) frente a las IN. «Te faltan 13 uds del 2711JA22 talla L.»
- **Listar contenedores y ver saltos**: como se pegan y se leen en orden, si falta el 54 es que se saltó (comida, una
  interrupción…) o que el último no se leyó. Se busca esa caja, se lee y cuadra.

## 4. Paso 2 — Ordenar (PDA)

- Se elige un **modelo** → una línea por **talla** (S, M, L…) con un **punto de color** por artículo.
- Al abrir una talla, un desplegable con sus KO: «KO 7 — palé 1A», «KO 15 — palé 3B (mixta)»…, **en orden de
  palé** (1A, 1B, 2A…) para recorrerlos seguidos.
- La persona va con el carro, coge esas cajas y las deja en un palé nuevo: queda ordenado por modelo y talla.

## 5. Paso 3 — Ubicar

Los mismos KO sirven para ubicar. La grabación se corta aquí («y tendremos una opción que es…»).

## 6. Decisiones (Isaac, 26/11/2026)

1. **Contenido = artículo con talla + uds.** Se lee el EAN de una prenda o se escribe la referencia con talla. Una
   caja mixta son varias líneas en el mismo KO.
2. **Stock: cuando la comprobación cuadra, se valida la IN dejando el stock en el KO de cada caja** (como en la
   1.0.x). Lo que no llega queda en la IN pendiente. Se deja la opción A.
3. **Numeración 1…N por recepción.** El nº va grande en la etiqueta («54») y el código KO_ debajo para escanear.
   Los saltos se ven sobre esa numeración.
4. **Ordenar apunta el movimiento**: se lee el KO y el palé nuevo, y el sistema sabe dónde queda cada caja.
5. **Pendiente**: la «opción» del paso 3 (ubicar), donde se corta la grabación.

6. **Los KO los genera el sistema (Isaac, 26/11):** al recepcionar, el sistema ya sabe cuántas cajas hay (packing
   de S4T o Excel del PL de la IN) y crea un KO por caja, numerados 1…N, con sus etiquetas a la Zebra. No se
   pregunta cuántas. Si llegan más cajas, «+ KO» añade los que falten (N+1…).

## 6 quater. Cómo se hace hoy (fotos de Isaac, 26/11)

- **Cada caja del proveedor lleva:**
  - la etiqueta «NO ASSORTMENT BOX», que da REFERENCE (2711JA09), ORDER NUMBER (0000001937), la tabla color ×
    talla (BLACK 000003 / PIEDRA 000062; S…3XL) con las uds («13» en L) y «Total pack»; si no va llena, «CAJA
    INCOMPLETA»;
  - impreso en el cartón, «Carton Number: 34/199» escrito a mano (nº de caja / total) y la talla rodeada en la
    rejilla S M L XL XXL 3XL;
  - el peso bruto y neto.
- **Lo que ponemos nosotros:**
  - una etiqueta de color y talla («NEGRO L», «ROJO S»), a veces con código;
  - una etiqueta KO_301026 con el nº escrito a mano («054»), que es **el mismo en todas las cajas del mismo
    artículo** (054 = las NEGRO L, 055 = las ROJO S). Hoy el KO es un grupo de cajas, no una caja.
- **Consecuencias para la v7:**
  - **ABIERTO (Isaac lo pregunta al jefe de almacén, 26/11): ¿KO único por caja o un KO por grupo de cajas del
    mismo artículo (como el 054 de hoy)?** Hasta saberlo, los datos se pensarán para que valgan las dos: cada caja
    es una fila, con su KO, y un KO podrá tener una caja o varias.
  - **Las cajas llegan cerradas:** no se puede leer el EAN de una prenda sin abrirlas. El artículo sale de la
    etiqueta del proveedor: referencia + color + talla + uds. Con el packing list, basta con el **Carton
    Number** (34) + la referencia: el PL dice color, talla y uds, y en la PDA solo se confirma o se corrige
    (cajas incompletas).
  - **Una caja abierta** (la «2» de las fotos, ROJO S a medias) se apunta con las uds que quedan.

## 6 quinquies. Flujo de lectura en la PDA (Isaac, 26/11: «escanearían caja por caja y le pondrían qué modelo es y
cuántas uds»)

1. Se escanea el KO de la caja. La pantalla dice «KO 54», o que ya tiene algo.
2. **Modelo**: se escribe la REFERENCE de la etiqueta del proveedor, con autocompletar (2711JA09).
3. **Color y talla**: salen como botones los artículos de ese modelo en las IN (NEGRO L, ROJO S…), tal como se
   lee en la etiqueta del proveedor y en la pegatina de color.
4. **Uds** («Total pack» de la etiqueta) → Guardar.
5. **Siguiente KO**. Si la caja es mixta, «+ otro artículo en este KO» antes de pasar al siguiente.

Sin abrir cajas.

## 6 bis. Modelo de datos (propuesta)

- Tabla nueva `koroshi.recepcion.caja` (no es compartida): recepción, nº (1…N), KO_ (`stock.location`), palé y
  palé tras ordenar. Una por cada KO de la recepción.
- Las lecturas (`koroshi.recepcion.lectura`) cuelgan de la caja: artículo + uds, varias por caja si es mixta.
- Sin campos nuevos en `stock.picking`, `stock.picking.type` ni `stock.move.line`.

## 6 ter. Fases

1. **Recepcionar**: etiquetas 1…N, leer KO + artículo + uds, «Asignar al palé» por lotes.
2. **Comprobación y validación**: cajas frente a packing / PL, uds por artículo frente a las IN, lista de KO con
   saltos y validar la IN a los KO.
3. **Ordenar**: modelo → talla (con color) → KO por orden de palé, y leer KO + palé nuevo.
4. **Ubicar**: cuando se aclare el punto 5.

## 7. Qué se reutiliza de koroshi_recepcion

- **Ya existe**: crear KO_ en tandas con su etiqueta a la Zebra (1.7.0) y lectura por artículo con cantidad
  (1.0.x/1.1.0, `guardar_lectura`).
- **Ya existe**: palés PAL-NN A/B, comparación por artículo frente a las IN (con huecos de numeración) y el
  packing list en Excel (cajas por modelo, tallas y uds).
- **Ya existe**: validar dejando el stock en el KO de cada caja (1.0.x).
- **Nuevo**: «Asignar al palé» por lotes (los KO sin palé), lista de KO con saltos y la pantalla «Ordenar»
  (modelo → talla → KO por palé, con color).

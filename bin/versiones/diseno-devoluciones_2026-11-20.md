# Devoluciones sin Excel: diseño v1 (20/11/2026)

**Estado: solo diseño, sin código.** Espera el visto bueno de Isaac (preguntas al final) y las respuestas de Betty.

Fuentes:
- Reunión en el almacén del 20/11 con Cruz (manipulaciones) y Betty (facturación): grabaciones 29 y 30.
- Resumen de la reunión: `bin/versiones/plan-grabaciones-29-30_2026-11-20.md`, puntos 1 y 2.
- Código leído: `koroshi_s4t_traspasos` 1.3.0, `koroshi_contenedores` 1.9.1 y la tarjeta compartida de
  `koroshi_operarios` 2.22.1.

Regla de Isaac: **quitar todos los Excel**. Hoy, además, hay gente en un taburete consultando la API de S4T a mano
mientras manipula. Esta herramienta quita las dos cosas.

---

## 1. Lo que se dijo (lo que hay que cumplir)

**Hoy.** Cruz manipula la prenda y la deja en un cajón según lo que le ha hecho (un cajón por tipo). Después se coge
el cajón y se ubica apuntándolo en un Excel. Ese Excel sirve para saber qué se ha hecho y para facturarlo.

**Las tres opciones** (Betty, grabación 30):
- **Quitar precio**: abrir la bolsa y quitar el cartón del precio. Se reaprovecha la bolsa (sobre todo en Marketplace).
- **Quitar precio y embolsar**.
- **Reetiquetar y embolsar**: se cambia la etiqueta (o el precio) y se aprovecha para embolsar.

Desalarmar no entra: las chapas se juntan y se piden alarmas aparte.

**Facturación.**
- Betty: «cobramos por recepcionar, cobramos por ubicar, cobramos por manipular».
- Las tres opciones se facturan por separado. Betty: «son distintos, ya se junta después al facturar».
- En «reetiquetar y embolsar» Betty dijo «tendría que cobrar dos cosas en esa prenda».
- M1, M2 y M3 son los códigos de factura. **No quedó claro cuál es cuál**. En la grabación 30 se oye «M2 y M3: uno
  es quitar precio y el otro es embolsar», y más tarde «ella dice que eso es un M1».
- El operario no ve M1/M2/M3: ve las palabras.

**El proceso entero** (Isaac, grabación 30):
1. Llega el paquete.
2. Se lee lo que lleva contra lo esperado.
3. Al leer, se marca la manipulación.
4. Se manipula por días.
5. Se ubica.

«Han comenzado por el final.» Primero se hace el final (ubicar), porque es rápido y le quita el Excel a Cruz.

---

## 2. Módulo: **`koroshi_devoluciones`, nuevo**

| Opción | Por qué no / por qué sí |
|---|---|
| Ampliar `koroshi_contenedores` | No. Es el área de **compactación** y se usa todo el día. Meter ahí devoluciones mezcla dos áreas de la entrada única. Además, cada versión de devoluciones obligaría a actualizar la pantalla de compactar. |
| Ampliar `koroshi_s4t_traspasos` | No. Es un proceso de fondo que habla con la API de S4T (cron cada 15 min, en real desde el 19/11). No tiene pantalla de PDA y no conviene tocarlo por cada cambio de pantalla. |
| Ampliar `koroshi_actividades` | No. Ahí se mide el tiempo con un botón, sin lecturas. Lo de devoluciones lleva lecturas, prendas y un informe para facturar. |
| **Módulo nuevo `koroshi_devoluciones`** | **Sí.** Un área de la PDA es un módulo y puede tenerlo una sola sesión (regla 6). Solo escribe en sus tablas. Si falla, no tumba Lecturas ni Contenedores. |

**Dependencias.**
- **Fase 1**: `stock`, `hr`, `barcodes`, `koroshi_base` y `koroshi_operarios` (tarjeta).
- **Fase 2**: además `koroshi_s4t_traspasos`, para saber qué trae cada devolución web.
  - Fase 2 sale como una versión 2.x del mismo módulo.
  - Si Isaac prefiere que la Fase 1 no dependa de S4T, la Fase 2 puede ir en un segundo módulo,
    `koroshi_devoluciones_s4t`.

**Sin campos nuevos** en `stock.picking`, `stock.picking.type` ni `stock.move.line`. Tampoco en `stock.location` ni
en `product.product`.

---

## 3. Fase 1: «Ubicar devoluciones» en la PDA

### 3.1 Pantalla (PDA o portátil)

Hasta que exista la entrada única por áreas, se abre como app propia (icono «Devoluciones»). Después será la pestaña
**Devoluciones** de esa entrada. Lo diseña la sesión «PDA, entrada única por áreas».

1. **Tarjeta.** La pantalla coge la tarjeta guardada en la PDA (`koroshi_operarios_pda_<uid>`), igual que
   Contenedores 1.9.1. Dura lo que diga `koroshi_operarios.minutos_tarjeta`. Si no hay tarjeta, la pide.
2. **Tres botones grandes**, con las palabras:
   - **Quitar precio**
   - **Quitar precio y embolsar**
   - **Reetiquetar y embolsar**

   La opción elegida queda arriba, en grande y con su color, hasta que se cambie. Así nadie lee un cajón con la
   opción del anterior.
3. **Leer prendas.** Cada lectura cuenta 1 ud. Se ve la lista, con el artículo, la talla y las uds.
   - «Quitar la última».
   - «Cantidad» para N uds de golpe, como en Contenedores.
   - Un EAN que no está en Odoo pita, dice «Prenda no encontrada» y no se cuenta.
4. **Leer el contenedor o la ubicación.** Al leerlo se guarda la tanda y la pantalla dice, por ejemplo,
   «Guardado: 23 uds de Quitar precio y embolsar en KO_201126_0012».
   - La opción se queda puesta para el siguiente cajón.
   - Valen las dos formas de trabajar que se dijeron: «prenda, contenedor, prenda, contenedor» y «prenda, prenda,
     prenda y contenedor».
5. **Cambiar de opción** con prendas leídas y sin guardar: lo pregunta antes, para no perder lecturas.

Qué vale como «contenedor o ubicación»:
- un contenedor `KO_`/`TT_` que exista;
- o el código de barras de un hueco de la compañía 8 (no los de UBRAN; el mismo fallo se arregló en Contenedores
  1.8.1).

Si no es ninguno de los dos, pita y no guarda.

### 3.2 Qué se guarda (modelos nuevos, solo en este módulo)

**`koroshi.devolucion.manipulacion`**: el catálogo de opciones. Lo edita un jefe, no el código.

| Campo | Ejemplo | Para qué |
|---|---|---|
| `name` | «Quitar precio y embolsar» | Lo que ve el operario |
| `codigo_factura` | «M2» (lo dice Betty) | Solo en el informe |
| `concepto_ids` | M2 + M3 | Si una opción se cobra como dos conceptos («reetiquetar y embolsar» = dos cosas) |
| `color`, `sequence`, `active` | | Orden y color del botón. Si Betty añade una opción, no hace falta programar |

**`koroshi.devolucion.ubicada`**: una línea por artículo y tanda. El informe sale de aquí.

| Campo | Qué es |
|---|---|
| `tanda` | Número de la tanda: todas las prendas que acaban en el mismo contenedor de una vez |
| `employee_id` | Quién (tarjeta) |
| `user_id` | Usuario de Odoo (la PDA) |
| `fecha` | Cuándo (Datetime) |
| `dia` | El día en hora del almacén (`koroshi_base.comun`). Así una tanda de las 00:30 no cae en el día anterior al agrupar |
| `manipulacion_id` | Qué opción |
| `product_id` | Artículo |
| `uds` | Unidades |
| `contenedor` | Texto leído |
| `ubicacion_id` | El contenedor o el hueco, en `stock.location` (Many2one, sin tocar la tabla) |
| `estado` | `hecha` / `anulada`. Un jefe puede anular una tanda leída por error; no se borra y queda quién la anuló |

### 3.3 Stock: **en la 1.0, solo se apunta y no se mueve** (pregunta P1)

El Excel de hoy solo apunta. Mover stock a la vez tiene tres riesgos:
- Las prendas tienen que estar en Odoo en una ubicación de origen conocida. Las web entran por la recepción DEV a
  `DEVOLUCIO_KOROSHI`, pero solo si alguien la valida. De las de tienda y Zalando no sabemos dónde están en Odoo.
- Si no están, el movimiento falla o deja stock en negativo, y el operario se queda parado con el cajón en la mano.
- Facturar no necesita mover stock.

Propuesta:
- **1.0: solo registro.** Rápido, sin riesgo, y quita el Excel desde el primer día.
- **1.1 (opcional)**: se mueve el stock del origen que diga Isaac al contenedor leído. Se haría con un movimiento
  interno, no con un ajuste de inventario. Encaja mejor después de la Fase 2, cuando la entrada de la devolución ya
  está en Odoo.

### 3.4 Informe para facturar (Cruz y Betty)

En el menú: **Devoluciones › Informe para facturar**. Es una vista pivote y gráfica de `koroshi.devolucion.ubicada`:
- **Filas**: día, semana o mes (con el `dia` del almacén).
- **Columnas**: código de factura (M1/M2/M3). Si una opción tiene dos conceptos, cuenta en los dos.
- **Valor**: uds.
- Filtros listos: «Este mes», «Mes pasado», «Esta semana», «Hoy», y por operario.
- Betty lo baja a Excel con el botón de Odoo si lo necesita para la factura. Es una salida, no un Excel en el que se
  trabaja.

En la lista, también: quién ha ubicado cuánto cada día, para el responsable.

### 3.5 Lo que no hace la Fase 1

- No mira de qué paquete viene la prenda.
- No dice si la prenda estaba bien o era tara.
- No mide el tiempo del área: eso es de la entrada única. Aun así, cada tanda guarda la hora y se podría sacar un
  ritmo aproximado.

### 3.6 Pruebas

- **En local**: lecturas, tanda, anular e informe con datos de prueba.
- **En producción**: es un módulo nuevo y no toca stock, así que se puede probar con prendas reales sin riesgo.
  Una tanda de prueba se anula.
- **En una PDA real**:
  - tarjeta compartida con Lecturas y Contenedores;
  - pitido en un EAN desconocido;
  - leer un `KO_` y un hueco;
  - las dos formas de trabajar (una prenda y su contenedor, o muchas prendas y un contenedor).

---

## 4. Fase 2: el proceso entero (por etapas, cada una una versión)

### 4.1 Llega el paquete: «Ha llegado hoy»

En la PDA, pestaña **Llegadas**. Se lee lo que trae el paquete:
- una matrícula `CJ…` si es de tienda;
- un código de Zalando;
- o el código del transportista (GLS, etc.).

Queda «ha llegado hoy, lo leyó X». Después se puede buscar: «lo de GLS del día 28».

**`koroshi.devolucion.paquete`**

| Campo | Qué es |
|---|---|
| `codigo` | Lo leído (indexado, para buscar) |
| `tipo_codigo` | `matricula_tienda` / `zalando` / `transportista` / `otro`. Se adivina por el formato y el operario lo puede cambiar |
| `canal` | `tienda` / `web` (V2C) / `zalando` / `marketplace` |
| `tienda_id` | Tienda (`res.partner` con barcode), si es matrícula |
| `transportista` | Transportista |
| `llegada`, `dia`, `employee_id` | Cuándo llegó y quién lo leyó |
| `traspaso_id` | → `koroshi.s4t.traspaso`, si se encuentra la devolución web que le corresponde |
| `box_id` | En qué box del día ha quedado (4.4) |
| `estado` | `llegado` → `leido` → `manipulado` → `ubicado` |

Cuidado con las matrículas: las de tienda (`CJ080…`, `CJ065…`) tienen el mismo formato que nuestras cajas de salida
`CJ665…`. Ya se vio en el diseño de inversa del 12/11. Aquí no molesta, porque es otra pantalla, pero el prefijo
`CJ665` se rechaza con aviso.

### 4.2 Qué lleva: bien / tara / no ha llegado

Se abre el paquete y se leen las prendas contra lo esperado.

**`koroshi.devolucion.paquete.linea`**

| Campo | Qué es |
|---|---|
| `product_id` | Artículo |
| `esperadas` | Uds esperadas |
| `leidas` | Uds leídas |
| `bien` | Uds que están bien |
| `tara` | Uds con tara |
| `manipulacion_id` | Qué manipulación necesita |
| `resultado` | `bien` / `tara` / `no_ha_llegado` / `no_esperada` |

De dónde sale lo esperado:

| Canal | Fuente | Estado hoy |
|---|---|---|
| Web (V2C) | `koroshi.s4t.traspaso` (DevoEcom, API) | Ya entra (en real desde el 19/11). **Falta saber cómo casar el paquete con el traspaso**: no sabemos si el JSON trae el tracking de GLS o el número de pedido (pregunta a S4T) |
| Tiendas | Teórico por matrícula de S4T | **No lo tenemos**. Pregunta a S4T del 14/11 sin respuesta. Existen `POST /matriculas/verify` y `POST /box/validate` (OK / FALTA / EXCEDE), que podrían servir |
| Zalando | ? | Sin fuente conocida |
| Sin información | Lo leemos nosotros | «O ells mos ho passen, o nosaltres fem la lectura i els enviem» |

Cuando no hay información, se lee todo y se manda a quien toque. Cómo se manda (correo, fichero o API de S4T) es una
pregunta para S4T y para KOROSHI. En esta etapa no se manda nada solo.

### 4.3 Al leer se marca la manipulación

En la misma pantalla de 4.2, cada lectura va por defecto a «Está bien → a su puesto».

Si la prenda necesita algo, se toca el botón de la manipulación antes de leerla (o después, sobre la última). Los
botones son:
- **Quitar precio**;
- **Quitar precio y embolsar**;
- **Reetiquetar y embolsar**;
- **Tara**.

Es el mismo catálogo de la Fase 1, más «Tara», que no se factura como manipulación.

### 4.4 Manipular por días: un box por día y canal

Isaac no quiere ubicaciones nuevas: «crear ubicació mos mataran». El box es un **registro**, no una
`stock.location`.

**`koroshi.devolucion.box`**

| Campo | Qué es |
|---|---|
| `name` | «20/11 V2C», «20/11 Tiendas»… |
| `dia`, `canal` | Día y canal |
| `prioridad` | Prioridad |
| `estado` | `abierto` / `manipulando` / `hecho` |
| uds | Por manipulación (calculado de las líneas) |

Se imprime una etiqueta con código de barras para la zona del palé. Al acabar la lectura de un paquete, sus prendas
para manipular caen en el box de su día y canal. Las de tienda pueden ir por matrícula, como se dijo.

El responsable ve la lista de boxes:
- «hazme el de ayer»;
- cuántas prendas tiene cada uno y de qué tipo;
- un tiempo estimado (uds × minutos por tipo, un parámetro que se ajusta con lo real);
- y puede subir la prioridad.

Cuando el tablero lo permita, «Manipular box 19/11 V2C» puede ser una tarjeta que se arrastra a una persona. Lo
decide la sesión del tablero.

### 4.5 Ubicar

Es la Fase 1. Con la Fase 2 detrás:
- leer el box (opcional) propone su manipulación y avisa si una prenda no estaba en el box;
- la tanda queda ligada al box y al paquete;
- el box pasa a «hecho» cuando todo está ubicado.

### 4.6 Qué toca de stock la Fase 2 (a decidir más adelante)

Para las web, lo natural es que la lectura de 4.2 rellene y valide la recepción DEV que ya crea
`koroshi_s4t_traspasos`. Así la devolución entra en Odoo con lo que ha llegado de verdad, no con lo que dice S4T.
Ubicar (1.1) movería después de `DEVOLUCIO_KOROSHI` al contenedor.

Esto valida albaranes y mueve stock, así que **se decide aparte** y con pruebas.

### 4.7 Cómo encaja con lo que ya existe

| Módulo | Relación |
|---|---|
| `koroshi_s4t_traspasos` | Fuente de lo esperado en las web. Devoluciones lo **lee** (Many2one a `koroshi.s4t.traspaso`) y no le cambia nada. Si algún día validamos la DEV desde la lectura, el cambio va en devoluciones, no en traspasos |
| `koroshi_contenedores` | Mismos contenedores `KO_`/`TT_` y huecos de la compañía 8. Devoluciones repite **la misma búsqueda** (solo compañía 8, nombre literal sin `=ilike`), sin depender del módulo. Si se pasa a `koroshi_base`, cada módulo se cambia con su versión. Lo de Contenedores (mover, poner a cero, añadir) no se toca |
| `koroshi_operarios` | Tarjeta compartida (clave `koroshi_operarios_pda_<uid>` y `minutos_tarjeta`) |
| Entrada única por áreas (otra sesión) | «Devoluciones» es una pestaña. Esa sesión cuenta el tiempo del área; esta pone la pantalla |
| `koroshi_actividades` | «Manipulación devoluciones» sigue allí mientras la manipulación no tenga lecturas |
| `api_s4t_batch_update_PROD` (`s4t.matricula`) | Para tiendas, si S4T no da el teórico, nuestro recuento es lo que leemos (ya pasó con inversa) |

---

## 5. Lo que tiene que confirmar Betty (para la factura)

Isaac se lo puede pasar tal cual:

1. **¿Qué código es cada opción?** ¿«Quitar precio» es M1, M2 o M3? ¿Y «Quitar precio y embolsar» y «Reetiquetar y
   embolsar»? En la reunión salieron dos versiones distintas.
2. **¿«Reetiquetar y embolsar» se cobra como un concepto o como dos** (reetiquetar + embolsar)? ¿Y «Quitar precio y
   embolsar»: uno o dos (quitar precio + embolsar)?
3. **¿Se cobra igual «Quitar precio» que «Quitar precio y embolsar»?** Si el precio es el mismo, ¿hace falta separarlas
   en el informe? (Recomiendo separarlas igual: no cuesta nada.)
4. **Ubicar se cobra aparte** («cobramos por ubicar»): ¿se cobra también ubicar una prenda que **no** se ha
   manipulado? Si es que sí, hace falta una cuarta opción para el operario, **«Sin manipular»**, para que también se
   cuente.
5. **¿Por prenda (uds) o por otra cosa** (por paquete, por pedido)? Recepcionar, ¿por paquete o por prenda?
6. **¿La factura separa canal** (web, tiendas, Zalando, marketplace) o va todo junto? Si separa, en la Fase 1 el
   operario tendría que elegir también el canal, o hay que esperar a la Fase 2, donde lo da el box.
7. **Periodo**: ¿mes natural? ¿La semana empieza en lunes?
8. **La tara**: ¿se cobra algo por revisar o separar la tara?

---

## 6. Preguntas a Isaac (para empezar la Fase 1)

- **P1. Stock.** ¿La 1.0 solo apunta (como el Excel) o mueve el stock al contenedor? Recomiendo **solo apuntar**
  (3.3). Una pregunta para saberlo: el Excel de hoy, ¿se sube después a Odoo para mover stock, o solo sirve para
  contar?
- **P2. Qué se lee al final.** ¿Contenedor `KO_`/`TT_`, hueco, o los dos? Recomiendo **los dos**, siempre que existan.
  ¿Los contenedores de devoluciones ya tienen su etiqueta `KO_` impresa, o hace falta crearlos desde la pantalla?
- **P3. Módulo nuevo `koroshi_devoluciones`.** ¿De acuerdo? Mientras no esté la entrada única, sale como app propia
  con su icono.
- **P4. Opciones.** Hasta que conteste Betty, ¿empiezo con las tres opciones y sus códigos sin poner (se rellenan en
  el catálogo sin programar)? Y la cuarta, «Sin manipular», ¿la pongo ya o espero a Betty (pregunta 5.4)?
- **P5. Fase 2.** Con lo que sabemos hoy, ¿la primera etapa es «Llegadas» (4.1), aunque todavía no podamos casar el
  paquete con lo esperado? Antes hay que preguntar a S4T si el DevoEcom trae el tracking del transportista.

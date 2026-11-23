# Diseño v2: recepción por contenedor (`koroshi_recepcion`, módulo nuevo), 23/11/2026

**Solo diseño. Sin código hasta que Isaac lo apruebe.** Sustituye a la v1
(`diseno-recepciones-packing-list_2026-11-19.md`, que se conserva).

Fuente nueva: la reunión en el almacén del 23/11 (`C:\Users\tuctuc\Videos\Nueva grabación 32_1975.txt`, transcripción
automática en catalán y castellano; la parte de recepciones está en las líneas 9-16, 48-79 y 92-98). Isaac: «Mira
esto, es importante: sería el apartado de recepciones».

## 0. Qué cambia respecto a la v1

| v1 (19/11) | v2 (reunión 23/11) |
|---|---|
| Se carga el Excel del packing list de Maite | Se entra **por el contenedor marítimo** (su matrícula). Los shipments y las PO ya están en el sistema y solo se enseñan como **información** |
| Se marca la caja tocando la pantalla, sin leer artículos | **Se lee cada caja**: artículo, cantidad, contenedor de control y palé. A ciegas: el operario no ve el teórico |
| Puestos con nombre libre | **Palés 1…N con cara A y cara B** |
| Cajas sin etiqueta | **Una etiqueta por caja**: un «contenedor de control» impreso (muelle-fecha-número, 6 etiquetas por fila) |
| Avance por grupos de cajas | Al acabar, **validar contra el packing list** con avisos de diferencias por modelo, y para cada modelo en qué palés y contenedores está |
| — | Fase 2: **ordenar y ubicar** por EAN, modelo, colección y familia con colores, **picos**, y quitar los contenedores de control |
| — | **Reabrir un shipment** que llegó incompleto, cuando llegan las cajas que faltaban |

## 1. El proceso, tal como lo contaron

**Recepción (fase 1, la urgente):**
1. Llega el camión. Se mira la matrícula del contenedor (en la puerta y en el lateral). Es obligatoria: «igual que los
   camiones llevan matrícula, los contenedores también».
2. En la PDA o tablet, **Recepciones** enseña los contenedores pendientes de llegar. Se elige el contenedor y sale su
   información: hora de llegada, **total de cajas** (p. ej. 675), shipments y PO que van dentro y bultos por shipment.
   Es solo para mirar.
3. **«Recepcionar»** abre la lectura **en blanco**: no se enseña lo que debería haber.
4. Lo primero: **generar e imprimir un contenedor de control por caja** (675 cajas = 675 contenedores). Su nombre lleva
   el muelle, la fecha y el número (`M1-231126-001`…). Se imprimen 6 etiquetas por fila y se pega una a cada caja.
   «Solo es para tener trazabilidad hasta que se ubica».
5. **Lectura**, caja a caja, como hacen hoy pero contra el contenedor:
   - artículo, por código de barras o, si no lo hay, con un **buscador táctil** (modelo, descripción o los últimos 4
     dígitos del EAN);
   - cantidad;
   - contenedor de control (se lee la etiqueta);
   - palé y cara (Palé 1 A, Palé 1 B, Palé 2 A…).
6. **Validar**: compara lo leído con el packing list (los shipments). Si tenían que llegar 761 y no están, avisa. Por
   modelo: «tenían que llegar 150 y hay 140, falta una caja» (o sobran 25). Al desplegar el modelo se ve en qué palé y
   en qué contenedor está cada caja, para ir a revisar.
7. Se **exporta** y **se sube al sistema**. La mercancía ya está en Odoo, en su contenedor y su palé, y «hasta se podría
   hacer picking» desde ahí.

**Ordenar y ubicar (fase 2, «este paso no lo calientes; primero la recepción»):**
- Lista ordenada por EAN, modelo, colección y familia (en KOROSHI no hay colección: va directo a modelo).
- Cada modelo enseña sus contenedores y palés. Un operario coge la tarea y lleva las cajas a su palé.
- Estado con colores: gris sin empezar, naranja trabajándose, verde acabado. Queda quién lo hizo y cuándo.
- Función «poner colores»: cada modelo tiene un color de fondo y la persona pega la hoja de ese color.
- **Picos**: cajas con varias tallas o incompletas. Al ordenar, la misma caja sale en varios sitios. Hay que sacar las N
  prendas y **traspasarlas a otro contenedor**, como en Compactar.
- **Quitar los contenedores de control** al ubicar («eliminar, archivar»): el contenido queda en la ubicación final.
  Para mover contenedores ya sirve Compactar.

**Shipment incompleto:** a veces faltan cajas que llegan después en otro camión. Hace falta un buscador para
**reabrir el shipment** y recibir las cajas que faltaban.

**Impresión:** las etiquetas de palé se pueden marcar con rotulador («lo de imprimir no lo calientes»). Las de los
contenedores de control sí hacen falta: de momento, un PDF que se imprime desde un ordenador. Imprimir desde la PDA es
el tema aplazado de siempre (cola en Odoo y un script en el PC de la impresora).

## 2. Qué no sabemos de Odoo (decide gran parte del diseño)

Según la reunión, **la IN se crea sola** («sube por la API, creo»), una por shipment. Una PO puede llegar en varios
shipments. En el repo no hay nada de compras ni de recepciones de proveedor (lo miró `lector-modulo` el 19/11).
Antes de programar hay que leer en la BD, **solo leyendo y con el sí de Isaac**:
- dónde está la **matrícula del contenedor** marítimo (en la IN, en un modelo de shipment, en `origin`…);
- si existe un modelo de **shipment** o solo IN con un origen;
- si el teórico de un shipment es **por EAN** (lo normal) o **por caja**, y de dónde sale el **total de cajas**;
- el tipo de operación y la ubicación de destino de esas IN, y si dejan pendiente (*backorder*) lo que no llega.

## 3. Tablas propias

Ningún campo nuevo en `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Las relaciones van de
nuestras tablas a las de Odoo.

| Modelo | Una fila es | Campos principales |
|---|---|---|
| `koroshi.recepcion` | un contenedor marítimo que llega | matrícula, muelle, fecha y hora de llegada, IN de Odoo (Many2many a `stock.picking`: los shipments que trae), total de cajas esperado, estado (`pendiente` → `leyendo` → `validada` → `en_stock` / `cancelada`), quién y cuándo |
| `koroshi.recepcion.lectura` | una línea leída: lo que hay en una caja | recepción, contenedor de control (Many2one a `stock.location`), palé, cara (A/B), producto, cantidad, operario (`hr.employee`), hora, estado (`ok`, `anulada`) |
| `koroshi.recepcion.palet` | un palé de esa recepción (o del muelle) | número, cara, ubicación de Odoo (si se decide que lo sea, punto 4) |

El **teórico no se copia**: sale en cada momento de los `stock.move` de las IN enlazadas (cantidad pedida por
producto). Así, si compras corrige la IN, la comparación ya lo coge. Si al final no hay IN con teórico (punto 2), se
añade la importación del Excel de la v1 como plan B.

Una caja con varias tallas son varias lecturas con el mismo contenedor de control. Que el mismo contenedor salga con
modelos distintos es justo lo que la fase 2 trata como «pico».

## 4. Contenedores de control y palés en Odoo

Propuesta: **los contenedores de control son `stock.location` de verdad**, como los KO_/TT_ de Contenedores. Así, al
subir al sistema, el stock queda en su contenedor, se puede buscar (Buscador de stock), hacer picking si hace falta,
y moverlo con Compactar.

- Se crean con «Recepcionar» (uno por caja, según el total de cajas; botón «+10» si salen más) dentro de una ubicación
  del muelle (`EFFEC/Stock/Muelle 1`, o la que diga Isaac). Su código de barras es su nombre.
- **Palé y cara**: dos opciones.
  - (a) El palé es solo un dato de la lectura (columna de nuestra tabla). Lo más sencillo, pero Odoo no sabe en qué
    palé está cada contenedor.
  - (b) Cada «Palé N cara A» es una `stock.location` del muelle y los contenedores de control quedan **dentro** del
    palé, como hoy un KO_ dentro de un hueco. Odoo lo sabe y Compactar ya mueve contenedores de un sitio a otro.
  - **Propuesta: (b)**, porque en la reunión dicen que el palé «no es solo visual, también lo has de ubicar».
- **Quitar los contenedores de control** (fase 2): pasar su contenido a la ubicación final y archivar la ubicación
  vacía.
- Formato del nombre: muelle-fecha-número (`M1-231126-001`). **Ojo:** las pantallas de Contenedores reconocen los
  contenedores por el prefijo `KO_`/`TT_`. O se les da un prefijo que Contenedores ya entienda, o hay que tocar
  Contenedores, que lo lleva otra sesión: es un cambio en dos módulos y se avisa antes.
- **Ya hay piezas hechas el 23/11** (`diseno-crear-imprimir-lineales-contenedores_2026-11-23.md`,
  `koroshi_ubicaciones` 1.0.0 sin instalar). Los KO_ son `KO_ddmmaa_NNN`, con código = nombre, y nacen en
  `EFFEC/Stock/NAVE2`. Ya existen huecos de muelle (`MU-04 P18 C1`). Y `koroshi_ubicaciones` crea contenedores en
  tanda y saca su PDF en la Zebra 4x6 del PC de Recepciones. Lo más simple sería que **los contenedores de control
  fuesen KO_ normales**: Contenedores, Compactar y el Buscador ya los entienden y no hay que tocar nada. Lo que se
  pierde es el muelle en el nombre: el muelle y la fecha quedarían en nuestra tabla y en el PDF, debajo del código.
  Hay que decidir el formato (pregunta 4) y si las etiquetas van en hoja de 6 por fila o en la Zebra (pregunta 6).
- Crear ubicaciones es escribir datos en producción. Lo hace el módulo en su botón, con permiso de Isaac para la
  primera prueba.

## 5. Cómo se pasa a stock

Al pulsar **«Validar»** en la recepción:
1. **Comparación** por producto (EAN), agrupada por modelo: teórico de las IN, leído y diferencia. Aviso de lo que
   falta, de lo que sobra y de los productos leídos que no venían en ningún shipment. Si hay diferencias, pide
   confirmación con la lista delante.
2. **Rellenar las IN**: en cada IN enlazada se ponen las `stock.move.line` con `qty_done`, el producto, la cantidad y
   **la ubicación de destino = el contenedor de control**. Si un producto viene en dos shipments, se reparte en el orden
   de las IN. Lo que sobra o no venía en ningún shipment no se añade solo: queda en la lista de diferencias.
3. **Validar la IN** (`button_validate`), con *backorder* para lo que no ha llegado. **Esa IN pendiente es el
   «shipment incompleto» que se reabre**: cuando llegan las cajas, se elige el contenedor nuevo, se enlaza a esa IN
   pendiente y se repite la lectura.

**Pregunta abierta:** el paso 3 lo puede hacer el módulo (lo que pidieron en la reunión: «se valida y ya puedes
trabajar») o dejarlo a back office, como la DEV de traspasos. Propuesta: el módulo rellena (paso 2) y el botón
«Validar en Odoo» solo sale al responsable de recepciones, no al operario.

## 6. Pantallas (fase 1)

Acción cliente propia en **KOROSHI > Recepciones**, para PDA y tablet, con ruta JSON propia y `role="presentation"`
(nunca `aria-hidden`). El operario entra con su sesión de `hr.employee`, como en Contenedores.

1. **Contenedores pendientes**: matrícula, fecha prevista, nº de cajas, shipments. Buscador por matrícula (también
   para reabrir un shipment incompleto).
2. **Ficha del contenedor**: información (shipments, PO, bultos por shipment, total de cajas) y el botón
   **«Recepcionar»**.
3. **Recepcionar**: «Generar contenedores de control» (nº de cajas, muelle) e «Imprimir etiquetas» (PDF de 6 por fila)
   y después la **lectura**:
   - arriba, el palé y la cara activos (se cambian con dos botones grandes, o leyendo su etiqueta si la hay);
   - leer el contenedor de control (o tocar «siguiente»);
   - leer el artículo, o el buscador: se escribe «27 onde» o los 4 últimos dígitos del EAN y salen los modelos con
     sus tallas; se toca una;
   - cantidad con teclado grande; «Guardar» y pasa a la siguiente caja;
   - abajo, las últimas lecturas con «Anular»; se ve el número de cajas leídas sobre el total, pero **no el teórico**.
   - Protección contra el doble toque de la PDA (salió en la reunión: «esta PDA cliquea dos veces»): el botón se
     bloquea hasta que responde el servidor y la misma lectura repetida en menos de 2 s se ignora.
4. **Validar** (responsable): la comparación por modelo, con desplegable de palés y contenedores; botones «Exportar»
   (Excel con filtros: falta, sobra, no venía) y «Validar en Odoo».

## 7. Qué NO toca

- Ningún campo nuevo en tablas compartidas ni en tablas de Odoo. Solo crea registros: ubicaciones (contenedores de
  control y palés) y las líneas de las IN.
- No toca compras, PO ni el estado «despachado» o «en tránsito»: «eso es de compras y back office».
- En la fase 1 no toca Contenedores (si hace falta el prefijo, se pregunta antes), preparación, PDA de picking, zonas ni
  S4T.
- No imprime desde la PDA (aplazado). Las etiquetas salen en PDF.
- Depende de `stock`, `hr`, `koroshi_base` y `koroshi_menu`. Se instala solo, con `-i`, y nunca a la vez que otra
  actualización.

## 8. Fases

1. **Fase 1, recepción**: puntos 3 a 6. Lista de contenedores, información, contenedores de control con su PDF,
   lectura a ciegas con buscador, palés A/B, comparación, exportación, rellenar las IN y validar con backorder (reabrir
   el shipment incompleto). Antes, la lectura en la BD del punto 2.
2. **Fase 2, ordenar y ubicar**: tareas por modelo con colores y estados, quién lo hizo, picos y traspaso de prendas
   entre contenedores, quitar los contenedores de control. Seguramente un cambio en dos módulos (con Contenedores).
3. **Después**: imprimir desde la PDA o desde las estaciones (cola de Odoo) y etiquetas de palé.

## 9. Qué queda decidido y qué queda pendiente

**Decidido en la reunión:**
- Se entra por la matrícula del contenedor; shipments y PO solo como información.
- Lectura en blanco, caja a caja: artículo + cantidad + contenedor de control + palé con cara.
- Un contenedor de control por caja, nombre muelle-fecha-número, 6 etiquetas por fila.
- Buscador táctil por modelo o por los últimos 4 dígitos del EAN.
- Palés 1…N con cara A/B; las etiquetas de palé, por ahora, a rotulador.
- Validar contra el packing list con avisos y con dónde está cada caja.
- Ordenar y ubicar, picos y colores van después.
- Hay que poder reabrir un shipment incompleto.

**Pendiente (preguntas para Isaac):**
1. **Leer la BD** (solo lectura): dónde está la matrícula del contenedor, si hay modelo de shipment, de dónde sale el
   total de cajas y cómo se crean las IN. ¿Doy el paso? Sin esto no se puede empezar a programar.
2. **¿Quién valida la IN en Odoo?** ¿El módulo, con el botón del responsable, o back office aparte?
3. **Palé como ubicación de Odoo** (opción b del punto 4) o solo como dato.
4. **Nombre de los contenedores de control**: ¿KO_ normales (`KO_231126_001`, con el muelle solo en la etiqueta; no
   se toca nada más) o `M1-231126-001` tal cual, que obliga a tocar Contenedores para que lo reconozca?
5. **¿Qué ubicación es el muelle** (`EFFEC/Stock/Muelle 1`…) y cuántos muelles hay?
6. **Etiquetas**: ¿hoja A4 de 6 por fila (¿qué marca y modelo?) o la Zebra 4x6 del PC de Recepciones, como
   `koroshi_ubicaciones`?
7. ¿Hace falta todavía el packing list de Maite? Solo si las IN no traen el teórico (punto 2).

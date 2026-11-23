# Diseño v5: recepción por contenedor (`koroshi_recepcion`, módulo nuevo), 23/11/2026

**Diseño de la fase 1 aprobado por Isaac (23/11).** Sin código todavía: falta que el almacén confirme quién crea el
contenedor (punto 9). Es la v4 con las decisiones de Isaac. Se conservan la v1
(`diseno-recepciones-packing-list_2026-11-19.md`) y la v2, la v3 y la v4 (`diseno-recepciones-packing-list_2026-11-23_v2.md`,
`_v3.md` y `_v4.md`).

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

## 2. Cómo está hoy en Odoo (leído en producción el 23/11, solo lectura)

Leído con el usuario Departament IT desde el navegador, solo con `search_read`, `search_count`, `read_group` y
`fields_get`. No se ha escrito nada.

**Las IN de KOROSHI:**
- Tipo de operación **44, «6665 STOCK GENERAL KOROSHI: Recepciones»** (secuencia IN). Van de `Partner Locations/Vendors`
  a **`EFFEC/RECEP_KO`**, una ubicación interna sin hijos y hoy vacía.
- Las crea **OdooBot por API**, a las 18:00, una por **pedido de compra del sistema de KOROSHI**: el `origin` es su
  número (`0000002142`). El proveedor de la IN siempre es DIGITAL E-GLOBAL XPERIENCE, SL. No hay ningún cron en Odoo que
  las cree, así que vienen de fuera (S4T o el ERP de KOROSHI: por confirmar).
- El teórico es **por artículo** (un `stock.move` por SKU: `2711SU06-000015-M`, 75 uds). **No hay cajas**: ni nº de
  bultos (`number_of_packages` = 0) ni cajas por artículo.
- `x_studio_order_remarks` (y `note`) trae a veces una referencia del proveedor, que parece **el nº de factura o del
  BL** (`HT26343HZ155`, `LY26030039`, `SSL-2026/177`, `BL2026-010A`…). Muchas veces está vacío o es «xxxx». Dos IN con
  la misma referencia (IN/00388 y IN/00391, `HT26343HZ155`) son seguramente el mismo envío con dos pedidos.
- **No hay matrícula del contenedor en ningún sitio.**
- Estados: 91 abiertas (`assigned`), 215 hechas, 44 canceladas y 6 en borrador.

**Cómo reciben hoy:** el usuario «Almacén Nath» (la PDA) valida la IN **a trozos, varias veces al día, con
backorder**. Por ejemplo, el pedido 0000002134 pasó por IN/00350 → 00351 → … → 00360, de 15 a 5.830 uds cada vez, entre
el 07/10 y el 20/10. **El destino de cada línea es un contenedor KO_**: la IN/00381 dejó sus 706 uds en
`EFFEC/Stock/NAVE2/KO_301026_145` a `_150`. O sea, **hoy ya leen artículo + cantidad + contenedor KO_**, que es casi
lo que pidieron en la reunión. Lo que falta es el palé, el contenedor marítimo, la lectura a ciegas, la comparación
clara y la pantalla.

**El módulo de shipments existe, pero KOROSHI no lo usa.** `shipment_management` tiene `purchase.order.shipment` con
`container_no`, `number_of_cartons` y líneas con `box_no`, y en `stock.picking` el campo `shipments_ids`. Pero sus
1.127 shipments son de otras marcas (Code22, Kayser Roth, Ateliers Isa; el último es de marzo de 2025). **Las IN de
KOROSHI no tienen ningún shipment.** No se usa: sería otro circuito de compras, y esto es de back office.

**Muelle:** hay 980 huecos `MU-xx Pyy Cz` en `EFFEC/Stock/NAVE2` (`MU-00 P01 C1`…).

**Consecuencias para el diseño:**
1. **El contenedor marítimo no existe en Odoo**: lo crea nuestra tabla. La matrícula y el total de cajas los escribe
   quien recibe (o la oficina al saber que llega). Se le enlazan una o varias IN abiertas del tipo 44: el buscador
   enseña `origin`, la referencia del proveedor y las uds.
2. **El teórico sale de las IN enlazadas, por SKU.** No hay teórico por caja. El total de cajas solo se compara si
   alguien lo escribe (del papel del proveedor). El packing list de Maite solo haría falta para comparar caja a caja.
3. **Contenedores de control = KO_ normales**: es lo que ya se usa como destino de las IN.
4. **«Reabrir un shipment incompleto» = la IN pendiente (backorder)**, que ya existe hoy. Se enlaza al contenedor nuevo
   cuando llegan las cajas que faltaban.

## 3. Tablas propias

Ningún campo nuevo en `stock.picking`, `stock.picking.type` ni `stock.move.line` (regla 7). Las relaciones van de
nuestras tablas a las de Odoo.

| Modelo | Una fila es | Campos principales |
|---|---|---|
| `koroshi.recepcion` | un contenedor marítimo que llega | matrícula (la escribe una persona: Odoo no la tiene), referencia del proveedor o BL, muelle, fecha y hora de llegada, IN de Odoo (Many2many a `stock.picking`, solo del tipo 44 y abiertas: los pedidos que trae), total de cajas del papel (a mano, opcional), estado (`pendiente` → `leyendo` → `validada` → `en_stock` / `cancelada`), quién y cuándo |
| `koroshi.recepcion.lectura` | una línea leída: lo que hay en una caja | recepción, contenedor de control (Many2one a `stock.location`), palé, cara (A/B), producto, cantidad, operario (`hr.employee`), hora, estado (`ok`, `anulada`) |
| `koroshi.recepcion.palet` | un palé de esa recepción (o del muelle) | número, cara, ubicación de Odoo (si se decide que lo sea, punto 4) |

El **teórico no se copia**: sale en cada momento de los `stock.move` pendientes de las IN enlazadas (cantidad por SKU,
punto 2). Así, si compras corrige la IN, la comparación ya lo coge. La importación del Excel de la v1 solo se
añadiría si se quiere comparar caja a caja.

Una caja con varias tallas son varias lecturas con el mismo contenedor de control. Que el mismo contenedor salga con
modelos distintos es justo lo que la fase 2 trata como «pico».

## 4. Contenedores de control y palés en Odoo

Propuesta: **los contenedores de control son `stock.location` de verdad**, como los KO_/TT_ de Contenedores. Así, al
subir al sistema, el stock queda en su contenedor, se puede buscar (Buscador de stock), hacer picking si hace falta,
y moverlo con Compactar.

- **Decidido por lo leído (punto 2): son KO_ normales** (`KO_231126_001`), como los que ya reciben hoy las IN. Se crean
  con «Recepcionar» (uno por caja; botón «+10» si salen más) con la misma regla de nombres que `koroshi_ubicaciones`
  (sigue el último NNN del día, también de los archivados). El muelle y la fecha de llegada van en nuestra tabla y en
  la etiqueta, debajo del código. Al leerlos quedan **dentro de su palé** (abajo).
- **Palé y cara (decidido por Isaac, 23/11): ubicación provisional de Odoo.** «Si un contenedor llega en 30 palés,
  tener 30 palés, cara A y cara B».
  - Cada cara es una `stock.location` interna: `PAL-01 A`, `PAL-01 B`, `PAL-02 A`… (código de barras = nombre),
    dentro de una ubicación padre de recepción (propuesta: `EFFEC/Stock/NAVE2/RECEPCION`).
  - **Son fijas y se reutilizan** de un contenedor a otro: se crean una vez en tanda (p. ej. 40 palés = 80 caras) y,
    si un contenedor necesita más, botón «+ palés». Se vacían al ubicar (fase 2).
  - Al leer una caja, el KO_ se mueve dentro de su palé y cara, como hoy un KO_ dentro de un hueco. Odoo sabe en qué
    palé está cada caja, el Buscador de stock lo enseña y Compactar ya mueve los KO_ de ahí a su sitio.
  - La pantalla de lectura dice qué palés tienen cosas de otro contenedor sin ubicar todavía, para no mezclar.
- **Quitar los contenedores de control** (fase 2): pasar su contenido a la ubicación final y archivar la ubicación
  vacía.
- Así Contenedores, Compactar y el Buscador los entienden sin tocar nada, y no hace falta un cambio en dos módulos.
  Si Isaac quiere de verdad `M1-231126-001` en el nombre, habría que tocar Contenedores (lo lleva otra sesión).
- **Etiquetas (decidido 23/11): la Zebra 4x6 del PC de Recepciones**, con el mismo formato que `koroshi_ubicaciones`
  1.0.0 (hecho el 23/11, sin instalar). Debajo del código van el muelle, la fecha y la matrícula del contenedor. Las
  etiquetas de las caras de palé salen igual, una vez, cuando se crean.
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
3. **Validar la IN** (`button_validate`), con *backorder* para lo que no ha llegado, **como ya hace hoy «Almacén
   Nath» desde la PDA** (punto 2). **Esa IN pendiente es el «shipment incompleto» que se reabre**: cuando llegan las
   cajas, se elige el contenedor nuevo, se enlaza a esa IN pendiente y se repite la lectura.

**Cuándo se valida (Isaac preguntó «¿antes de empezar o al acabar?»):**
- **Antes de empezar no hay nada que validar.** La IN ya existe (llega sola por API) y «Recepcionar» solo abre la
  lectura. Validar una IN es decirle a Odoo «estas uds ya están en el almacén», y antes de leer no se sabe cuántas son.
- **Al acabar**: botón **«Validar»**, con la comparación delante (paso 1). Pasa a stock lo leído y deja pendiente lo
  que falta. Desde ese momento el stock se ve en Odoo, en su palé y su KO_, y se puede trabajar.
- **A medias, si el contenedor es grande**: botón **«Validar lo leído hasta ahora»**. Pasa a stock lo leído y la
  lectura sigue. Es lo que se hace hoy, varias veces al día. Así no hay que esperar a acabar 700 cajas para poder
  servir algo.
- El botón solo sale al **responsable de recepciones**, no al operario que lee.

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
   el shipment incompleto = la IN pendiente).
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

**Decidido por lo leído en la BD (23/11):**
- El contenedor marítimo lo crea nuestra tabla: Odoo no tiene matrícula. Se le enlazan las IN abiertas del tipo 44.
- El teórico es por SKU, de las IN. No hay cajas en Odoo; el total de cajas, si se quiere, se escribe a mano.
- Contenedores de control = KO_ normales, como hoy.
- Shipment incompleto = la IN pendiente (backorder), como hoy.
- No se usa `shipment_management` (es de otras marcas).

**Decidido por Isaac (23/11):**
- **Validar**: al acabar, con la comparación delante. Si hace falta, «Validar lo leído hasta ahora» a medias. Botones
  solo para el responsable de recepciones (punto 5).
- **Palés**: ubicación provisional `PAL-01 A`, `PAL-01 B`… (punto 4).
- **Etiqueta de cada caja = contenedor KO_ normal** (`KO_231126_001`), con el muelle, la fecha y la matrícula escritos
  debajo. No se toca Contenedores.
- **Etiquetas**: Zebra 4x6 del PC de Recepciones.
- **Quién crea el contenedor**: el muelle, al llegar. Escribe la matrícula de la puerta y marca las IN que trae, de la
  lista de IN abiertas del tipo 44 ordenada por fecha prevista, con la referencia del proveedor y las uds. La oficina
  también puede dejarlo creado antes. **Isaac lo confirma con el almacén.**

**Pendiente antes de programar:**
1. Que el almacén confirme lo de quién crea el contenedor.
2. Cuántos palés se crean de entrada. Si nadie dice otra cosa: 40 palés (80 caras) en `EFFEC/Stock/NAVE2/RECEPCION`,
   con botón «+ palés».

**Para programar** (cuando Isaac dé la orden): módulo nuevo `koroshi_recepcion` 1.0.0, Opus en high (toca stock y
validación). Se instala solo, con `-i`. La primera prueba en real se hace con un contenedor pequeño, con permiso de
Isaac, porque crea ubicaciones y valida una IN.

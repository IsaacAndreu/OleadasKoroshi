# KOROSHI Monitor zonas (Odoo 13)

Pantalla en directo de cómo van las agrupaciones de picking por zonas (Z-ddmm-D1…D5, ZX).
Es la misma página que `bin/versiones/estado-OUT-agrupaciones-Z-*.html`, pero dentro de Odoo
y con datos al momento. **Solo lee: no cambia nada.**

En la cabecera hay un botón **Abrir mapa operativo**. Abre la acción del módulo
`koroshi_warehouse_map`; el mapa consulta las zonas internas `KOR-ddmm-*`
creadas durante el día y las pinta solo cuando existen. El monitor y el mapa
siguen siendo vistas separadas para que una pantalla sin zonas no cargue una
capa inventada ni ralentice el seguimiento.

- Menú: **Inventario › Monitor picking** (desde v1.3, al lado de KOROSHI KPI; antes en Operaciones).
- Se refresca sola cada minuto; botón **Refrescar** para hacerlo al momento.
- Desplegable con las últimas agrupaciones (Z-2210, Z-2110…). Por defecto, la última.
- Se acuerda de qué zonas has abierto o cerrado en «OUT por zona» al refrescar.
- **v1.1:** en el desplegable salen también **«Tiendas <día>»** (hoy y 2 días antes) para cuando se coge
  **una OUT por pedido** sin zonas: % hecho, **ritmo del equipo (u/h)**, **hora prevista de fin**,
  unidades leídas por hora y cada OUT con lo que ha tardado y su ritmo. Si hoy hay agrupaciones de zona
  Z-ddmm, por defecto se abre esa; si no, «Tiendas (hoy)».
- **v1.2:** en «Tiendas», **cajas cerradas** de cada OUT, **hace cuánto** se cerró la última (si una OUT
  cogiéndose pasa de 20 min sin cerrar caja sale en naranja y en un aviso arriba), **personas cogiendo ahora**
  (OUT en curso con caja cerrada en los últimos 20 min) y u por caja. Los minutos de cada OUT se estiman con
  las horas de sus cajas (Odoo solo guarda cuándo se cierra cada caja).
- **v1.3:** bloque **«Personas y horas»** en cualquier día (también días anteriores y zonas): personas (máximo a la vez
  y media), horas-persona, horas de reloj, uds por hora-persona, uds por persona y segundos por prenda. Se estima con
  las cajas cerradas cada cuarto de hora (cuántas OUT cierran caja a la vez), igual que KOROSHI KPI.
- **v1.4:** OUT **«Parcial (falta stock)»** en morado: ya se ha cogido todo lo que hay y solo faltan prendas sin stock
  (al validar van a pedido pendiente). **«Sin stock»**: OUT en espera sin nada que coger. El % y la hora de fin cuentan
  solo lo que hay en stock. Al final de la pantalla, **lista de faltantes** por OUT y artículo.





## v1.28.0: pasa a koroshi_base (16/11/2026, auditoría 13/11, fase 6)

- La empresa sale de `koroshi_base.comun` (instalar koroshi_base antes).
- La hora sigue siendo **la del usuario** (decidido el 16/11; si no tiene zona, la del almacén).
- Días del cambio de hora: el día de una Z-ddmm- y el día elegido en Tiendas sumaban 24 h fijas; ahora el día acaba
  a las 00:00 del siguiente (el 25/10, de 25 h, ya no pierde la última hora).
- Sin campos ni vistas nuevas.

## v1.27.0: permisos, caché y año de las zonas (14/11/2026, auditoría 13/11, fase 3)

- Todas las rutas (monitor y consulta de envíos) piden el permiso de **Inventario** (`stock.group_stock_user`).
- **Caché compartida**: con varias pantallas abiertas, cada una calculaba lo mismo cada minuto. Ahora se calcula una vez
  a la vez y el resultado vale **20 s** para todas (como oriola_monitor). Los datos pueden ir hasta 20 s atrasados.
- Con la **pestaña oculta** (otra pestaña, pantalla bloqueada) no pide nada; al volver, se refresca al momento.
- **Z-ddmm-** no lleva año: solo salen las agrupaciones creadas de 7 días antes a 10 días después de ese día (el
  26/10 se creó «Z-2210- SALE 26-10», 4 días después). Así, en 2027 no se mezclarán con las de 2026.

## v1.26.0: la u/h de siempre (14/11/2026, auditoría 13/11, fase 2)

- En la tabla **Operarios** (vista por día), la **u/h** es la de koroshi_operarios 2.12 (`resumen_operario_dia`): uds
  × 60 / minutos efectivos, sin los huecos de 15 min o más sin leer. Es la misma que Productividad, el correo de
  koroshi_informe y el KPI. Antes era uds / minutos con el pedido abierto (más baja si alguien paraba).
- En la vista de una agrupación sigue la cuenta de antes (solo las tareas de esa agrupación).
- Con koroshi_operarios anterior a la 2.12, como antes.

## v1.25.0: quién tiene la alarma de parado (14/11/2026)

- En la tabla **Operarios**, la fila entera en **rojo** con **«🔔 ALARMA · N min sin leer»** (parpadea) cuando a ese
  operario la PDA le está pitando: OUT abierta, en horario de la alarma y sin leer desde hace
  `koroshi_preparacion.minutos_alarma` minutos (ahora 10). Lee los mismos parámetros que la PDA
  (`minutos_alarma` y `horario_alarma`); en la pausa del café y la comida no se marca.
- Los minutos sin leer son los de Operarios (última lectura). La PDA también cuenta como actividad cerrar caja,
  poner cantidad o faltante, así que puede haber un desfase de un minuto o dos.
- Sigue el aviso de antes (más de `koroshi_operarios.minutos_sin_leer` min, en rosa).

## v1.24.0: operarios en pausa (13/11/2026)

- En la tabla **Operarios**, quien está en pausa (comer, café) sale con **«⏸ Pausa»**, su OUT y en «Desde» la hora en
  que la empezó. Necesita koroshi_operarios 2.11 o más; con versiones anteriores no sale nada.

## Instalar

1. Copiar la carpeta `koroshi_monitor` (o descomprimir `bin/koroshi_monitor_2026-10-22_0825_v1.zip`)
   en una carpeta de módulos del servidor que esté en el `addons_path`
   (la de los módulos propios, junto a `/opt/nath-erp/odoo13`).
2. Reiniciar Odoo (hace falta para que lea el controlador Python).
3. En Odoo, modo desarrollador: **Aplicaciones › Actualizar lista de aplicaciones**.
4. Buscar **KOROSHI Monitor zonas** (quitar el filtro «Aplicaciones») e **Instalar**.
5. Abrir **Inventario › Operaciones › Monitor zonas**.

Para actualizar una versión nueva: copiar encima, reiniciar Odoo y en el módulo pulsar **Actualizar**.

## Qué calcula

Para cada OUT de las agrupaciones `<prefijo>*` de la empresa 8 (EFFECTIVE LOGISTICS):

| Dato | De dónde sale |
|---|---|
| Uds | Suma de `product_uom_qty` de los movimientos no cancelados |
| Leído | Suma de `qty_done` de las líneas |
| Estado | Hecha = OUT validada · Cogiéndose = algo leído · Sin empezar = nada leído |
| Huecos | Ubicaciones distintas de las líneas (`27009 - L59 P14 C1`) |
| Lineales | `L` mínimo–máximo de esas ubicaciones; en ZX, `MU-xx` |
| Empieza / última | Primera y última línea leída (`write_date`), o la hora de validación si está hecha |
| Caja | Número de caja de tienda de la nota de la OUT («CAJA nn») |

Ficheros: `controllers/main.py` (datos, ruta `/koroshi_monitor/datos`), `static/src/js/monitor.js`
(pantalla), `static/src/css/monitor.css`, `views/menu.xml`, `views/assets.xml`.
- **v1.5:** los **pedidos pendientes en espera** (lo que faltaba al validar, sin stock) ya no salen: solo una nota con
  cuántos hay. En la lista, columna **«Sin stock»** (uds que no se pueden coger) en vez del número negativo al lado de
  «Leído». Fuera la tarjeta de «faltan» de arriba (el detalle sigue abajo del todo).
- **v1.6:** fuera la lista de **faltantes** de abajo y la columna «Sin stock»: las faltas, guardadas por día, están en
  **KOROSHI KPI › Faltas por día** (koroshi_kpi v1.3).
- **v1.7 (tiendas):** franja grande arriba (% hecho, hora de fin, uds por coger); filas con color según el estado;
  «Sin empezar» como fichas de tienda (K10 138 u…) con la lista plegada y «Hechas» plegadas. Botón **Modo pantalla**
  para la pantalla vertical del almacén: sin el menú de Odoo, letra grande y solo lo que se está cogiendo; se queda
  guardado en ese navegador (botón «Salir de pantalla» para volver). La K75 sale bien (su nombre lleva coma).
- **v1.8:** las OUT que ya tienen cogido todo lo que hay (solo faltan prendas sin stock o no encontradas), o que llevan más
  de 20 min sin cerrar caja, salen como **Hecha** con la nota «sin validar · faltan N», no como «parcial». El aviso de
  arriba lista las que faltan por validar en Odoo.
- **v1.17:** en «Tiendas» se puede filtrar por estado y transporte, buscar por tienda/OUT/pedido/etiqueta y ordenar
  con doble clic en los encabezados. Se muestran transportista y número de etiqueta. La gráfica de unidades por hora
  se desglosa por OUT con un color estable para identificar qué OUT compone cada total.
- **v1.17.1:** las OUT hechas con transportista o etiqueta aparecen con fondo azul y el monitor utiliza todo el ancho
  disponible de la pantalla.
- **v1.18:** operarios por **código** (OP1, OP2...), del módulo `koroshi_operarios` (tarjeta + OUT en la PDA). Nunca sale
  el nombre: quién es cada código lo sabe almacén. Columna «Operario» en Tiendas (también en modo pantalla), en las
  listas de cada zona y en los totales por zona; tabla «Operarios» con lo que coge ahora, pedidos, uds, minutos y u/h
  del día. En negrita quien la tiene abierta ahora; en gris quien la empezó o la dejó. El buscador también encuentra
  por código. Si `koroshi_operarios` no está instalado, el monitor sale igual que antes (no depende de él).
- **v1.18.2:** una caja que está en dos OUT (OUT pequeña metida con la PDA en la caja de otra OUT, módulo
  `koroshi_caja_existente`) cuenta como caja/bulto solo en la OUT que la usó primero. K8 del 10/11: salían 6 y son 5.
- **v1.18.1:** si la OUT o la agrupación ya está validada, el operario sale como acabado al momento (hora de
  validación), sin esperar al cron de `koroshi_operarios`, que cierra cada 5 min.
- **v1.19:** menú **«Consulta de envíos»** para oficina. Busca en todo el histórico por pedido, OUT, tienda o número
  de expedición; reúne todas las OUT del pedido; muestra transportista, **número de expedición XPO/GLS** y estado; y compara los
  **bultos declarados en Odoo** con las **cajas CJ distintas realmente preparadas**. Los botones *Copiar resumen* y
  *Compartir* dejan el texto listo para enviarlo por correo, Teams o WhatsApp. Tiene dos apartados:
  - **Tiendas:** Excel por fecha de **XPO SAS** o **GLS**, una línea por pedido. En GLS solo salen expediciones
    con etiqueta ya generada y se cuentan como máximo **5 etiquetas por pedido**; si hay más cajas, viajan juntadas.
  - **Web:** Excel por fecha de **GLS** o **SEUR** con solo estas columnas: **Fecha de transferencia**,
    **Documento origen**, **Referencia**, **Marca**, **Transportista** y **Done Quantity**. Según las muestras
    actuales, `W-000…` es SEUR y el resto de `W-…` es GLS.
  Es solo lectura: no cambia pedidos ni expediciones en Odoo.
- **v1.19.1:** en la vista de zonas, **cada OUT abierta cuenta como una persona** en «Personas y horas». Varias OUT
  abiertas dentro de la misma zona ya no se agrupan como si fueran una sola persona.
- **v1.19.2:** el botón **«Consulta envíos / Excel»** aparece dentro de la cabecera del **Monitor picking**, tanto en
  Tiendas como en Zonas, para entrar directamente a la consulta y descarga de Excel.
- **v1.19.3:** corrección del Kanban móvil de Odoo 13: carga TouchSwipe antes de abrir Inventario y evita que
  el error **«this.$el.swipe is not a function»** tape o bloquee la pantalla en una PDA. Si el plugin no está
  disponible, solo se desactiva el gesto lateral; las pestañas y el resto de Inventario continúan funcionando.
- **v1.19.4:** una OUT solo cuenta como persona mientras tenga actividad en los últimos **5 minutos**. Cada
  lectura/caja abre una ventana de cinco minutos y las ventanas consecutivas de la misma OUT se unen; los huecos
  mayores por picos o faltantes no cuentan como persona ni como horas-persona.
- **v1.19.5:** la descarga Excel de **Web** queda reducida exactamente a las seis columnas solicitadas por Betty,
  sin bultos, cajas, número de expedición ni comprobación. En el Excel de **Tiendas GLS** solo se incluyen
  expediciones con etiqueta generada y se cuentan como máximo **5 etiquetas**; las cajas adicionales se consideran
  juntadas. **XPO** mantiene el cálculo anterior.
- **v1.19.6:** botón **«← Volver al Monitor picking»** (antes salía en catalán) en la cabecera de Consulta de envíos, también adaptado para PDA.
- **v1.19.7:** tabla **Operarios**: cuando dos operarios preparan la misma OUT a la vez (koroshi_operarios v2.5 /
  koroshi_preparacion v3.4), las uds en curso de cada uno son solo las que ha leído él, no las del compañero. Sin
  esas versiones, se cuentan como antes.
- **v1.20.0:** Consulta de envíos:
  - **Excel de Tiendas por fecha de etiqueta.** Ya no va por la fecha de validación de la OUT sino por el día en
    que se generó la **etiqueta del transportista**. Al generarla, XPO y GLS dejan el PDF como adjunto de la OUT
    (`LabelXPO_<expedición>.pdf` / `gls_label_<código>.pdf`) y se usa su fecha de creación. Elegir del 11 al 11 saca
    todos los pedidos etiquetados el 11, aunque se prepararan el 9 o el 10. Una expedición cuenta el día de su
    **primera** etiqueta y arrastra todas las OUT con el mismo número (también la `-O` de outlet, que no tiene
    adjunto propio). Comprobado el 11/11/2026: las 165 expediciones desde el 05/11 tienen ese adjunto; el 11/11 XPO
    pasa de 8 pedidos (por validación) a 28 (por etiqueta), 20 de ellos preparados días antes. La primera columna se
    llama «Fecha etiqueta» y hay una columna nueva «Observación». El Excel de Web sigue por fecha de validación.
  - **Recuadro «Añadir un pedido u OUT al Excel de un día»** (en Tiendas y en Web). Se escribe el pedido
    (`S-…`, `W-…`) o la OUT (`OUT/24601`, `24601`) y el día; con un pedido se añaden todas sus OUT. Cada OUT va al
    Excel de su transportista (XPO/GLS según la OUT; en Web, `W-000…` SEUR y el resto GLS) y sale con el resto de
    ese día, con «Añadido a mano» en «Observación» (solo Tiendas; el Excel Web conserva sus seis columnas). Debajo
    se ve lo añadido en las fechas elegidas, quién y cuándo, con un botón **Quitar** por si fue un error (solo quita
    la marca; la OUT no se toca). Se guarda en el modelo nuevo `koroshi.envio.extra` (permisos para Usuario de
    Inventario).
  - Textos de la pantalla que estaban en catalán («Tendas», «Tria…», «Tornar…»), ahora en castellano.
- **v1.20.1:** «Personas y horas» en **zonas**: cada OUT es una persona **desde que empieza cada caja hasta que la
  cierra**. Entre dos cajas de la misma OUT, hasta **20 min** (`PARADA_MIN`) se sigue cogiendo y cuenta; más, es un
  pico o faltante y no cuenta. La primera caja de cada tramo empieza el tiempo típico entre cajas de ese día (mediana)
  antes de cerrarse. Con la ventana fija de 5 min (v1.19.4) se perdía el tiempo entre cajas (mediana ~7 min) y las
  u/h por persona salían infladas: Z-1111-, 167 u/h en lugar de ~114. Tiendas sigue igual.
- **v1.20.2:** «Personas cogiendo ahora» en **Tiendas (hoy)** = operarios de Lecturas con una tarea abierta (OUT,
  INT de web o agrupación) **+** OUT de tiendas cogiéndose sin operario (caja cerrada en los últimos 20 min). Cada
  persona cuenta **una vez**: si la OUT ya tiene su operario, no suma otra persona. Antes solo contaban las OUT, y el
  operario que hacía la INT de web no salía. Las u/h por persona solo cuentan a los que cogen OUT de tiendas.
- **v1.21.0 (12/11/2026):** **alarma de bloqueo**. Si un operario tiene un pedido abierto en Lecturas y lleva más de
  `koroshi_operarios.minutos_sin_leer` minutos (15 por defecto) sin leer nada, sale un aviso en rojo arriba (código,
  pedido y minutos sin leer), y su código sale en rojo en la OUT y en la tabla de operarios. Tiendas y zonas. Solo
  códigos, nunca nombres. Necesita koroshi_operarios 2.8; con una versión anterior no sale nada.
- **v1.22.0 (12/11/2026):** Consulta de envíos, apartado Tiendas: en Transportista hay una tercera opción,
  **«Todos (con y sin transportista)»**. Descarga un Excel con **todos los pedidos de tienda validados** en las fechas
  elegidas, tengan o no transportista: la columna Transportista dice XPO/GLS o **«Sin transportista»**, la primera
  columna es «Fecha validación» y al final pone cuántos pedidos van con y sin transportista. También salen los
  añadidos a mano de cualquier transportista. Los Excel de XPO SAS y GLS no cambian (siguen por fecha de etiqueta).
- **v1.23.0 (12/11/2026):** el Excel de **Tiendas** (XPO SAS, GLS y Todos) sale con **una fila por tienda** en vez
  de una por pedido, para que haya muchas menos líneas. A la izquierda: **Tienda**, **todos sus pedidos** y **todas sus
  OUT**; después fecha, transportista, nº de expedición, bultos, cajas y si coinciden, y dos columnas nuevas:
  **Uds pedidas** y **Done Quantity** (uds hechas, leídas). Las tiendas van ordenadas por número K. En GLS el máximo
  de 5 etiquetas se sigue aplicando por pedido antes de sumar la tienda. La línea TOTAL dice cuántas tiendas, pedidos y
  OUT hay. El Excel de Web no cambia.
- **v1.23.1 (12/11/2026):** Excel de Tiendas: columna nueva **«Cajas por pedido (expedición)»**, con una línea por
  pedido: «S-6665004084 (1378195458): 3 cajas». Al agrupar por tienda en la v1.23.0 se perdía cuántas cajas lleva cada
  pedido o expedición, y hace falta para el Excel de GLS.
- **v1.23.2 (12/11/2026):** Excel de Tiendas **XPO**: solo cuentan las OUT que tienen **su propia etiqueta XPO**
  (adjunto `LabelXPO_…`). Una OUT con el mismo nº de expedición pero sin etiqueta no se registró en XPO: no suma bultos
  ni cajas y sale en «Observación»: «No cuenta: OUT 24900 de S-6665004175 (1 caja) con el nº 121771203 pero sin etiqueta
  XPO». Caso K81 del 12/11: XPO 17 bultos, el Excel daba 18. GLS no cambia.

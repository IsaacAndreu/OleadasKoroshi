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
  - **Tendas:** Excel por fecha de **XPO SAS** o **GLS**, una línea por pedido. En GLS solo salen expediciones
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
  sin bultos, cajas, número de expedición ni comprobación. En el Excel de **Tendas GLS** solo se incluyen
  expediciones con etiqueta generada y se cuentan como máximo **5 etiquetas**; las cajas adicionales se consideran
  juntadas. **XPO** mantiene el cálculo anterior.
- **v1.19.6:** botón **«← Tornar al Monitor picking»** en la cabecera de Consulta de envíos, también adaptado para PDA.
- **v1.19.7:** tabla **Operarios**: cuando dos operarios preparan la misma OUT a la vez (koroshi_operarios v2.5 /
  koroshi_preparacion v3.4), las uds en curso de cada uno son solo las que ha leído él, no las del compañero. Sin
  esas versiones, se cuentan como antes.

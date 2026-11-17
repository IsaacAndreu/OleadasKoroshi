# Mejoras del Monitor picking (koroshi_monitor) — 17/11/2026

Fuente: transcript `Nueva grabación 21_4342.txt` (conversación en el almacén) + petición de Isaac del 17/11.
Versión instalada: koroshi_monitor 1.29.0. **Nada modificado**: lista para decidir.

## 1. Nombres en vez de códigos (OP1, OP2…)

- **Qué pide**: en la tabla «Operarios» y en la columna «Operario» que salga el nombre de la persona. En el
  transcript: «aquí es donde te suelta el nombre… ¿quién operaría?» y la respuesta «ahora fijaré que salga el nombre».
- **Pantallas**: Monitor picking, modo Tiendas y modo Zonas (tabla Operarios, columna Operario, matriz de zonas).
- **Dónde va**:
  - `koroshi_monitor/controllers/main.py:67` `codigo_op()`: hoy devuelve solo el código, a propósito desde la v1.18
    («En el monitor nunca sale el nombre»).
  - `controllers/main.py:370` (`cod = codigo_op(t.employee_id)`) y `:437` (pausas): ahí se añade `nombre`.
  - `static/src/js/monitor.js:57-62` (celda Operario), `:76-92` `tablaOperarios()` (encabezado «Código» en la `:78`,
    nota de la `:92`), `:208` (ordenar por operario) y `:228` (buscar: con el nombre se podría buscar por nombre).
- **Ya existe**: `resumen_operario_dia()` de koroshi_operarios (`models/tarea.py:236`) ya devuelve `nombre`; el
  nombre está en `hr.employee`. Solo hay que llevarlo hasta la pantalla.
- **Esfuerzo**: pequeño (1-2 h + versión 1.30.0).
- **Pregunta abierta**: ¿nombre en lugar del código, nombre + código («Ana · OP3») o el nombre solo para los jefes
  (grupo `koroshi_operarios.grupo_productividad`) y el código en el «Modo pantalla» de la tele del almacén?

## 2. «81 OUT hechas» que no cuadra

- **Qué pide**: Isaac ve «81 OUT hechas» y dice «hoy no hemos hecho 81 ni de broma».
- **Pantalla**: Monitor picking, modo Tiendas, franja grande de arriba (`monitor.js:602`, `T.hecha`).
- **Por qué puede salir alto** (sin confirmar con datos):
  - entran las OUT **creadas o validadas** ese día (`main.py:595-602`): una OUT de días anteriores validada hoy
    cuenta como hecha hoy («arrastrar uno del día anterior»);
  - cuentan como hechas las «hechas sin validar»: todo lo que hay cogido y faltan prendas sin stock (`main.py:332`) o
    más de 20 min sin cerrar caja (`main.py:632`).
- **Ya existe**: el KPI de «hechas sin validar» (`monitor.js:622`) separa una parte.
- **Esfuerzo**: pequeño, pero primero hay que **confirmarlo con un día real** (no se puede saber desde el código cuál
  de las dos causas es).
- **Pregunta abierta**: ¿qué día y qué pantalla era (Tiendas hoy o una Z-)? ¿Quieres que «OUT hechas» cuente solo
  las validadas ese día, o las de hoy aparte de las arrastradas?

## 3. Pestaña nueva «Producción por operario» (lo principal del transcript)

- **Qué pide**: un botón en el Monitor que abra una pestaña de producción con un desplegable de día. Por cada
  operario: qué pedidos ha hecho y cuántas uds de cada uno, y **uds por hora, hora a hora** (7-8: 80, 8-9: 100,
  9-10: 50…) para ver patrones y saber por qué una hora rinde menos. Columnas: uds, minutos/horas y u/h. «Me imagino
  los nombres, las horas y uds/hora».
- **Dónde va**:
  - ruta nueva en `controllers/main.py` (p. ej. `/koroshi_monitor/produccion`, mismo `_comprobar_grupo()` y caché);
  - pantalla nueva `static/src/js/produccion.js` (como `envios.js`, acción cliente propia) y su entrada en
    `views/assets.xml` y `views/menu.xml`;
  - botón en la cabecera junto a «Consulta envíos / Excel» (`monitor.js:318-320`).
  - Cálculo: cada tarea de koroshi_operarios (operario + OUT/agrupación + inicio/fin) y la hora de cierre de cada
    caja (como `_filas`, `main.py:208-225`) → uds por operario y franja de hora. Con «preparar a dos», cada uno solo
    lo suyo (como `_uds_hasta_ahora`).
- **Ya existe algo parecido**:
  - tabla Operarios del Monitor: uds, minutos y u/h del **día entero**, sin horas (`main.py:360-465`);
  - gráfica «uds por hora» del Monitor: por hora pero del **equipo**, desglosada por OUT, no por operario
    (`main.py:219-225`, `monitor.js:659`);
  - Inventario > KOROSHI Operarios > Productividad y el correo de koroshi_informe (diario/semanal/mensual): por
    operario y día, **sin desglose por hora**.
- **Esfuerzo**: medio (1-1,5 días). Sin campos nuevos en tablas compartidas: solo lee.
- **Preguntas abiertas**: ¿la pestaña la ven todos o solo los jefes? ¿Un día cada vez o también semana?

## 4. Descargar / correo semanal de producción por hora

- **Qué pide**: poder descargarlo y un correo semanal (también para Cruz) con «tal día, tantas horas, producción por
  hora, por operario».
- **Dónde va**: Excel en la pantalla del punto 3 (ya hay Excel en `controllers/envios.py`). El correo semanal ya
  existe en **koroshi_informe** (otro módulo): añadirle la tabla por hora sería una versión de ese módulo, no del
  Monitor.
- **Esfuerzo**: Excel pequeño (medio día); correo semanal, medio día en koroshi_informe (otra sesión/otro módulo).
- **Pregunta abierta**: ¿Excel en la pantalla basta para empezar, o el correo semanal también ya?

## 5. Más adelante: actividades que no son picking (cartón, manipulación, etiquetar/reetiquetar)

- **Qué pide**: después, ver en la producción los ratos en que no hay picking porque están tirando cartón,
  manipulando o reetiquetando. Isaac: «de momento necesito que funcione lo del operario».
- **Ya existe**: **koroshi_actividades 1.3** (tarjeta en el portátil, elige actividad, empieza/pausa/acaba).
- **Dónde iría**: una fila más por operario en la pestaña del punto 3, leyendo koroshi_actividades.
- **Esfuerzo**: medio. **Aplazado** por lo que dice el transcript.

## Lo que sale en el transcript pero NO es del Monitor picking

- Cerrar camión y enviar manifiesto a XPO con copia a Erika: **hecho** en koroshi_monitor 1.29.0 (Consulta de envíos).
- Prioridad por **documento de origen** (no por número de tienda) al repartir/preparar: es del reparto
  (koroshi_operarios / oleadas), no del Monitor.
- Backorders de pedidos con 1-3 prendas que quizá se juntan: acción 1800 v6/v6.1 (ya hecho hoy).
- Juntar un pedido en la caja de otro sin pedir tipo de caja ni validar: es de la PDA (koroshi_preparacion /
  koroshi_caja_existente).
- Pedidos que en S4T salen «ready» y no «enviado» (el «de 30», la OUT que se validó con Víctor): S4T, no Monitor.

## Orden propuesto

1. Nombres (punto 1) en cuanto Isaac elija la opción → koroshi_monitor 1.30.0.
2. Revisar «OUT hechas» (punto 2) con los datos de un día real.
3. Pestaña Producción por operario y hora (punto 3) → 1.31.0, después Excel (punto 4).
4. Correo semanal por hora (koroshi_informe) y actividades (punto 5), más adelante.

Antes de tocar `koroshi_monitor`: confirmar que ninguna otra sesión lo está tocando (la 1.29.0 la hizo hoy la sesión
de XPO/S4T) y mirar la `installed_version` del servidor.

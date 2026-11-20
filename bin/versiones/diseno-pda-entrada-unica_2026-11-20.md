# PDA: entrada única por áreas — diseño v1 (20/11/2026, sin código)

Petición de Isaac: grabación 29 del 20/11 y punto 3 de `plan-grabaciones-29-30_2026-11-20.md`.
Encaja con:
- el Tablero v6 (`diseno-tablero-responsable_2026-11-20_v6.md`): columnas por área;
- el cierre por turno (`diseno-cierre-por-turno_2026-11-20.md`).

## 1. Qué pidió Isaac

- El operario entra **una vez**: pasa la tarjeta y ve un botón por área.
  - **Recepciones** (con descargar camión).
  - **Picking** (Lecturas).
  - **Compactación** (Contenedores).
  - **Devoluciones** (la herramienta nueva del chat «Devoluciones»).
  - **Inversa**.
  - **Expediciones** (cargar camión, montar cajas).
- Al entrar en un área empieza a contar su tiempo, y se para al cambiar: se sabe qué hace cada persona en cada
  momento.
- Tareas sin lecturas (cartón, limpieza…): botón **Extra** con opciones, como en Actividades.
- **Gestión** (monitor, tablero, integración S4T, cajas escaneadas): solo para los jefes. En el almacén no se ve
  contabilidad ni informes de dinero.
- Que no se pierda la sesión enseguida. Ya está hecho: la tarjeta compartida dura 60 min.

Lo que dijo en la grabación:
- «Recepción, compactación y devoluciones no se asignan»: el operario entra en su área y ya está.
- Solo el picking se asigna, por zonas o agrupaciones, y eso va en el Tablero.

## 2. Qué hay hoy (leído en el código, 20/11)

| Pieza | Qué hace | Archivo |
|---|---|---|
| Tarjeta compartida | `{id, nombre, t}` en la memoria de la PDA, clave `koroshi_operarios_pda_<uid>`, 60 min (`koroshi_operarios.minutos_tarjeta`). La usan Lecturas, Contenedores y Faltante | `koroshi_operarios/static/src/js/operarios_pantalla.js:204`, `koroshi_contenedores/static/src/js/contenedores.js:133`, `koroshi_faltantes/static/src/js/faltantes_pantalla.js:123` |
| Tiempo de picking | `koroshi.operario.tarea`: un tramo por OUT o agrupación, con uds, minutos parados y u/h. Se cierra al validar, al dejarla, a los 15 min sin leer (2.19) o a medianoche | `koroshi_operarios/models/tarea.py` |
| Tiempo sin lecturas | `koroshi.actividad.registro`: un tramo por persona y actividad. Empezar, Pausar, Seguir y Fin, «¿Sigues?» y cierre de las 17:00. **Un índice único impide dos tramos abiertos de la misma persona** | `koroshi_actividades/models/registro.py` |
| Jornada | Vista SQL: entrada, salida, horas y pausas por persona y día, sacadas de los tramos de actividades | `koroshi_actividades/models/jornada.py` |
| Inversa | Es una actividad con «Lee matrículas» en el portátil (`koroshi.inversa.caja`) | `koroshi_actividades/models/inversa.py` |
| Compactación | Cada movimiento de contenedor guarda el operario de la tarjeta (`employee_id`) | `koroshi_contenedores/models/movimiento.py:23` |
| Recepciones | **No hay pantalla KOROSHI.** Se usa la app de código de barras de Odoo. La de packing list (tablet en el muelle) solo está diseñada | `diseno-recepciones-packing-list_2026-11-19.md` |
| Expediciones | Sin pantalla propia. Lo que va «a expediciones» (Sin caja, saltadas) vive en las colas de Lecturas. Las cajas de cartón se descuentan al cerrar caja (`koroshi_consumibles`) | — |
| Entrada de la PDA | Acción inicial de «Almacén Nath» = Lecturas. La app instalada (`koroshi_pda_app`) abre Lecturas. «Salir» de Lecturas lleva a la pantalla de inicio de Odoo, con todas las apps (2.7.0) | `koroshi_pda_app/controllers/main.py`, `koroshi_operarios/__manifest__.py` v2.7.0 |
| Menús y jefes | Grupo «KOROSHI: Jefes de almacén» (`koroshi_menu.grupo_jefes`). **«Almacén Nath» es administrador**: ve todas las apps de la pantalla de inicio | `koroshi_menu/views/menu.xml`, TABLERO (2.21.1) |
| Tablero | Estado por operario: leyendo / parado / «en el portátil» / sin tarea. `koroshi_actividades` ya lo amplía (`models/tablero.py`) | `koroshi_operarios/models/tablero_formatos.py:106-112` |

Conclusiones:
- Ya existe casi todo para contar el tiempo por área: **la tabla de tramos de Actividades**, con su «un tramo
  abierto por persona», su «¿Sigues?», su cierre y su jornada.
- Falta la puerta de entrada y decir a qué área pertenece cada tramo.

## 3. Propuesta

### 3.1 Pantalla «Inicio» en la PDA

```
┌──────────────────────────────┐
│ KOROSHI      DC · Dani C.  ⏻ │   ⏻ = Salir (olvida la tarjeta)
├──────────────────────────────┤
│ Ahora: PICKING · 1 h 12 min  │   área actual y tiempo
├──────────────┬───────────────┤
│ RECEPCIONES  │ PICKING  ●    │
├──────────────┼───────────────┤
│ COMPACTACIÓN │ DEVOLUCIONES  │
├──────────────┼───────────────┤
│ INVERSA      │ EXPEDICIONES  │
├──────────────┴───────────────┤
│ EXTRA (cartón, limpieza…)    │
├──────────────────────────────┤
│ ☕ PAUSA                     │
├──────────────────────────────┤
│ GESTIÓN (solo jefes)         │
└──────────────────────────────┘
```

- **Sin tarjeta**: pantalla completa «Pasa tu tarjeta», como Lecturas con tarjeta obligatoria.
  - Usa la misma clave de la memoria de la PDA, así que con la tarjeta pasada en Lecturas ya entra.
- **Tocar un área**:
  1. se cierra el tramo anterior (motivo «cambió de área») y se abre uno nuevo en esa área;
  2. se abre su herramienta, con el operario ya puesto:
     - Picking → Lecturas;
     - Compactación → Contenedores;
     - Devoluciones → la pantalla nueva;
     - Inversa → la lectura de matrículas.
  - Si el área aún no tiene herramienta (Recepciones, Expediciones), sale una lista de sus tareas, que se
    empiezan y paran como en Actividades. Por ejemplo:
    - Recepciones: «Descargar camión», «Recepcionar (app código de barras)»;
    - Expediciones: «Cargar camión», «Montar cajas», «Meter en caja lo de expediciones».
- **Extra**: hoja con las opciones (Cartón, Limpieza, Reubicar material…). Funciona como Actividades: tocar una es
  empezar y cambiar a otra cierra la anterior. Se cambian en Configuración, sin tocar código.
- **Pausa**: cierra el tramo (motivo «pausa»). Al volver a pasar la tarjeta, se le ofrece seguir en la misma área.
- **Salir**: cierra el tramo, olvida la tarjeta y vuelve a «Pasa tu tarjeta». No va a la pantalla de inicio de Odoo.
- **Volver al Inicio desde un área**: un botón pequeño «◀ Áreas», siempre en el mismo sitio.
  - Primera versión: lo pinta el módulo del Inicio por encima de la pantalla, sin tocar Lecturas, Contenedores ni
    Faltante.
  - Si en la PDA real tapa algo (Lecturas tiene su menú abajo), se mete dentro de cada pantalla, una versión por
    módulo.
- **Gestión**: solo sale si quien entra es jefe (pregunta 2). Abre lo que ya existe, sin código nuevo:
  - Monitor;
  - Tablero;
  - Integración S4T (matrículas, packing feed);
  - cajas escaneadas.

### 3.2 Áreas = actividades con área (sin tabla nueva de tiempos)

- Se añade un campo **«Área»** a `koroshi.actividad`. Es la tabla propia de Actividades; no se toca `stock.*` ni
  `hr.employee` (regla 7).
  - Valores: recepciones, picking, compactación, devoluciones, inversa, expediciones y extra.
- Cada área tiene **una actividad principal** (p. ej. «Picking») y, si hace falta, tareas dentro (p. ej.
  Recepciones → «Descargar camión»).
- Las actividades del portátil se reparten en áreas:
  - «Inversa» va en Inversa;
  - «Manipulación devoluciones» va en Devoluciones;
  - Marketplace, Tiendas, Web y Bolsas: pregunta 3.
- Dos campos más:
  - **«Abre»**: la acción de su herramienta, guardada como texto (`koroshi_operarios.action_koroshi_operarios_pantalla`).
    Así Actividades no depende de Contenedores ni de Devoluciones; si la acción no existe, el botón no sale.
  - **«Solo jefes»**: para Gestión.
- **Cada entrada en un área es un tramo de `koroshi.actividad.registro`**, la misma tabla del portátil. Con eso, sin
  hacer nada más:
  - una persona solo está en un sitio a la vez (el índice único ya existe);
  - la Jornada da la entrada, la salida y las horas de toda la gente, la del portátil y la de la PDA;
  - el «¿Sigues?», la pausa y el cierre (y después el cierre por turno) valen para las áreas;
  - informe nuevo «Horas por área»: tabla dinámica de los tramos agrupados por área, persona y día.

### 3.3 Picking sin duplicar las tareas

Hay dos medidas distintas que no se suman nunca:

| | Tramo de área «Picking» (Actividades) | Tarea de picking (Operarios) |
|---|---|---|
| Qué mide | Cuánto rato está la persona en picking: andar, esperar entre OUT, cambiar de caja | Cada OUT o zona: uds, minutos parados y u/h |
| Para qué | Dónde está cada uno y horas por área | Productividad (Monitor, correo, KPI) |
| Quién la abre | Entrar en Picking en el Inicio (o leer una OUT, en la fase 4) | Leer la OUT en Lecturas, como hoy |

- **No cambia nada de la productividad**: la u/h sigue saliendo de `resumen_operario_dia()`, con los mismos
  números del Monitor, el correo y el KPI.
- El tramo de área solo responde a «¿cuántas horas ha estado Dani en picking hoy?».
- La regla para los informes: **las horas por área salen solo de los tramos; las uds y la u/h, solo de las tareas**.
- Diferencia esperable: horas de picking (tramo) ≥ minutos de sus tareas. Lo que sobra es lo que pasa entre OUT y
  OUT. Es un dato útil: cuánto se pierde entre pedido y pedido.

### 3.4 Que el área no mienta («la lectura manda»), fase 4

Si alguien entra en Picking y se pone a compactar sin cambiar de área, el tiempo iría mal. Propuesta:
- **leer una OUT en Lecturas** pasa a la persona a Picking;
- **mover un contenedor** la pasa a Compactación;
- **leer una matrícula de inversa** la pasa a Inversa.

Sin pulsar nada. Cómo se haría:
- Actividades amplía la creación de la tarea de picking. Ya depende de Operarios.
- Los movimientos de contenedor se miran solo si el modelo existe, sin depender de Contenedores.
- En las áreas con lecturas, el tramo se cierra como la tarea: **a la última lectura**, a los 15 min sin leer. En
  las áreas sin lecturas se pregunta «¿Sigues?» en la PDA (pita y parpadea), como en el portátil.

### 3.5 Tablero

- Actividades ya amplía el tablero. Se le añade «área actual» por operario: el área del tramo abierto, o «Sin área».
- Con eso el Tablero v6 pinta sus columnas por área sin leer nada más.
- Las tarjetas de actividad del tablero (1.5.0) desaparecen, como dice la v6: las actividades ya no se asignan.

### 3.6 Que en la PDA no se vea contabilidad

- «Almacén Nath» es administrador: por grupos lo ve todo.
- Con el Inicio como acción inicial, sin barra de Odoo y con «Salir» que no lleva a la pantalla de inicio, desde la
  PDA ya no se llega a las demás apps. Gestión solo abre lo suyo.
- Lo de fondo, quitar el administrador a «Almacén Nath», es más seguro pero puede romper cosas que hoy funcionan por
  serlo. Es la pregunta 4.

## 4. Módulos y orden (uno por sesión, uno detrás de otro)

| Fase | Módulo | Qué | Nota |
|---|---|---|---|
| 1 | `koroshi_actividades` 1.6.0 | Campo Área, «Abre» y «Solo jefes» en `koroshi.actividad`. Datos de las 6 áreas y las Extra (noupdate; ojo: los `<function>` noupdate no corren al actualizar, así que van como `<record>`). Pantalla «Inicio (PDA)» (acción cliente nueva) con tarjeta compartida, áreas, Extra, Pausa, Salir y el «◀ Áreas» flotante. Ruta para entrar en un área. Informe «Horas por área» | El grueso. Tablas propias. **Antes**, ver si la sesión del cierre por turno va a tocar Actividades: se hacen una detrás de otra |
| 2 | `koroshi_pda_app` 1.2.0 | La app instalada abre el Inicio, no Lecturas | Pequeña |
| — | (a mano, Isaac) | Acción inicial de «Almacén Nath» = Inicio (PDA). Se deshace volviendo a poner «Operarios» | Sin versión: es un dato de usuario |
| 3 | `koroshi_operarios` 2.23.0 | «Salir» de Lecturas vuelve al Inicio, no a la pantalla de inicio de Odoo. Si el «◀ Áreas» flotante tapa algo en Lecturas, se mete en su cabecera | Coordinar con el Tablero y con el cierre por turno, que también tocan Operarios |
| 4 | `koroshi_actividades` 1.7.0 | «La lectura manda» y cierre del área por inactividad. «Área actual» para el Tablero | |
| 5 | `koroshi_operarios` (Tablero v6) | Columnas por área | Lo hace la sesión del Tablero |
| 6 | Herramienta de Devoluciones | Rellena «Abre» del área Devoluciones con su acción y coge el operario de la tarjeta compartida | Lo hace la sesión de Devoluciones; aquí no hay código |
| 7 | `koroshi_contenedores`, `koroshi_faltantes` | Solo si el «◀ Áreas» flotante no sirve: meterlo en su pantalla | Opcional |

- `koroshi_menu` (la 2.6.2 la lleva otro chat) **no se toca**: Gestión abre acciones que ya existen.
- Instalación: una versión cada vez, y primero Actividades (la PDA sigue entrando en Lecturas hasta la fase 2 y el
  cambio de acción inicial).
- Para probar sin molestar: el Inicio se abre a mano desde su menú con «Departament IT» antes de cambiar la acción
  inicial de «Almacén Nath».

## 5. Riesgos

- **Tocar Actividades** toca el portátil de manipulaciones.
  - El Inicio es una pantalla nueva y el portátil sigue igual.
  - Lo que hay que probar es que el índice «un tramo abierto» no choque: una persona abierta en el portátil que
    entra en un área de la PDA cierra lo del portátil. Es lo correcto, pero hay que avisar.
- **Un botón flotante por encima de Lecturas** puede tapar algo. Probar en una PDA real antes de cambiar la acción
  inicial.
- **Dos medidas de picking** (tramo y tarea): si alguien las suma en un informe, sale el doble. Queda escrito en el
  código y en el informe.
- **Recarga de las PDA tras actualizar**: Lecturas se recarga sola (2.15), el Inicio no. Hay que hacer Ctrl+F5 la
  primera vez o copiarle la misma recarga.

## 6. Preguntas para Isaac

1. **Áreas y orden de los botones**: ¿Recepciones, Picking, Compactación, Devoluciones, Inversa y Expediciones, más
   Extra? ¿Falta alguna, como «Reubicar material»?
2. **Gestión, ¿cómo se sabe que es un jefe?** En la PDA todos entran con «Almacén Nath», así que:
   - (A, recomendada) por la **tarjeta**: una lista de operarios jefes en Configuración. El jefe pasa su tarjeta en
     cualquier PDA y le sale Gestión.
   - (B) solo con su **usuario de Odoo** (Almacen 2…): en las PDA de «Almacén Nath» Gestión no sale nunca.
3. **Actividades del portátil de manipulaciones** (Marketplace, Tiendas, Web, Bolsas y etiquetas), ¿en qué área van?
   ¿En Expediciones, en Devoluciones o en una «Manipulación» aparte?
4. **Quitar el administrador a «Almacén Nath»**: ¿lo hablamos aparte? (recomendado: sí, más adelante y con prueba)
   ¿O basta con que la PDA no llegue a la pantalla de inicio?
5. **«La lectura manda»** (fase 4): ¿leer una OUT o mover un contenedor cambia el área sola? (recomendado: sí)

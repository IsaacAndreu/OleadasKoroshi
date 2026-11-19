# Tablero del responsable: repartir tareas entre operarios (diseño, 19/11/2026, sin código)

Petición (grabaciones del 19/11, sección 3 de `notas-grabaciones-recepciones-y-tareas_2026-11-19.md`): por la mañana
el responsable reparte zonas o tareas entre operarios en **una columna por operario**. Las tareas se arrastran y se
hacen de arriba abajo. Al validar un pedido, la PDA saca sola la siguiente. Se puede mandar a alguien que está a punto
de acabar a reforzar otra zona. Tiene que haber una barra de progreso.

Este documento es solo diseño. No se escribe código hasta que Isaac lo apruebe.

---

## 1. Qué hay hoy (leído en el repo el 19/11)

**La cola por operario ya existe.** Está en `koroshi_operarios`: el tablero tiene que ser otra forma de verla, no una
cola nueva.

| Pieza | Dónde | Qué hace ya |
|---|---|---|
| Cola por operario | `koroshi.operario.asignacion` (`koroshi_operarios/models/reparto.py:253`) | Una fila por pedido (`tipo` = `out`) o por agrupación (`tipo` = `agrupacion`, cualquier `stock.picking.batch`: Z-, WEB_…). Tiene `employee_id`, `secuencia` (orden), `estado` (cola / curso / oficina / hecha / quitada), `origen` (manual / auto / pasillos / leida) y `ayudante_id`. |
| Siguiente al validar | `siguiente()` (`reparto.py:624`) + `operarios_pantalla.js:332` («¡Hecho!» y la siguiente en 3 s) | Lo primero es la tarea que ya está en curso. Después, la de ayudante que le hayan puesto. Después, su cola por `secuencia`. Si la cola está vacía, `_dar_nueva` le da una según el modo del día, solo si está encendido «darle otra solo». |
| Reparto del día | `koroshi.operario.dia` (`reparto.py:75`) | Modo A automático, B por pasillos (con un tramo de lineales por operario) o C solo manual. «Repartir ahora» manda bloques de N pedidos. Se imprimen las etiquetas por persona. |
| Asignar a mano | `wizard/asignar.py` (Acción > Asignar a operario, en albaranes y en agrupaciones) | Pone OUT o agrupaciones en la cola de alguien. Ya admite cualquier agrupación. |
| Subir / Quitar / Liberar | `action_subir`, `action_quitar`, `action_liberar` (`reparto.py:820-838`) | «Subir» la pone la primera de la cola. «Quitar» la saca de la cola y, si estaba en curso, cierra la tarea como dejada. |
| Preparar a dos | `ayudante_de`, `unirse` (`reparto.py:770-818`) | Solo para **OUT sueltas**: el ayudante empieza por el final. En agrupaciones no se puede: si alguien la está haciendo, sale «X la está haciendo» (`reparto.py:731-749`). |
| Zonas D1, D2, MU1, MU2 | `koroshi_zonas` + cron 202 / acción 1883 | Agrupaciones `Z-ddmm-D1`, `Z-ddmm-MU2` y, en la segunda ronda, `Z-ddmm-R2-…`. Las crea el cron, no el responsable. Preparación en Lecturas las recorre enteras (`koroshi_preparacion/models/agrupacion.py`). |
| Agrupaciones web | `koroshi_agrupaciones_web` | `WEB_ddmmyy_NN`, creadas en cada corte (06:00 y 11:00). Son `stock.picking.batch` normales. |
| Manipular | `koroshi_actividades` | Tiempo por persona y actividad en el **portátil** (Manipulación marketplace, Tiendas, Web, Devoluciones, Inversa, Bolsas). Va aparte de la PDA y de la cola. Depende de `koroshi_operarios`, no al revés. |
| Monitor | `koroshi_monitor` | Producción por operario (u/h, parado, en pausa con `asignacion.en_pausa()`). Hoy no enseña las colas. |
| Cierre por inactividad | `koroshi_operarios` 2.19.0 | Cierra la tarea a los 15 min sin actividad. La asignación sigue siendo del operario. |

**Conclusión.** Tres de las cinco cosas que pide ya funcionan:

- la cola por operario de arriba abajo;
- la siguiente al validar;
- asignar zonas y agrupaciones con nombre.

Lo que falta:

1. **La vista de columnas con arrastre.** Hoy la cola es una lista (Colas) dentro de «Reparto de hoy».
2. **Tareas que no son un pedido**, como manipular.
3. **Zonas que aún no existen** por la mañana: D1 se crea cuando corre el cron.
4. **Dos personas en la misma zona** (reforzar D2 mientras otro la hace).
5. **La barra de progreso.**

---

## 2. Propuesta

### 2.1 El tablero es una vista kanban de `koroshi.operario.asignacion`

- **Una columna por operario**: kanban agrupado por `employee_id`.
  - Con `group_expand` salen también los operarios de hoy que aún no tienen nada; se toman de «Operarios de hoy» (`tramo_ids`).
  - Hay una columna «Sin asignar» con lo que está en expediciones o libre.
- **Tarjeta** = una asignación. Lleva:
  - un icono por tipo (OUT, zona, agrupación, actividad);
  - el nombre (`Z-1911-D2`, `WEB_191126_01`, `S-6665…`, «Manipular devoluciones»);
  - tienda y uds;
  - su barrita de progreso;
  - el estado por color: gris en cola, azul haciéndose, verde hecha hoy.
- **Qué se puede hacer**:
  - Arrastrar dentro de la columna cambia el orden (`secuencia`).
  - Arrastrar a otra columna cambia de operario.
  - Botones en la tarjeta: Subir, Quitar, Ayudante (los de hoy).
- **Reglas al mover** (en el servidor, no solo en la pantalla):
  - Solo se mueven las tarjetas **en cola**.
  - Una tarjeta en curso no cambia de operario arrastrándola: sale «X la está haciendo; usa Quitar». Así nadie pierde el pedido a medias sin enterarse.
  - Al cambiar de columna, la tarjeta va al final de la cola nueva, salvo que se suelte en otro sitio.
- **Barra de la columna**: la nativa del kanban de Odoo 13 (`<progressbar field="estado">`), con hechas, haciéndose y en cola.
  - Para eso las tarjetas **hechas hoy** se quedan en el tablero (filtro: `estado = hecha` y `write_date` de hoy).
  - Encima, el total de la columna: uds leídas / uds pedidas.
- **Barra de la tarjeta** (pedido o agrupación): uds leídas / uds pedidas.
  - Usa `_uds_leidas` y `_uds_pedidas`, que ya existen (`tarea.py:288-302`).
  - Se calcula de golpe para todo el tablero en una sola consulta, no tarjeta a tarjeta.
- **Por qué no una pantalla JS propia**: el kanban de Odoo ya hace el arrastre, las columnas y la barra. Es poco código y
  se rompe poco. Una pantalla propia solo haría falta si el tablero se usa en una tablet (ver riesgo R3).

### 2.2 Tipos de tarjeta nuevos

| Tarjeta | Cómo se guarda | Qué hace la PDA cuando le toca |
|---|---|---|
| OUT, agrupación Z- o WEB_ ya creada | Como hoy (`tipo` = `out` / `agrupacion`) | Lo de hoy: la abre (Preparación en Lecturas o la app de código de barras). |
| **Zona que aún no existe** («D1», «MU2») | `tipo` = `zona` + `zona_codigo` (D1…) | Al llegarle el turno, busca la agrupación viva de hoy que acaba en `-D1` y no tiene otro dueño. La tarjeta pasa a `agrupacion` con ese `batch_id` y se abre como hoy. Si aún no existe, la PDA dice «La zona D1 aún no está creada. Pide a tu responsable» y no se salta la tarjeta. |
| **Actividad** (manipular…) | `tipo` = `actividad` + `actividad_id` (`koroshi.actividad`) | Pantalla «Ahora: Manipulación devoluciones. Ve al portátil de Actividades y pasa tu tarjeta», con el botón «Hecho, siguiente». No abre ningún pedido ni cuenta uds; el tiempo sale de `koroshi_actividades`, como hoy. |
| **Nota libre** (opcional) | `tipo` = `nota` + `nota` | Igual que la actividad, con el texto del responsable («Ayuda a descargar el camión»). |

En `siguiente()` cambian dos cosas: resolver la zona y no abrir nada si la tarjeta es una actividad o una nota.
Los caminos de `out` y `agrupacion` **no cambian**.

### 2.3 Reforzar una zona («ahora ve a reforzar D2»)

Hay dos casos.

- **D2 aún no la ha empezado nadie, o el que la tiene va por la mitad de su cola**: se arrastra la tarjeta D2 (o
  las que le quedan al lento) a la columna del que está a punto de acabar, arriba del todo. Al validar lo que tiene,
  su PDA abre D2. **Esto sale en la fase 1, sin tocar la preparación.**
- **D2 la está haciendo ya otra persona** y se quiere que dos la acaben a la vez: hoy no se puede (salta «X la está
  haciendo»). Hay dos opciones; las dos tocan `koroshi_preparacion`, el módulo más delicado de la PDA:
  - **A. Ayudante en agrupación**, como el «preparar a dos» de las OUT: el segundo recorre la misma Z- desde el final
    de la ruta. Reutiliza lo que ya funciona en OUT, pero dos PDA escriben en las mismas líneas de la misma
    agrupación. Hay riesgo de «could not serialize» y de que uno valide una OUT que el otro aún llena.
  - **B. Partir la zona**: las OUT de la Z- que nadie ha tocado (sin `qty_done`) pasan a la cola del segundo como
    OUT sueltas, y la pantalla del primero deja de enseñarlas. Cada OUT tiene un solo dueño, así que hay menos riesgo
    con el stock. Pero cambia el recorrido del primero a medias.
  - **Recomendación**: B, en una fase 2 aparte, con su propio diseño junto con quien lleve `koroshi_preparacion`.
    Antes, ver con datos reales (sin tocarlos) cuántas veces pasa.

### 2.4 Qué módulo lo lleva

- **`koroshi_operarios` 2.20.0**: la vista kanban, `group_expand`, las reglas al mover, el tipo `zona`, las barras,
  el hueco genérico para «tarea sin pedido» en `siguiente()`, y la pantalla de Lecturas que la enseña.
  - La cola, la PDA y `siguiente()` ya están aquí. Ponerlo en otro módulo partiría la lógica de la PDA en dos sitios.
  - Menú: Inventario > KOROSHI Operarios > **Tablero de hoy**, con el mismo grupo que Reparto de hoy.
- **`koroshi_actividades` 1.4.0**: el tipo `actividad` (`selection_add` en `tipo` + `actividad_id`) y el texto de la
  pantalla. Tiene que ir aquí porque `koroshi_actividades` depende de `koroshi_operarios` y no al revés.
- **`koroshi_monitor`** (fase 3, opcional): el tablero en la tele en modo solo lectura. Lo lleva la sesión del monitor
  cuando se instale su 1.36.0.
- **`koroshi_zonas` y `koroshi_agrupaciones_web`: no se tocan.** El tablero solo lee sus agrupaciones por nombre.
- **Campos nuevos**, todos en la tabla propia `koroshi.operario.asignacion`, **ninguno en `stock.*`** (regla 7):
  - en `tipo`, los valores `zona` y `nota`; `actividad` va en `koroshi_actividades`;
  - `zona_codigo` (Char);
  - `actividad_id` (en `koroshi_actividades`);
  - quizá un `sequence` como alias de `secuencia`: el arrastre del kanban de Odoo 13 reordena con el campo
    `sequence`. **Hay que comprobarlo en el código de Odoo del servidor antes de escribir nada.**

---

## 3. Qué cambia en la PDA

- **No cambia nada mientras el responsable no use los tipos nuevos.** Los caminos de OUT y agrupación son los de hoy.
- **La cola de Lecturas** enseña el tipo de cada tarjeta: «Zona D2», «WEB_191126_01», «Manipular devoluciones».
- **Pantalla nueva «tarea sin pedido»** para las actividades y las notas: texto grande y el botón «Hecho, siguiente».
  - Tiene el mismo aspecto que Lecturas («etiqueta de estantería»).
  - Con `role="presentation"`, no `aria-hidden`.
- **Zona aún sin crear**: aviso naranja «La zona D1 aún no está creada». La PDA vuelve a probar cuando el operario
  lee su tarjeta o pulsa «Probar otra vez».
- **Cambio de planes con la OUT a medias**: nada salta. El cambio del responsable se nota al validar o al volver a
  Lecturas: «¡Hecho!» enseña la siguiente nueva. Opcional: aviso «Tu responsable ha cambiado tu siguiente tarea:
  Zona D2» en la pantalla de «¡Hecho!».
- **Recarga**: las PDA se recargan solas tras actualizar (`koroshi_operarios` 2.15). La primera vez, Ctrl+F5.

---

## 4. Riesgos

- **R1. `siguiente()` es el camino por el que pasa cada pedido en todas las PDA.** Si falla ahí, el almacén se para.
  - Los tipos nuevos se tratan antes y aparte.
  - Si la zona no se puede resolver, aviso y no error.
  - Hay que probarlo en una PDA real con una OUT de prueba, sin validar (pruebas reversibles).
- **R2. Mover a la vez.** El responsable arrastra mientras una PDA pide la siguiente: las dos escriben en la misma
  asignación.
  - La tabla es pequeña y el choque dura poco, pero un «could not serialize» al validar se notaría.
  - Al mover se comprueba en el servidor que la tarjeta sigue en cola. Si no, sale el aviso y el tablero se recarga.
- **R3. Tablet o móvil.** El arrastre del kanban de Odoo 13 (jQuery UI) **no funciona con el dedo**.
  - Si el responsable lo quiere en una tablet o en la PDA, hace falta otra forma de mover:
    - botones «Subir / Bajar / Pasar a…» en la tarjeta (barato);
    - o una pantalla JS propia (caro).
  - En el PC, el arrastre va bien.
- **R4. Modo del día.**
  - Con el modo A o B, cuando una columna se vacía, la PDA da sola la OUT más antigua si «darle otra solo» está
    encendido.
  - Si el responsable quiere que **solo** salga lo del tablero, el modo tiene que ser C.
  - Hay que decidir qué es lo normal (pregunta P3).
- **R5. Zonas por nombre.** La tarjeta «D1» depende del nombre `Z-ddmm-[R2-]D1` que da la 1883 o `koroshi_zonas`.
  Si la 1.6.0 de zonas o un cambio de la 1883 lo cambian, la tarjeta no la encuentra. Antes de escribir el código,
  confirmarlo con la sesión de zonas.
- **R6. Agrupaciones WEB_.** Preparación en Lecturas solo recorre enteras las Z- (`koroshi_preparacion`, manifest
  línea 11). Una WEB_ asignada entera se abre en la app de código de barras, como la abre hoy «Asignar a operario».
  Hay que confirmar que así es como las preparan hoy.
- **R7. Coordinación.**
  - `koroshi_operarios` 2.19.0 lo vigila la sesión «Cierre por inactividad».
  - La fila «Alarma PDA» del TABLERO tiene operarios/preparación con «?».
  - Antes de tocar operarios hay que avisarlas y pedir la `installed_version` real (regla 3).
- **R8. Instalar.** Actualizar operarios saca las sesiones unos minutos, y no se puede a la vez que otra
  actualización. Hay que instalarlo fuera de horas punta y uno a uno (después de zonas 1.6.0 y monitor 1.36.0, que
  esperan).
- **R9. Rendimiento del tablero.** Con unos 10 operarios y unas 10 tarjetas cada uno (muchas Z- de unas 20 OUT), las
  uds leídas por tarjeta tienen que salir de una sola consulta. Si no, el tablero tarda.

---

## 5. Fases propuestas

1. **Fase 1** (`koroshi_operarios` 2.20.0):
   - tablero kanban con arrastre en el PC y barras;
   - tarjetas de zona («D1») y de nota;
   - reglas al mover;
   - cola de Lecturas con el tipo de cada tarjeta;
   - pantalla «tarea sin pedido».
   - Así ya se puede repartir por la mañana y mandar a reforzar moviendo tarjetas sin empezar.
2. **Fase 1b** (`koroshi_actividades` 1.4.0): tarjetas de actividad (manipular…), con la pantalla de la fase 1.
3. **Fase 2** (diseño aparte, con `koroshi_preparacion`): dos personas en la misma zona ya empezada (opción B, partir).
4. **Fase 3** (`koroshi_monitor`, opcional): el tablero en la tele, solo lectura.

---

## 6. Preguntas para Isaac

- **P1.** ¿Dónde lo usará el responsable: PC, tablet o PDA? Si es una tablet o la PDA, el arrastre nativo no sirve
  (R3) y hay que poner botones o hacer una pantalla propia.
- **P2.** «Zona 1, zona 2»: ¿son las D1 y D2 de la primera ronda, o cualquier `-D1` del día (también la R2)? ¿A qué
  hora están creadas las Z- por la mañana?
- **P3.** Cuando a alguien se le acaba la columna, ¿qué hace la PDA?
  - «Pide a tu responsable» (modo C).
  - O le da sola la siguiente libre (modo A o B, como hoy si está encendido).
- **P4.** Las tarjetas de manipular: ¿se acaban con «Hecho, siguiente» en la PDA? ¿O cuando la persona pasa su
  tarjeta en el portátil de Actividades? Lo segundo enlaza los dos módulos y es más trabajo.
- **P5.** Reforzar una zona que otro **ya está haciendo**: ¿pasa a menudo? ¿Basta con la fase 1 (mover lo que aún no ha
  empezado nadie)? La fase 2 toca la preparación y es la parte con más riesgo.
- **P6.** ¿Quién más puede mover tarjetas: solo los responsables o también la oficina (expediciones)? ¿Mismo grupo que
  «Reparto de hoy»?
- **P7.** ¿Hace falta guardar un plan de un día para otro? Por ejemplo, «lunes: Diana D1 y D2, Sheyla MU…». Con
  «copiar el reparto de ayer» (lo que ya hace `de_hoy`) también se podrían copiar las tarjetas de zona y de actividad.
- **P8.** Las tarjetas hechas: ¿se quedan en verde todo el día en su columna (así sale la barra), o desaparecen?

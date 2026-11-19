# Tablero del responsable: repartir tareas entre operarios (diseño v4, 19/11/2026, sin código)

**v4** (sale de la v3, que no se toca). Recoge la tercera tanda de respuestas de Isaac (19/11):

- **Por la mañana el tablero sale vacío**: no se copia nada de ayer. A un lado están las **piezas por repartir**:
  las zonas y las agrupaciones de hoy, las OUT libres y una etiqueta por cada actividad. Almacén 2 las arrastra a la
  columna de cada operario, y a ese operario le salen en su PDA.
- **«Validar cosas» y lo de S4T para Almacén 2 lo lleva otro chat.** Sale de este diseño: el punto 6 queda solo como
  nota y se quitan P8 y P9.

**v3** (sale de la v2, que no se toca). Recoge la segunda tanda de respuestas de Isaac (19/11):

- **Orden de las OUT dentro de una zona**: lo decide `koroshi_zonas`, no el tablero. El tablero las da en el orden que
  deje zonas (la 1.6.0 las ordena por número de pedido) y no inventa uno propio. Hay que confirmarlo con la sesión de
  zonas antes de escribir el código.
- **Manipular se acaba cuando la persona pulsa «Fin»** en la pantalla de Actividades del portátil. No hay botón en la
  PDA.
- **Solo Almacén 2 asigna trabajo.** Nadie más mueve tarjetas.
- La pregunta del «tablero de ayer» estaba mal planteada. Va reescrita en P7.
- «Validar cosas» lo dijo Isaac en su mensaje anterior. Ahora se le pregunta qué quería decir (P8).

**v2** (sale de `diseno-tablero-responsable_2026-11-19.md`, que no se toca). Recoge lo que contestó Isaac el 19/11:

- El tablero **solo lo ve Almacén 2** (almacen2@nath.es, la cuenta de los jefes). Almacén Nath (las PDA) no lo ve.
  Sirve para mandar trabajo sin que nadie tenga que ir dando gritos.
- **Se usa en el PC**: vale el arrastre del kanban de Odoo.
- **Columna vacía = la siguiente OUT libre**, como el modo automático de hoy con «darle otra solo» encendido.
- **En una zona trabajan 4 o 5 personas a la vez, y cada una lee OUT a OUT.** La zona entera (leer la Z-) no se usa.
  Se deja como está, pero el tablero no la usa.
- **Almacén 2 tampoco ve lo de S4T ni puede validar.** Va en el punto 6.

Este documento es solo diseño. No se escribe código hasta que Isaac lo apruebe.

---

## 1. Qué hay hoy (leído en el repo el 19/11)

La cola por operario ya existe en `koroshi_operarios` (`koroshi.operario.asignacion`,
`models/reparto.py:253`):

- Una fila por OUT o por agrupación, con operario, orden (`secuencia`) y estado (cola / curso / oficina / hecha /
  quitada).
- `siguiente()` (`reparto.py:624`): lo que está en curso; si no, lo de ayudante; si no, su cola; si no, la siguiente
  libre según el modo del día (`_dar_nueva`, con `_candidatos` en `reparto.py:424`).
- Al validar, la PDA enseña «¡Hecho!» y abre la siguiente a los 3 s (`operarios_pantalla.js:332`).
- Leer una OUT de una zona abre **solo esa OUT** (v2.9). Así es como trabajan hoy.
- `_candidatos` **deja fuera las OUT de las Z-** (`reparto.py:432-436`). Hoy el automático solo da OUT sueltas, y la
  OUT de zona la coge el operario leyéndola.

Otros módulos que intervienen:

- `koroshi_zonas` y la acción 1883 crean `Z-ddmm-D1`, …, `Z-ddmm-MU2` y, en la segunda ronda, `Z-ddmm-R2-…`.
- `koroshi_agrupaciones_web` crea `WEB_ddmmyy_NN`.
- `koroshi_actividades` lleva la manipulación en el portátil.
- `koroshi_menu` 2.4.1 ya tiene un grupo con solo Almacén 2: «Bandeja del encargado en Aplicaciones», con su icono en
  Aplicaciones.

---

## 2. La idea: tarjetas de «origen de trabajo»

Una tarjeta no tiene por qué ser un pedido. Puede decir **de dónde salen sus siguientes OUT**:

| Tarjeta | Qué le da la PDA, una OUT detrás de otra |
|---|---|
| **Zona** («D2», «MU1») | La siguiente OUT libre de las Z- vivas de hoy que acaban en `-D2` (también las de la R2). |
| **Agrupación con nombre** (`WEB_191126_01` o cualquier otra) | La siguiente OUT libre de esa agrupación. |
| **OUT concreta** | Esa OUT, como hoy. |
| **Actividad** (manipular…) | Pantalla «Ahora: Manipulación devoluciones. Ve al portátil de Actividades». **Se acaba cuando la persona pulsa «Fin» en el portátil**. Después, la PDA pasa sola a la siguiente tarjeta. |
| **Nota** | Texto del responsable («Ayuda a descargar el camión»), con «Hecho, siguiente». |

**Cuatro o cinco operarios pueden tener la misma zona.** Cada uno se lleva OUT distintas.

- Cada OUT dada crea su asignación, igual que hoy. Una OUT que ya tiene otro no se da (lo mismo que hace hoy
  `_candidatos`).
- **Orden dentro de la zona**: el que deje `koroshi_zonas` (en la 1.6.0, por número de pedido). El tablero no decide
  el orden.
- **La tarjeta de zona sigue «haciéndose»** mientras queden OUT libres en la zona.
- **Cuando la zona no tiene más OUT libres**, la tarjeta pasa a hecha y la PDA va a la siguiente tarjeta de su columna.
  Si la columna está vacía, le da la siguiente OUT libre de cualquier sitio, como el automático de hoy.
- **Mandar a reforzar D2**: se arrastra (o se copia) la tarjeta D2 a lo alto de la columna del que está a punto de
  acabar. Cuando valide la OUT que tiene entre manos, su PDA le abre la siguiente OUT libre de D2. **No interrumpe la OUT
  que esté haciendo.**
- **No hace falta tocar `koroshi_preparacion`.** Cada OUT la hace una sola persona, como hoy. La fase 2 de la v1 (dos
  personas en la misma agrupación) desaparece.

---

## 3. El tablero (solo Almacén 2, en el PC)

- **Icono propio «Tablero»** en Aplicaciones. Solo lo ve el grupo nuevo «KOROSHI: Tablero del responsable»:
  - al instalar entra Almacén 2, como ya se hace con la Bandeja;
  - para dárselo a otro: Ajustes › Usuarios.
  - **Almacén Nath no entra**: no cambia ningún menú de las PDA.
- **Vista kanban** de `koroshi.operario.asignacion`, con una columna por operario:
  - salen los operarios activos con tarjeta, aunque no tengan nada (`group_expand`);
  - se pueden ocultar los que hoy no vienen.
- **Por la mañana sale vacío.** Las tarjetas de días anteriores no se ven: las hechas se quedan en el historial, y lo
  que quedó en cola se puede ver con un filtro.
- **Primera columna, «Por repartir»**: las piezas de hoy, que se calculan solas cada vez que se abre el tablero.
  - **Zonas**: una pieza por zona viva de hoy (D1, D2…, MU1, MU2), con cuántas OUT libres le quedan.
  - **Agrupaciones con nombre** de hoy (`WEB_…` u otras), con sus OUT libres.
  - **OUT libres** sueltas (las que hoy daría el automático), las más antiguas primero.
  - **Actividades**: una etiqueta por cada actividad activa de `koroshi_actividades` («Manipulación marketplace»,
    «Tiendas», «Devoluciones»…), más una «Nota» en blanco.
- **Qué se puede hacer**:
  - **Arrastrar una pieza** de «Por repartir» a la columna de un operario, en el puesto que se quiera.
    - Las zonas, las agrupaciones y las actividades **se quedan también en «Por repartir»**, para poder dárselas a
      4 o 5 personas.
    - Una OUT suelta, al dársela a alguien, sale de «Por repartir».
  - **Arrastrar dentro de una columna** para cambiar el orden. **Arrastrar a otra columna** para cambiar de operario.
  - **Volver a dejarla en «Por repartir»** = quitársela, como el «Quitar» de hoy.
  - **Comprobar en el Odoo del servidor**: el kanban de Odoo 13 mueve tarjetas, no las copia. Al soltar una pieza que
    se queda, el servidor crea la tarjeta del operario, deja la pieza donde estaba y el tablero se recarga. Si el
    kanban no lo permite así, la pieza se da con un botón «Dar a…» y una lista de operarios.
- **Reglas al mover** (las comprueba el servidor):
  - solo se arrastran las tarjetas en cola;
  - una tarjeta que alguien está haciendo no cambia de dueño arrastrándola (sale «X la está haciendo; usa Quitar»).
- **Cómo se ve una tarjeta**:
  - icono por tipo;
  - nombre;
  - las personas que también están en esa zona;
  - color por estado: gris en cola, azul haciéndose, verde hecha hoy.
- **Barras de progreso**:
  - **Tarjeta de zona o agrupación**: OUT validadas / OUT de la zona y uds leídas / uds pedidas, entre todos los que
    están en ella.
  - **Columna**: la barra nativa del kanban (hechas / haciéndose / en cola) y las uds del operario hoy, con la misma
    cifra que Productividad (`resumen_operario_dia()`).
  - **Arriba del todo**: el total del día por zona (OUT validadas / OUT), para ver qué zona va atrasada y a quién
    mover.
  - Todo se calcula en una sola consulta por pantalla. El tablero se refresca solo cada 30-60 s.

---

## 4. Qué cambia en la PDA (Almacén Nath)

- **Si el responsable no pone tarjetas, nada cambia**: OUT sueltas, OUT de zona leídas a mano y el automático
  funcionan como hoy.
- **Con tarjeta de zona o de agrupación**: al validar (o al entrar en Lecturas), «¡Hecho!» enseña la siguiente OUT de
  esa zona, por ejemplo «Siguiente: S-6665004410 · K34 · Zona D2», y la abre a los 3 s.
  - La abre en Preparación en Lecturas, como cuando se lee la OUT a mano.
  - Las etiquetas de zona ya están impresas, así que no hay que imprimir nada.
- **Cola de Lecturas**: enseña las tarjetas («Zona D2 · quedan 14 OUT», «Manipular devoluciones»).
- **Pantalla nueva «tarea sin pedido»** para las actividades y las notas:
  - texto grande;
  - en una nota, el botón «Hecho, siguiente»;
  - en una actividad, ningún botón: espera a que la persona pulse «Fin» en el portátil, y la pantalla lo comprueba al
    consultar `/estado`;
  - mismo aspecto que Lecturas;
  - con `role="presentation"`, no `aria-hidden`.
- **Si leen una OUT a mano** (de otra zona), se respeta, como hoy. Al validarla, sigue con su tarjeta.
- **Zona que todavía no existe** (la 1883 aún no ha partido): la tarjeta se salta y se usa la siguiente o la OUT libre,
  y la tarjeta se vuelve a mirar en el siguiente pedido. No se queda la PDA parada esperando.

---

## 5. Qué módulo lo lleva

- **`koroshi_operarios` 2.20.0**:
  - tipos de tarjeta `zona`, `agrupacion_out` (agrupación OUT a OUT) y `nota`;
  - candidatos de zona en `siguiente()`;
  - la vista kanban y las reglas al mover;
  - las barras;
  - la pantalla «tarea sin pedido» de Lecturas;
  - el grupo y el icono «Tablero».
- **`koroshi_actividades` 1.4.0**: el tipo `actividad` (`selection_add` + `actividad_id`). Va aquí porque actividades
  depende de operarios y no al revés.
  - Al pulsar «Fin» (`acabar()`, `koroshi_actividades/models/registro.py:195`), la tarjeta de esa persona pasa a
    hecha.
  - Cambiar a otra actividad o la pausa de las 13:00 no la acaban.
  - Al empezar la actividad en el portátil, la tarjeta pasa a «haciéndose», para que el tablero vea que ya ha llegado.
- **`koroshi_zonas`, `koroshi_agrupaciones_web` y `koroshi_preparacion` no se tocan.** El tablero solo lee las Z- y las
  WEB_ por nombre.
- **Campos nuevos**, solo en la tabla propia `koroshi.operario.asignacion`, **ninguno en `stock.*`** (regla 7):
  - valores nuevos de `tipo`;
  - `zona_codigo`;
  - `tarjeta_id`: la tarjeta de la que salió cada OUT, para las barras y para saber quién está en cada zona;
  - `actividad_id`, en `koroshi_actividades`;
  - quizá un `sequence` como alias de `secuencia`. Hay que comprobar en el Odoo del servidor con qué campo reordena el
    kanban.

---

## 6. Almacén 2 y S4T (fuera de este diseño)

Lo lleva otro chat (19/11). La v3 tiene lo que se vio en el código (menús en Inventario › Operaciones; los botones
solo para Responsable de Inventario). El tablero solo añade su icono para Almacén 2 y no toca nada de S4T.

---

## 7. Riesgos

- **R1. Todas las PDA pasan por `siguiente()`.** La tarjeta de zona añade una búsqueda de candidatos en cada pedido.
  - Tiene que ir acotada a las Z- de hoy, con su propio límite.
  - Si algo falla, cae al automático de hoy en vez de dar error.
  - Hay que probarlo en una PDA real con OUT de prueba, sin validar.
- **R2. Dos PDA piden a la vez la siguiente de la misma zona** (4-5 personas en D2). Es más probable que hoy.
  - Ya se protege con `_crear_segura` (índice único de asignación viva por OUT, `reparto.py:364`): si la otra se la
    lleva, pasa a la siguiente.
  - Las tarjetas de zona y de agrupación OUT a OUT llevan un `tipo` distinto de `agrupacion`. Así el índice único
    por agrupación (`reparto.py:335`) no impide que varias personas tengan la misma.
  - Hay que probarlo con dos PDA a la vez.
- **R3. El responsable mueve tarjetas mientras una PDA pide la siguiente.** El servidor comprueba que la tarjeta sigue
  en cola; si no, avisa y recarga el tablero.
- **R4. Las OUT de zona entran en el automático.** Hoy el automático no las da (`reparto.py:432-436`), así que no se
  cuelan entre las sueltas. Con el tablero, solo se dan las de una zona cuando el operario tiene esa tarjeta. El resto
  sigue igual.
- **R5. Nombres de las Z-.** La tarjeta «D2» busca `Z-ddmm-[R2-]D2`. Si `koroshi_zonas` 1.6.0 o la 1883 cambian los
  nombres, hay que cambiarlo aquí. Confirmarlo con la sesión de zonas.
- **R6. Coordinación.**
  - Operarios 2.19.0 lo vigila «Cierre por inactividad», y «Alarma PDA» tiene operarios/preparación con «?». Hay que
    avisarlas.
  - Antes de nada, pedir la `installed_version` real (regla 3).
  - Toca dos módulos: operarios y actividades.
- **R7. Instalar.** Actualizar operarios saca las sesiones unos minutos. Hay que instalarlo uno a uno y fuera de horas
  punta, después de zonas 1.6.0 y monitor 1.36.0, que esperan.

---

## 8. Fases

1. **Fase 1** (`koroshi_operarios` 2.20.0):
   - tablero para Almacén 2;
   - tarjetas de zona, agrupación OUT a OUT, OUT y nota;
   - barras;
   - pantalla «tarea sin pedido».
2. **Fase 1b** (`koroshi_actividades` 1.4.0): tarjetas de manipular.
3. **Opcional** (`koroshi_monitor`): el tablero en la tele, solo lectura.

---

## 9. Preguntas para Isaac

Contestadas el 19/11:

- **P1**: en el PC.
- **P2**: el orden lo pone `koroshi_zonas`.
- **P3**: si se acaba la columna, la siguiente libre.
- **P4**: manipular se acaba con «Fin» en el portátil.
- **P5**: 4-5 personas por zona, OUT a OUT.
- **P6**: solo Almacén 2 asigna.
- **P7**: por la mañana, vacío, con las piezas por repartir a un lado.
- **P8** y **P9**: los lleva otro chat.

Pendientes:

- **P2b.** Si hoy hay D2 de la primera ronda y D2 de la R2, ¿una tarjeta «D2» sirve para las dos, o son tarjetas
  distintas («D2» y «R2-D2»)? Se puede preguntar a la sesión de zonas.

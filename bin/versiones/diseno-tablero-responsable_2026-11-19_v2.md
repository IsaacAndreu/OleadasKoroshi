# Tablero del responsable: repartir tareas entre operarios (diseño v2, 19/11/2026, sin código)

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
| **Actividad** (manipular…) | Pantalla «Ahora: Manipulación devoluciones. Ve al portátil de Actividades», con el botón «Hecho, siguiente». |
| **Nota** | Texto del responsable («Ayuda a descargar el camión»), con «Hecho, siguiente». |

**Cuatro o cinco operarios pueden tener la misma zona.** Cada uno se lleva OUT distintas.

- Cada OUT dada crea su asignación, igual que hoy. Una OUT que ya tiene otro no se da (lo mismo que hace hoy
  `_candidatos`).
- **Orden dentro de la zona**: el mismo que en el resto (por número de pedido, como `koroshi_zonas` 1.6.0, o por
  fecha prevista, como hoy). Ver P2.
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
  - salen todos los operarios de hoy, aunque no tengan nada (`group_expand` sobre «Operarios de hoy»);
  - hay una columna «Sin asignar».
- **Qué se puede hacer**:
  - **Arrastrar** para cambiar el orden o el operario.
  - **Botón «+ Tarea»** en cada columna: zona (lista D1…MU2), agrupación (las vivas de hoy), actividad, nota u OUT.
  - **«Copiar a…»** para poner la misma zona a varias personas.
  - **Subir y Quitar**, como hoy.
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
  - texto grande y el botón «Hecho, siguiente»;
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
- **`koroshi_menu` 2.4.3** (rama `koroshi_menu-2.4`; la 2.5.0 sigue sin instalar): la parte S4T para Almacén 2, si se
  hace con menús (punto 6).
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

## 6. Almacén 2 y S4T: «no ven nada ni pueden validar»

**Lo que dice el código** (sin mirar el servidor):

- «Envios a S4T» y «Traspasos S4T» están en **Inventario › Operaciones** (`stock.menu_stock_warehouse_mgmt`), no en la
  app KOROSHI. Para verlos basta con ser usuario de Inventario.
- **Sus botones** (reenviar, recuperar, etc.) solo los tiene **Responsable de Inventario** (`stock.group_stock_manager`):
  - `koroshi_s4t_envios/views/envio_views.xml:35-44`;
  - `koroshi_s4t_traspasos/views/traspaso_views.xml:31-34`;
  - `wizard/recuperar_views.xml:29`.
- **La app «Integración S4T»** de Effective (pedidos, matrículas) no está en el repo: no sé con qué grupos se ve.
- `koroshi_s4t_sync` y `koroshi_s4t_pedidos` no tienen menús.

**No he podido confirmar** qué le falta a Almacén 2: hay que mirar sus grupos y su compañía en el servidor (solo leer).
Hay tres explicaciones posibles:

- a) no es Responsable de Inventario;
- b) le falta el grupo de la app de Effective;
- c) no lo encuentra, porque no está en la app KOROSHI.

**Propuesta**, cuando se sepa qué falta:

1. **Si es a) o b)**: darle el grupo que falte desde Ajustes › Usuarios. No hace falta código; lo hace Isaac.
2. **Siempre**: una sección **«S4T»** dentro del icono «Tablero», solo para Almacén 2, con enlaces a:
   - Envíos a S4T (rechazados primero);
   - Traspasos S4T (con error primero, y los DEV sin validar);
   - Pedidos S4T sin OUT o atascados (cola `root.s4t_sync`);
   - la acción 1960 (sync manual).
   Así está todo en un sitio, que es lo que ya cuenta la Bandeja.
3. **«Validar cosas»**: hace falta saber cuáles (P8). Si son los DEV de traspasos o las OUT de expediciones, es
   permiso de Inventario. Si es otra cosa de S4T, hay que verlo.

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
  - Toca dos módulos (operarios y actividades), más el menú si la parte S4T va por menús.
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
3. **S4T para Almacén 2**: grupos (Isaac) y la sección S4T del tablero, cuando se sepa qué le falta.
4. **Opcional** (`koroshi_monitor`): el tablero en la tele, solo lectura.

---

## 9. Preguntas para Isaac

Ya contestadas el 19/11: P1 (PC), P3 (la siguiente libre) y P5 (4-5 personas por zona, OUT a OUT).

- **P2.** Dentro de una zona, ¿en qué orden se dan las OUT?
  - Por número de pedido, como `koroshi_zonas` 1.6.0 y «Siguiente tienda».
  - O por el orden de la ruta, o por la fecha prevista, como hoy.
  ¿Cuenta la R2 como la misma zona D2?
- **P4.** Las tarjetas de manipular: ¿se acaban con «Hecho, siguiente» en la PDA, o cuando pasan la tarjeta en el
  portátil?
- **P6.** ¿Solo Almacén 2 mueve tarjetas, o también otro usuario (oficina, expediciones)?
- **P7.** ¿Se copia el tablero de ayer al día siguiente (las mismas zonas a las mismas personas), o se empieza vacío?
- **P8.** «Validar cosas» desde Almacén 2: ¿qué exactamente? ¿Los DEV de traspasos, las OUT de expediciones, los envíos
  rechazados por S4T u otra cosa?
- **P9.** ¿Me das permiso para **leer** (sin cambiar nada) en el servidor los grupos y la compañía de Almacén 2 y los
  grupos de los menús de la app «Integración S4T»? Es para saber por qué no ve lo de S4T.

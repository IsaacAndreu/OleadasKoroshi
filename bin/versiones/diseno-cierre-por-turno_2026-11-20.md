# Cierre por turno y descansos — diseño (20/11/2026, sin código)

Petición de Isaac (grabación del 20/11, punto 4 de `plan-grabaciones-29-30_2026-11-20.md`).

## Cómo está ahora (servidor, 20/11)

- **Actividades** (`koroshi_actividades` 1.5.0, `registro.py` `cron_cerrar`): dos horas fijas para todos.
  - `hora_pausa` = «no». Antes era 13:00 y alguien lo cambió a mano con el turno de 6 a 14.
  - `hora_cierre` = 17:00. Quien se va a las 14:00 queda abierto hasta las 17:00.
  - Desde la 1.4.0, el «¿Sigues?» (desde las 13:00; pregunta a los 30 min sin señal; espera 15 min) ya cierra a quien
    no contesta. Pero no sabe a qué hora acaba cada turno.
- **Picking** (`koroshi_operarios` 2.22.1): las tareas se cierran solas a los 15 min sin leer (2.19.0) y a
  medianoche. No hay hora de cierre. La tarjeta de la PDA dura 60 min (`minutos_tarjeta`).
- **Horario de Odoo**: un solo horario, «Estándar de 40 horas», en los 25 operarios. No se usa en ningún módulo.
- **Alarma de Preparación**: `horario_alarma` = 06:00-10:00, 10:15-13:00, 14:00-17:00. Es otro horario fijo escrito
  a mano.
- **Turnos reales** (primera y última señal por persona):
  - 16 y del 18 al 20/11: casi todos de 6:00 a 13:00-14:00.
  - 17/11: de 8:00 a 16:45 (partido).
  - Algún día hasta las 20:00.
  - El turno cambia por semana y casi siempre es el mismo para todo el equipo.

## Propuesta

### 1. Turnos (tabla propia nueva, en `koroshi_operarios`)

`koroshi.turno`: nombre, tramos de trabajo, hora de fin y descanso. Ejemplos:

| Turno | Tramos | Descanso que se descuenta |
|---|---|---|
| Mañana 6-14 | 06:00-14:00 | 15 min (8 h seguidas) |
| Partido 8-17 | 08:00-13:00, 14:00-17:00 | la comida 13-14 (ya fuera de los tramos) |
| Tarde camión | 14:00-19:00 (o lo que toque) | — |

- **Turno de la semana**: uno marcado «por defecto» para todo el equipo. Lo cambia el responsable en un sitio
  (sin tocar parámetros a mano).
- **Excepciones**: persona + día (o rango de días) + turno, p. ej. «Pep, 21/11, hasta las 19:00 (camión)». Tabla propia;
  no se toca `hr.employee`.
- No se usa `resource.calendar` de Odoo: los responsables no tienen permisos de RRHH y cambiar a todos cada
  semana sería un lío.

### 2. Cierre al final del turno (Actividades y picking)

- **Al llegar la hora de fin de su turno**, a quien siga abierto se le pregunta «¿Sigues?» enseguida (sin esperar los
  30 min). Si en 15 min no contesta, se cierra **a la hora de fin del turno**, no más tarde.
- Si contesta (expediciones hasta las 19:00), sigue y el «¿Sigues?» de siempre le pregunta cada 30 min.
- La hora fija de las 17:00 (`hora_cierre`) desaparece. Queda un tope de seguridad (p. ej. 22:00) para lo que nadie
  cierre.
- En horario partido, la pausa de la comida es la del turno (13:00-14:00), no un parámetro para todos.
- Picking: a la hora de fin del turno + 15 min, la tarea abierta se cierra igual que por inactividad (con fin = última
  lectura) y la PDA olvida la tarjeta.

### 3. Descanso de la regla de la empresa

- **8 h seguidas**: 15 min de descanso que se descuentan solos de las horas del día de esa persona, aunque no haya
  parado (y si ha parado más, no se descuenta dos veces).
- **Partido**: la hora de comida ya no cuenta, porque no está dentro de los tramos.
- Dónde se descuenta: horas de la jornada de Actividades y la presencia del Monitor y del correo (u/h real). Hay que
  decidir si también en el Monitor.

## Qué toca

- `koroshi_operarios`: modelo de turnos, pantalla del responsable y el cierre de las tareas de picking.
- `koroshi_actividades`: el cron cierra por turno.
- Si se descuenta el descanso en la u/h, también `koroshi_monitor` y `koroshi_informe`.
- Son varios módulos (regla 6): uno detrás de otro, cada uno con su versión.
- `koroshi_operarios` lo ha tocado hoy la sesión de la tarjeta compartida (2.22.1, instalada): confirmar que está libre.

## Preguntas para Isaac

1. ¿El turno es el mismo para todo el equipo cada semana, con excepciones por persona y día? ¿O cada persona tiene el suyo?
2. ¿Quién lo cambia: el responsable desde el Tablero, o tú en Ajustes?
3. Los 15 min de descanso con 8 h seguidas: ¿se descuentan de las horas de la jornada y también de la presencia del
   Monitor y del correo (u/h real)?
4. Al fin del turno: ¿«¿Sigues?» y, sin respuesta, cierre a la hora de fin del turno (lo que propongo)? ¿O cierre directo?

## v2 (20/11, respuestas de Isaac)

1. El turno no es fijo: **lo decide la hora de entrada**. Quien entra a las 8 hace 8-13 y 14-17. Quien entra a las 6
   hace 6-14 con 15 min de pausa. → No hay tabla de turnos que mantener: una regla por hora de entrada.
2. (Quién cambia el turno) Ya no hace falta: nadie lo cambia, se deduce solo.
3. El descanso se descuenta de la presencia del Monitor y del correo.
4. Al acabar el turno, «¿Sigues?» y, sin respuesta, cierre a la hora de fin del turno: sí.

### Regla (un parámetro, en koroshi_base)

`koroshi_base.turnos` = `antes de 07:00 = 06:00-14:00 descanso 15; de 07:00 a 11:00 = 08:00-13:00 y 14:00-17:00`

- **Entrada** = primera señal de la persona ese día (primera tarea de Lecturas o primer tramo de Actividades).
- Entra después de las 11:00 (camión, refuerzo): sin hora de fin. Solo el «¿Sigues?» cada 30 min y el tope de noche.
- La función que lo calcula va en `koroshi_base.comun` (regla 8), y la usan los otros módulos.

### Qué hace cada módulo

- **Actividades**: a la hora de fin de su turno, «¿Sigues?» enseguida; sin respuesta en 15 min, se cierra a esa hora.
  En partido, la pausa de la comida (13:00) es la del turno. Fuera la hora fija de las 17:00 (queda un tope a las 22:00).
- **Picking**: a la hora de fin del turno + 15 min sin leer, la tarea se cierra con fin = última lectura (ya lo hace
  la inactividad; esto solo lo asegura).
- **Monitor y correo**: la presencia no pasa de la hora de fin del turno si no hay lecturas después. Turno de 6-14:
  se descuentan 15 min, menos lo que ya se haya quitado ese día por huecos de 15 min o más (no se descuenta dos veces).
  Partido: de 13 a 14 no es presencia.

### Orden (un módulo cada vez)

koroshi_base → koroshi_actividades (cuando lo suelte «PDA: entrada única», que hace la 1.6.0) → koroshi_operarios →
koroshi_monitor → koroshi_informe.

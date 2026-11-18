# KOROSHI Actividades (registro de tiempo de manipulaciones)

Sustituye la hoja donde las personas de manipulaciones apuntaban a mano la hora de empezar y de acabar.
No cuenta unidades: solo **tiempo por persona y actividad**.


## v1.3.1: icono propio (18/11/2026)

- Cronómetro morado en la pantalla de inicio. Antes era una copia del de Lecturas y no se distinguían. Solo imagen.

## v1.3.0: pasa a koroshi_base (16/11/2026, auditoría 13/11, fase 6)

- La hora del almacén sale de `koroshi_base.comun` (instalar koroshi_base antes). Mismo resultado; sin campos ni
  vistas nuevas.

## v1.2.0: permisos (14/11/2026, auditoría 13/11, fase 3)

- Las rutas de la pantalla (`/koroshi/actividades/*`) piden el permiso de **Inventario** (`stock.group_stock_user`):
  el usuario del portátil tiene que tenerlo (el 14/11 lo tienen todos los usuarios de la empresa 8).
- La persona se comprueba en el servidor: empleado activo, con tarjeta y de una empresa del usuario.

## En el portátil

App **Actividades** en la pantalla de inicio (o Inventario > KOROSHI Operarios > Actividades (manipulaciones) >
Actividades (portátil)).

1. Pasa tu tarjeta de operario (la misma de Lecturas) o escribe tu código y Enter.
2. Toca lo que vas a hacer: Manipulación marketplace, Tiendas, Web, Manipulación devoluciones, Inversa, Bolsas y
   etiquetas… Tocar otra actividad = cambiar (la anterior se cierra sola).
3. **Pausar** / **Seguir** / **Fin** (Fin pide confirmación). El panel se cierra solo a los 20 s.

Pueden trabajar varias personas a la vez: cada una con su tarjeta. A la derecha se ve quién está en cada actividad,
quién en pausa y quién ha terminado, con su tiempo de hoy.

## Solo, sin que nadie toque nada

- **13:00**: quien siga trabajando queda en pausa a las 13:00 exactas (comida). Al volver: tarjeta y «Seguir».
- **17:00**: se cierra todo lo que siga abierto, a las 17:00 exactas.
- Lo que quede abierto de otro día se cierra a las 17:00 de ese día.

Parámetros del sistema (no se pisan al actualizar):

| Clave | Por defecto | Qué hace |
|---|---|---|
| `koroshi_actividades.hora_pausa` | `13:00` | pausa automática ('' = no) |
| `koroshi_actividades.hora_cierre` | `17:00` | cierre automático ('' = no) |
| `koroshi_actividades.sin_tarjeta` | `0` | `1` = abrir a una persona tocando su nombre en la lista |
| `koroshi_actividades.inversa_destinos` | `JA=JA, PT=PT, TR=TR, ML=ML, ...=ACC, *=RESTO` | palet de cada familia en la inversa |

## Informes (grupo «KOROSHI Operarios: ver productividad»)

- **Jornada por persona**: entrada, salida, horas trabajadas, horas en pausa, y si se le olvidó pausar o acabar
  (en naranja).
- **Horas por actividad**: tabla dinámica persona × actividad y gráfico por día.
- **Tramos de tiempo**: cada tramo; se puede corregir a mano (inicio, fin) y cerrar uno abierto.
- **Configuración: actividades**: nombre, orden, color y texto del botón; archivar para quitarla sin perder horas.

## Qué toca

Solo sus tablas: `koroshi.actividad`, `koroshi.actividad.registro`, `koroshi.inversa.caja` y la vista
`koroshi.actividad.jornada`. Lee `s4t.matricula` si existe.
No añade campos a albaranes, movimientos, tipos de operación ni empleados. Depende de `koroshi_operarios` (tarjetas
y grupo de productividad).

## Inversa (v1.1.0)

En las actividades con «Lee matrículas» (de partida, **Inversa**):

1. La persona pasa su tarjeta y toca **Inversa**. Queda como persona de esa pantalla (PDA o portátil de la estación):
   desde ahí no hace falta volver a pasar la tarjeta.
2. Cada vez que abre una caja de tienda, lee su **matrícula** (CJ + 9 cifras). No cuenta ni lee uds.
3. En pantalla: la caja abierta, su tiempo, las uds del teórico por familia y a qué palet va cada familia
   (`koroshi_actividades.inversa_destinos`, p. ej. `JA=JA, PT=PT, TR=TR, ML=ML, XC ZC ...=ACC, *=RESTO`), y las
   cajas y uds de hoy.
4. **Anular última lectura** si se ha leído una por error. Una matrícula ya leída pregunta si se cuenta otra vez.
   Una CJ665… (caja nuestra de salida) no se acepta.

Tiempo de una caja = desde que se lee hasta la siguiente matrícula, la pausa o el fin (también las automáticas).
El teórico sale de `s4t.matricula` (importación del Excel «EAN | CAJA», módulo de Effective); solo se lee. Si la
matrícula aún no está importada, la caja cuenta igual y un cron pone sus uds cuando aparece (últimos 14 días).
Informe: **Inversa: cajas leídas** (tabla dinámica persona × día: recuento de cajas, uds y minutos).

## Pendiente

- Confirmar con Betty que el teórico de las matrículas llegará por `s4t.matricula`.

## Versiones

- v1.0.0 (13/11/2026): primera versión.
- v1.1.0 (14/11/2026): inversa (matrículas) y fase 2.8 de la auditoría (tramos olvidados, un solo tramo abierto).

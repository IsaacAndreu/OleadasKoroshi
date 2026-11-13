# KOROSHI Actividades (registro de tiempo de manipulaciones)

Sustituye la hoja donde las personas de manipulaciones apuntaban a mano la hora de empezar y de acabar.
No cuenta unidades: solo **tiempo por persona y actividad**.

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

## Informes (grupo «KOROSHI Operarios: ver productividad»)

- **Jornada por persona**: entrada, salida, horas trabajadas, horas en pausa, y si se le olvidó pausar o acabar
  (en naranja).
- **Horas por actividad**: tabla dinámica persona × actividad y gráfico por día.
- **Tramos de tiempo**: cada tramo; se puede corregir a mano (inicio, fin) y cerrar uno abierto.
- **Configuración: actividades**: nombre, orden, color y texto del botón; archivar para quitarla sin perder horas.

## Qué toca

Solo sus tablas: `koroshi.actividad`, `koroshi.actividad.registro` y la vista `koroshi.actividad.jornada`.
No añade campos a albaranes, movimientos, tipos de operación ni empleados. Depende de `koroshi_operarios` (tarjetas
y grupo de productividad).

## Pendiente

- Inversa: leer la matrícula de cada caja dentro de la actividad «Inversa» (cajas, tiempo por caja y uds del
  teórico). Diseño en `bin/versiones/diseno-lectura-matriculas-inversa_2026-11-12_1705.md`.

## Versiones

- v1.0.0 (13/11/2026): primera versión.

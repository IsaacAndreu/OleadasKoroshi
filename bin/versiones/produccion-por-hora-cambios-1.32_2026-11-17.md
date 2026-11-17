# Producción por hora — cambios pedidos por el responsable (17/11/2026)

Fuente: `bin/versiones/transcripciones-almacen_2026-11-17.md`, secciones 1 y 2. Versión instalada: koroshi_monitor
1.31.0 (17/11, 10:53). **Nada modificado todavía.**

## Propuesta para koroshi_monitor 1.32.0

| # | Qué pide | Qué haría | Dónde |
|---|---|---|---|
| 1 | Dos u/h: la de picking (la de ahora) y la **real de la hora entera** (Diana 9-10: 42 uds = 42 u/h, no 65). La principal, la real. | En cada casilla: uds, **u/h real** grande y u/h picking pequeña. u/h real de una hora = uds ÷ minutos de presencia en esa hora × 60 (hora entera = 60 min; en la primera, la última y la hora en curso, solo los minutos que ha estado). Total del día: uds ÷ horas de presencia. Presencia = de su primera tarea del día a la última (o ahora), con los huecos entre pedidos dentro. | `produccion_calc.py` (nuevo `minutos_presencia_por_hora`), `produccion.js` (casilla y columnas) |
| 2 | **Minutos efectivos y tiempo perdido** bien visibles (se confundió 91 uds con minutos). | En cada casilla: «41 min · 19 perdidos». Columna nueva «Perdido» por operario y fila EQUIPO. | `produccion.js`, Excel (columna «Min perdidos» y «u/h real») |
| 3 | **Colores** según el ritmo. | Verde / ámbar / rojo según la u/h real de la casilla contra un **ritmo estándar** (pregunta abierta). | `produccion.js`, `produccion.css` |
| 4 | Separar **tiendas (zonas) / webs / Zalando-Volldur**; las webs también. | Cada pedido se clasifica por el tipo de su pedido de venta (PED. TIENDAS / PED. MARKETPLACE / web e INT) y la pantalla tiene un selector «Todo · Tiendas · Web · Marketplace». Solo puede salir lo que se hace con tarjeta en Lecturas: lo de la app de siempre sin tarjeta no tiene operario. | `produccion.py` (`_tareas`: tipo), `produccion_calc.py`, `produccion.js` |
| 5 | «No salen las tiendas». | Comprobado a las 10:55: salen (12 operarios, 1.632 uds). Era la caché del navegador (Ctrl+F5) o una PDA con la versión anterior. Nada que cambiar. | — |
| 6 | ¿Cuenta pedidos de ayer? (3 uds de 8 a 9). | Solo cuenta las tareas empezadas ese día. Las 3 uds de 8 a 9 de Maria Cristina son de 2 minutos de tarea dentro de esa hora: empezó a las 8:58. Correcto. | — |
| 7 | **Cabecera del día**: total (pendiente a primera hora + entrado), hecho, pendiente, previsión de horas y **hora de fin** al ritmo actual. | Franja arriba con lo mismo que la vista Tiendas del Monitor (uds por coger, % hecho, hora de fin). Ojo: el Monitor cuenta las OUT **creadas o validadas** ese día, no lo pendiente de días anteriores. Para «pendiente a primera hora» hay que sumar las OUT de tienda abiertas creadas antes. | `produccion.py` (reusar `KoroshiMonitor._calcular_datos` o su consulta) |
| 8 | La pantalla de la otra nave: «2.530 de 3.171, 80 %… no puede ser». | Es otro módulo (`oriola_monitor`), no este. Otra sesión. | — |
| 9 | **Barra de progreso por pedido** (120 uds a ritmo estándar = 1 h; se pone roja si va atrás) y pantalla para los operarios. | Para la 1.33.0, cuando esté decidido el ritmo estándar. | `produccion.js` / pantalla nueva |
| 10 | Extender a la otra nave. | Más adelante. | — |
| — | Informe a final de mes. | Lo lleva la sesión del informe por correo (`koroshi_informe`). | — |

## Preguntas abiertas
1. **Ritmo estándar** (u/h real) para los colores y la barra: ¿verde a partir de cuántas u/h y rojo por debajo de cuántas? (Hoy el equipo va a 65 u/h de picking.)
2. **Presencia**: ¿de la primera tarea del día a la última, contando como perdidos los huecos entre pedidos (cerrar caja, palé, desayuno)? Las pausas de la PDA (comer, café) no se guardan con hora de fin, así que hoy no se pueden descontar.
3. **Pendiente a primera hora**: ¿solo OUT de tiendas, o también web y marketplace?

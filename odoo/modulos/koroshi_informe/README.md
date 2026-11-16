# KOROSHI Informe de productividad (v1.2.0, 16/11/2026)


## v1.2.0: pasa a koroshi_base (16/11/2026, auditoría 13/11, fase 6)

- Empresa, hora del almacén y límites de día salen de `koroshi_base.comun` (instalar koroshi_base antes). Mismo
  resultado: los límites ya estaban bien los días del cambio de hora. Sin campos ni vistas nuevas.

## v1.1.0: la misma cifra que todo lo demás (14/11/2026, auditoría 13/11, fase 2)

- La u/h de los operarios sale de **koroshi_operarios 2.12** (`resumen_operario_dia`): la misma que Productividad, el
  KPI, el Monitor y la PDA. La fórmula no cambia (uds × 60 / minutos efectivos, sin parados), solo deja de estar
  repetida aquí.
- Es el **único correo diario**: el de koroshi_operarios se ha quitado.
- La tabla por operario y día ya no hace la media de u/h al agrupar.
- «Horas estimadas» sale de la fuente de horas de la ficha KPI (koroshi_kpi 1.6).
- Necesita koroshi_operarios 2.12 y koroshi_kpi 1.6 (el script los instala juntos).
- Al actualizar, su migración recalcula las tareas de operario que ya hay con la cifra nueva (va aquí porque necesita
  las lecturas de koroshi_preparacion, que se carga después de koroshi_operarios).

## v1.0.1 (13/11/2026)

- La 1.0.0 no se instalaba: «View inheritance may not use attribute 'string' as a selector». El grupo de Ajustes se
  engancha ahora al campo `kpi_dias_falta_repetida` (su grupo «KPI»), no a `@string`.

Correo automático de productividad del almacén KOROSHI para la responsable y el jefe de almacén. Lo pidió la
responsable en la reunión: un resumen diario por operario, más uno semanal y uno mensual.

## Qué manda

| Correo | Cuándo | Qué |
|---|---|---|
| Diario | cada día a las **17:00** (si ese día hubo actividad) | el día |
| Semanal | **lunes 08:00** | la semana anterior (lunes a domingo) contra la de antes |
| Mensual | **día 1, 08:00** | el mes anterior contra el de antes |

**Diario:**
1. **Cifras:**
   - uds hechas contra el mismo día de la semana pasada;
   - pedidos de tienda (OUT y OUT por hacer);
   - uds de falta;
   - operarios con tarjeta y OUT validadas con operario.
2. **Operarios de hoy:** de qué hora a qué hora, pedidos, uds, tiempo, u/h, parado y la u/h contra sus últimos 5 días.
3. **Mejores de los últimos 5 días y récords:** el de cada operario (🏆 si lo bate hoy) y el del almacén.
4. **Tiempos parados:**
   - pedidos abiertos ahora sin leer;
   - huecos sin leer con el pedido abierto;
   - total del día.
5. **Faltas del día:** por motivo, los artículos con más falta y las faltas repetidas que siguen.
6. **Esta semana contra la pasada:** día a día (uds, u/h-persona y faltas) y total de lunes a hoy.

**Semanal y mensual:** llevan lo mismo, pero del periodo:
- cifras contra el periodo anterior;
- día a día (semanal) o semana a semana (mensual);
- operarios con días, pedidos, uds, tiempo, u/h y parado, contra el periodo anterior;
- mejores y récords batidos;
- parado total;
- faltas, con los 10 artículos que más fallan.

## Cómo se cuenta

- **Uds, pedidos, cajas y u/h-persona del almacén:** ficha KPI del día completo (`koroshi_kpi`).
  - Uds = las de las cajas cerradas ese día de los pedidos de tienda.
  - Antes de mandar el diario se recalculan la ficha y las faltas de ese día. Es lo mismo que el botón *Recalcular*
    de la ficha.
  - ⚠ = horas de picking **estimadas** por las cajas, no apuntadas a mano. Con zonas salen pocas horas y la u/h se
    dispara (180 u/h el 10 y el 11/11).
- **Operarios:** tareas con tarjeta (`koroshi_operarios`). Las uds y el tiempo son los de *Productividad*. Las tareas
  abiertas cuentan hasta ahora.
- **Parado:** `koroshi_operarios.minutos_sin_leer` minutos o más (**15**) sin ninguna lectura de Preparación con el
  pedido abierto. Es el mismo número que la alarma del monitor. Cuenta también lo que lleva sin leer un pedido aún
  abierto.
  - Las tareas hechas con la app de código de barras (sin Preparación) no dejan rastro de las lecturas una vez
    validadas. Su parado sale como «?» y no se cuenta.
- **u/h de un operario** = uds × 60 / (minutos con el pedido abierto − parado).
- **Mejores y récords:** solo días con **60 min** o más trabajando con tarjeta (parámetro).
  - Los «últimos 5 días» son los 5 últimos días con tarjeta.
  - El récord de un operario es su mejor día. 🏆 sale solo si ya tenía otro día antes.
- Se guarda un resumen por operario y día en `koroshi.informe.operario.dia`. Lo usan los récords y las comparaciones.
  - El cron rellena los días acabados. La primera vez, desde la primera tarea.
  - Se puede ver en *Productividad por operario y día*.

## Ajustes

*Inventario › Configuración › KOROSHI › Ajustes KOROSHI*, grupo **Informe de productividad (correo)**:

| Campo | Parámetro | De inicio |
|---|---|---|
| Correos | `koroshi_informe.destinatarios` | vacío = **no se manda nada** |
| Mandar el diario / hora | `koroshi_informe.diario` / `.hora_diario` | sí / 17:00 |
| Mandar el semanal / el mensual / hora | `.semanal` / `.mensual` / `.hora_resumen` | sí / sí / 08:00 |
| Mejores y récords desde (min) | `.minutos_ranking` | 60 |
| No sacar estos operarios | `.excluir` | `OP9990001, OP9980001` (las tarjetas de prueba Isaac e Isaac2) |

Hay más parámetros en *Ajustes › Técnico › Parámetros del sistema*:
- `koroshi_informe.servidor`: servidor de correo saliente, `NATH`.
- `ultimo_diario`, `ultimo_semanal`, `ultimo_mensual` y `cerrado_hasta`: los escribe el cron.

Al instalar no se manda el semanal ni el mensual atrasados: el primer paso del cron solo los marca.

## Menús

En *Inventario › Informes › KOROSHI › Informe de productividad (correo)*, para el grupo «KOROSHI Operarios: ver
productividad»:

- **Ver informe de hoy / semana pasada / mes pasado:** abre el correo en el navegador **sin mandarlo**
  (`/koroshi/informe/ver?tipo=diario|semanal|mensual&dia=AAAA-MM-DD`).
  - El de hoy recalcula antes la ficha KPI. Con `&recalcular=0` no.
- **Mandar informe de hoy ahora:** a los correos de Ajustes. No marca el día como enviado.
- **Productividad por operario y día:** la tabla que guarda el informe.

Cron: *KOROSHI Informe: correo de productividad*, cada 15 min.

## Con el informe de koroshi_operarios

`koroshi_operarios` ya manda a las 17:00 su informe diario (parámetro `koroshi_operarios.informe_destinatarios`).
Este módulo no lo toca.

Cuando este funcione, se puede apagar aquel. Hay dos formas:
- vaciar sus correos en Ajustes KOROSHI;
- archivar el cron *KOROSHI Operarios: informe diario por email*.

## Seguridad

- Solo escribe en `koroshi.informe.operario.dia`, en sus parámetros `koroshi_informe.*` y en `mail.mail`.
- Antes del diario recalcula la ficha KPI y las faltas del día (tablas de `koroshi_kpi`) y cierra las tareas ya
  validadas (`cron_cerrar` de `koroshi_operarios`), igual que su informe.
- No añade campos a ninguna tabla de otro módulo.
- Ajustes KOROSHI se amplía por herencia: `koroshi_menu` no cambia.

## Ficheros

```
models/informe.py         koroshi.informe (datos, html, envio, cron) y koroshi.informe.operario.dia
models/ajustes.py         campos en Ajustes KOROSHI (hereda koroshi.ajustes)
controllers/main.py       /koroshi/informe/ver (vista previa)
data/parametros.xml       parametros (noupdate)
data/cron.xml             cron cada 15 min
views/informe_views.xml   menus, acciones, lista por operario y dia
views/ajustes.xml         grupo en Ajustes KOROSHI
```

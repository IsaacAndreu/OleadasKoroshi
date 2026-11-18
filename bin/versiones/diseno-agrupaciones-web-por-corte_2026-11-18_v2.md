# Agrupaciones web por corte horario y cancelación de las no reservadas: diseño v2 (18/11/2026)

Sustituye a `diseno-agrupaciones-web-por-corte_2026-11-18.md` (v1). Sigue sin código.

## Respuestas de Isaac (18/11)

1. Tope de **100 unidades** por agrupación: sí.
2. Cortes a las **6:00 y a las 11:00**.
3. «Las dejas en cancelar»: lo entiendo como «las que no están al 100 % se cancelan» (ver 5). Las agrupaciones se dejan
   **En curso**, como las que hace hoy la oficina.
4. ¿Módulo nuevo o dentro de otro? Se puede poner dentro de otro, pero no conviene:
   - `koroshi_preparacion` es la PDA: si un fallo de esto la tumba, para el almacén.
   - `koroshi_s4t_sync` lo tiene cogido otra sesión (TABLERO.md, regla 6).
   - Un módulo nuevo se instala, se apaga o se desinstala sin tocar nada de lo que ya funciona.
   Propuesta: **módulo nuevo `koroshi_agrupaciones_web`**.
5. La cancelación de las no reservadas va **en esta misma versión**.

## Lo nuevo que he encontrado (solo lectura)

- **La oficina ya cancela a mano las web.** Hoy, entre las 13:52 y las 13:54 (hora local), «Almacén Nath» canceló 18
  OUT web, una cada 4-5 s. Cancela la OUT; el pedido de venta se queda en «Pedido de venta». Del 11 al 17/11, unas
  17-23 al día.
- **S4T no recibe nada de ningún pedido web.** Los 867 pedidos `W-` desde el 10/11 están en `x_s4t_status = PENDING`,
  también los hechos y enviados. El cron 186 (acción 1800 v6.3) solo sincroniza `S-6665%`, y `koroshi_s4t_envios`
  también (`envio.py:366`). Por eso «pasar el estado cancelado a S4T» **no tiene hoy ningún camino**: sería el primer
  pedido web que se manda a S4T.

## Diseño

### Agrupación (igual que en la v1, con los valores de Isaac)

- **Cortes**: `koroshi_agrupaciones_web.cortes` = `06:00,11:00` (hora del almacén). Un cron cada 15 min hace el corte
  que toque y lo apunta para no repetirlo.
- **Qué entra**: OUT web (`origin` `W-`, tipo de pedido distinto de MARKETPLACE: Zalando no entra nunca), compañía 8,
  100 % reservadas, sin agrupación y creadas antes de la hora del corte.
- **100 % reservada**: OUT «Preparada» y ningún movimiento «En espera», «Esperando otra operación» o «Parcialmente
  disponible». Todas las OUT web tienen `move_type='direct'` y Preparada sola no basta: `EFFEC/OUT/26287` está
  Preparada con 2 de 3 líneas reservadas.
- **Orden de llegada** (fecha de creación de la OUT). **100 uds como máximo** por agrupación: si la siguiente OUT se
  pasa, se abre otra (`_02`, `_03`…). Una OUT nunca se parte.
- **Nombre** `WEB_ddmmaa_NN`, siguiendo la numeración del día (PedidosMultiples las coge por `WEB_`). **En curso**.
- **Filtros** en la lista de albaranes: «100 % reservada», «Reserva incompleta», «Web sin agrupar». Sin campos nuevos en
  `stock.picking`: son dominios sobre `move_lines.state`.

### Cancelación de las no reservadas (nuevo)

En cada corte, **antes de agrupar**, se cancelan las OUT web que:
- no están al 100 % reservadas,
- se crearon antes de la hora del corte,
- no están en ninguna agrupación,
- no tienen nada leído (`qty_done` = 0 en todas sus líneas),
- no son MARKETPLACE ni tiendas (doble comprobación: origen `W-` y tipo `PED. ONLINE`).

Se cancela la OUT con `action_cancel()` (no se borra: borrar deja huecos, ver memoria del K72), como hace hoy la
oficina. El pedido de venta no se toca. Cada cancelación queda apuntada en el chatter de la OUT y en una lista del
módulo (fecha, corte, OUT, pedido, qué faltaba: «2 de 3 uds reservadas; falta SKU …»).

Seguridad:
- Interruptor `koroshi_agrupaciones_web.cancelar` = `0` al instalar. Con 0, cada corte apunta **qué cancelaría** sin
  cancelar nada. Se mira una mañana y se enciende.
- Interruptor general `koroshi_agrupaciones_web.activo` = `0` al instalar (ni agrupa ni cancela).
- Botones en la lista de OUT: «Simular corte ahora» (no cambia nada) y «Hacer corte ahora».

### Informe a S4T

Hasta que se decida (pregunta B), **cada corte deja una lista de las canceladas** en Odoo y la manda por correo a quien
diga Isaac. No se llama a la API de S4T.

## Preguntas que faltan

**A. Reserva parcial.** Un pedido web de 3 prendas con 2 reservadas: ¿se **cancela entero** (tu nota del 13/11) o se
mandan las 2 y se cancela solo la que falta? La oficina hoy cancela la OUT entera.

**B. Cómo se le dice a S4T que está cancelado.** Hoy no se le manda nada de ningún pedido web, ni los enviados.
Opciones:
1. **Correo con la lista** (Excel) a S4T u oficina en cada corte. Sin riesgo. *(Propuesto para esta versión.)*
2. **API de S4T** (`batch-update` con 0 uds servidas, el mismo que usa el cron 186 para tiendas). Sería el primer pedido
   web que se le manda a S4T: hay que preguntarles antes si lo esperan y cómo lo leen. Se haría en una segunda versión.
3. Nada: solo se cancela en Odoo.

**C. ¿A quién va el correo** de las canceladas?

## Cómo se probaría

- Simulación sobre las OUT reales (no cambia nada) y comparar con lo que hizo la oficina ese día.
- Instalado con los dos interruptores a 0; luego `activo=1` (agrupa) con `cancelar=0` (solo lista) un día; luego
  `cancelar=1`.
- La `WEB_…` de las 6:00 tiene que salir en PedidosMultiples igual que una hecha a mano.
- En PDA real: nada (no la toca).

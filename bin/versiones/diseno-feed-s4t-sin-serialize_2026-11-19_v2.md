# Diseño: pedidos S4T grandes sin «could not serialize» (19/11/2026), v2

v2 (19/11 ~10:20 UTC): leído en el servidor el código de Effective y el log. Hay una segunda causa: dos copias
del mismo job a la vez, por reencolar uno que seguía vivo. Se añade el candado por feed (D) y la v7 del cron 192
deja de reencolar jobs vivos. La opción C se descarta: Effective ya crea todas las líneas en un solo `create`.

Estado: **PROPUESTA, sin código.** Espera el visto bueno de Isaac antes de implementar (regla 11).

## 1. Qué pasa hoy (leído en el servidor el 19/11 ~10:14 UTC, solo lectura)

Caso: feed 10131 = S-6665004459, K ZALANDO ZFS, 329 líneas, job uuid 0608006b-…, canal `root.s4t_sync` (capacidad 1).

### Código de Effective (`api_s4t_batch_update_PROD/models/s4t_order_feed.py`)

- `:56` `action_create_sale_order`: si el feed no está en draft/error (`:66`) o ya tiene `sale_order_id` (`:71`), para
  con ValidationError. Así que un feed `done` con pedido **nunca se procesa dos veces**.
- Todo va dentro de `try:` + `with self.env.cr.savepoint():`: busca productos por `style_code`, crea o actualiza el
  contacto de entrega (`res.partner.create/write`), crea el pedido **con todas las líneas en un solo
  `sale.order.create(vals)`**, `write` de condiciones de pago, `action_confirm()` (`:218`, si b2c/b2b) y
  `self.write({'state': 'done', 'sale_order_id': …})` (`:222-224`). En el `except` escribe `state='error'` y relanza.
- Después de `action_confirm` **no lee ni escribe nada de la OUT**. Se puede sacar la confirmación de este método sin
  romper nada de Effective.
- `:242-251` `action_retry`: botón que encola de nuevo los feeds en `error`.
- El fetch (`s4t_order_sync`) se salta el pedido si ya tiene feed («Saltando pedido S-6665004459 … porque ya tiene
  un feed en estado …»). Con eso no se duplican feeds.

### El log: hay DOS causas, no una

1. **Reserva dentro de la transacción larga** (la esperada). 10:12:42:
   `UPDATE "stock_quant" SET … "reserved_quantity"=3.0 … WHERE id IN (2842026)` → serialize. Es la reserva de
   `action_confirm` chocando con otra transacción que tocó ese quant (una PDA o la otra copia del mismo job, ver 2).
   Así queda confirmado que en Odoo 13 `action_confirm` reserva dentro de la misma transacción.
2. **Dos ejecuciones del MISMO job a la vez** (nueva y, hoy, la principal). El cron 192 lo reencoló a las 09:49:26 y
   alguien lo reencoló **a mano** desde la web (`queue.requeue.job`) a las 09:52:56. Las dos copias corrían a la vez.
   Tres de los cuatro fallos (09:57:31, 10:04:33, 10:11:47) **no son de stock**: son
   `UPDATE "queue_job" SET "state"='done' …` → serialize. La copia había **creado y confirmado el pedido**
   («procesado correctamente») y se deshizo al guardar porque la otra copia había tocado la fila del job. Cada fallo
   deja el job en «pending» con retry+1. El jobrunner lanza otra copia mientras la anterior sigue viva, así que
   siempre quedan dos y se tumban entre ellas (retry 2 de 5 a las 10:11). Además, las dos copias reservan los mismos
   quants, con lo que también chocan en `stock_quant`.
   El origen probable: el intento de las 08:38:21 se quedó 71 min sin terminar (¿vivo y esperando un bloqueo, o
   muerto?). El cron 192 da por muerto un job «started» por el tiempo, pero **no sabe si el worker sigue vivo**.

Hay otro serialize, de las 08:44:05, en `koroshi_consumable_item` (`POST /koroshi/preparacion/caja`): es de la PDA,
Odoo lo reintentó solo («retry 1/5 in 0,38 s») y no tiene que ver con el feed.

### En los módulos KOROSHI (subagente `lector-modulo` sobre `odoo/modulos`)

- **Nadie hereda `sale.order` ni `sale.order.line`**: no hay ningún `action_confirm` propio.
- `stock.picking.create/write` en `koroshi_delegacion/models/stock_picking.py:49,56` (delegación desde el contacto) y
  `write`/`action_done` en `koroshi_caja_existente/models/stock_picking.py:176,181` (bultos al validar). Ninguno
  reserva.
- Nadie hereda `stock.move._action_confirm/_action_assign`, `stock.rule._run_pull` ni `_action_launch_stock_rule`.
- **No hay ningún cron que reserve OUT confirmadas sin reservar.** Hoy la reserva sale entera de `action_confirm`.
- El cron 192 no está en ningún módulo: es una acción de servidor en la BD. Su código está versionado en
  `bin/versiones/20261104_1600_cron-alerta-cola-s4t_v6.py`.

## 2. Alternativas

### A. Crear y guardar en un job; confirmar en otro job aparte

Un módulo nuevo `koroshi_s4t_pedidos` (depende de `api_s4t_batch_update_PROD` y de `sale_stock`), sin editar
el de Effective:

- Hereda `s4t.order.feed.action_create_sale_order` y llama a `super()` con el contexto
  `koroshi_confirmar_diferido=True`.
- Hereda `sale.order.action_confirm`: con ese contexto y si el pedido pasa de un umbral (p. ej. **≥ 60 líneas**;
  los de tienda siguen igual que hoy), **no confirma**: encola
  `pedido.with_delay(channel='root.s4t_sync', description='S4T Confirmar pedido S-…')._koroshi_confirmar_s4t()`
  y devuelve True. Effective sigue y escribe `state='done'` y `sale_order_id` → el COMMIT es corto (solo inserts de
  `sale.order`/`sale.order.line`, que nadie más toca) y **el pedido ya no se pierde**.
- El job de confirmar hace `action_confirm()` normal en su propia transacción.

Pros: el cambio es pequeño; no toca ninguna tabla compartida ni añade campos; los pedidos pequeños no cambian; el
pedido queda guardado (presupuesto) aunque la confirmación falle.
Contras: la confirmación sigue reservando 329 líneas en una sola transacción. Si el conflicto está en los quants,
el job de confirmar también puede fallar con serialize. Al menos se reintenta solo ese paso, que es más corto.
Riesgo para la PDA: ninguno directo. Las OUT nacen igual que hoy, solo unos minutos más tarde.
Si falla el segundo paso: el pedido se queda en **presupuesto** (no hay confirmado a medias: `action_confirm` es
atómico) y el job queda `failed`. El PASO 3b del cron 192 ya avisa de los jobs fallidos por correo.

### B. Confirmar sin reservar y reservar después, por bloques

Además de lo de A, el job de confirmar llama a `action_confirm()` con el contexto `koroshi_sin_reservar=True`:

- En el mismo módulo, se hereda `stock.move._action_assign`: si viene ese contexto, no hace nada. Solo afecta a
  esta llamada, no a la PDA ni a las oleadas, porque el contexto no sale de este job.
- Después, encola un tercer job `S4T Reservar OUT S-…` que reserva los moves de la OUT **por bloques de 50**
  (`moves[i:i+50]._action_assign()` + `commit` por bloque). Si un bloque da serialize, se deshace solo ese bloque y
  se reintenta (hasta 3 veces, con unos segundos de espera). Al final se escribe una línea en el Registro con
  cuántas líneas han quedado reservadas.

Pros: la transacción que choca con las PDA (escribir en quants) pasa de 4,5 min a unos segundos por bloque, así que
el serialize casi desaparece. Una OUT a medio reservar es un estado normal en Odoo («parcialmente disponible»),
no un pedido a medias: el pedido y sus líneas están todos.
Contras: hay que heredar `stock.move._action_assign`, aunque sea con un contexto. Durante unos minutos la OUT está
«En espera» o parcial.
Riesgo para la PDA: bajo. **Hay que comprobar** que nada actúe sobre una OUT de Zalando en ese rato:
`koroshi_agrupaciones_web` cancela a las 11:00 las no reservadas (confirmar que filtra solo web y nunca Zalando) y
la oleada de zonas no debe cogerla hasta que esté reservada. El job de reservar suele tardar menos de 1-2 min.
Si falla el tercer paso: el pedido está confirmado y la OUT queda sin reservar o parcial (igual que cuando falta
stock). El job queda `failed`, el cron 192 avisa y se puede reservar a mano con «Comprobar disponibilidad».

### C. Crear las líneas de una vez: descartada

Ya lo hace: Effective crea el pedido con todas las líneas en un solo `create`. No hay nada que ganar aquí.

### D. Un candado por feed, para que nunca corran dos copias del mismo job (NUEVA, imprescindible)

En el mismo módulo, `action_create_sale_order` empieza con
`SELECT pg_try_advisory_xact_lock(<clave fija>, <id del feed>)`:

- Si no lo consigue, es que otra copia del mismo feed está viva. Entonces **no hace nada** y lanza
  `RetryableJobError(seconds=300)` (vuelve a mirar en 5 min, sin tocar stock).
- Si lo consigue, sigue normal. Postgres suelta el candado al acabar la transacción, también si el worker muere o
  se corta la conexión: no se queda puesto nunca.
- Los jobs de confirmar y de reservar (A y B) llevan el mismo candado con el id del pedido.

Pros: corta de raíz el bucle de hoy, venga el reencolado de donde venga (cron 192, botón «Reencolar»,
`action_retry`). No toca tablas ni añade campos.
Contras: un job duplicado espera 5 min en vez de pelearse; hay que comprobar en local que `RetryableJobError`
no gasta los reintentos de forma que el job acabe en «failed» por esperar.
Riesgo para la PDA: ninguno (el candado es por feed o por pedido, no por quant).

### Descartada: trocear el pedido por líneas

Deja pedidos a medias en Odoo y en S4T (el feed es uno; habría que unir trozos y el envío a S4T vería pedidos
incompletos). No hay ninguna razón en el código para hacerlo.

### Descartada: subir límites de tiempo o la capacidad del canal

No es un tema de tiempo (`limit_time_real = 9999`). Con el canal a 2, dos pedidos grandes chocarían entre sí.

## 3. Lo que comparten A, B y D

- **Módulo**: nuevo, `koroshi_s4t_pedidos` (no `koroshi_s4t_sync`, que lo tiene otra sesión; regla 6). No se edita
  el módulo de Effective.
- **Tablas compartidas (regla 7)**: **no se añade ningún campo**. El seguimiento lo dan el job, el Registro
  (`ir.logging`) y el estado del pedido. No hace falta preguntar por campos nuevos.
- **Canal `root.s4t_sync` (capacidad 1)**: los jobs nuevos van al mismo canal, así que pasan de uno en uno detrás
  de los pedidos que ya hay. No hace falta tocar `nath-erp.conf` ni reiniciar. Un pedido grande ocupa el canal en
  tres ratos cortos y no en uno de 4,5 min (o de 71, si se cuelga).
- **Cron 192 «Alerta cola de S4T»** (acción de servidor, versionada en `bin/versiones/…cron-alerta-cola-s4t_v6.py`):
  los jobs nuevos no se llaman `action_create_sale_order`, así que hoy entrarían como «cortos» (se reencolan a los
  20 min). Además, hoy reencola un job «started» solo por el tiempo, aunque siga vivo, y eso es lo que provocó las
  dos copias. Hace falta una **v7** que:
  - **antes de reencolar un job de pedido, compruebe el candado de D** (`pg_try_advisory_xact_lock` en su propia
    transacción): si está cogido, el job está vivo y no lo reencola, solo avisa por correo («S-… lleva N min
    trabajando»);
  - trate «S4T Confirmar pedido» y «S4T Reservar OUT» con el límite por unidades, como los de crear pedido;
  - en el PASO 3c, avise también de los feeds `done` cuyo pedido sigue en **presupuesto** más de 60 min (falló
    confirmar) y de las OUT S4T confirmadas sin reservar nada más de 60 min (falló reservar).
- **Idempotencia**: el job de confirmar no hace nada si el pedido ya no está en presupuesto, y el de reservar no
  hace nada con los moves ya reservados. Reencolarlos no duplica nada.

## 4. Recomendación

**D + A + B juntas, en `koroshi_s4t_pedidos` 1.0.0, y la v7 del cron 192 a la vez.** A y B solo para pedidos de
**≥ 60 líneas**; D para todos los feeds (no cambia nada si no hay copias).

- D quita la causa de hoy: dos copias del mismo job tumbándose entre ellas.
- B quita la otra: reservar 329 líneas en una transacción de minutos mientras las PDA mueven stock.
- A hace que el pedido nunca se pierda: queda guardado aunque falle confirmar o reservar.
- El umbral deja los pedidos de tienda exactamente como hoy.

Orden:

1. Programar el módulo y la v7 del cron, con pruebas en local: pedido de 329 líneas simulado, dos copias del mismo
   job a la vez (la segunda tiene que esperar) y un fallo provocado en el paso 2 y en el paso 3.
2. Instalar con `-i`, solo, sin otra actualización a la vez y sin jobs «started» en el canal.

**Hoy, sin código (lo decide Isaac; desde aquí no se toca nada):**

- **No reencolar a mano** el job 0608006b mientras siga «started» o «pending»: cada reencolado añade otra copia y
  alarga el bucle.
- El bucle se acaba solo cuando el job llegue a 5 reintentos y quede «failed». Entonces, en Cola de trabajos,
  comprobar que **no queda ninguna copia «started»** y reencolarlo **una sola vez**, mejor en un rato tranquilo
  (descanso o fin de turno). Con una sola copia, lo normal es que entre.
- Mientras el cron 192 siga en la v6, puede volver a reencolar un job vivo. Para evitarlo del todo, se puede
  desactivar el cron 192 hasta que entre el pedido (se pierde su correo de alerta mientras tanto).

## 5. Qué probar en real cuando esté instalado

- Un pedido de tienda pequeño: entra igual que hoy (un solo job).
- El primer pedido Zalando grande: tres jobs seguidos en Cola de trabajos, la OUT pasa a Preparada en 1-2 min y no
  la cancela agrupaciones_web.
- Una PDA preparando a la vez que entra un pedido grande: sin «Sesión expirada» ni errores.

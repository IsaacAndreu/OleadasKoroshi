# Diseño: pedidos S4T grandes sin «could not serialize» (19/11/2026)

Estado: **PROPUESTA, sin código.** Espera el visto bueno de Isaac antes de implementar (regla 11).

## 1. Qué pasa hoy (lo confirmado y lo que falta)

Caso: feed 10131 = S-6665004459, K ZALANDO ZFS, 329 líneas, job 108863, canal `root.s4t_sync` (capacidad 1).

Confirmado por la otra sesión en el log y en el código de Effective
(`api_s4t_batch_update_PROD/models/s4t_order_feed.py`, `action_create_sale_order`, ~líneas 210-235):

- Todo va en **una sola transacción** del job: `sale.order.create(vals)` → `write` de condiciones de pago →
  `action_confirm()` (si b2b/b2c) → `feed.write({'state': 'done', 'sale_order_id': ...})` → log «procesado
  correctamente». En el `except`, el feed pasa a `error` y se relanza la excepción.
- Tarda ~4,5 min con 329 líneas. Postgres va en REPEATABLE READ: si en esos 4,5 min una PDA, «Juntar matrículas»,
  «Enviar al Expedidor» o el cron 186 ha cambiado una fila que esta transacción también escribe (quants al reservar,
  sobre todo), el COMMIT falla y **se deshace todo**, también el `state='done'`. Por eso el log dice «correctamente»
  pero no hay pedido.
- queue_job reintenta solo (retry n de 5) y el cron 192 reencola los que se quedan en «started». Mientras tanto, el
  canal de capacidad 1 bloquea a todos los pedidos que vienen detrás.

En los módulos KOROSHI (subagente `lector-modulo` sobre `odoo/modulos`):

- **Nadie hereda `sale.order` ni `sale.order.line`**: no hay ningún `action_confirm` propio.
- Hay `stock.picking.create/write` en `koroshi_delegacion/models/stock_picking.py:49,56` (rellena la delegación desde
  el contacto: escribe en la OUT al crearla, no en quants) y `write`/`action_done` en
  `koroshi_caja_existente/models/stock_picking.py:176,181` (bultos; solo al validar). Ninguno reserva.
- Nadie hereda `stock.move._action_confirm/_action_assign`, `stock.rule._run_pull` ni `_action_launch_stock_rule`.
- **No hay ningún cron que reserve OUT confirmadas sin reservar.** Hoy la reserva sale entera de `action_confirm`.

**Falta confirmar antes de programar** (solo lectura en el servidor, con tu permiso para cada comando):

1. El método entero, para ver si después de `action_confirm` Effective lee algo de la OUT (picking_ids, estado,
   disponibilidad) o lo escribe:
   `sed -n 56,251p /opt/nath-erp/nath/custom_addons/api_s4t_batch_update_PROD/models/s4t_order_feed.py`
2. Cómo se encola el job y si el fetch evita duplicados por `state` del feed o por `sale_order_id`:
   `grep -n "with_delay\|state\|sale_order_id\|def " /opt/nath-erp/nath/custom_addons/api_s4t_batch_update_PROD/models/s4t_order_feed.py`
3. Qué fila exacta da el serialize (el error trae la consulta):
   `grep -n -A6 "could not serialize" /var/log/odoo/nath-erp.log | grep -i "update\|statement" | tail -20`
4. Dónde reserva Odoo 13 al confirmar un pedido (yo creo que sí lo hace en la misma llamada, porque las OUT
   quedan «Preparadas» nada más entrar, pero no lo he visto en el código de este Odoo):
   `grep -rn "_action_assign" /usr/lib/python3/dist-packages/odoo/addons/{stock,sale_stock}/models/*.py`
   (la ruta del core hay que comprobarla: `ls /usr/lib/python3/dist-packages/odoo` o dónde diga `nath-erp.conf`).

Si el punto 3 dice que la fila en conflicto **no** es un quant (por ejemplo, `res_partner` o `product_template`),
la opción B no basta y hay que revisar qué escribe Effective al crear.

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

### C. Hacer más corta la transacción de Effective (sin partirla)

Si el punto 1 muestra que Effective crea las líneas una a una (un `create` por línea con onchanges), se puede
crear todo en un solo `create` con `order_line`. Solo se sabrá al leer el código. Baja el tiempo, pero no quita
la reserva de dentro: es una mejora, no un arreglo.

### Descartada: trocear el pedido por líneas

Deja pedidos a medias en Odoo y en S4T (el feed es uno; habría que unir trozos y el envío a S4T vería pedidos
incompletos). No hay ninguna razón en el código para hacerlo.

### Descartada: subir límites de tiempo o la capacidad del canal

No es un tema de tiempo (`limit_time_real = 9999`). Con el canal a 2, dos pedidos grandes chocarían entre sí.

## 3. Lo que comparten A y B

- **Módulo**: nuevo, `koroshi_s4t_pedidos` (no `koroshi_s4t_sync`, que lo tiene otra sesión; regla 6). No se edita
  el módulo de Effective.
- **Tablas compartidas (regla 7)**: **no se añade ningún campo**. El seguimiento lo dan el job, el Registro
  (`ir.logging`) y el estado del pedido. No hace falta preguntar por campos nuevos.
- **Canal `root.s4t_sync` (capacidad 1)**: los jobs nuevos van al mismo canal, así que pasan de uno en uno detrás
  de los pedidos que ya hay. No hace falta tocar `nath-erp.conf` ni reiniciar. Un pedido grande ocupa el canal en
  tres ratos cortos y no en uno de 4,5 min (o de 71, si se cuelga).
- **Cron 192 «Alerta cola de S4T»** (acción de servidor, versionada en `bin/versiones/…cron-alerta-cola-s4t_v6.py`):
  los jobs nuevos no se llaman `action_create_sale_order`, así que hoy entrarían como «cortos» (se reencolan a los
  20 min). Hace falta una **v7** que:
  - trate «S4T Confirmar pedido» y «S4T Reservar OUT» con el límite por unidades, como los de crear pedido;
  - en el PASO 3c, avise también de los feeds `done` cuyo pedido sigue en **presupuesto** más de 60 min (falló
    confirmar) y de las OUT S4T confirmadas sin reservar nada más de 60 min (falló reservar).
- **Idempotencia**: el job de confirmar no hace nada si el pedido ya no está en presupuesto, y el de reservar no
  hace nada con los moves ya reservados. Reencolarlos no duplica nada.

## 4. Recomendación

**A + B juntas, en `koroshi_s4t_pedidos` 1.0.0, solo para pedidos de ≥ 60 líneas**, y la v7 del cron 192 a la vez.

Con A sola puede seguir fallando el paso de confirmar si el choque está en los quants (lo más probable). B es lo
que de verdad quita el serialize, y A hace que nunca se pierda el pedido. El umbral deja los pedidos de tienda
exactamente como hoy.

Orden:

1. Leer en el servidor los 4 puntos del apartado 1 (solo lectura, con permiso).
2. Si cuadra, programar el módulo y la v7 del cron, con pruebas en local: pedido de 329 líneas simulado, y fallo
   provocado en el paso 2 y en el paso 3.
3. Instalar con `-i` en un momento sin actualizaciones a la vez, y con el canal parado.

**Mientras tanto (sin código, lo decide Isaac):** S-6665004459 sigue en reintentos (retry 1 de 5). Tiene más
opciones de entrar en un rato sin PDA ni crons moviendo stock (descanso o al acabar el turno). Desde aquí no se
reencola ni se toca nada.

## 5. Qué probar en real cuando esté instalado

- Un pedido de tienda pequeño: entra igual que hoy (un solo job).
- El primer pedido Zalando grande: tres jobs seguidos en Cola de trabajos, la OUT pasa a Preparada en 1-2 min y no
  la cancela agrupaciones_web.
- Una PDA preparando a la vez que entra un pedido grande: sin «Sesión expirada» ni errores.

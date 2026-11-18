# Agrupaciones web por corte horario: diseño (18/11/2026)

Petición de Isaac:
- 13/11: «cancelar los pedidos de web que no estén al 100% reserva y pasar informe estado cancelado directamente»
  y «oleadas de 100 uds, corte a las 11:00».
- 18/11: «Que se haga una agrupación tal y como llegan: a las 6 de la mañana, por ejemplo, y otra a las 10 de la
  mañana. Y que solo coja las que están al 100% reservadas. Añade también un filtro para filtrar por esto.»

Estado: **diseño, sin código.** Espera el visto bueno y la respuesta a las preguntas del final.

## Lo que hay hoy (leído en código y en datos, solo lectura)

- **Las agrupaciones web se hacen a mano.** La oficina crea `WEB_ddmmaa_NN` (usuario «Almacén Nath»), dos o tres al día:
  la primera hacia las 6:15-8:00 y otra hacia las 11:30-16:00. Del 2 al 18/11: entre 17 y 108 OUT y entre 31 y 200 uds
  por agrupación. Hay restos vacíos (`WEB_091126_01`, `WEB_171126_03`).
- **Se preparan con PedidosMultiples** (el programa del PC), que acepta los lotes que empiezan por `WEB_`
  (`PedidosMultiples/InitialForm.cs:932`). La PDA (koroshi_preparacion) no las trata: solo trata las `Z-`.
  Por eso el nombre tiene que seguir siendo `WEB_ddmmaa_NN`.
- **Ningún módulo ni cron crea agrupaciones web.** Los scripts sueltos (`odoo/KOROSHI_crear_oleadas.py`,
  `KOROSHI_crear_agrupaciones_OUT.py`) son para tiendas.
- **Cómo se reconoce un pedido web**: `origin` empieza por `W-` y el tipo de pedido es `PED. ONLINE`
  (`s_order_type_id` 3). Zalando y About You son `PED. MARKETPLACE` (id 1, origen `S-66…`); tiendas, `PED. TIENDAS`
  (id 38). Se filtra por `W-` **y** tipo distinto de MARKETPLACE: así Zalando no puede entrar nunca.
- **Volumen**: unas 90-120 OUT web al día (~180-200 uds); llegan repartidas por todo el día y la noche (importación
  cada hora en punto). Se cancelan a mano unas 17-23 al día (≈18 %): son justo las que se quedan sin agrupación.

## Qué es «100 % reservada»

**«Preparada» no basta.** Todas las OUT web tienen `move_type = 'direct'` (1.689 de 1.689 desde el 01/11): con eso, Odoo
13 pone la OUT en «Preparada» en cuanto hay **una** línea reservada. Ejemplo real de hoy: `EFFEC/OUT/26287`
(W-0000059271) está Preparada con 2 de 3 líneas reservadas; `EFFEC/OUT/26415` igual, con 3 de 4.

Regla que propongo: **OUT en «Preparada» y ningún movimiento en «En espera», «Esperando otra operación» o «Parcialmente
disponible»** (los movimientos cancelados no cuentan). En Odoo 13 un movimiento «Reservado» (`assigned`) lo está del todo.

Como filtro de búsqueda, **sin campo nuevo en `stock.picking`** (regla 7):

```
[('state', '=', 'assigned'),
 '!', ('move_lines.state', 'in', ['confirmed', 'waiting', 'partially_available'])]
```

y el filtro contrario, «Reserva incompleta», para ver de un vistazo las que se quedarán fuera.

## Propuesta

Un **módulo nuevo, `koroshi_agrupaciones_web`** (depende de `stock_picking_batch` y `koroshi_base`). No se toca
koroshi_preparacion ni nada que use la PDA, y no añade campos a tablas compartidas.

1. **Cortes configurables**: parámetro `koroshi_agrupaciones_web.cortes` = `06:00,10:00` (hora del almacén, con
   `comun.ahora_local()`). Un cron cada 15 min mira si ha pasado un corte de hoy que aún no se ha hecho (se apunta en
   `koroshi_agrupaciones_web.ultimo_corte`), como hace `koroshi_informe` con `hora_diario`. Si el servidor estaba parado
   a las 6:00, el corte se hace en cuanto vuelve (y solo una vez).
2. **Qué coge cada corte**: OUT web (`W-`, no MARKETPLACE) de la compañía 8, 100 % reservadas, **sin agrupación**,
   creadas antes de la hora del corte. Las que no entraron a las 6:00 porque les faltaba reserva entran a las 10:00 si
   ya la tienen.
3. **Orden de llegada**: por fecha de creación de la OUT (y por nombre si empatan).
4. **Tope por agrupación**: parámetro `koroshi_agrupaciones_web.tope_uds` = 100. Se van metiendo OUT en orden hasta que
   la siguiente pasaría de 100 uds; entonces se abre la siguiente (`_02`, `_03`…). Una OUT nunca se parte. Una OUT sola
   de más de 100 uds va en su propia agrupación. (Ver pregunta 1.)
5. **Nombre y estado**: `WEB_ddmmaa_NN`, siguiendo la numeración que ya haya ese día (si la oficina ya hizo la `_01`, el
   cron hace la `_02`). Se deja «En curso», como las que hace la oficina, sin volver a reservar.
6. **Botón en la lista de OUT**: «Agrupar web ahora (simulación)» y «Agrupar web ahora». La simulación enseña qué
   agrupaciones haría y qué OUT se quedan fuera y por qué (reserva incompleta, ya agrupada, Zalando), sin crear nada.
7. **Interruptor**: parámetro `koroshi_agrupaciones_web.activo` = `0` al instalar. Se instala apagado, se mira la
   simulación una mañana y se enciende cuando Isaac diga.
8. **Filtros** en la búsqueda de albaranes: «100 % reservada», «Reserva incompleta» y «Web sin agrupar».

## Lo que NO hace (decisión aparte)

**Cancelar las no reservadas e informar a S4T**: no entra en esta versión. Cancelar una OUT web y mandar «cancelado» a
S4T no tiene vuelta atrás para el cliente final. Hoy la oficina ya cancela unas 20 al día a mano. Si se quiere
automatizar, propongo una segunda fase: en cada corte, una **lista** (o correo) de las web con reserva incompleta desde
hace más de N horas, y el botón de cancelar a mano. Nunca Zalando.

## Preguntas para Isaac

1. **¿100 unidades o 100 pedidos?** El 13/11 dijiste «100 uds», pero las agrupaciones que hace la oficina rondan las
   50-100 OUT (`WEB_161126_01` y `_02`: 100 OUT cada una, ~175 uds). Con 100 uds saldrían 2-3 agrupaciones de ~55 OUT por
   corte. ¿Y si a un corte le sobra, se hacen varias agrupaciones o el resto espera al corte siguiente?
2. **¿Cortes a las 6:00 y 10:00, o 6:00 y 11:00?** (el 13/11 dijiste corte a las 11:00).
3. **¿Lo deja en «En curso» o en borrador** para que la oficina lo revise antes?
4. **¿Módulo nuevo `koroshi_agrupaciones_web`** (propuesto) o dentro de otro módulo?
5. Cancelar las no reservadas: ¿lo dejamos para una segunda fase como arriba?

## Cómo se probaría

- Simulación en el servidor sobre las OUT reales (no crea nada) y comparar con lo que hizo la oficina ese día.
- Instalado con el interruptor apagado; encenderlo un día y comprobar que la `WEB_…` de las 6:00 sale en
  PedidosMultiples igual que una hecha a mano.
- En PDA real: nada (no la toca).

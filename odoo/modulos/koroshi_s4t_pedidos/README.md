# KOROSHI Pedidos S4T grandes

Hace que los pedidos S4T grandes (Zalando, ~330 líneas) entren en Odoo sin «could not serialize access due to
concurrent update». No toca el módulo de Effective (`api_s4t_batch_update_PROD`) y no añade campos.

Diseño: `bin/versiones/diseno-feed-s4t-sin-serialize_2026-11-19_v2.md`.

## Qué hace

| Paso | Job (canal `root.s4t_sync`) | Qué guarda | Si falla |
|---|---|---|---|
| 1 | `S4T Create sale.order from feed …` (el de Effective) | El pedido en **presupuesto** y el feed en `done` | Como antes: feed en error y reintentos |
| 2 | `S4T Confirmar pedido S-…` | Pedido confirmado y OUT **sin reservar** | El pedido sigue en presupuesto; el cron 192 v7 avisa |
| 3 | `S4T Reservar OUT S-…` | Reserva por bloques de 50 movimientos, un commit por bloque | Lo reservado se queda; el resto, como una OUT con falta de stock |

- Los pasos 2 y 3 solo se hacen en pedidos **b2b** con `koroshi_s4t_pedidos.umbral_lineas` líneas o más (60 si no
  existe el parámetro). Los pedidos de tienda pequeños y los web entran igual que antes, en un solo job.
- **Candado por feed y por pedido** (`pg_advisory_lock`, claves en `logica.py`): nunca corren dos copias del mismo
  job a la vez. La segunda no hace nada y se vuelve a mirar en 5 min. Si el feed ya tiene pedido, el job acaba bien.
- Commit al acabar cada paso (y cada bloque): lo hecho no se pierde si después choca la escritura de queue_job.

## Parámetros (Ajustes › Técnico › Parámetros del sistema; no hace falta crearlos)

- `koroshi_s4t_pedidos.umbral_lineas`: 60. **0 = apagado**: todos los pedidos como antes, quedando solo el
  candado.
- `koroshi_s4t_pedidos.bloque_reserva`: 50.

## Dónde mirar

- Cola de trabajos, canal `root.s4t_sync`: los tres jobs y su resultado («S-… confirmado sin reservar en N s…»,
  «S-… reservado en N s: … movimientos…»).
- Log del servidor: líneas `KOROSHI S4T:`.

## Pruebas sin Odoo

```
python odoo/modulos/koroshi_s4t_pedidos/pruebas/test_logica.py
python odoo/modulos/koroshi_s4t_pedidos/pruebas/test_comun_jobs.py
```

## v1.1.0: reserva de las tiendas por prioridad

Que el stock reservado de las tiendas siga el mismo orden que el Monitor y que zonas: **número de pedido S4T, el más
bajo primero**. Diseño: `bin/versiones/diseno-reserva-tiendas-por-prioridad_2026-11-23.md`.

- **Cuándo:** cron «KOROSHI S4T: reserva de tiendas por prioridad» a las 03:30 UTC (20 min antes de que zonas parta)
  y a mano en Inventario › Informes › Reserva tiendas por prioridad › Repartir ahora.
- **Qué OUT:** PED. TIENDAS en Esperando/Preparada que nadie ha empezado (sin unidades leídas, sin cajas, sin lote
  que no sea la agrupación `TIENDA…`, sin puesto de operario, fuera del SORTER). Las ya partidas por zonas (lote Z-)
  no entran. Nunca Zalando, About ni web.
- **Qué hace:** solo en los artículos en disputa (a una le falta y otra de número más alto tiene). Quita la reserva de
  esos movimientos y vuelve a reservar uno a uno en orden. Un savepoint por artículo: si falla, ese artículo queda como
  estaba.
- **Modo** (`koroshi_s4t_pedidos.prioridad_modo`): `simular` (por defecto: lo hace y lo deshace, solo deja el informe),
  `real` o `apagado`. Un valor mal escrito cuenta como `simular`.
- **Informe:** cada ejecución con las OUT y artículos que ganan (verde) o pierden (rojo) unidades, las OUT saltadas y
  cuánto tardó.

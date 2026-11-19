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

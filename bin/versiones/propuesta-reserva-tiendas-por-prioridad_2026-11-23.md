# Propuesta: reservar el stock de las tiendas por prioridad (nº de pedido S4T) — 23/11/2026

Petición de Isaac (23/11): «que el stock reservat vaigue tmb en esta prioritat» (la misma que «Cada tienda en cada
zona» del Monitor: número de pedido S4T, S-6665…, el más bajo primero).

## Dónde se reserva hoy (solo leído, sin tocar nada)

| Quién | Dónde | En qué orden |
|---|---|---|
| Pedidos S4T grandes (≥ 60 líneas) | `koroshi_s4t_pedidos/models/sale_order.py:74-95` (job «S4T Reservar OUT», bloques de 50) | Cada pedido por su cuenta, movimientos por id. Entre pedidos, el orden en que llegan los jobs |
| Pedidos pequeños (las tiendas casi siempre) | Reserva estándar de Odoo al confirmar el pedido que baja de S4T | El orden de llegada de S4T (≈ orden de número, porque S4T numera al crear) |
| Stock que entra después (recepción, ajuste) | Reserva estándar de Odoo (planificador / «Comprobar disponibilidad») | El de Odoo (prioridad y fecha prevista; sin verificar en el servidor), **no** por número de pedido |
| `koroshi_zonas` | No reserva: solo trocea lo ya reservado (`models/escritor.py:97`) | Ya ordena por número de pedido para la ronda y las cajas |

Ningún proceso ordena la reserva por número de pedido. Cuando hay stock para todos no importa; importa cuando una
referencia no llega para todas las tiendas: hoy se la queda quien confirmó o reservó antes, no el número más bajo.

## Propuesta

Un paso «Repartir la reserva por prioridad», solo para **OUT de tienda (PED. TIENDAS) sin nada leído**:

1. Coge las OUT de tienda abiertas, sin lecturas ni cajas (nunca las que alguien ya está preparando).
2. Por cada artículo que no llega para todas: quita la reserva de esas OUT y vuelve a reservar de la más baja a la
   más alta (S-6665… ascendente).
3. Nunca toca Zalando ni web, ni las OUT ya partidas en zonas con lecturas.
4. Primero en modo SIMULAR: dice qué OUT ganarían o perderían unidades, sin cambiar nada. Isaac lo mira y, si está
   bien, se pasa a real.

Cuándo correría: a mano (botón) o justo antes de que `koroshi_zonas` parta a las 04:50, para que la ronda salga con la
reserva ya en el orden bueno.

**Sin campos nuevos** en `stock.picking` ni `stock.move.line`: el orden sale del `origin` que ya existe.

## Qué módulo y qué sesión

- No es del Monitor (que solo lee). Lo natural es `koroshi_s4t_pedidos` (ya reserva los pedidos S4T; sesión «Feed S4T
  sin serialize») o `koroshi_zonas` (parte a las 04:50 y ya ordena por pedido; sesión «Zonas: mejorar»).
- Decide Isaac cuál. Toca reservas en producción: nada sin su visto bueno y primero SIMULAR.

# Diseño: reserva de las tiendas por prioridad (nº de pedido S4T) — 23/11/2026

Estado: **PROPUESTA, sin código.** Espera el visto bueno de Isaac. Parte de
`bin/versiones/propuesta-reserva-tiendas-por-prioridad_2026-11-23.md` (sesión «Millores del Monitor picking»).

## Lo confirmado en el código (solo lectura)

- **OUT de tienda** = `sale_id.s_order_type_id.name == 'PED. TIENDAS'` (igualdad exacta, como zonas:
  `koroshi_zonas/motor/modelo.py:27`, `models/lector.py:61`). Zalando/About = 'PED. MARKETPLACE'; web = origin `W-`.
- **Número de prioridad**: `koroshi_zonas/motor/evaluar.py:29-37` `numero_pedido('S-6665004409') → 6665004409`. Es el
  mismo orden que el Monitor (`koroshi_monitor/controllers/prioridad_calc.py:21-24`).
- **«Ya empezada»**: líneas con `qty_done > 0` (lo que escribe la PDA, `koroshi_preparacion/models/lectura.py:741`),
  líneas con caja (`result_package_id`), OUT en lote (`batch_id`) o en un puesto de operario en cola/curso/oficina
  (`koroshi.operario.asignacion`, como `koroshi_zonas/models/lector.py:71-74`).
- **Zonas** parte a las 03:50 UTC (04:50 hora local) y **no reserva**: reparte lo ya reservado moviendo las líneas a OUT
  por zona (`escritor.py:57-104`). Desreservar **después** de partir rompería sus comprobaciones (OUT de zona en
  `assigned`, lotes Z-). Por eso el reparto tiene que ir **antes** y no tocar nada ya partido.
- Ningún módulo KOROSHI desreserva hoy (solo `koroshi_faltantes` mueve o borra líneas dentro de un savepoint).

## Diseño

Va en `koroshi_s4t_pedidos` 1.1.0 (la sesión que lo lleva). **No toca koroshi_zonas** ni añade campos a tablas
compartidas: un modelo propio para el informe y dos parámetros.

### Qué OUT entran (todas a la vez)

OUT de la compañía 8, tipo salida, `PED. TIENDAS`, en estado `confirmed`/`assigned` (incluye las parciales), y que **no**
tengan: líneas leídas, cajas, lote, puesto de operario, ni estén ya partidas por zonas (OUT `-Z`/lote Z- o registro en
`koroshi.zonas.ejecucion.out`). Nunca Zalando, About ni web.

### Qué hace, artículo por artículo

1. Solo los artículos **en disputa**: alguno de esos movimientos no está reservado entero y otro con número **más alto**
   tiene reservado ese artículo. Si hay stock para todas, no se toca nada.
2. En cada artículo en disputa, **en una sola transacción**: quitar la reserva de todos esos movimientos
   (`_do_unreserve`) y volver a reservar **uno a uno del número más bajo al más alto** (`_action_assign`).
   Si algo falla, se deshace solo ese artículo: ninguna OUT se queda sin la reserva que tenía.
3. Commit por artículo (transacciones de segundos).

Lo que puede cambiar al volver a reservar: el **hueco** de donde sale una unidad (Odoo vuelve a elegir ubicación), y una
OUT de número alto puede pasar de «Preparada» a «En espera» o parcial. Eso es justo lo pedido.

### SIMULAR primero

Parámetro `koroshi_s4t_pedidos.prioridad_modo`: `simular` (por defecto) | `real` | `apagado`.
En `simular` hace exactamente lo mismo dentro de un savepoint y lo **deshace**. Guarda un informe: por artículo y OUT,
uds reservadas antes y después (quién gana y quién pierde), y cuánto tardó. Así el ensayo es el algoritmo real, no una
copia.

### Cuándo corre

- Cron nuevo a las **03:30 UTC** (04:30 hora local), 20 min antes de que zonas parta. Si a las 03:50 siguiera
  trabajando, zonas vería OUT a medio cambiar: el informe dirá cuánto tarda y, si hace falta, se adelanta.
- Botón «Repartir reserva por prioridad» en el informe, para lanzarlo a mano (avisa si hay OUT ya empezadas que no toca).

## Lo que necesito que decidas

1. ¿Va bien en `koroshi_s4t_pedidos` 1.1.0 y con el cron a las 04:30 hora local?
2. ¿A esa hora hay alguien preparando con la PDA? Las OUT empezadas no se tocan, pero conviene que no haya nadie.
3. ¿Las OUT de tienda de **días anteriores** entran también, por número como las demás, o van siempre primero?
4. Primera semana en `simular`: miras el informe y decides si se pasa a `real`.

## Qué no cambia

Los pedidos S4T grandes siguen igual (crear, confirmar y reservar por bloques). La reserva de Odoo cuando entra un
pedido o stock sigue igual. Este paso solo **reordena una vez al día** antes de partir.

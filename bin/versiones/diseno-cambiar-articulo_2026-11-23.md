# «Cambiar artículo» en Contenedores (errores de talla) — diseño v1 (23/11/2026)

**Estado: solo diseño. No hay código ni nada instalado.** Revisión general del 23/11, R23 (entrega 5). Módulo:
**koroshi_contenedores** (servidor 1.13.0; esto sería la 1.14.0). Espera el sí de Isaac (preguntas al final).

## 0. Qué pasa hoy

Lo que se dijo en el almacén (grabación 32):
- Al ubicar, se apunta una caja con una talla y dentro hay otra: «aquí puse top 34 y es top 36».
- El preparador coge la 6 en vez de la 7. Luego, en la caja de la 6 aparece una 7.
- No se puede poner a 0 si hay reservas.
- La tienda no tiene que notar el error: si un artículo sale a 0 y luego aparece, la tienda se queja.

Hoy no hay forma de decir «esto que Odoo llama A es en realidad B». Se hacen dos cosas sueltas:
1. «Cambiar» A a menos.
2. «Añadir prendas» de B.

Son dos ajustes, en dos momentos, que nadie relaciona. Si el segundo no se hace, se pierde stock. Si A está
reservado, el primero se para.

## 1. Qué ve el operario (PDA, ficha del contenedor)

1. Abre el contenedor como hoy, con su tarjeta de operario.
2. En la lista de artículos, al lado de «Cambiar», aparece un botón nuevo: **«Es otro»**.
3. Pulsa «Es otro» en la línea del artículo que dice Odoo (A).
4. La PDA pide **leer una prenda de verdad** (el EAN de B).
   - B es el mismo modelo en otra talla o color: sigue sin más.
   - B es **otro modelo**: aviso en rojo, «No es el mismo modelo (A: …, B: …). ¿Seguro?», y otro toque para seguir
     (ver pregunta 3).
   - B es igual que A: «Es el mismo artículo; si faltan uds usa Cambiar».
5. Pone **cuántas uds** son B. Por defecto, todas las de A en el contenedor; como máximo, esas.
6. Pantalla de confirmación, en grande: «**KO_241026_115: 3 uds de TOP 34 → TOP 36**». Botón «Guardar».
7. Si alguna de esas uds de A está reservada para una OUT, sale **un paso más antes de guardar**:
   - «3 uds de TOP 34 están reservadas para S-… (K12). Se buscan en otro hueco; si no hay, la OUT sale sin ellas.»
   - Para seguir hay que pulsar «Guardar» otra vez, igual que en «Cambiar» por debajo de lo reservado (v1.12).
8. Resultado: «TOP 34 pasa de 5 a 2 uds y TOP 36 de 0 a 3 en KO_…». Se añade lo que se haya pasado a Faltantes, y
   el contenedor se recarga.

No se puede hacer «Es otro» (sale un mensaje y no se cambia nada) en estos casos:
- **Hay prendas leídas sin validar** de A o de B en ese contenedor: están en un carro. Es la misma regla que «Cambiar»
  desde R2: hay que esperar a que se valide.
- **Las uds de A han cambiado desde que se abrió** el contenedor (comprobación de «antes», como en «Cambiar»).
- A tiene lote, paquete o propietario.
- Son más de MAX_ANADIR uds.

## 2. Qué movimientos de stock hace

Todo va dentro de **una sola transacción** (un savepoint): o se hace todo, o nada. El orden es este:

1. **Reservas de A que sobran** (solo si hace falta; ver apartado 4). Pasan por Faltantes con el mismo código de hoy
   (`_reservas_a_faltantes(producto=A, dejar=uds_A − N)`), que reubica o deja la OUT sin ellas.
2. **Ajuste de −N de A**: del contenedor a la ubicación de pérdidas de inventario del artículo.
3. **Ajuste de +N de B**: de pérdidas al contenedor.

Los pasos 2 y 3 usan el mismo `_ajuste` que «Poner a cero», «Añadir» y «Cambiar»: un `stock.move` hecho, probado en
producción. Odoo no tiene un movimiento «de A a B» entre dos artículos, así que son dos movimientos. Los dos llevan el
mismo nombre: «KOROSHI contenedor KO_…: A → B (operario)». Así, buscando el nombre se encuentran juntos en
Inventario › Movimientos.

En pérdidas entra N de A y sale N de B, así que el saldo de unidades queda a cero. Con el mismo modelo (mismo coste),
la valoración tampoco cambia. Si son modelos distintos con distinto coste, sí cambia; por eso el aviso del punto 4 del
apartado 1.

## 3. Qué registro deja

**Una línea** en Contenedores › Registro (`koroshi.contenedor.movimiento`), con la acción nueva **«Cambiar artículo»**
(`cambiar_articulo`):

| Campo | Valor |
|---|---|
| Artículo (`producto_id`) | A (lo que decía Odoo) |
| **Artículo real** (`producto_nuevo_id`, campo nuevo) | B |
| Uds | N |
| Movimiento de stock (`move_id`) | el de −N de A |
| **Movimiento del artículo real** (`move_nuevo_id`, campo nuevo) | el de +N de B |
| Operario, usuario, contenedor, hueco, fecha | como siempre |
| Tanda (`tanda`) | id que pone la PDA: si se corta la wifi y se reintenta, no se hace dos veces (como «Añadir», R3) |

Los dos campos nuevos van en la **tabla propia** del módulo, no en stock.picking, stock.picking.type ni
stock.move.line: no hace falta pedir permiso por la regla 7. Si alguna línea pasa a Faltantes, deja además su línea
«A Faltantes», igual que hoy.

En la vista lista del registro se añade la columna «Artículo real», y un filtro «Cambiar artículo» para ver todos los
errores de talla de un día o de un operario.

## 4. Qué pasa si hay reservas

**Reservas de A.** Sea libre = uds de A − reservadas de A en el contenedor.
- **N ≤ libre**: no se toca ninguna reserva. Solo los dos ajustes.
- **N > libre**: las OUT tienen reservadas prendas de A que en realidad son B. Lo que sobra (N − libre) pasa por
  Faltantes, como en «Cambiar» por debajo de lo reservado:
  - si hay A libre en otro hueco, la línea de la OUT se reserva allí (el más cercano, `mejor_destino`): **la tienda no
    nota nada**;
  - si no hay A en ningún hueco, la OUT sale sin esas uds (`sin_alternativa`) y queda en Faltantes para la oficina.
  - La PDA lo dice antes (paso 7 del apartado 1) y hay que volver a pulsar «Guardar».
- **No se toca nada** si la OUT ya tiene algo leído de A en ese contenedor: el mismo control que hoy.

**Reservas de B.** Las N uds de B entran **libres**. No se reserva nada solo:
- Si hay OUT esperando B (sin reservar, o con un faltante pendiente de B), la PDA lo avisa al acabar: «Hay 2 OUT
  esperando TOP 36 (S-…, S-…): ya hay stock en KO_…». La oficina o el cron de reservas las cogerán.
- No se llama a `action_assign` desde aquí: reservaría según la estrategia de Odoo, también en OUT que alguien está
  preparando, y desde la PDA no se ve qué haría. Ver pregunta 1.

## 5. Qué NO hace (de momento)

- **No cambia un artículo dentro de una OUT** («el preparador leyó la 6 y la tienda pidió la 7»). Eso es Lecturas o
  Faltantes, y es otra conversación. Lo de la grabación («el programa de faltantes, cuando sea por un error de
  talla…») podría ser un motivo «Error de talla» en Faltantes que abra esta misma pantalla. Lo dejo para después.
- No mueve prendas de un contenedor a otro: para eso está «Mover».
- No va en el backend de Odoo: solo en la PDA de Contenedores. Quien tenga Inventario sigue pudiendo hacer los dos
  ajustes a mano.

## 6. Qué se toca (cuando haya sí)

- `models/movimiento.py`: acción `cambiar_articulo` y campos `producto_nuevo_id` y `move_nuevo_id`.
- `controllers/main.py`: ruta `/koroshi/contenedores/cambiar_articulo` (contenedor, operario, A, EAN de B, N, antes,
  tanda, pasar_faltantes). Reutiliza `_ajuste`, `_leidas`, `_reservas_a_faltantes` y `_buscar_producto`.
- `logica.py` y `tests/test_logica.py`: las cuentas puras (libre, cuánto pasa a Faltantes, mismo modelo sí/no).
- `static/src/js/contenedores.js` y `xml`: botón «Es otro», lectura de B, uds y confirmaciones.
- `views/`: columna y filtro en el registro.
- Versión **1.14.0**, sin campos en tablas compartidas. Al actualizar contenedores se actualiza también
  **koroshi_menu**, que depende de él: hay que hacerlo fuera de horas.

## 7. Preguntas para Isaac

1. **B: ¿reservar solo para las OUT que lo esperan?** Mi propuesta: no, solo avisar (apartado 4). La otra opción es
   reservar B únicamente en las OUT que no ha empezado nadie, con la misma regla que la reserva por prioridad.
2. **A reservado: ¿Faltantes, como «Cambiar», o rechazar?** Mi propuesta: Faltantes (busca A en otro hueco y la tienda
   no lo nota). La otra opción es no dejar hacerlo y que lo haga un jefe.
3. **Otro modelo (no solo otra talla): ¿se deja con aviso o se prohíbe?** Mi propuesta: se deja con el aviso en rojo,
   porque también hay errores de color o de referencia. Si se prohíbe, «Es otro» solo serviría para tallas y colores
   del mismo modelo.
4. **¿Quién puede?** Mi propuesta: los mismos que hoy hacen «Cambiar» y «Poner a cero», con su tarjeta. La otra opción
   es solo jefes.
5. **¿Nombre del botón?** «Es otro» (corto para la PDA) o «Cambiar artículo».

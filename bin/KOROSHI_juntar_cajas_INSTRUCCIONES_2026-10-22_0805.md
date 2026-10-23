# Juntar cajas pequeñas en expediciones (KOROSHI)

## Para qué sirve

Cuando una tienda tiene una caja con muy pocas unidades (1, 2 o 3 uds), en expediciones se mete
dentro de otra caja **de la misma tienda y del mismo pedido**. Cada caja tiene su matrícula (CJ) y
cada CJ cuenta como un bulto en el envío. Si se juntan dos cajas y no se avisa a Odoo, el envío
saldrá con un bulto de más.

Con **Juntar** se le dice a Odoo: "las unidades de la CJ pequeña ahora están en la CJ grande".
La CJ pequeña deja de contar como bulto.

---

## Cómo se hace (almacén)

1. Abrir el pedido de la tienda en Odoo: **Ventas › Pedidos › buscar el pedido** (S-6665…).
   El número de pedido sale en la etiqueta de la caja, en el recuadro **PEDIDO**.
2. Entrar en la pestaña **Juntar cajas** (abajo, junto a las líneas del pedido).
3. Pulsar **Editar**.
4. Clic en la casilla **CJ pequeña** y **escanear la matrícula de la caja pequeña**
   (el código de barras de abajo del todo de la etiqueta, el de MATRÍCULA).
   **Si van varias cajas pequeñas a la misma caja grande, escanearlas todas seguidas en esta
   misma casilla**, sin borrar nada. Quedan pegadas (`CJ665004067CJ665003851…`) y no pasa nada:
   Odoo las separa. Si se escanea una dos veces, solo cuenta una.
5. Clic en la casilla **CJ destino (caja grande)** y **escanear la matrícula de la caja grande**,
   donde se han metido las unidades. Solo una.
   Si alguna de las pequeñas no cuadra, **no se junta ninguna**: corregir y volver a pulsar.
6. Pulsar el botón azul **Juntar** y aceptar el aviso.
7. Si todo está bien, las dos casillas se quedan vacías y en el historial del pedido (abajo
   a la derecha) aparece una nota: *"Juntar cajas: CJ… (2 uds) metida en CJ…. Bultos del pedido: 10 -> 9"*.
8. La caja pequeña **ya no es un bulto**: su etiqueta se tapa o se quita para que el transportista
   no la vea como una caja aparte.

**Antes de juntar en Odoo, la caja pequeña tiene que estar ya dentro de la grande.**

### Si sale un aviso

Odoo pone a todos los avisos de esta acción el título **"¡Algo salió mal!"**, también a la lista de
cajas pequeñas. Hay que leer el texto de dentro.

Si algo no cuadra, sale un mensaje y **no se cambia nada**. Los más normales:

| Aviso | Qué pasa | Qué hacer |
|---|---|---|
| *no son del mismo pedido* | Las dos cajas son de pedidos distintos | No juntar. Comprobar que la caja grande es de la misma tienda y pedido |
| *son del pedido S-…, no de S-…* | Se ha abierto otro pedido | Abrir el pedido que sale en la etiqueta |
| *no es una caja cerrada* | La CJ no está cerrada o está mal escaneada | Volver a escanear. Si sigue, avisar a IT |
| *está vacía (ya juntada?)* | Esa caja pequeña ya se juntó antes | Nada: ya está hecho |
| *Falta escanear la …* | Solo hay una casilla rellena | Escanear la que falta |

### Ver qué cajas pequeñas tiene un pedido

Con las dos casillas **vacías**, pulsar **Juntar**: sale la lista de cajas pequeñas del pedido
(3 uds o menos) y en qué caja grande se pueden meter. No cambia nada.

---

## Montarlo en Odoo (una sola vez, IT)

**Ya está montado (22/10/2026):** campos `x_cj_pequena` (26776) y `x_cj_destino` (26777),
acción 1844 en REAL con modelo Pedido de venta, vista 6036. Lo de abajo es por si hay que rehacerlo.

En modo desarrollador (Ajustes › Activar modo desarrollador):

1. **Casillas en el pedido.** Ajustes › Técnico › Campos › Crear, dos veces:
   - Modelo: *Pedido de venta* (sale.order) · Nombre: `x_cj_pequena` · Etiqueta: *CJ pequeña* · Tipo: *Char*
   - Modelo: *Pedido de venta* (sale.order) · Nombre: `x_cj_destino` · Etiqueta: *CJ destino (caja grande)* · Tipo: *Char*
   - En los dos: quitar *Copiado*.
2. **La acción.** Ajustes › Técnico › Acciones de servidor › **KOROSHI Juntar matriculas** (id 1844):
   - Modelo: cambiar a **Pedido de venta**.
   - Código: pegar `KOROSHI_juntar_matriculas_2026-10-22_0800_v2-desde-pedido-REAL.py` entero
     (ya va con `DIAGNOSTICO = False`, en REAL).
   - **No** pulsar "Crear acción contextual": el botón va en la pestaña.
3. **La pestaña.** Ajustes › Técnico › Vistas › Crear:
   - Nombre: `koroshi.sale.order.juntar.cajas` · Tipo: *Formulario* · Modelo: `sale.order`
   - Vista heredada: *sale.order.form* · Modo: *Extensión* · Prioridad: 99
   - Arquitectura: pegar `KOROSHI_vista_pedido_juntar_cajas_2026-10-22_0805.xml`.
   - Si la acción no es la 1844, cambiar `name="1844"` del botón por su id.
4. Probar con un pedido: dejar las casillas vacías y pulsar **Juntar** (solo enseña la lista).

## Para deshacer una junta

En Ajustes › Técnico › Registro está la línea *KOROSHI JUNTAR MATRICULAS - HECHO* con las líneas y
quants que se han movido (*Movido (para deshacer)*). Volviendo a poner la CJ pequeña en esas
líneas (`result_package_id`) y quants (`package_id`) queda como estaba. Avisar a IT.

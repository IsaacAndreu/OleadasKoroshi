# KOROSHI KPI (Odoo 13)

KPI diarios del almacén KOROSHI (Effective Logistics, empresa 8), con los datos que pidió el jefe el 21/10:
uds totales, profundidad por SKU, peso y volumen (total y por ud), metros recorridos (total y por ud),
horas y personas de cada fase, y **segundos por prenda** de picking (andando y leyendo), packing y expedición.

- Menú: **Inventario › KOROSHI KPI › KPI por día** (lista agrupada por semana con totales, formulario, tabla dinámica y gráfico)
  y **Pesos y litros por tipo**.
- Solo escribe en sus tablas (`koroshi.kpi.dia`, `koroshi.kpi.peso.tipo`): no toca albaranes, stock ni productos.

## De dónde sale cada dato

| Dato | Cómo |
|---|---|
| Uds, líneas, SKU, pedidos, OUT, cajas | Líneas con cantidad hecha de las OUT de `PED. TIENDAS` cuyas cajas (matrícula CJ) se cerraron ese día; sin caja, las de OUT validadas ese día |
| Profundidad por SKU | Uds ÷ SKU distintos |
| Volumen | `volume` del producto (m³) o, si no tiene, los litros de su tipo |
| Peso | Gramos de su tipo (tabla **estimada**: pesar 10 prendas de cada tipo y corregir) |
| Tipo de prenda | Letras 5 y 6 de la referencia o del nombre (`2421JA14-…` = JA) |
| Metros | Recorrido por el plano de la nave de cada OUT (o de cada INT de oleada), saliendo y volviendo a expediciones; en agrupaciones de zona `Z-`, solo del primer al último hueco |
| Personas y horas | **A mano** en la ficha del día (picking, packing, expedición) |
| Andando / leyendo | Andando = metros ÷ velocidad (1 m/s por defecto); leyendo = horas de picking − andando |
| s/ud | Horas-persona de la fase × 3.600 ÷ uds; el total es la suma de las tres fases |

Cada noche (23:30) se crea la ficha del día y se recalculan hoy y ayer. Botón **Recalcular de Odoo** para hacerlo al momento.

## Faltas por día (v1.3)

**Inventario › KOROSHI KPI › Faltas por día**: lo que piden los pedidos de tienda y no se ha cogido, una línea por
OUT, artículo y motivo (lo mismo que sale abajo del todo en el Monitor picking, pero guardado por día). Lista agrupada
por día y OUT con el total de uds, tabla dinámica (día × motivo) y gráfico.

- OUT del día: las de `PED. TIENDAS` creadas ese día que no son pedido pendiente de otra. Lo que queda en sus
  pedidos pendientes (backorders) cuenta en la OUT de origen, así no sale como trabajo de otro día.
- Motivos: **Sin stock** (no está reservado), **No cogido** (había stock pero no se cogió; solo en OUT parciales
  o validadas), **En pedido pendiente** (ya validada: quedó en su backorder) y **No servido** (validada sin pendiente).
- Se saca con el botón Recalcular de la ficha del día completo, cada noche (hoy y ayer) y con el menú
  **Recalcular faltas de hoy**. Solo escribe en `koroshi.kpi.falta`.

## Hoja de carga XPO (v1.4)

**Inventario › Informes › Hoja de carga XPO de hoy** descarga un Excel con las OUT que tienen etiqueta XPO generada
hoy, agrupadas por **delegación**: tiendas, pedidos, uds, bultos y **palets** (bultos ÷ cajas por palet, redondeando
hacia arriba; 16 por defecto, en una celda amarilla que se puede cambiar). Hoja «Detalle» con una línea por pedido.
También desde la lista de albaranes: seleccionar las OUT › Acción › **KOROSHI Hoja de carga XPO**.
Avisa de OUT con bultos negativos y de pedidos sin etiqueta. Las tiendas sin delegación van solas. Solo lee.

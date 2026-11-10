# KOROSHI Caja existente (v1.3, 10/11/2026)

v1.3: con la caja de **otra OUT del mismo pedido y tienda** (validada o no) las prendas van a esa caja y la OUT
pequeña **se valida como siempre, con 0 bultos**. Ya no se cancela ninguna OUT ni se pasan unidades de una OUT
a otra: la v1.1/v1.2 cancelaba la OUT pequeña y una OUT cancelada en el pedido bloquea el sync S4T
(«tiene transferencias en diferentes estados»).

v1.2: el número de bultos de la OUT pequeña se corrige también cuando la validación de la PDA lo escribe después.

Meter prendas en una caja CJ que ya existe desde la PDA, sin crear otra caja con la misma matrícula, y meter las
prendas de una OUT pequeña en la caja de otra OUT de la misma tienda y pedido sin tener que «Juntar cajas».

## Qué pasaba

- En la PDA, el botón de caja abre el diálogo «Nombre del Paquete» del módulo `stock_barcode_optimization`
  (Brain Station, `/opt/nath-erp/nath/custom_addons`).
- Al pulsar *Create* llama a `stock.picking.put_in_pack(package_name=...)`, que siempre crea una caja nueva
  y le pone el nombre leído.
- Con una matrícula ya usada salía una caja duplicada. Desde el 30/10 la acción automática 20 lo bloquea.
- Las OUT pequeñas (1-3 uds, muchas de zona ZX) tenían que ir en su propia caja y luego, en expediciones,
  «Juntar cajas» desde el pedido (acción 1844), que deja una caja vacía de más.

## Qué hace

Antes de llamar al método de Brain Station, si el nombre es `CJ` + 9 números, la OUT es de EFFEC y esa matrícula
ya existe:

| La caja es...                                                | Resultado                                                                 |
|--------------------------------------------------------------|---------------------------------------------------------------------------|
| de esta OUT, sin validar                                     | las uds leídas sin caja entran en esa caja; nota en la OUT                |
| de esta OUT y ya lleva prendas de una OUT pequeña validada   | igual: se puede seguir llenando                                           |
| de **otra OUT** del mismo pedido y tienda (validada o no)    | las uds leídas van a esa caja. Se valida la OUT pequeña: **0 bultos**     |
| de otra OUT de otro pedido u otra tienda                     | error «La caja CJ... es de la OUT X (tienda, pedido)»; no cambia nada     |
| de una OUT cancelada                                         | error; no cambia nada                                                     |
| con stock en el almacén (no enviada)                         | error; no cambia nada                                                     |
| repetida en 2 o más cajas                                    | error; no cambia nada                                                     |

- La caja «es» de la OUT que la usó primero (la línea más antigua). Esa OUT la cuenta como bulto; las demás no.
  Lo mismo hace el monitor (v1.18.2).
- Las líneas con menos uds leídas que reservadas se parten igual que hace Odoo: lo leído va a la caja, el resto
  se queda sin caja.
- No se cancela ni se borra nada. Cada OUT sigue en su pedido y en su agrupación.
- Si la matrícula no existe, o no es una OUT de EFFEC: igual que antes (caja nueva con ese nombre).
- No añade campos a ninguna tabla ni cambia la acción automática 20, la app de código de barras ni las
  agrupaciones.
- Log: `KOROSHI CAJA EXISTENTE` en el log del servidor y notas en el chatter de las dos OUT.

## Para almacén

> **OUT pequeña de una tienda (1-3 uds)**
> 1. La OUT grande de esa tienda tiene que tener **ya su caja hecha** (al menos una prenda dentro).
> 2. Abrid la OUT pequeña y leed las prendas en la PDA como siempre.
> 3. Botón de caja y, en vez de una matrícula nueva, leed la **matrícula de la caja de la OUT grande**
>    (la etiqueta pone la misma tienda y el mismo PEDIDO).
> 4. Meted las prendas en esa caja y **validad la OUT pequeña** como siempre. Sale con 0 bultos.
> 5. La etiqueta de la OUT pequeña no se usa: tiradla.
>
> Da igual que la OUT grande esté validada o no. Si no lo está, se sigue trabajando normal y se puede volver a
> leer su caja para meter más prendas.
>
> Si sale «es de la OUT ... de otro pedido» la caja es de otra tienda o pedido: leed otra.

## Prueba (fuera de horas)

1. OUT de prueba A de EFFEC: leer 2 prendas, botón de caja, matrícula CJ nueva. Sale la caja nueva como siempre.
2. Leer 1 prenda más en A y la **misma** matrícula: queda en la misma caja, nota «Caja existente CJ...: añadidas 1 uds».
3. OUT B del **mismo pedido**, A **sin validar**: leer 1 prenda en B y la matrícula de A. Validar B: bultos = 0.
4. Volver a A: leer 1 prenda más y la misma matrícula (ahora con la prenda de B ya en Clientes): entra. Validar A:
   bultos = 1. Inventario > Paquetes: la caja tiene las prendas de A y de B.
5. Igual que el 3 pero con A ya validada: B valida bien con 0 bultos.
6. OUT de otro pedido: leer la matrícula de A → «La caja CJ... es de la OUT ... no es del mismo pedido».
7. Pedido de venta: las uds entregadas cuadran y ninguna OUT está cancelada. Monitor: bultos A = 1, B = 0.

Si algo falla: volver a instalar la v1.2 (`bin/20261110_koroshi_caja_existente_v1.2.zip`) o desinstalar el módulo
en Aplicaciones. No deja datos propios.

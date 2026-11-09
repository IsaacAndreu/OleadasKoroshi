# KOROSHI Caja existente (v1.0, 09/11/2026)

Añadir prendas a una caja CJ que ya existe desde la PDA, sin crear otra caja con la misma matrícula.

## Qué pasaba

- En la PDA, el botón de caja abre el diálogo «Nombre del Paquete» del módulo `stock_barcode_optimization`
  (Brain Station, `/opt/nath-erp/nath/custom_addons`).
- Al pulsar *Create* llama a `stock.picking.put_in_pack(package_name=...)`, que siempre crea una caja nueva
  (`super().put_in_pack()`) y le pone el nombre leído.
- Con una matrícula ya usada salía una caja duplicada. Desde el 30/10 la acción automática 20 lo bloquea, así que
  no había forma de añadir prendas a una caja ya hecha desde la PDA.

## Qué hace

Antes de llamar al método de Brain Station, si el nombre es `CJ` + 9 números, la OUT es de EFFEC y esa matrícula
ya existe:

| La caja es...                    | Resultado                                                              |
|----------------------------------|------------------------------------------------------------------------|
| de esta OUT, sin validar         | las uds leídas sin caja entran en esa caja; nota en la OUT             |
| de otra OUT                      | error «La caja CJ... es de la OUT X (tienda)»; no cambia nada          |
| con stock (ya enviada/ubicada)   | error; no cambia nada                                                  |
| repetida en 2 o más cajas        | error; no cambia nada                                                  |

- Las líneas con menos uds leídas que reservadas se parten igual que hace Odoo: lo leído entra en la caja y el
  resto queda sin caja.
- Si la matrícula no existe, o no es una OUT de EFFEC: igual que antes (caja nueva con ese nombre).
- No añade campos a ninguna tabla ni cambia la acción automática 20, la app de código de barras ni las
  agrupaciones (procesar agrupación tiene su propio `put_in_pack` sin nombre).
- Log: `KOROSHI CAJA EXISTENTE` en el log del servidor y nota en el chatter de la OUT.

## Prueba (fuera de horas)

1. En una OUT de prueba de EFFEC, desde la PDA: leer 2 prendas, botón de caja, leer una matrícula CJ nueva.
   Sale la caja nueva como siempre.
2. Leer 1 prenda más, botón de caja, leer **la misma** matrícula. Tiene que quedar en la misma caja, sin error,
   y en la OUT la nota «Caja existente CJ...: añadidas 1 uds».
3. Comprobar en Inventario > Paquetes que solo hay una caja con esa matrícula y que tiene 3 prendas.
4. En otra OUT, leer una prenda y la matrícula del paso 1: tiene que salir «La caja CJ... es de la OUT ...».
5. Validar la OUT de prueba: bultos = 1.

Si algo falla: desinstalar el módulo en Aplicaciones. No deja datos propios.

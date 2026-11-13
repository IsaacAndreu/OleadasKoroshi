# Inversa KOROSHI · Lectura de matrículas por operario (propuesta de diseño)

12/11/2026 17:05 · Propuesta para Isaac. **No hay nada instalado ni programado todavía.**

## Qué queremos saber

- Cajas (matrículas) por operario y día.
- Tiempo de cada caja.
- Uds de cada caja, **sacadas del teórico de la matrícula**: el operario no cuenta ni lee unidades.

## Cómo se trabaja en la mesa

- 4 estaciones, cada una con ~8 palets y 1 operario (reparto de palets en el informe del teórico: JA ×3, PT, TR, ML, Resto de prendas, Accesorios y calzado).
- Con 10.000 uds/día y ~17 uds por matrícula salen **~580 matrículas al día, ~145 por estación**: una cada ~3,3 minutos por operario.

## Flujo en la PDA (pantalla Lecturas de siempre)

1. **Estación.** Al empezar el turno se lee una vez la etiqueta de la estación (`INV-E1` … `INV-E4`, se imprimen). La PDA se queda en *modo inversa* para esa estación hasta «Salir». Así no hace falta tocar nada a los usuarios ni a los operarios de la preparación.
2. **Tarjeta.** El operario lee su tarjeta, igual que en la preparación (`hr.employee`, código OP…).
3. **Matrícula.** Cada vez que abre una caja lee su matrícula (CJ + 9 cifras).
   - Se cierra la caja anterior (fin = ahora) y empieza la nueva.
   - En grande: matrícula, **uds del teórico** y familias de la caja con su palet. Por ejemplo: «CJ080000717 · 20 uds · SU 6 → RESTO · TR 14 → TR».
   - Si la matrícula aún no tiene teórico, se apunta igual («sin teórico») y las uds se rellenan solas cuando se importe.
   - Si ya la había leído alguien, sale un aviso («la abrió Ana a las 10:42») y no cuenta dos veces.
4. **Pausa / Salir.** «Pausa» cierra la caja que está abierta (para el almuerzo o para ir a cambiar un palet sin que cuente como tiempo de caja). «Salir» hace lo mismo y suelta al operario.
5. A medianoche lo que siga abierto queda «sin cerrar» y no cuenta para el tiempo (igual que las tareas de `koroshi_operarios`).

**Tiempo de una caja** = desde que se lee su matrícula hasta que se lee la siguiente (o «Pausa»/«Salir»). Es la única lectura que hace el operario, así que no le añadimos trabajo.

## Qué se reutiliza y qué es nuevo

| Pieza | Reutiliza | Nuevo |
|---|---|---|
| Operarios y tarjetas | `hr.employee` + tarjetas de `koroshi_operarios` | — |
| Pantalla | Lecturas (acción de cliente de `koroshi_operarios` / `koroshi_preparacion`) | un *modo inversa* que se activa con la etiqueta de estación |
| Teórico | `s4t.matricula` / `s4t.matricula.line` (Excel «EAN \| CAJA») | solo se lee |
| Registro | — | tabla `koroshi.inversa.caja` (módulo nuevo `koroshi_inversa`) |
| Informes | mismo estilo que Tareas/Productividad | cajas, uds, minutos, cajas/h y uds/h por operario, estación y día; también en el correo diario de las 17:00 |

Propuesta de módulo: **`koroshi_inversa` v1.0**, depende de `koroshi_operarios`.

- Tabla `koroshi.inversa.caja`: operario, estación, matrícula (texto), enlace a `s4t.matricula` (por nombre), inicio, fin, minutos, uds teóricas, SKU, familias («JA 8 · TR 4»), estado (abierta / cerrada / sin cerrar), cómo se cerró (siguiente caja / pausa / salir / medianoche), día.
- Ruta `/koroshi/inversa/leer` y una extensión del JS de Lecturas (`include`) para el modo inversa. **No cambia el código de `koroshi_operarios` ni de `koroshi_preparacion`.**
- Solo escribe en su propia tabla. No toca albaranes, movimientos, quants ni tipos de operación; no añade campos a tablas compartidas. Así no se repite lo del 03/11 (campo en `stock.picking.type` que tumbó la PDA).
- Cron cada 5 min: rellena las uds de las cajas «sin teórico» cuando ya existe la matrícula importada. A medianoche: «sin cerrar».

## Cuidado: las matrículas de tienda también son CJ + 9 cifras

En la preparación, leer una CJ **cierra la caja de la OUT**. Las matrículas de tienda tienen el mismo formato:

- Nuestras cajas de salida: `CJ665…` (665 = almacén 6665). Hay 23.045 en Odoo.
- Matrículas de tienda en `s4t.matricula`: `CJ080…` (K80), `CJ065…` (K65). Ninguna coincide con un paquete de Odoo.

Por eso el modo inversa va por estación: en una PDA de inversa, cualquier CJ es una matrícula y nunca se mira la OUT. Además, si en modo inversa se lee una `CJ665…`, saldrá un aviso: «Esta es una caja nuestra de salida, no de tienda».

## Lo que hay que decidir

1. **¿Dónde estará el teórico de las matrículas del lunes?** En Odoo solo existe `s4t.matricula` (67 cajas de julio y agosto, todas en *error* al mandarlas a S4T porque falta «almacen»). Hay que confirmarlo con Betty. Si llega por otro sitio (packing list, IN, Excel distinto), solo cambia la búsqueda del teórico.
2. **¿Cómo entra la PDA en modo inversa?** Recomiendo la etiqueta de estación. La otra opción es una lista de operarios en un parámetro, pero entonces no sabríamos la estación.
3. **¿El tiempo de caja va hasta la siguiente matrícula?** Es lo que recomiendo, porque no añade lecturas. La otra opción es un botón «Caja vacía»: da tiempos más exactos, pero es un toque más por caja.
4. **¿Enseñar el palet de destino de cada familia?** Ayuda a la operaria nueva. Necesita la tabla familia → destino (la del informe, como parámetro).

## Siguiente paso

Si te parece bien, preparo `koroshi_inversa` v1.0 en `odoo/modulos/` y el ZIP en `bin/` con fecha. Lo probamos primero en una PDA, con mis matrículas de prueba sobre las 67 que ya existen. No se instala en producción hasta que lo pidas.

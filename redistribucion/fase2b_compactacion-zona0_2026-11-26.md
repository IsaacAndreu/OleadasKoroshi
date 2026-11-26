# Compactación de la zona 0 (26/11/2026)

**Estado: propuesta para revisar.** Sale de `python programa.py compactar-0`, que no se conecta a Odoo. Datos:
- copia de Odoo del 23/11 a las 17:07;
- litros por unidad del MASTER v14 (24/11).

Todo el detalle está en el Excel `compactacion-zona0_20261126_0836.xlsx`, en esta misma carpeta.

## Cómo se clasifica cada modelo-color de la zona 0

| Dato | Cómo |
|---|---|
| Rotación (ABC) | Por **líneas** de salida en 28 días (albarán–producto de las órdenes de entrega), no por unidades. Así cuenta la profundidad: un artículo con 400 uds da muchas más líneas que uno con 10. A = hasta el 80 % de las líneas; B = hasta el 95 %; C = el resto. |
| Profundidad | Unidades en la nave y unidades por talla |
| Tamaño | Unidades que caben en una caja de 84 L (confirmado por Isaac el 26/11; los 93 L del MASTER son la caja de 60×36×42 cm del PL, por fuera). Reglas del MASTER v7: grande si caben menos de 15; pequeño si caben más de 40 |
| Litros | Del packing list del MASTER en 549 de 562 modelos-color; los otros 13, de la copia |

| ABC | Tamaño | Modelos-color | Líneas | Uds en nave | m³ |
|---|---|---|---|---|---|
| A | pequeño | 12 | 1.688 | 3.544 | 6 |
| A | mediano | 127 | 24.587 | 43.272 | 173 |
| A | grande | 133 | 31.960 | 70.737 | 753 |
| B | pequeño | 40 | 2.687 | 5.909 | 8 |
| B | mediano | 85 | 6.588 | 15.364 | 52 |
| B | grande | 22 | 1.747 | 3.575 | 26 |
| C | pequeño | 64 | 1.730 | 4.636 | 6 |
| C | mediano | 50 | 1.363 | 4.212 | 13 |
| C | grande | 19 | 562 | 4.115 | 34 |
| Sin salidas | mediano | 10 | 0 | 8.814 | 27 |

El grupo «A grande» (sobre todo chaquetas) concentra el 44 % de las líneas y el 73 % del volumen.

## Reglas de la compactación (criterios de Isaac del 26/11)

- Se vacían los huecos de la zona 0 llenos a menos de la mitad. Sus cajas van a otros huecos de la zona 0 del mismo
  lineal o de hasta 2 lineales más allá.
- **En un hueco compartido, modelos lo más distintos posible:** se prefiere otra familia y otro color, para que el
  picker vea enseguida cuál busca.
- **El mismo artículo no se mezcla:** nunca dos colores del mismo modelo en un hueco. Las cajas del mismo
  modelo-color de un hueco van juntas al mismo destino. Si ese destino ya tiene el mismo modelo-color, mejor: así se
  junta lo suyo.
- **Restos de talla al fondo:** una talla es resto si tiene ≤ 2 uds o ≤ 5 % de la talla más fuerte del modelo-color
  (el ejemplo de Isaac: 50 de la L y 2 de la XS). Los restos y lo de clase C o sin salidas van al destino más lejano.
  Lo de clase A va al más cercano, y solo a C1–C2.
- Un hueco solo cuenta como liberado si caben todas sus cajas. Ningún destino pasa del 90 %.
- **Orden por beneficio:** primero los huecos que se vacían moviendo menos cajas.
- Los huecos que tienen algo de Z no se vacían.

## Resultado

| | |
|---|---|
| Huecos de zona 0 con stock | 3.329 |
| **Huecos que se liberan** | **1.216 (36,5 %)** |
| Posiciones de suelo con zona 0 | 2.042 |
| **Posiciones que quedan vacías del todo** | **517 (25 %)** |
| Cajas a mover | 2.524 |
| Unidades a mover | 32.756 |
| Cajas medio vacías del mismo modelo-color que después se pueden juntar | 361 |

**El beneficio se concentra al principio** (hoja «Huecos liberados»):

| Huecos liberados | Uds movidas (acumulado) |
|---|---|
| 100 | 957 |
| 300 | 2.694 |
| 600 | 8.843 |
| 900 | 18.695 |
| 1.216 | 32.756 |

Con menos de 3.000 uds movidas ya se liberan 300 huecos. Encaja con la estimación de Isaac: liberar un 30–40 % del
suelo de la 0.

## Paso 0: cajas a 0 en Odoo (añadido el 26/11 a las 11:57)

En la foto de L67 P16 del 26/11 hay cajas que siguen en el palé y que en Odoo están a 0. Las 030, 032, 046 y 047 están
vacías; la 045 tiene una prenda. Isaac: «confirmar que están a 0 y retirarlas». La compactación de arriba no cuenta
estas cajas, así que da por hecho que ya se han retirado. El Excel `compactacion-zona0_20261126_1157.xlsx` (los mismos
datos más esta hoja) trae la hoja **«Cajas a 0 (retirar)»**. Va ordenada por hueco: primero la zona 0, después el resto.
Lleva una columna para marcar «comprobado vacía» y, si la tiene, el paso de la compactación en que entra el hueco.

| Copia del 23/11 | Cajas | Huecos |
|---|---|---|
| Cajas a 0 en huecos de zona 0 (el hueco tiene además cajas con stock) | 5.924 | 1.984 |
| Huecos sin stock, solo con cajas a 0, de L44 en adelante (quedan libres al retirarlas) | 7.264 | 1.487 |
| Huecos sin stock, solo con cajas a 0, antes de L44 (zona Z) | 763 | 86 |
| Cajas a 0 en huecos de zona Z o mixtos (fuera de esta propuesta) | 12.161 | — |
| Cajas con stock negativo (revisar; no se retiran) | 26 | — |

L67 P16 en la lista: C1 → 030 y 032; C2 → 045, 046 y 047. Es lo mismo que se ve en la foto.

**Sin confirmar:** si una caja a 0 sigue en la nave o ya se tiró y solo queda en Odoo, lo dirá la comprobación. Los
1.487 huecos con solo cajas a 0 pueden estar ya vacíos de verdad. Y si una caja a 0 tiene prendas (como la 045), no se
retira: es una diferencia de stock que hay que mirar aparte. Retirar el contenedor en Odoo no forma parte de este
programa.

## Lo que falta

- **FALTA MEDIDA: capacidad de un hueco.** Uso 770 L, medidos en Odoo como lo que cabe en los huecos llenos. No es la
  medida física.
- Formatos de estantería (1-0-60, 1C40, 2C40…): para compararlos hacen falta las medidas del módulo.
- Los datos son del 23/11. Una copia nueva, con el sí de Isaac, daría la foto de hoy.
- No se ha probado en el almacén. Antes de mover nada, conviene revisar en la nave los 20 primeros pasos de la lista.

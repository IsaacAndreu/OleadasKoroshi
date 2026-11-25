# Respuesta a KOROSHI: diferencias entre prendas servidas y prendas en caja (19/11/2026, v2 con matrículas)

Versión nueva. La v1 (`correo-koroshi-prendas-sin-caja-diferencias_2026-11-19.md`) no se toca. Esta añade qué matrícula
está realmente dentro de cuál. Matrículas sacadas de las notas «Juntar cajas» de cada pedido en Odoo (19/11, lectura).

---

**Para:** Miguel Cabot (y quien haya pedido el Excel)
**Asunto:** RE: Diferencias entre prendas servidas y prendas en caja

Hola Miguel,

Hemos mirado las 10 órdenes de tu Excel y **las prendas no se han perdido ni salieron sin caja**: están físicamente
dentro de otra caja de la misma tienda. La diferencia sale de cómo lo guardamos en Odoo.

**Qué pasa**
1. Cuando una tienda tiene una caja pequeña (de 1 a 6 prendas, en estos casos), en expediciones se mete dentro de otra
   caja de la misma tienda. Lo hacemos con la acción «Juntar cajas», para que la caja pequeña no cuente como un bulto
   más y el transportista no la vea como caja aparte.
2. Al juntar, las prendas de la caja pequeña **se quedan en Odoo sin matrícula**: la caja pequeña ya no existe como
   bulto y sus prendas no se pasan a la grande.
3. Vuestro Excel cuenta «en caja» solo las prendas con matrícula, así que sale una prenda de menos, o seis de menos.

**Qué matrícula está realmente dentro de cuál**

| Tienda | Orden | Prendas | La matrícula (caja pequeña)… | …está realmente dentro de |
|---|---|---|---|---|
| K01 Maquinista | 6665004426 | 1 | CJ665012247 | CJ665012171 |
| K29 Marineda | 6665004452 | 1 | CJ665012255 | CJ665012057 |
| K38 Artea | 6665004443 | 3 | CJ665012260 | CJ665012119 |
| K26 Magic | 6665004440 | 1 | CJ665012254 | CJ665012111 |
| K31 Condomina | 6665004428 | 1 | CJ665012256 | CJ665012058 |
| K10 Maxcenter | 6665004416 | 2 | CJ665012251 | CJ665012181 |
| K09 Ballonti | 6665004421 | 2 | CJ665012250 | CJ665012105 |
| K08 Itaroa | 6665004415 | 6 | CJ665012249 | CJ665012103 |
| K22 Vitoria | 6665004413 | 2 | CJ665012252 | CJ665012108 |
| K24 Valladolid | 6665004412 | 3 | CJ665012253 | CJ665012186 |

Las unidades de cada fila coinciden con la columna «Prendas sin caja» de vuestro Excel en las 10 órdenes. El juntado
se hizo el 19/11 entre las 07:22 y las 10:09.

**Qué os llega a vosotros**
La caja grande lleva físicamente todas las prendas, pero su contenido, tal como lo tenemos, solo incluye lo que se
preparó en ella.

**Qué vamos a hacer**
Que al juntar las cajas, las prendas de la caja pequeña pasen a la caja grande en Odoo. Así el contenido por caja
cuadra con lo servido y vuestro Excel no tendría diferencias. Lo estamos revisando con calma, porque toca el cálculo
de bultos que usamos para XPO y GLS. Os avisamos cuando esté.

Mientras tanto, si una orden sale en vuestro Excel con esa diferencia, no hay que repasarla: las prendas estarán en
otra caja de la misma tienda. Si alguna no cuadra con esta tabla, decídnoslo y la miramos una a una.

Gracias,

Isaac

---

## Para Isaac (no va en el correo)

- Las dos matrículas salen de la nota del pedido: «Juntar cajas: CJ… (N uds) metida en CJ…. Bultos del pedido: 4 -> 3».
- Confirmar con Miguel que su Excel cuenta «en caja» las líneas con matrícula.
- El cambio en Odoo (pasar las prendas a la caja grande al juntar) se ha pasado al chat de la sync (ver abajo).

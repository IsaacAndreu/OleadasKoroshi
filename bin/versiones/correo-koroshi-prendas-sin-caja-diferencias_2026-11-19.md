# Respuesta a KOROSHI: diferencias entre prendas servidas y prendas en caja (19/11/2026)

Borrador. No enviado: lo revisa Isaac. Respuesta al Excel «DIFERENCIAS DE ERRORES EN PRENDAS SERVIDAS Y EXPEDIDAS»
(Miguel Cabot, 19/11). Comprobado en Odoo en modo lectura el 19/11 (las 10 órdenes).

---

**Para:** Miguel Cabot (y quien haya pedido el Excel)
**Asunto:** RE: Diferencias entre prendas servidas y prendas en caja

Hola Miguel,

Hemos mirado las 10 órdenes de tu Excel y **las prendas no se han perdido ni salieron sin caja**: están físicamente
dentro de otra caja de la misma tienda. La diferencia sale de cómo lo guardamos en Odoo.

**Qué pasa**
1. Cuando una tienda tiene una caja pequeña (1 a 6 prendas, en estos casos), en expediciones se mete dentro de otra
   caja de la misma tienda. Lo hacemos con la acción «Juntar cajas», para que la caja pequeña no cuente como un bulto
   más y XPO o GLS no la vean como caja aparte.
2. Al juntar, la OUT pequeña se queda **sin caja propia**. Odoo guarda en esa OUT una nota: «las N uds de esta OUT van
   dentro de la caja CJ…, que es la que lleva la matrícula».
3. La línea de esas prendas queda sin matrícula (CJ). Y vuestro Excel cuenta «en caja» solo las prendas con matrícula.
   Por eso sale una prenda de menos, o seis de menos.

**Comprobación**
- Las 10 órdenes tienen exactamente esas unidades sin matrícula, y la **cifra coincide con la de vuestro Excel en
  todas**: K01 6665004426 (1), K29 6665004452 (1), K38 6665004443 (3), K26 6665004440 (1), K31 6665004428 (1),
  K10 6665004416 (2), K09 6665004421 (2), K08 6665004415 (6), K22 6665004413 (2) y K24 6665004412 (3).
- En cada una de ellas, la OUT pequeña tiene la nota de «Juntar cajas», del 19/11 entre las 07:22 y las 10:09.
- Las prendas concretas de vuestra columna «Prendas sin caja» son las que cuadran con esas líneas (por ejemplo, K01:
  2621PT01 col. 000003 T.28 ×1, en la OUT EFFEC/OUT/26510, dentro de la caja CJ665012171).

**Qué os llega a vosotros**
La caja grande que lleva la matrícula tiene en el contenido solo lo que preparamos en ella. Lo de la caja pequeña, que
se metió dentro, no consta en ese contenido. Físicamente la caja lleva todas las prendas.

**Qué proponemos**
Que al juntar las cajas, las prendas de la caja pequeña se asignen en Odoo a la caja grande. Así el contenido por caja
cuadra con lo servido y vuestro Excel no tendría diferencias. Es un cambio en nuestro lado y lo tenemos que revisar
con calma, porque toca el cálculo de bultos que usamos para XPO y GLS. Os avisamos cuando esté.

Mientras tanto, si una orden sale en vuestro Excel con la diferencia de una caja pequeña, **no hay que repasarla**:
estará en una caja de esa misma tienda.

Si alguna orden de vuestro Excel no tiene esa nota de «Juntar cajas», decídnoslo y la miramos una a una.

Gracias,

Isaac

---

## Para Isaac (no va en el correo)

- Las 10 son órdenes de tienda del 19/11 con zona MU2 (lote Z-1911-MU2).
- «Juntar cajas» es la acción 1844 del pedido (`bin/KOROSHI_juntar_cajas_INSTRUCCIONES_2026-10-22_0805.md`).
- **Pendiente de confirmar** con quien sepa cómo arma S4T el contenido de la caja: no he podido ver qué recibe de nosotros. La explicación vale si su Excel cuenta las líneas con matrícula; el cuadre de números lo confirma, pero conviene preguntárselo a Miguel.
- El arreglo (asignar las prendas a la caja grande al juntar) es un cambio de código en el flujo de «Juntar cajas».
  No lo he tocado.

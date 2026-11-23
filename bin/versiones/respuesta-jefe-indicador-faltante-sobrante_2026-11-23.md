# Respuesta al jefe: indicador relativo de faltante y sobrante (23/11/2026)

Buenas tardes,

Sí, ya lo tenemos, con faltante y sobrante juntos y para uso interno (aparte de lo de Andrés). Está en el
libro «2 Recepción y desviaciones» v2, con datos de Odoo del 20/11.

**Cómo se calcula**
- Desvío de cada SKU = stock en sistema − (recibido − salidas).
- El índice suma faltante y sobrante en valor absoluto: −10 en una talla y +8 en otra del mismo modelo-color
  cuentan 18, no 2. Así no se esconde ningún cruce.
- Va en tres niveles: SKU, modelo-color y modelo, primero en % sobre lo recibido y después en unidades,
  ordenado de mayor a menor para atacar primero lo que canta.
- En el nivel modelo se ve aparte el **cruce entre colores**: lo que se compensa dentro del modelo pero no dentro
  de cada color, que es lo que parece que ha pasado ahora.

**Primera foto (20/11)**
- 687 SKU con desvío de 3.726: 1.717 uds de desvío bruto (1.006 faltan y 711 sobran); el neto es −295.
- Índice de error global: 0,32 % sobre lo recibido.
- 70 modelo-color con cruce de tallas y 18 modelos con cruce entre colores. El más claro es el 2621XC04:
  faltan 22 y sobran 20, entre colores del mismo modelo.
- Gravedad alta: 8 modelos y 11 modelo-color.

**Objetivo 95 %**
Cada desvío se marca como localizado o regularizado, y una hoja de resumen enseña el % resuelto frente al 95 %, en
unidades y en número de SKU, y por separado para faltantes y sobrantes. Hoy está en 0 %: empezamos por los de gravedad
alta.

Un apunte: el stock de sistema solo recoge los ajustes ya hechos. Para confirmar cada caso hay que comprobarlo en
físico (stock físico a cero y sistema mayor que cero = faltante).

Saludos

# WhatsApp grupo Koroshi: el sobrante entra en el índice de error (20/11/2026)

Hola a todos 👋 Os comento una mejora que hemos metido en el control de stock.

Al revisar las desviaciones hemos visto que no basta con mirar los faltantes. Cuando aparece un sobrante,
casi siempre hay un faltante detrás en el mismo modelo o en el mismo modelo-color: tallas cambiadas en una
matrícula, colores cruzados o, a veces, modelos distintos de un mismo proveedor.

Por eso, a partir de ahora el índice de desviación incluye también los sobrantes:

• Por modelo-color: lo que falta, lo que sobra y lo que se compensa entre tallas.
• Siempre primero en % (sobre lo recibido) y luego en unidades, para ver el impacto real.
• El resultado es un indicador rápido de la probabilidad de que haya un error en cada artículo, ordenado
  de mayor a menor, para atacar primero los de probabilidad alta.

Primera pasada con datos de hoy: de 674 modelo-color, 70 tienen a la vez tallas con falta y tallas con
sobra (probable cruce de tallas) y 11 salen con probabilidad alta.

El criterio de faltante es sencillo: stock físico a cero y stock en sistema mayor que cero. Así podemos
comprobarlo en cualquier momento, incluso en la ubicación inicial, y hacer un barrido de todo el stock, no
solo de lo que se pide.

En cuanto lo tengamos revisado os pasamos el listado. Cualquier duda, me decís 🙂

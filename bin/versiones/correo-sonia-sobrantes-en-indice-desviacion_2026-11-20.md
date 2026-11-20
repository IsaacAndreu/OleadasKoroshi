# Mensaje a Sonia (Koroshi): sobrantes dentro del índice de desviación (20/11/2026)

Hola Sonia:

Al revisar las desviaciones de stock hemos visto que no basta con mirar los faltantes. Cuando aparece un
sobrante, casi siempre hay un faltante detrás en el mismo modelo o en el mismo modelo-color: una matrícula
con tallas cambiadas, dos colores de un mismo modelo cruzados o, a veces, modelos distintos de un mismo
proveedor. Un sobrante «limpio» es rarísimo.

Por eso vamos a incorporar el sobrante al índice relativo de desviación, junto al faltante:

- **Por artículo-color y por modelo**: faltante, sobrante y la parte que se compensa entre los dos. Si en
  un mismo modelo falta una talla y sobra otra, lo tratamos como un probable cruce y no como una pérdida.
- **Siempre en relativo primero** (% sobre las unidades recibidas) y **después en absoluto** (unidades), para
  ver el impacto real.
- El objetivo es tener un indicador rápido de la **probabilidad de que haya un error** en cada artículo, para
  decidir qué acción tomar: los de probabilidad alta se revisan primero y se corrigen.

Para detectar un faltante, el criterio es sencillo: el stock físico es cero y el que tenemos en el sistema
es mayor que cero. Esto permite hacer una comprobación en cualquier momento, incluso en la ubicación
inicial, sin esperar a un inventario completo. La idea es hacer un barrido de todo el stock, no solo de los
artículos que nos pedís, y ordenarlo por esa probabilidad.

En cuanto lo tengamos montado os pasamos el primer listado.

Un saludo,
Isaac

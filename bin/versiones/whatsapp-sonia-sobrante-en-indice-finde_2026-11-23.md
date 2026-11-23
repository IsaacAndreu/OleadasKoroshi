# WhatsApp a Sonia: el sobrante entra en el índice (23/11/2026, idea «de finde»)

Hola Sonia 👋 Este finde he estado dándole vueltas a lo de los faltantes y creo que nos falta una pata: el sobrante.

Cuando aparece un sobrante, casi siempre hay un faltante detrás: tallas cambiadas en una matrícula, colores
cruzados dentro del mismo modelo o, a veces, modelos distintos de un mismo proveedor. Si solo miramos faltantes,
esos casos se compensan y no se ven.

Así que he metido el sobrante en el índice relativo, en tres niveles (SKU, modelo-color y modelo). Lo que falta y lo
que sobra se suman en valor absoluto: si en una talla faltan 10 y en otra del mismo color sobran 8, cuenta 18 y
no 2. Primero en % y luego en unidades.

La idea es tener un indicador rápido de la probabilidad de que haya un error. Ordenado de mayor a menor, se ve
enseguida qué casos cantan y se atacan primero los de probabilidad alta: o se localiza o se regulariza, que los
saltos tiendan a cero.

Y lo bueno es que vale para todo el stock, no solo para lo que se pide: faltante = stock físico a cero y sistema
mayor que cero. Se puede comprobar en cualquier momento, incluso en la ubicación inicial, y hacer un barrido.

Con los datos del viernes ya sale algo claro: el 2621XC04 tiene 22 que faltan y 20 que sobran, entre colores del
mismo modelo. Si quieres, el lunes lo vemos juntos con el Excel 🙂

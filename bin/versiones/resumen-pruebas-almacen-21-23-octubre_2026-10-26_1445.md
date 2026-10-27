# Pruebas de picking KOROSHI del 21 al 23 de octubre: qué hemos aprendido

Resumen para hablarlo con el almacén. Los datos salen de Odoo, salvo donde se indica.

## 1. Qué probamos

| Día | Método | Cómo se trabajó |
|---|---|---|
| Miércoles 21 | **Oleada + U** | Se coge por artículo para 10 tiendas a la vez y se reparte en el puesto de U (1 persona). |
| Miércoles 21 y jueves 22 | **Zonas** | Cada persona coge una zona de la nave para muchas tiendas; cada tienda sale en varias OUT. |
| Viernes 23 | **Tradicional** | Una OUT por pedido: una persona coge el pedido entero de una tienda. |

En los tres días se prepararon **11.441 uds** de pedidos de tienda, en **1.032 cajas**.

## 2. Lo que salió de cada método

**Velocidad cogiendo** (medida con la hora a la que Odoo cierra cada caja):

| Método | Segundos por unidad | Uds por caja |
|---|---|---|
| Tradicional (vie 23) | **48 s** | **13,8** |
| Zonas (jue 22) | 38 s (es un máximo: cada persona lleva varias tiendas a la vez) | **7,8** |
| Oleada (mié 21) | 31 s cogiendo + 20 s en la U = **51 s** | 14,1 |

Conclusiones:

- **Cogiendo, los tres métodos van parecido.** El método no es lo que nos frena.
- **Las zonas hacen casi el doble de cajas** (7,8 uds por caja frente a 13,8). El jueves salieron 252 OUT para 60 pedidos. Cada caja de más hay que cerrarla, juntarla, etiquetarla y cargarla, y es una ocasión más de equivocarse.
- **En la oleada, la U es un embudo**: todo pasa por una sola persona. El miércoles estuvo casi 1 hora parada esperando a que llegaran los INT.
- **El tiempo se va en la ubicación, no andando**: de los 48 s por unidad, unos 10 son de recorrido y unos 38 de leer la PDA, buscar, coger y meter en la caja.

**Decisión: el tradicional (una OUT por pedido) es el método base** mientras seguimos midiendo. Más adelante probaremos el carro con 2 o 3 tiendas a la vez.

## 3. Problemas que vimos

- **Cajas cerradas con la matrícula equivocada**: de otra tienda o una preimpresa.
- **Compactar cajas a mano sin usar «Juntar»** y **etiquetar antes de juntar**: la etiqueta de XPO sale con bultos de más.
- **Bultos negativos o de más** en las OUT: un módulo de Odoo suma y resta cada vez que se pone o quita una caja.
- **Cajas que se pierden** por el almacén y **prendas leídas sin caja**.
- **Faltantes**: en los tres días no salieron **311 uds** de lo pedido (un 2,7%), sobre todo por falta de stock.
- En los INT, la PDA **deja leer artículos que el INT no pide** (líneas «fantasma»).
- Alguien pulsó **«Forzar disponibilidad»**, y hubo que deshacerlo.

## 4. Lo que ya está hecho en Odoo

- **Monitor picking** (Inventario › Monitor picking): cómo van los pedidos de tienda del día. Las OUT a las que solo les faltan prendas sin stock (o que llevan más de 20 minutos sin cerrar caja) salen como **«Hecha · sin validar»**: hay que **validarlas**. También tiene modo pantalla para la tele del almacén.
- **Etiqueta de caja** con la matrícula grande, la tienda en medio y la OUT.
- **«Juntar»** cajas de un mismo pedido y **«Comprobar bultos»** antes de sacar la etiqueta de XPO.
- **Hoja de carga XPO** del día, por delegación, con palets (Inventario › Informes).
- **Etiquetas «Delegación …»** en las tiendas.
- **Aviso cuando en un INT se lee algo que no pide** o más unidades de las pedidas. De momento solo avisa (queda apuntado), no bloquea.

## 5. Lo que pedimos al almacén

1. **Cerrar cada caja con su matrícula**, nunca con una preimpresa ni con la de otra tienda.
2. **Primero juntar, después comprobar los bultos y al final etiquetar.** No compactar a mano sin «Juntar».
3. **Validar las OUT que el monitor marca como «Hecha · sin validar».**
4. **En los INT, coger solo lo que pide el INT.** Si se lee algo de más, devolverlo a su hueco.
5. **No pulsar nunca «Forzar disponibilidad».**
6. **Apuntar cada día las personas y las horas de cada fase** (picking, packing, expedición): entrada, salida y pausas.
7. **Un usuario por PDA**, para saber quién coge qué y cuánto tarda. Hoy todas entran como «Almacén Nath».

## 6. Para llegar a 10.000 uds al día

Con lo que hemos medido, 10.000 uds necesitan **entre 19 y 23 personas cogiendo de 6:00 a 13:00**, solo de picking, sin contar juntar, etiquetar ni cargar.

Para bajar de ahí:
- **Menos tiempo en la ubicación**: que el artículo esté en su hueco de picking, no lanzar lo que no tiene stock y quitar pasos a la PDA.
- **Andar menos**: carro con 2 o 3 tiendas a la vez.

Con las dos mejoras podríamos quedar en unas **14 a 16 personas**. Son objetivos que hay que probar y medir igual que hemos hecho estos días.

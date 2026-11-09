# Prompt · Organizar la zona Z (outlet) en colmenas · 30/10/2026 v2

v2 = v1 + lo acordado en la reunión del 30/10 (transcript `2026-10-30 15-01-05.txt`).

## Ideas que ya tenemos (resumen)

1. **Qué hay:** outlet de L01–L42 (zona Z), stock de Odoo del 28/10: unas 10.155 referencias-color, 74.272 uds, que hoy ocupan unos 1.851 palets.
2. **Fichero base:** `20261030colmenas-zona-Z-outlet_2026-10-28_1558_v3-litros-Koroshi.xlsx` (hojas Resumen, Medidas, Referencias). La hoja Medidas se rehízo en la reunión.
3. **Plan mixto de la v3:** columna en librería A, restos en celdas, lo demás en palet o caja. Salían 751 palets, un 59 % menos.
4. **Error en la v3:** en el Resumen, B, C y D salen con litros en m³ (0,009 en lugar de 52 L) y por eso dicen que no cabe ninguna referencia. Hay que corregirlo.
5. **Datos de verano de Koroshi:** solo han pasado 58 artículos de los 208 modelos de verano. El resto lo irán mandando, por modelo, familia y subfamilia.

## Estanterías (acordado en la reunión)

| Tipo | Ancho × alto × fondo (cm) | Columnas × pisos | Huecos | Notas |
|---|---|---|---|---|
| A18 | 120 × 160 × 40 | 2 × 9 | 18 | Librería (la nuestra). Mínimo 18 celdas por palet. Se puede montar A18 + 9 |
| A36 | 120 × 160 × 40 | 4 × 9 | 36 | Hueco más pequeño, unos 21 L |
| B12 | 118 × 140 × 38 | 2 × 6 | 12 | Estantería modulable de verdad |
| B24 | 118 × 140 × 38 | 4 × 6 | 24 | La B partida |
| C | 118 × 158 × 40 | 2 × 4 | 8 | KOROSHI, huecos muy grandes |
| D10 | 120 × 150 × 41 | 2 × 5 | 10 | Cajas de cartón de KOROSHI. Se cuentan 5 huecos por columna, no 10 |
| E | 86 × 164 × 60 | 2 × 4 | 8 | TucTuc, almacenada en alto. Se sale del palet: el hueco es 43 de ancho × 60 de fondo y se monta al revés. **Hay que volver a medirla** |

- **Fondo:** el palet mide 80 cm y la estantería tiene dos caras, así que cada cara tiene 40 cm de fondo.
- **Lineal:** se cuenta por media cara.
- **Nombres:** A, B, C, D, E. No se usa C1–C4, porque ya son nombres de ubicaciones.
- **Unidades del Excel:** medidas en el orden ancho, alto, fondo. Volumen del hueco en m³ y en litros. Volumen de la columna = volumen del hueco × pisos.
- **Cuántas hay de cada tipo:** las va a contar Jara con una foto de cada estantería. Hoy no se sabe.

## Reglas

- **Volumen por prenda:**
  - Invierno: litros medios de cada familia, con los datos de Koroshi.
  - Verano: 3 L por prenda en todas las familias. En verano el volumen medio varía poco (2,1 – 3,5 L).
  - Si falta el dato: 5 L en invierno y 3 L en verano.
- **Llenado:** como máximo, un 90 % de la capacidad de cada hueco.
- **1 hueco = 1 SKU** (referencia + color + talla). Nunca se mezclan dos SKU en un hueco.
- **1 columna = 1 referencia-color.** Es el contenedor mínimo: en una columna nunca hay dos artículos.
- **Referencia que no cabe en una columna:** sigue en la columna de al lado del mismo palet, con las tallas en el mismo orden. Ejemplo: S y M en la columna 1, y L, XL, 2XL, 3XL en la columna 2.
- **Una talla puede ocupar varios huecos seguidos** (por ejemplo, la L en 3 huecos).
- **Orden de tallas:** la más pequeña arriba y la más grande abajo, para que lo pesado quede abajo.
  - Letras: XXS, XS, S, M, L, XL, XXL, 3XL (3XL solo en caballero).
  - Pantalones (36, 38, 40…) y calzado (38, 40, 42…): de menor a mayor.
- **Huecos vacíos:** se aceptan. Para que la columna sea estable, mejor que queden arriba que abajo.
- **Color de talla:** cada talla de KOROSHI ya tiene un color en Odoo, y se usa para la pegatina de la caja.
- **Ubicación:** formato `L24P18C1` (lineal, palet, columna). Cada hueco lleva su contenedor.
- **Tipo de estantería:** la que corresponda al volumen de la familia. Por ejemplo, abrigos y parkas en E o C (huecos grandes) y blusas y camisetas en A.

## Debate abierto: ¿qué es el contenedor mínimo?

- **Opción 1, la que se calcula primero:** contenedor = columna, con una sola referencia-color.
  - Picking más rápido.
  - Se pierden huecos.
  - Compactar cuesta más: hay que tocar el sistema cada vez que se mueve algo.
- **Opción 2:** contenedor = ubicación física (palet), con varias referencias-color en el mismo palet, cada una en su hueco.
  - Compactar es más fácil.
  - El picker pierde unos 30 s en buscar cuál de los modelos es.
- **Por qué importa:** en la Z los artículos mueren en 3–6 meses y compactar es crítico.
- **Qué lo decide:** la profundidad (uds por SKU).
  - Con 1–2 uds por SKU, la opción 1 desperdicia mucho espacio.
  - Con unas 15 uds por SKU, ya no está tan claro.
- **Pendiente:** el A36 tiene 4 columnas físicas, pero hoy las ubicaciones del palet se nombran con 2 columnas (C1, C2). Hay que decidir si un palet A36 tiene 4 ubicaciones.

---

## PROMPT

> Eres analista de almacén. Organiza la zona Z (outlet KOROSHI, L01–L42) en estanterías de colmena y propón cómo compactarla.
>
> **Datos**
> - Fichero `bin/versiones/20261030colmenas-zona-Z-outlet_2026-10-28_1558_v3-litros-Koroshi.xlsx`.
>   - Hoja Referencias: referencia-color, temporada, familia, subfamilia, tallas, uds por talla.
>   - Hoja Medidas: tipos de estantería.
> - Stock de Odoo del 28/10/2026. Si se actualiza, solo en lectura.
>
> **Volumen por prenda (litros)**
> - Temporada de invierno: media de litros por prenda de su familia, con los datos de Koroshi (`datos_outlet_por_familia_para_Amposta_28.10.2026.xlsx`). Si la familia no tiene dato, 5 L.
> - Temporada de verano: 3 L por prenda en todas las familias. Koroshi solo ha pasado 58 de 208 modelos.
> - Litros de un SKU = uds × L por prenda.
>
> **Estanterías.** Usa estas medidas (ancho × alto × fondo, cm):
>
> | Tipo | Medidas | Columnas × pisos |
> |---|---|---|
> | A18 | 120×160×40 | 2×9 |
> | A36 | 120×160×40 | 4×9 |
> | B12 | 118×140×38 | 2×6 |
> | B24 | 118×140×38 | 4×6 |
> | C | 118×158×40 | 2×4 |
> | D10 | 120×150×41 | 2×5 |
> | E | 86×164×60 | 2×4, hueco 43×41×60; provisional, hay que volver a medirla |
>
> - Hueco = ancho / columnas × alto / pisos × fondo.
> - Calcula en litros: en la v3, B, C y D salen en m³.
> - Llena cada hueco como máximo al 90 %.
> - Calcula también el volumen de la columna (hueco × pisos).
> - De momento no hay límite de cuántas estanterías hay de cada tipo. Deja una celda para ponerlo cuando Jara las cuente.
>
> **Reglas obligatorias**
> 1. Un hueco guarda un solo SKU (referencia + color + talla). Un SKU puede ocupar varios huecos seguidos.
> 2. Una columna guarda una sola referencia-color. Es el contenedor mínimo.
> 3. Si la referencia-color no cabe en una columna, sigue en la columna de al lado del mismo palet, con las tallas en orden.
> 4. Orden de tallas: la más pequeña arriba y la más grande abajo.
>    - Letras: XXS, XS, S, M, L, XL, XXL, 3XL.
>    - Pantalones y calzado: numéricas de menor a mayor.
>    - Talla única: UNI.
> 5. Los huecos vacíos se aceptan y van arriba de la columna, no abajo, por estabilidad.
> 6. Para cada referencia-color, elige el tipo de estantería que gaste menos espacio (menos columnas y huecos vacíos) cumpliendo las reglas 1–5. Las prendas voluminosas irán a C o E y las pequeñas a A.
>
> **Excepciones**
> - Si un SKU no cabe ni en el hueco más grande, va a palet o caja.
> - Lístalas aparte con el motivo.
>
> **Color de talla**
> - Lee en Odoo (solo lectura) el color de cada valor de talla y ponlo en la asignación.
>
> **Comparativa de dos escenarios**
> - **Escenario 1:** contenedor = columna (las reglas de arriba).
> - **Escenario 2:** contenedor = palet. Varias referencias-color pueden compartir columna, pero nunca hueco.
> - Para cada escenario da:
>   - palets;
>   - metros de lineal a media cara;
>   - superficie (m²);
>   - huecos vacíos;
>   - nº de ubicaciones.
> - Estima el coste de picking del escenario 2 con 30 s más por línea que caiga en una columna compartida. Compáralo con el espacio que se ahorra.
> - Da la distribución de profundidad (uds por SKU y por referencia-color) para ver cuántas referencias son restos (1–2 uds).
>
> **Resultado:** un Excel nuevo. Nombre con fecha y hora, en `bin/versiones`. No se sobrescribe la v3. Hojas:
> 1. **Parámetros:** litros por familia, tipos de estantería, 90 % y celdas para contar estanterías.
> 2. **Asignación (escenario 1):**
>    - referencia-color;
>    - tipo;
>    - ubicación `L..P..C..`;
>    - piso de cada talla;
>    - color de talla;
>    - uds;
>    - litros;
>    - % de llenado.
> 3. **Resumen por tipo de estantería.**
> 4. **Por familia y temporada.**
> 5. **Profundidad:** uds por SKU, en rangos.
> 6. **Escenarios 1 y 2:** palets, lineal, m², ubicaciones y tiempo de picking estimado.
> 7. **Excepciones.**
> 8. **Comparativa con hoy (1.851 palets) y con la v3 (751).**
>
> No escribas nada en Odoo.

---

## Pendiente antes de lanzarlo

1. **Medidas de la E (TucTuc):** volver a medirla y confirmar el fondo de 60 cm, que se sale del palet.
2. **D:** confirmar que se cuenta como D10 (5 huecos por columna) y que la D20 queda descartada.
3. **A36:** ¿un palet A36 tiene 4 ubicaciones (C1–C4) o 2?
4. **Cuántas estanterías hay de cada tipo:** las cuenta Jara.
5. **Estallados:** preguntar a Antonio cuántos artículos estallados hay en la Z.

# Prompt · Organizar la zona Z (outlet) en colmenas · 30/10/2026 v1

## Ideas que ya tenemos (resumen)

1. **Qué hay:** outlet de L01–L42 (zona Z), stock de Odoo del 28/10: unas 10.155 referencias-color, 74.272 uds, que hoy ocupan unos 1.851 palets.
2. **Fichero base:** `20261030colmenas-zona-Z-outlet_2026-10-28_1558_v3-litros-Koroshi.xlsx` (hojas Resumen, Medidas, Referencias).
3. **Estanterías (hoja Medidas):** A18, A36 (librería), B12, B24 (TucTuc), C (KOROSHI), D10, D20, E. Las celdas amarillas están por confirmar en la nave.
4. **Plan mixto de la v3:** columna en librería A, restos en celdas, lo demás en palet o caja. Salían 751 palets, un 59 % menos.
5. **Error detectado en la v3:** en el Resumen, B, C y D salen con litros en m³ (0,009 en lugar de 52 L) y por eso dicen que no cabe ninguna referencia. Hay que corregirlo antes de comparar estanterías.

## Reglas nuevas (las de hoy)

- **Volumen por prenda:**
  - Invierno (temporadas I..): litros medios de cada familia, con los datos de Koroshi.
  - Verano (temporadas V..): 3 L por prenda en todas las familias.
- **1 hueco = 1 SKU** (referencia + color + talla). Nunca se mezclan dos SKU en un hueco.
- **1 columna = 1 referencia-color**, con todas sus tallas en la misma columna.
- **Orden de tallas:** la más pequeña arriba (XS/S) y la más grande abajo (XXXL).
- **Huecos vacíos:** se aceptan. Es mejor dejar uno vacío que romper la regla.
- **Color de talla:** cada talla tiene un color en Odoo. Hay que comprobarlo y usarlo para la etiqueta del hueco.

---

## PROMPT

> Eres analista de almacén. Organiza la zona Z (outlet KOROSHI, L01–L42) en estanterías de colmena y compáctala todo lo posible.
>
> **Datos**
> - Fichero: `bin/versiones/20261030colmenas-zona-Z-outlet_2026-10-28_1558_v3-litros-Koroshi.xlsx`.
>   - Hoja Referencias: una fila por referencia-color, con temporada, familia, subfamilia, tallas y uds por talla (T1…T10).
>   - Hoja Medidas: tipos de estantería con medidas de palet y de hueco, nº de columnas y pisos.
> - Stock de Odoo del 28/10/2026. Si se actualiza, solo en lectura.
>
> **Volumen por prenda (litros)**
> - Temporada de invierno (I..): media de litros por prenda de su familia, con los datos de Koroshi (`datos_outlet_por_familia_para_Amposta_28.10.2026.xlsx`). Saca una tabla Familia → L medio.
> - Temporada de verano (V..): 3 L por prenda, en todas las familias.
> - Litros de un SKU = uds × L por prenda.
>
> **Estanterías**
> - Usa los tipos de la hoja Medidas: A18, A36, B12, B24, C, D10, D20, E.
> - Capacidad del hueco en litros = ancho × alto × fondo del hueco. Calcúlala bien en litros: en la v3, B, C y D salen en m³.
> - Marca qué medidas están sin confirmar.
>
> **Reglas obligatorias**
> 1. Un hueco guarda un solo SKU (referencia + color + talla). Nunca se mezclan.
> 2. Una columna guarda una sola referencia-color con todas sus tallas.
> 3. Orden vertical: la talla más pequeña arriba y la más grande abajo, siguiendo el orden de tallas: XXS, XS, S, M, L, XL, XXL, XXXL, numéricas de menor a mayor, UNI.
> 4. Los huecos vacíos se aceptan. No se rellenan con otro SKU.
> 5. Se elige la estantería más pequeña en la que la referencia-color cumpla las reglas 1–3, para gastar los mínimos palets.
>
> **Casos que no cumplen**
> - Si un SKU no cabe en un hueco, pasa a un tipo con huecos más grandes. Si no cabe en ninguno, va a palet o caja.
> - Si una referencia tiene más tallas que pisos, pasa a un tipo con más pisos. Si no hay, va a palet o caja.
> - Lista estos casos aparte con el motivo.
>
> **Color de talla**
> - Comprueba en Odoo (solo lectura) dónde está el color de cada talla (valor de atributo talla) y añade la columna «Color talla».
>
> **Resultado:** un Excel nuevo. Nombre con fecha y hora, en `bin/versiones`. No se sobrescribe la v3. Hojas:
> 1. **Parámetros:** litros por familia (invierno), 3 L (verano) y medidas de cada estantería.
> 2. **Asignación:** referencia-color, tipo de estantería, palet nº, columna y piso de cada talla, color de talla, uds y litros, y % de ocupación del hueco.
> 3. **Resumen por tipo de estantería:** referencias, columnas, palets, huecos llenos y vacíos.
> 4. **Por familia y temporada.**
> 5. **Excepciones:** palet o caja, con el motivo.
> 6. **Comparativa:** palets de hoy (1.851), palets de la v3 (751) y palets con este plan.
>
> No escribas nada en Odoo.

---

## Lo que hay que decidir antes de lanzarlo

1. **Talla que no cabe en un hueco:** ¿se puede usar dos huecos seguidos de la misma columna (el mismo SKU repetido), o va a palet?
2. **Referencias de una sola talla (4.468):** con «1 columna = 1 referencia» cada una gasta una columna entera. ¿Es así, o pueden compartir columna sin compartir hueco?
3. **Más tallas que pisos:** ¿puede la referencia seguir en la columna de al lado?
4. **Estanterías disponibles:** ¿cuántos palets hay de cada tipo, o se puede comprar sin límite?
5. **Medidas en amarillo:** sobre todo el fondo (en Medidas sale 40 cm). ¿Están confirmadas?

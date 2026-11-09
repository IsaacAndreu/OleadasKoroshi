# Prompt · Zona Z en colmenas: informe + planos visuales · 30/10/2026 v3

v3 = v2 (reunión del 30/10) + informe Excel + HTML con planos. Se lanza **con supuestos** aunque haya cosas pendientes: cada supuesto queda marcado en amarillo y se puede cambiar.

---

## PROMPT (copiar entero)

> Eres analista de almacén y diseñador de layouts. En **un solo turno**, sin preguntarme nada, haz un estudio para reorganizar la **zona Z** (outlet KOROSHI, lineales L01–L42) en estanterías de colmena. El resultado tiene que decir qué tipo de estantería, o qué mezcla de tipos, es la más óptima y cuánto tiempo costaría.
>
> Lo que no sepas, lo supones. Apunta cada supuesto en la hoja «Supuestos» y en amarillo, y sigue adelante.
>
> ### 1. Datos de entrada (solo lectura)
>
> **Stock y referencias**
> - Fichero `bin/versiones/20261030colmenas-zona-Z-outlet_2026-10-28_1558_v3-litros-Koroshi.xlsx`.
> - Hoja **Referencias**: 10.155 referencias-color, 74.272 uds, stock de Odoo del 28/10. Columnas: referencia-color, temporada, familia, subfamilia, tallas, uds por talla (T1…T10).
>
> **Litros de invierno por familia**
> - `Downloads/datos_outlet_por_familia_para_Amposta_28.10.2026.xlsx` (Koroshi).
>
> **Color de cada talla**
> - Odoo nath.tuctuc.com, empresa EFFECTIVE LOGISTICS (company_id 8).
> - Solo lectura: atributo talla, campo de color del valor.
> - Si no se puede leer, pon colores provisionales y márcalo.
>
> **Plano de la nave**
> - Si te sirve para dibujar los lineales, usa `bin/versiones/20261030_warehouse_planner_NAU2_editor_v38.html`.
> - Si no, dibuja L01–L42 como lineales a dos caras, con palets de 1,20 × 0,80.
>
> **Prohibido**
> - Escribir en Odoo.
> - Sobrescribir ficheros existentes.
>
> ### 2. Volumen por prenda
>
> - **Invierno (temporadas I..):** litros medios de su familia (Koroshi). Si la familia no tiene dato, 5 L.
> - **Verano (temporadas V..):** 3 L para todas las familias. Koroshi solo ha dado 58 de 208 modelos.
> - **Litros de un SKU** = uds × L por prenda.
>
> ### 3. Tipos de estantería
>
> Medidas en cm (ancho × alto × fondo, a una cara):
>
> | Tipo | Medidas | Col × pisos | Huecos | Estado |
> |---|---|---|---|---|
> | A18 | 120×160×40 | 2×9 | 18 | medido (librería) |
> | A36 | 120×160×40 | 4×9 | 36 | medido |
> | B12 | 118×140×38 | 2×6 | 12 | medido (TucTuc modulable) |
> | B24 | 118×140×38 | 4×6 | 24 | medido |
> | C | 118×158×40 | 2×4 | 8 | medido (KOROSHI, huecos grandes) |
> | D10 | 120×150×41 | 2×5 | 10 | medido (cajas de cartón KOROSHI) |
> | E | 86×164×60 | 2×4 | 8 | **SUPUESTO**: hueco 43×41×60, se sale del palet, hay que volver a medirla |
>
> - El palet mide 80 de fondo y la estantería tiene dos caras. Cada lineal tiene dos caras.
> - **Hueco** = (ancho / columnas) × (alto / pisos) × fondo. Calcúlalo en litros: la v3 tenía B, C y D en m³ por error.
> - **Capacidad útil** = 90 % del hueco.
> - **Volumen de columna** = hueco × pisos.
> - **Estanterías disponibles de cada tipo:** sin límite (SUPUESTO; las va a contar Jara). Deja una celda de límite por tipo.
>
> ### 4. Reglas de colocación (escenario base)
>
> 1. **Un hueco = un SKU** (referencia + color + talla). Un SKU puede ocupar varios huecos seguidos.
> 2. **Una columna = una referencia-color.** Es el contenedor mínimo.
> 3. **Si la referencia-color no cabe en una columna,** sigue en la columna de al lado del mismo palet, con las tallas en orden.
> 4. **Orden de tallas:** la más pequeña arriba y la más grande abajo.
>    - Letras: XXS, XS, S, M, L, XL, XXL, 3XL.
>    - Pantalón y calzado: numéricas de menor a mayor.
>    - Talla única: UNI.
> 5. **Huecos vacíos:** se aceptan y van arriba, por estabilidad. El bloque de tallas va pegado abajo.
> 6. **Nombre de ubicación:** `L..P..C..` (lineal, palet, columna).
> 7. **Excepciones:** un SKU que no cabe ni en el hueco más grande va a «palet / caja» y se lista con el motivo.
>
> ### 5. Escenarios a comparar
>
> Calcula todos los escenarios con las mismas referencias:
>
> - **E0 · Hoy:** 1.851 palets.
> - **V3 · Plan mixto de la v3:** 751 palets, como referencia.
> - **S-A36, S-A18, S-B12, S-B24, S-C, S-D10, S-E · Un solo tipo:** toda la Z en un único tipo de estantería, con las reglas del punto 4. Lo que no cabe va a palet o caja.
> - **MIX · Mezcla óptima:** cada referencia-color al tipo que gaste menos espacio (menos m³ de estantería por litro guardado, con desempate por menos huecos vacíos). Es la propuesta principal.
> - **MIX-P · Mezcla con contenedor = palet:** varias referencias-color pueden compartir columna, pero nunca hueco. Así se compacta más, pero el picking es más lento.
>
> Para cada escenario calcula:
> - palets;
> - metros de lineal a media cara;
> - m² de suelo (palets × 0,96 m² más pasillo; supuesto: pasillo de 3 m entre lineales);
> - número de ubicaciones;
> - huecos llenos y vacíos;
> - % de ocupación en litros;
> - número de excepciones;
> - palets liberados respecto a hoy.
>
> Añade un análisis de **profundidad**: uds por SKU y por referencia-color, en rangos (1, 2, 3–5, 6–15, más de 15). Sirve para ver cuántas referencias son restos.
>
> ### 6. Tiempos
>
> Todos los parámetros van en celdas amarillas editables y son SUPUESTOS:
>
> | Parámetro | Valor por defecto |
> |---|---|
> | Montar una estantería de colmena en un palet | 20 min |
> | Trasladar una referencia-color de su ubicación actual a su columna | 3 min + 4 s por unidad, incluye etiquetar el hueco con el color de talla |
> | Mover una excepción a palet o caja | 5 min |
> | Plantilla | 4 personas × 7 h al día |
> | Picking por línea en columna exclusiva | 25 s |
> | Penalización por línea en columna compartida (MIX-P) | +30 s |
> | Líneas de picking al mes en la Z | SUPUESTO: estímalo con 1 línea por SKU al mes; si encuentras salidas reales, úsalas |
> | Compactación en MIX (columna exclusiva) | 2 min por referencia que se agota |
> | Compactación en MIX-P | 1 min por referencia que se agota |
> | Vida del artículo en la Z | 4 meses |
>
> Para cada escenario da:
> - **Implantación:** horas-persona y días con la plantilla.
> - **Picking:** horas al mes.
> - **Compactación:** horas al mes.
> - **Total a 4 meses:** implantación + picking + compactación.
>
> Con esto, la recomendación final dice si compensa la columna exclusiva (MIX) o la columna compartida (MIX-P).
>
> ### 7. Resultado 1: Excel
>
> Nombre: `bin/versiones/AAAAMMDD_HHMM_zona-Z-colmenas-estudio_v1.xlsx`. Fórmulas vivas donde se pueda, para que al cambiar un supuesto se recalcule. Hojas:
>
> 1. **Resumen:** recomendación en 5 líneas y tabla de escenarios (palets, lineal, m², ubicaciones, % de ocupación, horas de implantación, horas al mes, total a 4 meses). El mejor de cada columna, en verde.
> 2. **Supuestos:** todo lo supuesto, en amarillo y editable.
> 3. **Estanterías:** medidas, litros por hueco, litros útiles (90 %), volumen de columna, límite disponible.
> 4. **Litros por familia:** invierno (Koroshi) y verano (3 L).
> 5. **Asignación MIX:** una fila por SKU:
>    - referencia-color, talla, color de talla;
>    - tipo de estantería;
>    - ubicación `L..P..C..`;
>    - piso o pisos;
>    - uds, litros, % de llenado del hueco.
> 6. **Asignación MIX-P:** igual que la anterior.
> 7. **Por familia y temporada:** qué tipo usa cada familia y cuántos palets.
> 8. **Profundidad:** los rangos de uds por SKU.
> 9. **Tiempos:** cálculo por escenario.
> 10. **Excepciones:** con el motivo.
>
> ### 8. Resultado 2: HTML con planos visuales
>
> Nombre: `bin/versiones/AAAAMMDD_HHMM_zona-Z-colmenas-planos_v1.html`.
>
> **Requisitos del fichero**
> - Un solo fichero, sin internet: CSS y JS dentro y dibujos en SVG.
> - Se ve bien en pantalla y se imprime en A4 apaisado.
> - Textos en castellano.
> - Pestañas o índice arriba con estos apartados:
>
> 1. **Resumen**
>    - Tarjetas grandes: palets hoy, palets con la propuesta, palets liberados, % ahorrado, días de implantación.
>    - Recomendación en una frase.
>
> 2. **Catálogo de estanterías**
>    - Una ficha por tipo (A18, A36, B12, B24, C, D10, E) con su **alzado a escala** en SVG: columnas, pisos, cotas en cm y litros por hueco.
>    - Junto a cada alzado, un ejemplo real de la Z rellenado con las reglas: una referencia-color con sus tallas de colores (S arriba, grande abajo, vacíos arriba).
>    - Las medidas supuestas (E), con borde discontinuo y la nota «a medir».
>
> 3. **Comparativa de escenarios**
>    - Gráficos de barras en SVG: palets, metros de lineal, horas de implantación y horas totales a 4 meses.
>    - Cada escenario con un color fijo y la recomendación resaltada.
>
> 4. **Qué tipo para cada familia**
>    - Matriz familia × tipo de estantería, con el nº de referencias por casilla y un color más intenso cuantas más haya.
>
> 5. **Plano de planta de la Z, antes y después**
>    - Vista cenital de L01–L42 a escala.
>    - Hoy: palets ocupados.
>    - Propuesta MIX: cada palet coloreado por tipo de estantería.
>    - En gris rayado, el espacio que queda libre.
>    - Leyenda y escala gráfica.
>
> 6. **Alzado de un lineal tipo**
>    - Una cara de un lineal de la propuesta, dibujada palet a palet con sus columnas.
>    - Etiqueta `L..P..C..` en cada columna y el color de talla en cada hueco.
>    - Al pasar el ratón por un hueco: referencia-color, talla y uds.
>
> 7. **Profundidad**
>    - Histograma de uds por SKU, con el porcentaje de restos (1–2 uds).
>
> 8. **Tiempos**
>    - Diagrama de Gantt sencillo de la implantación (montar estanterías → trasladar por lineal → excepciones), en días con la plantilla supuesta.
>    - Tabla de picking y compactación al mes, MIX contra MIX-P.
>
> 9. **Supuestos y pendientes**
>    - La lista de supuestos.
>    - Lo que falta confirmar:
>      - medidas de la E;
>      - D10 o D20;
>      - 4 o 2 ubicaciones por palet A36;
>      - recuento de estanterías (Jara);
>      - estallados (Antonio);
>      - datos de verano de Koroshi.
>
> ### 9. Al terminar
>
> 1. Abre el HTML para comprobar que se ve bien:
>    - cada dibujo tiene sus cotas;
>    - no hay textos montados;
>    - se imprime bien.
> 2. Haz el PDF del HTML con el mismo nombre.
> 3. En el chat, en castellano y en menos de 15 líneas:
>    - la recomendación;
>    - los números clave;
>    - los 3 supuestos que más pueden cambiar el resultado;
>    - las rutas de los ficheros.

---

## Notas

- **Ficheros:** no se sobrescriben. Llevan fecha y hora en el nombre.
- **Odoo:** solo lectura.
- **Tiempos por defecto:** son estimaciones razonables, no medidas. Cambiarlos en la hoja Supuestos, cuando haya datos reales, recalcula todo.

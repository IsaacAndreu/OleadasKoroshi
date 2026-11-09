# Prompt · Zona Z: planos reales del warehouse por propuesta · 30/10/2026 v4

## Lo que he entendido

- **El problema:** los planos del estudio v1 (`20261030_1945_zona-Z-colmenas-planos_v1.html`) son un esquema inventado (42 filas × 44 palets) y no sirven.
- **Lo que queremos:** que los planos salgan del plano real de la nave, el mismo del warehouse planner (`20261030_warehouse_planner_NAU2_editor_v38.html`), con los lineales en su sitio, sus medidas y sus nombres.
- **Un plano por cada propuesta.** En cada uno se ve:
  - dónde va cada tipo de estantería;
  - qué lineales quedan **libres** (los que podríamos reducir).
- **La zona Z va del L01 al L43**, no al L42. Se compacta primero la Z, y lo que se libera son lineales de la Z.

---

## PROMPT

> Eres analista de almacén. Rehaz los planos del estudio de la zona Z usando el **plano real de la nave** del warehouse planner, con **un plano por cada propuesta** y marcando los **lineales que se pueden liberar**. Hazlo en un solo turno, sin preguntarme nada. Los supuestos van marcados.
>
> ### 1. Fuentes (solo lectura)
>
> **Plano real**
> - `bin/versiones/20261030_warehouse_planner_NAU2_editor_v38.html`.
> - Saca de su código la geometría de cada lineal: nombre (L01…), posición, largo, orientación, caras accesibles y pasillos.
> - Usa los mismos colores, el mismo dibujo y la misma orientación que el planner, para que el plano se reconozca.
>
> **Estudio anterior**
> - `bin/versiones/20261030_1945_zona-Z-colmenas-estudio_v1.xlsx`: escenarios, asignaciones y supuestos.
> - Los scripts de cálculo están en el scratchpad (`zonaZ/calculo.py`, `zonaZ/gen.py`). Reutilízalos.
>
> **Stock**
> - Zona Z = **L01–L43**.
> - Comprueba si el L43 tenía stock en los datos del 28/10. Si no está en el Excel v3, dilo y apúntalo como pendiente.
>
> ### 2. Capacidad real de cada lineal
>
> - **Palets por lineal:** el largo real del lineal (del planner) dividido entre 1,20 m, redondeado hacia abajo.
> - **Caras:** dos estanterías por palet, una en cada cara. Si un lineal solo tiene acceso por una cara, solo cuenta una.
> - Esto sustituye al supuesto de 44 palets por lineal.
> - Recalcula metros de lineal y m² con las medidas reales.
>
> ### 3. Cómo se coloca cada propuesta en el plano
>
> - **Se llena la Z empezando por L01** y siguiendo el orden de los lineales (L01, L02…) hasta colocar todos los palets de la propuesta.
> - **Agrupación:** cada tipo de estantería en bloque seguido y, dentro de cada tipo, las familias juntas (como en el estudio).
> - **Reservas:** las excepciones (palet o caja) van al final de lo ocupado.
> - **Lineales libres:** los de la Z (hasta L43) que quedan sin nada. Un lineal medio lleno no cuenta como libre: marca cuántos palets le quedan libres.
> - **Fuera de la Z:** no se toca nada de L44 en adelante. Se dibuja en gris claro, como contexto.
>
> ### 4. Planos: uno por propuesta
>
> **Propuestas:**
> 1. **Hoy:** cómo está la Z ahora, con L01–L43 ocupados.
> 2. **V3:** plan mixto del 28/10, 751 palets.
> 3. **MIX:** una columna para cada referencia-color.
> 4. **MIX-P:** contenedor = palet.
> 5. **MIX-H:** híbrido, la propuesta recomendada.
> 6. **S-A36** y **S-B24:** los mejores con un solo tipo.
>
> **Cada plano lleva:**
> - **Título:** la propuesta y sus cifras: palets, lineales ocupados, lineales libres, m² libres y días de implantación.
> - **Lineales ocupados:** pintados por tipo de estantería, palet a palet. Leyenda con los mismos colores del estudio.
> - **Lineales libres:**
>   - en verde rayado, con un rótulo grande «LIBRE»;
>   - aparte, una lista con los lineales que se pueden reducir, por ejemplo «L19–L43: 25 lineales, X m²».
> - **Lineal a medias:** si queda un lineal a medio llenar, se marca con el número de palets libres.
> - **Al pasar el ratón por un palet:**
>   - el palet (`L..P..`);
>   - el tipo de estantería;
>   - las familias que lleva;
>   - las referencias y las unidades.
> - **Escala gráfica y norte**, igual que en el planner.
>
> ### 5. Resultado
>
> **Página nueva**
> - `bin/versiones/AAAAMMDD_HHMM_zona-Z-colmenas-planos_v2.html`. **No sobrescribir la v1.**
> - Pestañas: Resumen · un plano por propuesta (7) · Comparativa · Catálogo de estanterías · Lineal tipo · Profundidad · Tiempos · Supuestos.
> - Las secciones que no cambian se copian de la v1.
>
> **Tabla nueva en la Comparativa**, una fila por propuesta:
> - palets;
> - lineales ocupados;
> - lineales libres (lista);
> - m² libres;
> - % de la Z liberado.
>
> **Excel**
> - `..._zona-Z-colmenas-estudio_v2.xlsx`, con una hoja más: «Lineales por propuesta».
> - Una fila por lineal L01–L43, con:
>   - palets de capacidad;
>   - palets usados en cada propuesta;
>   - libre sí o no.
>
> **PDF** del HTML, con el mismo nombre.
>
> **Al terminar, en el chat (en castellano, máximo 12 líneas):**
> - lineales libres de cada propuesta;
> - los supuestos que cambian respecto a la v1 (capacidad real por lineal, L43);
> - las rutas de los ficheros.
>
> **Prohibido:**
> - escribir en Odoo;
> - tocar el planner v38;
> - sobrescribir ficheros.

---

## Dudas para confirmar

1. **Orden de llenado:** ¿se llena de L01 hacia L43, de modo que se liberan los últimos (L43 hacia atrás)? ¿O preferís liberar los lineales más cercanos a algún sitio (muelles, pasillo central)?
2. **Propuestas:** ¿os valen estas 7, o solo MIX, MIX-P y MIX-H?
3. **Planner:** ¿basta con verlo en el HTML del estudio, o también queréis añadirlo como capa nueva en el planner (por ejemplo «LINEALS: PROPUESTA Z»)? Esto último sería una v39 del planner.

# Prompt · Zona Z: planos reales del warehouse por propuesta · 30/10/2026 v5

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

## Añadido en la v5 (respuesta del usuario)

- **Objetivo:** liberar lineales compactando el OUTLET (zona Z, L01–L43), que es lo que pide el jefe. Se llena de L01 hacia L43, de modo que los libres quedan al final. Solo HTML: no se toca el planner.
- **Primero, una sola librería:** un mapa para cada tipo (A18, A36, B12, B24, C, D10, E) con toda la Z en ese tipo. Para cada uno:
  - lineales ocupados y libres;
  - si no cabe en L01–L43, cuántos lineales faltan.
  - Al final, **cuál es la mejor librería única** y por qué.
- **Después, los MIX:** un mapa de cada mezcla:
  - **MIX:** columna exclusiva.
  - **MIX-P:** contenedor = palet.
  - **MIX-H:** híbrido con umbral del 33 %, del 50 % y del 75 %.
  - **MIX-H solo A36 + B24:** dos tipos, más fácil de comprar y montar.
  - **MIX-H A36 + B24 + C:** con C para las prendas voluminosas.
  - Al final, **qué MIX es el mejor**, contando lineales liberados y horas a 4 meses.
- **Datos:** todos los posibles de cada propuesta:
  - palets y posiciones;
  - lineales ocupados y libres;
  - m² libres;
  - ubicaciones;
  - huecos llenos y vacíos;
  - ocupación;
  - referencias por tipo;
  - excepciones;
  - implantación, picking, compactación y total a 4 meses.
- **Modelo del plano real (planner v38):**
  - Cada lineal tiene P01–P36 de 1,20 m y 0,5 m de fondo.
  - Las parejas de lineales van espalda con espalda (L01-02…).
  - Hay pasillos después de P03 y P24, y un pasillo central entre P17 y P18.
  - **Una cara de colmena = una posición (L, P).** Un palet de colmena (2 caras) ocupa la misma P en los dos lineales de la pareja.
  - El L43 no tiene pareja dentro de la Z: solo cuenta una cara.
- **Hoy:** posiciones ocupadas reales de L01–L43, sacadas de los datos del planner.

## Dudas para confirmar

1. **Orden de llenado:** ¿se llena de L01 hacia L43, de modo que se liberan los últimos (L43 hacia atrás)? ¿O preferís liberar los lineales más cercanos a algún sitio (muelles, pasillo central)?
2. **Propuestas:** ¿os valen estas 7, o solo MIX, MIX-P y MIX-H?
3. **Planner:** ¿basta con verlo en el HTML del estudio, o también queréis añadirlo como capa nueva en el planner (por ejemplo «LINEALS: PROPUESTA Z»)? Esto último sería una v39 del planner.

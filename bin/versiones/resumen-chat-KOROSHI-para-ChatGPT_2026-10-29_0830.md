# Resumen del trabajo KOROSHI (27–29/10/2026) para seguir en otro chat

Soy Isaac, del almacén (logística) de **KOROSHI** en la nave **NAU-2** (Amposta). Trabajamos con **Odoo 13 Enterprise** (nath.tuctuc.com, compañía 8 = KOROSHI). Repo local: `C:\dev\OleadasKoroshi`. Hablo en catalán o en castellano; respóndeme en el mismo idioma en que te escriba.

---

## 1. Normas de trabajo (respetarlas siempre)

- **Versiones:** no sobrescribir nunca un archivo. Cada versión nueva lleva fecha y hora en el nombre. Los scripts y las acciones van a `bin/`; las páginas, Excels y PDF van a `bin/versiones/`.
- **Acciones de servidor de Odoo 13 (safe_eval):**
  - Prohibido: f-strings, `import`, comprensiones de listas y lambdas que capturen variables.
  - Antes de un `raise Warning` va un `log(...)`.
- **Acciones que escriben en Odoo:**
  - Primero se prueban en modo DIAGNÓSTICO (acción 1837). En modo REAL solo cuando yo lo diga.
  - La línea `MODO =` se cambia con una regex anclada (`^MODO =`). Una vez se tocó un comentario y la prueba corrió en REAL.
- **Alcance:** solo KOROSHI. No tocar crons ni acciones de otros (por ejemplo, Oriola).
- **Prohibido:**
  - escribir contraseñas (poner ***);
  - pulsar «Forzar disponibilidad»;
  - borrar datos;
  - tocar el AutoUpdater o la versión del programa de escritorio (0.8.0.9);
  - ejecutar el programa compilado, porque escribe en la base de datos de producción.
- **Git:**
  - hacer push solo cuando yo lo pida;
  - autor de los commits: Isaac Andreu (isaacandreu76@gmail.com).
- **Fuera del repo:** preguntar antes de instalar nada.
- **Escenario de cálculo de oleadas y picking:** 10.000 unidades al día.

---

## 2. Conceptos del almacén

- **Ubicaciones:** formato `L## P## C#`.
  - **L (lineal):** hay 136.
  - **P (posición):**
    - el lado izquierdo va de P00 a P17;
    - el lado derecho va de P18 a P42 y solo existe hasta el L120.
  - **C (nivel):** C1 a C4.
    - **Bajos** = C1–C2, a mano.
    - **Altos** = C3–C4, hace falta máquina o escalera.
  - Las cajas son sububicaciones `KO_`.
- **Expedición:** está por debajo del L01, así que el L01 es la zona más cercana a la salida.
- **Tamaños:**
  - 1 ubicación = medio palé = 1,20 × 0,40 × 1,60 m = 768 L;
  - caja estándar de 60×40 de base;
  - la altura de la caja sale del CBM del packing ÷ 0,24 (0,40 por defecto).
- **Implantación y reposición por tienda:**
  - **implantación** = unidades enviadas a una tienda en los 5 días siguientes al primer envío de ese modelo a esa tienda;
  - **reposición** = lo que se envía después.
  - Se cuentan 50 tiendas físicas (sin About You, Zalando ni muestras).
- **Zona Z** = outlet (temporadas viejas). Sale género cada día: unas 9.358 uds en 30 días, el 9,5 % de la salida, sobre todo I26 y V26.

---

## 3. MASTER OI 26/27 (Excel de la reunión)

- **Archivos:**
  - versión 1: `MASTER OI 26-27_2026-10-27_1605.xlsx`;
  - versión 2: `261028_1256 MASTER OI 26-27 KOROSHI v2.xlsx`;
  - **última:** `261028_1557 MASTER OI 26-27 KOROSHI v3 datos Koroshi.xlsx`.
- **Correcciones pedidas en la reunión:**
  - TEU = 28 m³;
  - ubicaciones = CBM / 0,77;
  - columnas = CBM / 0,385;
  - % de implantación y % de reposición calculados sobre lo comprado;
  - eficacia = (implantación + reposición) / comprado;
  - la columna E es el nº de packing lists.
- **Hojas añadidas:**
  - «Implantación por tienda» y «Reposición por tienda» (650 modelos × 53 tiendas);
  - «V27 (packing Koroshi)»;
  - «V27 sin packing».
- **Resultados:**
  - implantación: 35,2 % de lo comprado (191.199 uds);
  - reposición: 15,5 %;
  - eficacia: 50,7 %;
  - de media, cada modelo va a 37 tiendas (75 %);
  - CBM comprado: unos 2.893 m³.
- **Datos que Koroshi mandó el 28/10:**
  - **Las 58 líneas que estaban a 0 en la OI 26/27:** ya están todas rellenas, unas con documentos y otras con estimaciones. Cada una tiene el color de su fiabilidad y un comentario.
  - **262JA13:** era 2622JA13 (corregido).
  - **Peso neto:** real en 38 líneas.
  - **Outlet (zona Z):** no son packing lists. Son estimaciones de m³ y kg por prenda para cada familia y subfamilia, porque de las temporadas viejas no guardan datos por referencia.
  - **V27:** 51 artículos, 59.361 uds y 279 m³.

---

## 4. Análisis de la nave

- **Aire (espacio vacío):**
  - unos 2.582 m³, el 36 %, casi todo en los niveles bajos;
  - los altos (C3–C4) están casi vacíos: 11.766 de 13.425 huecos libres.
- **Dónde está cada cosa hoy:**
  - el outlet ocupa del L01 al L68 (unos 347 m³, con los litros de Koroshi);
  - en el outlet del L01 al L42 hay unos 219 m³;
  - el invierno I27 va del L43 al L136.
- **Familias** (siglas): CH TR PA SU CA VE ZA CM PO RI FA CO TO BL OT.
- **Lineales grises L01–L43:** hay 9.094 referencias; 2.332 son para apartar (las que tienen todas las tallas o al menos 3).

---

## 5. Colmenas (estanterías de huecos para el outlet)

Las medidas son de la estantería entera. Se supone un fondo de 80 cm, que hay que confirmar.

| Tipo | Medidas | Huecos |
|---|---|---|
| A, librería | 160×120×80 | 4×9 huecos (42,7 L cada uno) |
| B, TucTuc | 180×120×80 | 2×7 huecos (123 L cada uno) |
| C, KOROSHI | 180×117×80 | 2×5 huecos |
| D | 145×120×80 | 2×5 huecos |

- **Cómo se reparte el género:**
  - referencia-color con 3 tallas o más: una columna entera (tipo A si cabe; si no, tipo B);
  - restos de 1–2 tallas: celdas A compartidas;
  - lo que no encaja: a palé.
- **Resultado (v3):** 883 palés en lugar de los 1.851 de hoy (−52 %).
- **Archivo:** `colmenas-zona-Z-outlet_2026-10-28_1558_v3-litros-Koroshi.xlsx`.

---

## 6. Plan final de la NAU-2

1. **Outlet:** sube a colmenas en los niveles altos C3–C4.
   - Z verano: L99–L108 (377 palés).
   - Z invierno: L108–L136 (762 palés).
2. **Delante, en bajos C1–C2 (cerca de expedición):**
   - I27 clase A en L01–L18: 277 referencias que son el 80 % de los picks, 785 m³ y 1.203 ubicaciones;
   - I27 clase B en L18–L22;
   - V27 en L22–L68;
   - la reserva de A y B va encima.
3. **Ojo:**
   - como el outlet sale cada día, tenerlo arriba obliga a usar máquina o a sacarlo en ventanas de 10–15 días;
   - hay que mirar en la nave: el fondo real de la estantería, la caja vieja de TucTuc, la altura útil de una ubicación y si el lado izquierdo tiene C4.

**Plano:** hay un HTML con pestañas (Aire / Invierno-outlet / Familias / Plan final, cada una en bajos y altos).
- Archivo: `plano-final-NAU2_2026-10-28_1559_v2-litros-Koroshi.html`.
- Publicado en https://claude.ai/artifact/CbLjAf2inZfQnKYYBJv2Ps

**Warehouse planner:**
- Archivo: `bin/warehouse_planner_NAU2_23_2026-10-28_1559_plan.html`. El original `_21` sigue sin tocar.
- El botón 🔥 LINEALS pasa por 9 modos: OFF, CALOR, TEMPORADA, AIRE·BAJOS, AIRE·ALTOS, INVIERNO/OUTLET, FAMILIAS, PLAN·BAJOS y PLAN·ALTOS.

**Otros documentos:**
- PDF de la reunión para mi compañera: `resumen-reunion-master-mapas-outlet-KOROSHI_2026-10-28_1226.pdf`.
- Coste de licencias: 268 €/año por usuario; con 6 usuarios son 1.608 €/año.

---

## 7. GLS: el problema de los bultos (caso K85 / Betty)

- **Problema:** en un envío agrupado con OUT juntadas (0 bultos, porque van dentro de la caja de otra OUT), el módulo `delivery_gls_asm` cuenta como mínimo 1 bulto por cada OUT. Con 3 cajas reales, la etiqueta salía 8/8.
- **Arreglo en el albarán:** la OUT/21894 tenía 9 bultos (cada edición de línea sumaba +1) y la pusimos a 1.
- **Arreglo en la acción de servidor 1834 «Enviar al Expedidor (multiple)»:**
  - a GLS solo se mandan las OUT con bultos;
  - las OUT juntadas reciben el mismo tracking que la OUT con bultos de su mismo cliente, más un mensaje en el chatter;
  - si un cliente no tiene ninguna OUT con bultos, sus OUT se mandan como antes.
- **Archivos:**
  - copia del original: `bin/accion_1834_enviar_expedidor_2026-10-28_1513_ANTES.py`;
  - versión nueva: `..._v2_sin-bultos-juntadas.py`, ya escrita en Odoo.
- **Pendiente:**
  - Betty tiene que anular en GLS la expedición 1371100275, quitar el tracking de las 7 OUT y volver a enviarlas con la acción 1834. Debería salir con 3 bultos.
  - La acción v2 aún no se ha probado con un envío real.
  - El arreglo de fondo, en el módulo, le toca a SAAC.

---

## 8. Pendiente

1. **Pedir a Koroshi el V27 que falta.** En Odoo hay 208 modelos V27 y han mandado 51; faltan 158:

   | Familia | Modelos que faltan |
   |---|---|
   | MC (camiseta manga corta) | 43 |
   | PT (pantalón) | 36 |
   | PC (pantalón corto) | 25 |
   | JA (chaqueta) | 25 |
   | TR (tricot) | 13 |
   | CC (camisa corta) | 7 |
   | SU (sudadera) | 7 |
   | CL (camisa) | 2 |

   - Les pido el mismo formato, o como mínimo uds, cartones, CBM y fecha prevista de llegada.
   - La lista está en la hoja «V27 sin packing» del MASTER v3.
2. **Confirmar con Koroshi:**
   - 2712JA36: viene en el Excel pero no está en Odoo;
   - 23 líneas de V27 no tienen PL del ERP;
   - 2622JA16 (PL2090): ¿es real el CBM de 16,5 m³ para 63 cartones o son unos 6 m³?;
   - 2621JA67: ¿a qué PL va?;
   - 2624JA67: ¿hay packing?
3. **Medir en la nave:** el fondo de la estantería, la caja vieja de TucTuc, la altura útil de una ubicación y si el lado izquierdo tiene C4.
4. **GLS:** la parte de Betty explicada en el punto 7.
5. **Git:** hay muchos cambios sin commit (monitor v1.14, Excels, mapas, planner v22/v23, acción 1834). Solo se hace commit si yo lo pido.

---

## 9. Borrador del correo a Koroshi para el V27

> Buenas tardes,
>
> Muchas gracias, ya lo hemos cargado y nos sirve.
>
> Solo una cosa del V27: en el Excel vienen 51 artículos, pero en Odoo tenemos 208 modelos de V27 creados. Os adjunto la lista de los 158 que no vienen (sobre todo camisetas manga corta, pantalones, PC y chaquetas). ¿Nos podéis pasar los mismos datos de esos, o como mínimo uds, cartones y CBM, y cuándo está previsto que lleguen?
>
> Y unas cosas pequeñas:
> - 2712JA36 viene en el Excel pero no lo tenemos en Odoo.
> - 23 líneas de V27 no tienen PL del ERP. Cuando lo tengáis, nos lo pasáis.
> - 2622JA16 (PL2090): ¿cuál es el CBM correcto?
> - 2621JA67: ¿a qué PL corresponde? Y del 2624JA67, ¿hay packing?
>
> Gracias,
> Isaac

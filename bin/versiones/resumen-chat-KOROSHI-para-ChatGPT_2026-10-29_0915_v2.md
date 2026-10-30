# Resumen del trabajo KOROSHI (27–29/10/2026) para seguir en otro chat · v2

Soy Isaac, del almacén (logística) de **KOROSHI**, en la nave **NAU-2** de Amposta.

- La nave mide **210 m × 60 m = 12.600 m²**.
- Trabajamos con **Odoo 13 Enterprise** en nath.tuctuc.com. KOROSHI es la compañía 8.
- El repo local está en `C:\dev\OleadasKoroshi`.
- Hablo en catalán o en castellano: respóndeme en el idioma en que te escriba.

La v1 de este resumen es `resumen-chat-KOROSHI-para-ChatGPT_2026-10-29_0830.md`. Esta v2 añade los puntos 8 a 12.

---

## 1. Normas de trabajo (respetarlas siempre)

- **Versiones**
  - No sobrescribir nunca un archivo. Cada versión nueva lleva fecha y hora en el nombre.
  - Scripts, acciones y el planner van a `bin/`.
  - Páginas, Excels, PDF y MD van a `bin/versiones/`.
- **Acciones de servidor de Odoo 13 (safe_eval)**
  - No se pueden usar f-strings, `import`, comprensiones de listas ni lambdas que capturen variables.
  - Antes de cada `raise Warning` va un `log(...)`.
- **Acciones que escriben en Odoo**
  - Primero se prueban en modo DIAGNÓSTICO (acción 1837). Solo pasan a REAL cuando yo lo diga.
  - La línea `MODO =` se cambia con una regex anclada (`^MODO =`). Una vez se tocó un comentario por error y la prueba corrió en REAL.
- **Alcance:** solo KOROSHI. No tocar crons ni acciones de otros (por ejemplo, de Oriola).
- **Prohibido**
  - Escribir contraseñas: se pone `***`.
  - Pulsar «Forzar disponibilidad».
  - Borrar datos.
  - Tocar el AutoUpdater o la versión del programa de escritorio (0.8.0.9).
  - Ejecutar el programa compilado, porque escribe en la base de datos de producción.
- **Git**
  - Push solo cuando yo lo pida.
  - Commits como Isaac Andreu (isaacandreu76@gmail.com).
- **Fuera del repo:** preguntar antes de instalar nada.
- **Oleadas y picking:** los cálculos se hacen sobre un escenario de 10.000 unidades al día.

---

## 2. Conceptos del almacén

- **Ubicaciones `L## P## C#`**
  - L = lineal. Hay 136.
  - P = posición:
    - lado izquierdo: P00–P17;
    - lado derecho: P18–P42, solo hasta el L120.
  - C = nivel:
    - **Bajos** = C1–C2, a mano.
    - **Altos** = C3–C4, con máquina o escalera.
  - Las cajas son sububicaciones `KO_`.
- **Expedición:** está por debajo del L01. El L01 es lo más cercano a la salida.
- **Tamaños**
  - Una ubicación de medio palé mide 1,20 × 0,40 × 1,60 m (768 L).
  - Un palé mide 1,20 × 0,80 × 1,60 m (1.536 L).
  - La caja estándar es de 60 × 40 de base. Su altura sale del CBM del packing ÷ 0,24, y es 0,40 si no hay dato.
- **Implantación y reposición por tienda**
  - **Implantación:** lo que se envía en los 5 días siguientes al primer envío de ese modelo a la tienda.
  - **Reposición:** lo que se envía después.
  - Se cuentan 50 tiendas físicas. No entran About You, Zalando ni las muestras.
- **Zona Z (outlet, temporadas viejas)**
  - Sale género cada día: unas 9.358 uds en 30 días, el 9,5 % de toda la salida.
  - Es sobre todo I26 y V26.

---

## 3. MASTER OI 26/27

- **Archivo actual:** `bin/versiones/261028_1557 MASTER OI 26-27 KOROSHI v3 datos Koroshi.xlsx`. Antes hubo una v1 (27/10) y una v2.
- **Reglas de cálculo**
  - TEU = 28 m³.
  - Ubicaciones = CBM / 0,77.
  - Columnas = CBM / 0,385.
  - Los % de implantación y de reposición van sobre lo comprado.
  - Eficacia = (implantación + reposición) / comprado.
  - La columna E es el nº de packing lists.
- **Hojas añadidas**
  - «Implantación por tienda» y «Reposición por tienda» (650 modelos × 53 tiendas).
  - «V27 (packing Koroshi)».
  - «V27 sin packing».
- **Resultados**
  - Implantación: 35,2 % de lo comprado.
  - Reposición: 15,5 %.
  - Eficacia: 50,7 %.
  - Cada modelo va de media a 37 tiendas (75 %).
  - CBM comprado: unos 2.893 m³.
- **Datos que mandó Koroshi el 28/10**
  - **Las 58 líneas que estaban a 0:** ya están rellenas, unas con documentos y otras estimadas. Llevan un color según la fiabilidad.
  - **262JA13:** era el 2622JA13.
  - **Peso neto real:** en 38 líneas.
  - **Outlet:** no mandaron packing lists por referencia, sino una estimación de m³ y kg por prenda para cada familia y subfamilia.
  - **V27:** 51 artículos, 59.361 uds y 279 m³.

---

## 4. Análisis de la nave

- **Aire (huecos vacíos)**
  - Hay unos 2.582 m³ de aire, el 36 %, casi todo en los niveles bajos.
  - Los niveles altos están casi vacíos: 11.766 de 13.425 libres.
- **Dónde está cada cosa hoy**
  - El outlet va del L01 al L68 (unos 347 m³).
  - El I27 va del L43 al L136.
- **Familias:** CH TR PA SU CA VE ZA CM PO RI FA CO TO BL OT.
- **Lineales grises L01–L43:** hay 9.094 referencias. Hay que apartar 2.332, las que tienen 3 tallas o más.

---

## 5. Colmenas y celdas

**Tipos de estantería** (medidas del palé entero; el fondo de 80 cm es una suposición):

| Tipo | Medidas | Huecos | Litros por hueco |
|---|---|---|---|
| A, librería | 160 × 120 × 80 | 4 × 9 | 42,7 L |
| B, TucTuc | 180 × 120 × 80 | 2 × 7 | 123 L |
| C, KOROSHI | 180 × 117 × 80 | 2 × 5 | |
| D | 145 × 120 × 80 | 2 × 5 | |

**Cómo se reparte el género:**
- Referencia-color con 3 tallas o más: una columna entera.
- Restos de 1–2 tallas: celdas compartidas.
- El resto: a palé.

Resultado: **883 palés en lugar de 1.851 (−52 %)**.

**Celdas que pidió el jefe el 29/10.** Ya están en el planner v24, en la sección «Celdas (colmenas)». Se calculan sobre una ubicación de 1,20 × 0,80 × 1,60:

| Celda | Por ubicación | Columnas × pisos | Hueco (ancho × alto × fondo) | Litros |
|---|---|---|---|---|
| 1 | 36 | 4 × 9 | 30 × 17,8 × 80 cm | 42,7 L |
| 2 | 18 | 2 × 9 | 60 × 17,8 × 80 cm | 85,4 L |
| 3 | 9 | 1 × 9 | 120 × 17,8 × 80 cm | 170,9 L |
| 4, TucTuc antigua | 14 | 2 × 7 | 60 × 25,7 × 80 cm | 123,4 L (hay que medirla) |

Si la «ubi» es media ubicación (1,20 × 0,40), todos los litros se dividen entre 2.

---

## 6. Plan final de la NAU-2

- **Outlet:** va arriba, en colmenas en C3–C4.
  - Z verano: L99–L108 (377 palés).
  - Z invierno: L108–L136 (762 palés).
- **Delante, en C1–C2:**
  - I27 de clase A en L01–L18: 277 referencias, que son el 80 % de los picks.
  - I27 de clase B en L18–L22.
  - V27 en L22–L68.
  - La reserva va encima.
- **Ojo:** el outlet sale cada día, así que tenerlo arriba obliga a usar máquina o a hacer ventanas de 10–15 días.
- **Archivos**
  - Plano: `plano-final-NAU2_2026-10-28_1559_v2-litros-Koroshi.html` (https://claude.ai/artifact/CbLjAf2inZfQnKYYBJv2Ps).
  - Planner: `bin/warehouse_planner_NAU2_24_2026-10-29_0900_celdas.html`.
    - Es el último. El original `_21` no se ha tocado.
    - El botón 🔥 LINEALS pasa por 9 modos: OFF / CALOR / TEMPORADA / AIRE BAJOS / AIRE ALTOS / INVIERNO-OUTLET / FAMILIAS / PLAN BAJOS / PLAN ALTOS.

---

## 7. GLS: el problema de los bultos (caso K85 de Betty)

- **El problema:** en un envío agrupado, cada OUT juntada (0 bultos) contaba como 1 bulto. 3 cajas salían como 8/8.
- **El arreglo**
  - La OUT/21894 se ha dejado en 1 bulto.
  - Se ha hecho la v2 de la acción 1834 «Enviar al Expedidor (multiple)»:
    - solo manda a GLS las OUT que tienen bultos;
    - las OUT juntadas se quedan con el tracking de la OUT de su mismo cliente.
  - Archivos: `bin/accion_1834_..._ANTES.py` (la versión anterior) y `..._v2_sin-bultos-juntadas.py`.
- **Pendiente**
  - Betty tiene que anular la expedición 1371100275 en GLS, quitar el tracking de las 7 OUT y volver a enviarlas.
  - La v2 todavía no se ha probado con un envío real.
  - El arreglo de fondo en el módulo le toca a SAAC.

---

## 8. Licencias de Odoo y PDA (preguntas del jefe del 29/10)

- **Precio:** pagamos **280 € por usuario al año**. Con 6 usuarios son 1.680 € al año.
  - La licencia es anual: no se pueden quitar usuarios ni pagar por meses hasta que se renueve.
  - Sí se pueden añadir usuarios a mitad de año; se paga la parte proporcional.
- **«Asignar PDA a licencia»** quiere decir tener un usuario de Odoo por cada PDA (PDA-01, PDA-02…) en lugar de uno por persona.
  - Se pagarían tantas licencias como PDAs.
  - El problema es que no se sabe qué persona ha hecho cada picking.
  - Las condiciones de Odoo no permiten compartir un usuario entre varias personas. Hay que confirmarlo con SAAC.
- **PIN:** para saber quién usa cada PDA, el operario metería su PIN al coger la PDA y se guardaría en el albarán.
  - En Odoo 13 el PIN de empleado solo sirve para fichar y para el TPV, así que haría falta un desarrollo a medida.

---

## 9. Localización de PDA y operarios dentro de la nave

- El GPS no funciona dentro de la nave.
- Hace tiempo pensé en usar balizas Bluetooth.
- **Precios aproximados** (de memoria, no son presupuestos):

| Opción | Precisión | Coste |
|---|---|---|
| Último escaneo de ubicación en la PDA | El lineal exacto, pero solo cuando escanea | **0 €** (pintarlo en el planner) |
| BLE: balizas fijas y una app en la PDA (90–150 balizas de 15–30 €) | 2–5 m | **1.500–4.500 €** + desarrollo |
| BLE: gateways fijos (21–32 de 80–250 €) y la PDA emite | 2–5 m | **2.000–8.500 €** + cuota del software |
| UWB (40–60 anclas de 150–500 €, etiquetas de 40–150 €, software) | 10–30 cm | **12.000–48.000 €** |

- **Con BLE el operario no tiene que hacer nada.**
  - La app de la PDA funciona en segundo plano, como servicio fijo en Android, y envía la posición cada pocos segundos por wifi.
  - También puede ser al revés: la PDA emite y los gateways la detectan.
  - Hace falta que la PDA tenga Bluetooth 4.0 o superior y que esté siempre encendido. Gasta un 5–10 % más de batería por turno.
- **Recomendación:** empezar por el último escaneo, que cuesta 0 €. Poner balizas solo si hace falta saber dónde está alguien que no escanea.

---

## 10. Pendientes

1. Pedir a Koroshi los **158 modelos V27** que no vinieron. Hay 208 en Odoo y mandaron 51.
   - Faltan: MC 43, PT 36, PC 25, JA 25, TR 13, CC 7, SU 7, CL 2.
   - Hay que pedirles uds, cartones, CBM y fecha de llegada.
2. Confirmar con Koroshi:
   - el 2712JA36, que no está en Odoo;
   - 23 líneas de V27 que no tienen PL del ERP;
   - el CBM del 2622JA16;
   - el PL del 2621JA67;
   - el packing del 2624JA67.
3. Medir en la nave:
   - el fondo de la estantería;
   - la celda 4 (la TucTuc antigua);
   - la altura útil de una ubicación;
   - si el lado izquierdo tiene nivel C4.
4. GLS: la parte de Betty (punto 7).
5. SAAC: si se puede compartir un usuario por PDA, y el arreglo de GLS en el módulo.
6. Git: hay muchos cambios sin commit. Solo se hace commit si yo lo pido.

---

## 11. Borrador del correo a Koroshi (V27)

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

---

## 12. PROYECTO NUEVO: mapa interactivo y editable del almacén

### 12.1 Qué queremos

Convertir el *warehouse planner* (un único HTML grande) en un **mapa interactivo totalmente editable**, sin tener que tocar código:

- añadir, mover, girar, copiar y borrar cualquier elemento: estanterías, lineales, pasillos, celdas, zonas, muelles, luminarias, altillos…;
- **crear tipos de elemento nuevos** desde la pantalla (medidas, color, icono, huecos o niveles) y que queden guardados en la leyenda, como los tipos de pasillo y las celdas;
- editar las propiedades de cada elemento: nombre, código de ubicación (`L## P## C#`), tipo, niveles, capacidad en litros, familia o temporada asignada;
- capas que se pueden activar y desactivar: estructura, pasillos, ocupación, aire, familias, plan, PDAs;
- guardar y cargar el layout y tener **versiones** (no sobrescribir nunca);
- más adelante, conectarlo a Odoo para mostrar datos en vivo: ocupación por ubicación, último escaneo de cada PDA y picks.

### 12.2 Cómo es el planner ahora (para quien lo tenga que programar)

- Es un solo HTML, con JS y CSS dentro, y dibuja sobre un `<canvas>`.
- **Barra lateral:** secciones plegables con `toggleSection(id)`. Cada una tiene una cabecera `id+'-arrow'` y un contenido `id+'-content'`. Ahora son Estanterías, Pasillos, Celdas, Zonas/Objetos y otras.
- **Elementos que se arrastran:** son tarjetas `<div class="elem-card" data-type="..." data-w="m" data-h="m" data-mult="1" data-color=... data-pasillo-id=...>`.
  - Tipos actuales: `pasillo_t`, `pasillo_p`, `zona`, `bloque`, `luminaria`, `altillo`, `garita`, estanterías/racks…
  - Las medidas van en metros. Un elemento colocado es un objeto `p` con `p.type`, posición y medidas. El dibujo depende de `p.type`, que tiene una rama `if` por cada tipo, alrededor de la línea 2.200.
- **Ya tiene:** botón SAVE/LOAD, cotas, rejilla, deshacer, duplicar, PNG/imprimir, contadores.
- **Lineales:** geometría `LIN`, `linX(p)` y `linY(l)`. Los datos de ocupación, temporada y familias van dentro, en la constante `PF`. Los modos se pintan con `pfChar`, `pfLegend`, `pfLine` y `pfMarks`.
- **Problema:** los tipos están **escritos a mano en el HTML y en el código de dibujo**. Para añadir uno nuevo hay que programar. Eso es lo que hay que cambiar.

### 12.3 Arquitectura propuesta

**Fase 1: editor que funciona solo con JSON (sin servidor)**

1. **Catálogo de tipos en JSON.** La barra lateral y el dibujo se generan a partir de él. Ejemplo:
   ```json
   {
     "id": "celda1", "grupo": "Celdas", "nombre": "CELDA 1",
     "forma": "rect", "w": 1.20, "h": 0.80, "alto": 1.60,
     "color": "#38bdf8", "rejilla": {"cols": 4, "pisos": 9},
     "huecoLitros": 42.7, "editable": true
   }
   ```
2. **Layout en JSON:** una lista de elementos `{id, tipo, x, y, rot, w, h, props:{...}}`, más la versión y la fecha.
3. **Dibujo genérico** por `forma` (rect, línea, polígono, icono), con color y etiqueta sacados del catálogo. Se acaba el `if` por cada tipo.
4. **Panel de propiedades:** al hacer clic en un elemento se abre un formulario con todos sus campos, que se pueden editar.
5. **Editor de tipos:** un botón «＋ Nuevo tipo» abre un formulario que añade el tipo al catálogo, y aparece en la leyenda.
6. **Guardado:** exportar e importar un archivo `.json` con fecha y hora en el nombre (por ejemplo `layout-NAU2_2026-10-29_1000.json`) y autoguardado en `localStorage`.
7. **Herramientas:** selección múltiple, alinear y distribuir, ajuste a la rejilla, girar 90°, deshacer/rehacer, buscar por código `L## P## C#`.
8. **Capas:** cada capa es una función que pinta por encima, a partir de datos (ocupación, aire, familias, plan…). Los datos de `PF` pasan a ser un archivo de datos aparte.

Tecnología: se puede hacer en JS puro sobre el canvas actual, o pasar a **Konva.js** o **Fabric.js**, que ya traen seleccionar, mover, girar y transformar. Recomiendo Konva, porque hace mucho más fácil la edición. Todo cabe en un HTML que se abre en local.

**Fase 2: módulo de Odoo `koroshi_layout` (opcional, después)**

- Modelos:
  - `koroshi.layout` (nombre, nave, versión, JSON del layout);
  - `koroshi.layout.tipo` (el catálogo).
- Relación elemento ↔ `stock.location` por el código `L## P## C#`.
- Vista web (un controlador como el de `koroshi_monitor`) que carga el editor y lee y guarda el layout por JSON-RPC.
- Capas en vivo:
  - ocupación (`stock.quant`);
  - picks y movimientos;
  - **último escaneo de cada PDA** (la localización que cuesta 0 €).
- Permisos: solo los responsables editan; los demás solo ven.
- Normas: es Odoo 13; primero probar en DIAGNÓSTICO; solo KOROSHI; no tocar nada de otros.

### 12.4 Primer paso concreto

1. Sacar del planner v24 todos los tipos que hay ahora (estanterías, pasillos PP1/PP2/VM1–4/VV1–2, celdas 1–4, zonas, luminaria, altillos, garita…) y pasarlos a `catalogo.json`.
2. Hacer `layout-editor_v1_<fecha>.html` con Konva:
   - leer `catalogo.json`;
   - barra lateral generada a partir del catálogo;
   - arrastrar y soltar en el plano;
   - panel de propiedades;
   - guardar y cargar el JSON.
3. Importar el layout actual de la NAU-2 (210 × 60 m, 136 lineales) a `layout-NAU2_<fecha>.json`.
4. Añadir las capas de AIRE, FAMILIAS y PLAN a partir de los datos de `PF`.
5. Cuando esté probado, valorar el módulo de Odoo.

# Inversa KOROSHI (devoluciones de tienda de verano): propuesta para la guía

Versión 27/11/2026 13:58. Sustituye como guía a `diseno-lectura-matriculas-inversa_2026-11-12_1705.md` y
`teorico-inversa-KOROSHI_2026-11-12_*.html`, que no se tocan.

Datos de Odoo leídos el 27/11/2026, solo lectura: registro de matrículas y salidas desde el 01/09/2026. No se ha
tocado nada en producción.

---

## 1. Qué está pasando

- Las tiendas devuelven **a goteo**: ninguna ha hecho un envío único.
  - En Odoo hay **3.368 cajas** registradas, de **50 tiendas**, en **80 días** distintos (del 04/03 al 27/11).
  - Una tienda ha enviado en **13 días distintos** de media, y la que más en 25.
- Al llegar, se lee la **matrícula** de cada caja («esta caja ha llegado») y se manda a S4T. Así sabemos qué caja
  llegó y cuándo. El **contenido no se lee**.
- Todo lo que entra va a **OUTLET**.
- Días con más cajas:

  | Día | Cajas |
  |---|---|
  | 24/09 | 231 |
  | 01/04 | 202 |
  | 17/10 | 189 |
  | 29/10 | 189 |
  | 16/10 | 138 |
  | 17/11 | 124 |
  | 19/11 | 120 |

- La matrícula es `CJ` + 3 cifras de tienda + 6 de caja: `CJ080000717` es la caja 717 de la tienda 080.
  - Tiendas con más cajas: 080 (367), 010 (143), 041 (142), 072 (134), 048 (117).
  - Las que menos: 029 (19), 060 (22), 037 (23).

## 2. El proceso, paso a paso

| # | Paso | Quién | Dónde queda |
|---|---|---|---|
| 1 | **Llegada**: leer la matrícula de cada caja y apilarla en la zona de espera, por día de llegada. Ya se hace. | recepción | Odoo: Registro de Matrículas de Caja → S4T |
| 2 | **Preparar el lote**: cuando se empieza la inversa, se decide qué cajas trabaja cada manipuladora (opción A o B, apartado 3) y se llevan a su puesto. | responsable | hoja del lote (tiendas o días de cada una) |
| 3 | **Empezar**: la manipuladora pasa la tarjeta en la PDA o portátil del puesto y toca **Inversa**. | manipuladora | Actividades: tiempo por persona |
| 4 | **Abrir caja**: lee la **matrícula** antes de abrirla. Si tenemos el teórico, la pantalla dice qué lleva por familia y a qué palé va cada familia. | manipuladora | Actividades: caja, persona, hora, tiempo por caja |
| 5 | **Leer el contenido**: lee cada prenda (EAN) mientras la saca. Sin contar a mano. | manipuladora | recuento real de la caja (ver apartado 6) |
| 6 | **Manipular**: quitar alarmas y etiquetas de tienda, poner la de outlet si toca, doblar y embolsar. | manipuladora | — |
| 7 | **Clasificar**: dejar cada prenda en el palé de su familia, en su puesto (layout, apartado 4). | manipuladora | — |
| 8 | **Cerrar caja**: al leer la siguiente matrícula se cierra la anterior sola. Las cajas de cartón vacías, plegadas y fuera. | manipuladora | tiempo por caja |
| 9 | **Palé lleno**: se cierra, se etiqueta con familia y temporada y se lleva a su sitio de stock (apartado 5). | carretillero | ubicación en Odoo |
| 10 | **Comparar**: teórico contra leído, por matrícula y por tienda. Diferencias a KOROSHI. | responsable | informe de diferencias |

Los pasos 5 y 10 dependen de tener el teórico (apartado 6). Sin él se puede trabajar igual: se leen las matrículas
y el tiempo, pero no se puede planificar antes ni comparar después.

## 3. Cómo repartir el trabajo entre manipuladoras

### Opción A: cada manipuladora con un grupo de tiendas

Cada una trabaja solo cajas de sus tiendas; nunca se mezclan tiendas entre manipuladoras.

**A favor**
- Control por tienda: las diferencias de una tienda son de una sola persona, y se puede cerrar «tienda K48 hecha».
- Cuando haya teórico, la comparación por tienda sale limpia.

**En contra**
- Las cajas están apiladas por **día de llegada**, no por tienda. Para repartir por tienda hay que mover y separar
  las 3.368 cajas antes de empezar: un trabajo grande que no añade nada.
- Las tiendas no pesan lo mismo (de 19 a 367 cajas): hay que equilibrar los grupos, y una tienda grande hace
  esperar a las demás.
- Si una manipuladora falta, sus tiendas se paran o se tienen que repartir.

### Opción B: cada manipuladora con unos días de llegada

Por ejemplo: lo del 24/09 a una, lo del 01/10 a otra… Se cogen los montones tal como están.

**A favor**
- Sin clasificar antes: se trabaja el montón tal como está.
- Fácil de equilibrar: se dan días hasta llegar a las mismas cajas por persona (p. ej. unas 150 a cada una).
- Si alguien falta, se coge el siguiente día.

**En contra**
- Una tienda queda repartida entre varias personas (envió en 13 días de media).
- El control por tienda no se pierde, porque cada matrícula lleva la tienda y Odoo sabe quién la leyó y cuándo. Pero
  la diferencia de una tienda tiene varias responsables.

### Recomendación

**Opción B**, porque el registro de matrículas permite sacar luego el control por tienda sin ordenar antes:

- Tienda = cifras 3–5 de la matrícula.
- Persona y hora = lectura en Actividades.
- Con el informe «cajas por tienda y persona» se ve qué tiendas faltan y quién hizo cada una.

**Mezcla posible**: B en general, y A solo para las 3–4 tiendas grandes (080, 010, 041, 072) si se quiere
seguirlas de cerca. Sus cajas son fáciles de separar al llegar porque la matrícula empieza igual.

## 4. Layout del puesto de manipulación

Un puesto = una manipuladora = una mesa y palés alrededor en U, para no andar.

```
             [ palé 1 ]  [ palé 2 ]  [ palé 3 ]
             [ palé 8 ]   MESA +     [ palé 4 ]
                          PDA
             [ palé 7 ]  [ palé 6 ]  [ palé 5 ]
   cajas por abrir ──►  (entrada)       (salida)  ──► cartón vacío
```

- **8 palés por puesto**, o jaulas o cajas grandes si hay poco espacio. Delante de la mesa, a un paso, van las
  familias que más salen; detrás, las que menos.
- Qué familia va en cada palé: **sale del teórico de lo que hay que abrir**, no de la venta de invierno. La
  devolución de verano llevará sobre todo familias de verano, y el reparto real se sabrá con el teórico.

| Palé | Si la devolución se parece a lo que sale ahora (otoño) | Si es de verano (a confirmar con el teórico) |
|---|---|---|
| 1 | JA chaquetas (32–34 %) | MC camiseta manga corta |
| 2 | PT pantalón largo (16–18 %) | PS pantalón corto y bermudas |
| 3 | TR tricot (16–19 %) | VS vestidos |
| 4 | ML camiseta manga larga (~10 %) | CC / PC camisa y polo manga corta |
| 5 | SU sudaderas (5–7 %) | PT pantalón largo |
| 6 | CL / BL camisas y blusas | WA bañadores + MS sin mangas |
| 7 | VS / FA vestidos y faldas | TP tops / FA faldas |
| 8 | **Resto** | **Accesorios y calzado** (XC, ZC, ZB, HA, ZT, SG…) + resto |

- La pantalla de Actividades ya dice, por cada familia de la caja, **a qué palé va**. La tabla se cambia en el
  parámetro `koroshi_actividades.inversa_destinos`, sin tocar código. Cuando se sepa la mezcla real del verano,
  se cambia el parámetro y cada puesto pone carteles a sus palés con el mismo nombre.
- Familias pequeñas que juntas son menos del 5 %: todas al palé «Resto». Se reparten después, en un segundo paso,
  cuando haya volumen.
- Volumen de referencia: una caja llena son 0,084 m³ (~10 uds plegadas). Las matrículas que ya conocemos llevaban
  17 uds de media.

## 5. Ubicar en stock: temporada y familia

Según la venta (salidas desde el 01/09/2026, en uds):

| Temporada (Odoo / código) | Web (39.659 uds) | Tiendas (284.883 uds) |
|---|---|---|
| I27 = invierno 26-27 (códigos 2621/2622) | 58,6 % | 95,5 % |
| I26 = invierno 25-26 (2521/2522) | 25,8 % | 1,5 % |
| I25 = invierno 24-25 | 5,3 % | 0,4 % |
| V25 / V24 / I24 | 4,4 % | 0,8 % |
| Más antiguas (I19–I23, V18–V23) | ~5 % | ~0 % |

- La web vende de verdad desde la 22-23. Lo nuevo y la 25-26 dan unos tres cuartos de las ventas, y con lo más
  antiguo se llega al ~95 %. Cuadra con el «85 % de lo vivo» que se comentó.
- Las tiendas venden casi solo la temporada en curso.
- Las familias, en web y tiendas, van casi igual:

  | Familia | Web | Tiendas |
  |---|---|---|
  | JA | 32 % | 34 % |
  | TR | 19 % | 16 % |
  | PT | 16 % | 18 % |
  | ML | 9 % | 10 % |
  | SU | 5 % | 7,5 % |
  | VS | 4,7 % | 2,5 % |

**Propuesta de ubicación** (de muelle a fondo):

| Zona | Qué va | Orden dentro |
|---|---|---|
| **1. Junto al muelle** | Temporadas que se venden: **25-26 y más nuevas**, y las familias fuertes de **22-23 a 24-25** | por familia, la que más sale delante: JA, PT, TR, ML, SU… |
| **2. Centro** | Resto de 22-23 a 24-25 (familias que salen poco) | por temporada y, dentro, por familia |
| **3. Final de la nave** | Temporadas muertas (anteriores a 22-23) y lo que no se vende | por temporada, sin orden fino |

Los límites exactos (qué familia de 23-24 va junto al muelle) se fijan con las **ventas de OUTLET**, que aún no
tenemos (apartado 6). Hasta entonces sirve la venta web de arriba.

## 6. Qué falta y qué hay ya en Odoo

### Lo que ya hay

| Qué | Dónde | Estado |
|---|---|---|
| Llegada de cada caja (matrícula y fecha) | `s4t.box.registry` «Registro de Matrículas de Caja» (módulo S4T de Effective) | **3.368 cajas**, se lee una a una (~9 s por caja) y se manda a S4T |
| Lectura de matrícula por persona y tiempo por caja | `koroshi_actividades`, actividad **Inversa** | hecho (v1.1.0 en adelante). Hay que probarlo en el puesto |
| Palé de cada familia en pantalla | parámetro `koroshi_actividades.inversa_destinos` | hecho; cambiar los valores para el verano |
| Temporada y familia de cada artículo | ficha del producto (`season_id`, `family_id`) y código (`2621JA10-…`: 26 = año, 2 = invierno, JA = familia) | hay |
| `s4t.matricula` | módulo S4T | **No es el teórico**: es lo que contamos nosotros (Excel EAN \| CAJA) para verificar contra S4T. Hay 67, de julio y agosto, todas en error: S4T pide el campo `almacen` |

### Lo que falta

1. **El teórico de cada matrícula** (qué SKU y cuántas uds envió la tienda en cada caja).
   - Lo tiene S4T/KOROSHI: su verificación responde «esperada» por SKU, pero solo después de mandarle lo contado.
   - Pregunta ya preparada: `pregunta-s4t-teorico-matriculas_2026-11-14_1457.md`. Se pide un `GET` por matrícula
     y la lista de pendientes.
   - Sirve para dos cosas:
     - **antes**: saber la mezcla de familias y preparar los palés de cada puesto;
     - **después**: comparar con lo leído.
   - Cuando llegue, Actividades lo enseña al leer la matrícula. Solo hay que cambiar de dónde sale.
2. **Las ventas del OUTLET por familia y temporada.** En Odoo solo están las salidas a tiendas y a web; el outlet no.
   Hay que pedirlas a KOROSHI: un Excel con temporada, familia y uds de los últimos 12 meses basta.
3. **Dónde guardar lo leído** (paso 5 del proceso). Hay que decidir una de estas dos:
   - **(a)** ampliar la pantalla de Inversa para leer EAN dentro de la caja abierta (lo más limpio, módulo propio);
   - **(b)** generar el Excel EAN | CAJA que ya entiende el módulo S4T y verificar con S4T (cuando se arregle el
     campo `almacen`).
4. **Puestos y espacio**: cuántas manipuladoras a la vez y cuántos metros hay para los puestos en U, para dibujar el
   plano de la zona.

## 7. Siguiente paso propuesto

1. Isaac pide el teórico a S4T/KOROSHI y las ventas del outlet.
2. Con el teórico de las cajas que hay en espera, recalcular la mezcla de familias del verano y fijar los 8 palés
   de cada puesto, cambiando `inversa_destinos`.
3. Montar **un puesto de prueba** con la opción B (un día de llegada): matrícula en Actividades, contenido leído y
   tiempo por caja. Con eso salen las cajas por hora y la gente que hace falta.
4. Decidir el punto 6.3 (dónde se guarda lo leído) antes de pasar de un puesto a todos.

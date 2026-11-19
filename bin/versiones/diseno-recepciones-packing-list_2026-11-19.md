# Diseño: recepción por packing list (`koroshi_recepcion_pl`, módulo nuevo), 19/11/2026

**Solo diseño. Sin código hasta que Isaac lo apruebe.** Sale de la sección 2 de
`bin/versiones/notas-grabaciones-recepciones-y-tareas_2026-11-19.md` (grabación con el responsable del muelle).

## 0. Lo que falta para cerrarlo

- **El packing list de ejemplo de Maite.** No está en el repo ni en Descargas. Allí solo hay `Packing_List.xlsx`
  (United Brands, agosto, una devolución con una fila por EAN y la columna `Box` vacía), que es otro formato. El diseño
  de abajo supone el formato de la grabación («cajas 1 a 3 = modelo tal, talla tal; cajas 4 a 7 = …»). Con el
  archivo real se ajusta la importación (punto 3) y nada más.
- Las preguntas del punto 8.

## 1. Cómo se recibe hoy

- **En el repo no hay nada de recepciones de proveedor.** Ningún módulo toca `purchase.order` ni recepciones de compra,
  y ninguno habla de tránsito en dos pasos. Lo ha buscado el subagente `lector-modulo` en todo `odoo/modulos`.
  El muelle trabaja con Odoo estándar (o con lo que venga de S4T) y con el «shipping», con columnas de recibido,
  teórico y en tránsito. Desde el código no se sabe de dónde sale esa pantalla: va en las preguntas.
- **La única recepción que crea un módulo nuestro** es la DEV de `koroshi_s4t_traspasos`
  (`models/traspaso.py:214-262`):
  - busca el tipo `incoming` con `sequence_code='DEV'`, almacén `EFFEC` y compañía 8;
  - crea el `stock.picking` con un `stock.move` por producto (no crea `stock.move.line` a mano);
  - hace `action_confirm()` y `action_assign()` y **la deja lista para validar**: valida una persona.
  Es el patrón que se copia aquí.
- `koroshi_contenedores`: sus «contenedores» KO_/TT_ son sububicaciones de un hueco, no contenedores marítimos.
  Mueve la ubicación entera (`controllers/main.py:569-571`) y no crea albaranes. **No se toca ni se reutiliza.**
  Su pantalla táctil (acción cliente `AbstractAction` + ruta JSON) sí sirve de modelo para la nuestra.

## 2. Qué es

Un papel del proveedor convertido en pantalla. El muelle **recibe contra el papel** y no contra la PO:

1. La oficina **carga el packing list** de un contenedor (Excel). Sale una «Recepción PL» con todas sus cajas.
2. En una **tablet** del muelle, el operario ve las cajas **agrupadas por referencia y color**, con su avance
   («Modelo 3300 negro: 5 de 7 cajas»). Toca una caja y le asigna un **puesto** (Palé 1, D1, Ubicación 4…).
   No hay código de barras: todo se hace tocando la pantalla.
3. Lo hecho se ve a medida que avanza: una barra por grupo y una barra total.
4. Al acabar, la oficina **exporta** con filtros («falta», «contenido distinto», «sin artículo en Odoo»).
   Después, si se quiere, **pasa a stock** (punto 5). El cruce con compras, PO y el «shipping» lo hace back office.

## 3. Tablas propias (ninguna compartida)

Todas nuevas y del módulo. **No se añade ningún campo** a `stock.picking`, `stock.picking.type` ni `stock.move.line`
(regla 7). La relación con Odoo va siempre desde nuestra tabla hacia la suya (`Many2one`), nunca al revés.

| Modelo | Una fila es | Campos principales |
|---|---|---|
| `koroshi.recepcion.pl` | un packing list (un contenedor o una entrega) | nombre (`PL/0001`), proveedor (texto o `res.partner`), referencia del proveedor, fecha prevista, archivo original (adjunto), estado (`borrador` → `en_curso` → `terminada` → `en_stock` / `cancelada`), recepción de Odoo (`picking_id`, Many2one a `stock.picking`, opcional), notas |
| `koroshi.recepcion.pl.caja` | **una caja física** | recepción, número de caja (1…335), grupo (texto: referencia + color), puesto, estado (`pendiente`, `recibida`, `no_llega`, `incidencia`), nota de la incidencia, operario (`hr.employee`), fecha y hora de marcado |
| `koroshi.recepcion.pl.linea` | lo que **dice el papel** que hay en una caja | caja, referencia del proveedor, color, talla, EAN (si viene), `product_id` (si se encuentra), uds teóricas, uds contadas (solo si hay incidencia) |
| `koroshi.recepcion.pl.puesto` | un puesto de esa recepción | recepción, nombre libre («Palé 1», «D1»), orden, ubicación de Odoo (opcional, ver 5) |

Detalles:
- **Los rangos se expanden al importar.** «Cajas 1 a 3 = 3300 negro M, 12 uds/caja» crea las cajas 1, 2 y 3, cada una
  con su línea de 12 uds. Así cada caja se marca sola y el avance se cuenta por cajas, que es lo que ve el operario.
  Una caja mixta (varias tallas) son varias líneas de la misma caja.
- **El artículo se busca al importar** por EAN, si viene, y si no por referencia + color + talla. Lo que no se
  encuentra se queda con el texto del papel y la marca «sin artículo en Odoo». **No impide recibir**: solo impide pasar
  a stock esa línea.
- **Los puestos son de cada recepción** y se crean desde la tablet con un botón «+ Puesto» (nombre libre). Se ofrece
  copiar los de la recepción anterior. No son ubicaciones de Odoo salvo que se diga (punto 5).
- Tamaño: 335 cajas × ~3 líneas = ~1.000 filas por contenedor. Nada.

## 4. La pantalla del muelle (tablet)

Acción cliente propia (como Contenedores) en **KOROSHI > Recepciones PL**, con ruta JSON propia. Pensada para el dedo:
botones grandes y nada de listas de Odoo.

1. **Lista de recepciones** abiertas: nombre, proveedor, «212 / 335 cajas».
2. **Recepción**, con una baldosa por grupo (referencia + color; se puede cambiar a «por referencia») y en cada baldosa
   el avance («5/7»). Color: gris = sin empezar, ámbar = a medias, verde = completo, rojo = con incidencia.
   Arriba, la barra total y un filtro «solo pendientes».
3. **Grupo**: las cajas como fichas numeradas (1, 2, 3…), cada una con su talla y uds. Se toca una caja y salen los
   **puestos** como botones grandes. Por defecto se propone el **siguiente puesto libre**: es la idea de la grabación,
   «15 cajas, 15 puestos, cada caja a su puesto». También se puede elegir el puesto ya usado por el grupo, para juntar.
   Un toque más y la caja queda `recibida`, con operario y hora.
4. **Incidencia** (pulsación larga o botón «!» en la caja): «no llega», «dañada», «contenido distinto» (se escriben
   las uds reales por talla) y una nota.
5. **Deshacer** la última marca y **desmarcar** cualquier caja (vuelve a `pendiente`). Hasta pasar a stock todo se
   puede corregir.
6. **Vista por puesto**: qué cajas hay en «Palé 1». Es la que sirve para coger el palé y llevárselo.

Varias tablets a la vez: cada marca es una escritura de una caja. Si la caja ya la marcó otro, la ruta lo dice («la
marcó Diana a las 10:32») y no la pisa. La pantalla se refresca cada 10 s. Se usa `role="presentation"`, no
`aria-hidden` (regla 9).

El operario sale de la sesión de la tablet (`hr.employee`, como en Contenedores). No hace falta un usuario de Odoo
por operario.

## 5. Cómo se pasa a stock

Propuesta: **el módulo prepara la recepción de Odoo, pero no la valida**. Valida una persona de back office, igual
que la DEV de traspasos. Así el cruce con PO y compras sigue siendo suyo y el muelle no toca el stock.

Botón **«Pasar a recepción de Odoo»** (oficina, con la recepción PL en `terminada`):

- **(A) Si ya existe la recepción de Odoo** de ese contenedor (de la PO o de donde venga hoy), se elige en `picking_id`
  y el módulo **solo pone `qty_done`** en sus líneas, por artículo = suma de las uds recibidas. No crea moves ni cambia
  cantidades pedidas. Lo que llega de más o de un artículo que no estaba se deja en el informe de discrepancias, no se
  añade solo.
- **(B) Si no existe**, crea una recepción nueva del tipo de entrada que diga Isaac (pregunta 3), con un `stock.move`
  por artículo y la cantidad recibida, y la deja confirmada y reservada, como `traspaso.py:240-258`.

Ubicación de destino: la del tipo de entrada. **Solo si un puesto tiene una ubicación de Odoo** se pone esa en las
`stock.move.line` de sus cajas (al poner `qty_done`, una línea por artículo y puesto). Por defecto los puestos no
tienen ubicación: son sitios del muelle, no huecos.

La recepción PL pasa a `en_stock`, queda enlazada y ya no se puede tocar. **Nunca se llama a `button_validate`.**

Alternativa más corta, por si se quiere empezar sin tocar stock: **fase 1 sin el punto 5**. El módulo solo es la hoja
del muelle más la exportación, y back office sigue recibiendo en Odoo como hoy, con el Excel al lado. Lo recomiendo
como primera entrega: se prueba en el muelle sin ningún riesgo para el stock ni para la PDA, y el paso a stock llega
en la 1.1 cuando se sepa cómo nace hoy la recepción del contenedor.

## 6. Exportación y discrepancias

- Lista de **líneas** (caja × talla) con filtros guardados: «Pendientes», «No llega», «Incidencia», «Contenido
  distinto», «Sin artículo en Odoo», «Por puesto». Se exporta con el «Exportar» estándar de la lista (Excel).
- **Resumen por artículo** (modelo, color, talla): teórico del papel, recibido, diferencia, y la cantidad de la
  recepción de Odoo enlazada si la hay, con el filtro «diferencia ≠ 0». Es la vista SQL de solo lectura que mira back
  office. No es una tabla que se escriba.
- Botón «Exportar discrepancias» en la recepción: un Excel con dos hojas (cajas con problema y resumen con
  diferencia ≠ 0) para mandar a Maite o a compras.

## 7. Qué NO toca

- Ningún campo nuevo en `stock.picking`, `stock.picking.type`, `stock.move.line` ni en ninguna tabla de Odoo.
- No valida recepciones ni mueve stock por su cuenta. En la fase 1 no escribe nada en `stock.*`.
- No toca la PDA ni la preparación (`koroshi_preparacion`, Lecturas, operarios), ni `koroshi_contenedores`, ni zonas.
- No toca compras ni PO, ni S4T (`koroshi_s4t_*`): el cruce con el «shipping» es de back office.
- No crea ubicaciones ni tipos de operación. Si un puesto necesita ubicación, se crea a mano con permiso.
- Depende de `stock`, `hr`, `koroshi_base` (compañía 8, hora del almacén) y `koroshi_menu` (menú). Se instala solo, con
  `-i`, y no a la vez que otra actualización.

## 8. Preguntas para Isaac

1. **El packing list de Maite**: ¿me lo pasas (Excel o PDF)? ¿Siempre llegará en Excel y con el mismo formato? Si
   llega en PDF, la importación es a mano o hay que pedirle el Excel. Propuesta: dar a Maite una **plantilla fija**
   (`caja_desde, caja_hasta, referencia, color, talla, uds_por_caja, EAN`) y pedirle que la mande siempre así.
2. **¿Cómo nace hoy la recepción de un contenedor en Odoo?** ¿Hay una PO y su recepción, la crea S4T o la crea alguien
   a mano? ¿Qué es la pantalla del «shipping» con recibido / teórico / en tránsito: Odoo (¿qué menú?) o S4T? Decide
   entre (A) y (B) del punto 5.
3. **Tipo de operación y ubicación** de entrada para los contenedores (¿EFFEC/Recepciones a EFFEC/Stock? ¿hay entrada
   en dos pasos?). Lo miro en la BD solo leyendo, si me das el sí.
4. **¿Fase 1 sin paso a stock** (solo la hoja del muelle y la exportación) o directamente con él?
5. **Puestos**: ¿son siempre sitios del muelle (Palé 1…), o alguna vez son huecos reales donde se quedan las cajas?
   Si son huecos, ¿la recepción de Odoo debe dejar el stock ahí?
6. **¿Se cuenta dentro de la caja?** En la propuesta se marca la caja entera como «recibida» y solo se cuentan uds si
   hay incidencia. ¿Basta así o quieren contar alguna caja (por ejemplo, una de cada modelo)?
7. **Agrupar**: ¿por referencia, por referencia + color o se elige en la pantalla? (Propuesta: + color por defecto y
   botón para cambiar.)
8. **Tablet**: ¿cuál, y el muelle tiene buena wifi? ¿Hay una sola o varias a la vez en el mismo contenedor?
9. **Quién carga el PL y quién pasa a stock**: ¿oficina, back office o el responsable del muelle? (Define los grupos.)

## 9. Estimación

- Fase 1 (tablas, importación, pantalla de la tablet y exportación): un módulo nuevo, sin riesgo para la PDA.
- Fase 2 (paso a stock, A o B): una versión más, cuando estén respondidas las preguntas 2, 3 y 5.

Modelo para programarlo: Opus en high (pantalla táctil y, en la fase 2, stock). Diseño de la fase 2: Fable u Opus en
high.

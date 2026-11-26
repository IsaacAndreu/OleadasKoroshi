# Investigación: por qué KOROSHI tiene tantos faltantes y cancelaciones por falta (26/11/2026, v1)

Solo lectura. Datos de Odoo (nath.tuctuc.com, compañía 8) leídos el **26/11/2026 por la mañana** por JSON-RPC
(usuario Departament IT), sin crear, escribir ni validar nada. Packing list: conciliación del 24/11
(`20261124_conciliacion-PL-vs-odoo_koroshi_v1.xlsx`) y MASTER v14. Detalle en
`20261126_investigacion-faltantes_v1.xlsx` (hecho con `odoo/KOROSHI_investigacion_faltantes_2026-11-26.py` a partir de
`20261126_investigacion-faltantes_datos-sku_v1.txt`).

Convenciones: **CPA** = movimiento «Cantidad de producto actualizada». **Prendas** = códigos `NNNNLLNN-…` sin SUMI ni
el pack de calcetines 2611UN10-000323. «Ajuste» = movimiento hecho entre una ubicación interna y *Inventory adjustment*
(id 81) o *Scrap* (id 83). Cada cifra lleva su consulta; **Hipótesis** marca lo que no está probado.

---

## Resumen en 8 líneas

1. **No es que el almacén pierda un 7 %.** Temporada OI 26/27 (3.661 SKU «26…»): recibido 541.627, salido 378.115,
   devuelto 144, bajas por ajuste 1.940, altas 1.751, stock 163.467. El libro **cuadra exacto**; la pérdida neta es
   **189 uds (0,035 %)** y las bajas brutas, **0,36 %**.
2. **Las faltas se cuentan 2,8 veces**: del 16 al 25/11, 3.814 líneas y 4.216 uds de falta, pero solo **1.358 pares
   tienda-SKU y 1.507 uds únicas**. Cada día llega un pedido nuevo por tienda con los mismos SKU.
3. **Causa principal (73 % de las líneas):** 240 SKU con stock 0 porque sus últimas unidades se dieron de baja por ajuste
   (−504 uds netas). **145 de ellos perdieron una sola unidad** y generan 1.074 líneas.
4. Esas bajas son casi todas **CPA de 1–3 uds** (91 %), con el usuario compartido «Almacén Nath». **No queda rastro del
   operario.** Las crea el núcleo de Odoo al poner la cantidad a mano, no ningún módulo nuestro.
5. Una parte se explica por **recepciones de más**: en 4 modelo-color, la unidad dada de baja coincide con lo recibido
   en Odoo por encima del packing list (+13/−13, +15/−15, +8/−8, +20/−22).
6. **18 %** de las líneas son SKU que «tienen stock» en Odoo, pero en FALTANTE (lo que no se encontró y está sin ronda),
   SORTER, DEVOLUCIÓN o TARKO. Solo hay 18 SKU con stock libre en hueco (46 líneas), y en 16 de esos huecos el operario
   ya dijo que no está.
7. **8 %** de las líneas: SKU agotados de verdad (todo lo recibido ya salió). KOROSHI pide reponer lo que no existe.
8. **A S4T no se le comunica ningún ajuste desde el 14/08** (6 regularizaciones en Odoo, la última en borrador). Es la
   explicación más probable de «nosotros tenemos stock»: **hipótesis**, porque no tenemos su stock por SKU.

---

## 1. Ajustes: de dónde salen y quién los hace

**Consulta.** `stock.move` hechos, `location_id child_of 85` (EFFEC/Stock), `location_dest_id = 81`, `date >= 2026-08-01`:
860 movimientos (hoja «P1 Ajustes por tipo»).

| Tipo | Movs | Uds | Origen en el código | Rastro del operario |
|---|---|---|---|---|
| Cantidad de producto actualizada (CPA) | 782 | 3.048 | Núcleo: `odoo/nucleo_tuctuc/addons/stock/models/stock_quant.py:585` (`_set_inventory_quantity`, solo en modo inventario y con el grupo de responsable de inventario) | Ninguno: solo el usuario |
| INV:… (ajuste de inventario) | 53 | 5.039 | `stock.inventory` del núcleo | Ninguno |
| KOROSHI contenedor …: poner a cero / cambiar cantidad (Nombre) | 25 | 341 | `koroshi_contenedores/controllers/main.py:462-511, 627` (desde v1.5.0, 18/11) | Sí: nombre en el movimiento y `koroshi.contenedor.movimiento.employee_id` |

- De las 3.048 uds de CPA, 1.956 son SUMI (08–09/10). De las 5.039 de INV, 2.024 son el pack de calcetines (29/09) y
  2.723 son SUMI (23–24/11). **En prendas, las CPA son 743 movimientos y 1.055 uds.**
- **Ningún módulo KOROSHI crea CPA** (búsqueda del subagente en `odoo/modulos`: nadie escribe `inventory_quantity` ni
  llama a `action_apply_inventory`, `stock.change.product.qty` ni `_update_available_quantity` hacia ajustes).
  `koroshi_faltantes/models/faltante.py:54, 60-61` solo **lee** esas CPA (logins `almacen@nath.es` y `almacen2@nath.es`).
- **Desde qué pantalla:** hay instalados `stock_barcode`, `stock_barcode_mobile`, `stock_barcode_optimization` y
  `barcode_*` (ir.module.module), que no están en el repo. **Hipótesis:** las CPA salen de poner la cantidad a mano, en
  la app de código de barras o en «Actualizar cantidad» o la lista de existencias editable, con el usuario compartido.
  No lo he podido confirmar sin el código de esos módulos.

**Cómo son las CPA de prendas** (743 movimientos; hoja «P1 Puestas a 0 (CPA) prendas»):
- Por mes: agosto 220/237 uds, septiembre 188/241, octubre 160/277, noviembre (hasta el 26) 175/300. Unas 10 al día,
  estable desde agosto.
- Usuario: «Almacén Nath» 734, «Almacen 2» 9. Lunes a viernes (sábado 6), de 06 a 17 h con un pico a las 12 h (144).
- 609 de 743 (82 %) son de 1 ud. 675 en un contenedor dentro de un hueco. Repartidas en 122 lineales (los que más:
  L84 32, L86 31, L37 26, L87 24, L88 23).
- Van sueltas o en ráfagas cortas: 306 sueltas y el resto en grupos de 2 a 9 de lineales distintos con menos de 3 min
  entre una y otra. **Hipótesis:** alguien repasa una lista (desde la PDA o desde la oficina) más que ir hueco por hueco.
- **Relación con la preparación:** solo 162 (22 %) tienen una OUT del mismo SKU y ubicación a ±2 h; 101 en las 24 h
  anteriores; **477 (64 %) ninguna**.
- **Relación con Faltantes:** de 128 CPA desde el 09/11, 2 tienen un `koroshi.faltante` del mismo SKU a ±3 días y
  **0 en la misma ubicación**; ningún faltante tiene `move_cero_id`. Las puestas a 0 **no pasan por el flujo de
  Faltantes**.

**¿Hay rastro del operario real?** Para las CPA y los INV, **no**: ni empleado, ni log, ni registro propio; solo el
usuario compartido. Sí lo hay en lo que pasa por nuestros módulos: `koroshi.faltante.employee_id` (563 registros, 19
personas), `koroshi.contenedor.movimiento.employee_id`, `koroshi.preparacion.lectura.employee_id` y
`koroshi.operario.tarea.employee_id`.

## 2. Origen del faltante: historia de los SKU

**Consulta.** `koroshi.kpi.falta` con `fecha` del 16/11 al 25/11 (3.814 líneas, 472 SKU). Para cada SKU se suman los
`stock.move` hechos por pareja de ubicaciones (proveedor → interna, interna → clientes, ajustes) y el `stock.quant`
interno de hoy (hoja «Resumen - causas por peso»).

| Clase | SKU | Líneas | % líneas | Uds (cada día) | Pares tienda-SKU | Dato |
|---|---|---|---|---|---|---|
| **B** Stock 0 por baja de ajuste | 240 | 2.798 | 73,4 % | 3.126 | 839 | −504 uds netas por ajuste; recibido 23.575 |
| **C** Stock en Odoo pero no servible o reservado | 139 | 691 | 18,1 % | 748 | 324 | Ver punto 3 |
| **A** Agotado: recibido = salido | 91 | 319 | 8,4 % | 336 | 192 | |
| **D** Nunca recibido | 2 | 6 | 0,2 % | 6 | 3 | |

**Grupo B: cuánto se perdió** (hoja «P2 Cómo se perdió (B)»):
- Uds netas perdidas por SKU: **1 ud, 145 SKU y 1.074 líneas**; 2–3 uds, 64 SKU y 849 líneas; 4–10 uds, 25 SKU y 625
  líneas; más de 10, 6 SKU y 250 líneas.
- Las 303 bajas de esos SKU (`stock.move.line` hechas, 18.430 líneas leídas): **276 de 1–3 uds (347 uds)**, 21 de 4 o
  más (130 uds) y **6 cajas enteras** (50 uds: igual a lo que entró en esa ubicación, sin ninguna salida desde ella).
  Por tipo: CPA 286 (448 uds), INV 15 (77), contenedor 2 (2). Altas en esos SKU: 23 uds.

**Clasificación con evidencia:**
- **Recibido de más en Odoo frente al packing list (recepción).** En la conciliación del 24/11, el modelo-color se
  recibió por encima del PL justo en lo que luego se dio de baja: **2622VS17-000003** +13 en el PL y −13 en la talla S
  (la caja de L83 P21 C1, ubicada el 12/08 y ajustada el 28/08 sin ninguna salida); **2622JA17-000003** +15 y −15 en
  la XXL (una caja de 15 en L130 P12 C2); **2621CL51-000139** +8 y −8 en la XL; **2621XC04-000019** +20 y −22 entre la
  40 y la 44. De los 70 SKU de B con más líneas, 13 están en modelo-color «recibido de más», 4 en «llegado y sin
  recepcionar», 1 en «cruce de colores» y 50 cuadran. **Dato** en esos 4; en el resto el PL no baja a talla y no se
  puede afirmar.
- **Cruce de colores o tallas:** 2621XC04 (caso Sonia): el color 000019 tiene bajas en las tallas 40 (−11) y 44 (−13), y
  el 000003 tiene altas en las 42, 43 y 44 (+16, +12 y +4). En la temporada 26, de 510 uds dadas de baja en SKU con
  falta, **como mucho 68** se compensan con sobrantes de otra talla del mismo modelo-color y **102** con otro color o
  talla del mismo modelo. **El cruce explica como máximo un 20 %.**
- **Unidades sueltas que no se encuentran** (el grueso: 276 de 303 bajas). En 8 historias completas (hoja «P2 Historias
  (muestra)») la baja llega **el día de la última salida o poco después**: se acaba lo visible del hueco y lo que queda
  en el sistema se pone a 0. **No se puede saber** si la unidad nunca llegó, se ubicó en otro hueco o salió en otra caja.
- **Puestas a 0 que eran falsas:** 98 quants internos están en negativo (−185 uds), 22 en SKU con falta (−44) y 16 en
  el grupo B (−31). Un quant negativo quiere decir que se sacó de una ubicación que según Odoo estaba vacía. **Hipótesis:**
  en parte, alguien puso a 0 y después la unidad apareció y se envió.
- **Devoluciones sin ubicar:** en los SKU con falta, la devolución de clientes por movimiento es mínima (17 uds en los
  472 SKU). Lo que hay en DEVOLUCIÓN está en el punto 3.
- **Recepciones abiertas:** 16 SKU de A y B tienen 17 líneas de recepción en estado reservado con 1.257 uds (IN/00174
  de junio a IN/00371 de septiembre, e IN/00394 del 23/11). Son las «recepciones abiertas de más» del 20/11. Hasta que se
  cierren, el sistema de KOROSHI puede verlas como stock (**hipótesis**).

## 3. Stock que sí existe en Odoo (grupo C, 139 SKU, 691 líneas)

**Consulta.** `stock.quant` interno de esos SKU, agrupado por zona (hoja «P3 Por qué no se sirvió»).

| Dónde está | SKU | Uds | Reservadas | Líneas (SKU solo ahí) |
|---|---|---|---|---|
| FALTANTE | 88 | 146 | 35 | 326 (+59 con hueco, +9 con TARKO) |
| Hueco | 38 | 177 | 44 | 74 |
| SORTER | 11 | 16 | 0 | 103 |
| DEVOLUCIÓN | 9 | 11 | 0 | 59 (+33 combinadas) |
| TARKO (taras) | 20 | 37 | 0 | 25 |

- **FALTANTE es la mitad.** Es la ubicación adonde va lo que el operario no encuentra: no es stock servible, es stock
  por buscar. `koroshi.faltante`: 563 registros desde el 09/11, **3 «encontrado»** y **ningún resultado de ronda**.
  La única ronda (EFFEC/INT/67387, 17/11) sigue abierta.
- **SORTER y DEVOLUCIÓN** (162 líneas): unidades que no están en un hueco y que la OUT no coge.
- **Stock libre en hueco y aun así cancelado:** 18 SKU, 134 uds libres, 46 líneas (cancelado 35, no cogido 10,
  pendiente 1). En **16** de esos huecos hay un `koroshi.faltante` «sin alternativa» del mismo SKU: Odoo dice que hay y
  el operario dice que no. Son los primeros a revisar en físico.
- **Cuándo llegó el stock del hueco:** 26 quants (152 uds, 39 reservadas) ya estaban antes de la primera falta (entraron
  por recepción). 9 llegaron entre faltas por «añadir prendas» de contenedores (19 uds) y 2 después (2 uds).
- **Cuántas líneas se habrían servido:** como mucho las **46** del stock libre en hueco, y solo si la unidad está de
  verdad (en 16 de 18 el operario dice que no). Si SORTER y DEVOLUCIÓN se ubicaran a diario, 195 líneas más tendrían
  stock servible. Lo de FALTANTE solo vuelve si una ronda lo encuentra.

## 4. Reclamación de KOROSHI: «nosotros tenemos stock, vosotros no»

**Dato.**
- `s4t.stock.regularization`: solo 6 regularizaciones (100 líneas), todas entre el 07/08 y el 14/08. La del 14/08
  (24 líneas, −50 uds) está **en borrador y nunca se mandó**. En el repo no hay código que llame a
  `/stock/regularization` ni a `/stock/snapshot`.
- Desde el 14/08, en prendas de EFFEC: **bajas 1.510 uds** (CPA 914, INV 255, contenedor 341) y **altas 1.850 uds**
  (CPA 40, INV 576, «añadir prendas» de contenedores 1.234). **Ninguna ha llegado a S4T.**

**Hipótesis (no probada).** El stock de S4T por SKU es lo recibido menos lo enviado según sus datos, sin nuestros
ajustes. Si es así, KOROSHI ve las unidades que Odoo ha dado de baja (las −504 netas del grupo B, el 73 % de las faltas)
y no ve las que han aparecido. También vería stock en las recepciones abiertas de más (1.257 uds en 16 SKU con falta).

**Para probarlo hace falta** el stock de S4T por SKU: el snapshot de los viernes o `GET /stock/weekly/{año}`. En Odoo
no está. **Hay que pedírselo a KOROSHI o S4T** (o autorizar la lectura de la API; esta sesión no ha llamado a S4T).

## 5. Volumen y coste

| Prendas EFFEC (desde 01/08) | Bajas | Altas | Neto (altas − bajas) |
|---|---|---|---|
| Agosto | 289 | 141 | −148 |
| Septiembre | 241 | 18 | −223 |
| Octubre | 301 | 58 | −243 |
| Noviembre (hasta 26/11) | 857 | 1.660 | +803 |
| **Total** | **1.688** | **1.877** | **+189** |

En octubre hay un −42 de 2622PT28 (02/10) que se devolvió con un INV de +42 el 07/10. Noviembre sube por los «poner a
cero» y «añadir prendas» de contenedores (compactación de huecos, desde el 18/11).

- **Valor: no se puede sacar de Odoo.** `product.product.standard_price = 0` y `lst_price = 1` en todos los artículos
  leídos (1.142). Hace falta el precio de coste por SKU o familia: **pedirlo a KOROSHI**.
- **El ~7 %:** con estos datos, el almacén pierde un 0,035 % neto (0,36 % bruto) de lo recibido. En el MASTER v14
  (27/10), el «pendiente de recibir» era 40.687 uds = **7,5 % de lo comprado** (542.592). **Hipótesis:** el 7 % de la
  reunión es lo comprado que aún no se había recepcionado (o recepciones abiertas), no una pérdida del almacén.
  Confirmarlo con quien dio la cifra.

## 6. El KPI cuenta cada día las mismas faltas

**Dato** (`koroshi.kpi.falta`, 16–25/11; hoja «P6 KPI diario vs únicas»):
- Cada día entra un pedido S- nuevo por tienda (**0 pedidos repetidos**), pero con los mismos SKU. El 18/11 hubo 471
  líneas y solo 84 pares tienda-SKU nuevos; el 24/11, 578 y 54.
- En total: 3.814 líneas y 4.216 uds, pero **1.358 pares y 1.507 uds únicas**. Un par sale de media 2,8 días; 165
  pares salen 6 días seguidos.
- Ya existe `koroshi.kpi.falta.repetida` (425 filas; 275 con último día el 25/11), que cuenta los días seguidos.
- Antes del 16/11 el KPI daba entre 30 y 135 líneas al día y desde entonces entre 380 y 580. **No sé por qué** (más
  pedidos de reposición o un cambio en el cálculo): sin comprobar.

**Propuesta (sin tocar el módulo):** que el informe diario dé tres números en vez de uno:
1. **Faltas nuevas:** pares tienda-SKU que fallan hoy y no fallaron en los 7 días anteriores, con sus uds.
2. **Faltas vivas:** pares abiertos, contados una vez y con las uds máximas pedidas (hoy: 1.358 y 1.507).
3. **Repeticiones:** líneas de pares ya abiertos (las que hoy hinchan el KPI). Sirve para pedir a KOROSHI que no reponga
   un SKU con stock 0 en el almacén.

Un par se cierra cuando se sirve o cuando pasan 7 días sin pedirlo.

## 7. % de faltantes y avisos (propuesta para decidir)

Base: lo que pidió Andrés el 18/11 (faltante relativo por SKU = faltante ÷ recepcionado, en %, con dos decimales,
ordenable, primero lo que pase del 10 %, tolerancia la fija KOROSHI, cruce con el inventario de los viernes) y nuestro
índice del 20/11 (faltante + sobrante en valor absoluto, 0,32 % de lo recibido).

**Definiciones exactas**
- **Faltante relativo por SKU** (el de Andrés) = (bajas − altas por ajuste + stock en FALTANTE) ÷ recibido de
  proveedor, en %, con dos decimales. Con el libro cuadrado, eso es exactamente lo que falta respecto a
  recibido − salido + devuelto.
  - Hoy, en los 70 SKU del grupo B con más líneas: **9 SKU ≥ 10 %** (por ejemplo, 2622JA17-000003-XXL 20,00 %,
    2621XC04-000019-40 18,33 %, 2621PL06-000039-XXL 11,76 %, 2622VS17-000003-S 10,00 %) y 50 ≥ 2 %. Columna
    «Faltante relativo» de la hoja «P2 Stock 0 por ajuste (B)».
- **Faltante global del almacén** = Σ(bajas − altas) ÷ Σ recibido de la temporada: **0,035 % neto**. En bruto
  (solo bajas): **0,36 %**. El índice del 20/11 (valor absoluto, por SKU): 0,32 %.
- **% de servicio perdido por falta** (lo que nota la tienda) = uds únicas no servidas por falta ÷ uds pedidas, por
  semana. Del 16 al 25/11: 1.507 uds únicas frente a 38.825 uds enviadas en OUT del tipo 45 (todas las OUT, también web
  y marketplace) ≈ **3,7 %**; contando repeticiones sale ≈ 9,8 %. El denominador debería ser solo tiendas: queda por
  afinar.
- **% por ajuste** (para aprobar): uds del ajuste ÷ recibido de ese SKU, más el total del día ÷ uds movidas en el día.

**Escala de avisos propuesta** (los nombres y los umbrales finales los decide Isaac):

| Nivel | Cuándo | Quién | Qué hace |
|---|---|---|---|
| 0 | El operario no encuentra una unidad | Operario (queda su nombre) | «No está» en Lecturas o Contenedores → la ud va a FALTANTE. **Nunca puesta a 0 directa** con el usuario compartido |
| 1 | Baja de 1–3 uds de un SKU después de una 2.ª búsqueda (91 % de las bajas actuales) | Jefe de almacén (¿quién?) | Confirma en la ronda de faltantes |
| 2 | Baja de 4 o más uds, una caja entera, un SKU con faltante relativo ≥ 2 %, o el total del día > 0,2 % de las uds movidas | Isaac | Aprueba; mira la recepción frente al PL |
| 3 | SKU ≥ 10 % (o la tolerancia que fije KOROSHI) y el resumen semanal | KOROSHI (¿Andrés, Efrén?) | Informe semanal y regularización a S4T |

Sobre el 0,2 % de la reunión: si se aplica **por SKU**, una sola unidad de un SKU de 130 recibidas ya es 0,77 % y todo
subiría de nivel. Si se aplica al **total del día** (bajas ÷ uds movidas), con unas 3.000–8.000 uds hechas al día en
OUT, el umbral sería de 6 a 16 uds diarias. En noviembre las bajas de prendas van por unas 45 uds por día laborable (857 en 19 días). **Hay que
decidir sobre qué base se aplica.**

## Acciones propuestas (nada se aplica sin el sí de Isaac)

| # | Acción | Dato que la justifica |
|---|---|---|
| 1 | **Que nadie ponga cantidades a mano con «Almacén Nath».** Las bajas pasan por Faltantes o Contenedores (con nombre). Si se mantiene la puesta a 0, con un usuario por persona o un motivo obligatorio | 743 CPA de prendas sin rastro; 0 casan con un faltante; 91 % de las bajas son de 1–3 uds |
| 2 | **Hacer la ronda de faltantes ya.** Primero los 16 huecos donde Odoo dice que hay y el operario dice que no, y los 88 SKU con stock en FALTANTE | 326 + 59 + 9 líneas con el stock solo en FALTANTE; 3 encontrados de 563; ronda del 17/11 sin tocar |
| 3 | **Ubicar a diario SORTER y DEVOLUCIÓN** | 162 líneas canceladas con stock en esas zonas |
| 4 | **Mandar a S4T la regularización de los ajustes** (o el snapshot) y pedir su stock por SKU para cuadrar | 0 regularizaciones desde el 14/08; 1.510 bajas y 1.850 altas sin comunicar |
| 5 | **Pedir a KOROSHI que no reponga SKU con stock 0 en el almacén**, o filtrar la reposición | Cada falta se repite 2,8 días de media; 1.507 uds únicas frente a 4.216 contadas |
| 6 | **Recepción: contar frente al PL antes de cerrar** y revisar los modelo-color «recibido de más» | +13/−13, +15/−15, +8/−8, +20/−22: lo recibido de más es lo que luego se da de baja |
| 7 | **Cerrar o anular las recepciones abiertas de más** | 1.257 uds abiertas en 16 SKU con falta |
| 8 | **Revisar los 98 quants negativos** (−185 uds) | Señal de puestas a 0 falsas o de salidas desde ubicaciones equivocadas |
| 9 | **KPI de tres números** (nuevas, vivas, repeticiones) y el **% por SKU de Andrés** cada semana | Punto 6 y punto 7 |
| 10 | **Dar precio de coste a los artículos** (o recibirlo de KOROSHI) para valorar las bajas | Coste 0 en Odoo |

## Qué se ha probado y qué no

**Probado con datos:** clases A, B, C y D por SKU; que el libro de la temporada cuadra; tamaño y tipo de las bajas; que
las CPA no pasan por Faltantes ni dejan nombre; regularizaciones a S4T; repeticiones del KPI; zonas del stock de C; los 4
casos de recibido de más igual a la baja; el cruce de colores de 2621XC04.

**No probado:**
- desde qué pantalla exacta se hacen las CPA (los módulos de código de barras no están en el repo);
- quién las hace;
- el stock de S4T y KOROSHI por SKU;
- el valor;
- de dónde sale el 7 %;
- por qué el KPI salta el 16/11;
- si la unidad suelta nunca llegó o se perdió dentro.

El detalle por SKU del Excel recoge los 70 SKU con más líneas de cada grupo, no los 472.

**Preguntas para Isaac:**
1. ¿Quién es el jefe de almacén del nivel 1, y quién en KOROSHI recibe el nivel 3?
2. El 0,2 % de la reunión, ¿se aplica por SKU o al total del día?
3. ¿Quién dio el 7 %, y sobre qué base?
4. ¿Podemos pedir a KOROSHI o S4T el snapshot de los viernes y los precios de coste?
5. ¿Quién usa «Almacén Nath» en la oficina para poner cantidades?

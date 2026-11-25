# ¿Cancela Amposta (6665) pedidos web por «No hay stock» teniendo stock? (24/11/2026)

Queja de KOROSHI (support@koroshi.tv, 24/11/2026 13:08, reenviada por Sonia). Análisis **solo leyendo** en Odoo
producción (nath.tuctuc.com, compañía 8) el 24/11/2026 por la tarde. No se ha tocado nada. No se ha mirado S4T.

## Respuesta corta

**Tienen razón en parte, pero no por lo que creen.**

- Los artículos que KOROSHI enseña en su pantalla **sí tenían stock y Odoo sí los había reservado**. El pedido se
  canceló por **otra línea** que KOROSHI no enseña y de la que Odoo no tenía ni una unidad.
- Desde el 19/11 el corte automático de las 06:00 y las 11:00 (`koroshi_agrupaciones_web`) cancela **la OUT entera**
  en cuanto falta **una sola línea**. Del 19 al 24/11 canceló 39 pedidos (97 uds): en 24 de ellos había 56 líneas
  reservadas que se perdieron por 41 líneas sin stock. **Eso es lo que ve KOROSHI**: prendas con stock en pedidos
  cancelados por «No hay stock».
- De esas 41 líneas que faltaban, en **40 Odoo no tenía ninguna unidad que se pudiera preparar** en ese momento. Solo
  una (2521TR17-000139-S) tenía 6 uds en el hueco y el operario la marcó como faltante.
- Antes del corte automático (17 y 18/11) la oficina canceló a mano 58 OUT web; **24 de ellas tenían todas las prendas
  en huecos de NAVE2** según Odoo. Esas son las que más se parecen a la queja (detalle en el apartado 4).
- Los pedidos 0000059444-02 y 0000059444-02-02 **nunca llegaron a Odoo**: el almacén no los pudo rechazar. Se
  cancelaron en el TPV de KOROSHI.

## 1. El pedido 0000059444 (Irati, 19/11/2026)

| Dato | Odoo |
|---|---|
| Pedido de venta | W-0000059444 (id 129328), PED. ONLINE, creado el 19/11 14:01 (hora local) |
| OUT | EFFEC/OUT/26642 (id 388229), salida directa desde EFFEC/Stock, `move_type` direct |
| Líneas | **5**, no 2 |
| Cancelada | 20/11 11:10 (hora local), por OdooBot: corte web de las 11:00 (`koroshi.web.corte` 5, línea 83) |
| Nota en la OUT | «Cancelada por el corte de pedidos web de las 11:00: no estaba reservada del todo. Falta: 8445962749635 2521ML09-000003-L: 0 de 1» |

Las 5 líneas en el corte:

| Prenda | Reservada | Stock hoy en Odoo |
|---|---|---|
| 2521ML12-000006-L | 1 de 1 | 9 en L32 P31 C2 (1 reservada) + 2 en taras |
| 2521PL66-000039-L | 1 de 1 | 4 en L31 P30 C1 + 3 en taras |
| 2521PL05-000003-L | 1 de 1 | 16 en L31 P32 C1 |
| 2521PL34-000003-L | 1 de 1 | 5 en L31 P30 C2 (1 reservada) |
| **2521ML09-000003-L** | **0 de 1** | **0 desde el 21/10/2026** |

- Las cifras de la pantalla de KOROSHI (L = 9 de 2521ML12-000006 y L = 4 de 2521PL66-000039) **coinciden con Odoo**.
  Esas dos prendas estaban reservadas para el pedido.
- **2521ML09-000003-L**: la última unidad se quitó con un ajuste de inventario el 21/10/2026 16:55 (hora local) en L32 P33 C1
  («Cantidad de producto actualizada»). Desde entonces Odoo tiene 0 y no ha vuelto a entrar. También dejó sin servir
  S-6665004405 (18/11) y S-6665003666 (30/10), y hoy espera S-6665004761. **Hay que preguntar a KOROSHI cuánto stock
  tiene su sistema de 2521ML09-000003-L en el 6665**: si dice 1, su stock no recogió el ajuste del 21/10.
- **-02 y -02-02**: en Odoo no hay ningún pedido ni OUT con esos nombres (se ha buscado en todas las compañías). En su
  pantalla aparecen asignados al 6665 y anulados el 20/11 con el operador 000001: se crearon y se anularon dentro del
  TPV de KOROSHI, sin pasar por el almacén. Su pantalla enseña solo 2 líneas: puede que el -02 fuera el pedido rehecho
  con lo que sí había. Hay que preguntar a Betty o a KOROSHI quién es el operador 000001 y por qué se anularon. El
  almacén no lo puede saber.

## 2. Cómo cancela el corte (koroshi_agrupaciones_web 1.0.0, instalado el 18/11)

`models/corte.py:154-195`: en cada corte (06:00 y 11:00) coge las OUT web sin agrupación creadas antes de la hora; las
que no están **100 % reservadas** y no tienen nada leído se cancelan **enteras** (`action_cancel`) y se manda un
correo a Betty «que no tenían todo el stock. Hay que cancelarlos en el TPV de KOROSHI y rehacerlos con lo que sí hay».
Cancelación encendida desde el corte de las 11:00 del 19/11.

| Corte | OUT agrupadas | OUT canceladas |
|---|---|---|
| 19/11 06:00 | 45 | 0 (cancelación apagada) |
| 19/11 11:00 | 5 | 2 |
| 20/11 11:00 | 7 | 10 |
| 21/11 06:00 | 16 | 4 |
| 21/11 11:00 | 2 | 0 |
| 23/11 06:00 | 0 | 1 |
| 23/11 11:00 | 0 | 0 |
| 24/11 06:00 | 16 | 11 |
| 24/11 11:00 | 64 | 11 |
| **Total** | | **39 OUT, 97 uds** |

(El 20/11 06:00 y el 22/11 no tienen corte apuntado.)

- **24 de las 39** tenían otras líneas reservadas: **56 líneas con stock** se perdieron por **41 líneas sin stock**.
- 15 eran pedidos de una sola línea sin stock.

## 3. Las 41 líneas que faltaban: ¿había stock en Odoo a la hora del corte?

Stock reconstruido a la hora del corte: stock de hoy en ubicaciones internas menos lo que entró y más lo que salió
después (movimientos hechos). Ubicaciones «que se pueden preparar» = huecos de `EFFEC/Stock/NAVE2/`.

| Qué había en Odoo | Líneas |
|---|---|
| **Nada en ninguna ubicación** | 31 |
| Solo en **EFFEC/FALTANTE** (el operario no la encontró en el hueco) | 7 |
| Solo en **taras** (TARKO/…/KO_TARAS_…, prenda defectuosa) | 1 |
| Solo en **EFFEC/SORTER** (ya cogida para otro pedido) | 1 |
| **En un hueco de NAVE2** | **1** |

La única con stock en hueco: **2521TR17-000139-S** (W-0000059395, corte 20/11 11:00). Odoo tenía 7 en L24 P36 C2. El
19/11 a las 06:31 el operario la marcó como faltante (1 ud a FALTANTE, `KOROSHI Faltante EFFEC/INT/67393`), se canceló
la INT al sorter y la OUT se quedó sin reserva hasta que el corte la canceló. Odoo sigue diciendo que hay 6 en L24 P36
C2 (hoy reserva 2 para S-6665004761): **hay que contar ese hueco**.

Detalle (hora del corte en hora local):

| Corte | Pedido | Líneas del pedido | Prenda que faltaba | Stock en Odoo a esa hora |
|---|---|---|---|---|
| 19/11 11:00 | W-0000059345-02 | 4 | 2521TR13-000030-L | 1 en taras |
| 19/11 11:00 | W-0000059408-02 | 2 | 2621CL56-000014-XXL | 0 |
| 20/11 11:00 | W-0000059395 | 2 | 2521TR17-000139-S | **6 en L24 P36 C2** + 1 en FALTANTE |
| 20/11 11:00 | W-0000059438 | 3 | 2622PT01-000306-40 | 0 |
| 20/11 11:00 | **W-0000059444** | 5 | 2521ML09-000003-L | 0 |
| 20/11 11:00 | W-0000059471 | 3 | 2621TR46-000014-M | 0 |
| 20/11 11:00 | W-0000059479 | 3 | 2622JA16-000017-XS | 0 |
| 20/11 11:00 | W-0000059481 | 1 | 2621ML25-000039-S | 0 |
| 20/11 11:00 | W-0000059487-03 | 2 | 2522PT46-000017-36 | 1 en SORTER |
| 20/11 11:00 | W-0000059497 | 3 | 2622PT06-000301-44 | 0 |
| 20/11 11:00 | W-0000059526 | 3 | 2622JA00-000003-S | 4 en FALTANTE |
| 20/11 11:00 | W-0000059531 | 3 | 2621PT87-000014-L | 0 |
| 21/11 06:00 | W-0000059544 | 1 | 2621JA10-000003-XXL | 0 |
| 21/11 06:00 | W-5930007720 | 1 | 2511ZA09-000010-UNI | 0 |
| 21/11 06:00 | W-0000059547 | 4 | 2622VS34-000003-M | 0 |
| 21/11 06:00 | W-5930007721 | 6 | 2622PT20-000306-42 | 0 |
| 23/11 06:00 | W-5910008736-02 | 3 | 2611WA15-000323-L, 2611WA15-000027-M, 2611WA15-000027-L | 0 las tres |
| 24/11 06:00 | W-0000059578 | 1 | 2621PT87-000014-XL | 0 |
| 24/11 06:00 | W-0000059650 | 1 | 2521SU32-000002-L | 0 |
| 24/11 06:00 | W-0000059659 | 1 | 2621TR46-000016-XXL | 0 |
| 24/11 06:00 | W-0000059694 | 1 | 2622BL11-000003-M | 0 |
| 24/11 06:00 | W-0000059747 | 1 | 2525ML05-000039-10 | 5 en FALTANTE |
| 24/11 06:00 | W-0000059851 | 3 | 2622JA93-000003-S | 2 en FALTANTE |
| 24/11 06:00 | W-0000059852 | 3 | 2621JA04-000019-L | 0 |
| 24/11 06:00 | W-0000059869 | 4 | 2621SU01-000130-M | 0 |
| 24/11 06:00 | W-0000059927 | 3 | 2622VS37-000003-S | 0 |
| 24/11 06:00 | W-0000059929 | 3 | 2621TR46-000014-L | 0 |
| 24/11 06:00 | W-0000059610-02 | 4 | 2525ML05-000039-10 | 5 en FALTANTE |
| 24/11 11:00 | W-0000059942 | 1 | 2521PL28-000003-L | 1 en FALTANTE |
| 24/11 11:00 | W-0000059955 | 1 | 2622PT06-000301-44 | 0 |
| 24/11 11:00 | W-0000059974 | 1 | 2622VS16-000003-L | 0 |
| 24/11 11:00 | W-0000059976 | 6 | 2622ML18-000003-XS | 0 |
| 24/11 11:00 | W-0000059982 | 1 | 2522TR12-000003-XS | 1 en taras + 1 en FALTANTE |
| 24/11 11:00 | W-0000059987 | 4 | 2621ML08-000039-M | 0 |
| 24/11 11:00 | W-0000059994 | 1 | 2621TR46-000016-XXL | 0 |
| 24/11 11:00 | W-0000060011 | 1 | 2622VS34-000003-L | 0 |
| 24/11 11:00 | W-0000060030 | 2 | 2622VS16-000003-M | 0 |
| 24/11 11:00 | W-0000060033 | 1 | 2622ML51-000005-XS | 0 |
| 24/11 11:00 | W-0000060010-02 | 2 | 2522VS05-000323-XL | 1 en FALTANTE |

Muchas de estas prendas también se quedan sin servir en pedidos de tienda del mismo día (S-6665004512, -4513, -4612,
-4614, -4761…): **KOROSHI vende y reparte prendas que en Odoo están a 0**. Señal de que su stock del 6665 no es el de
Odoo (ajustes que no recoge, FALTANTE y taras que sí cuenta, o tránsito: su pantalla es «STOCK - TRÁNSITO»).

## 4. Cancelaciones a mano de la oficina (17 y 18/11, antes del corte automático)

Del 17 al 24/11 entraron 626 OUT web; 354 hechas y **99 canceladas**: 39 por el corte, 2 a mano el 20/11 (Almacen 2,
58547 y 58548-02, que ya iban a caer en el corte) y **58 a mano por «Almacén Nath»** (17/11 06:24-06:29 y 18/11
13:50-13:59, hora local, una cada 4-5 s, sin nota). Ya están en `pedidos-web-cancelados-odoo-noviembre_2026-11-20.md`.

De esas 58, **34** tenían al menos una prenda a 0 en los huecos. **24 tenían todas las prendas en huecos de NAVE2**
a la hora de cancelar (cantidad física; no se puede saber si estaban reservadas para tiendas en ese momento, porque al
cancelar se borra la reserva):

| Cancelada | Pedidos |
|---|---|
| 17/11 06:24-06:29 | 59060-02, 59078, 59086, 59132, 59171, 59187 |
| 18/11 13:52-13:58 | 59222, 59240-02, 59320, 59321, 59323, 59324, 59325, 59328, 59329, 59330-02, 59332-03, 59333, 59334, 59335, 59336, 59340, 59342, 59344 |

Ejemplos: 59324 (2621TR24-000003-M, 58 uds en huecos), 59342 (2622JA11-000003-S, 81), 59171 (2521ML12-000006-L, 10:
la misma prenda de Irati). Las del 18/11 se crearon entre las 09:31 y las 13:30 y se cancelaron a las 13:52: parece
que se cancelaba todo lo que no entraba en la agrupación del día, tuviera stock o no. **Hay que preguntar a la oficina
qué criterio usó.** Desde el 19/11 esto lo hace el corte y no se ha repetido.

## 5. Causas

1. **Todo o nada**: el corte cancela la OUT entera si falta una línea. Es la causa principal de lo que ve KOROSHI
   (24 de 39 pedidos, 56 líneas con stock perdidas).
2. **El stock de KOROSHI no es el de Odoo**: ajustes a mano que no les llegan (2521ML09-000003-L, 21/10), prendas en
   FALTANTE (7 líneas) y taras (2) que ellos pueden contar como stock, y tránsito. Por eso venden y reparten al 6665
   prendas que el almacén no tiene.
3. **Faltantes sin resolver**: el operario no encuentra la prenda; Odoo la pasa a FALTANTE y la OUT se cae en el
   siguiente corte, aunque el hueco aún diga que quedan (2521TR17-000139-S en L24 P36 C2).
4. **17-18/11: cancelación a mano** de 24 pedidos que tenían las prendas en los huecos (criterio por confirmar).
5. **-02 / -02-02**: se anulan en el TPV de KOROSHI sin llegar a Odoo; no es el almacén.

## 6. Qué se podría cambiar (sin programar todavía; lo decide Isaac)

1. **Corte por líneas, no por pedido**: cancelar solo las líneas sin stock (o dejar la OUT esperando un día más) y
   preparar el resto. Primero hay que saber si el TPV de KOROSHI admite anular una línea sin anular el pedido y qué
   hace con el -02 (lo sabe Betty). Toca `koroshi_agrupaciones_web` (hoy cogido por «Correcciones revisión general»,
   con la 1.1.0 sin instalar).
2. **Que el correo a Betty diga claro** qué línea falta y que las otras sí están reservadas, para que el -02 se rehaga
   solo con esas y no se vuelva a anular.
3. **Mandar a KOROSHI el stock preparable** del 6665 (huecos de NAVE2, sin FALTANTE, sin taras ni sorter) cada día, y
   pedirles el suyo de las 38 prendas del apartado 3 para ver dónde se separan. Ya hay un volcado:
   `20261123_stock_por_sku_odoo.csv`.
4. **Contar los huecos con faltante** antes del corte (ronda de faltantes / `koroshi_recuentos`) y, si aparece la
   prenda, que la OUT vuelva a reservar en vez de caer. Empezar por L24 P36 C2 (2521TR17-000139-S).
5. **Avisar de los ajustes a mano** que dejan a 0 una prenda que KOROSHI sigue vendiendo.

## Cómo se ha hecho

- RPC de solo lectura (`search_read`, `read`, `search_count`) desde la pestaña de nath.tuctuc.com del navegador
  integrado: `sale.order`, `stock.picking`, `stock.move`, `stock.move.line`, `stock.quant`, `mail.message`,
  `koroshi.web.corte` y `koroshi.web.corte.linea`.
- Stock a la hora del corte: reconstruido con los movimientos hechos posteriores. No tiene en cuenta reservas de otros
  pedidos en ese momento (no quedan guardadas), así que «había stock» quiere decir stock físico, no libre.
- No se ha mirado S4T (el -02 y el -02-02 podrían estar allí): pendiente si hace falta.

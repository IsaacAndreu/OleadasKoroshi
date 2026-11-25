# Estudio: implantar los módulos KOROSHI en odoo.tuctuc.com (24/11/2026)

**Solo estudio.** No se ha instalado, copiado ni consultado nada en el servidor de tuctuc: todo sale del código del
repositorio (`odoo/modulos/`, rama `main`, commit `ff40e88`). Lo que hay que mirar en tuctuc está marcado con
**[comprobar en tuctuc]** y las consultas, en solo lectura, están en el apartado 6.

Alcance: los 32 módulos `koroshi_*`. Los otros 6 de `odoo/modulos/` no entran: `tuctuc_rendimiento` (descartado),
`multi_search_with_comma`, `l10n_es_aeat_mod347/349` y `dms_package_consume` ya son de tuctuc, y `oriola_monitor` es
del almacén de Oriola.

## 1. Conclusión en cuatro líneas

1. **Ningún módulo KOROSHI se puede instalar en tuctuc tal cual.** Todos dependen de la compañía 8 (`comun.COMPANY_ID`,
   155 usos en Python, y `cids=8` en el JS del monitor), de nombres de NAU-2 (`EFFEC/Stock/NAVE2`, `KO_`/`TT_`,
   `SORTER`, `PED. TIENDAS`, `XPO SAS`) o de S4T.
2. **Dos módulos harían daño en tuctuc nada más instalarse**: `koroshi_menu` (archiva el menú de **Punto de venta**,
   CRM, Web, Fabricación, Proyecto… para todos) y `koroshi_delegacion` (columna e índice nuevos en `stock_picking`
   creados con la tabla bloqueada, más un `UPDATE` de todos los albaranes). Más abajo, el detalle.
3. Lo que **sí puede tener sentido** es el bloque «PDA de almacén»: `base`, `operarios`, `faltantes`, `preparacion`,
   `caja_existente`, `contenedores`, `recuentos`, `devoluciones`, `prenda_suelo`, `pda_app`, `buscador_stock`,
   `ubicaciones`, `recepcion`, `consumibles` y quizá `actividades`. Antes, `koroshi_base` tiene que dejar de llevar
   la compañía 8 escrita en el código.
4. Antes de nada, **hay que arreglar en tuctuc la apertura de Lecturas** (`stock_barcode`
   `get_all_locations_by_barcode`: 18 s cada vez, por las ~730.000 ubicaciones con código de barras). Todo el bloque
   PDA pasa por Lecturas.

## 2. Tabla por módulo

Columnas: **Sentido** (Sí / Quizá / No en tuctuc) · **Depende de** (Odoo y propios) · **Qué hay que adaptar** ·
**Riesgo** en tuctuc · **Esfuerzo** (S: horas, M: 1-3 días, L: una semana o más). LOC = líneas de código propias.

### 2.1 Base y bloque PDA (lo que podría servir)

| Módulo | Para qué | Sentido | Depende de | Qué hay que adaptar | Riesgo | Esf. |
|---|---|---|---|---|---|---|
| `koroshi_base` (541 LOC) | Constantes comunes: compañía, hora del almacén, rangos de días en UTC, matrícula CJ, turnos, tarjeta de la PDA | Sí (lo necesitan todos) | `base`, `web` | `COMPANY_ID = 8` es una constante en `comun.py:14` que se lee al importar. Pasarla a parámetro de sistema (`koroshi_base.company_id`) o a una función `comun.company_id(env)` con 8 por defecto. `TZ`, `RE_CJ` y `TURNOS` (parámetro `koroshi_base.turnos`) se revisan con tuctuc | Bajo en tuctuc. **Alto en NAU-2**: un `-u koroshi_base` actualiza ~23 módulos en producción | M |
| `koroshi_operarios` (5.718) | Cola de pedidos por operario en la PDA: tarjeta una vez, siguiente pedido solo; tablero del responsable | Quizá (si tuctuc prepara pedidos con PDA y operarios) | `web`, `mail`, `hr`, `stock`, `stock_picking_batch`, `stock_barcode` (EE), base | Empleados con tarjeta (`hr`), grupos (Tablero, tarjeta obligatoria), 6 parámetros `koroshi_operarios.*`, cron cada 5 min. Las migraciones que meten usuarios por nombre («Almacen 2», Departament IT, Ismael) solo corren al actualizar, no en una instalación nueva | Medio: abre `stock_barcode` (Lecturas lento, ver 4.1). SQL en `models/reparto.py:316-419` sobre `stock_move`/`stock_move_line` filtrado por compañía y estado | L |
| `koroshi_faltantes` (2.613) | Pieza que no está: buscar otra ubicación con stock libre, cambiar la reserva y llevar la que falta a FALTANTE | Quizá | `web`, `hr`, `stock`, `stock_picking_batch`, `stock_barcode`, base, operarios | `data/ubicacion.xml:10-11`: crea la ubicación FALTANTE buscando el almacén `EFFEC` **de la compañía 8** y le pone `company_id = 8` (escrito a mano, no usa `comun`). En tuctuc, o falla o la crea en otra compañía. Cron cada 15 min | Medio: si la compañía 8 existe en tuctuc y es otra, crea la ubicación en ella **[comprobar en tuctuc]** | M |
| `koroshi_preparacion` (6.450) | Preparar la OUT dentro de Lecturas: leer, cerrar caja con la CJ y validar | Quizá (núcleo de la PDA) | `web`, `hr`, `stock`, `stock_picking_batch`, `stock_barcode`, base, operarios, faltantes, **consumibles** | Matrícula CJ, tipos de caja (consumibles), parámetros `koroshi_preparacion.*`, nombres `OUT` en `models/lectura.py`. Bloquea filas con `FOR UPDATE NOWAIT` (`lectura.py:586`) | Alto si se usa: valida OUT y mueve stock; todo pasa por Lecturas | L |
| `koroshi_consumibles` (639) | Control de cajas y materiales fuera del stock de prendas | Quizá | `base`, `mail`, `stock`, `delivery`, **`koroshi_warehouse_map`** | Las cajas iniciales (`data/cajas.xml`: `_cajas_koroshi_iniciales`) son las de KOROSHI. La dependencia de `warehouse_map` (mapa de NAU-2) obliga a llevarse el mapa: cortarla | Bajo | S-M |
| `koroshi_caja_existente` (230) | PDA: leer la CJ de una caja ya hecha y meter las uds leídas en ella | Quizá | `stock`, **`stock_barcode_optimization`** [¿existe en tuctuc?], base | Ninguna fuera de la compañía | **Toca `stock.picking`**: hereda `write` y `action_done` (`models/stock_picking.py:176-186`); cada escritura de estado o bultos de **cualquier** albarán de tuctuc (también los del TPV) pasa por aquí. Sale enseguida si no es de la compañía, pero es código en el camino de todos | S |
| `koroshi_contenedores` (2.752) | Mover contenedores KO_/TT_ con sus prendas, compactar huecos, ver inventario por lineal | Quizá | `web`, `stock`, `hr`, `barcodes`, base, operarios, faltantes | Prefijos `KO_`/`TT_` y lineales de NAU-2 | Medio: búsquedas de ubicaciones por nombre (ver 4.2) | M |
| `koroshi_recuentos` (1.930) | PDA: una referencia con todas sus tallas, dónde está, cuánto dice Odoo y su recuento | Quizá | `web`, `stock`, `hr`, `barcodes`, base, operarios | Compañía; límites en `controllers/main.py:25-30` | Medio: lee `stock.quant` por producto y ubicación | M |
| `koroshi_devoluciones` (1.895) | Ubicar devoluciones (opción, prendas y contenedor) con informe | Quizá | `web`, `stock`, `hr`, `barcodes`, base, operarios | Compañía; textos de S4T (2 referencias); `data/datos.xml` | Bajo | M |
| `koroshi_prenda_suelo` (1.211) | PDA: prenda encontrada en el suelo → a qué faltante o compañero va | Quizá | `web`, `stock`, `hr`, `barcodes`, base, operarios, preparacion, faltantes | Compañía | Bajo | S |
| `koroshi_pda_app` (196) | Lecturas como app instalable en la PDA | Quizá | `web`, base, operarios | URL `/web#cids=8&action=…` (`controllers/main.py:25`); parámetro `koroshi_pda_app.usuarios` = `2` al instalar (en tuctuc el usuario 2 será otro) | Bajo (hereda `web.layout` solo para los usuarios del parámetro) | S |
| `koroshi_actividades` (3.749) | Manipulaciones: tarjeta en el portátil, qué hace cada persona y cuánto tarda | Quizá | `web`, `hr`, `barcodes`, base, operarios | Actividades y áreas de KOROSHI (`data/actividades.xml`, `areas_pda.xml`), destinos de inversa, 3 crons (5, 5 y 15 min), 7 referencias a S4T | Bajo | M |
| `koroshi_buscador_stock` (798) | Pantalla de oficina: buscar stock por EAN, referencia, hueco, lineal o contenedor | Quizá (útil para cualquier almacén) | `web`, `stock`, `product`, base, **`koroshi_menu`** | Prefijos `KO_`/`TT_` (`controllers/main.py:100-101`); usa `product.barcode` (de `product_multi_barcode`) si existe. Cortar la dependencia de `koroshi_menu` | **Alto en rendimiento**: `name =ilike '%texto%'` sobre `stock.location` (`main.py:100`, `289`) = recorrido entero de ~760.000 ubicaciones sin índice trigrama; `read_group` de `stock.quant` (6,8 M) | M |
| `koroshi_ubicaciones` (660) | Botón que crea contenedores KO_/TT_ o los huecos de un lineal e imprime etiquetas 4x6 | Quizá | `stock`, base, **`koroshi_menu`** | Padre fijo `EFFEC/Stock/NAVE2` (`models/crear.py:15`), prefijos, formato de etiqueta | Bajo (crea hasta 2.000 ubicaciones por tanda: tuctuc ya tiene demasiadas) | S-M |
| `koroshi_recepcion` (2.613) | Recibir un contenedor marítimo caja a caja: caja KO_, palé A/B, prendas | Quizá | `web`, `mail`, `stock`, `hr`, base, **menu**, ubicaciones | Compañía, nombres de ubicación (4), etiqueta de tanda | Medio (mueve stock) | M |

### 2.2 Específicos de KOROSHI, S4T, XPO o NAU-2 (no tienen sentido en tuctuc tal como están)

| Módulo | Para qué | Sentido | Depende de | Por qué no / qué habría que cambiar | Riesgo si se instala | Esf. |
|---|---|---|---|---|---|---|
| `koroshi_menu` (1.527) | App KOROSHI (Hoy, Faltantes, Personas, Almacén, KPI, Ajustes) y bandeja del jefe | **No tal cual** | `stock`, base, kpi, operarios, preparacion, zonas, warehouse_map, monitor, consumibles, faltantes, contenedores, actividades | Es el «cubo» que arrastra casi todo. **`models/apps.py` + `views/apps.xml` archivan, en cada instalación y actualización, los menús raíz de Punto de venta, CRM, Sitio web, Helpdesk, Fabricación, Proyecto, Asistencias, Tableros… y los menús 857 y 1178 si coinciden de nombre.** En tuctuc dejaría a las tiendas sin el TPV en el menú | **Muy alto** | L |
| `koroshi_delegacion` (150) | Campo Delegación en los albaranes (de la etiqueta de la tienda) | No (además, «no instalar todavía» en NAU-2) | `stock` | **Campo nuevo en `stock.picking`** con `index=True` (`models/stock_picking.py:39`): el `-u` crea el índice sin `CONCURRENTLY` (bloquea escrituras en `stock_picking`, también las del TPV) y hace un `UPDATE` de todos los albaranes (`:19-33`). Regla 7 del CLAUDE.md | **Alto** | S (si se quisiera: columna e índice a mano antes, `CONCURRENTLY`) |
| `koroshi_zonas` (6.011) | Partir los pedidos de tienda por zonas de picking (motor v12f) | No | `mail`, `stock`, `stock_picking_batch`, kpi, base | Atado a la operativa de KOROSHI: tipo `PED. TIENDAS`, `Z-ddmm-…`, `KO_`/`TT_`, litros por caja. **Mira el cron con id 202 escrito a mano** (`models/ejecucion.py:654`): en tuctuc el 202 es otro cron y, si está activo, no parte nada. 6 crons | Alto (crons sobre OUT de la compañía) | L |
| `koroshi_monitor` (5.382) | Pantalla en directo de las agrupaciones por zonas y cierre del camión XPO | No | `web`, `mail`, `stock`, `stock_picking_batch`, base, warehouse_map | Zonas Z-, `XPO SAS`, `cids=8` en `static/src/js/monitor.js:31` y `envios.js:250,539`, correo a expediciones@koroshi.tv | Medio | L |
| `koroshi_warehouse_map` (1.033) | Mapa editable y operativo de picking de NAU-2 | No (es el plano de NAU-2) | `web`, `stock`, `stock_picking_batch`, base | Plano de otra nave; solo serviría rehaciendo el plano | Bajo | M |
| `koroshi_kpi` (2.205) | KPI diarios: uds, profundidad por SKU, peso, volumen, metros | Quizá más adelante | `stock`, `sale_stock`, base | 18 referencias a XPO, pesos por tipo de KOROSHI (`data/peso_tipo.xml`), 2 crons (21:30 y 04:30) | Medio: recalcula días enteros de `stock.move` de la compañía | M |
| `koroshi_informe` (1.564) | Correo diario/semanal/mensual de productividad | No (sin operarios/KPI/monitor no tiene datos) | `mail`, base, operarios, kpi, preparacion, menu, monitor | Destinatarios y formato KOROSHI | Bajo | M |
| `koroshi_agrupaciones_web` (792) | Cortes de pedidos web 06:00 y 11:00: cancela los incompletos y agrupa en WEB_ddmmaa_NN | No | `mail`, `stock`, `sale_stock`, `stock_picking_batch`, base, menu | Reglas y avisos de KOROSHI (Betty). **Cancela OUT**: no se instala sin decidir la regla con tuctuc | Alto (cancela pedidos) | M |
| `koroshi_retener_tiendas` (1.006) | Retiene pedidos de tienda duplicados antes de las zonas | No | `mail`, `sale_stock`, base, menu | Pregunta a S4T (45 referencias), tipo `PED. TIENDAS`, correos a betty@, j.luis@ e isaac.andreu@ | Alto (puede cancelar OUT) | M |
| `koroshi_s4t_pedidos` (1.180) | Pedidos S4T grandes sin «could not serialize»; reserva por prioridad a las 03:30 | No (salvo que tuctuc use S4T) | `api_s4t_batch_update_PROD` [¿en tuctuc?], `sale_stock`, `queue_job`, `stock_picking_batch`, base | **Hereda `sale.order.action_confirm` y `stock.move`**; canal `root.s4t_sync`; ubicación `SORTER`; referencia el cron de `koroshi_zonas` | Alto (confirmación de todos los pedidos) | L |
| `koroshi_s4t_envios` (743) | Envía a S4T transportista, tracking y bultos | No | `api_s4t_batch_update_PROD`, `delivery`, `sale_stock`, xpo_bultos | S4T y XPO | — | M |
| `koroshi_s4t_sync` (74) | Deja sincronizar con S4T pedidos con backorders canceladas | No | `api_s4t_batch_update_PROD`, `sale_stock` | S4T | — | S |
| `koroshi_s4t_traspasos` (679) | Descarga de S4T devoluciones e-commerce y correcciones de traspasos | No | `api_s4t_batch_update_PROD`, `stock`, base | S4T, `stock.stock_location_customers` | — | M |
| `koroshi_xpo_bultos` (162) | XPO: cajas distintas y 15 kg / 0,09 m³ por bulto | Solo si tuctuc envía con XPO | `delivery_xpo` [¿en tuctuc?], base | Hereda `delivery.carrier` (afecta a todos los envíos XPO de la base) | Medio | S |
| `koroshi_rendiment` (205) | Botones Previsto y Stock rápidos | **No: ya está hecho en tuctuc** en el núcleo (24/11) | `stock`, `product_multi_barcode` | Hereda `stock.quant`, `product.product` y `report.stock.quantity`, lo mismo que se ha corregido en el núcleo de tuctuc: chocaría | Alto (pisa el arreglo del núcleo) | — |
| `koroshi_sesiones` (210) | Las sesiones con usuario no se borran nunca | No hace falta salvo que las PDA pierdan la sesión | `base` | Hereda `ir.autovacuum` (afecta a toda la base) | Bajo-medio: las sesiones del TPV y de todos los usuarios se acumulan en disco | S |

## 3. Dependencias

### 3.1 Módulos Odoo que hacen falta (fuera de KOROSHI)

| Módulo | Tipo | Lo piden | En tuctuc |
|---|---|---|---|
| `base`, `web`, `mail`, `product`, `stock`, `sale_stock`, `delivery`, `barcodes`, `hr` | Community | casi todos | `stock`, `sale_stock` seguro; `hr` y `barcodes` **[comprobar en tuctuc]** |
| `stock_picking_batch` | Community | operarios, faltantes, preparacion, monitor, zonas, warehouse_map, agrupaciones_web, s4t_pedidos | **[comprobar en tuctuc]** |
| `stock_barcode` | **Enterprise** | operarios, faltantes, preparacion | Sí (el traspaso del 24/11 lo nombra) |
| `stock_barcode_optimization` | De terceros o propio de NATH | caja_existente | **[comprobar en tuctuc]**; si no está, hay que traerlo |
| `queue_job` | OCA | s4t_pedidos | Sí (la cola de exportaciones) |
| `api_s4t_batch_update_PROD` | Integración S4T de NATH | los 4 `s4t_*` | **[comprobar en tuctuc]** |
| `delivery_xpo` | Transportista XPO | xpo_bultos | **[comprobar en tuctuc]** |
| `product_multi_barcode` | OCA | rendiment (y lo usa buscador_stock si está) | **[comprobar en tuctuc]** |

### 3.2 Dependencias entre módulos KOROSHI

```
koroshi_base
 ├─ koroshi_operarios ─┬─ koroshi_faltantes ─┬─ koroshi_contenedores
 │                     │                     └─ koroshi_preparacion (también consumibles) ── koroshi_prenda_suelo
 │                     ├─ koroshi_recuentos, koroshi_devoluciones, koroshi_actividades, koroshi_pda_app
 ├─ koroshi_warehouse_map ─┬─ koroshi_consumibles (→ preparacion)
 │                         └─ koroshi_monitor
 ├─ koroshi_kpi ── koroshi_zonas
 ├─ koroshi_caja_existente, koroshi_xpo_bultos, koroshi_s4t_pedidos, koroshi_s4t_traspasos
 └─ koroshi_menu (depende de 11 módulos) ─┬─ koroshi_buscador_stock, koroshi_ubicaciones ── koroshi_recepcion
                                          ├─ koroshi_agrupaciones_web, koroshi_retener_tiendas
                                          └─ koroshi_informe (también kpi, preparacion, monitor)
```

Dos dependencias impiden instalar el bloque PDA sin arrastrar lo de NAU-2:
- **`koroshi_consumibles` → `koroshi_warehouse_map`**: sin cortarla, `preparacion` se lleva el plano de NAU-2.
- **`buscador_stock`, `ubicaciones`, `recepcion` → `koroshi_menu`**: `koroshi_menu` arrastra zonas, monitor, kpi… y
  oculta el TPV. Hay que cortarlas (que pongan su menú en Inventario si `koroshi_menu` no está) o partir
  `koroshi_menu` en dos (la app y la «limpieza de iconos», que en tuctuc no se instalaría).

## 4. Rendimiento en la base de tuctuc

Cifras de partida: 20 M de `stock_move`, 6,8 M de `stock_quant`, ~760.000 ubicaciones (259.126 activas con código de
barras según el encargo; el traspaso del 24/11 dice 730.337 con código: **[comprobar en tuctuc]** cuál vale).

1. **Lecturas (`stock_barcode`)**: `get_all_locations_by_barcode` tarda 18 s y se llama al abrir Lecturas. Operarios,
   faltantes y preparación viven dentro de Lecturas: con la PDA abriendo y cerrando OUT todo el día, cada apertura
   serían 18 s y una consulta pesada en la base del TPV. **Requisito previo**: arreglarlo en el núcleo de tuctuc
   (lo lleva la sesión de rendimiento).
2. **Búsquedas por nombre de ubicación con `%texto%`** (`buscador_stock`, `contenedores`, `recuentos`,
   `ubicaciones`): en NAU-2 hay pocas ubicaciones; en tuctuc es un recorrido de toda `stock_location`. Hace falta un
   índice trigrama (`pg_trgm`) en `stock_location.name`/`barcode` o limitar por ubicación padre del almacén.
   **[comprobar en tuctuc]** con `EXPLAIN` (sin `ANALYZE`) en solo lectura.
3. **Crons**: los módulos traen ~20 crons (cada 5 o 15 min: operarios, actividades ×3, faltantes, informe,
   agrupaciones_web, retener_tiendas, zonas vigilante; diarios: kpi ×2, zonas ×4, s4t_pedidos). Todos filtran por
   la compañía, así que el coste depende del volumen de la compañía de tuctuc que se configure. En tuctuc la
   cola tiene 5 plazas y las exportaciones de stock ya la llenan: los crons del ERP no van por la cola, pero sí cargan
   la misma base. Los de NAU-2 solo se instalarían si se instala su módulo.
4. **Tablas compartidas**:
   - Campo nuevo: solo `koroshi_delegacion` (`stock.picking.koroshi_delegacion`, con índice). No instalar.
   - Herencias de métodos en todo el modelo: `caja_existente` (`stock.picking.write`/`action_done`),
     `s4t_pedidos` (`sale.order.action_confirm`, `stock.move`), `xpo_bultos` (`delivery.carrier`),
     `rendiment` (`stock.quant`, `product.product`, `report.stock.quantity`), `sesiones` (`ir.autovacuum`),
     `pda_app` (`res.users`, solo un método nuevo).
   - El resto crea tablas propias (`koroshi_*`): no toca `stock_picking`, `stock_move`, `stock_move_line` ni
     `stock_quant` en su estructura.
5. **Instalación**: los `<function>` que corren al instalar (`kpi.recalcular_todo`, `zonas._rellenar_campos`,
   `zonas.config`, `consumibles._cajas_koroshi_iniciales`, `menu.ocultar_apps`) solo escriben en tablas propias,
   salvo `ocultar_apps` (menús). En una instalación nueva no hay días que recalcular.

## 5. Orden de implantación propuesto

Solo si Isaac decide seguir (pregunta 1). Cada paso con su versión, etiqueta y ZIP, y sin tocar el servidor sin su sí.

0. **Requisitos en tuctuc** (sin módulos KOROSHI): arreglar la apertura de Lecturas; ver qué módulos de 3.1 hay; ver
   qué es la compañía 8 en tuctuc; decidir la compañía y el almacén de tuctuc que usarían la PDA.
1. **`koroshi_base` con la compañía configurable** (parámetro o función con 8 por defecto). Se prueba primero en NAU-2
   (debe quedar igual: el parámetro vacío = 8) y se instala allí fuera de horas (arrastra ~23 módulos).
2. **Pasar los módulos del bloque PDA a la compañía configurable**, uno a uno y cada uno con su versión (regla 8 del
   CLAUDE.md): operarios → faltantes (FALTANTE sin el 8 escrito a mano) → consumibles (sin `warehouse_map`) →
   preparacion → caja_existente → contenedores, recuentos, devoluciones, prenda_suelo, pda_app → actividades.
   Prefijos y padres (`KO_`, `TT_`, `EFFEC/Stock/NAVE2`, `SORTER`) a parámetros.
3. **Cortar la dependencia de `koroshi_menu`** en buscador_stock, ubicaciones y recepción, y meter un índice trigrama
   (o el filtro por almacén) antes de instalar `buscador_stock`.
4. **Prueba en una copia de tuctuc** (no en producción): instalar `base` → `operarios` → `faltantes` →
   `consumibles` → `preparacion` y preparar OUT reales de la copia con una PDA. Medir tiempos.
5. Instalación en tuctuc fuera del horario de tiendas, de uno en uno.
6. Más adelante, si tiene sentido: `kpi`, una versión de `menu` sin `ocultar_apps`, `informe`.
7. **No se instalan**: zonas, monitor, warehouse_map, agrupaciones_web, retener_tiendas, los cuatro `s4t_*`,
   xpo_bultos (salvo XPO), rendiment, delegacion, sesiones (salvo problema de sesiones en las PDA).

Esfuerzo total del camino 1-5 (bloque PDA, sin la prueba en almacén): **L, del orden de 2-3 semanas** de trabajo, la
mayor parte en el paso 2 (155 usos de `COMPANY_ID` repartidos en 23 módulos) y en las pruebas.

## 6. Qué hay que comprobar en tuctuc (solo lectura)

Con la conexión del apartado «Servidor» de `bin/versiones/20261124_traspaso_rendimiento_odoo-tuctuc.md`
(`PGOPTIONS='-c default_transaction_read_only=on'`):

```sql
-- 1. Módulos de los que dependen
SELECT name, state, latest_version FROM ir_module_module
 WHERE name IN ('hr','barcodes','stock_picking_batch','stock_barcode','stock_barcode_optimization','queue_job',
                'api_s4t_batch_update_PROD','delivery_xpo','product_multi_barcode','sale_stock','delivery')
    OR name LIKE 'koroshi%' ORDER BY name;
-- 2. Qué es la compañía 8 y qué almacenes hay
SELECT id, name FROM res_company ORDER BY id;
SELECT id, code, name, company_id FROM stock_warehouse ORDER BY company_id, id;
-- 3. Qué es el cron 202 (koroshi_zonas lo mira por id)
SELECT id, cron_name, active FROM ir_cron WHERE id = 202;
-- 4. Ubicaciones: cuántas hay y cuántas con código
SELECT count(*) FILTER (WHERE active), count(*) FILTER (WHERE active AND barcode IS NOT NULL), count(*)
  FROM stock_location;
-- 5. ¿Está pg_trgm?
SELECT extname FROM pg_extension;
```

## 7. Qué hay que preguntar a Isaac

1. **Para qué se quiere en tuctuc**: ¿hay un almacén de tuctuc que vaya a preparar pedidos con PDA (cuál, de qué
   compañía), o se busca solo alguna pantalla suelta (p. ej. el buscador de stock)? De esto depende todo lo demás.
2. ¿tuctuc usa S4T y XPO? (si no, fuera los `s4t_*` y `xpo_bultos`).
3. ¿Se acepta tocar `koroshi_base` en NAU-2 para que la compañía sea configurable? (un `-u` arrastra ~23 módulos).
4. ¿Hay una copia de `TUCTUC_PRODUCTION` donde probar, o hay que pedirla?
5. ¿Quién mantendría dos instalaciones del mismo módulo (NAU-2 y tuctuc) con la regla de «un módulo, una sesión»?

## 8. Riesgos

| Riesgo | Cómo se evita |
|---|---|
| `koroshi_menu` oculta el TPV y otras apps a todo tuctuc | No instalarlo; si se quiere la app, partirlo y dejar la limpieza de iconos solo en NAU-2 |
| `koroshi_delegacion` bloquea `stock_picking` al crear el índice y reescribe todos los albaranes | No instalarlo (ya está así en NAU-2) |
| Compañía 8 de tuctuc = otra empresa: FALTANTE y otros datos acabarían en ella | Compañía configurable antes de instalar nada; comprobar `res_company` |
| `koroshi_zonas` mira el cron 202 por id | No instalar zonas; si algún día, buscar el cron por xmlid |
| Lecturas a 18 s por apertura con la PDA todo el día | Arreglo previo en el núcleo de tuctuc |
| Búsquedas `%texto%` en 760.000 ubicaciones | Índice trigrama o filtro por almacén; `EXPLAIN` antes |
| Cambiar `koroshi_base` rompe NAU-2 (PDA parada) | Versión con 8 por defecto, misma conducta probada con los tests de `koroshi_base/tests`, instalación fuera de horas |
| `koroshi_rendiment` pisa los arreglos del núcleo de tuctuc | No instalarlo |
| Dos servidores con el mismo módulo y versiones distintas | Un solo repo y una sola versión por módulo; `desplegar.sh` con `ADDONS_DIR` de tuctuc (`/opt/tuctuc-erp/nath/...`) en vez de `/opt/nath-erp` |
| Credenciales y correos de KOROSHI (Betty, José Luis, expediciones@koroshi.tv) en parámetros | Pasar los destinatarios a parámetros vacíos al instalar en tuctuc |

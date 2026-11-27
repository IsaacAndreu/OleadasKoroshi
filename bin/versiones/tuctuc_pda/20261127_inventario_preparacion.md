# Inventario para clonar a `tuctuc_*`: koroshi_preparacion, koroshi_consumibles, koroshi_warehouse_map, koroshi_caja_existente

Repo: `OleadasKoroshi/odoo/modulos/` (rama feat/tuctuc-pda, solo lectura).
Destino: odoo.tuctuc.com (Odoo 13 EE), almacén físico Oriola-Amposta, MULTIEMPRESA: PRIME COLLECTIONS (company 1, WH-OR),
UNITED BRANDS 2015 (company 21, UBRAN), MODA INTIMA 1964 (company 23, MODAI).

Las rutas de archivo son relativas a `odoo/modulos/`. "no encontrado" = se ha buscado y no existe.

---------------------------------------------------------------------------------------------------------------------

## A. Inventario por módulo

### A.1 koroshi_preparacion (v13.0.3.38.1, author NATH)

**Depende de** (`__manifest__.py:265-267`): `web, hr, stock, stock_picking_batch, stock_barcode, koroshi_base, koroshi_operarios, koroshi_faltantes, koroshi_consumibles`.
NO depende de koroshi_warehouse_map ni de koroshi_caja_existente (aunque usa la segunda indirectamente vía `put_in_pack`, ver E).

| Archivo | Líneas |
|---|---|
| `__init__.py` | 3 |
| `__manifest__.py` | 284 (casi todo es historial de versiones en `description`) |
| `README.md` | 600 |
| `controllers/__init__.py` | 2 |
| `controllers/main.py` | 372 |
| `data/parametros.xml` | 16 |
| `data/parametros_v315.xml` | 12 |
| `data/parametros_v317.xml` | 13 |
| `data/parametros_v322.xml` | 19 |
| `data/parametros_v334.xml` | 12 |
| `migrations/13.0.3.29.0/pre-migrate.py` | 29 |
| `models/__init__.py` | 6 |
| `models/lectura.py` | 1479 |
| `models/agrupacion.py` | 465 |
| `models/ruta.py` | 124 |
| `models/tarea.py` | 48 |
| `models/preferencia.py` | 38 |
| `models/caja_llena.py` | 52 |
| `security/ir.model.access.csv` | 9 |
| `static/src/css/preparacion.css` | 866 |
| `static/src/js/preparacion.js` | 3263 |
| `static/src/xml/preparacion.xml` | 267 |
| `tests/__init__.py` | 4 |
| `tests/test_idempotencia.py` | 204 |
| `tests/test_ruta.py` | 111 |
| `tests/test_validar_parcial.py` | 96 |
| `views/assets.xml` | 9 |
| `views/lectura_views.xml` | 78 |
| `views/caja_llena_views.xml` | 63 |

**Modelos definidos (`_name`)**
- `koroshi.preparacion.lectura` — `models/lectura.py:76` (Model). Campos: fecha, picking_id, move_line_id, employee_id, user_id, tipo (leer/deshacer/caja/validar/mover), codigo, producto, cantidad, resultado, mensaje, id_lectura, deshecha, en_caja, diferida. Contiene TODA la lógica (estado, leer, deshacer, poner_cantidad, caja, mover_caja, validar, ronda, impresos…).
- `koroshi.preparacion.equipo` — `models/lectura.py:1449` (Model). OUT a dos. `_sql_constraints pareja_unica` (1464-1467).
- `koroshi.preparacion.agrupacion` — `models/agrupacion.py:33` (AbstractModel). Agrupaciones Z- enteras.
- `koroshi.preparacion.preferencia` — `models/preferencia.py:12` (Model, color de la franja por operario; `employee_uniq`).
- `koroshi.preparacion.caja_llena` — `models/caja_llena.py:11` (Model). Respuestas «¿Caja llena?». Campo `tipo_caja_id` Many2one a `koroshi.consumable.item` (línea 18).
- Clase `Ocupada(UserError)` — `models/lectura.py:70` (excepción, no modelo).
- `models/ruta.py`: Python puro (sin modelo), geometría NAU-2.

**Modelos heredados (`_inherit`)**
- `koroshi.operario.tarea` (de koroshi_operarios) — `models/tarea.py:15`: sobreescribe `_uds_hasta_ahora` (27) y `_cerrar` (34); escribe `uds_inicio, uds_fin, a_dos, companero_id, nota`.
- Ningún `_inherit` de modelos estándar de stock.

**Controladores / rutas** (`controllers/main.py`, todas `type='json', auth='user'`):
| Ruta | Línea |
|---|---|
| `/koroshi/preparacion/modo` | 101 |
| `/koroshi/preparacion/cargar` | 115 |
| `/koroshi/preparacion/leer` | 129 |
| `/koroshi/preparacion/deshacer` | 153 |
| `/koroshi/preparacion/caja` | 175 |
| `/koroshi/preparacion/cantidad` | 199 |
| `/koroshi/preparacion/rechazadas` | 224 |
| `/koroshi/preparacion/color` | 248 |
| `/koroshi/preparacion/caja_llena` | 260 |
| `/koroshi/preparacion/mover_caja` | 277 |
| `/koroshi/preparacion/impresos` | 295 |
| `/koroshi/preparacion/ronda_marcar` | 308 |
| `/koroshi/preparacion/validar` | 324 |

**JS (`static/src/js/preparacion.js`)**
- `odoo.define('koroshi_preparacion.Pantalla')` — línea 1. `AbstractAction.extend` (91). Registra el client action tag **`koroshi_preparacion_pantalla`** (3058).
- `odoo.define('koroshi_preparacion.Lecturas')` — línea 3063. `require('koroshi_operarios.Pantalla')` (3067) + `Operarios.include({...})` (3073-3207).
- `odoo.define('koroshi_preparacion.Faltantes')` — línea 3212. `require('koroshi_faltantes.Pantalla')` (3216) + `Faltantes.include({...})` (3218-3262).
- requires estándar: `web.AbstractAction`, `web.core`, `web.session` (50-52).
- localStorage: `koroshi_operarios_sonido` (61, compartido con Lecturas), `koroshi_preparacion_pda` (62), `koroshi_preparacion_cola` (72), `koroshi_preparacion_caducadas` (74), claves de tipo de caja y color por operario (1099, 1194, 1233, 1496, 1505).

**Acciones / vistas** (`views/lectura_views.xml`, `views/caja_llena_views.xml`)
- `action_koroshi_preparacion_pantalla` (ir.actions.client, tag `koroshi_preparacion_pantalla`) — lectura_views.xml:65-68.
- `action_koroshi_preparacion_lectura` (42), `action_koroshi_preparacion_rechazadas_cola` (51), `action_koroshi_preparacion_caja_llena` (caja_llena_views.xml:47).
- Menús con `parent="koroshi_operarios.menu_koroshi_operarios_root"` y `groups="koroshi_operarios.grupo_productividad"` — lectura_views.xml:70-77, caja_llena_views.xml:59-62.

**Assets**: `views/assets.xml:3` template `assets_backend` hereda `web.assets_backend` (CSS + JS). QWeb: `static/src/xml/preparacion.xml` (template `koroshi_preparacion.Pantalla`, línea 4), declarado en `'qweb'` del manifest.

**Data**: los 5 `data/parametros*.xml` (todos `noupdate="1"`, solo ir.config_parameter).

**Crons**: no encontrado (ninguno en los 4 módulos).

**ir.config_parameter** (constantes en `models/lectura.py:39-66`):
| Clave | Defecto en código | Creado por data | Valor data |
|---|---|---|---|
| `koroshi_preparacion.activa` | '1' | parametros.xml:6 | 1 |
| `koroshi_preparacion.empleados` | '' | parametros.xml:11 | `OP9990001,OP9980001` |
| `koroshi_preparacion.agrupaciones` | '1' | parametros_v315.xml:7 | 1 |
| `koroshi_preparacion.orden` | 'ubicacion' | parametros_v317.xml:8 | ubicacion |
| `koroshi_preparacion.minutos_alarma` | '4' | parametros_v322.xml:8 | 4 |
| `koroshi_preparacion.horario_alarma` | `06:00-10:00,10:15-13:00,14:00-17:00` | parametros_v322.xml:14 | igual |
| `koroshi_preparacion.refresco_solo_s` | '30' | parametros_v334.xml:7 | 30 |
| `koroshi_preparacion.caja_llena_activa` | '1' | no | — |
| `koroshi_preparacion.caja_llena_capacidades` | `600X400X400=0.100;MEDIANA=0.075` | no | — |
| `koroshi_preparacion.caja_llena_umbrales` | (90,100,115) | no | — |
| `koroshi_preparacion.validar_parcial` | '1' | no | — |
| `koroshi_faltantes.pedido_pendiente` (de otro módulo, solo lectura) | 'no' | — | — (lectura.py:1344, agrupacion.py:393) |

**Grupos de seguridad**: no define ninguno. ACL (`security/ir.model.access.csv`) con `stock.group_stock_user` / `stock.group_stock_manager` para lectura, equipo, preferencia, caja_llena (la agrupación es AbstractModel, sin ACL). Las rutas que escriben exigen `stock.group_stock_user` vía `koroshi_base.pda.GRUPO_ALMACEN` (controllers/main.py:48).

**Migraciones**: `migrations/13.0.3.29.0/pre-migrate.py` (borra duplicados de koroshi_preparacion_equipo; menciona EFFEC/OUT/24410). Para el clon: NO hace falta (instalación nueva).

**Tests**: `test_ruta.py` (geometría NAU-2, ubicaciones EFFEC/NAVE2), `test_idempotencia.py` y `test_validar_parcial.py` (parchean COMPANY_ID, EAN 8445962999991/2, CJ999000001…, lote `Z-TEST-D1`).

### A.2 koroshi_consumibles (v13.0.1.4.0)

**Depende de** (`__manifest__.py:31`): `base, mail, stock, delivery, koroshi_warehouse_map`.

| Archivo | Líneas |
|---|---|
| `__init__.py` | 2 |
| `__manifest__.py` | 39 |
| `README.md` | 55 |
| `data/cajas.xml` | 8 |
| `models/__init__.py` | 2 |
| `models/consumable.py` | 400 |
| `security/ir.model.access.csv` | 3 |
| `views/consumable_views.xml` | 185 |

- Modelos definidos: `koroshi.consumable.item` (`models/consumable.py:20`), `koroshi.consumable.move` (`models/consumable.py:306`). Sin `_inherit`.
- Métodos públicos usados por preparación: `cajas_pda(company=None)` (219-224), `consumir_caja(item_id, nota)` (227-246). Otros: `_sincronizar_packaging` (191-202, crea/actualiza `product.packaging`), `_avisar_si_cruza` (146-177, crea `mail.mail`), `_cajas_koroshi_iniciales` (249-270).
- Controladores: no encontrado. JS: no encontrado. Assets: no encontrado.
- Data: `data/cajas.xml` (noupdate) llama a `_cajas_koroshi_iniciales` (línea 6).
- Crons: no encontrado. ir.config_parameter: no encontrado. Grupos: no define; ACL con `stock.group_stock_user`.
- Menús: `menu_koroshi_consumables_root` con `parent="koroshi_warehouse_map.menu_koroshi_warehouse_root"` (`views/consumable_views.xml:180`) — ES LA ÚNICA RAZÓN de depender de koroshi_warehouse_map. Submenús 181-184.
- Migraciones: no encontrado.

### A.3 koroshi_warehouse_map (v13.0.0.1.20261116.46)

**Depende de** (`__manifest__.py:39`): `web, stock, stock_picking_batch, koroshi_base`.

| Archivo | Líneas |
|---|---|
| `__init__.py` | 3 |
| `__manifest__.py` | 48 |
| `README.md` | 111 |
| `controllers/__init__.py` | 2 |
| `controllers/main.py` | 613 |
| `models/__init__.py` | 3 |
| `models/warehouse_layout.py` | 66 |
| `models/picking_tracking.py` | 85 |
| `security/ir.model.access.csv` | 9 |
| `static/src/css/warehouse_map.css` | 15 |
| `static/src/html/warehouse_planner_20261029_v1.html` | 8188 (plano NAU-2 dibujado a mano) |
| `static/src/js/warehouse_map_action.js` | 28 |
| `views/assets.xml` | 9 |
| `views/koroshi_layout_views.xml` | 124 |
| `views/menu.xml` | 43 |

- Modelos definidos: `koroshi.layout` (`models/warehouse_layout.py:6`), `koroshi.layout.element` (38), `koroshi.pick.session` (`models/picking_tracking.py:6`), `koroshi.pick.event` (53). Sin `_inherit`.
- Rutas (`controllers/main.py`, `type='http'`): `/koroshi_warehouse_map/layout/save` POST (460), `/koroshi_warehouse_map/layout/load` GET (508), `/koroshi_warehouse_map/planner` GET (533), `/koroshi_warehouse_map/data` GET (548).
- JS: `odoo.define('koroshi_warehouse_map.action')` (`warehouse_map_action.js:1`), action tag **`koroshi_warehouse_map`** (26). Iframe a `/koroshi_warehouse_map/planner`.
- Assets: `views/assets.xml:3` `assets_backend` hereda `web.assets_backend`.
- Acciones/menús (`views/menu.xml`): `action_koroshi_warehouse_map` (3, client), `action_koroshi_layouts` (8), `action_koroshi_pick_sessions` (14); menús `menu_koroshi_warehouse_root` «KOROSHI · Operaciones» bajo `stock.menu_stock_root` (20), `menu_koroshi_warehouse_map` (25), `menu_koroshi_pick_sessions` (31), `menu_koroshi_layouts` (37).
- Data, crons, ir.config_parameter, grupos propios, migraciones: no encontrado. ACL con `stock.group_stock_user/manager`.

### A.4 koroshi_caja_existente (v13.0.1.4.0)

**Depende de** (`__manifest__.py:36`): `stock, stock_barcode_optimization, koroshi_base`.

| Archivo | Líneas |
|---|---|
| `__init__.py` | 2 |
| `__manifest__.py` | 40 |
| `README.md` | 78 |
| `models/__init__.py` | 2 |
| `models/stock_picking.py` | 186 |

- Modelos: `_inherit = 'stock.picking'` (`models/stock_picking.py:34`). Sobreescribe `put_in_pack(package_name=None)` (36-44), `action_done` (176-179), `write` (181-186). Métodos propios `_koroshi_dueno`, `_koroshi_mismo_pedido`, `_koroshi_lineas_leidas`, `_koroshi_anadir_a_caja`, `_koroshi_meter_en_caja_propia`, `_koroshi_meter_en_caja_ajena`, `_koroshi_corregir_bultos` (escribe `number_of_packages`, campo que en el destino da `delivery_package_number`).
- Controladores, JS, assets, data, crons, parámetros, grupos, migraciones: no encontrado (`'data': []`).

---------------------------------------------------------------------------------------------------------------------

## B. Puntos específicos de NATH / instancia (archivo:línea → cambio propuesto en el clon)

### B.1 Empresa (company id 8)
| Dónde | Qué | Cambio propuesto |
|---|---|---|
| `koroshi_base/comun.py:14` | `COMPANY_ID = 8` (origen de todo) | En el clon: `COMPANY_IDS = (1, 21, 23)` (o parámetro `tuctuc_base.company_ids`) y comparar con `in`. |
| `koroshi_preparacion/models/lectura.py:28` | `COMPANY_ID = comun.COMPANY_ID` | Importar la tupla de empresas. |
| `koroshi_preparacion/models/lectura.py:248` | `picking.company_id.id != COMPANY_ID` → la OUT no se prepara aquí | `picking.company_id.id not in COMPANY_IDS`. **Bloqueante**: sin esto ninguna OUT de Oriola entra. |
| `koroshi_preparacion/models/agrupacion.py:23` | importa `COMPANY_ID` de lectura | Importar la tupla. |
| `koroshi_preparacion/models/agrupacion.py:72` | `lote.company_id.id != COMPANY_ID` | `not in COMPANY_IDS`. |
| `koroshi_preparacion/models/agrupacion.py:456` | fallback `COMPANY_ID` en `allowed_company_ids` de la URL del PDF | Usar `vivas[0].company_id.id` siempre (ya lo hace primero). |
| `koroshi_preparacion/tests/test_idempotencia.py:15-16`, `test_validar_parcial.py:12-13` | `patch(...COMPANY_ID)` | Adaptar al nombre nuevo. |
| `koroshi_consumibles/models/consumable.py:251` | `res.company.browse(8)` al crear las cajas iniciales | Crear las cajas por cada empresa (1, 21, 23) o hacer el modelo sin empresa. |
| `koroshi_consumibles/models/consumable.py:221-223` | `cajas_pda` filtra por `company_id` | Con 3 empresas: o 3 juegos de cajas, o quitar el filtro de empresa (un juego compartido). |
| `koroshi_warehouse_map/controllers/main.py:17,40` | `COMPANY_ID` para el mapa | Irrelevante si no se clona el mapa. |
| `koroshi_caja_existente/models/stock_picking.py:29,39,164` | solo actúa si `company_id.id == COMPANY_ID` | `in COMPANY_IDS`. |

### B.2 Nombres de ubicación / regex / geometría de la nave
| Dónde | Qué | Cambio propuesto |
|---|---|---|
| `koroshi_preparacion/models/ruta.py:5-34` | Geometría NAU-2: L01-L136 por parejas, P01-P36 a 1,2 m, pasillos transversales `PASILLOS_X=(2.5,10.1,29.9,41.3,58.5)`, `MUELLES=(0,29.9)`, `ZONA_MU=(0,40.0)`, `PENAL_PASILLO=10` | Solo se usa con `koroshi_preparacion.orden='ruta'` (por defecto 'ubicacion'). Clon: dejar 'ubicacion' y no copiar ruta.py, o rehacer la geometría de Oriola (L hasta ≥147, P≥38: no cabe en P01-P36). |
| `koroshi_preparacion/models/ruta.py:27` | `RE_LPC = (?:^|/|-\s)L(\d+)\s+P(\d+)(?:\s+C(\d+))?` | Con `WH-OR/Stock/N1/06298 - L75 P38 C2` sí casa (por el `- `). Vale tal cual; solo afecta a `_parada`/«Aquí mismo». |
| `koroshi_preparacion/models/ruta.py:28` | `RE_MU = (?:^|/)MU-\d+` (zona MU- de NATH) | Quitar (en Oriola no se ha visto MU-: no encontrado). |
| `koroshi_preparacion/models/ruta.py:26` (comentario) y 49 | `N1-L07` se trata como "no se sabe dónde está"; ejemplo `EFFEC/Stock/NAVE2/...` | En Oriola `N1` es un nivel de carpeta (`/N1/`), no prefijo `N1-`: no afecta. |
| `koroshi_preparacion/models/lectura.py:291-295` | orden por defecto `complete_name` + `default_code` (comentario cita `EFFEC/Stock/NAVE2/00114 - L02…`, `MU-`, `N1-`) | Genérico: sirve. Ojo: `UBRAN/STOCK/...` vs `WH-OR/Stock/...` solo cambia el prefijo; dentro de una OUT (una empresa) no importa. |
| `koroshi_preparacion/models/lectura.py:296-306, 309-312` | `_ordenar` modo ruta y `_parada` usan ruta.py | Ver ruta.py. |
| `koroshi_preparacion/models/lectura.py:671` | `ubicacion_codigos` = barcode de la ubicación y de su padre («la caja KO_ o el hueco») | Genérico; en Oriola también hay KO_/UB_ como hoja (`…/KO_300726_755`, `…/UB_240725_612`). Vale. |
| `koroshi_preparacion/models/lectura.py:1474-1479` | `corte_nombre()`: penúltimo tramo del `complete_name` | Genérico. Vale. |
| `koroshi_preparacion/static/src/js/preparacion.js:2755-2778` | `_partesUbicacion`: quita los tramos `'EFFEC'` y `'Stock'` (2764), trata `^NAVE` como zona (2773), separa `NNNNN - Lx Px Cx` | Quitar `WH-OR`, `UBRAN`, `MODAI`, `Stock` y `STOCK` (o: quitar los dos primeros tramos); `^NAVE` → `^N\d` si se quiere. Solo cosmético (detalle pequeño encima de la ubicación). |
| `koroshi_preparacion/static/src/js/preparacion.js:2652-2660` | casillas color E: `/^([A-Za-z]+)-?(\d+)$/` sobre L24 P19 C2 / MU-02 | Genérico. Vale. |
| `koroshi_preparacion/static/src/css/preparacion.css:280` | comentario «L87 P23 C2 · KO_130826_523» | Nada. |
| `koroshi_warehouse_map/controllers/main.py:18-20, 71-89` | `LINE_RE/POSITION_RE/LEVEL_RE` y marcador: 16 lineales por fila (`x = 10 + ((l-1)%16)*5.2`) | No clonar el mapa. |
| `koroshi_warehouse_map/controllers/main.py:380` | zonas del día por `origin =like 'KOR-ddmm-%'` (proceso de zonas NATH) | No clonar. |
| `koroshi_warehouse_map/static/src/html/warehouse_planner_20261029_v1.html` | Plano NAU-2 completo (66 apariciones de NAU-2/KOR-/L1xx/EFFEC) | No clonar. |
| `koroshi_warehouse_map/models/warehouse_layout.py:11,18`, `controllers/main.py:488,496,498`, `views/menu.xml:4,9,26`, `__manifest__.py:3` | «NAU-2», `NAU2-`, «NAU-2 · 2026-10-29» | No clonar. |

### B.3 Prefijo EAN / regex de código de producto / talla
| Dónde | Qué | Cambio propuesto |
|---|---|---|
| `koroshi_preparacion/models/lectura.py:33` | `RE_EAN = ^\d{8,14}$` | Vale. |
| `koroshi_preparacion/models/lectura.py:34` | `PREFIJO_KOROSHI = '8445962'` | Tupla `('8447333', '8435689')` (o parámetro). |
| `koroshi_preparacion/models/lectura.py:868-873` | `_msg_desconocido`: «Lee el de KOROSHI, el que empieza por 8445962» | `startswith(tupla)` y texto sin «KOROSHI» (p. ej. «el que empieza por 8447333 u 8435689»). |
| `koroshi_preparacion/models/lectura.py:315-321` | `_modelo`: `product.name` partido por `-`, quita la talla final (ej. `2621PT26-000306-32`) | Comprobar el formato de `name` en TUCTUC (no encontrado en el repo). Con `9873-07-36` funciona; con `KG14A401W1` (sin guiones) devuelve '' → no hay aviso de «talla hermana» (degrada, no rompe). |
| `koroshi_preparacion/models/lectura.py:354-363` | `_talla`: atributo cuyo nombre contiene TALLA/SIZE; si no, último tramo de `name` con `-` (≤5 car.) | Comprobar el nombre del atributo de talla en TUCTUC (no encontrado). Si no se llama TALLA/SIZE, añadir el nombre real. |
| `koroshi_preparacion/models/lectura.py:713-720`, `preparacion.js:365-366` | UPC-12 ↔ EAN-13 | Genérico. |
| `koroshi_preparacion/models/lectura.py:681-690, 735-747` | `product.barcode` (product_multi_barcode) | Protegido con `'product.barcode' in self.env`: en TUCTUC (sin el modelo) simplemente no se usa. Se puede quitar. |
| `koroshi_preparacion/tests/*` | EAN `8445962999991/2` | Cambiar a 8447333…. |

### B.4 Matrícula de caja CJ
| Dónde | Qué | Cambio propuesto |
|---|---|---|
| `koroshi_base/comun.py:18` | `RE_CJ = ^CJ\d{9}$` | En Oriola los paquetes de OUT son `BOX0699806` (= `BOX` + 7 cifras). Decidir: (a) si BOX es etiqueta preimpresa que se lee → `RE_CAJA = ^BOX\d{7}$` (parámetro); (b) si BOX lo pone la secuencia de Odoo al hacer «Put in pack» → todas las OUT en modo `pack_auto` (sin leer etiqueta). Origen del nombre BOX en TUCTUC: no encontrado en el repo. |
| `koroshi_preparacion/models/lectura.py:29` | `RE_CJ = comun.RE_CJ` | Lo que se decida arriba. |
| `koroshi_preparacion/models/lectura.py:821-822` | una CJ leída en «leer» → «Es una caja: pulsa Caja» | Con el patrón nuevo. |
| `koroshi_preparacion/models/lectura.py:995-997` | `caja()`: si no casa `RE_CJ` → «no es una etiqueta de caja (CJ + 9 cifras)» | Patrón y texto nuevos. |
| `koroshi_preparacion/models/lectura.py:1158-1161` | `mover_caja`: caja nueva por CJ, rechaza si ya existe | Patrón nuevo. |
| `koroshi_preparacion/models/agrupacion.py:217, 336-338` | CJ en agrupación | Patrón nuevo. |
| `koroshi_preparacion/static/src/js/preparacion.js:63` | `RE_CJ = /^CJ\d{9}$/i` (usada en 363, 823, 829, 851, 858, 1304, 1992) | Mismo patrón que Python (idealmente servido desde el estado). |
| `koroshi_preparacion/static/src/js/preparacion.js:1278, 1305, 1311` y `static/src/xml/preparacion.xml:162` | textos «Lee la etiqueta CJ…», «(CJ + 9 cifras)», «la de CAJA nn» | Textos. |
| `koroshi_caja_existente/models/stock_picking.py:30,38` | `RE_CJ` | Patrón nuevo. |

### B.5 Lógica de agrupaciones Z-
| Dónde | Qué | Cambio propuesto |
|---|---|---|
| `koroshi_preparacion/models/lectura.py:38` | `PREFIJOS_ZONA = ('Z-',)` | En Oriola no hay Z-: las OUT de B-ECI_/B-VP_/WEB_/B-MIECI_ cuentan como «sueltas» y SÍ se preparan (lectura.py:260-262 devuelve True). |
| `koroshi_preparacion/models/lectura.py:41, 236-238` | parámetro `agrupaciones` | Si no se usan Z-, ponerlo a '0' o quitar. |
| `koroshi_preparacion/models/lectura.py:260-261, 396-397, 1358-1359` | ramas Z- en `picking_propio`, `_parcial`, `validar` | Inofensivas sin Z-. Se pueden borrar en el clon. |
| `koroshi_preparacion/models/agrupacion.py` (todo) | agrupación Z- entera: `lote_propio` exige nombre `Z-` (70), caja de tienda por nota `| CAJA nn |` (25, 86-90), CJ por `zebra.label` con nota `ETQ ZONA <OUT>` (26, 305-324) | Sin Z- nunca se usa (`lote_propio` = False → Lecturas abre la app de código de barras). Para preparar un B-/WEB_ entero haría falta reescribirlo (sin zebra.label ni nota CAJA nn). Propuesta: no clonar agrupacion.py en la primera versión. |
| `koroshi_preparacion/static/src/js/preparacion.js:3170-3207` | `_abrirLote` (tarea tipo 'agrupacion') | Se queda en `deSiempre` (app de código de barras) si `lote_propio` es False. |
| `koroshi_faltantes/models/faltante.py:55, 537-539` | `validar_out` rechaza OUT de batch Z- | Sin Z- no afecta. |

### B.6 Marketplace (PED. MARKETPLACE / ZALANDO / ABOUT YOU)
| Dónde | Qué | Cambio propuesto |
|---|---|---|
| `koroshi_preparacion/models/lectura.py:36` | `TIPO_MARKETPLACE = 'PED. MARKETPLACE'` (nombre de `sale.order.s_order_type_id`, sales_ext) | El destino tiene sales_ext; nombres de tipos de pedido en TUCTUC: no encontrado. Pasar a parámetro (lista de tipos que van «sin etiqueta»). |
| `koroshi_preparacion/models/lectura.py:37` | `MARKETPLACES = ('ZALANDO', 'ABOUT YOU')` (match por nombre del partner) | Parámetro con los clientes de Oriola (ECI, VP… según cómo se cierren las cajas). |
| `koroshi_preparacion/models/lectura.py:374-386` | `_pack_auto` | Es la pieza que decide «caja sin leer etiqueta (secuencia de Odoo)». Si los BOX0699806 los pone Odoo, esta función debería devolver True para todas las OUT (o según tipo). |
| `koroshi_preparacion/models/lectura.py:1207-1245, 1312-1319, 1323-1330, 1346-1347, 1399-1401` | validar incompleta y caja automática para marketplace | Según lo anterior. |
| `koroshi_preparacion/static/src/js/preparacion.js:1049-1069, 1234, 1249-1268, 1440, 1566, 1673-1742, 2736-2741`, `xml:166`, `css:602, 771` | flujo pack_auto en la PDA (número PACK en grande, «Validar incompleto») | Textos «Zalando / About You», «PACK» → genéricos. |

### B.7 Otros puntos NATH
| Dónde | Qué | Cambio propuesto |
|---|---|---|
| `koroshi_preparacion/data/parametros.xml:13` | empleados `OP9990001,OP9980001` (tarjetas NATH) | Poner `*` o las tarjetas de los 61 empleados de TUCTUC. |
| `koroshi_preparacion/data/parametros_v322.xml:16`, `lectura.py:46`, `preparacion.js:87` | horario alarma 06-10, 10:15-13, 14-17 (turnos NATH) | Horario de Oriola (no encontrado). |
| `koroshi_preparacion/models/lectura.py:55-60` | capacidades de caja `600X400X400=0.100;MEDIANA=0.075`, `VOL_UD_DEFECTO=0.0084` (medidas de NATH) | Cajas de Oriola (no encontrado). O `caja_llena_activa='0'` al principio. |
| `koroshi_preparacion/models/lectura.py:967-970`, `agrupacion.py:458-461` | informe por nombre `koroshi.report_etiqueta_zona` (de koroshi_zonas) | Protegido con `search(...)`: en TUCTUC no sale. Quitar. |
| `koroshi_preparacion/models/lectura.py:981-983`, `agrupacion.py:462-464` | informe por nombre `stock.report_deliveryslip` | Estándar: vale. |
| `koroshi_preparacion/models/lectura.py:972-980` | adjuntos PDF de la OUT con nombre `ilike 'label'` / `'etiq'` = etiqueta del transportista | Comprobar cómo nombra TUCTUC las etiquetas (no encontrado). |
| `koroshi_preparacion/models/lectura.py:881-887` | `picking.set_barcode_start_date()` (stock_barcode_optimization, Brain Station) | Protegido con `hasattr`; TUCTUC tiene el módulo: vale. |
| `koroshi_preparacion/models/lectura.py:1019` | `picking.put_in_pack(package_name=codigo)` (firma de stock_barcode_optimization) | TUCTUC tiene stock_barcode_optimization: vale (comprobar que es la misma versión: no verificable desde el repo). |
| `koroshi_preparacion/static/src/js/preparacion.js:2262-2296` | «Sin caja (bolsa) → expediciones»: busca el motivo con `sin_caja: true` de koroshi_operarios (`motivo_sin_caja`, operarios controllers/main.py:238) | Depende de cómo trabaje expediciones en Oriola. |
| `koroshi_preparacion/static/src/js/preparacion.js:2372-2386` | pausa: motivo con `destino: 'pausa'` de koroshi_operarios | Depende del clon de operarios. |
| zebra.label | `koroshi_preparacion/models/agrupacion.py:26, 305-324` | Protegido con `'zebra.label' in self.env`. En TUCTUC no existe: no rompe, pero la agrupación no sabe la tienda de una caja. |
| product.barcode | ver B.3 | Protegido. |
| Emails | no encontrado ningún email fijo en los 4 módulos (consumibles usa el campo `aviso_emails`, dato). |
| Logins de usuario | no encontrado. |
| S4T | solo comentarios: `controllers/main.py:354`, `preparacion.js:2263`, `koroshi_caja_existente/models/stock_picking.py:15`, manifest de caja_existente:19. Sin lógica. |
| Nombres de personas | comentarios/ayudas: «Isaac» (lectura.py:65), «Betty» (consumable.py:36, 229). Sin lógica. |
| xmlids de otros módulos | `koroshi_preparacion/views/lectura_views.xml:71,73,75,77` y `caja_llena_views.xml:59-62` (`koroshi_operarios.menu_koroshi_operarios_root`, `koroshi_operarios.grupo_productividad`); `preparacion.js:1817` (`koroshi_faltantes.action_koroshi_faltantes_pantalla`); `preparacion.js:3098,3145,3165,3194,3252` (`koroshi_preparacion.action_koroshi_preparacion_pantalla`, propio → renombrar a `tuctuc_preparacion.`); `koroshi_consumibles/views/consumable_views.xml:180` (`koroshi_warehouse_map.menu_koroshi_warehouse_root`); `koroshi_operarios/controllers/main.py:238` (`koroshi_operarios.motivo_sin_caja`, usado desde la PDA). |
| Consumibles: cajas KOROSHI | `koroshi_consumibles/models/consumable.py:252-257` (KCAJA590X390X400, KCAJA600X400X400, KCAJAMEDIANA, KCAJA280X280X120) y ayuda 86-87 (CJ/Zalando/SORTER) | Cajas reales de Oriola (no encontrado). |
| Nombres «KOROSHI» en modelos/textos | todos los `_name koroshi.*`, rutas `/koroshi/...`, clases CSS `o_koroshi_*`, claves localStorage `koroshi_*`, parámetros `koroshi_preparacion.*` | Renombrar a `tuctuc.*` / `/tuctuc/...` / `tuctuc_preparacion.*` (convivir sin choque si algún día se instala algo koroshi_*). |

---------------------------------------------------------------------------------------------------------------------

## C. Qué usa koroshi_preparacion de koroshi_consumibles y de koroshi_warehouse_map

### C.1 De koroshi_consumibles (modelo `koroshi.consumable.item`)
| Uso | Archivo:línea | ¿Protegido? |
|---|---|---|
| Dependencia en manifest | `koroshi_preparacion/__manifest__.py:267` | — |
| `cajas_pda(company)` → lista de tipos de caja para la PDA `[{id, nombre, medidas}]` | `models/lectura.py:1066` (dentro de `tipos_caja`, 1061-1079, llamado desde `estado` 638 y `agrupacion.estado` 196) | Sí (`try/except`, devuelve []) |
| `search([('packaging_id','in',…)])` + campos `packaging_id`, `nombre_pda`, `name` → nombre corto del tipo de cada caja | `models/lectura.py:1087-1090` (`_tipos_de_paquetes`, llamado en 579 y agrupacion 156) | No: si falta el modelo, `KeyError` al pintar el estado (el controlador lo traga, `controllers/main.py:79`, y la PDA se queda sin estado) |
| `browse(tipo_caja)` + `es_caja`, `packaging_id` (escribe `stock.quant.package.packaging_id`), `consumir_caja(item.id, nota)` (resta 1), `nombre_pda`/`name` | `models/lectura.py:1098-1111` (`_poner_tipo_caja`, llamado desde `caja` 1050) | No (el `browse` está fuera del try) |
| Many2one `tipo_caja_id` → `koroshi.consumable.item` | `models/caja_llena.py:18` | No: el modelo es obligatorio para instalar |
| `browse(tipo_caja)` | `models/caja_llena.py:40` | No |
| JS: la hoja de caja enseña `estado.tipos_caja` (id, nombre, medidas, capacidad, defecto_barra) y manda `tipo_caja` en caja/validar; recuerda el último por operario en localStorage | `preparacion.js:731-732, 866, 1096-1106, 1194, 1211-1253, 531` | — |

Conclusión C.1: preparación solo necesita **una lista de tipos de caja por empresa** (id, nombre corto, medidas, orden, `product.packaging`) y opcionalmente **restar 1** al cerrar. No usa `koroshi.consumable.move` directamente (solo a través de `consumir_caja`), ni emails, ni totales.
Opciones para el clon: (a) clonar consumibles entero como `tuctuc_consumibles` cambiando el menú padre y la empresa 8; (b) **pieza mínima**: un modelo `tuctuc.caja.tipo` (name, nombre_pda, secuencia, largo/ancho/alto, packaging_id, company_id/compartido, activo) dentro de tuctuc_preparacion, con `cajas_pda()` y sin contador; (c) usar `product.packaging` directamente (filtrado por un booleano o por nombre) y quitar `caja_llena.tipo_caja_id` → Many2one a `product.packaging`. Las tres eliminan la dependencia de warehouse_map.

### C.2 De koroshi_warehouse_map
- Python, JS, XML, rutas, modelos: **nada**. No está en `depends` de preparación.
- Solo menciones en comentarios: `koroshi_preparacion/models/ruta.py:5` («la del plano de koroshi_warehouse_map») y `README.md:288`.
- Única dependencia indirecta: `koroshi_consumibles/__manifest__.py:31` depende de warehouse_map únicamente por el menú padre `koroshi_warehouse_map.menu_koroshi_warehouse_root` (`koroshi_consumibles/views/consumable_views.xml:180`). Ningún código de consumibles usa `koroshi.layout`/`koroshi.pick.*`.

Conclusión C.2: el clon puede **prescindir de koroshi_warehouse_map**. Si se clona consumibles, cambiar el menú padre a `stock.menu_stock_config_settings` (o el que se quiera) y quitar la dependencia.

---------------------------------------------------------------------------------------------------------------------

## D. Qué usa koroshi_preparacion de koroshi_operarios, koroshi_faltantes y koroshi_base

### D.1 koroshi_base
| Uso | Archivo:línea |
|---|---|
| `from odoo.addons.koroshi_base import comun` → `comun.COMPANY_ID` (=8, `koroshi_base/comun.py:14`), `comun.RE_CJ` (`comun.py:18`) | `models/lectura.py:22, 28-29` |
| `from odoo.addons.koroshi_base import pda` → `pda.GRUPO_ALMACEN` ('stock.group_stock_user', `pda.py:15`), `pda.es_empleado_valido(env, emp)` (`pda.py:27-32`: activo, con barcode y empresa del empleado ∈ `env.user.company_ids`), `pda.TARJETA_NO_VALE` (`pda.py:17`) | `controllers/main.py:20, 48-52` |
| JS de koroshi_base (`static/src/js/comun.js`): no se usa desde preparacion.js (no hay `require('koroshi_base…')`) | — |
Para el clon: copiar estas 4 constantes/funciones a un `tuctuc_base` o dentro del propio módulo (es poco código). `es_empleado_valido` ya es multiempresa si el usuario de la PDA tiene las 3 empresas.

### D.2 koroshi_faltantes (modelo `koroshi.faltante`, rutas y JS)
| Uso | Preparación (archivo:línea) | Definido en |
|---|---|---|
| `es_ronda(picking)` | `models/lectura.py:268` (sin protección; se llama en `picking_propio` 252, `_ubi` 274, `_parcial` 394, `estado` 596/635, `validar` 1348, `ronda_marcar` 1267) | `koroshi_faltantes/models/faltante.py:868` |
| `search` de `koroshi.faltante` (campos `picking_id, employee_id, fecha, tipo, product_id, ubicacion_nueva_id`) para avisos a dos | `models/lectura.py:460-472` (protegido con `'koroshi.faltante' in self.env`) | faltante.py |
| `lineas_pendientes(pickings)` | `models/lectura.py:1200, 1219, 1252, 1312, 1315, 1320, 1381`; `agrupacion.py:388` | faltante.py:297 |
| `pendiente_de(ml)` | `models/lectura.py:1220, 1316, 1381` | faltante.py:292 |
| `_todo_o_nada(funcion, *args)` | `models/lectura.py:1205, 1221, 1257, 1258`; `agrupacion.py:404` | faltante.py:361 |
| `_validar_out(picking, pedido_pendiente)` (button_validate + asistente de pedido pendiente) | idem | faltante.py:548 |
| `validar_out(picking, pedido_pendiente)` (validación normal de una OUT suelta) | `models/lectura.py:1361` | faltante.py:530 |
| `ronda_antes_de_validar`, `ronda_cerrar_sin_leer`, `sincronizar_rondas`, `ronda_marcar` | `models/lectura.py:1255, 1257, 1395, 1275` | faltante.py:908, 919, 754, 874 |
| Parámetro `koroshi_faltantes.pedido_pendiente` | `models/lectura.py:1344`, `agrupacion.py:393` | — |
| Ruta `/koroshi/faltantes/buscar` (alternativas de Faltante) | `preparacion.js:1894, 1954` | `koroshi_faltantes/controllers/main.py:195` |
| Ruta `/koroshi/faltantes/reubicar` | `preparacion.js:1999` | controllers/main.py:276 |
| Ruta `/koroshi/faltantes/sin_alternativa` | `preparacion.js:2047` | controllers/main.py:304 |
| Acción `koroshi_faltantes.action_koroshi_faltantes_pantalla` («Marcar varias a la vez») con contexto `desde_operarios, desde_preparacion, faltante_out, faltante_operario` | `preparacion.js:1817-1824` | `koroshi_faltantes/views/faltante_views.xml:266` |
| JS `require('koroshi_faltantes.Pantalla')` + `include` de `init` y `_onVolver`; usa `this.out`, `this.ocupado`, `this.paso`, `this._empleadoId()`, `this.operario` | `preparacion.js:3216-3262` | `faltantes_pantalla.js:1, 313, 407` |
Mínimo imprescindible para el clon: **validar_out / _validar_out / _todo_o_nada / lineas_pendientes / pendiente_de** (validación) y **es_ronda** (llamado sin protección). Lo de Faltante (buscar/reubicar/sin_alternativa, pantalla) es necesario solo si se quiere el botón «Faltante» en la PDA.

### D.3 koroshi_operarios
| Uso | Preparación (archivo:línea) | Definido en |
|---|---|---|
| `_inherit = 'koroshi.operario.tarea'`: override `_uds_hasta_ahora`, `_cerrar`; escribe `uds_inicio, uds_fin, a_dos, companero_id, nota`; lee `picking_id, tipo, estado, inicio, fin, employee_id` | `models/tarea.py` | `koroshi_operarios/models/tarea.py:75, 126-127, 302, 372` |
| `koroshi.operario.tarea` search `('tipo','=','out'),('estado','=','curso')` → equipo (quién prepara la OUT) | `models/lectura.py:448-454` (sin protección; llamado en estado, caja, validar, `_parcial`) | tarea.py |
| `koroshi.operario.tarea`: `_reabrir_inactivas`, `_pickings`, `_validado`, `_hora_validacion`, `_cerrar`, campo `batch_id` | `models/lectura.py:1424-1438` (protegido con `in self.env`) | tarea.py:509, 281, 356, 362, 372 |
| `koroshi.operario.asignacion`: `_terminada`, `_cerrar_hecha`, campos `estado, picking_id, batch_id` | `models/lectura.py:1439-1443` (protegido) | `koroshi_operarios/models/reparto.py:256, 349, 716` |
| Rutas `/koroshi/operarios/motivos`, `/saltar` (sin caja, pausa), `/dejar`, `/soltar`, `/siguiente` | `preparacion.js:2284-2287, 2376-2384, 2436, 2469` | `koroshi_operarios/controllers/main.py:234, 243, 282, 268, 213` |
| Motivos por propiedad: `{sin_caja: true}` (xmlid `koroshi_operarios.motivo_sin_caja`) y `{destino: 'pausa'}` | `preparacion.js:2285, 2377` | controllers/main.py:238 |
| JS `require('koroshi_operarios.Pantalla')` + `include`: `on_attach_callback`, `_pintarActual`, `_mostrarHecho`, `_abrir` (y método nuevo `_precargar`, `_abrirLote`). Usa de Lecturas: `this.operario{id,nombre}`, `this.sinRed`, `this.actual`, `this.ocupado`, `this.precarga`, `_olvidarOperario`, `_aviso`, `_mostrarAbriendo`, `_esSinConexion`, `_ocultarCapa`, `_sinConexion`; objetos `obj.tipo ('out'|'agrupacion')`, `obj.picking_name|ref`, `obj.batch_id` | `preparacion.js:3067-3207` | `operarios_pantalla.js:1, 154, 241, 433, 526, 536, 576, 855, 874, 961, 1088` |
| Comunicación por `window.koroshiPausaHecha` | `preparacion.js:2390, 2442, 3076-3078` | — |
| localStorage `koroshi_operarios_sonido` (interruptor de sonido de Lecturas) | `preparacion.js:61, 2922` | operarios |
| Menús `koroshi_operarios.menu_koroshi_operarios_root`, grupo `koroshi_operarios.grupo_productividad` | `views/lectura_views.xml:71-77`, `caja_llena_views.xml:59-62` | `koroshi_operarios/views/menu.xml:7`, `security/grupo.xml:7` |
Conclusión D.3: preparación es una **extensión de la pantalla Lecturas** de koroshi_operarios (la abre `_abrir` cuando `/modo` dice `propia`). Sin un clon de operarios (Lecturas + tareas) no hay punto de entrada en la PDA: la pantalla podría abrirse sola con `do_action('…pantalla', {preparacion_out, preparacion_operario})`, pero el «equipo» (lectura.py:448) y el cierre de tareas dependen de `koroshi.operario.tarea`.

---------------------------------------------------------------------------------------------------------------------

## E. Lógica que asume el flujo NATH y puede no encajar en Oriola

1. **Una sola empresa (8)** — `lectura.py:248`, `agrupacion.py:72`, `caja_existente/stock_picking.py:39,164`, `consumable.py:251`. BLOQUEANTE: hay que pasar a lista de empresas (1, 21, 23).
2. **Multiempresa en las peticiones de la PDA (riesgo, no verificado)** — el controlador usa `request.env` sin `sudo` para `stock.picking` (`controllers/main.py:55-61, 63-64`), `put_in_pack`, `button_validate` (vía faltantes). En Odoo 13 las reglas multiempresa usan `allowed_company_ids` del contexto: si en la PDA solo está marcada PRIME COLLECTIONS, una OUT de UBRAN/MODAI daría AccessError o crearía paquetes/movimientos con la empresa equivocada. Propuesta: en cada ruta, `with_context(allowed_company_ids=[picking.company_id.id] + resto)` o `with_company`, y que el usuario PDA tenga las 3 empresas. `impresos` ya lo hace para los PDF (`lectura.py:966`).
3. **Caja = etiqueta CJ preimpresa** — `_con_caja` (`lectura.py:369-372`) obliga a cerrar caja en TODA OUT `outgoing` antes de validar (`lectura.py:1331-1341`: «Hay N uds sin caja: pulsa Caja y lee la etiqueta»). En Oriola los paquetes son `BOX0699806`: hay que decidir si se leen (cambiar regex) o los genera Odoo (modo `pack_auto` para todas). Si alguna OUT de Oriola no va en caja, `_con_caja` debe poder decir False (hoy solo las INT van sin caja).
4. **Tipos de caja por empresa** — `cajas_pda` filtra por `company_id` (`consumable.py:223`) y `tipos_caja(picking.company_id)` (`lectura.py:638`): con 3 empresas, hacen falta cajas en las 3 o un juego compartido.
5. **Agrupaciones = Z-** — `PREFIJOS_ZONA` (`lectura.py:38`) y toda `agrupacion.py`. En Oriola (B-ECI_, B-VP_, WEB_, B-MIECI_) las OUT se preparan sueltas (bien), pero si koroshi_operarios/el clon reparte tareas de tipo 'agrupacion', `lote_propio` = False y se abre la app de código de barras (`preparacion.js:3170-3207`). Preparar un batch B- entero en un solo recorrido NO está soportado sin reescribir (depende de `zebra.label` «ETQ ZONA» y de la nota «| CAJA nn |» de koroshi_zonas).
6. **Web a SORTER** — `picking_propio` acepta INT cuyo origen cuelga de la ubicación origen por defecto del tipo (`lectura.py:250-255`) y las prepara sin caja (`_con_caja` False). En NATH las web van por INT a `EFFEC/SORTER`; en Oriola hay `WH-OR/SORTER` y `MODAI/SORTER` (y no se ha visto UBRAN/SORTER: no encontrado). Si los WEB_ de Oriola son OUT (no INT), irían por la rama «con caja» y pedirían etiqueta: revisar.
7. **Ronda de faltantes** — `es_ronda` de koroshi_faltantes se llama sin protección (`lectura.py:268`) desde `picking_propio`: el clon de faltantes (o un stub que devuelva False) es obligatorio.
8. **Validación = koroshi_faltantes** — todo pasa por `Faltante.validar_out / _validar_out / _todo_o_nada` (`lectura.py:1361, 1205, 1221, 1258`). Usa el asistente estándar `stock.backorder.confirmation`; si TUCTUC tiene otros asistentes al validar (p. ej. de delivery/queue_job/transportista), `_validar_out` lanza «Odoo pide otra cosa al validar» (faltante.py:552-556). No verificable desde el repo.
9. **Equipo / «preparar a dos»** — depende de tareas `koroshi.operario.tarea` en curso (`lectura.py:448-454`); sin operarios clonado, siempre «solo».
10. **Marketplace por nombre** — `_pack_auto` (`lectura.py:374-386`) por tipo de pedido 'PED. MARKETPLACE' o cliente ZALANDO/ABOUT YOU. En Oriola los clientes/tipos son otros (ECI, VP… por los nombres de batch): pasar a parámetro.
11. **«Validar a medias» (pedido pendiente) por defecto encendido** — `validar_parcial` '1' (`lectura.py:66, 400`). Decisión de negocio de Oriola.
12. **Geometría y orden** — orden por defecto por `complete_name` (genérico); `ruta.py` es NAU-2 (no usar). El JS que separa la ubicación filtra `EFFEC`/`Stock` y `^NAVE` (`preparacion.js:2764, 2773`): cosmético.
13. **Prefijo EAN y talla** — `PREFIJO_KOROSHI` (`lectura.py:34`) y `_talla`/`_modelo` por formato de nombre NATH (`lectura.py:315-363`). Degradan (mensajes peores), no bloquean.
14. **Tipos de operación por nombre** — no encontrado: preparación usa solo `picking_type_code` ('outgoing'/'internal') y `default_location_src_id`; no busca tipos por nombre. Tampoco asume un único `stock.warehouse` (no hay búsquedas de almacén salvo en tests: `test_idempotencia.py:30`).
15. **Parámetros por defecto NATH** — empleados `OP9990001,OP9980001`, horario de alarma, capacidades de caja (`data/parametros*.xml`, `lectura.py:44-60`).
16. **koroshi_caja_existente** — solo actúa con empresa 8, OUT y CJ (`stock_picking.py:38-39`); busca la caja por nombre en TODAS las empresas (`stock.quant.package` con sudo, 40) — en multiempresa debería filtrar por empresa. Su regla de «mismo pedido» compara `origin`, `partner_id`, `picking_type_id`, `location_dest_id` (53-59): genérica. Corrige `number_of_packages` (campo de delivery_package_number en TUCTUC, protegido con `in self._fields`, 161). Sin él, leer una matrícula ya usada en preparación crea una caja DUPLICADA (`put_in_pack` de stock_barcode_optimization siempre crea una nueva; en NATH lo paraba una acción automática 20, que en TUCTUC no existe: no encontrado). Si en Oriola los BOX los pone Odoo (secuencia), este módulo no hace falta.
17. **koroshi_warehouse_map** — NAU-2 de arriba abajo (plano HTML, `KOR-ddmm-*`, empresa 8). No aporta nada a la preparación: no clonar.
18. **Consumibles** — empresa 8 (`consumable.py:251`), cajas KOROSHI fijas (252-257), menú bajo warehouse_map (views:180). Clonar solo si se quiere contar cajas.

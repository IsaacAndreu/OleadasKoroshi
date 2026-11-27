# Inventario para clonar a `tuctuc_*`: base, operarios, pda_app, faltantes, contenedores (Compactar)

Origen: `odoo/modulos/` (rama feat/tuctuc-pda, commit e71282a). Solo lectura. Destino: odoo.tuctuc.com (Odoo 13 EE),
nave Oriola-Amposta, multicompañía: PRIME COLLECTIONS (cía 1, WH-OR), MODA INTIMA 1964 (cía 23, MODAI),
UNITED BRANDS 2015 (cía 21, UBRAN).

Convenciones: `archivo:línea`. «no encontrado» = buscado en los 5 módulos y no aparece. «verificar» = depende del
destino o del núcleo de Odoo, no se puede comprobar desde este repo.

---

## A. Inventario por módulo

### A.1 koroshi_base (13.0.1.2.1) — depende de `base`, `web`

| Archivo | Líneas |
|---|---|
| `__init__.py` | 3 |
| `__manifest__.py` | 47 |
| `comun.py` | 154 |
| `pda.py` | 71 |
| `data/parametros.xml` | 14 |
| `static/src/js/comun.js` | 119 |
| `tests/test_comun.py` | 125 |
| `views/assets.xml` | 8 |

- Modelos: ninguno (Python puro + ayudas para las rutas).
- `comun.py`: `COMPANY_ID=8` (:14), `TZ='Europe/Madrid'` (:15), `RE_CJ`/`es_matricula` (:18-23), `ahora_local`,
  `hoy_local`, `inicio_dia_utc`, `rango_dia_utc`, `rango_dias_utc`, `a_local`, `dia_local` (:30-68),
  turnos `PARAM_TURNOS`/`TURNOS`/`leer_turnos`/`texto_turnos`/`turno_de` (:78-138), `variantes_codigo` (:144-154).
- `pda.py`: `comprobar_grupo` (:21), `es_empleado_valido` (:27), `empleado_valido` (:35), `buscar_producto` (:53).
- Controladores/rutas: ninguno.
- JS: `odoo.define('koroshi_base.comun')` (comun.js:1). Exporta `COMPANY_ID:8`, `RE_CJ`, `RAFAGA_MS`, `esMatricula`,
  `tarjeta` (clave localStorage `koroshi_operarios_pda_<uid>`, :25-60; `tarjeta.minutos` llama a la ruta
  `/koroshi/operarios/minutos_tarjeta` de koroshi_operarios, :52 → dependencia inversa implícita), `esFinDeLectura`,
  `leerAlParar`, `cancelarLector`. Sin acción de cliente.
- Assets: `views/assets.xml:3` hereda `web.assets_backend`.
- Datos: `data/parametros.xml:9-12` parámetro `koroshi_base.turnos` (noupdate).
- Migraciones: ninguna. Tests: `tests/test_comun.py` (16 tests, unittest sin Odoo; :21-22 afirman `COMPANY_ID==8` y TZ).
- Consumidores de `comun.COMPANY_ID` en el repo (Python): pda.py, koroshi_contenedores, koroshi_faltantes (relativo,
  relativo_correo), koroshi_pda_app y ~35 ficheros de otros módulos fuera de alcance (kpi, menu, monitor, zonas,
  preparacion…). En JS, `comun.COMPANY_ID` no lo usa nadie (solo se define en comun.js:110).
- Turnos (`turno_de`/`texto_turnos`): solo los usan koroshi_actividades, koroshi_informe y koroshi_monitor; ninguno
  de los 5 módulos de este alcance.

### A.2 koroshi_operarios (13.0.2.25.0) — depende de `web, mail, hr, stock, stock_picking_batch, stock_barcode, koroshi_base`

| Archivo | Líneas | Archivo | Líneas |
|---|---|---|---|
| `README.md` | 363 | `models/tarea.py` | 570 |
| `__init__.py` | 4 | `models/reparto.py` | 876 |
| `__manifest__.py` | 220 | `models/tablero.py` | 489 |
| `controllers/__init__.py` | 2 | `models/tablero_areas.py` | 263 |
| `controllers/main.py` | 343 | `models/informe.py` | 23 |
| `data/categoria.xml` | 6 | `models/__init__.py` | 6 |
| `data/cron.xml` | 17 | `security/grupo.xml` | 37 |
| `data/informe.xml` | 22 | `security/ir.model.access.csv` | 11 |
| `data/motivos.xml` | 31 | `static/src/css/operarios.css` | 388 |
| `data/motivos_v2100.xml` | 16 | `static/src/css/tablero.css` | 29 |
| `data/motivos_v2170.xml` | 11 | `static/src/css/tablero_areas.css` | 58 |
| `data/motivos_v221.xml` | 8 | `static/src/js/operarios_pantalla.js` | 1205 |
| `data/parametros.xml` | 34 | `static/src/js/sin_error_cors.js` | 16 |
| `migrations/13.0.2.20.0/post-migrate.py` | 22 | `static/src/js/tablero.js` | 92 |
| `migrations/13.0.2.21.1/post-migrate.py` | 29 | `static/src/js/tablero_areas.js` | 234 |
| `views/assets.xml` | 17 | `static/src/xml/operarios.xml` | 153 |
| `views/etiquetas_report.xml` | 73 | `views/tablero_views.xml` | 110 |
| `views/gestion_views.xml` | 79 | `views/tarea_views.xml` | 174 |
| `views/menu.xml` | 32 | `views/wizard_views.xml` | 30 |
| `views/reparto_views.xml` | 249 | `wizard/__init__.py` | 4 |
| `wizard/asignar.py` | 81 | `wizard/crear_operarios.py` | 48 |
| `wizard/gestion_operarios.py` | 154 | `static/description/icon*.png` | — |

Modelos definidos:
- `koroshi.operario.tarea` (tarea.py:74) — productividad por tarea (OUT o agrupación).
- `koroshi.operario.motivo` (reparto.py:57) — motivos de «Saltar» (destino oficina/final/suya/libre/pausa).
- `koroshi.operario.dia` (reparto.py:75) — reparto del día por compañía (modo auto/pasillos/manual; `unique(fecha, company_id)` :112).
- `koroshi.operario.tramo` (reparto.py:166) — operarios de hoy y tramo de lineales.
- `koroshi.operario.asignacion` (reparto.py:255) — la cola; índice único parcial en `init()` (:331-340).
- `_inherit koroshi.operario.asignacion` en tablero.py:69 (tipos `lote`/`nota`, estado `pieza`, `_dar_nueva`
  sobrescrito :323, `_siguiente_de_tarjeta` :156, `nota_hecha` :176, kanban) y tablero_areas.py:69 (tablero por áreas).
- `koroshi.operario.informe` (AbstractModel, informe.py:21; vacío, solo exporta `codigo_corto`, `hm`, `RE_OP` para koroshi_informe).
- Wizards: `koroshi.crear.operarios` (crear_operarios.py:10), `koroshi.operario.asignar` (asignar.py:10),
  `koroshi.operarios.gestion` + `.linea` (gestion_operarios.py).
- Heredados de Odoo: ninguno (no añade campos a stock.*/hr.*).

Rutas (controllers/main.py, todas `type='json', auth='user'`, con `sudo()` interno):
`/koroshi/operarios/leer` (:159), `/operario` (:204), `/siguiente` (:213), `/nota_hecha` (:222), `/motivos` (:234),
`/saltar` (:243), `/soltar` (:268), `/dejar` (:282), `/estado` (:294), `/minutos_tarjeta` (:310).

JS:
- `koroshi_operarios.Pantalla` (operarios_pantalla.js:1) → acción de cliente `koroshi_operarios_pantalla` (:1203).
- `koroshi_operarios.sin_error_cors` (sin_error_cors.js:1).
- `koroshi_operarios.Tablero` (tablero.js:1) → vista `js_class` `koroshi_tablero` (:90).
- `koroshi_operarios.TableroAreas` (tablero_areas.js:1) → acción de cliente `koroshi_tablero_areas` (:232).
- QWeb: `koroshi_operarios.Pantalla` (static/src/xml/operarios.xml:5; koroshi_faltantes la extiende por `.o_ko_dejar`).
- Assets: views/assets.xml:3 (operarios.css/js, sin_error_cors.js, tablero.css/js, tablero_areas.css/js).

Acciones/vistas: `action_koroshi_operarios_pantalla` (tarea_views.xml:170, tag :172), tareas/productividad
(tarea_views.xml:135,146), `action_koroshi_validadas_sin_operario` (:153), empleados (:161); reparto/colas/motivos/asignar
(reparto_views.xml:68,178,200,230,240 — 230 y 240 con binding a stock.picking y stock.picking.batch); gestión + informe
tarjeta (gestion_views.xml:41,49,58); tablero kanban/form/acciones (tablero_views.xml:8,57,90,101; menú app :107);
portada + server action imprimir (etiquetas_report.xml:4,19,29,64); menús (menu.xml; app «Lecturas (PDA)» :5).

Datos: cron `cron_koroshi_operarios_cerrar` cada 5 min (cron.xml:7); parámetros noupdate `minutos_inactividad`(0),
`uds_a_dos`(150), `minutos_sin_leer`(15), `minutos_cierre_inactividad`(15), `minutos_tarjeta`(60) (parametros.xml);
`informe_destinatarios/hora/servidor` (informe.xml:5-16, ya sin uso); categoría `Operario KOROSHI` (categoria.xml:3);
motivos (motivos*.xml; motivos_v221.xml archiva 3 motivos en cada actualización); grupos `grupo_productividad`,
`grupo_tarjeta_obligatoria`, `grupo_tablero` (grupo.xml:7,17,25; :34-36 quita implied de base.group_system).
ACL: solo para `grupo_productividad`/`grupo_tablero` (ir.model.access.csv) — el usuario PDA no tiene ACL; las rutas usan sudo.
Plantillas de correo: ninguna.

Migraciones: 13.0.2.20.0 y 13.0.2.21.1 (logins @nath.es al grupo tablero). Tests: ninguno.

### A.3 koroshi_pda_app (13.0.1.2.0) — depende de `web, koroshi_base, koroshi_operarios`

| Archivo | Líneas |
|---|---|
| `README.md` | 39 |
| `__init__.py` | 3 |
| `__manifest__.py` | 41 |
| `controllers/__init__.py` / `main.py` | 2 / 88 |
| `data/parametros.xml` | 16 |
| `models/__init__.py` / `res_users.py` | 2 / 21 |
| `views/layout.xml` | 23 |
| `static/img/icon-192.png`, `icon-512.png`, `static/description/icon.png` | — |

- Modelos: `_inherit res.users` (res_users.py:12) método `koroshi_pda_app_activa`.
- Rutas (auth='none', http): `/koroshi_pda/manifest.webmanifest` (:51), `/koroshi_pda/sw.js` (:76), `/koroshi_pda/inicio` (:84).
- JS: ninguno con odoo.define (solo un `<script>` en layout.xml:13-19 que registra el SW en Android).
- Plantilla: `layout_pda_app` hereda `web.layout` (layout.xml:6).
- Datos: `koroshi_pda_app.usuarios`='2' (parametros.xml:5-8), `koroshi_pda_app.inicio`='lecturas' (:11-14).
- Migraciones/tests: ninguno.

### A.4 koroshi_faltantes (13.0.1.12.0) — depende de `web, hr, stock, stock_picking_batch, stock_barcode, koroshi_base, koroshi_operarios`

| Archivo | Líneas | Archivo | Líneas |
|---|---|---|---|
| `README.md` | 273 | `models/faltante.py` | 1022 |
| `__init__.py` | 4 | `models/relativo.py` | 248 |
| `__manifest__.py` | 127 | `models/relativo_correo.py` | 182 |
| `controllers/main.py` | 341 | `models/__init__.py` | 4 |
| `data/cron.xml` | 16 | `security/ir.model.access.csv` | 5 |
| `data/cron_relativo.xml` | 26 | `static/src/css/faltantes.css` | 141 |
| `data/parametros.xml` | 15 | `static/src/js/faltantes_pantalla.js` | 691 |
| `data/parametros_correo.xml` | 13 | `static/src/xml/faltantes.xml` | 43 |
| `data/parametros_relativo.xml` | 17 | `views/assets.xml` | 9 |
| `data/ubicacion.xml` | 13 | `views/faltante_views.xml` | 270 |
| `data/ubicacion_v131.xml` | 7 | `views/menu.xml` | 35 |
| `wizard/encontrado.py` | 24 | `views/relativo_views.xml` | 107 |
| `wizard/__init__.py`, `controllers/__init__.py` | 2/2 | `views/wizard_views.xml` | 20 |

- Modelos: `koroshi.faltante` (faltante.py:89), `koroshi.faltante.relativo` (relativo.py; tabla llenada por SQL),
  extensión de correo en relativo_correo.py, wizard `koroshi.faltante.encontrado` (encontrado.py:9). Sin herencias de Odoo.
- Rutas (json, auth user, **sin sudo**: usuario de sesión): `/koroshi/faltantes/buscar` (:195), `/reubicar` (:276),
  `/sin_alternativa` (:304), `/pendientes` (:321), `/validar` (:332).
- JS: `koroshi_faltantes.Pantalla` (faltantes_pantalla.js:1) → acción `koroshi_faltantes_pantalla` (:659);
  `koroshi_faltantes.BotonOperarios` (:663) hace `Operarios.include` (botón Faltante en Lecturas, :668-688) y abre
  `koroshi_faltantes.action_koroshi_faltantes_pantalla` (:681). QWeb `koroshi_faltantes.Pantalla` y `t-extend`
  de `koroshi_operarios.Pantalla` (faltantes.xml:3,38-39).
- Acciones: `action_koroshi_faltantes_pantalla` (faltante_views.xml:266, tag :268), revisión/rondas/puestos a 0
  (:151-207), % faltante (relativo_views.xml:60-101).
- Datos: ubicación `ubicacion_faltant` FALTANTE (ubicacion.xml:5-12, noupdate; v131 renombra), crons
  `cron_koroshi_faltantes_rondas` 15 min (cron.xml:6), `cron_koroshi_faltante_relativo` 1 h y `_correo` 15 min
  (cron_relativo.xml:4,16), parámetros `validar_sola`, `pedido_pendiente`, `vigilar/alarma/critico_pct`,
  `correo_destinatarios`, `correo_hora`. Grupos propios: ninguno (usa stock.group_stock_user/manager).
  Plantillas de correo: ninguna (correo HTML montado en Python, relativo_correo.py).
- Migraciones/tests: ninguno.

### A.5 koroshi_contenedores (13.0.1.17.0, «Compactar fase 1 en curso») — depende de `web, stock, hr, barcodes, koroshi_base, koroshi_operarios, koroshi_faltantes`

| Archivo | Líneas |
|---|---|
| `__init__.py` | 3 |
| `__manifest__.py` | 169 |
| `controllers/__init__.py` / `main.py` | 2 / 1710 |
| `data/parametros.xml` | 43 |
| `logica.py` | 313 |
| `models/__init__.py` / `compactar.py` / `movimiento.py` | 3 / 50 / 49 |
| `security/grupos.xml` / `ir.model.access.csv` | 9 / 4 |
| `static/src/css/contenedores.css` | 109 |
| `static/src/js/contenedores.js` | 2018 |
| `static/src/xml/contenedores.xml` | 25 |
| `tests/test_logica.py` | 259 |
| `views/assets.xml` / `menu.xml` / `views.xml` | 9 / 15 / 138 |

- Modelos: `koroshi.contenedor.movimiento` (movimiento.py:5; Many2one `faltante_id` a koroshi.faltante :37 →
  dependencia dura de faltantes), `koroshi.compactacion.paso` (compactar.py:11), `koroshi.contenedor.banda`
  (compactar.py:39). Sin `company_id` en ninguno de los tres.
- Rutas (json, auth user, todo con sudo): `/koroshi/contenedores/hueco` (:177), `/limpiar` (:190), `/detalle` (:307),
  `/archivar` (:319), `/archivar_uno` (:354), `/producto` (:399), `/cero` (:496), `/anadir` (:554), `/cantidad` (:617),
  `/cambiar_articulo` (:704), `/buscar` (:863), `/donde` (:873), `/leer` (:909), `/mover` (:954),
  `/ronda/resumen` (:1118), `/ronda/lineal` (:1150), `/ronda/hueco` (:1181), `/ronda/retirar` (:1195),
  `/ronda/con_prendas` (:1242), `/ronda/lista` (:1263), `/compactar/calcular` (:1462), `/compactar/lineal` (:1553),
  `/compactar/resumen` (:1566), `/compactar/hacer` (:1601), `/compactar/marcar` (:1687).
- JS: `koroshi_contenedores.Pantalla` (contenedores.js:1) → acción `koroshi_contenedores_pantalla` (:2016);
  usa `koroshi_base.comun` (:50). QWeb `koroshi_contenedores.Pantalla` (contenedores.xml:3).
- Acciones: `action_koroshi_contenedores_pantalla` (views.xml:3, tag :5), movimientos (:60), pasos (:115), bandas (:133).
  Menús: app «Contenedores» (menu.xml:3) y submenú bajo `koroshi_operarios.menu_koroshi_operarios_root` (menu.xml:6).
- Datos (noupdate): `cajas_cero_lineales`='44-136', `tarjetas_revisar`='0', `tarjetas_con_prendas`='0',
  `cajas_columna`=8, `cajas_vaciar`=4, `lineales_distancia`=2, `temporadas_zona0`='I27,V27' (parametros.xml:9-41).
  Grupo `group_revisar` (grupos.xml:5).
- `logica.py` (sin Odoo): repartir, modelo/mismo_modelo, rango_lineales (`RANGO_LINEALES=(44,136)` :74), lineal_de,
  orden_hueco, clasificar, ids_tarjetas, partir_codigo, tallas_por_altura, banda_caja, clases_abc, plan_lineal, aviso_destino.
- Tests: `tests/test_logica.py` (38 tests sin Odoo; datos KO_/MU-/modelos KOROSHI). Migraciones: ninguna.

### A.6 Referencias de operarios / pda_app a otros módulos KOROSHI

| Módulo | Dónde | Tipo |
|---|---|---|
| koroshi_actividades | operarios_pantalla.js:767-785 (`sessionStorage koroshi_inicio_pda`, `do_action('koroshi_actividades.action_koroshi_inicio_pda')`, ruta `/koroshi/actividades/inicio/salir`) | Opcional (solo si el Inicio marcó el navegador) |
| koroshi_actividades | pda_app controllers/main.py:27-28,46-48 (`env.ref(..., raise_if_not_found=False)`) | Opcional |
| koroshi_actividades | tablero_areas.py:102-106,121-123 (`'koroshi.actividad.registro' in self.env`) | Opcional |
| koroshi_contenedores | tablero_areas.py:96-101,124-127 (`'koroshi.contenedor.movimiento' in self.env`) | Opcional |
| koroshi_preparacion | tarea.py:174,185,325,514 (`'koroshi.preparacion.lectura' in self.env`); operarios_pantalla.js:46 (claves localStorage) | Opcional |
| koroshi_zonas / koroshi_preparacion | tablero.py:35-41 (copias de RE_CAJA_NOTA, RE_ZONA, `_numero_pedido`) | Copia, sin import |
| koroshi_menu | — | no encontrado |
| koroshi_kpi | — | no encontrado (en faltantes sí: relativo.py:166 `to_regclass('koroshi_kpi_falta')`, opcional) |
| koroshi_monitor | — | no encontrado (solo comentarios) |
| Dependencias inversas | koroshi_informe importa `codigo_corto`, `hm`, `RE_OP`, `ZONA_HORARIA` (informe.py, tarea.py:32) | Fuera de alcance |

Ninguna referencia DURA de operarios/pda_app a actividades, menu, kpi o monitor.

---

## B. Puntos propios de la instancia NATH / KOROSHI (con cambio propuesto en el clon)

### B.1 Compañía 8 y cids=8
| archivo:línea | Qué | Cambio en el clon |
|---|---|---|
| koroshi_base/comun.py:14 | `COMPANY_ID = 8` | Quitar la constante; función `compania_de(registro)` (picking/ubicación/quant) o lista de compañías del almacén por parámetro `tuctuc_base.companias` (1,21,23). |
| koroshi_base/static/src/js/comun.js:110 | `COMPANY_ID: 8` | Quitar (nadie lo usa en JS). |
| koroshi_base/tests/test_comun.py:21 | afirma 8 | Ajustar test. |
| koroshi_base/pda.py:13,70 | `buscar_producto` por nombre con `company_id in [8, False]` | Pasar `companias` (las del usuario o la del documento) como argumento. |
| koroshi_pda_app/controllers/main.py:24-27 | `/web#cids=8&action=koroshi_operarios_pantalla` y AREAS | `cids=1,21,23` (o las `company_ids` del usuario, calculadas en `_destino`) y acción `tuctuc_operarios_pantalla`. Imprescindible: la app de código de barras usa `allowed_company_ids` de la sesión. |
| koroshi_pda_app/README.md:25 | URL con cids=8 y `nath.tuctuc.com` (:14,19) | Documentación. |
| koroshi_faltantes/data/ubicacion.xml:10-11 | almacén `code='EFFEC'`, `company_id 8` | Crear FALTANTE por almacén (WH-OR, MODAI, UBRAN) con `post_init_hook` o 3 registros. |
| koroshi_faltantes/models/relativo.py:157 | `cia = comun.COMPANY_ID` | Recorrer las 3 compañías (fila por compañía) o parámetro. |
| koroshi_faltantes/models/relativo_correo.py:136 | remitente de la compañía 8 | Compañía del usuario/cron o parámetro. |
| koroshi_contenedores/controllers/main.py:35,46 | `COMPANY_ID`, `DE_LA_COMPANIA` | Compañía de la ubicación/contenedor leído o elegida por el operario (ver C). |
| koroshi_contenedores/controllers/main.py:386,594,667,698,773,848,857,1052-1054,1363-1364,1385-1387,1400-1405 | usos de `COMPANY_ID` | Ver sección C. |

### B.2 Almacén EFFEC / NAVE2 / prefijo `EFFEC/`
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_operarios/models/tarea.py:248 | `ref.replace('EFFEC/', '')` | Quitar el prefijo de almacén genérico: `re.sub(r'^[^/]+/', '', ref)` o usar `picking_type_id.warehouse_id.code`. |
| koroshi_operarios/models/tablero_areas.py:95,172,225 | `.replace('EFFEC/', '')` | Ídem (solo tablero, se puede no clonar). |
| koroshi_faltantes/models/faltante.py:65 | `ZONA_PICKING = 'NAVE2'` | En destino el nivel es `N1` (`WH-OR/Stock/N1/...`, `UBRAN/STOCK/N1/...`). Parámetro `tuctuc_faltantes.zona_picking` (lista). |
| koroshi_faltantes/models/faltante.py:205-213 | `_excluida` exige NAVE2 en la ruta | Usar el parámetro anterior. |
| koroshi_faltantes/models/faltante.py:77-86 | `nombre_corto`: ejemplo EFFEC y `split('/Stock/')` | UBRAN usa `STOCK` en mayúsculas: hacer el split sin distinguir mayúsculas o desde `lot_stock_id.complete_name`. |
| koroshi_faltantes/models/faltante.py:171 | docstring «EFFEC/Stock» | Texto. |
| koroshi_faltantes/controllers/main.py:129-131 | número suelto → `%/23649` (comentario EFFEC/OUT) | Con 3 almacenes habrá 2-3 coincidencias (WH-OR/OUT/…, MODAI/OUT/…): filtrar por compañías del usuario o pedir el nombre completo. |
| koroshi_faltantes/data/ubicacion.xml:3,10 | FALTANTE bajo la vista EFFEC | Ver B.1. |
| koroshi_base/comun.py:14 | comentario «EFFECTIVE LOGISTICS, NAU-2» | Texto. |

### B.3 Expresiones de ubicación (L P C, MU-, N1-) y coordenadas de pasillo
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_operarios/models/reparto.py:34 | `RE_LINEAL = r'\bL(\d+)\b'` (modo por pasillos) | Compatible con `06298 - L75 P38 C2`. Mantener; ojo: la ruta incluye el KO, no tiene L. |
| koroshi_operarios/models/reparto.py:410-423 | SQL `substring(l.complete_name from '\mL([0-9]+)\M')` + `p.company_id = %s` | Igual regex; compañía del día. |
| koroshi_faltantes/models/faltante.py:67-68 | `RE_LINEAL`, `RE_HUECO = r'((?:L|MU-)\d+\s+P\d+\s+C\d+)'` | `L75 P38 C2` encaja. `MU-` (muelle): en el destino no encontrado; dejarlo inofensivo o parametrizar. |
| koroshi_faltantes/models/faltante.py:62-64 | comentario `N1-L09 P08 C1` (MU1), DEVOLUCIO_KOROSHI, CAJAS, PRUEBA, PERCHAS_KO | Nombres de NATH; revisar qué ubicaciones excluir en Amposta (no encontrado en el destino). |
| koroshi_faltantes/models/faltante.py:223-238 | distancia = |lineal − lineal viejo| | Coordenada de pasillo = número de lineal. Vale si la numeración L de Amposta es lineal; si no, tabla de distancias (verificar). |
| koroshi_contenedores/controllers/main.py:48-49,62-69 | `LINEAL_RE`, `LINEAL_DELANTE_RE` (L y MU-xx) | Mantener L; MU según destino. |
| koroshi_contenedores/controllers/main.py:148-152 | lineal en medio del nombre (`' L94 '`) o al principio (MU) | Compatible con `06298 - L75 P38 C2`. |
| koroshi_contenedores/controllers/main.py:845 | `^(L\d|MU-|KO_|TT_)` | Añadir `UB_`. |
| koroshi_contenedores/controllers/main.py:1161-1162,1398-1402,1508-1509 | `h.name ILIKE '% L67 %'` / `'L67 %'` | Compatible; añadir filtro de compañía/almacén. |
| koroshi_contenedores/controllers/main.py:1524-1525 | columna = texto tras `' - '` | Compatible con `06298 - L75 P38 C2`. |
| koroshi_contenedores/logica.py:74 | `RANGO_LINEALES = (44, 136)` zona 0 | Parámetro por almacén (Amposta: no encontrado). |
| koroshi_contenedores/logica.py:75-78,90-100 | `_RE_LINEAL/_RE_P/_RE_C` | Compatibles. |
| koroshi_contenedores/logica.py:231-232,261 | clase A al lineal más bajo (muelle antes de L01) | Supuesto de la nave de NATH. Confirmar en Amposta dónde está el muelle; si no, parámetro de sentido. |
| koroshi_contenedores/data/parametros.xml:9-11 | `cajas_cero_lineales` 44-136 | Valor de Amposta (no encontrado). |
| koroshi_contenedores/data/parametros.xml:26-37 | 8 cajas/columna, vaciar <4, ±2 lineales | Confirmar físico de Amposta. |
| koroshi_contenedores/controllers/main.py:43-46 | Comentario: UBRAN tiene **los mismos huecos con el mismo código de barras** (`UBRAN/STOCK/N1/07828 - L94 P35 C1`) | Clave para el clon: un código de barras de hueco puede dar 2-3 ubicaciones (una por compañía). Desempatar por la compañía del contenedor/operario. |

### B.4 Prefijos de contenedor KO_/TT_ (destino: KO_, TT_, UB_)
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_contenedores/controllers/main.py:32 | `PREFIJOS = ('KO_', 'TT_')` | `('KO_', 'TT_', 'UB_')` o parámetro. |
| koroshi_contenedores/controllers/main.py:812-813 | dominio `=ilike 'KO\_%'` / `'TT\_%'` | Generar desde PREFIJOS. |
| koroshi_contenedores/controllers/main.py:1053 | SQL `upper(left(c.name,3)) IN ('KO_','TT_')` | Desde PREFIJOS. |
| koroshi_contenedores/controllers/main.py:1405 | SQL `NOT IN ('KO_','TT_')` | Ídem. |
| koroshi_contenedores/controllers/main.py:891 | `l.name.upper()[3:]` (prefijo de 3) | Vale si todos los prefijos tienen 3 caracteres (KO_, TT_, UB_ sí). |
| koroshi_contenedores/static/src/js/contenedores.js:3,1484,1552,1990 | textos «KO_/TT_», «KO_…», «etiqueta KO_» | Textos. |
| koroshi_faltantes/static/src/js/faltantes_pantalla.js:637 | comentario `KO_110626_032` | Texto. |
| koroshi_contenedores/tests/test_logica.py:102-103,130 | datos KO_/MU- | Tests. |

### B.5 Matrícula CJ
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_base/comun.py:17-23 | `RE_CJ`, `es_matricula` | Ningún módulo del alcance lo usa. Clonar solo si se clona Preparación; si no, quitar. |
| koroshi_base/static/src/js/comun.js:13,18-20 | `RE_CJ`, `esMatricula` | Ídem. |
| koroshi_operarios/models/reparto.py:100,608 | textos «matrícula CJ preimpresa», acción reserva CJ | Solo reparto/etiquetas (manager). |

### B.6 Agrupaciones Z- (destino: B-ECI_…, B-VP_…, WEB_…; sin Z-)
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_operarios/models/tarea.py:33 | `PREFIJOS_ZONA = ('Z-',)` | Inofensivo en destino (no hay Z-), pero leer una agrupación B-ECI_ se trata como `agrupacion` entera (tarea.py:396-398). Decidir prefijos de agrupación «entera» por parámetro. |
| koroshi_operarios/models/reparto.py:437-438,453 | candidatos excluyen OUT de Z- y buscan lotes `name =like 'Z-%'` | Parametrizar; en destino `agrupaciones` = vacío. |
| koroshi_operarios/models/reparto.py:761 | OUT de zona leída sola | Ídem. |
| koroshi_operarios/models/tablero.py:38-41 | `RE_CAJA_NOTA`, `RE_ZONA`, `RE_TRADICIONAL` (Z-ddmm-D/MU/T) | En destino todas las agrupaciones caen en «grupo 2, OUT a OUT» (:272). Revisar si B-ECI_ debe darse OUT a OUT o entera. |
| koroshi_operarios/controllers/main.py:74-78 | `_zona(lote)` = último trozo tras `-` o `_` | Con `B-ECI_271126_06` da `06`. Revisar qué mostrar. |
| koroshi_operarios/models/tarea.py:137-141 | `_compute_zona` ídem | Ídem. |
| koroshi_faltantes/models/faltante.py:55; controllers/main.py:36,147-150,189 | `PREFIJOS_ZONA` y `_lote` solo si empieza por Z- | En destino no se podría leer una agrupación en Faltante; parametrizar prefijos. |
| koroshi_faltantes/static/src/js/faltantes_pantalla.js:60,673 | comentarios Z- | Texto. |

### B.7 EAN y referencias de producto
| archivo:línea | Qué | Cambio |
|---|---|---|
| (todos) | Prefijo EAN 8447333 / 8435689 | no encontrado (no hay prefijo EAN fijo en el código). |
| koroshi_base/pda.py:65-66 | `product.barcode` (código alternativo) si existe el modelo | En destino no existe `product.barcode`: el `if 'product.barcode' in env` ya lo salta. Sin cambio. |
| koroshi_base/comun.py:144-154 | UPC 12 → con 0; EAN 13 con 0 → sin 0 | Genérico. Sin cambio. |
| koroshi_faltantes/models/relativo.py:28-29 | `PATRON_PRENDA = '^[0-9]{4}[A-Z]{2}[0-9]{2}-'` (nombres KOROSHI) | Parámetro; patrón de los productos del destino: no encontrado. |
| koroshi_faltantes/views/relativo_views.xml:51 | filtro «Temporada 26» `name =like '26%'` | Revisar. |
| koroshi_contenedores/logica.py:31-40 | `modelo()` = nombre sin la última parte `-talla` | Supone referencia `MODELO-COLOR-TALLA`. Verificar formato de referencias del destino. |
| koroshi_contenedores/logica.py:153,159-169 | `partir_codigo` (modelo, color, talla) y formato antiguo `\d{6}` | Ídem: núcleo de Compactar (modelo-color). Si el destino no codifica así, el plan no agrupa bien. |
| koroshi_contenedores/controllers/main.py:1373-1387 | `upper(pp.default_code) LIKE ANY ('MC-%')` | Ídem. |
| koroshi_contenedores/controllers/main.py:1423-1425 | campo `season_id` en product.template; temporadas I27,V27 | Existencia de `season_id` en destino: verificar. Si no existe, `temporada` vacía → todas las columnas quedan «z» y no se compacta nada (:1439-1442). BLOQUEANTE si no existe. |

### B.8 Correos, servidor de correo, logins, ids de usuario y de empleado
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_operarios/data/informe.xml:7 | `isaac.andreu@nath.es` | No clonar (sin uso desde v2.12). |
| koroshi_operarios/data/informe.xml:15 | servidor `NATH` | No clonar. |
| koroshi_faltantes/data/parametros_correo.xml:7 | `isaac.andreu@nath.es` | Destinatario de TUCTUC o vacío. |
| koroshi_faltantes/models/relativo_correo.py:19 | `DEF_DESTINATARIOS` @nath.es | Vacío por defecto. |
| koroshi_faltantes/models/relativo_correo.py:134 | servidor de correo por nombre `'NATH'` | Parámetro sin valor por defecto. |
| koroshi_operarios/migrations/13.0.2.20.0/post-migrate.py:10 | `almacen2@nath.es` | No clonar migraciones. |
| koroshi_operarios/migrations/13.0.2.21.1/post-migrate.py:11-12 | `almacen2@`, `departamentit@`, `ismael@`, `almacen@nath.es` | No clonar. |
| koroshi_operarios/security/grupo.xml:22-24,31-33 | comentarios Almacen 2 / Almacén Nath | Texto. |
| koroshi_faltantes/models/faltante.py:59-61 | `CERO_USUARIOS_DEFECTO = 'almacen@nath.es,almacen2@nath.es'`, `CERO_DESDE_DEFECTO='2026-11-01'` | Defecto vacío; parámetro con logins del destino. |
| koroshi_pda_app/data/parametros.xml:7 | `koroshi_pda_app.usuarios = 2` (id de usuario de NATH) | Valor del destino (id del usuario PDA de TUCTUC) o `*`. |
| koroshi_contenedores/data/parametros.xml:6-7,13-20 | `tarjetas_revisar`, `tarjetas_con_prendas` (ids hr.employee; aquí `0`) y nombres Isaac/Betty/José Luis/Jordi/Darwin en comentario | Ids de empleados del destino (no encontrados). Solo afectan a la ronda de cajas a 0 y a «revisar». |
| koroshi_contenedores/security/grupos.xml:3-4 | comentario usuarios | Texto. |
| koroshi_operarios/wizard/crear_operarios.py:15,42 | prefijo `OP` + 4 cifras | En destino ya hay 61 empleados con barcode (formato no encontrado); el asistente puede no clonarse. |
| koroshi_operarios/models/tarea.py:41-47 | `RE_OP = ^([A-Za-z]+)0*(\d+)$` (OP0007→OP7) | Si el barcode del destino es numérico puro, `codigo_corto` devuelve el código tal cual. Sin cambio. |

### B.9 Turnos, zona horaria y pausas
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_base/comun.py:15 | `TZ='Europe/Madrid'` | Amposta también es Europe/Madrid; mejor parámetro o `tz` de la compañía/usuario. |
| koroshi_base/comun.py:78-79; data/parametros.xml:9-12 | `koroshi_base.turnos` (06-14 con 15 min; 08-13 y 14-17) | Ningún módulo del alcance lo usa. Clonar solo si se clona Actividades/Informe; si se clona, valor de Amposta (no encontrado). |
| koroshi_operarios/models/reparto.py:470 | `_dejadas_hoy`: medianoche en **UTC** (`fields.Datetime.now().replace(hour=0…)`) | Bug latente (1-2 h de desfase): usar `comun.inicio_dia_utc(comun.hoy_local())`. |
| koroshi_operarios/data/motivos_v2100.xml:11-14 | motivo «Pausa (comer, café)» | Genérico. |

### B.10 Informes/acciones buscados por nombre, y rutas de stock_barcode
| archivo:línea | Qué | Cambio |
|---|---|---|
| koroshi_operarios/models/reparto.py:36-38 | `INFORME_ZONA='koroshi.report_etiqueta_zona'`, `ACCION_ZONA='KOROSHI Etiquetas zona'` (creados a mano en NATH) | No existen en destino (no hay zebra.label). Quitar `_imprimir_etiquetas` del clon o hacerlo opcional. |
| koroshi_operarios/models/reparto.py:595-602,609 | búsqueda por `report_name` / `name` y `.run()` de la acción | Ídem. |
| koroshi_operarios/models/reparto.py:610 | `env.ref('koroshi_operarios.action_report_portada_operario')` | Renombrar xmlid a `tuctuc_operarios.`. |
| koroshi_operarios/controllers/main.py:171 | `has_group('koroshi_operarios.grupo_tarjeta_obligatoria')` | Renombrar xmlid. |
| koroshi_operarios/controllers/main.py:238 | `env.ref('koroshi_operarios.motivo_sin_caja')` | Renombrar. |
| koroshi_operarios/controllers/main.py:63-64 | huella de módulos `name LIKE 'koroshi%'` | Cambiar a `'tuctuc%'`. |
| koroshi_operarios/controllers/main.py:66 | parámetro `koroshi_operarios.recargar_pda` | Renombrar claves de parámetro (todas `koroshi_*` → `tuctuc_*`). |
| koroshi_operarios/static/src/js/operarios_pantalla.js:114 | `user_has_group('koroshi_operarios.grupo_tarjeta_obligatoria')` | Renombrar. |
| koroshi_operarios/static/src/js/operarios_pantalla.js:44,46,204 | claves localStorage `koroshi_operarios_sonido`, `koroshi_preparacion_cola/caducadas`, `koroshi_operarios_pda_` | Renombrar (y en comun.js:27). |
| koroshi_operarios/static/src/js/operarios_pantalla.js:456,488 | `stock.picking.batch.start_batch_processing` | Verificar que existe en destino (stock_barcode 13 EE) y que `stock_barcode_optimization` no lo cambia. |
| koroshi_operarios/static/src/js/operarios_pantalla.js:462,501,507 | ruta `/stock_barcode/scan_from_main_menu` | Ídem. |
| koroshi_operarios/static/src/js/operarios_pantalla.js:812 | `do_action('stock_barcode.stock_barcode_action_main_menu')` | Ídem. |
| koroshi_operarios/static/src/js/operarios_pantalla.js:497-505 | `search_read` de stock.picking / batch por nombre | Con cids de las 3 compañías; nombres de batch pueden repetirse entre compañías (verificar). |
| koroshi_faltantes/static/src/js/faltantes_pantalla.js:421,427,461 | las mismas llamadas a stock_barcode | Ídem. |
| koroshi_faltantes/static/src/js/faltantes_pantalla.js:681 | `do_action('koroshi_faltantes.action_koroshi_faltantes_pantalla')` | Renombrar. |
| koroshi_faltantes/models/faltante.py:164 y relativo.py:158 | `env.ref('koroshi_faltantes.ubicacion_faltant')` | Por almacén (ver C). |
| koroshi_faltantes/models/faltante.py:54 | `NOMBRE_PUESTA_A_CERO = 'Cantidad de producto actualizada'` | Texto de Odoo en español; depende del idioma del usuario PDA del destino (verificar). |
| koroshi_contenedores/controllers/main.py:54 | `GRUPO_REVISAR='koroshi_contenedores.group_revisar'` | Renombrar. |
| koroshi_contenedores/static/src/js/contenedores.js:50 | `require('koroshi_base.comun')` | `tuctuc_base.comun`. |
| koroshi_base/static/src/js/comun.js:52 | ruta `/koroshi/operarios/minutos_tarjeta` | Renombrar rutas `/koroshi/...` → `/tuctuc/...` (las dos BD no comparten servidor, pero mejor no chocar si alguna vez sí). |
| koroshi_pda_app/controllers/main.py:25-29 | rutas `/koroshi_pda/*`, nombre «Lecturas KOROSHI», COLOR | Renombrar marca. |

---

## C. Supuestos de UNA sola compañía (y sudo) — el clon debe sacar la compañía del documento/ubicación

Nota de núcleo (verificar en el código de Odoo 13 del destino): en las rutas JSON llamadas con `_rpc({route})` el
contexto no trae `allowed_company_ids`; entonces `env.company` = compañía por defecto del usuario y `env.companies` =
todas sus compañías. Con `sudo()` no se aplican reglas multicompañía: las búsquedas ven las 3 compañías.

### C.1 koroshi_base
1. comun.py:14 — `COMPANY_ID = 8` global.
2. comun.js:110 — `COMPANY_ID: 8` (sin consumidores).
3. pda.py:70 — producto por nombre en `[COMPANY_ID, False]`.
4. pda.py:31-32 — `es_empleado_valido`: empleado sin compañía o de `env.user.company_ids`. Multicompañía-compatible si el usuario PDA tiene las 3 compañías (requisito de configuración).
5. pda.py:38,47 — `hr.employee` con sudo (ve todas las compañías).
6. pda.py:63-68 — producto con sudo (ve todas las compañías; productos compartidos o no: verificar en destino).

### C.2 koroshi_pda_app
7. controllers/main.py:24-27 — `cids=8` fijo en la URL de entrada (la sesión queda con una sola compañía permitida).
8. controllers/main.py:45 — `env(user=SUPERUSER_ID)` para leer parámetro (inocuo).

### C.3 koroshi_operarios
9. controllers/main.py:45-50 — `_empleado_valido` (igual que 4).
10. controllers/main.py:165-166 — tarjeta buscada con sudo en todas las compañías (bien para multicompañía; sin comprobar validez aquí).
11. controllers/main.py:298 — `/estado`: todas las tareas en curso sin filtro de compañía (cuenta operarios de las 3).
12. controllers/main.py:305 — empleado con sudo sin validar.
13. models/tarea.py:87-88 — `company_id` por defecto `self.env.company`.
14. models/tarea.py:390-398 — `buscar_objetivo`: picking/batch por nombre con sudo y `limit=1`, sin compañía (los nombres de batch podrían repetirse entre compañías: verificar).
15. models/tarea.py:431 — compañía del objetivo (bien) con fallback `env.company`.
16. models/tarea.py:233 — `resumen_operario_dia` sin compañía (informe).
17. models/tarea.py:458,493,520 — crons sobre todas las compañías (correcto).
18. models/tarea.py:553-558 — `action_validadas_sin_operario`: pickings con el usuario (sus compañías) y tareas con sudo (todas).
19. models/reparto.py:82 — `koroshi.operario.dia.company_id` default `env.company`; :112 único por (fecha, compañía).
20. models/reparto.py:121-136 — `de_hoy(company=None)` → `env.company`.
21. models/reparto.py:648 — **`siguiente()` llama `de_hoy()` sin compañía** → modo, «darle otra solo», solo_preparadas y candidatos de la compañía por defecto del usuario PDA. Con 3 compañías, la PDA solo recibiría trabajo automático de una. Hay que decidir: un `dia` por compañía y recorrerlos, o un `dia` del almacén físico sin compañía.
22. models/reparto.py:117-118 — colas del día filtradas por la compañía del día.
23. models/reparto.py:296-297 — `asignacion.company_id` default `env.company`.
24. models/reparto.py:410-423 — SQL `_pickings_tramo` con `p.company_id = %s`.
25. models/reparto.py:429-455 — `_candidatos`: OUT y lotes de `dia.company_id`; `cogidas` (:429,:451) sin compañía (bien).
26. models/reparto.py:537 — asignación con `dia.company_id`.
27. models/reparto.py:636 — `action_imprimir_etiquetas` → `de_hoy()` (env.company).
28. models/reparto.py:790 — compañía del objetivo (bien).
29. models/reparto.py:500 — motivo `libre` buscado sin compañía (catálogo global; bien).
30. models/tablero.py:150 — compañía de la OUT (bien).
31. models/tablero.py:191-194 — columnas del tablero: día y empleados de `env.company`.
32. models/tablero.py:200-207 — `_lotes_vivos(company=None)` → `env.company`.
33. models/tablero.py:287,290,303 — compañía del día.
34. models/tablero.py:340,349,360 — `tablero_refrescar` con `env.company`.
35. models/tablero.py:374 — dominio de la acción con `env.company`.
36. models/tablero_areas.py:117-118,138,198,219 — `env.company`.
37. models/tablero_areas.py:115 — tareas del día sin compañía (mezcla).
38. wizard/crear_operarios.py:16 — default `env.company`.
39. wizard/gestion_operarios.py:28 — `env.companies` (bien).
40. wizard/asignar.py:64 — compañía del objeto con fallback `env.company`.

### C.4 koroshi_faltantes
41. data/ubicacion.xml:9-11 — una sola FALTANTE (cía 8, vista EFFEC).
42. models/faltante.py:163-167 — `_ubicacion_faltant()` único por xmlid → en el clon, FALTANTE del almacén del picking (`picking.picking_type_id.warehouse_id`), p. ej. buscando por código de barras `FALTANTE` + compañía, o campo/parámetro por almacén.
43. models/faltante.py:174-176 — comprobación FALTANTE fuera de la raíz (por almacén en el clon).
44. models/faltante.py:147-148 — default `env.company` (en create se pasa la del picking: :274,281,446,506,698,714 — bien).
45. models/faltante.py:181 — `force_company=company.id` (pérdidas por compañía; bien si `company` = la del picking).
46. models/faltante.py:196-197,218-219 — quants buscados con el usuario (sus compañías) dentro de `raiz` (del almacén del picking; bien).
47. models/faltante.py:671 — `crear_ronda` sin selección: todos los pendientes de las compañías del usuario; agrupa por (tipo INT, origen) → con FALTANTE por almacén queda una INT por almacén (bien si 42 se hace).
48. models/faltante.py:944 — `env.companies` (bien).
49. models/relativo.py:53,63,157 — SQL con `cia = COMPANY_ID`.
50. models/relativo.py:158-159 — `parent_path` de una sola FALTANTE.
51. models/relativo.py:117 — tabla con `company_id` pero se llena con una.
52. models/relativo_correo.py:136 — compañía 8 para el remitente.
53. controllers/main.py:114 — tarjeta con sudo en todas las compañías.
54. controllers/main.py:128-131 — picking por nombre con el usuario (sus compañías); el número suelto da varias coincidencias.
55. controllers/main.py:139-141 — ubicación por código de barras en `[compañía del picking, False]` (bien; resuelve el código de barras repetido entre compañías).
56. controllers/main.py:150 — batch por nombre `limit=1`.
57. controllers/main.py:180 — `cron_cerrar()` de operarios con sudo (todas; bien).

### C.5 koroshi_contenedores
58. controllers/main.py:35,46 — `COMPANY_ID` y `DE_LA_COMPANIA` (usados en :150, :812, :835, :926, :937): búsquedas de huecos/contenedores solo en la cía 8. En el clon: compañía del operario/elección en pantalla, o buscar en las 3 y desempatar (mismo código de barras de hueco en varias compañías, ver B.3).
59. controllers/main.py:386 — `_donde`: quants solo de la cía 8.
60. controllers/main.py:594,667,773 — fallback de compañía `COMPANY_ID` (el principal ya es la del quant/contenedor; bien).
61. controllers/main.py:698 — `_esperando`: OUT de la cía 8.
62. controllers/main.py:848 — productos `company_id in [8, False]`.
63. controllers/main.py:857 — stock por artículo de la cía 8.
64. controllers/main.py:922 — tarjeta por barcode con sudo en todas.
65. controllers/main.py:954-996 — `/mover`: no comprueba que contenedor y destino sean de la misma compañía. Con sudo se podría colgar un KO de WH-OR bajo un hueco de UBRAN (si Odoo 13 no lo impide con `check_company` en `stock.location.location_id`: verificar). Añadir comprobación.
66. controllers/main.py:1601-1675 — `/compactar/hacer`: ídem (destino leído sin comprobar compañía).
67. controllers/main.py:1052-1054 — SQL `_cajas` con `COMPANY_ID`.
68. controllers/main.py:1062-1067 — líneas abiertas de TODA la BD si hay >3000 cajas (sin compañía; inocuo pero caro).
69. controllers/main.py:1363-1364 — `_lineas_28` (ABC) con tipo de operación de la cía 8.
70. controllers/main.py:1385-1387 — `_stock_tallas` de la cía 8.
71. controllers/main.py:1400-1405 — `_columnas_compactar` huecos de la cía 8.
72. models/compactar.py:11-36 — `koroshi.compactacion.paso` sin `company_id`/almacén: el lineal (L67) es el mismo número en WH-OR, MODAI y UBRAN. Afecta a :1477 (otros pendientes), :1499 (sustituir), :1529, :1574-1580 (SQL resumen agrupado solo por lineal), :1702. Añadir `company_id` (o `warehouse_id`) y filtrar siempre.
73. models/movimiento.py:5-44 — `koroshi.contenedor.movimiento` sin `company_id`; `_marcas_con_prendas` (main.py:1027-1037) agrupa por nombre de contenedor (choque si un nombre se repite entre compañías: verificar).
74. models/compactar.py:39-50 — `koroshi.contenedor.banda` por id de ubicación (bien).
75. controllers/main.py:1009 — empleados de los parámetros con sudo (todas).

Total: 75 puntos listados; de ellos ~45 son supuestos reales de una compañía o mezcla de compañías
(1-3, 7, 11, 13-14, 16, 18-27, 31-37, 40-43, 49-52, 54, 56, 58-59, 61-63, 65-67, 69-73) y el resto ya son
correctos o inocuos en multicompañía.

Recomendación general para el clon: (a) usuario PDA con las 3 compañías y URL con `cids=1,21,23`; (b) toda escritura
toma la compañía del picking / ubicación / quant (ya se hace en muchos sitios); (c) las lecturas «de la nave» filtran
por `company_id in (compañías del almacén físico)` (parámetro) en vez de `= 8`; (d) los modelos propios por lineal
(paso de compactación, día de reparto) llevan `company_id` o `warehouse_id`.

---

## D. Mínimo para PDA «Lecturas» + preparación + Compactar

Preparación = abrir la OUT o la agrupación en la app estándar `stock_barcode` desde Lecturas (koroshi_preparacion
no entra en este alcance; operarios solo la usa si existe).

### D.1 koroshi_base → tuctuc_base (todo, es pequeño)
- Núcleo: `comun.py` (TZ y fechas; `variantes_codigo`), `pda.py`, `static/src/js/comun.js`, assets.
- Prescindible: turnos (`koroshi_base.turnos`, :78-138 + data) y CJ, si no se clonan Actividades/Preparación.

### D.2 koroshi_operarios → tuctuc_operarios
NÚCLEO PDA (imprescindible):
- `controllers/main.py`: `/leer`, `/operario`, `/siguiente`, `/saltar`, `/motivos`, `/soltar`, `/dejar`, `/estado`,
  `/minutos_tarjeta` (la usan Contenedores y Faltante vía comun.js). `/nota_hecha` solo si se clona el tablero.
- `models/tarea.py` completo (tarea, cron de cierre, inactividad; `action_validadas_sin_operario` es informe).
- `models/reparto.py`: `koroshi.operario.motivo`, `koroshi.operario.dia` (lo pide `siguiente()` vía `de_hoy()`:
  modo, `dar_sin_etiqueta`, `agrupaciones`, `solo_preparadas`), `koroshi.operario.tramo` (lo usan `dia` y el modo por
  pasillos), `koroshi.operario.asignacion` (cola, `siguiente`, `_empezar`, `saltar`, `soltar`, `leida_a_mano`,
  `ayudante_de`, `unirse`, `cron_actualizar`).
- Datos: `motivos.xml`, `motivos_v2100.xml`, `motivos_v2170.xml` (sin caja), `motivos_v221.xml` (opcional),
  `cron.xml`, `parametros.xml`; grupo `grupo_tarjeta_obligatoria`.
- Pantalla: `operarios_pantalla.js`, `sin_error_cors.js`, `operarios.xml`, `operarios.css`, acción de cliente
  (tarea_views.xml:170-174) y menú app «Lecturas (PDA)» (menu.xml:5).
- Atención: `reparto.py:679-686` llama a `_siguiente_de_tarjeta` (definido en tablero.py:156) para tipos `lote`/`nota`.
  Si no se clona tablero.py, quitar ese bloque. Y `tablero.py:323-333` sobrescribe `_dar_nueva` para dar primero
  OUT de agrupaciones vivas (útil para B-ECI_/B-VP_/WEB_, que caerían en el grupo «OUT a OUT»): decidir si se
  conserva esa parte (`_lotes_vivos`, `_lotes_por_prioridad`, `_dar_zona_libre`, `_dar_una_zona`, `_dar_de_lote`,
  `_libres_de_lote`, `_siguiente_de_tarjeta`, tipos `lote`/`nota`) sin el kanban.

TABLERO / RESPONSABLES / INFORMES (se pueden quitar del clon):
- `models/tablero_areas.py` + `tablero_areas.js/css` + acción `koroshi_tablero_areas` (tablero_views.xml:101-109).
- Kanban del tablero: `tablero.js/css`, `tablero_views.xml:8-90`, `group_expand` (tablero.py:72,185-196),
  `tablero_refrescar`, `action_abrir_tablero`, `_compute_tablero`, `write`/`_mover_en_tablero`, `action_*_tablero`,
  `_dar_pieza`; grupo `grupo_tablero` y su ACL; migraciones 13.0.2.20.0 y 13.0.2.21.1.
- Reparto del responsable: `reparto_views.xml` (Reparto de hoy, Colas, asignar desde albarán/agrupación),
  `wizard/asignar.py`, `action_repartir_ahora`, `action_dar_bloque`, `action_imprimir*`, `_imprimir_etiquetas`
  (depende de un informe y una acción creados a mano en NATH: BLOQUEANTE si se clona) y `etiquetas_report.xml`.
  Ojo: sin vistas de reparto, el `dia` se crea solo con valores por defecto (modo auto, `dar_sin_etiqueta=False` →
  la PDA diría «No tienes más pedidos» si nadie asigna). Hace falta al menos un formulario mínimo del día o cambiar el
  defecto de `dar_sin_etiqueta` en el clon.
- Productividad: vistas lista/pivot/gráfico de tareas (tarea_views.xml:3-152), `action_koroshi_validadas_sin_operario`,
  `grupo_productividad` (las ACL actuales cuelgan de él: si se quita, dar ACL de lectura a un grupo de responsables).
- Gestión de operarios: `wizard/gestion_operarios.py`, `wizard/crear_operarios.py`, `gestion_views.xml` (+ informe
  tarjeta), `categoria.xml` (el destino ya tiene 61 empleados con barcode).
- `models/informe.py` + `data/informe.xml` (vacío/sin uso).

### D.3 koroshi_pda_app → tuctuc_pda_app (opcional pero barato)
- Todo (3 rutas, `res.users` y layout). Cambiar `cids`, marca, ids de usuario. Sin parte de responsables.

### D.4 koroshi_faltantes → tuctuc_faltantes
- Necesario para Compactar: `koroshi.contenedor.movimiento.faltante_id` (dependencia de modelo) y `/cero`,
  `/cantidad`, `/cambiar_articulo`, `/anadir`, `limpiar/archivar` usan `reubicar`, `sin_alternativa`,
  `mejor_destino`, `_raiz_stock`, `antes_de_archivar`, `marcar_encontrado`. El flujo `/compactar/*` en sí no llama a
  Faltantes.
- Núcleo PDA (botón Faltante en Lecturas): controlador, `faltante.py` (reubicar/sin_alternativa/validar/pendientes/
  alternativas), JS + `Operarios.include`, FALTANTE por almacén.
- Oficina (prescindible al principio): rondas INT, puestos a 0, wizard Encontrado, vistas de revisión.
- Prescindible: `% de faltante` (`relativo.py`, `relativo_correo.py`, sus vistas, crons, parámetros y correo).

### D.5 koroshi_contenedores → tuctuc_contenedores (Compactar)
- Núcleo Compactar: rutas `/leer`, `/hueco`, `/detalle`, `/mover`, `/compactar/calcular|lineal|resumen|hacer|marcar`;
  helpers `_datos_contenedor`, `_datos_hueco`, `_datos_lineal`, `_hijos_contenedor`, `_validar_destino`, `_leidas`,
  `_empleado`, `_cajas` (cuenta de cajas a 0 en `calcular`), `_columnas_compactar`, `_lineas_28`, `_stock_tallas`,
  `_banda`; modelos `paso`, `banda`, `movimiento`; `logica.py` (plan_lineal, tallas_por_altura, partir_codigo…);
  parámetros de compactar.
- Bloqueantes de Compactar en destino: `season_id` + temporadas zona 0, formato de referencia MODELO-COLOR-TALLA,
  rango de lineales de la zona 0, sentido del muelle, paso sin compañía, prefijo UB_, código de barras de hueco
  repetido entre compañías.
- Prescindible para Compactar: ronda de cajas a 0 (`/ronda/*`, `tarjetas_*`, `group_revisar`), `/cero`, `/anadir`,
  `/cantidad`, `/cambiar_articulo`, `/limpiar`, `/archivar*`, `/producto`, `/buscar`, `/donde` (pero la pantalla JS
  de 2018 líneas las mezcla todas: recortar JS a la par).

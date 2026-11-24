# Adaptar los módulos KOROSHI a Prime Collections (odoo.tuctuc.com) — 24/11/2026

Sigue a `20261124_estudio-modulos-koroshi-en-tuctuc.md` (si tiene sentido cada módulo). Aquí: **qué hay que cambiar en
cada módulo para que haga en Prime lo mismo que hace en KOROSHI.** Solo lectura del código del repo (rama `main`); no se
ha tocado ni consultado el servidor. Rutas relativas a `odoo/modulos/`.

**Lo que quiere Prime (Isaac, 24/11):** operarios, monitor, recepciones y devoluciones. **No** reparto por zonas.

## 1. Idea general

El proceso es el mismo; lo que cambia son **los datos que el código da por hechos**. Están repetidos módulo a módulo:

| Suposición de KOROSHI | Dónde (ejemplos) | Copias |
|---|---|---|
| Compañía 8 | `koroshi_base/comun.py:14`; además `cids=8` en `koroshi_monitor/static/src/js/monitor.js:31` y `envios.js:250,539`; `company_id = 8` en `koroshi_faltantes/data/ubicacion.xml:10-11`; `browse(8)` en `koroshi_consumibles/models/consumable.py:350-370`; `company_ids in [8]` en `koroshi_menu/__init__.py:81`; `COMPANY_ID: 8` propio del motor en `koroshi_zonas/motor/modelo.py:26` | 155 usos de `COMPANY_ID` + 6 fuera de `comun` |
| Zona horaria Europe/Madrid | `comun.py:15`; vista SQL `koroshi_kpi/models/semana.py:55-56` | — |
| Matrícula de caja `CJ` + 9 cifras | `comun.py:18`, **y copia en JS** `koroshi_preparacion/static/src/js/preparacion.js:63`; `CJ665` = caja propia en `koroshi_devoluciones/models/paquete.py:23` y `koroshi_actividades/models/inversa.py:29-30` | 3+ |
| Contenedor = nombre que empieza por `KO_`/`TT_` | `koroshi_contenedores/controllers/main.py:32`, `koroshi_devoluciones/models/devolucion.py:35`, `koroshi_recuentos/controllers/main.py:24`, `koroshi_ubicaciones/nombres.py:14`, `koroshi_buscador_stock/controllers/main.py:16`, `koroshi_recepcion/controllers/main.py:235` | 6 |
| Hueco = `L94 P35 C1` o `MU-01 P00 C1`; lineal sacado del nombre | `koroshi_contenedores/controllers/main.py:48-59,131-139`, `koroshi_faltantes/models/faltante.py:65-87`, `koroshi_recuentos/logica.py:11-13`, `koroshi_operarios/models/reparto.py:34,404-422`, `koroshi_monitor/controllers/main.py:58-60,232-241`, `koroshi_ubicaciones/nombres.py:17-21` | 6+ |
| Zona de picking = ruta con `NAVE2`; padre `EFFEC/Stock/NAVE2` | `koroshi_faltantes/models/faltante.py:65,206-213`; `koroshi_ubicaciones/models/crear.py:15`; `koroshi_recepcion/models/recepcion.py:29` | 3 |
| Artículo = `MODELO-COLOR-TALLA` en el nombre | `koroshi_recuentos/logica.py:20-33`, `koroshi_recepcion/logica.py:19-29`, `koroshi_contenedores/logica.py:30-39`, `koroshi_preparacion/models/lectura.py:219-268` | 4 |
| Tipo de pedido `sale.order.s_order_type_id` = `PED. TIENDAS` / `PED. WEB` / `PED. MARKETPLACE` (campo de un módulo que no está en el repo) | monitor, kpi, zonas, menu, retener_tiendas, s4t_pedidos, preparacion | 7 módulos |
| Agrupaciones `Z-ddmm-…` (zonas), `WEB_…`, `TIENDA…`, `B-KOR` | operarios, preparacion, faltantes, monitor, kpi, informe | 6 |
| Tienda = cliente `K##`; pedidos `S-6665…` (S4T) y web `W-…` | monitor, zonas, retener_tiendas, s4t_envios, devoluciones (`CJ080…` = K80, `paquete.py:69-73`) | 5 |
| Albaranes `EFFEC/OUT/…` (se recorta el prefijo para mostrar) | operarios `tarea.py:248`, monitor, kpi | 3 |
| Usuarios y correos de NATH/KOROSHI | `almacen@`, `almacen2@`, `departamentit@nath.es` en `koroshi_menu/__init__.py` y `koroshi_faltantes/models/faltante.py:58-61`; destinatarios XPO y `@koroshi.tv` en `koroshi_monitor/data/parametros.xml`; betty@, j.luis@, isaac.andreu@ en varios `data/parametros.xml` | — |
| Ids de base de datos | cron 202 (`koroshi_zonas/models/ejecucion.py:654`), menús 857 y 1178 (`koroshi_menu/models/apps.py:45-48`), usuario 2 (`koroshi_pda_app/data/parametros.xml`) | — |

**Propuesta (un solo cambio de fondo): un «perfil de almacén» en `koroshi_base`.** Funciones en `comun`
(`comun.company_id(env)`, `comun.prefijos_contenedor(env)`, `comun.re_matricula(env)`, `comun.re_hueco(env)`,
`comun.zona_picking(env)`, `comun.tipo_pedido_tienda(env)`, `comun.partes_articulo(env, producto)`…) que leen
parámetros `koroshi_base.*` y, **si están vacíos, devuelven lo de KOROSHI**. Así NAU-2 no cambia de conducta y en
Prime se rellenan los parámetros. Los módulos se pasan uno a uno a esas funciones (regla 8 del CLAUDE.md), cada uno con
su versión. El JS recibe los valores en el JSON de carga, no escritos en el código.

- **Alternativa**: un modelo `koroshi.almacen` con un registro por almacén. Es mejor si un día una misma base tiene dos
  almacenes con PDA, pero cuesta más (vistas, permisos, migración). **Recomiendo parámetros**: cada base tiene un solo
  almacén con PDA (NAU-2 en nath, el de Prime en tuctuc). Si Prime tuviera dos, se pasaría al modelo.
- **Cuidado**: las constantes se copian al importar (`COMPANY_ID = comun.COMPANY_ID` en cada archivo). Cambiar solo
  `comun.py` no basta: hay que cambiar cada uso por la función.

## 2. Los cuatro que quiere Prime, en detalle

### 2.1 `koroshi_operarios` (cola de pedidos por operario y tablero del responsable) — esfuerzo M-L

El núcleo es genérico: tarjeta del empleado, cola, tareas y tablero solo escriben en tablas propias y en
`hr.employee`, **sin heredar ningún modelo de stock**. Lo que hay que cambiar:

| Qué | Dónde | Cambio |
|---|---|---|
| **Supone zonas**: agrupaciones `Z-`, regex `RE_ZONA`, nota `\| CAJA n`, orden por número de pedido `S-…` | `models/tarea.py:33`, `models/reparto.py:453`, `models/tablero.py:38-66` | Prefijo/regex del perfil; si están vacíos, el tablero reparte OUT sueltas y agrupaciones sin orden de zona. Saber cómo agrupa Prime (pregunta 2) |
| **Dependencia no declarada de `koroshi_zonas`**: «Imprimir etiquetas» usa `koroshi.report_etiqueta_zona` y la acción «KOROSHI Etiquetas zona» (por nombre) | `models/reparto.py:37-38,576-583` | Esconder el botón si no está el informe |
| Modo «por pasillos»: lineal `L\d+` sacado de `complete_name` con SQL `substring(...)` | `models/reparto.py:34,404,410-422` | `comun.re_hueco`; en Prime, apagado mientras no se mida (es la consulta más pesada del módulo) |
| Candidatas: todas las `stock.picking` de salida (`picking_type_code = outgoing`) en estado asignado/confirmado | `models/reparto.py:431-444`, `models/tarea.py:553-558` | **Filtrar por los tipos de albarán del almacén de Prime**: en tuctuc los albaranes del TPV también son «outgoing» |
| Recorte `EFFEC/` del nombre | `models/tarea.py:248`, `models/tablero_areas.py:95,172` | Prefijo de secuencia del tipo de albarán |
| Portada 4x6 «KOROSHI · PEDIDOS DE» y tarjeta «KOROSHI» | `views/etiquetas_report.xml:6-33`, `views/gestion_views.xml:67` | Texto del perfil (nombre del almacén) |
| Categoría «Operario KOROSHI», credencial `OP…` | `data/categoria.xml`, `wizard/crear_operarios.py:15,34` | Nombre de la categoría del perfil |
| Grupos (Tablero, productividad) y migraciones con usuarios de NATH | `security/grupo.xml`, `migrations/13.0.2.20.0`, `13.0.2.21.1` | Las migraciones no corren en una instalación nueva; dar los grupos a mano en Prime |
| Residuo: correo de informe `isaac.andreu@nath.es`, servidor `NATH` | `data/informe.xml:5-7` | Quitar |
| Abre `stock_barcode` (Lecturas) | `static/src/js/operarios_pantalla.js:456-812` | Requiere `stock_barcode` y `stock_picking_batch` en Prime y **arreglar los 18 s de `get_all_locations_by_barcode`** |

### 2.2 `koroshi_monitor` (pantalla en directo, producción, envíos y cierre de camión) — esfuerzo L

Hoy es la pantalla de **las zonas**: casi todo gira alrededor de las agrupaciones `Z-ddmm-*`. Para Prime hay que decidir
qué enseña (pregunta 3). Lo que se puede llevar casi igual: **modo Tiendas, Producción por hora y Consulta de envíos.**

| Qué | Dónde | Cambio |
|---|---|---|
| Compañía y `cids=8` en los enlaces | `controllers/main.py:37,637`, `envios.py:32,171`, `produccion.py:30`, `models/imprimir.py:36-47`; JS `monitor.js:31`, `envios.js:250,539` | Perfil; quitar `cids` del JS o enviarlo desde el servidor |
| Agrupaciones `Z-`, rondas `R2` (pantalla de zonas) | `controllers/main.py:130,647-690` | En Prime, sin zonas: ocultar esa vista o enseñar las agrupaciones que use Prime |
| Tienda `K\d+ - …`, lineal `' L(\d+) '`, `MU-`, caja leída de la nota `CAJA ` | `controllers/main.py:58-60,158-159,232-241` | Perfil |
| Tipos `PED. TIENDAS/MARKETPLACE/WEB` | `controllers/main.py:51,620,723,732`, `envios.py:36,181,477,1031`, `produccion.py:41` | Perfil (y saber si Prime tiene `s_order_type_id`) |
| Webs `W-…`, SEUR si `W-000…`, resto GLS; transportistas por `carrier_id.name ilike` | `envios.py:41,179,479-485,1029,1062-1064` | Lista de transportistas del perfil |
| Etiquetas como adjuntos `LabelXPO_%`, `gls_label_%` | `envios.py:38,490-492` | Según conectores de Prime. **Rendimiento**: `ir_attachment` por nombre y fecha, sin índice útil |
| Cierre de camión XPO: asunto «PREVISIÓN XPO AMPOSTA», fichero «Envios Koroshi AMPOSTA», «Effective Logistics, NAU-2», 15 kg y 0,09 m³ por bulto | `envios.py:786,822,829`, `controllers/xpo_calc.py:20-21` | Plantilla y parámetros; solo si Prime cierra camiones con un transportista que pida manifiesto |
| Destinatarios XPO, GLS y `@koroshi.tv` por defecto | `data/parametros.xml` | Vaciar al instalar en Prime |
| OUT por `picking_type_code = outgoing` y fechas | `controllers/main.py:619-621,719-732` | **Filtrar por tipo de albarán del almacén** (si no, entran los del TPV) |
| Menús colgados de `koroshi_warehouse_map` | `views/menu.xml` | Colgar de Inventario si no está el mapa; quitar la dependencia del manifest |
| No declara `sale_stock` ni `delivery`, que usa | `__manifest__.py` | Añadirlas |

### 2.3 `koroshi_recepcion` (contenedor marítimo caja a caja) — esfuerzo L

Es el más atado a cómo entran las IN en KOROSHI (las crea una API con un tipo y destino concretos).

| Qué | Dónde | Cambio |
|---|---|---|
| Tipo de IN: el de la compañía 8 con destino `EFFEC/RECEP_KO` (si no hay parámetro) | `models/recepcion.py:27-28,134-147` | Ya existe el parámetro `koroshi_recepcion.tipo_in_id`: darle el tipo de Prime |
| Nave `EFFEC/Stock/NAVE2` (nacen los `KO_`) y `…/RECEPCION` (palés) | `models/recepcion.py:29-30,201-217` | Perfil |
| Palés `PAL-NN A/B`, hasta 99 | `logica.py:14-60` | Perfil (o quitar las caras si Prime no las usa) |
| Una ubicación `KO_ddmmaa_NNN` por caja (usa `koroshi_ubicaciones.nombres`) | `models/recepcion.py:19,243-256` | Prefijo del perfil. **Rendimiento**: `name =like 'KO_ddmmaa_%'` en `stock.location` a cada «Recepcionar» (`:249-250`) |
| Comparador y etiqueta por `MODELO-COLOR-TALLA` | `logica.py:19-32`, `models/recepcion.py:368`, `controllers/main.py:76-77` | `comun.partes_articulo` (atributos de variante si Prime los usa) |
| Búsqueda táctil de prenda `ilike '%trozo%'` en nombre y referencia, `barcode =like '%texto'` | `controllers/main.py:269-273` | Usar `koroshi_base/pda.py` (`buscar_producto`) en vez de su copia; nada de comodín delante |
| Compañía | `models/recepcion.py:66,139,202,217,240,255,482`, `controllers/main.py:21` | Perfil |
| Etiqueta 4x6, secuencia `RC/` | `views/etiqueta_report.xml:10`, `data/datos.xml:5-9` | Papel de Prime |
| Depende de `koroshi_menu` | `__manifest__.py` | Quitarla (menú en Inventario) |
| Solo artículos sin lote ni serie | `models/recepcion.py:~400-408` | Comprobar en Prime |

### 2.4 `koroshi_devoluciones` (ubicar devoluciones y llegadas de paquetes) — esfuerzo S (Ubicar) / M (Llegadas)

| Qué | Dónde | Cambio |
|---|---|---|
| Compañía | `models/devolucion.py:31,117,153`, `controllers/main.py:28-29,118` | Perfil |
| Contenedores `KO_`/`TT_` | `models/devolucion.py:35`, `controllers/main.py:57,91` | Perfil |
| Manipulaciones de partida (Quitar precio, embolsar, reetiquetar) | `data/datos.xml:6-20` (noupdate) | Darlas de alta con las de Prime |
| Modo de stock `mover`/`apuntar`; todo entra como ajuste desde pérdidas de inventario, no desde una ubicación de devoluciones | `data/datos.xml:23-26`, `models/devolucion.py:94,161-178` | Decidir con Prime cómo debe entrar el stock devuelto (pregunta 5) |
| Origen DEV de la compañía 8 (código muerto desde v1.0.1) | `models/devolucion.py:98-110` | Quitar |
| Llegadas: matrícula `CJ`, `CJ665` = caja propia, tienda sacada de la matrícula (`CJ080` = K80 por `res.partner.barcode`), canales fijos Tiendas/Web/Zalando/Marketplace | `models/paquete.py:23-28,69-73,90-92` | Perfil, o no usar Llegadas en Prime |
| Lectura de contenedor con `=ilike` en `stock.location` (no usa índice) | `controllers/main.py:58-59` | `=` exacto en mayúsculas; el de `barcode =` (`:64`) ya va bien |

### 2.5 Lo que estos cuatro arrastran

| Necesario para | Módulo | Qué hacer |
|---|---|---|
| todos | `koroshi_base` | El perfil de almacén (apartado 1). S-M |
| operarios, devoluciones, monitor (opcional) | `koroshi_operarios` | Apartado 2.1 |
| recepción | `koroshi_ubicaciones` (crea `KO_`/`TT_` y huecos, etiquetas 4x6) | Padre `EFFEC/Stock/NAVE2` (`models/crear.py:15`), prefijos y formato de hueco (`nombres.py:14-97`), papel. **Rendimiento**: dos búsquedas `=like` en `stock.location` dentro de un `@api.depends` que salta a cada cambio del asistente (`crear.py:74-84,124-131`). Quitar la dependencia de `koroshi_menu`. S-M |
| monitor | `koroshi_warehouse_map` | **No** llevarlo (es el plano de NAU-2, 8.188 líneas de HTML): quitar la dependencia del monitor |
| recepción, monitor | `koroshi_menu` | **No** llevarlo tal cual (oculta el TPV, apartado 4): quitar las dependencias |

`koroshi_pda_app` (S) es muy recomendable con operarios: `cids` y el parámetro `koroshi_pda_app.usuarios` (hoy `2`,
otro usuario en tuctuc).

## 3. El resto de módulos: qué habría que cambiar

| Módulo | Qué hay que cambiar para Prime | Esf. |
|---|---|---|
| `koroshi_preparacion` | Compañía (`models/lectura.py:28,152`, `agrupacion.py:72,444`); `CJ` en Python y **en JS** (`preparacion.js:63`); prefijo EAN `8445962` (`lectura.py:34,746-751`); marketplaces `PED. MARKETPLACE`/ZALANDO/ABOUT YOU (`lectura.py:36-37,279-290`); zonas `Z-` y nota `CAJA` (`lectura.py:38,164,1211`, `agrupacion.py:25-26,88-90,298-313`); talla por atributo `TALLA`/`SIZE` o por nombre (`lectura.py:219-268`); ruta de NAU-2 (`models/ruta.py`, dejar `orden=ubicacion`); tarjetas piloto `OP9990001,OP9980001` (`data/parametros*.xml`); informe de etiqueta de zona (`lectura.py:845-861`). **Rendimiento**: `stock.quant.package` con `name =ilike` (`lectura.py:1023`) | L |
| `koroshi_faltantes` | Ubicación FALTANTE con almacén `EFFEC` y compañía 8 en XML (`data/ubicacion.xml:7-11`): crearla por código según el perfil; zona `NAVE2` y huecos `L P C`/`MU` (`models/faltante.py:65-87,206-213`); logins de PDA `almacen@`/`almacen2@` (`:58-61`); texto «Cantidad de producto actualizada» según idioma (`:54,941,1018`). **Rendimiento**: búsqueda de `stock.location` por `name` a cada EAN que no es ubicación (`controllers/main.py:140-141`); `stock.picking` `name =like '%/x'` (`:130`); bucle N+1 de `stock.quant` (`faltante.py:957`) | L |
| `koroshi_caja_existente` | Compañía y `CJ` (`models/stock_picking.py:28-40`); regla «mismo pedido» (`:56-62`); requiere `stock_barcode_optimization` (Brain Station). **Hereda `stock.picking.write/action_done`** (sale pronto si no es de la compañía). **Rendimiento**: `stock.quant.package name =ilike` a cada cierre de caja (`:46`) | S |
| `koroshi_consumibles` | Cajas iniciales de KOROSHI con `browse(8)` (`models/consumable.py:350-370`): quitar o sembrar las de Prime; menú colgado de `koroshi_warehouse_map`: cortar | S |
| `koroshi_prenda_suelo` | Compañía (`models/prenda.py:106-255`); sitio sin hueco «la mesa de los jefes» (parámetro); hereda las reglas de faltantes y la ruta de NAU-2 | M |
| `koroshi_contenedores` | Compañía, prefijos, lineal y hueco (`controllers/main.py:32-59,131-139`); modelo = nombre sin talla (`logica.py:30-39`); dependencia de `koroshi_faltantes` (`:199-202,429-443`). **Rendimiento**: `=ilike '%texto%'` en `stock.location` a cada pulsación desde 3 letras (`:754-756,777-779`), `ilike ' L94 '` (`:134-135`) | M |
| `koroshi_recuentos` | `MODELO-COLOR-TALLA` y tallas fijas (`logica.py:15-33`); lineales (`:11-13`); compañía (`controllers/main.py:70-390`) | M |
| `koroshi_buscador_stock` | Compañía; prefijos; lineal `L`; **no filtra compañía en `stock.location`** (`controllers/main.py:100,289,338,348`); dependencia de `koroshi_menu`. **Rendimiento (el peor)**: `_modelos_por_trozo` con tres `=ilike '%w%'` en `product.product` y `read_group` de `stock.quant` con hasta 3.000 productos (`:113-144`) | M |
| `koroshi_actividades` | Áreas fijas en código (`models/actividad.py:17-25`, igual en operarios); actividades y áreas de partida (`data/*.xml`, noupdate); Inversa con `CJ`/`CJ665` y teórico `s4t.matricula` (`models/inversa.py:29-30,253-272`): quitar si Prime no hace inversa; instalar con la compañía de Prime activa (`models/actividad.py:57`) | M |
| `koroshi_kpi` | `PED. TIENDAS`; métodos `Z-`/`B-KOR`; plano de NAU-2 para metros (`models/kpi.py:60-75`); 31 tipos de producto con gramos y litros (`data/peso_tipo.xml`); hoja de carga XPO con 49 delegaciones (`hoja_carga.py:26-65`). **Rendimiento**: `_lineas_dia` sobre `stock.move.line` con dominios encadenados (`kpi.py:333-341`), `write_date` sin índice (`:398-401`) | M |
| `koroshi_informe` | Compañía, «NAU-2» en asuntos, categoría «Operario KOROSHI», servidor `NATH`; arrastra kpi, preparacion, menu y monitor | M |
| `koroshi_menu` | Vaciar `APPS_OCULTAS` y quitar menús 857/1178 (`models/apps.py:20-48`); usuarios de NATH (`__init__.py:21-81`); 11 dependencias obligatorias por los menús | M |
| `koroshi_zonas` | No se usa en Prime | — |
| `koroshi_warehouse_map` | Rehacer el plano (solo si un día se quiere el mapa) | L |
| `koroshi_agrupaciones_web` | Origen `W-`, exclusiones, `WEB_ddmmaa_NN`, texto a Betty y «TPV de KOROSHI», servidor `NATH` (todo en `models/corte.py` y `data/parametros.xml`); instalado apagado | S-M |
| `koroshi_retener_tiendas` | `S-`, `PED. TIENDAS`, tienda `K##`, S4T (`s4t_almacen=2`), correos; arrancar con `cancelar_pocas=0` | M |
| `koroshi_s4t_*` (4) | Solo si Prime usa S4T con el mismo módulo (`api_s4t_batch_update_PROD`): prefijo `S-6665`, tipo DEV de `EFFEC`, `style_code`, avisos. Si no, no aplica | M |
| `koroshi_xpo_bultos` | Solo si Prime envía con `delivery_xpo`: compañía y 15 kg / 0,09 m³ como parámetros | S |
| `koroshi_delegacion` | Prefijo `Delegación `; **no instalar** sin crear antes la columna y el índice a mano (`CONCURRENTLY`) y sin el `UPDATE` masivo | S |
| `koroshi_rendiment` | No: el núcleo de tuctuc ya está arreglado | — |
| `koroshi_sesiones` | Genérico; solo si las PDA pierden la sesión | S |

## 4. Avisos que no dependen de adaptar

- **`koroshi_menu` oculta el menú de Punto de venta** (y CRM, Web, Fabricación…) en cada instalación y actualización
  (`models/apps.py`). En tuctuc no se instala hasta vaciar esa lista.
- **«outgoing» en tuctuc incluye el TPV.** Operarios, monitor, warehouse_map e informe buscan OUT por
  `picking_type_code = 'outgoing'`: en Prime hay que filtrar por los tipos de albarán del almacén.
- **Lecturas a 18 s** (`stock_barcode` `get_all_locations_by_barcode`): requisito previo para todo lo de la PDA.
- **Búsquedas con comodín delante** en `stock.location` (~760.000) y `product.product`: contenedores, devoluciones,
  buscador, ubicaciones y recepción (lista completa en el apartado 2 y 3). Dos salidas: índice trigrama (`pg_trgm`, a
  decidir con Isaac, se crea con `CONCURRENTLY`) o cambiar a búsqueda exacta por código o con prefijo y limitar por
  ubicación padre del almacén. Cada una se mide antes con `EXPLAIN` (sin `ANALYZE`) en solo lectura.

## 5. Plan propuesto (cada paso con su versión, etiqueta y ZIP; nada en el servidor sin el sí de Isaac)

1. **Datos de Prime** (consultas del apartado 6) y respuestas a las preguntas del apartado 7.
2. **`koroshi_base` 1.3.0: perfil de almacén** con valores vacíos = KOROSHI y tests que prueben que en NAU-2 todo
   devuelve lo de hoy. Instalar en NAU-2 fuera de horas.
3. **Pasar a `comun` los módulos de Prime**, uno a uno y en NAU-2 primero (deben seguir igual): operarios →
   ubicaciones → devoluciones → recepción → monitor (y pda_app). En cada uno, quitar las dependencias de `koroshi_menu`,
   `koroshi_warehouse_map` y la oculta de `koroshi_zonas`, y filtrar OUT por tipo de albarán.
4. **Búsquedas lentas** de esos cinco módulos, rehechas o con índice.
5. **Copia de `TUCTUC_PRODUCTION`**: instalar `base` → `operarios` → `pda_app` → `ubicaciones` → `devoluciones` →
   `recepcion` → `monitor`, con los parámetros de Prime, y probar con una PDA.
6. Instalación en tuctuc fuera del horario de tiendas, de uno en uno.
7. Después, si Prime lo pide: faltantes, preparación, caja_existente, consumibles, contenedores, recuentos, buscador.

Esfuerzo de 2 a 5 (base + los cuatro + ubicaciones + pda_app): **unas 3-4 semanas**, la mayor parte en el monitor y la
recepción y en las pruebas.

## 6. Datos de Prime que hacen falta (consultas en solo lectura)

Conexión: apartado «Servidor» de `20261124_traspaso_rendimiento_odoo-tuctuc.md`, con
`PGOPTIONS='-c default_transaction_read_only=on'`. Las que cuentan albaranes van por `stock_picking.date` (con índice)
y a 30 días.

```sql
-- 1. Compañías y almacenes (sustituyen a la compañía 8 y a EFFEC)
SELECT id, name FROM res_company ORDER BY id;
SELECT w.id, w.code, w.name, w.company_id, l.complete_name AS stock
  FROM stock_warehouse w JOIN stock_location l ON l.id = w.lot_stock_id ORDER BY w.company_id, w.id;
-- 2. Tipos de albarán en uso (OUT, IN, devoluciones, internos, TPV)
SELECT t.id, t.name, t.code, t.sequence_code, t.warehouse_id, t.company_id, count(p.id) AS albaranes_30d
  FROM stock_picking_type t
  LEFT JOIN stock_picking p ON p.picking_type_id = t.id AND p.date > now() - interval '30 days'
 WHERE t.active GROUP BY t.id ORDER BY albaranes_30d DESC LIMIT 40;
-- 3. Cómo se llaman las ubicaciones internas y prefijos de código
SELECT l.location_id, p.complete_name AS padre, count(*) AS hijas, min(l.name), max(l.name)
  FROM stock_location l JOIN stock_location p ON p.id = l.location_id
 WHERE l.active AND l.usage = 'internal'
 GROUP BY l.location_id, p.complete_name HAVING count(*) > 50 ORDER BY hijas DESC LIMIT 30;
SELECT left(barcode, 3) AS prefijo, count(*) FROM stock_location
 WHERE active AND barcode IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 30;
-- 4. Cajas: formato del nombre (en KOROSHI, CJ + 9 cifras)
SELECT left(name, 3) AS prefijo, length(name) AS largo, count(*) FROM stock_quant_package
 WHERE id > (SELECT max(id) - 50000 FROM stock_quant_package) GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15;
-- 5. Agrupaciones y cómo se nombran
SELECT left(name, 6) AS prefijo, count(*), max(create_date) FROM stock_picking_batch
 WHERE create_date > now() - interval '30 days' GROUP BY 1 ORDER BY 2 DESC LIMIT 15;
-- 6. Transportistas en uso
SELECT c.id, c.name, c.delivery_type, count(p.id) AS albaranes_30d FROM delivery_carrier c
  LEFT JOIN stock_picking p ON p.carrier_id = c.id AND p.date > now() - interval '30 days'
 GROUP BY c.id ORDER BY 4 DESC LIMIT 20;
-- 7. Empleados con tarjeta
SELECT company_id, count(*) AS empleados, count(barcode) AS con_tarjeta FROM hr_employee WHERE active GROUP BY 1;
-- 8. Módulos de los que dependen (y el del tipo de pedido)
SELECT name, state, latest_version FROM ir_module_module
 WHERE name IN ('hr','barcodes','stock_picking_batch','stock_barcode','stock_barcode_optimization','queue_job',
                'api_s4t_batch_update_PROD','delivery_xpo','product_multi_barcode','sale_stock','delivery')
    OR name LIKE 'koroshi%' OR name LIKE '%s4t%' OR name LIKE '%order_type%' ORDER BY name;
SELECT model, name FROM ir_model_fields WHERE name IN ('s_order_type_id', 'style_code');
-- 9. Formato de artículo: ¿MODELO-COLOR-TALLA en la referencia o atributos?
SELECT default_code FROM product_product WHERE active AND default_code IS NOT NULL ORDER BY id DESC LIMIT 20;
SELECT a.name, count(v.id) FROM product_attribute a JOIN product_attribute_value v ON v.attribute_id = a.id
 GROUP BY a.name ORDER BY 2 DESC LIMIT 10;
-- 10. pg_trgm
SELECT extname FROM pg_extension;
```

## 7. Qué hay que preguntar a Isaac (o a Prime)

1. ¿Qué almacén de Prime (y de qué compañía) usaría la PDA? ¿Solo uno?
2. ¿Cómo se agrupa el trabajo en Prime: OUT sueltas, agrupaciones (con qué nombre), oleadas web?
3. Monitor: ¿qué quiere ver Prime: producción por hora, tiendas, envíos, cierre de camión (con qué transportista)?
4. Recepción: ¿cómo llegan las IN a Prime (las crea una API, compras a mano…), con palés y cajas de control como en
   KOROSHI?
5. Devoluciones: ¿el stock devuelto entra como ajuste (como en KOROSHI) o desde un albarán de devolución? ¿Hay
   «llegadas» de paquetes de tienda con matrícula?
6. ¿Prime usa S4T, XPO, cajas con matrícula y el campo de tipo de pedido?
7. ¿Se acepta el «perfil de almacén» en `koroshi_base` (un `-u` en NAU-2 arrastra ~23 módulos)?
8. ¿Hay una copia de `TUCTUC_PRODUCTION` donde probar?

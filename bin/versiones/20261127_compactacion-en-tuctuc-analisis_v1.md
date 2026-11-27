# Compactación de KOROSHI en odoo.tuctuc.com: qué haría falta (análisis v1, 27/11/2026)

**Solo análisis.** No se ha cambiado código ni datos, ni se ha entrado en el servidor de tuctuc ni en el de KOROSHI.
Todo sale del repositorio (`main` en `c007aa4` y la copia de trabajo de `koroshi_contenedores`, que tiene la 1.17.0
sin commitear de otra sesión) y de los documentos de tuctuc del 24-25/11. Lo que no se puede saber desde aquí va a
las **preguntas del apartado 7**.

Pide Isaac: «Miram què necessitaríem per poder implementar-lo; es tindran que modificar coses perquè són dos mons
diferents, KOROSHI i tuctuc».

Este documento amplía, solo para la compactación, el estudio general
`bin/versiones/20261124_estudio-modulos-koroshi-en-tuctuc.md` (fila `koroshi_contenedores`: «Quizá», esfuerzo M).

## 0. Resumen en cinco líneas

1. El «módulo de compactación» es **`koroshi_contenedores`** (en NAU-2: 1.16.0 instalada; 1.17.0 «Compactar» hecha,
   sin instalar). Aparte está el **programa de Windows** `redistribucion/` (solo lee Odoo y calcula). Son dos cosas
   distintas y se pueden llevar a tuctuc por separado.
2. **No se puede instalar en tuctuc tal cual**: lleva escritos la compañía 8, los prefijos `KO_`/`TT_`, el nombre de
   los huecos de NAU-2 (`07828 - L67 P16 C1`), los lineales L44–L136, la regla «muelle antes de L01», el código de
   artículo de KOROSHI (`modelo-color-talla`), las temporadas I27/V27 y las tarjetas de Isaac, Betty y José Luis.
3. Además arrastra `koroshi_operarios` y `koroshi_faltantes` (y con ellos `stock_barcode`, `stock_picking_batch`, sus
   crons y la ubicación FALTANTE creada en la compañía 8). Para tuctuc hay que **cortar esas dos dependencias**.
4. Propuesta: **un mismo módulo con un «perfil de almacén»** (compañía, ubicación raíz, prefijos, forma del nombre del
   hueco, orden de los pasillos, forma del código de artículo, temporadas…) cuyos valores por defecto son los de
   KOROSHI, para que en NAU-2 no cambie nada. tuctuc pone su perfil. Esfuerzo: **del orden de 3-4 semanas** con
   pruebas, si las respuestas del apartado 7 no cambian el planteamiento.
5. Antes de escribir nada hace falta saber **cómo es el almacén de tuctuc** (¿hay cajas/contenedores dentro de huecos?
   ¿cómo se llaman los huecos?) y **si mover stock allí genera asientos o cambia el stock que se manda a las tiendas
   online**. Sin eso no se puede diseñar el perfil.

## 1. Qué es exactamente lo que se llevaría

`koroshi_contenedores` (pantalla de PDA «Contenedores»), por partes:

| Parte | Versión | Qué hace | ¿Sirve en tuctuc? |
|---|---|---|---|
| Mover contenedores | 1.0–1.4 | Leer una o varias KO y el hueco de destino: cambia el `location_id` de la KO (prendas y reservas van con ella) | Sí, si tuctuc guarda en cajas/contenedores que son sububicaciones de un hueco |
| Limpiar / archivar / poner a cero / añadir / cambiar / «Es otro» | 1.5–1.15 | Ajustes de inventario contra pérdidas, desde la PDA, con registro | Sí, pero ver riesgo contable (apartado 6) |
| Buscador (contenedor, hueco, lineal, artículo, «dónde está») | 1.7–1.8.2 | Búsquedas por trozo de nombre | Sí, con cuidado: tuctuc tiene ~260.000 ubicaciones internas activas |
| Retirar cajas a 0 | 1.16 | Ronda por lineal y hueco de las KO a 0; listas «Tiene prendas» y «Revisar» | Sí, si hay contenedores |
| **Compactar (fase 1)** | **1.17, sin instalar** | Plan por lineal: vaciar columnas con < 4 cajas moviendo KO enteras a columnas del mismo lineal o ±2, sin pasar de 8, sin mezclar colores, lo de más salida hacia el muelle; altura abajo/arriba por talla | Es lo más atado a NAU-2 (ver 2.3) |
| Compactar zona Z con tareas | diseño v1 del 27/11 | Solo diseño | Fuera de este análisis |

Y fuera de Odoo, `redistribucion/programa/` (Windows, PySide6): descarga en solo lectura por XML-RPC a una copia
SQLite y calcula compactación, plano y listas. Ya tiene la compañía en una constante (`COMPANIA`) y la configuración
en `config.local.toml`; está atado a `NAVE2` y a las matrices de KOROSHI de `bin/versiones`.

## 2. Qué está atado a KOROSHI

### 2.1 Dependencias de módulos (`__manifest__.py`, `depends`)

`web`, `stock`, `hr`, `barcodes`, `koroshi_base`, `koroshi_operarios`, `koroshi_faltantes`.

| Dependencia | Para qué la usa contenedores | Qué arrastra | Problema en tuctuc |
|---|---|---|---|
| `koroshi_base` | `comun.COMPANY_ID` (= 8, constante en `koroshi_base/comun.py:14`), `pda.empleado_valido` (tarjeta de un empleado activo **de la compañía 8**), `pda.buscar_producto` (busca con `company_id in [8, False]`, `pda.py:70`), `pda.comprobar_grupo` (`stock.group_stock_user`), `comun.js` (tarjeta compartida y lector «leer al parar») | `base`, `web` | La compañía 8 escrita. En tuctuc la compañía 8 será otra empresa o no existirá |
| `koroshi_operarios` | El menú cuelga de `koroshi_operarios.menu_koroshi_operarios_root` (`views/menu.xml`); la tarjeta dura `koroshi_operarios.minutos_tarjeta` | `mail`, `hr`, `stock_picking_batch`, **`stock_barcode`** (EE), cron cada 5 min, tablero, reparto de pedidos por operario | Se lleva toda la cola de pedidos de la PDA, que tuctuc no ha pedido |
| `koroshi_faltantes` | `koroshi.faltante.reubicar` y `antes_de_archivar`: al poner a cero o bajar una cantidad con reservas, la OUT se reserva en otro hueco o sale sin la prenda, y la ud va a FALTANTE (1.11–1.13, 1.16) | `stock_barcode`, `stock_picking_batch`, cron cada 15 min, **ubicación FALTANTE creada en el almacén `EFFEC` de la compañía 8 con `company_id = 8` escrito a mano** (`koroshi_faltantes/data/ubicacion.xml:10-11`) | Al instalar en tuctuc falla o crea FALTANTE en otra empresa |

Dependencias de Odoo que también hacen falta en tuctuc: `hr` (empleados con código de barras = tarjeta) y `barcodes`
**[comprobar en tuctuc]**. `stock_barcode` está (tuctuc usa el lector; el 24/11 se tocó `stock_barcode_optimization`).

### 2.2 Nombres y estructura de ubicaciones de NAU-2

| Qué | Dónde | Cómo está |
|---|---|---|
| Contenedor = sububicación de un hueco cuyo nombre empieza por `KO_` o `TT_` | `controllers/main.py:32` (`PREFIJOS`) y SQL con `upper(left(name, 3)) IN ('KO_', 'TT_')` (`main.py:1053`, `1405`) | Escrito en el código y en el SQL |
| Hueco = `07828 - L67 P16 C1` o `MU-01 P00 C1`; el lineal, la P y la C se sacan del nombre | `logica.py` `_RE_LINEAL`, `_RE_P`, `_RE_C`, `lineal_de`, `orden_hueco`; `main.py:48-49` (`LINEAL_RE`, MU-01…MU-14) | Expresiones regulares fijas |
| Lineales de un número se buscan con `name ILIKE '% L67 %'` | `main.py:1399-1404` (`_columnas_compactar`) | En tuctuc sería un recorrido de toda `stock_location` |
| Zona 0 = lineales 44–136 | `logica.py` `RANGO_LINEALES`; parámetro `koroshi_contenedores.cajas_cero_lineales` = `44-136` | Ya es parámetro (bien), pero supone lineales numerados |
| «Cerca del muelle» = lineal con número más bajo (el muelle está antes de L01) | `logica.plan_lineal` (`cerca = d['lineal']`) | Regla de NAU-2 metida en la lógica |
| Distancia = diferencia de número de lineal (±2) | `logica.plan_lineal`; parámetro `lineales_distancia` = 2 | Supone que lineales consecutivos están al lado |
| Columna = hueco de Odoo = medio palé = 8 cajas (4 de alto × 2 de fondo); C1–C4 son columnas, no alturas | parámetros `cajas_columna` = 8, `cajas_vaciar` = 4; tabla `koroshi.contenedor.banda` (abajo/arriba) | Parámetros (bien); el concepto de «columna de 4 alturas» es de las estanterías de NAU-2 |
| Solo ubicaciones de la compañía 8 (UBRAN tiene los mismos huecos con el mismo código) | `main.py:46` (`DE_LA_COMPANIA`) | Compañía escrita |
| Ajustes contra la ubicación de pérdidas del artículo (`property_stock_inventory` con `force_company`) | `main.py:274-300` (`_mover_ajuste`) | Genérico de Odoo; lo que cambia es la contabilidad (ver 6) |

### 2.3 Artículos y operativa de KOROSHI (sobre todo «Compactar» 1.17)

| Qué | Dónde | Cómo está |
|---|---|---|
| Modelo-color-talla sale del código: `2621JA67-NEGRO-M`, o del formato viejo `001-3-000003-36`; si no hay referencia, del nombre (9.116 artículos de KOROSHI no la tienen) | `logica.partir_codigo`, `logica.modelo` | Forma del código de KOROSHI. En tuctuc lo normal sería usar las **variantes con atributos** de Odoo **[comprobar]** |
| Zona 0 / zona Z por **temporada** del artículo (`product.template.season_id`, valores I27, V27) | `main.py:1419-1440`; parámetro `temporadas_zona0` | El campo `season_id` no es de Odoo estándar ni está en este repo: es de un módulo de la base de NAU-2. Si no existe, el código toma «sin temporada» = zona Z y **no compacta nada** |
| Clase A = modelos-color con el 80 % de las líneas de salida de 28 días (OUT hechas de la compañía) | `main.py:1350-1371` (`_lineas_28`), `logica.clases_abc` | Una consulta sobre `stock_move_line` de toda la compañía. En NAU-2 «unas decenas de miles de líneas»; en tuctuc (TPV + web + marketplaces) bastantes más |
| Tallas por altura (las más pedidas abajo, restos arriba) | `logica.tallas_por_altura`, `banda_caja` | Regla de KOROSHI (moda por tallas) |
| Tarjetas con permisos especiales: Isaac, Betty, José Luis (`tarjetas_revisar`), José Luis, Betty, Jordi, Darwin (`tarjetas_con_prendas`) | `data/parametros.xml` (ids de `hr.employee`, los pone IT) | Parámetros (bien); en tuctuc, otros empleados |
| Grupo «KOROSHI Contenedores: revisar» | `security/grupos.xml` | Nombre de KOROSHI; el grupo en sí sirve |
| Textos de pantalla: «KO_…», «zona 0», «zona Z», «muelle» | `static/src/js/contenedores.js` (2.018 líneas), `main.py` | Textos fijos |

### 2.4 Lo que ya es genérico (se aprovecha tal cual)

- **No añade campos a tablas de Odoo** (regla 7): solo tablas propias `koroshi.contenedor.movimiento`,
  `koroshi.compactacion.paso`, `koroshi.contenedor.banda`. No toca la estructura de `stock_picking`, `stock_move`,
  `stock_move_line` ni `stock_quant`.
- **Sin crons** propios.
- El mecanismo de mover (cambiar el padre de la ubicación-contenedor) y los ajustes son Odoo estándar.
- `logica.py` (313 líneas) no depende de Odoo y tiene pruebas sin servidor (`tests/test_logica.py`): el plan, las
  bandas y el reparto se pueden parametrizar y probar sin tocar ninguna base.
- Los parámetros de la 1.16/1.17 ya están en `ir.config_parameter` (`cajas_columna`, `cajas_vaciar`,
  `lineales_distancia`, `temporadas_zona0`, `cajas_cero_lineales`, tarjetas).

## 3. Qué habría que parametrizar o separar

### 3.1 Opciones

| Opción | Qué es | A favor | En contra |
|---|---|---|---|
| **A. Mismo módulo con perfil de almacén** (recomendada) | `koroshi_contenedores` lee todo lo de 2.2 y 2.3 de un perfil; los valores por defecto son exactamente los de hoy. En tuctuc se instala el mismo módulo con otro perfil | Un solo código; NAU-2 no nota nada si el perfil vacío = hoy; las pruebas de `logica` cubren los dos | Nombre «koroshi_» en tuctuc (se puede cambiar el nombre visible, no el técnico) |
| B. Núcleo común + adaptador por instancia | Núcleo `nath_contenedores` (modelos, lógica, pantalla) y dos módulos finos `koroshi_contenedores` / `tuctuc_contenedores` | Separación limpia | **Mover los modelos de módulo en NAU-2** (`model_koroshi_contenedor_movimiento` y sus `ir_model_data`) es una migración delicada en producción, con la PDA trabajando; más trabajo y más riesgo para el mismo resultado |
| C. Solo el programa de Windows para tuctuc | Llevar `redistribucion/programa` (solo lectura) con una configuración por instancia: da el plan en Excel, sin instalar nada | No toca ningún servidor; lo más rápido | No hay PDA ni registro: los movimientos se hacen a mano en Odoo; necesita un usuario de lectura en tuctuc (no se pueden crear usuarios nuevos) |

Recomendación: **A**, y **C** como primer paso barato si lo que se quiere en tuctuc es ver primero cuánto se gana.

### 3.2 El perfil (opción A)

Un registro propio (tabla nueva propia, p. ej. `koroshi.contenedor.perfil`, una fila por almacén) o un grupo de
parámetros `koroshi_contenedores.*`. Mejor la tabla: permite dos almacenes en una base y no mezcla claves.

| Campo del perfil | KOROSHI (por defecto) | tuctuc |
|---|---|---|
| Compañía | 8 (de `koroshi_base`, ver 3.3) | **[pregunta]** |
| Ubicación raíz del almacén (todas las búsquedas se limitan a sus hijas: `parent_path LIKE`) | `EFFEC/Stock/NAVE2` (hoy no se limita: se filtra solo por compañía) | **[pregunta]**. Imprescindible en tuctuc por el número de ubicaciones |
| Prefijos de contenedor | `KO_`, `TT_` | **[pregunta]** |
| Forma del nombre del hueco (expresión con grupos pasillo / posición / columna) | `L(\d+) P(\d+) C(\d+)`, `MU-\d+` | **[pregunta]** |
| Orden de los pasillos y distancia al muelle | número de lineal, muelle antes de L01 | Lista o regla propia **[pregunta]** |
| Pasillos de la zona a compactar | 44–136 | **[pregunta]** |
| Capacidad por hueco / umbral para vaciar / distancia máxima | 8 / 4 / ±2 | **[pregunta]** |
| Cómo saber modelo, color y talla | partir `default_code` | Atributos de la variante (Color, Talla) o expresión sobre la referencia **[pregunta]** |
| Qué artículos entran (zona) | campo `season_id` ∈ {I27, V27} | Campo y valores, o «todos» **[pregunta]** |
| Tipos de albarán que cuentan como salida (clase A) | `outgoing` de la compañía | Solo los del almacén (no TPV) **[pregunta]** |
| Días de salida | 28 | igual |
| Tallas por altura (abajo/arriba) | sí | ¿Tiene sentido allí? **[pregunta]** |

Todo con **valores por defecto = los de hoy**, y una prueba que compruebe que el plan de L67 con el perfil vacío sale
igual que con el código actual.

### 3.3 Compañía configurable en `koroshi_base`

Ya estaba en el estudio del 24/11 (paso 1): `COMPANY_ID = 8` se lee al importar. Pasarla a
`comun.company_id(env)` (parámetro `koroshi_base.company_id`, vacío = 8). Afecta a `pda.empleado_valido` y
`pda.buscar_producto`, que usa contenedores. **Un `-u koroshi_base` en NAU-2 actualiza ~23 módulos**: fuera de horas
y con el sí de Isaac. Alternativa de menos riesgo: que contenedores tome la compañía del perfil y pase la compañía a
`pda` como argumento (cambio pequeño en `koroshi_base` con 8 por defecto), sin tocar los otros 22 módulos todavía.

### 3.4 Cortar dependencias

- **`koroshi_operarios`**: el menú pasa a colgar de Inventario (o de un menú propio) y la duración de la tarjeta se
  lee si el parámetro existe (ya tiene 60 por defecto). La tarjeta compartida ya está en `koroshi_base` (`comun.js`).
  Sin operarios no entran `stock_barcode` ni `stock_picking_batch` ni su cron.
- **`koroshi_faltantes`**: pasar a opcional (`'koroshi.faltante' in env`). Sin él, «Poner a cero» y «Cambiar» con
  reservas se comportan como antes de la 1.11: **no se dejan** y dicen qué OUT las tiene. «Archivar» sigue mirando los
  movimientos sin validar. En tuctuc no se crea FALTANTE.
- En NAU-2 los dos siguen instalados: no cambia nada.

### 3.5 Rendimiento (obligatorio en tuctuc)

- Toda búsqueda de ubicación, limitada a la raíz del perfil (`parent_path`), nunca a toda la compañía.
- `name ILIKE '% L67 %'` y los buscadores por trozo: en tuctuc ya está `pg_trgm` (24/11 noche); comprobar con
  `EXPLAIN` (sin `ANALYZE`, solo lectura) que usan índice, o crear uno trigrama en `stock_location.name` con
  `CONCURRENTLY`.
- `_lineas_28`: limitar a los tipos de albarán del perfil y al almacén; medir antes en una copia.
- `read_group` de `stock.quant` (6,8 M filas en tuctuc) siempre con `location_id child_of` la raíz.

## 4. Qué se sabe de tuctuc y qué falta

**Se sabe** (documentos del 24-25/11, sin consultas nuevas):

- Odoo 13 Enterprise; servicio `tuctuc-erp`, base `TUCTUC_PRODUCTION`, código en `/opt/tuctuc-erp/odoo13/addons`,
  `nath/custom_addons` y `nath/enterprise-addons`. VM Ubuntu 16.04, Python 3.5.2, PostgreSQL 11. Se migrará de GCP a
  OVH después de nath.tuctuc.com (decisión del 26/11).
- Varias empresas (en contabilidad aparecen PRIME y UNITED); TPV en tiendas (`pos.order`); exportación de stock a
  tiendas online (Code22men, TUCTUC-Prod, Locker Gear) por `queue_job` con 5 plazas, que ya va llena.
- **~759.880 ubicaciones** (259.778 internas activas, 499.658 archivadas, se crean cada día; 185.468 de las que tienen
  código están vacías). Nadie ha dicho aún quién las crea ni para qué. `stock_quant` 6,8 M filas, `stock_move` ~20 M.
- `stock_barcode` en uso; abrir el lector tarda 18-19 s por cargar las ubicaciones (sin arreglar: lo decide Isaac).
  La pantalla de Contenedores **no** abre Lecturas, así que no le afecta, siempre que no se instale `koroshi_operarios`.
- `pg_trgm` instalado e índices de albaranes creados el 24/11.
- Ningún módulo `koroshi_*` instalado en tuctuc (el estudio del 24/11 no lo propuso).
- No se pueden crear usuarios nuevos de Odoo (se pagan).

**Falta** (todo a las preguntas): si hay un almacén físico con huecos y cajas, cómo se llaman, qué compañía y almacén,
si hay `hr` y empleados con código, cómo son las referencias y si hay temporada, y la contabilidad del stock.

## 5. Qué falta en tuctuc para instalarlo

1. Un almacén con **huecos y contenedores como sububicaciones** (si en tuctuc el stock está directamente en el hueco,
   sin cajas, «mover contenedores» y «Compactar» no tienen sentido tal como están: habría que mover artículos, que es
   otro módulo).
2. Módulos `hr` y `barcodes`; empleados con código de barras (tarjeta) **[comprobar]**.
3. Usuarios para las PDA: con usuarios existentes (no se pueden crear) y en el grupo `stock.group_stock_user`.
4. El perfil de su almacén (apartado 3.2) y las tarjetas con permisos especiales.
5. Si se quieren etiquetas de contenedor: `koroshi_ubicaciones` depende de `koroshi_menu`, que **no** se puede
   instalar en tuctuc (archiva el menú del TPV). Habría que cortarlo también, o crear los contenedores de otra forma.
6. Una **copia de `TUCTUC_PRODUCTION`** donde probar (no consta que exista).
7. `desplegar.sh` con el directorio de addons de tuctuc (`/opt/tuctuc-erp/nath/custom_addons`), no `/opt/nath-erp`.

## 6. Riesgos

| Riesgo | Por qué | Cómo se evita |
|---|---|---|
| **Romper la PDA en NAU-2** al parametrizar | Se cambia el módulo que el almacén usa todo el día, y `koroshi_base` arrastra ~23 módulos | Perfil vacío = conducta de hoy; prueba de igualdad del plan; una versión cada vez; instalar fuera de horas con el sí de Isaac |
| Se solapa con la 1.17.0 y el diseño de la zona Z | `koroshi_contenedores` está en obras (1.17 sin commitear en otra sesión; diseño Z del 27/11) | **No empezar hasta que la 1.17 esté instalada y probada en NAU-2**; regla «un módulo, una sesión» |
| **Asientos contables** en tuctuc | «Poner a cero», «Añadir», «Cambiar» y «Es otro» son ajustes contra pérdidas. Si tuctuc valora el stock en tiempo real, cada ajuste de la PDA es un asiento | Preguntar (7.6); si hay valoración, que esas acciones solo las tengan las tarjetas de «revisar», o quitarlas del perfil de tuctuc |
| **Stock que se manda a las tiendas online** | La exportación de tuctuc va por producto y «ubicación externa». Mover un contenedor de un hueco a otro cambia su padre: si el padre está en otro almacén o ubicación exportada, cambia el stock publicado | Preguntar (7.7); el perfil limita los destinos a la raíz del almacén |
| Lentitud en una base que ya va lenta (TPV con esperas) | 260.000 ubicaciones internas, 6,8 M quants, búsquedas por trozo, líneas de 28 días | Raíz obligatoria en el perfil, `EXPLAIN` antes, medir en una copia, sin crons |
| Compañía equivocada | La compañía 8 de tuctuc es otra empresa; FALTANTE se crearía en ella | Compañía del perfil; no instalar `koroshi_faltantes` en tuctuc |
| Nombres de huecos repetidos entre empresas (lo de UBRAN en NAU-2) | Si dos empresas de tuctuc comparten códigos de barras | Filtro por raíz del almacén, no solo por compañía |
| Dos instalaciones del mismo módulo | Versiones distintas en cada servidor | Un solo repo y una sola versión; el perfil es dato, no código |
| Coincide con la migración GCP → OVH | tuctuc se migra después de KOROSHI | Instalar en tuctuc después de su migración, o antes con margen |

## 7. Preguntas abiertas para Isaac

1. **¿Qué se quiere en tuctuc?** ¿La pantalla de PDA (mover, limpiar, retirar a 0, compactar) o solo saber cuánto
   se puede compactar (programa de Windows, opción C)?
2. **¿Qué almacén de tuctuc?** Nombre, compañía y ubicación raíz. ¿Hay más de uno?
3. **¿Cómo se guarda allí?** ¿Cajas o contenedores con etiqueta dentro de cada hueco (como las KO_ de KOROSHI), o el
   artículo directo en el hueco? ¿Con qué prefijo?
4. **¿Cómo se llaman los huecos?** Un ejemplo de nombre completo y código de barras de 3-4 huecos, y dónde está el
   muelle o la salida (qué pasillos están más cerca).
5. **¿Cómo son los artículos?** ¿Variantes con atributos Color/Talla o una referencia como `modelo-color-talla`?
   ¿Hay temporada en el artículo (qué campo) y qué temporadas son «la zona a compactar»?
6. **¿tuctuc valora el stock en tiempo real (asientos)?** Si sí, ¿quién puede hacer ajustes desde la PDA?
7. **¿La exportación a las tiendas online va por ubicación?** ¿Qué ubicaciones se exportan? (para no cambiar stock
   publicado al mover cajas).
8. **¿Quién usaría la PDA y con qué usuario de Odoo?** No se pueden crear usuarios: ¿hay usuarios existentes para eso?
   ¿Hay empleados (`hr`) con tarjeta?
9. **¿Se acepta tocar `koroshi_base` en NAU-2** (compañía configurable), o mejor solo pasarle la compañía desde
   contenedores (3.3)?
10. **¿Hay copia de `TUCTUC_PRODUCTION`** para probar, o hay que pedirla?
11. Con tu sí, las consultas de solo lectura del apartado 9 en tuctuc (lo resolverían 2, 4 y parte de 5 y 8).

## 8. Plan por fases (esfuerzo aproximado)

S = horas, M = 1-3 días, L = una semana o más. Cada fase con su versión, etiqueta y ZIP; nada en un servidor sin el sí
de Isaac. **Empieza después de que la 1.17.0 esté instalada y probada en NAU-2.**

| Fase | Qué | Dónde | Esfuerzo |
|---|---|---|---|
| 0 | Respuestas del apartado 7 y consultas de solo lectura en tuctuc (apartado 9) | tuctuc, solo lectura | S |
| 1 (opcional) | Opción C: el programa de Windows con configuración por instancia (raíz, compañía, nombres) y una pasada de solo lectura sobre tuctuc para ver cuánto se gana | Fuera de Odoo | M |
| 2 | Compañía configurable: contenedores la toma del perfil y la pasa a `koroshi_base.pda` (8 por defecto) | NAU-2: `koroshi_base` + `koroshi_contenedores` (dos módulos: avisar antes) | M |
| 3 | Perfil de almacén (3.2) en `koroshi_contenedores`, con valores por defecto = hoy; `logica` parametrizada; prueba de igualdad del plan; textos de pantalla sin «KO_»/«zona 0» fijos | NAU-2 (se instala igual que hoy) | L (4-6 días) |
| 4 | Cortar `koroshi_operarios` y `koroshi_faltantes` (3.4); búsquedas por raíz (3.5) | NAU-2 | M (2-3 días) |
| 5 | Perfil de tuctuc, tarjetas, permisos; `EXPLAIN` de las consultas; índice trigrama si hace falta | tuctuc (datos de configuración, con sí) | M (2-4 días, según respuestas) |
| 6 | Prueba completa en una copia de tuctuc: mover, limpiar, retirar a 0 y compactar un pasillo; medir tiempos | Copia | M (3-5 días) |
| 7 | Instalación en tuctuc fuera del horario de tiendas, un módulo cada vez (`koroshi_base` → `koroshi_contenedores`), y prueba reversible en la PDA | tuctuc | S |

Total fases 2-7: **del orden de 3-4 semanas** de trabajo, más el tiempo de esperar respuestas y la copia. Si en tuctuc
no hay contenedores dentro de los huecos (pregunta 3), las fases 3-7 cambian: haría falta compactar moviendo
artículos, no cajas, y eso es un diseño nuevo.

## 9. Consultas de solo lectura en tuctuc (cuando Isaac diga sí)

Con la conexión del traspaso del 24/11 y `PGOPTIONS='-c default_transaction_read_only=on'`:

```sql
-- Empresas y almacenes
SELECT id, name FROM res_company ORDER BY id;
SELECT id, code, name, company_id, view_location_id, lot_stock_id FROM stock_warehouse ORDER BY company_id, id;
-- Módulos que hacen falta
SELECT name, state, latest_version FROM ir_module_module
 WHERE name IN ('hr','barcodes','stock_barcode','product_season','queue_job') OR name LIKE 'koroshi%' ORDER BY name;
-- ¿Hay campo de temporada?
SELECT model, name, ttype FROM ir_model_fields WHERE model = 'product.template' AND name ILIKE '%season%';
-- Cómo son los nombres de las ubicaciones internas activas con hijas internas (posibles huecos con contenedores)
SELECT h.complete_name, count(c.id) AS hijas
  FROM stock_location h JOIN stock_location c ON c.location_id = h.id AND c.active AND c.usage = 'internal'
 WHERE h.active AND h.usage = 'internal' GROUP BY h.id, h.complete_name ORDER BY hijas DESC LIMIT 30;
-- Prefijos de los nombres de ubicaciones internas (los 30 más comunes)
SELECT left(name, 3) AS prefijo, count(*) FROM stock_location WHERE active AND usage = 'internal'
 GROUP BY 1 ORDER BY 2 DESC LIMIT 30;
-- ¿Valoración en tiempo real?
SELECT company_id, value_reference FROM ir_property WHERE name = 'property_valuation' LIMIT 20;
-- Empleados con tarjeta
SELECT company_id, count(*) FILTER (WHERE barcode IS NOT NULL), count(*) FROM hr_employee WHERE active GROUP BY 1;
```

(Si `hr_employee` no existe, la consulta da error: quiere decir que `hr` no está.)

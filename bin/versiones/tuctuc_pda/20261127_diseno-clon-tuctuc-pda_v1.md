# Clon de la PDA para la nave de Oriola - Amposta (odoo.tuctuc.com) — diseño v1

27/11/2026. Fase 0: diseño, sin código. Decisión de Isaac del 27/11/2026:
- se hace un **clon**, módulos nuevos `tuctuc_*`;
- los `koroshi_*` de NATH **no se tocan**;
- se prepara todo desde Lectura PDA, como en NATH.

Material de apoyo, en esta misma carpeta:
- `20261127_datos_odoo_tuctuc.md`: lo leído por RPC en odoo.tuctuc.com (almacenes, tipos, usuarios, paquetes).
- `20261127_inventario_preparacion.md`: preparación, consumibles, warehouse_map y caja_existente, con `archivo:línea`.
- `20261127_inventario_base_operarios_contenedores.md`: base, operarios, pda_app, faltantes y contenedores, con `archivo:línea`.

## 1. Lo que hay en el destino (comprobado el 27/11)

- **Versión**: Odoo 13.0+e, como nath. No hay que portar a otra versión de Odoo.
- **Módulos que necesitamos y están instalados**:
  - stock_barcode, stock_barcode_optimization (con su `put_in_pack(package_name=…)`), barcodes;
  - hr (61 empleados con tarjeta), stock_picking_batch, delivery;
  - sales_ext (`s_order_type_id`), style_management (`season_id`), delivery_package_number.
- **No existen**: zebra.label, product.barcode, el almacén EFFEC ni ningún koroshi_*.
- **Una nave, tres compañías y tres almacenes, todos `ship_only`** (OUT directa desde el stock):
  - PRIME COLLECTIONS (1), almacén WH-OR (id 1): OUT 2, INT 5.
  - MODA INTIMA 1964 (23), almacén MODAI (id 109): OUT 839, INT 842.
  - UNITED BRANDS 2015 (21), almacén UBRAN (id 99, stock `UBRAN/STOCK` en mayúsculas): OUT 747, INT 750.
- **Ubicaciones**:
  - Huecos con el mismo formato que NATH: `N1/06298 - L75 P38 C2`.
  - Contenedores como sububicación, con prefijo `KO_`, `TT_` o `UB_`.
  - Existe `WH-OR/Stock/N1/FALTAS_001`.
- **Cajas de OUT**: las crea Odoo con la secuencia «Packages» (`BOX` + 7 cifras) y un tipo de embalaje (`product.packaging`, p. ej. «Sobre 46x35x4(M)»). **No son etiquetas preimpresas.**
- **Usuarios del almacén**: ya tienen las compañías 1, 21 y 23 (tz Europe/Madrid).
- **Tipos de pedido (`s_order_type_id`)**: WEB, MUESTRARIO, PED. INICIAL, REPETICIÓN, RETAIL EXPRESS, B2B, PED. TIENDAS / CENTROS ECI…
- **Lotes**: B-ECI_ddmmyy_nn, B-VP_…, WEB_…, B-MIECI_… (no hay `Z-`).

## 1 bis. Flujo de Oriola (confirmado por Isaac el 27/11)

| Qué | Cómo se hace hoy | En la PDA |
|---|---|---|
| **Oleadas: WEB, WEB B&B, PED. INICIAL** | INT de la estantería al `SORTER`; desde allí el programa PedidosMultiples reparte por pedido y embala (las OUT salen de `SORTER`) | **La INT al SORTER**, sin caja (la misma rama que la web de KOROSHI a `EFFEC/SORTER`, `lectura.py:250-255`). PedidosMultiples **no se toca** |
| **Resto: REPETICIÓN, PED. TIENDAS / CENTROS ECI, B2B, RETAIL EXPRESS, MUESTRARIO, incidencia, sin pedido…** | OUT directa desde la estantería, la valida una persona | **La OUT entera**, con caja (embalaje y BOX de Odoo) |

- SORTER por almacén: `WH-OR/SORTER` y `MODAI/SORTER`; UBRAN no tiene.
- Los tipos de pedido que van por oleada son un parámetro, para poder cambiarlos sin tocar código.

Datos del 13 al 27/11 (OUT hechas):
- WEB: 4.598, de las que el sorter valida 3.833.
- PED. INICIAL: 1.706, todas las valida una persona y 1.375 salen del SORTER.
- RETAIL EXPRESS 94, REPETICIÓN 79, tiendas/ECI 66, sin pedido 65, B2B 54, otros 24.

## 2. Qué módulos se clonan

| Clon | Sale de | Qué se queda | Qué se quita |
|---|---|---|---|
| `tuctuc_base` | koroshi_base | `comun`: hora, rangos UTC, tarjeta, lector, `pda.py` | `COMPANY_ID = 8` y `RE_CJ` fijos (ahora configuración, ver 3); turnos de NAU-2 (se revisan) |
| `tuctuc_operarios` | koroshi_operarios | Pantalla Lecturas, rutas de la PDA, `tarea.py` y de `reparto.py` los modelos motivo, día, tramo y asignación; cron, parámetros, grupo de tarjeta | Tablero por áreas y kanban, vistas de reparto y colas, etiquetas de zona, productividad, informe, migraciones (el asistente «Crear operarios» se queda: ver 6.4). **Ojo**: `reparto.py:679` usa `_siguiente_de_tarjeta` del tablero: se porta esa pieza o se quita la llamada |
| `tuctuc_pda_app` | koroshi_pda_app | Entrada a la PDA y manifest web | `cids=8` (ahora las compañías configuradas) |
| `tuctuc_faltantes` | koroshi_faltantes | Faltante, validar OUT, ronda de faltantes (preparación y contenedores dependen de ello) | % de faltante y su correo; `ubicacion.xml` con EFFEC (ahora una ubicación por almacén, configurable) |
| `tuctuc_preparacion` | koroshi_preparacion | Preparar OUT e INT desde Lecturas, caja, validar | `agrupacion.py` (Z- con zebra.label y la nota CAJA nn), `ruta.py` (geometría de NAU-2), marketplace por nombre |
| `tuctuc_contenedores` | koroshi_contenedores | Leer, mover y compactar | Lo que no sea `/leer`, `/mover` y `/compactar/*`, si no se usa en Oriola (se confirma al clonarlo) |

**No se clonan**:
- `koroshi_warehouse_map`: la preparación no usa nada de él.
- `koroshi_consumibles`: la preparación solo usa sus tipos de caja, que se sustituyen por `product.packaging`, como ya hace Oriola.
- `koroshi_caja_existente`: solo sirve para etiquetas CJ preimpresas.
- `koroshi_actividades`: opcional.
- menú, kpi, monitor y zonas.

## 3. Decisiones de diseño (propuestas)

1. **Multicompañía de verdad.** La compañía sale del documento (OUT, ubicación o contenedor), nunca de la sesión.
   - Cada ruta trabaja con `allowed_company_ids` que incluye la compañía del documento.
   - Configuración en `tuctuc_base`: los almacenes que usan la PDA (WH-OR, MODAI, UBRAN) y, por almacén, la ubicación de faltantes y la zona de picking.
   - Nunca se mueve stock entre compañías: mover o compactar comprueba que origen y destino son de la misma compañía.
2. **Caja = la crea Odoo** (lo que hoy hace Oriola).
   - El modo «caja sin etiqueta» de NATH (`_pack_auto`, hoy solo para Zalando/About You) pasa a ser **el modo de todas las OUT**.
   - El operario elige el tipo de embalaje (`product.packaging`) y Odoo pone el `BOX…`. No se lee etiqueta CJ.
3. **Lotes B- y WEB_**: en la v1, las OUT se preparan **de una en una** desde Lecturas, aunque estén en un lote. Preparar un lote entero en un solo recorrido es una fase posterior, si se quiere.
4. **Reparto**: la PDA coge la siguiente OUT pendiente de las tres compañías sin que nadie asigne (`dar_sin_etiqueta` encendido por defecto). Prioridad por fecha prevista.
5. **Datos de NAU-2 fuera del código y a parámetros**:
   - prefijos EAN (`8447333`, `8435689`);
   - formato del código de producto;
   - prefijos de contenedor `KO_`, `TT_`, `UB_`;
   - corte por `/Stock/` y `/STOCK/`;
   - zona de picking;
   - correos;
   - empleados de prueba.
6. **Nombres sin choque con los de NATH**:
   - módulos `tuctuc_*`;
   - modelos `tuctuc.*`;
   - xmlids, rutas `/tuctuc_pda/...` y `odoo.define('tuctuc_...')`;
   - parámetros `tuctuc_*.…`.

   Se podrían instalar junto a los koroshi_* sin pisarse.
7. **Mismas reglas del repo** (CLAUDE.md):
   - versión e historial en cada manifest;
   - `empaquetar.py`, etiqueta y ZIP;
   - en castellano;
   - nada se instala sin el responsable.

## 4. Riesgos y lo que no se ha podido comprobar

- **Asistentes al validar.** Si el destino abre otros asistentes al validar una OUT (transportista, etc.), `_validar_out` dice «Odoo pide otra cosa al validar» (`faltante.py:552-556`). Se comprueba en la prueba.
- **Convivencia con el sorter.** El «Almacen Automatizado» seguirá haciendo sus OUT desde SORTER. Hay que separar qué OUT van por la PDA y cuáles por el sorter, para que no se pisen.
- **JS grande**: preparación 3.263 líneas, contenedores 2.018 y Lecturas ~1.500. Se renombra y se recorta; el riesgo está en lo que se quita.
- **Sin entorno de prueba de tuctuc**: las pruebas reales solo pueden ser reversibles (leer y deshacer, sin validar).

## 5. Orden de trabajo (cada paso con su versión 1.0.0 y su ZIP)

1. `tuctuc_base` (configuración multicompañía).
2. `tuctuc_operarios` + `tuctuc_pda_app` (Lecturas abre y reparte OUT de las tres compañías).
3. `tuctuc_faltantes`.
4. `tuctuc_preparacion` (preparar, caja por embalaje, validar).
5. `tuctuc_contenedores` (Compactar).
6. Prueba en una PDA de Oriola, con una OUT de cada compañía.

## 6. Preguntas abiertas para Isaac

1. ~~¿Qué OUT van por la PDA y cuáles por el sorter?~~ Resuelta el 27/11: ver 1 bis. Las oleadas van por INT al SORTER y el resto por OUT directa.
2. ¿El operario elige el tipo de embalaje en cada caja, o hay uno por defecto?
3. ¿Validar a medias (dejar pendiente lo que falta) sí o no en Oriola?
4. ~~¿Alta de operarios: se usan los 61 empleados con tarjeta que ya hay?~~ Resuelta el 27/11 (opción A de Isaac):
   **la misma tarjeta vale en los dos servidores**, porque son los mismos operarios.
   - Los 61 empleados con tarjeta de tuctuc son de tienda (RETAIL, códigos de 13 cifras): no se tocan.
   - En tuctuc se crean los operarios de NATH con **el mismo código `OP0001…`** en «ID de credencial», sin compañía
     (valen para las tres; `pda.es_empleado_valido` ya lo acepta).
   - Alta inicial: importación de la lista nombre + código OP sacada de NATH (la hace el responsable; no se escribe en
     producción sin su visto bueno).
   - Altas nuevas: se dan de alta en los dos servidores con el mismo código. Por eso `tuctuc_operarios` **sí** se lleva
     el asistente «Crear operarios» (`wizard/crear_operarios.py`), con la opción de poner el código a mano y
     comprobación de que el código no existe ya.
   - Descartado (opción B): copiar los operarios de NATH a tuctuc cada noche. Conectaría los dos servidores de
     producción con contraseñas y uno dependería del otro.

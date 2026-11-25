# Traspaso: rendimiento de odoo.tuctuc.com (24/11/2026, actualizado a las 19:40 hora de aquí)

> **Lo último está al final: «Tarde (18:40-19:40)».** El reinicio, la cola y los índices ya están hechos.

Para seguir en otra sesión de Claude. **Isaac lo hará esta tarde a partir de las 18:00 (17:00 UTC), cuando ya no
trabaja nadie en tuctuc.** Esta sesión lo ha dejado aquí: **no ha reiniciado** y no ha tocado nada más en el
servidor. Leer antes:
- `CLAUDE.md`;
- `odoo/nucleo_tuctuc/README.md`: qué está cambiado en el núcleo y cómo se instala y se vuelve atrás;
- `bin/versiones/20261124_informe_rendimiento_odoo-tuctuc_antes-despues.md`: el informe para dirección, con las cifras;
- las líneas de tuctuc en `TABLERO.md`.

## Servidor

- VM `tuctuc-erp-prod-eu-w1b` (proyecto nath-269506, zona europe-west1-b), con «SSH en el navegador» de Google
  Cloud desde Chrome.
- Servicio `tuctuc-erp` y base de datos `TUCTUC_PRODUCTION`.
- Configuración en `/opt/tuctuc-erp/tuctuc-erp.conf` y registro en `/var/log/odoo/tuctuc-erp.log`. La VM va en UTC
  (aquí es UTC+1).
- Código en `/opt/tuctuc-erp/odoo13/addons` (núcleo; copia de git con 12+ archivos ya cambiados por otros),
  `nath/custom_addons` y `nath/enterprise-addons`.
- Copias de seguridad en `/opt/tuctuc-erp/copias_modulos/<qué>_<fecha>_<hora>`.

**Reglas que ha puesto Isaac:**
- Cada subida, comando que cambie algo o reinicio necesita su sí.
- Reiniciar siempre con `sudo systemctl restart tuctuc-erp`, nunca stop + start.
- Arreglar el código, no poner módulos por encima.
- Probar en real antes de instalar, solo en lectura o con rollback.
- La contraseña de la base de datos no se escribe nunca en un comando; se lee de la configuración a una variable de
  entorno.

Para consultar en solo lectura con psql:
```
C=/opt/tuctuc-erp/tuctuc-erp.conf; v(){ grep "^$1" $C | cut -d= -f2 | tr -d ' '; }
export PGHOST=$(v db_host) PGUSER=$(v db_user) PGDATABASE=TUCTUC_PRODUCTION PGPASSWORD=$(v db_password)
PGOPTIONS='-c default_transaction_read_only=on' psql -X -c "..."
unset PGPASSWORD PGHOST PGUSER PGDATABASE
```

## Estado

| Qué | Estado |
|---|---|
| 349 (1.2.2), 347 (2.1.3), Previsto, trazabilidad, botón Stock, búsqueda con comas | Instalado y comprobado (ver el informe) |
| Búsqueda por stock (`qty_available = N`…), etiqueta `nucleo_tuctuc/busqueda-stock/2026-11-24` | Copiado al servidor a las 15:05 UTC. **Sin activar: entra con el próximo reinicio** (no se ha hecho). Copia de seguridad: `copias_modulos/nucleo_busqueda_stock_2026-11-24_150526` |
| `index=True` en `stock_package_level.picking_id`, `stock_move.created_purchase_line_id` y `dms_package_consume` 1.0.1 (`consume_package_id`); etiquetas `nucleo_tuctuc/indices/2026-11-24` y `dms_package_consume/v1.0.1` | Copiado a las 15:30 UTC (copia: `copias_modulos/indices_2026-11-24_153003/antes.tgz`), comprobado igual que el repo. Entra con el mismo reinicio. Solo sirve para que una actualización futura no borre los índices |
| Los tres índices (`stock_move_created_purchase_line_id_index` y `stock_move_consume_package_id_index`, parciales `WHERE ... IS NOT NULL`, y `stock_package_level_picking_id_index`) | Lanzados a las 15:23 UTC con `nohup psql` (proceso 2699525; registro en `~/crear_indices3.log`). **A las 15:47 UTC aún no había empezado ninguno**: el primero llevaba 24 min esperando (`virtualxid`) a que se cerrasen las transacciones de los trabajos `export_inventory` abiertos (Code22men desde las 15:10 y TUCTUC-Prod desde las 15:40). No bloquea a nadie mientras espera. El reinicio corta esas exportaciones y los índices siguen solos; **no lanzarlos otra vez** (`IF NOT EXISTS`) sin mirar antes si el psql sigue vivo. **Actualización hacia las 15:55 UTC:** el log ya dice un `CREATE INDEX` (el 1.º, `stock_move_created_purchase_line_id_index`) y el psql (proceso 8047 de la VM, `pgrep -a psql`) sigue con el 2.º. Comprobar `indisvalid` de los tres al acabar |

## Qué falta hoy (a partir de las 18:00 aquí, 17:00 UTC)

0. **Antes de reiniciar, la cola de trabajos.** Esta es la trampa:
   - El reinicio corta los trabajos de cola en marcha y los deja en estado «started» para siempre. No se
     reencolan solos: el 1723467 «Workflow Line: Validate Order [ECI-#352746]» sigue así desde el reinicio de las
     14:27 UTC.
   - La cola tiene 5 plazas (`channels = root:5`). Por cómo funciona el gestor de colas de OCA (`queue_job`, al
     arrancar carga también los «started» como en marcha), creo que cada trabajo colgado ocupa una plaza. **No está
     comprobado en este servidor.**
   - Si el reinicio corta 4 exportaciones más, serían 5 colgados y la cola entera podría pararse: pedidos,
     facturas, seguimientos y exportaciones.
   - Exportaciones de stock: Code22men, TUCTUC-Prod y Locker Gear, en bloques de 1.000 productos, cada 30 min, de
     8 a 28 min cada bloque. Antes de reiniciar, mirar `select id, name, date_started from queue_job where
     state='started'`.
   - **Plan propuesto a Isaac, sin respuesta aún:** reiniciar y, justo después, «Reencolar» en Ajustes › Técnico ›
     Trabajos en cola los que queden en «started», el 1723467 incluido, con su sí. Exportar otra vez solo vuelve a
     mandar el stock actual. El Validate Order se cortó sin guardar nada, porque su transacción se deshizo.
   - Después, comprobar que la cola se mueve: trabajos nuevos pasan a `done`.
1. **Índices**:
   - cuando `~/crear_indices3.log` diga tres veces `CREATE INDEX`, comprobar `indisvalid` en `pg_index`;
   - con `EXPLAIN`, comprobar que `consume_package_id = X`, `created_purchase_line_id IN (...)` y
     `stock_package_level.picking_id = X` usan Index Scan;
   - si alguno queda INVALID: `DROP INDEX CONCURRENTLY ...` y repetir.
2. **Reinicio** (Isaac había dicho sí a las 17:00; ahora lo hace él o la otra sesión desde las 18:00):
   - `sudo systemctl restart tuctuc-erp`;
   - comprobar que responde y que el registro está limpio;
   - en pantalla, Inventario › Productos, filtrar por Stock = 10: deben salir ~52 plantillas en ~20 s.
   - Ojo: el reinicio corta los trabajos de cola en marcha, que quedan en «started». Ya hay uno así desde el
     reinicio de las 14:27 UTC: el 1723467 «Workflow Line: Validate Order [ECI-#352746]». Mirar con Isaac qué
     hacer con él; no tocarlo sin preguntar.
3. Actualizar el apartado 3 del informe y la línea de tuctuc en `TABLERO.md`.
4. Limpiar en el servidor `~/20261124_nucleo_tuctuc_busqueda_stock.tar.gz`, `~/20261124_tuctuc_indices.tar.gz`,
   `~/tuctuc_indices.tgz`, `~/tuctuc_integration.tgz`, `/tmp/bs`, `/tmp/ix` y `~/crear_indices*.log`. Esto último,
   cuando el psql de los índices haya acabado.

## 25/11: conciliación bancaria de Shopify/Mollie (contabilidad: «solo concilia 13 de 42»)

- **Causa** (`odoo13/addons/account/models/account_reconcile_model.py:836`). «Casar con las facturas existentes»
  solo valida sola una línea si su número (WT#350966) coincide con el número, la referencia o la referencia de pago
  de la factura. Si solo coinciden la empresa y el importe, la propone y nada más.
  - Las devoluciones llevan el número en la referencia («Devolución #350031 (#350031-R1)»), así que se concilian
    solas.
  - Las facturas de venta (FW/…) solo lo llevan en el **origen** (`invoice_origin` = WT#350966). La referencia de
    pago es «RF30 1178 470».
- **Regla 330 «LIQUIDACION SHOPIFY-MOLLIE B2C»**: contabilidad la cambió a «Sugerir valores de contrapartida» con
  auto-validar. Así manda el cobro a la 43001000 **sin casar la factura**.
  - Apuntes 430 abiertos por la regla 330, a las 9:40 UTC del 25/11:
    - extracto 46154 (17/11): 2;
    - extracto 46155 (17/11): 1;
    - extracto 46265 (20/11): 19;
    - extracto 46266 (23/11): 28.
    - En total, 50 apuntes y −3.407,21 € (los cuatro saldos: −59,27 + 4,99 − 1.281,99 − 2.070,94).
  - **Pendiente de la respuesta de Isaac: volver a poner la regla en «Casar con las facturas existentes»**, él o
    contabilidad.
- **INSTALADO el 25/11 a las 13:30 UTC**, con el sí de Isaac:
  - copiado y reiniciado; copia de seguridad en `copias_modulos/conciliacion_origen_2026-11-25_132845`;
  - en ese momento no había ningún trabajo de cola en marcha;
  - **la regla 330 pasa a `invoice_matching`**: antes era `writeoff_suggestion`, con auto_reconcile,
    match_partner, misma moneda e importe 100 %, sin cambios en lo demás. Para volver atrás:
    `write({'rule_type': 'writeoff_suggestion'})`.
  - Falta la prueba de contabilidad en pantalla.
- Cambio: el origen de la factura cuenta como referencia.
  - Commit `81988d4`, etiqueta `nucleo_tuctuc/conciliacion-origen/2026-11-25`, paquete
    `bin/20261125_nucleo_tuctuc_conciliacion_origen.tar.gz`, md5 del archivo `6bd52206…`.
  - Entra con un reinicio (solo Python; el SQL se construye en el código).
  - Prueba con rollback: `bin/versiones/20261125_prueba_conciliacion_por_origen_ROLLBACK.py`, sobre el extracto
    46266.
    - Con el código de hoy: 12 de 40 solas.
    - Con el **nuevo: 38 de 40 solas, 0 con otra factura**; las 12 de hoy siguen igual.
    - Las 2 que quedan (WT#351003 y WT#351014) tienen en el banco **otra ficha de cliente** que la factura
      (clientes duplicados). Las tiene que arreglar contabilidad a mano.
- **Índice que falta: `account_move_line.payment_id`** (10,5 M filas, sin índice).
  - Deshacer una conciliación borra pagos, y la clave foránea obliga a leer toda la tabla por cada pago: la prueba
    tardó 461 s en deshacer 40 líneas.
  - Es lo mismo que le pasa a contabilidad con «Revertir conciliación».
  - Crearlo como los de ayer: `CREATE INDEX CONCURRENTLY account_move_line_payment_id_index ...` e `index=True` en
    el campo, con copia base al repo.
- **Orden propuesto para la tarde**:
  1. el índice de `payment_id`;
  2. el reinicio, que también activa la búsqueda por stock y los índices de ayer, y reencolar los trabajos;
  3. deshacer y volver a aplicar las reglas en esos 4 extractos, que con el código nuevo se casan solos: lo hace
     contabilidad o un script (primero en prueba con rollback y después con el sí de Isaac).

## Siguientes candidatos (orden que propuse a Isaac)

1. **`sale.integration.export_inventory`**, analizado a las 16:45. Código en `nath/custom_addons/integration`:
   `models/sale_integration.py` (`export_inventory`, `_collect_inventory_data`), `models/product_product.py`
   (`export_inventory_by_jobs`) e `integration_shopify/shopify_api.py:510`. Una copia de lectura se bajó a
   `C:\Users\tuctuc\Downloads\tuctuc_integration.tgz`; todavía no está en el repo.
   - **Últimas 24 h**:
     - Code22men: 24 bloques, 1.706 s de media;
     - TUCTUC-Prod: 131 bloques, 465 s de media;
     - Locker Gear: 12 bloques, 931 s de media.
     - En total, unas 31 h de cola al día. Las tres integraciones usan `free_qty`; el tamaño de bloque es
       `integration.export_inventory_block_size` = 1000.
   - **Por qué tarda**:
     - Cada vez manda TODOS los productos, aunque no hayan cambiado.
     - Calcula `free_qty` uno a uno: un `with_context(location=...)` por producto, sin precarga en lote.
     - Shopify hace 2 llamadas HTTP por producto: `fetch_one(VARIANT)` y `apply(INVENT_LEVEL)`. Code22men sale a
       1,7 s por producto, que es el límite de llamadas de Shopify.
     - Tiene la transacción abierta («idle in transaction») mientras habla con Shopify: la última consulta SQL es
       del principio.
   - **Efecto en Odoo** (medido a las 15:46 UTC):
     - No escribe ni bloquea filas (`backend_xid` vacío).
     - Tiene unas 125 tablas en AccessShare durante 30 min. Eso bloquea DDL: índices y actualizaciones de módulo.
       Un `-u` que haga ALTER sobre esas tablas esperaría y pondría en fila a todos los demás, y Odoo se quedaría
       «pensando». **Hasta arreglarlo, actualizar módulos solo sin exportaciones en marcha.**
     - También retrasa el vacuum (xmin). Hoy no se ve hinchazón grande: máximo un 7 % de filas muertas.
     - Ocupa 1-2 de las 5 plazas de la cola todo el día.
   - **Mejoras, de más a menos ganancia**:
     1. Mandar solo lo que ha cambiado: guardar la última cantidad enviada por producto y ubicación externa.
     2. Una llamada por producto en vez de dos: guardar `inventory_item_id`. Mejor aún, la llamada de Shopify por
        lotes (hasta 250 cantidades por llamada).
     3. Calcular las cantidades, cerrar la transacción y después llamar a Shopify.
     4. Calcular `free_qty` del bloque de una vez.
   - **Antes de tocarlo**:
     - confirmar si TUCTUC-Prod y Locker Gear también son Shopify;
     - ver qué cron lanza `export_inventory_by_jobs` y cada cuánto;
     - medir cuántos productos cambian de stock en 30 min.
   - Mismo método que la búsqueda por stock: copia exacta del servidor, cambio, prueba en real sin escribir y con
     rollback (comparar lo que se mandaría) e instalar con el sí de Isaac.
2. **`stock_barcode` `get_all_locations_by_barcode`**: 18 s cada vez. Hay 759.880 ubicaciones (730.337 con código
   de barras). Antes, preguntar a Isaac por qué hay tantas.
3. Conciliación bancaria `get_bank_statement_data` (hasta 128 s, 3.129 consultas); `stock.location.move`
   `action_validate` (117 s); búsquedas de `sale_order` que recorren la tabla entera.
4. Aplazado por Isaac: evitar el reintento por SERIALIZATION_FAILURE del 349.

## Lecciones de hoy

- Odoo 13 borra al actualizar un módulo el índice `<tabla>_<campo>_index` si el campo no tiene `index=True`.
  Por eso:
  - el índice se crea a mano, con `CONCURRENTLY` y ese mismo nombre;
  - en el código se pone `index=True`;
  - Odoo, al ver que existe, no lo vuelve a crear.
- `CREATE INDEX CONCURRENTLY` espera a todas las transacciones abiertas antes de empezar. Los `export_inventory`
  lo frenan.
- `git archive` en Windows sale con CRLF: usar `git -c core.autocrlf=false archive`.
- `bin/comprobar.py` para `dms_package_consume` por un campo que ya existía
  (`stock.move.line.package_material_transfer_created`). No se ha añadido a la lista de aprobados sin preguntar;
  se ha empaquetado con etiqueta y `git archive`.
- Hasta el 24/11, la historia de git de este ordenador y la de GitHub eran distintas (reescrita el 14/11 en la fase
  6). La `main` vieja de GitHub está en la rama `historial-github-13-11`.

## Tarde (18:40-19:40 hora de aquí, 17:40-18:40 UTC)

Trabajado desde el panel del navegador de la app (SSH web de Google y odoo.tuctuc.com con la sesión de Isaac). La
terminal SSH web solo acepta teclas una a una: Ctrl+C no llega y «Descargar archivo» no deja el archivo en el PC.

### Hecho

1. **Índices**: los tres creados (25:00, 7:52 y 7:43) y `indisvalid = t`. Falta el `EXPLAIN` (no urgente).
2. **Reinicio** 17:48:57 UTC con protección (no reiniciaba si había trabajos que no fueran exportaciones). `active`.
   En el log sale `Some modules are not loaded ... ['query_deluxe']`: **sin comprobar si ya salía antes**.
3. **Cola**: el reinicio la dejó **parada**. Último trabajo hecho 17:48:08; a las 18:00, 38 pendientes y 5 en
   «started» (4 exportaciones cortadas + 1723467) = las 5 plazas de `root:5`. Reencolados los 4 (Acción › Requeue
   Jobs) y la cola arrancó al momento. Después, con el sí de Isaac, el **1723467**: «sale.order(914454,)
   [ECI-#352746] confirmed successfully» a las 19:02:47 hora de aquí. **Queda comprobado: cada «started» colgado ocupa
   una plaza. Después de cada reinicio, reencolar enseguida.**
4. **Búsqueda «Stock = 10»** medida en el log (werkzeug): 46 s sola por RPC y 57 s desde la pantalla (~3.400
   consultas, 35-42 s de Python). Antes 10-19 min, pero no los 20-28 s de la prueba. Carga del servidor baja (14
   núcleos, carga 1,3). Sospecha sin comprobar: los 1.510 kits de `_buscar_stock_por_quants` (stock/models/product.py:394).

### Exportación de stock (`export_inventory`): analizada, sin tocar

- Las 3 integraciones son Shopify. Crons: 262 TUCTUC-Prod cada **2 h**, 252 Code22men cada **3 h**, 212 Locker Gear
  cada **4 h** (no cada 30 min como decía arriba).
- Código leído en el servidor (`~/tuctuc_integration.tgz`, desempaquetado en `/tmp/intl`): `product_product.py:236`
  (bloques de 1.000, todos los productos), `sale_integration.py:2184` (`free_qty` por producto) y
  `shopify_api.py:510` (`fetch_one(VARIANT)` + `apply(INVENT_LEVEL)` por producto).
- **Medido con rollback** (`/tmp/intl/medir.py`, `odoo shell`): 1.000 productos de TUCTUC-Prod, **una sola** llamada
  a `_compute_quantities_dict`, 5,3 s. **El cálculo ya va por bloques**; el ~99 % del tiempo es Shopify.
- Productos con `stock_quant.write_date` reciente: 2 h = 320, 24 h = 5.588. TUCTUC-Prod manda ~11.000 cada pasada.
- Propuesta (sin hacer, Isaac lo ve como mejora de fondo, no urgente): mandar solo lo que cambia (tabla propia con
  lo último enviado, apuntar solo si Shopify responde OK, pasada completa cada noche e interruptor; riesgo 4/10) y
  una llamada por producto en vez de dos.

### Abrir un artículo: 2-10 s

- Casi todo SQL. Muestreo en directo: `stock_quant` con `location_id in (...)` enorme, `stock_location` 0,5 s y dos
  agregados de `stock_move` 0,5 s.
- **259.778 ubicaciones internas activas** (+499.658 archivadas; se crean cada día, la última hoy). Cada cálculo de
  cantidades las mete todas en el IN. Antes de tocar nada: saber quién crea tantas ubicaciones y para qué.
- `stock_quant`: 6,8 M de filas (844 MB). Sin `pg_stat_statements`; `log_min_duration_statement = -1`.

### Ranking del log de hoy (peticiones > 3 s, desde las 06:25 UTC)

| Qué | Veces | Total | Peor |
|---|---|---|---|
| Botones (`call_button`) | 239 | 7,1 h | 2 h 47 min |
| TPV `pos.order/create_from_ui` | 130 | 30 min | 55 s |
| Abrir cliente `res.partner/read` | 160 | 37 min | 2 min 40 s |
| 349 `unlink` | 2 | 3,2 h | 1 h 37 min |
| Apuntes `account.move.line/web_read_group` | 100 | 22 min | 70 s |
| Conciliación (líneas de extracto) | 43 | 15 min | 2 min 5 s |
| Compras `get_model_lines` | 12 | 32 min | 8 min |
| Acciones de servidor `/web/action/run` | 46 | 73 min | 34 min |

- **Botones**: 6,8 de las 7,1 h son cuatro «Calcular» del 349 (tres con el código viejo, acaban a las 11:52 UTC; uno
  con la 1.2.2 a las 13:12 UTC, 644 s). Ya arreglado. El resto (30-80 s) son de `expediciones@`, que borra
  `stock.move.line` y `stock.move` **uno a uno, 0,8-1 s cada uno** (albarán 2051436 a las 11:09 UTC). No es un índice
  que falte (todas las FK grandes a `stock_move` lo tienen): es Python. Falta saber qué botón es.
- `style_management/models/product_template.py:170` escribe un marcador de depuración en `name_get`: 21.604 líneas
  hoy en el log. Solo ruido.
- **TPV** (lo más urgente para ventas): 130 de 133 tiquets > 2 s, 66 > 10 s, 12 > 30 s. Casi todo es espera en la base
  de datos (p. ej. 14:45 UTC: 130 consultas y 28 s de SQL). Parece bloqueo, **sin comprobar**.
- **Abrir cliente**: 171 de 308 > 2 s, 62 > 10 s, 17 > 30 s.

### Siguiente

1. **Mañana en horas de tienda**: lanzar el vigilante (`/tmp/intl/vigila.sh`: cada segundo, consultas activas de más
   de 2 s con `wait_event` y `pg_blocking_pids`) unas horas y mirar qué bloquea al TPV y a abrir clientes. Esta tarde
   se lanzó 30 min, pero casi sin actividad.
2. Quién crea las ubicaciones internas (abrir artículos, lector de códigos de barras).
3. Exportación de stock: solo lo que cambia (cuando haya tiempo).
4. Limpiar en el servidor `/tmp/intl` (código copiado, `medir.py`, `vigila.sh`, `espera.txt`) y lo del apartado
   «Qué falta hoy», punto 4.

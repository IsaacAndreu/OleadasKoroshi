# Traspaso: rendimiento de odoo.tuctuc.com (24/11/2026, actualizado a las 16:50 hora de aquí)

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
- **Cambio preparado, sin instalar**: el origen de la factura cuenta como referencia.
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

# Traspaso: rendimiento de odoo.tuctuc.com (24/11/2026, 16:40 hora de aquí)

Para seguir en otra sesión de Claude. Leer antes:
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
| Búsqueda por stock (`qty_available = N`…), etiqueta `nucleo_tuctuc/busqueda-stock/2026-11-24` | Copiado al servidor a las 15:05 UTC. **Entra con el reinicio de las 17:00 (16:00 UTC)**. Copia de seguridad: `copias_modulos/nucleo_busqueda_stock_2026-11-24_150526` |
| `index=True` en `stock_package_level.picking_id`, `stock_move.created_purchase_line_id` y `dms_package_consume` 1.0.1 (`consume_package_id`); etiquetas `nucleo_tuctuc/indices/2026-11-24` y `dms_package_consume/v1.0.1` | Copiado a las 15:30 UTC (copia: `copias_modulos/indices_2026-11-24_153003/antes.tgz`). Entra con el mismo reinicio. Solo sirve para que una actualización futura no borre los índices |
| Los tres índices (`stock_move_created_purchase_line_id_index` y `stock_move_consume_package_id_index`, parciales `WHERE ... IS NOT NULL`, y `stock_package_level_picking_id_index`) | Lanzados a las 15:23 UTC con `nohup psql` y `CREATE INDEX CONCURRENTLY`; registro en `~/crear_indices3.log`. **A las 15:36 UTC seguían esperando** (`virtualxid`) a que acabasen dos trabajos de cola `export_inventory` de Code22men abiertos desde las 15:10 UTC |

## Qué falta hoy

1. **Índices**:
   - cuando `~/crear_indices3.log` diga tres veces `CREATE INDEX`, comprobar `indisvalid` en `pg_index`;
   - con `EXPLAIN`, comprobar que `consume_package_id = X`, `created_purchase_line_id IN (...)` y
     `stock_package_level.picking_id = X` usan Index Scan;
   - si alguno queda INVALID: `DROP INDEX CONCURRENTLY ...` y repetir.
2. **Reinicio a las 17:00 aquí** (Isaac ya dijo sí):
   - `sudo systemctl restart tuctuc-erp`;
   - comprobar que responde y que el registro está limpio;
   - en pantalla, Inventario › Productos, filtrar por Stock = 10: deben salir ~52 plantillas en ~20 s.
   - Ojo: el reinicio corta los trabajos de cola en marcha, que quedan en «started». Ya hay uno así desde el
     reinicio de las 14:27 UTC: el 1723467 «Workflow Line: Validate Order [ECI-#352746]». Mirar con Isaac qué
     hacer con él; no tocarlo sin preguntar.
3. Actualizar el apartado 3 del informe y la línea de tuctuc en `TABLERO.md`.
4. Limpiar en el servidor `~/20261124_nucleo_tuctuc_busqueda_stock.tar.gz`, `~/20261124_tuctuc_indices.tar.gz`,
   `~/tuctuc_indices.tgz`, `/tmp/bs`, `/tmp/ix` y `~/crear_indices*.log`.

## Siguientes candidatos (orden que propuse a Isaac)

1. **`sale.integration.export_inventory`** (Code22men, «Export Product Quantities to External»):
   - 86 ejecuciones; 732 s de media y 2.253 s como máximo;
   - mantiene la transacción abierta todo ese rato (hoy ha frenado los índices);
   - probablemente calcula el stock producto a producto: mirar si se puede usar la suma de quants como en
     `_buscar_stock_por_quants`.
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

# Informe: qué hace hoy el cron 186 y qué cubre del tracking (12/11/2026)

Fuente: código del módulo `api_s4t_batch_update_PROD` v13.0.5.0.0 (EFFECTIVE LOGISTICS, SL), en
`/opt/nath-erp/nath/custom_addons/api_s4t_batch_update_PROD`, sacado con
`bin/ver_modulo_s4t_sync_2026-11-12_SOLO-LECTURA.sh`.

## Qué hace hoy

1. El cron 186 lanza la acción 1800 (v3). Busca pedidos `S-6665…` que no están en `READY` y tienen todas las OUT hechas.
2. La acción llama a `s4t.order.sync.action_sync_order(order)`, que hace **`PUT /orders/batch-update`** con:
   - `order_number` = `sale.order.s4t_order_number`
   - `lines[]`: `sku`, `quantity_served`, `box_code`
3. La caja (`box_code`) solo se envía en B2B con tipo de pedido 38 o 39. Sale del `result_package_id` (matrícula CJ) de las líneas hechas. En el resto de los pedidos se envía `qty_delivered` con `box_code` vacío.
4. Si S4T responde `success`, el pedido queda `x_s4t_status = order_status` (normalmente `READY`). Si no, queda `ERROR` con el detalle en `x_s4t_last_log`.
5. Antes del PUT y después de un timeout, el módulo comprueba si el pedido ya está en READY (`GET /orders/{id}/lines` devuelve 403). Así no reenvía.
6. Los pedidos web (`W-…`) los envía otro cron del módulo (`cron_send_s4t_orders_result`), con la misma función.

## Qué cubre del tracking: nada

- En el módulo no aparecen ni `/shipments` ni `/transfers`.
- No se envía el transportista, ni el tracking (`carrier_tracking_ref`), ni los bultos, ni el peso, ni el volumen.
- La v2 de la acción 1800 solo usaba el transportista y la etiqueta para decidir si enviaba el pedido. No los mandaba.
- Por lo tanto `POST /shipments` es todo nuevo. El orden sería: el pedido pasa a `READY` (batch-update de hoy) y después a `SHIPPED` (shipments).

## Qué se puede aprovechar

- `s4t.config`: el host y la clave `X-Api-Key` ya están configurados. **La clave ya existe**: es una clave `cust_live_…` que va de valor por defecto en el código fuente del módulo. Parece la misma API (`/api/service`), así que probablemente sirve para shipments y transfers. Hay que confirmarlo con S4T.
- `S4TApiService` (`services/s4t_api.py`): sirve como patrón para los reintentos y los timeouts.
- `s4t.order.feed`: hace justo lo de «guardar el dato crudo antes de procesarlo». Es el modelo a copiar para `return-ecommerce` y `corrections`.
- `queue_job` y su canal (`root.s4t_sync`): un job por pedido o traspaso, para que un error no bloquee el resto.

## Recomendaciones

1. **No tocar el módulo de Effective.** Hacer un módulo propio (`koroshi_s4t_envios`) que dependa de él y reutilice `s4t.config`.
2. **No añadir campos a `stock.picking`** (caso `no_overscan`, 03/11). Guardar los envíos en un modelo propio (`koroshi.s4t.envio`): pedido, OUT, transportista, tracking, bultos, peso, volumen, `is_final`, estado, respuesta y error.
3. **Seguridad de la clave**: está en el código fuente y en la base de datos. Por un fallo del filtro del script, también sale en `s4t_sync_codigo.txt` (Descargas): borrarlo o no compartirlo. Pedir a S4T HTTPS y valorar rotar la clave.
4. **Transportista**: S4T solo acepta `GLS` y `XPO`. Hay que mapear `carrier_id` a uno de los dos y no enviar los pedidos sin transportista válido. Desde la v3 hay pedidos READY sin transportista: el envío tendrá que llegar más tarde, cuando tengan etiqueta.

## Preguntas para S4T que siguen abiertas

- ¿Hay entorno de pruebas para `POST /shipments`? ¿Se puede deshacer `SHIPPED`?
- ¿La clave `cust_live_…` actual vale para shipments y transfers?
- ¿El `order_number` de shipments es el mismo `s4t_order_number` del batch-update? (Casi seguro que sí.)
- ¿Aceptan `POST /shipments` en un pedido que aún no está en READY?

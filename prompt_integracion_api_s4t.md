# Prompt: integrar las APIs B2B de soft4tex (S4T) con Odoo

> Todo en castellano (módulos, textos, docs y mensajes). Versiones nuevas con nombre y fecha, sin sobrescribir las anteriores. Mirar `installed_version` en el servidor antes de sacar versión.

## Contexto

S4T (soft4tex) nos ha avisado de que ya están integradas tres APIs B2B: consulta de traspasos de devoluciones e-commerce, consulta de correcciones de traspasos, e ingesta de cajas enviadas por órdenes de servicio (tracking de transportista). Llevamos días necesitando esto. Los manuales son:

- `C:\Users\tuctuc\Downloads\API_TRANSFERS (1).pdf`
- `C:\Users\tuctuc\Downloads\API_SHIPMENTS.pdf`

(Para leerlos: `python -I -X utf8` con `pypdf`; el Read de PDF por páginas falla porque no hay poppler.)

Ya tenemos un cron 186 de sync S4T que envía todos los pedidos con OUT hechas, con o sin transportista (v3, 12/11). Hay que revisar qué hace exactamente y qué parte del tracking queda cubierta antes de añadir nada.

## Especificación resumida

- Base URL: `http://82.223.131.45:3232/api/service` (HTTP sin TLS).
- Autenticación: cabecera `X-Api-Key: <clave>`. La clave la tiene que facilitar S4T; nunca meterla en el repo ni en logs. Va en un parámetro del sistema de Odoo (`ir.config_parameter`) o en el fichero de configuración del servidor.
- Formato JSON.

### API de traspasos (solo GET)

- `GET /transfers/return-ecommerce`: devoluciones de la tienda online.
- `GET /transfers/corrections`: correcciones de traspasos.
- Parámetros opcionales: `viewed` (true/false), `transfer_date` (YYYY-MM-DD), `limit` (1-500, por defecto 100), `skip` (>= 0).
- Respuesta: `total_count`, `skip`, `limit`, `transfers[]`, del más reciente al más antiguo.
- Cada traspaso: `transfer_id` (identificador único), `origin_id`, `destination_id`, `warehouse_id`, `transfer_date`, `operator_id`, `status`, `transfer_type` (p. ej. `DevoEcom`, `TRA`), `customer_viewed_at`, `total_quantity`, `lines[]`.
- Cada línea: `line_number`, `article_id`, `color_id`, `size`, `quantity` (en correcciones puede ser negativa), `boxes`.
- `boxes` es el mismo valor en todas las tallas de la misma línea: NO sumarlo.
- Campos de texto pueden venir `null`. Las cantidades vienen con decimal (`2.0`).
- Cada traspaso se marca como descargado la primera vez que se devuelve. Con `viewed=false` hay que dejar SIEMPRE `skip=0` y repetir hasta que `transfers` llegue vacío; si se avanza `skip` se saltan traspasos.
- Para re-descargar: `transfer_date` o `viewed=true`, y descartar por `transfer_id` los que ya tengamos.
- Errores: 401 clave inválida; 422 falta la cabecera o parámetro inválido.

### API de envíos (POST y GET)

- `POST /shipments` registra un envío de una orden. Cuerpo: `order_number` (1-100, obligatorio), `carrier` (`GLS` o `XPO`, obligatorio), `tracking_number` (1-50, obligatorio), `packages` (entero > 0), `weight_kg` (> 0), `volume_m3` (> 0), `is_final` (opcional, por defecto `true`).
- `is_final=true` (por defecto): es el último envío y la orden pasa a `SHIPPED`. Con varios envíos, todos `false` menos el último.
- Reenviar el mismo `order_number` + `tracking_number` actualiza el envío (`created: false`), no duplica; se puede reintentar sin riesgo.
- La respuesta incluye TODOS los envíos de la orden: `order_status`, `total_shipments`, `total_packages`, `total_weight_kg`, `total_volume_m3`, `shipments[]` (`carrier`, `tracking_number`, `packages`, `weight_kg`, `volume_m3`, `created`, `created_at`).
- `GET /shipments?order_number=...` consulta los envíos de una orden (mismo formato, `created: false`).
- Errores: 401 clave; 403 la orden no es de nuestros almacenes; 404 orden inexistente; 409 orden cancelada o el mismo envío llegó dos veces a la vez (reintentar); 422 campo inválido.

## Qué se quiere conseguir

### A. Enviar el tracking de XPO/GLS a S4T desde Odoo

1. Revisar el cron 186 y el flujo actual de pedidos S4T (canal `root.s4t_sync`) para ver cómo y cuándo se informa hoy del envío.
2. Diseñar el envío a `POST /shipments` cuando una OUT queda preparada/validada: transportista, tracking, bultos, peso y volumen.
3. Decidir de dónde salen los datos: bultos (cajas CJ de Lecturas), volumen (caja plena = 0,084 m3 si hay que estimar), peso (por artículo o estimado), transportista y tracking.
4. Soportar órdenes con varios envíos (`is_final=false` en todos menos el último). Pensar qué pasa si una orden se parte en varias OUT.
5. Idempotencia y reintentos (409 y fallos de red). Registrar en Odoo el resultado (`order_status`, `created_at`) y los errores por orden.
6. Manejar 403/404/409/422 sin bloquear el resto de la cola.

### B. Devoluciones y correcciones (lectura desde S4T)

La API de traspasos es SOLO LECTURA: nos da lo que S4T ya tiene registrado. No permite crear devoluciones ni correcciones en S4T desde Odoo.

1. Cron que lea `return-ecommerce` con `viewed=false` y `skip=0`, guarde el traspaso en Odoo ANTES de procesarlo (el GET ya lo marca como descargado y no vuelve a salir) y lo convierta en recepción/devolución.
2. Lo mismo para `corrections`, con cantidades negativas posibles, y ver cómo se reflejan en stock.
3. Idempotencia por `transfer_id`.
4. Pregunta abierta: si la intención es iniciar devoluciones desde Odoo hacia S4T, no hay endpoint para ello. Hay que preguntar a S4T si existe o si se avisa por otro canal.

## Riesgos y precauciones

- HTTP sin TLS y clave en cabecera: pedir a S4T HTTPS o IP fija con lista blanca.
- El último `POST` de una orden la pasa a `SHIPPED` en S4T y no sabemos si se puede deshacer. No probar con órdenes reales sin acuerdo previo: preguntar a S4T si hay entorno de pruebas o una orden de prueba. Seguir el criterio de pruebas reales reversibles.
- Antes de tocar módulos de Odoo, recordar que un campo de módulo en una tabla compartida puede romper otras operaciones (caso `no_overscan`, 03/11). Probar primero en un entorno seguro.
- Los cambios en el cron deben ser versionados y reversibles. Cambiar el MODO con cuidado en pruebas.

## Preguntas para S4T

1. ¿Hay entorno de pruebas para `POST /shipments`? ¿Se puede deshacer o corregir una orden ya en `SHIPPED`?
2. ¿Pueden dar la clave `X-Api-Key` y confirmar HTTPS o una IP fija?
3. ¿Hay endpoint para iniciar devoluciones o correcciones hacia S4T, o solo lectura?
4. ¿`order_number` es el mismo que ya enviamos en el sync de pedidos?
5. ¿Qué significan los valores de `status` y `transfer_type`?

## Entregables esperados

1. Informe breve de cómo funciona hoy el cron 186 y qué cubre del tracking.
2. Propuesta de diseño para A (envíos) y B (devoluciones/correcciones), con orden de prioridad.
3. Implementación por fases, empezando por lo que no tenga riesgo en producción (por ejemplo, lectura de `return-ecommerce` y consulta `GET /shipments`).
4. Documentación en castellano y versiones nuevas sin sobrescribir.

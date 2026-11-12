# API B2B de S4T: endpoints (12/11/2026)

Fuente: `http://82.223.131.45:3232/openapi.json`, «S4T Koroshi SMS - B2B Service API» v1.0.0. La página `/docs` pide
usuario y contraseña (HTTP Basic). Las llamadas van con `X-Api-Key`.
Base URL: `http://82.223.131.45:3232/api/service`. 33 endpoints.

Uso en Odoo:
- **USADO**: ya lo llama `api_s4t_batch_update_PROD` (Effective).
- **NUESTRO**: lo llama `koroshi_s4t_envios`.
- **NO**: no lo usa nadie.

| Endpoint | Qué hace | Uso en Odoo |
|---|---|---|
| GET /me | Datos del cliente y almacenes asignados | NO |
| GET /orders/b2b, /orders/b2c | Pedidos nuevos | USADO (crea S-/W-) |
| GET /orders/{id}/lines | Líneas de un pedido | USADO |
| PUT /orders/batch-update | Unidades servidas y caja (pasa a READY) | USADO (cron 186) |
| PUT /orders/update | Obsoleto | NO |
| POST /stock/register | Movimientos de stock | USADO |
| POST /box-number/register | Registra matrícula de caja recibida | USADO |
| POST /matriculas/verify | Contenido de caja frente al teórico | USADO |
| POST /box/validate | Contenido físico de caja frente al teórico: OK / FALTA / EXCEDE | NO |
| GET /packing-pro, /packing-pro/{company}/{id}/lines | Packings de entrada | USADO |
| POST /packing-reception | Recepción de packing | USADO |
| **GET /transfers/return-ecommerce** | Devoluciones web (`DevoEcom`) con destino 00006665. Sincronizadas desde el ERP cada 15 min, desde el 01/07/2026 | **NO** |
| **GET /transfers/corrections** | Correcciones de traspasos de **reposición diaria** de 00006665 a tiendas (+/−), desde el 01/07/2026 | **NO** |
| GET /clients | Clientes (tiendas) con búsqueda | NO |
| POST /shipments, GET /shipments | Envíos: transportista, tracking, bultos, peso y volumen | NUESTRO (desactivado) |
| GET /health | Estado | NO |
| GET /stock/almacenes | Almacenes con stock semanal | NO |
| GET /stock/weekly/{year} (+ /csv) | Stock semanal por almacén y artículo | NO |
| POST /stock/snapshot, GET /stock/snapshots | Stock que informamos frente al suyo | USADO (snapshots) |
| POST /stock/regularization, GET /stock/regularizations | Regularización de stock (suma/resta) | USADO |
| GET /products/seasons, /products/by-season/{t} (+ /csv) | Catálogo por temporada | NO |
| GET /logs/... | Visor y consulta de logs de la API | NO |

## Notas

- **Traspasos**: cada uno se marca como descargado la primera vez que se devuelve. La primera descarga con
  `viewed=false` traerá todo lo pendiente desde el 01/07/2026: guardarlo antes de procesarlo.
- **Logs** (`/logs/...`): sirven para ver qué ha recibido S4T de cada llamada nuestra (por ejemplo, los errores
  «KO: None» del batch-update).
- **Stock semanal**: sirve para cuadrar nuestro stock con el de S4T por semana, almacén y artículo.

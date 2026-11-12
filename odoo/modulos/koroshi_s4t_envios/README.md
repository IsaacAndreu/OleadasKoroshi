# KOROSHI Envíos a S4T (v1.1, 12/11/2026)

Envía a S4T (`POST /shipments`) el transportista, el tracking, los bultos, el peso y el volumen de cada pedido
S-6665. Con el último envío del pedido (`is_final=true`), S4T pasa la orden a `SHIPPED`.

## Se instala DESACTIVADO

- El cron **«KOROSHI - Envios a S4T (POST /shipments)»** queda archivado (inactivo).
- El parámetro del sistema `koroshi_s4t_envios.modo` vale **`diagnostico`**: el módulo calcula y guarda los envíos,
  pero **nunca llama a S4T**. El botón «Enviar ahora» da error en este modo.
- El botón «Consultar en S4T» (`GET /shipments`) solo lee y funciona en cualquier modo.

## Qué envía

Pedidos `S-6665…` con fecha desde `koroshi_s4t_envios.desde` (por defecto el 01/11/2026) que cumplen:
- están READY en S4T (el cron 186 ya ha hecho el batch-update);
- tienen todas las OUT hechas;
- todas las OUT tienen etiqueta.

Hace un envío por cada tracking distinto del pedido:

| Campo S4T | De dónde sale |
|---|---|
| `order_number` | `sale.order.s4t_order_number` |
| `carrier` | `XPO` o `GLS` según el transportista de las OUT |
| `tracking_number` | `carrier_tracking_ref` |
| `packages` | cajas distintas (`result_package_id`) de esas OUT |
| `weight_kg` | **15 kg × cajas** (v1.1: el criterio con el que factura XPO; igual que `koroshi_xpo_bultos` v1.1) |
| `volume_m3` | **0,09 m3 × cajas** (v1.1; en la v1.0 era el volumen del producto × unidades) |
| `is_final` | `true` solo en el último tracking. Primero se envían los demás y el final solo cuando están todos enviados |

- Si se reenvía el mismo `order_number` + `tracking_number`, S4T lo actualiza y no lo duplica.
- Los errores (401/403/404/409/422/red) se guardan en el envío y se reintentan en las siguientes pasadas,
  hasta 5 intentos. Un pedido con error no bloquea al resto.

## Dónde se ve

Inventario > Operaciones > **Envíos a S4T**. Filtros: con error, pendientes, enviados, XPO y GLS.

## Cómo activarlo (cuando S4T confirme el entorno de pruebas y si se puede deshacer SHIPPED)

1. **Diagnóstico.** Ajustes > Técnico > Automatización > Acciones planificadas: buscar el cron archivado y pulsar
   «Ejecutar manualmente». Llena la lista en estado *Diagnóstico* sin enviar nada. Revisar la lista.
2. **Un pedido de prueba.** Ajustes > Técnico > Parámetros del sistema: `koroshi_s4t_envios.modo` = `real`.
   Abrir **un** envío acordado con S4T, pulsar «Enviar ahora» y comprobarlo con «Consultar en S4T».
3. **Todo.** Activar el cron (cada 15 min).

Para pararlo: `koroshi_s4t_envios.modo` = `diagnostico`, o archivar el cron.

## Seguridad

- La clave `X-Api-Key` y el host se leen de `s4t.config` (módulo `api_s4t_batch_update_PROD`). La clave no se
  guarda ni se escribe en el log.
- La API va por HTTP sin cifrar.
- No añade campos a tablas que ya existen. Todo se guarda en `koroshi.s4t.envio` y en su tabla de relación con las OUT.
- Desinstalar el módulo borra solo sus propios datos.

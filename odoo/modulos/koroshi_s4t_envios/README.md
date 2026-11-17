# KOROSHI Envíos a S4T (v1.3, 17/11/2026)

Envía a S4T (`POST /shipments`) el transportista, el tracking, los bultos, el peso y el volumen de cada pedido
S-6665. Con el último envío del pedido (`is_final=true`), S4T pasa la orden a `SHIPPED`.


## v1.3.0 (17/11/2026: camión XPO y corrección de bultos; sigue en modo diagnóstico)

Spec: `intent/carga-camion-bultos/spec_2026-11-17.md`. Manual de S4T «API de envíos» (noviembre 2026): volver a mandar
el mismo `order_number` + `tracking_number` actualiza el envío.

- **Camión XPO.** Con koroshi_monitor 1.29 instalado, un tracking XPO está **cerrado** cuando alguna de sus OUT va en
  un *cierre de camión* (Consulta de envíos › «Cerrar camión XPO y enviar manifiesto»). Hasta entonces se manda sin
  `is_final`. El `is_final` (y SHIPPED) va cuando todas las OUT del pedido están hechas **y** todos sus trackings XPO
  están cerrados.
- **Bultos cambiados.** Si los bultos de un envío ya mandado cambian antes del cierre, el envío pasa a «Bultos
  cambiados (pulsar Reenviar)»: se ven los bultos de S4T y los nuevos. Con «Reenviar con los bultos nuevos»
  (responsable de Inventario) se manda el mismo tracking otra vez. Nunca se reenvía solo.
- Después del cierre, o con el final ya mandado, ya no se corrige: solo una nota interna en el pedido, una vez por
  cada cifra nueva.
- **GLS**, como en la v1.2: el final va en cuanto todas las OUT tienen etiqueta.
- **Sin koroshi_monitor 1.29**, todo como en la v1.2.
- Campos nuevos solo en `koroshi.s4t.envio`: `packages_nuevo`, `packages_aviso` y `cerrado`. Filtros «Bultos cambiados» y
  «Camión sin cerrar».

## v1.2.0 (14/11/2026, auditoría 13/11, fase 3; sigue en modo diagnóstico)

- **Una OUT pendiente ya no para el pedido**: se mandan los trackings de las OUT hechas, sin `is_final`. El final va
  cuando ya no queda ninguna OUT por hacer; si el último ya se había mandado sin `is_final`, se reenvía con él (S4T
  actualiza, no duplica).
- **Errores**: 408, 409, 429, 5xx y red se reintentan (hasta 5 veces). Los demás 4xx son definitivos: estado
  **«Rechazado por S4T»**, no se reintentan y se avisa con una nota interna en el pedido y un correo a los de
  `koroshi_s4t_envios.avisar` (parámetro, correos separados por coma; vacío = solo la nota). Al agotar los intentos,
  también se avisa. «Enviar ahora» los vuelve a intentar.
- Una respuesta 200 con una **lista** en vez de un objeto ya no rompe.
- **Cron**: los pedidos rechazados o con los intentos agotados ya no ocupan sitio entre los 500, y los pedidos se
  recorren por turnos (`koroshi_s4t_envios.cursor`), para que los que esperan no tapen siempre a los mismos.
- Bultos, peso y volumen: `bultos_de` y `valores_xpo` de **koroshi_xpo_bultos** (la misma cuenta que la expedición
  XPO). Nueva dependencia: koroshi_xpo_bultos (ya instalado).
- Valorado `queue_job` (un job por pedido en `root.s4t_sync`): no hace falta con los turnos y el commit por pedido, y
  ese canal ya dio problemas.

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

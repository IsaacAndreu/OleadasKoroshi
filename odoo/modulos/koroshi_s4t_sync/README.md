# KOROSHI Sync S4T con OUT canceladas

Deja sincronizar con S4T los pedidos que tienen alguna OUT (backorder) cancelada y todas las demás hechas.

- **Problema:** `s4t.order.sync.action_sync_order` (módulo de Effective `api_s4t_batch_update_PROD`) exige todas
  las transferencias del pedido en «done». Una backorder cancelada lo bloquea para siempre con «El pedido no tiene
  transferencias | tiene transferencias pendientes | tiene transferencias en diferentes estados».
- **Arreglo:** se hereda `action_sync_order`. Si las únicas transferencias no hechas están canceladas, el método de
  Effective ve el pedido solo con las no canceladas (caché de Odoo, sin escribir en la base de datos). El envío es el
  mismo: para tiendas (tipo 38/39) sale de las OUT hechas, que no cambian.
- No toca el módulo de Effective ni añade campos. Vale para el cron 186 (acción 1800) y el botón «Sincronizar S4T».

La acción 1800 v6 (`bin/versiones/20261117_accion-1800_*_v6-*.py`) cancela las backorders de tienda con 0 reservado y
espera a que se junten las cajas pequeñas (3 uds o menos); necesita este módulo instalado.

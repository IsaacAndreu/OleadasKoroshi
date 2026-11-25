# Sync S4T a mano de pedidos concretos (Isaac, 17/11/2026). Igual que la accion 1800, sin filtros.
for nombre in ['S-6665004301']:
    order = env['sale.order'].search([('name', '=', nombre)], limit=1)
    try:
        env['s4t.order.sync'].action_sync_order(order)
        env.cr.commit()
        log('SYNC S4T MANUAL: %s -> %s | %s' % (order.name, order.x_s4t_status, (order.x_s4t_last_log or '')[:200]))
    except Exception as e:
        env.cr.rollback()
        log('SYNC S4T MANUAL ERROR %s: %s' % (nombre, e), level='error')

# =============================================================================
# KOROSHI - SACAR LAS OUT CANCELADAS DE LOS PEDIDOS QUE NO SINCRONIZAN CON S4T
# Accion de servidor de Odoo 13. Modelo: sale.order. Tipo: Ejecutar codigo Python.
#
# El cron "S4T - Sync pedidos 17:00" (accion 1800) da por buenos los pedidos con
# todas las OUT hechas sin contar las canceladas, pero s4t.order.sync.action_sync_order
# mira TODAS las transferencias del pedido y falla con:
#   "El pedido no tiene transferencias | tiene transferencias pendientes |
#    tiene transferencias en diferentes estados"
# Pasa con las backorders canceladas (p.ej. S-6665003350: OUT/20097 done + OUT/20316 cancel).
#
# Esta accion, en los pedidos S-6665% que no estan en READY y cuyas OUT no canceladas
# estan TODAS hechas, quita el grupo de aprovisionamiento a los movimientos de las OUT
# canceladas. picking.group_id = move_lines.group_id y picking.sale_id = group_id.sale_id,
# asi que la OUT cancelada deja de colgar del pedido. No se borra nada.
# En la siguiente pasada del cron (cada 15 min) el pedido se sincroniza.
#
# Para deshacer: el registro guarda "OUT id -> grupo id"; basta volver a poner
# ese group_id en los movimientos de esa OUT.
#
# DIAGNOSTICO = True: no cambia nada, solo ensena lo que haria.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
DESDE = '2026-08-01 00:00:00'     # igual que el cron 1800
DIAGNOSTICO = True                # True: solo cuenta. False: lo arregla
# -----------------------------------------------------------------------------

pedidos = env['sale.order'].search([
    ('name', 'like', 'S-6665%'),
    ('state', 'in', ['sale', 'done']),
    ('s4t_remote_id', '!=', 0),
    ('x_s4t_status', '!=', 'READY'),
    ('date_order', '>=', DESDE),
], order='date_order asc')

texto = ['KOROSHI QUITAR OUT CANCELADAS DE PEDIDOS - %s' % (DIAGNOSTICO and 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)' or 'HECHO')]
texto.append('Pedidos no READY revisados: %d' % len(pedidos))
texto.append('')
texto.append('Pedido | estado S4T | OUT hechas | OUT canceladas que se sacan (id -> grupo id)')

a_tocar = env['stock.picking']
n_pedidos = 0
saltadas = []
for order in pedidos:
    outs = order.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')
    vivas = outs.filtered(lambda p: p.state != 'cancel')
    canceladas = outs.filtered(lambda p: p.state == 'cancel')
    if not canceladas or not vivas:
        continue
    if any(p.state != 'done' for p in vivas):
        continue
    sacar = env['stock.picking']
    for p in canceladas:
        # Solo si TODOS sus movimientos estan cancelados (no tocar nada con algo vivo)
        if any(m.state != 'cancel' for m in p.move_lines):
            saltadas.append('%s (%s): tiene movimientos no cancelados' % (p.name, order.name))
            continue
        sacar |= p
    if not sacar:
        continue
    n_pedidos += 1
    a_tocar |= sacar
    partes = []
    for p in sacar:
        partes.append('%s id %d -> grupo %d' % (p.name, p.id, p.group_id.id or 0))
    texto.append('   %s | %s | %s | %s' % (
        order.name, order.x_s4t_status or '', ', '.join(vivas.mapped('name')), ', '.join(partes)))

texto.append('')
texto.append('Total: %d pedidos, %d OUT canceladas a sacar' % (n_pedidos, len(a_tocar)))
if saltadas:
    texto.append('No se tocan:')
    for s in saltadas:
        texto.append('   ' + s)

if not DIAGNOSTICO and a_tocar:
    a_tocar.mapped('move_lines').write({'group_id': False})
    # Comprobar que ya no cuelgan de ningun pedido
    quedan = a_tocar.filtered(lambda p: p.sale_id)
    texto.append('')
    texto.append('Despues: OUT canceladas que siguen colgando de un pedido: %d' % len(quedan))
    for p in quedan:
        texto.append('   %s -> %s' % (p.name, p.sale_id.name))

mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + '\n\nEs un diagnostico: no se ha cambiado nada. Para arreglarlo: DIAGNOSTICO = False.')
# Sin aviso al final: un raise Warning desharia el arreglo. El resultado queda en el registro.

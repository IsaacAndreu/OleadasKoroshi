# =============================================================================
# KOROSHI - DESHACER "FORCE AVAILABILITY" EN LAS OUT DE UNA OLEADA
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# El boton "Force Availability" de la agrupacion pone las OUT en Preparado SIN reservar
# stock y con TODO como hecho (una linea por movimiento, reservado 0, hecho = pedido).
# Asi el programa de la U las ve ya leidas y, al validar, saldria stock que no esta.
# Esta accion, solo en las OUT de OLEADA que no estan hechas:
#   1. Borra las lineas SIN reserva (reservado 0): son las que ha creado el boton.
#      Si alguna linea tiene reserva, no se toca (y se avisa).
#   2. Recalcula el estado de los movimientos (vuelven a En espera).
#   3. "Comprobar disponibilidad": reservan lo que hay en el SORTER.
# DIAGNOSTICO = True: no cambia nada, solo cuenta y ensena lo que haria.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
OLEADA = 'B-KOR-2110-01'
DIAGNOSTICO = True                # True: solo cuenta. False: lo arregla
# -----------------------------------------------------------------------------

outs = env['stock.picking'].search([
    ('company_id', '=', COMPANY_ID),
    ('batch_id.name', '=', OLEADA),
    ('picking_type_code', '=', 'outgoing'),
    ('state', 'not in', ('done', 'cancel')),
], order='name asc')

texto = ['KOROSHI DESHACER FORCE AVAILABILITY - %s - %s' % (OLEADA, DIAGNOSTICO and 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)' or 'HECHO')]
if not outs:
    log(texto[0] + '\nNo hay OUT abiertas en la oleada')
    raise Warning('No hay OUT abiertas en la oleada %s' % OLEADA)

forzadas = env['stock.move.line']
total_lineas = 0
total_hecho = 0.0
for p in outs:
    sin_reserva = env['stock.move.line']
    con_reserva = 0
    hecho = 0.0
    for ml in p.move_line_ids:
        if ml.product_uom_qty > 0:
            con_reserva += 1
        else:
            sin_reserva |= ml
            hecho += ml.qty_done
    forzadas |= sin_reserva
    total_lineas += len(sin_reserva)
    total_hecho += hecho
    texto.append('   %s | %s | %s | lineas forzadas %d (hecho %d) | lineas con reserva %d' % (
        p.name, p.partner_id and p.partner_id.name or '', p.state, len(sin_reserva), hecho, con_reserva))
texto.append('Total: %d lineas forzadas, %d uds marcadas como hechas sin reserva' % (total_lineas, total_hecho))

if not DIAGNOSTICO:
    forzadas.unlink()
    outs.mapped('move_lines')._recompute_state()
    outs.action_assign()
    texto.append('')
    texto.append('Despues (OUT | estado | reservado / pedido | hecho):')
    for p in outs:
        pedido = 0.0
        reservado = 0.0
        hecho = 0.0
        for m in p.move_lines:
            if m.state != 'cancel':
                pedido += m.product_uom_qty
                reservado += m.reserved_availability
        for ml in p.move_line_ids:
            hecho += ml.qty_done
        texto.append('   %s | %s | %d / %d | %d' % (p.name, p.state, reservado, pedido, hecho))

mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + '\n\nEs un diagnostico: no se ha cambiado nada. Para arreglarlo: DIAGNOSTICO = False.')
# Sin aviso al final: un raise Warning desharia el arreglo. El resultado queda en el registro.

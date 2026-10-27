# =============================================================================
# KOROSHI - RECALCULAR LOS CONTADORES DE LAS OUT (Demanda / Reservado / Hecho)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Por que: las columnas de la lista de Transferencias "Demanded / Reserved / Done Quantity"
# (count_demand, count_reserve, count_done, del modulo stock_picking_date) son campos guardados
# que no se recalculan solos. Al partir las OUT por zonas, cada OUT nueva se copia de la original
# y se queda con los contadores del pedido entero: agrupadas por Batch transfer parece que cada
# agrupacion lleva ~600 uds (27/10/2026).
# Que hace: pone en cada OUT
#   count_demand  = suma de la demanda de sus movimientos no cancelados
#   count_reserve = suma de lo reservado de esos movimientos
#   count_done    = suma de lo hecho de esos movimientos
# OUT: las seleccionadas; sin seleccion, las de las agrupaciones de zona de hoy (Z-ddmm-...).
# MODO = 'DIAGNOSTICO': no cambia nada, ensena lo que cambiaria. MODO = 'REAL': lo escribe.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
MODO = 'DIAGNOSTICO'              # 'DIAGNOSTICO' (no cambia nada) o 'REAL'
ZONA_HORARIA = 'Europe/Madrid'
# -----------------------------------------------------------------------------

if MODO not in ('DIAGNOSTICO', 'REAL'):
    log('KOROSHI CONTADORES OUT - MODO desconocido: %s' % MODO)
    raise Warning("MODO tiene que ser 'DIAGNOSTICO' o 'REAL'")

Picking = env['stock.picking']
if env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    outs = Picking.browse(env.context.get('active_ids'))
else:
    hoy = datetime.datetime.now(timezone(ZONA_HORARIA)).strftime('%d%m')
    outs = Picking.search([('company_id', '=', COMPANY_ID), ('batch_id.name', '=like', 'Z-%s-%%' % hoy)], order='name')

cambian = []
total_antes = [0.0, 0.0, 0.0]
total_despues = [0.0, 0.0, 0.0]
for p in outs:
    dem = 0.0
    res = 0.0
    hecho = 0.0
    for m in p.move_lines:
        if m.state == 'cancel':
            continue
        dem += m.product_uom_qty
        res += m.reserved_availability
        hecho += m.quantity_done
    total_antes[0] += p.count_demand
    total_antes[1] += p.count_reserve
    total_antes[2] += p.count_done
    total_despues[0] += dem
    total_despues[1] += res
    total_despues[2] += hecho
    if abs(p.count_demand - dem) > 0.001 or abs(p.count_reserve - res) > 0.001 or abs(p.count_done - hecho) > 0.001:
        cambian.append((p, dem, res, hecho))

lineas = ['KOROSHI CONTADORES OUT - %s' % (MODO == 'REAL' and 'HECHO' or 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)'),
          'OUT revisadas: %d | a corregir: %d' % (len(outs), len(cambian)),
          'Total demanda / reservado / hecho: antes %d / %d / %d -> ahora %d / %d / %d' % (
              total_antes[0], total_antes[1], total_antes[2], total_despues[0], total_despues[1], total_despues[2]),
          '']
for p, dem, res, hecho in cambian:
    lineas.append('   %s | %s | %d/%d/%d -> %d/%d/%d' % (
        p.name, p.batch_id.name or '', p.count_demand, p.count_reserve, p.count_done, dem, res, hecho))
    if MODO == 'REAL':
        p.write({'count_demand': dem, 'count_reserve': res, 'count_done': hecho})

mensaje = '\n'.join(lineas)
log(mensaje)
if MODO == 'DIAGNOSTICO':
    raise Warning(mensaje + "\n\nEs un diagnostico: no se ha cambiado nada. Para corregirlo: MODO = 'REAL'.")

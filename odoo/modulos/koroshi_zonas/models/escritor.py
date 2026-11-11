# -*- coding: utf-8 -*-
# =============================================================================
# Escritor: aplica un Reparto en Odoo. Copia literal del partir de la v12f (accion 1883, lineas 967-1126):
# copia de la OUT por zona, _split de cada movimiento segun la zona de sus lineas reservadas, agrupaciones
# <prefijo><zona> y nota '... | CAJAS n'. Cada linea reservada va entera a una zona.
# Es lo UNICO que el modulo escribe fuera de sus tablas. Nunca cancela una OUT, nunca fuerza disponibilidad
# ni escribe stock.quant. Las comprobaciones (fallos) se devuelven: quien llama decide deshacer (savepoint).
# =============================================================================
from . import lector


def aplicar(env, rep):
    """Parte las OUT segun rep (motor.modelo.Reparto). Devuelve (lineas de informe, fallos, OUT, out_de)."""
    COMPANY_ID = rep.parametros['COMPANY_ID']
    ctx = lector.contexto_compania(env)
    Picking = env['stock.picking'].with_context(ctx)
    Move = env['stock.move'].with_context(ctx)
    MoveLine = env['stock.move.line'].with_context(ctx)
    Batch = env['stock.picking.batch'].with_context(ctx)
    orden_zonas = rep.orden_zonas
    prefijo = rep.prefijo

    # v12: el partir de la v9c tal cual, con la zona final de cada linea (zona_fin)
    zona_ml = rep.zona_fin
    lote_de = {}
    caja_de = {}
    cajas_zona = {}
    plan = []
    for pid, por_z, principal, sin_res, caja in rep.plan:
        p = Picking.browse(pid)
        uds_z = {}
        for zn in por_z:
            uds_z[zn] = por_z[zn][1]
            cajas_zona[(p.id, zn)] = por_z[zn][0]
        lote_de[p.id] = prefijo
        caja_de[p.id] = '%02d' % caja
        plan.append((p, uds_z, principal, sin_res, caja))

    # ---------------- 6. Partir ----------------
    lotes = {}
    todas_out = Picking.browse()
    out_de = {}
    uds_antes = {}
    for p, uds_z, principal, sin_res, caja in plan:
        total_p = 0.0
        for m in p.move_lines:
            if m.state not in ('done', 'cancel'):
                total_p += m.product_uom_qty
        uds_antes[p.id] = total_p
        out_de[(p.id, principal)] = p
        for zn in orden_zonas:
            if zn == principal or uds_z.get(zn, 0.0) <= 0:
                continue
            nueva = p.copy({
                'move_lines': [],
                'move_line_ids': [],
                'package_level_ids': [],
                'batch_id': False,
                'backorder_id': False,
                'origin': p.origin,
            })
            out_de[(p.id, zn)] = nueva
        for m in p.move_lines:
            if m.state in ('done', 'cancel'):
                continue
            por_z = {}
            reservado_m = 0.0
            for ml in m.move_line_ids:
                if ml.id not in zona_ml:
                    continue
                zn = zona_ml[ml.id]
                if zn not in por_z:
                    por_z[zn] = [0.0, MoveLine.browse()]
                por_z[zn][0] += ml.product_uom_qty
                por_z[zn][1] = por_z[zn][1] | ml
                reservado_m += ml.product_uom_qty
            zs = []
            for zn in orden_zonas:
                if zn in por_z:
                    zs.append(zn)
            if not zs:
                continue
            if principal in zs or m.product_uom_qty - reservado_m > 0.001:
                guarda = principal
            else:
                guarda = zs[0]
            for zn in zs:
                if zn == guarda:
                    continue
                destino = out_de[(p.id, zn)]
                nuevo = Move.browse(m._split(por_z[zn][0]))
                nuevo.write({'picking_id': destino.id})
                por_z[zn][1].write({'move_id': nuevo.id, 'picking_id': destino.id})
                nuevo._recompute_state()
            if guarda != principal:
                destino = out_de[(p.id, guarda)]
                m.write({'picking_id': destino.id})
                por_z[guarda][1].write({'picking_id': destino.id})
            m._recompute_state()
        for zn in orden_zonas:
            if (p.id, zn) not in out_de:
                continue
            o = out_de[(p.id, zn)]
            nl = lote_de[p.id] + zn
            if nl not in lotes:
                lotes[nl] = Batch.create({'name': nl, 'company_id': COMPANY_ID, 'batch_type': 'normal'})
            o.write({
                'batch_id': lotes[nl].id,
                'note': '%s | CAJA %s | %s | PEDIDO %s | CAJAS %d' % (
                    nl, caja_de[p.id], p.partner_id.name or '', p.origin or '', cajas_zona.get((p.id, zn), 0)),
            })
            todas_out |= o
    for nl in lotes:
        lotes[nl].write({'state': 'in_progress'})
    # v9: contadores de la lista de Transferencias (modulo stock_picking_date, no se recalculan solos)
    for o in todas_out:
        dem_o = 0.0
        res_o = 0.0
        hecho_o = 0.0
        for m in o.move_lines:
            if m.state == 'cancel':
                continue
            dem_o += m.product_uom_qty
            res_o += m.reserved_availability
            hecho_o += m.quantity_done
        o.write({'count_demand': dem_o, 'count_reserve': res_o, 'count_done': hecho_o})

    # ---------------- 7. Comprobaciones ----------------
    fallos = []
    n_no_cuadra = 0
    despues = []
    for p, uds_z, principal, sin_res, caja in plan:
        total_d = 0.0
        for zn in orden_zonas:
            if (p.id, zn) not in out_de:
                continue
            o = out_de[(p.id, zn)]
            res_o = 0.0
            for m in o.move_lines:
                if m.state not in ('done', 'cancel'):
                    total_d += m.product_uom_qty
            for ml in o.move_line_ids:
                res_o += ml.product_uom_qty
                if zona_ml.get(ml.id, zn) != zn:
                    fallos.append('%s (%s): linea de %s reservada en otra zona (%s)' % (
                        o.name, zn, ml.product_id.display_name, ml.location_id.complete_name))
            if zn != principal and abs(res_o - uds_z.get(zn, 0.0)) > 0.001:
                fallos.append('%s (%s): %d uds reservadas y deberian ser %d' % (o.name, zn, res_o, uds_z.get(zn, 0.0)))
            if o.state != 'assigned':
                fallos.append('%s (%s): estado %s' % (o.name, zn, o.state))
            despues.append('   %s | %s | %s | %d uds | %s' % (o.name, zn, o.state, res_o, o.batch_id.name or ''))
        if abs(total_d - uds_antes[p.id]) > 0.001:
            n_no_cuadra += 1
            fallos.append('%s %s: antes %d uds, despues %d' % (p.origin or '', p.name, uds_antes[p.id], total_d))

    lineas = []
    lineas.append('')
    lineas.append('Despues de partir (OUT | zona | estado | uds reservadas | agrupacion):')
    for d in despues:
        lineas.append(d)
    lineas.append('OUT nuevas: %d | agrupaciones: %d | pedidos que no cuadran: %d | fallos: %d' % (
        len(todas_out) - len(plan), len(lotes), n_no_cuadra, len(fallos)))
    if fallos:
        lineas.append('')
        lineas.append('FALLOS:')
        for f in fallos[:60]:
            lineas.append('   %s' % f)
    return lineas, fallos, todas_out, out_de

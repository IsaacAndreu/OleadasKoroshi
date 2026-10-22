# =============================================================================
# KOROSHI - PARTIR LAS OUT DE TIENDA POR ZONAS (una OUT por tienda y zona)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
# Se ejecuta sin seleccion: busca sola las OUT de hoy.
#
# 1. Coge las OUT de "PED. TIENDAS" creadas hoy (hora de Espana), Preparadas, sin ninguna
#    unidad leida, fuera de cualquier agrupacion que no sea la del dia (TIENDA...) y que no
#    salgan del SORTER. Como mucho N_PEDIDOS (ELEGIR = 'GRANDES': las de mas uds).
# 2. Corta la nave en N_ZONAS zonas seguidas por pasillo (lineal // 2), con el mismo tiempo:
#    SEG_HUECO por lectura (OUT + hueco + producto), SEG_UD por unidad y SEG_LINEAL por
#    cada lineal que visita cada OUT. Lo que no tiene lineal va a la zona ZX.
# 3. Cada OUT se queda en su zona principal (la de mas uds, sin contar ZX). Por cada otra
#    zona se crea una OUT nueva (copia, mismo origen S-...) y se le pasan los movimientos
#    con sus reservas. Lo que no esta reservado se queda en la OUT original.
# 4. Una agrupacion por zona: Z-ddmm-D1... Con mas de TIENDAS_POR_RONDA tiendas, rondas:
#    Z-ddmm-R1-D1... Nota de cada OUT: Z-ddmm-D3 | CAJA 05 | K34 ... | PEDIDO S-...
#
# MODO = 'DIAGNOSTICO' -> no escribe nada: ensena el reparto y acaba con raise Warning
# MODO = 'SIMULAR'     -> lo hace todo, comprueba y al final raise Warning (Odoo lo deshace)
# MODO = 'REAL'        -> lo hace de verdad (si alguna comprobacion falla, deshace todo)
#
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
MODO = 'DIAGNOSTICO'
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
N_ZONAS = 5
N_PEDIDOS = 200
TIENDAS_POR_RONDA = 50
ELEGIR = 'GRANDES'               # 'GRANDES' (las de mas uds) o 'PRIMERAS' (por orden de llegada)
SEG_HUECO = 20
SEG_UD = 4
SEG_LINEAL = 15
ZONA_OTRAS = 'ZX'                # huecos sin lineal (fuera de lineal)
PREFIJO_AGRUPACION = 'TIENDA'    # agrupacion del dia en la que llegan las OUT: se aceptan
ZONA_HORARIA = 'Europe/Madrid'
IDS_PRUEBA = []                  # ids de OUT concretas para probar; vacio = busca las de hoy
# -----------------------------------------------------------------------------

ctx = dict(env.context)
ctx['allowed_company_ids'] = [COMPANY_ID]
Picking = env['stock.picking'].with_context(ctx)
Move = env['stock.move'].with_context(ctx)
MoveLine = env['stock.move.line'].with_context(ctx)
Batch = env['stock.picking.batch'].with_context(ctx)

ahora_local = datetime.datetime.now(timezone(ZONA_HORARIA))
medianoche_local = timezone(ZONA_HORARIA).localize(datetime.datetime(ahora_local.year, ahora_local.month, ahora_local.day))
desde = medianoche_local.astimezone(timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S')
hoy = ahora_local.strftime('%d%m')

sorter = env['stock.location'].with_context(ctx).search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)

# ---------------- 1. OUT candidatas -------------------------------------------
if IDS_PRUEBA:
    candidatas = Picking.browse(IDS_PRUEBA).exists()
else:
    candidatas = Picking.search([
        ('company_id', '=', COMPANY_ID),
        ('picking_type_code', '=', 'outgoing'),
        ('state', '=', 'assigned'),
        ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO),
        ('create_date', '>=', desde),
    ], order='name asc')

validas = []
saltadas = []
for p in candidatas:
    motivo = ''
    tipo = p.sale_id and p.sale_id.s_order_type_id and p.sale_id.s_order_type_id.name or ''
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing':
        motivo = 'no es una OUT de la empresa %d' % COMPANY_ID
    elif tipo != TIPO_PEDIDO:
        motivo = 'tipo de pedido %s' % (tipo or 'sin tipo')
    elif p.state != 'assigned':
        motivo = 'no esta Preparada (%s)' % p.state
    elif p.batch_id and not (p.batch_id.name or '').startswith(PREFIJO_AGRUPACION):
        motivo = 'esta en la agrupacion %s' % p.batch_id.name
    elif sorter and p.location_id.id == sorter.id:
        motivo = 'sale del SORTER'
    else:
        for ml in p.move_line_ids:
            if ml.qty_done > 0:
                motivo = 'ya tiene unidades leidas'
                break
            if sorter and ml.location_id.id == sorter.id:
                motivo = 'tiene lineas reservadas en el SORTER'
                break
    if motivo:
        saltadas.append('%s (%s): %s' % (p.name, p.partner_id.name or '', motivo))
        continue
    uds_p = 0.0
    for m in p.move_lines:
        if m.state not in ('done', 'cancel'):
            uds_p += m.product_uom_qty
    validas.append((uds_p, p.id))

if ELEGIR == 'GRANDES':
    validas = sorted(validas, key=lambda v: -v[0])
elegidas_ids = []
for v in validas:
    if len(elegidas_ids) >= N_PEDIDOS:
        saltadas.append('%s: fuera del tope de %d pedidos' % (Picking.browse(v[1]).name, N_PEDIDOS))
        continue
    elegidas_ids.append(v[1])

# Orden de las tiendas: por numero de tienda (K1, K7, K8...) y despues por nombre de OUT
pares = []
for p in Picking.browse(elegidas_ids):
    nombre_t = p.partner_id.name or ''
    knum = 9999
    if nombre_t[:1] == 'K':
        num = ''
        for ch in nombre_t[1:]:
            if ch.isdigit():
                num += ch
            else:
                break
        if num:
            knum = int(num)
    pares.append((knum, p.name, p.id))
pares.sort()
elegidas = Picking.browse()
for par in pares:
    elegidas |= Picking.browse(par[2])

# ---------------- 2. Lineas reservadas y peso por pasillo ----------------------
info_ml = {}        # ml.id -> (pasillo o -1 si no tiene lineal, lineal)
peso_pas = {}       # pasillo -> segundos
lin_pas = {}        # pasillo -> [lineal min, lineal max]
peso_zx = 0.0
vistos_lect = {}
vistos_lin = {}
n_lineas = 0
for p in elegidas:
    for ml in p.move_line_ids:
        qty = ml.product_uom_qty
        if qty <= 0:
            continue
        n_lineas += 1
        lineal = 0
        segmentos = (ml.location_id.complete_name or '').split('/')
        for idx in range(len(segmentos) - 1, -1, -1):
            texto = segmentos[idx].strip()
            if ' - ' in texto:
                texto = texto.split(' - ', 1)[1]
            if len(texto) > 1 and texto[0] == 'L' and texto[1].isdigit():
                num = ''
                for ch in texto[1:]:
                    if ch.isdigit():
                        num += ch
                    else:
                        break
                if num:
                    lineal = int(num)
                break
        seg = SEG_UD * qty
        clave_lect = (p.id, ml.location_id.id, ml.product_id.id)
        if clave_lect not in vistos_lect:
            vistos_lect[clave_lect] = 1
            seg += SEG_HUECO
        if lineal:
            pasillo = lineal // 2
            clave_lin = (p.id, lineal)
            if clave_lin not in vistos_lin:
                vistos_lin[clave_lin] = 1
                seg += SEG_LINEAL
            peso_pas[pasillo] = peso_pas.get(pasillo, 0.0) + seg
            if pasillo not in lin_pas:
                lin_pas[pasillo] = [lineal, lineal]
            if lineal < lin_pas[pasillo][0]:
                lin_pas[pasillo][0] = lineal
            if lineal > lin_pas[pasillo][1]:
                lin_pas[pasillo][1] = lineal
            info_ml[ml.id] = (pasillo, lineal)
        else:
            peso_zx += seg
            info_ml[ml.id] = (-1, 0)

# ---------------- 3. Cortar en N_ZONAS zonas seguidas con el mismo tiempo -------
pasillos = sorted(peso_pas.keys())
peso_total = 0.0
for pa in pasillos:
    peso_total += peso_pas[pa]
objetivo = N_ZONAS and peso_total / N_ZONAS or 0.0
zona_pas = {}
z = 1
acum = 0.0
for pa in pasillos:
    w = peso_pas[pa]
    if acum > 0 and z < N_ZONAS and acum + w / 2.0 > objetivo * z:
        z += 1
    zona_pas[pa] = 'D%d' % z
    acum += w
orden_zonas = []
for i in range(1, z + 1):
    orden_zonas.append('D%d' % i)
orden_zonas.append(ZONA_OTRAS)

zona_ml = {}
for ml_id in info_ml:
    pa = info_ml[ml_id][0]
    if pa < 0:
        zona_ml[ml_id] = ZONA_OTRAS
    else:
        zona_ml[ml_id] = zona_pas[pa]

# Datos por zona: segundos, uds, OUT, lineales
datos_zona = {}
for zn in orden_zonas:
    datos_zona[zn] = {'seg': 0.0, 'uds': 0.0, 'outs': {}, 'lmin': 9999, 'lmax': 0}
for pa in pasillos:
    d = datos_zona[zona_pas[pa]]
    d['seg'] += peso_pas[pa]
    if lin_pas[pa][0] < d['lmin']:
        d['lmin'] = lin_pas[pa][0]
    if lin_pas[pa][1] > d['lmax']:
        d['lmax'] = lin_pas[pa][1]
datos_zona[ZONA_OTRAS]['seg'] = peso_zx

# Plan por OUT: uds por zona, zona principal y uds sin reserva
plan = []           # (p, uds por zona, principal, sin reserva, ronda, caja)
n_rondas = 1
if len(elegidas) > TIENDAS_POR_RONDA:
    n_rondas = (len(elegidas) + TIENDAS_POR_RONDA - 1) // TIENDAS_POR_RONDA
i = 0
for p in elegidas:
    uds_z = {}
    reservado = 0.0
    for ml in p.move_line_ids:
        if ml.id not in zona_ml:
            continue
        zn = zona_ml[ml.id]
        uds_z[zn] = uds_z.get(zn, 0.0) + ml.product_uom_qty
        reservado += ml.product_uom_qty
        datos_zona[zn]['uds'] += ml.product_uom_qty
        datos_zona[zn]['outs'][p.id] = 1
    demanda = 0.0
    for m in p.move_lines:
        if m.state not in ('done', 'cancel'):
            demanda += m.product_uom_qty
    principal = ''
    mejor = -1.0
    for zn in orden_zonas:
        if zn == ZONA_OTRAS:
            continue
        if uds_z.get(zn, 0.0) > mejor and uds_z.get(zn, 0.0) > 0:
            mejor = uds_z[zn]
            principal = zn
    if not principal:
        principal = uds_z and ZONA_OTRAS or orden_zonas[0]
    plan.append((p, uds_z, principal, demanda - reservado, i // TIENDAS_POR_RONDA + 1, i % TIENDAS_POR_RONDA + 1))
    i += 1

# Nombre de la agrupacion y de la caja de cada tienda (con rondas: Z-ddmm-R1-D1 y R1-01)
lote_de = {}
caja_de = {}
for p, uds_z, principal, sin_res, ronda, caja in plan:
    if n_rondas > 1:
        lote_de[p.id] = 'Z-%s-R%d-' % (hoy, ronda)
        caja_de[p.id] = 'R%d-%02d' % (ronda, caja)
    else:
        lote_de[p.id] = 'Z-%s-' % hoy
        caja_de[p.id] = '%02d' % caja

# ---------------- Resumen del reparto ------------------------------------------
lineas = []
lineas.append('KOROSHI PARTIR OUT ZONAS - %s' % MODO)
lineas.append('OUT de tienda: %d | lineas reservadas: %d | candidatas %d, saltadas %d' % (
    len(elegidas), n_lineas, len(candidatas), len(saltadas)))
lineas.append('')
for zn in orden_zonas:
    d = datos_zona[zn]
    if zn == ZONA_OTRAS:
        if not d['uds']:
            continue
        tramo = 'fuera de lineal'
    else:
        tramo = d['lmax'] and ('L%d-L%d' % (d['lmin'], d['lmax'])) or 'sin lineas'
    lineas.append('Zona %s | %s | %d uds | %d OUT (cajas) | ~%d min' % (
        zn, tramo, d['uds'], len(d['outs']), round(d['seg'] / 60.0)))
if n_rondas > 1:
    lineas.append('Rondas: %d (%d tiendas por ronda). Agrupaciones: Z-%s-R<n>-<zona>' % (n_rondas, TIENDAS_POR_RONDA, hoy))
else:
    lineas.append('Rondas: 1. Agrupaciones: Z-%s-<zona>' % hoy)
lineas.append('')
lineas.append('Caja | tienda | OUT | pedido | uds por zona (* = se queda la OUT original) | sin reserva')
n_nuevas_plan = 0
for p, uds_z, principal, sin_res, ronda, caja in plan:
    trozos = ''
    for zn in orden_zonas:
        if uds_z.get(zn, 0.0) > 0:
            marca = ''
            if zn == principal:
                marca = '*'
            else:
                n_nuevas_plan += 1
            trozos += '%s%s:%d  ' % (zn, marca, uds_z[zn])
    lineas.append('   %s %s | %s | %s | %s| %d' % (
        caja_de[p.id], p.partner_id.name or '', p.name, p.origin or '', trozos, sin_res))
lineas.append('OUT nuevas que se crearan: %d' % n_nuevas_plan)
if saltadas:
    lineas.append('')
    lineas.append('Saltadas (%d):' % len(saltadas))
    for s in saltadas[:60]:
        lineas.append('   %s' % s)
    if len(saltadas) > 60:
        lineas.append('   ... y %d mas' % (len(saltadas) - 60))

if not elegidas:
    lineas.append('')
    lineas.append('No hay ninguna OUT para partir.')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

if MODO == 'DIAGNOSTICO':
    lineas.append('')
    lineas.append('DIAGNOSTICO: no se ha escrito nada. Siguiente paso: MODO = SIMULAR.')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

# ---------------- 4. Partir (SIMULAR y REAL) -----------------------------------
lotes = {}
todas_out = Picking.browse()
out_de = {}         # (p.id, zona) -> OUT
uds_antes = {}
for p, uds_z, principal, sin_res, ronda, caja in plan:
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
    # Repartir cada movimiento segun la zona de sus lineas reservadas
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
        # El movimiento original se queda en la zona principal si tiene algo de ella o algo sin reserva
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
    # Agrupacion y nota de cada OUT de esta tienda
    for zn in orden_zonas:
        if (p.id, zn) not in out_de:
            continue
        o = out_de[(p.id, zn)]
        nl = lote_de[p.id] + zn
        if nl not in lotes:
            lotes[nl] = Batch.create({'name': nl, 'company_id': COMPANY_ID, 'batch_type': 'normal'})
        o.write({
            'batch_id': lotes[nl].id,
            'note': '%s | CAJA %s | %s | PEDIDO %s' % (nl, caja_de[p.id], p.partner_id.name or '', p.origin or ''),
        })
        todas_out |= o
for nl in lotes:
    lotes[nl].write({'state': 'in_progress'})

# ---------------- 5. Comprobaciones --------------------------------------------
fallos = []
n_no_cuadra = 0
despues = []
for p, uds_z, principal, sin_res, ronda, caja in plan:
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

if fallos:
    lineas.insert(0, 'NO SE HA HECHO NADA (se ha deshecho todo)')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

if MODO != 'REAL':
    lineas.append('')
    lineas.append('SIMULACION: al lanzar este aviso Odoo deshace todo. Para hacerlo de verdad: MODO = REAL.')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

lineas[0] = 'KOROSHI PARTIR OUT ZONAS - HECHO'
log('\n'.join(lineas), level='info')
action = {
    'type': 'ir.actions.act_window',
    'name': 'OUT por zonas %s (%d OUT)' % (hoy, len(todas_out)),
    'res_model': 'stock.picking',
    'view_mode': 'tree,form',
    'domain': [('id', 'in', todas_out.ids)],
    'target': 'current',
}

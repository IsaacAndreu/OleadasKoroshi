# v11 (06/11/2026): PRUEBA de 4 zonas fijas con el MUELLE como zona, sobre 7 OUT concretas.
# Basada en la v10b (27/10), pero sin corte optimo ni horas: las zonas son fijas por ubicacion.
#   MU = muelle (ubicaciones MU-..)   A = lineales L1-L100   B = L101-L120   C = L121-L140
# Cada OUT se queda en su zona con mas uds; por cada otra zona, una OUT nueva con sus movimientos y reservas.
# Una agrupacion por zona: Z-ddmm-MU, Z-ddmm-A... (si ya hay Z-ddmm de hoy: Z-ddmm-R2-MU...), para que el
# monitor de picking las vea como zonas. Las OUT salen de la agrupacion del dia (TIENDA ...).
# Cajas estimadas por volumen: caja llena = 0,084 m3 de product.volume (mediana de 3.050 cajas llenas 20/10-06/11).
# Ninguna OUT de zona por debajo de MIN_UDS_OUT: se junta con la zona de al lado (como la v10).
#
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python. Sin seleccion.
# MODO = 'DIAGNOSTICO' -> no escribe nada: ensena el reparto
# MODO = 'SIMULAR'     -> lo hace todo, comprueba y al final raise Warning (Odoo lo deshace)
# MODO = 'REAL'        -> lo hace de verdad (si alguna comprobacion falla, deshace todo)
# Reglas de safe_eval: sin f-strings, sin import, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
MODO = 'DIAGNOSTICO'
COMPANY_ID = 8
IDS_OUT = [384928, 384929, 384930, 384931, 384935, 384940, 384942]   # OUT/23442 23443 23444 23445 23449 23454 23456
ZONAS = ['MU', 'A', 'B', 'C']        # orden de las zonas (para juntar trozos chicos con la de al lado)
LIMITE_A = 100                       # A = lineales hasta L100
LIMITE_B = 120                       # B = L101..L120; C = desde L121
MIN_UDS_OUT = 15
VOL_CAJA = 0.084                     # m3 de product.volume que caben en una caja llena
PREFIJO_AGRUPACION = 'TIENDA'        # agrupacion del dia en la que estan las OUT: se aceptan
ZONA_HORARIA = 'Europe/Madrid'
# -----------------------------------------------------------------------------

ctx = dict(env.context)
ctx['allowed_company_ids'] = [COMPANY_ID]
Picking = env['stock.picking'].with_context(ctx)
Move = env['stock.move'].with_context(ctx)
MoveLine = env['stock.move.line'].with_context(ctx)
Batch = env['stock.picking.batch'].with_context(ctx)

ahora_local = datetime.datetime.now(timezone(ZONA_HORARIA))
hoy = ahora_local.strftime('%d%m')
sorter = env['stock.location'].with_context(ctx).search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)


def numero_k(nombre):
    if nombre[:1] != 'K':
        return 9999
    num = ''
    for ch in nombre[1:]:
        if ch.isdigit():
            num += ch
        else:
            break
    return num and int(num) or 9999


def lineal_de(ubicacion):
    segmentos = (ubicacion.complete_name or '').split('/')
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
            return num and int(num) or 0
    return 0


def zona_de(ubicacion):
    if 'MU-' in (ubicacion.complete_name or ''):
        return 'MU'
    lin = lineal_de(ubicacion)
    if not lin:
        return ''
    if lin <= LIMITE_A:
        return 'A'
    if lin <= LIMITE_B:
        return 'B'
    return 'C'


def sitio(ubicacion):
    # numero para ordenar el tramo: lineal (L119 -> 119) o fila del muelle (MU-11 -> 1011); 0 = nada
    if 'MU-' in (ubicacion.complete_name or ''):
        t = ubicacion.complete_name.split('MU-')[1][:2]
        return t.isdigit() and 1000 + int(t) or 0
    return lineal_de(ubicacion)


def txt_sitio(n):
    return n >= 1000 and ('MU-%02d' % (n - 1000)) or ('L%d' % n)


def tramo_txt(ss):
    if not ss:
        return '-'
    return len(ss) > 1 and ('%s..%s' % (txt_sitio(ss[0]), txt_sitio(ss[-1]))) or txt_sitio(ss[0])


# ---------------- 1. Comprobar las OUT ----------------------------------------
lineas = []
saltadas = []
validas = Picking.browse()
for p in Picking.browse(IDS_OUT).exists():
    motivo = ''
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing':
        motivo = 'no es una OUT de la empresa %d' % COMPANY_ID
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
            if not zona_de(ml.location_id):
                motivo = 'linea reservada fuera de zona (%s)' % (ml.location_id.complete_name or '')
                break
    if motivo:
        saltadas.append('%s (%s): %s' % (p.name, p.partner_id.name or '', motivo))
        continue
    validas |= p

pares = []
for p in validas:
    pares.append((numero_k(p.partner_id.name or ''), p.name, p.id))
pares.sort()
elegidas = Picking.browse()
for par in pares:
    elegidas |= Picking.browse(par[2])

# ---------------- 2. Zona de cada linea y trozos chicos ------------------------
zona_ml = {}
uds_pz = {}          # p.id -> {zona: uds}
mls_pz = {}          # p.id -> {zona: [ml.id]}
uds_juntadas = 0.0
for p in elegidas:
    uds_pz[p.id] = {}
    mls_pz[p.id] = {}
    for ml in p.move_line_ids:
        if ml.product_uom_qty <= 0:
            continue
        zn = zona_de(ml.location_id)
        zona_ml[ml.id] = zn
        uds_pz[p.id][zn] = uds_pz[p.id].get(zn, 0.0) + ml.product_uom_qty
        mls_pz[p.id].setdefault(zn, []).append(ml.id)
    while True:
        zs = []
        for zn in ZONAS:
            if uds_pz[p.id].get(zn, 0.0) > 0:
                zs.append(zn)
        if len(zs) < 2:
            break
        chica = -1
        for idx in range(len(zs)):
            if uds_pz[p.id][zs[idx]] < MIN_UDS_OUT and (chica < 0 or uds_pz[p.id][zs[idx]] < uds_pz[p.id][zs[chica]]):
                chica = idx
        if chica < 0:
            break
        if chica == 0:
            destino = 1
        elif chica == len(zs) - 1:
            destino = chica - 1
        elif uds_pz[p.id][zs[chica - 1]] <= uds_pz[p.id][zs[chica + 1]]:
            destino = chica - 1
        else:
            destino = chica + 1
        de = zs[chica]
        a = zs[destino]
        uds_juntadas += uds_pz[p.id][de]
        uds_pz[p.id][a] += uds_pz[p.id][de]
        uds_pz[p.id][de] = 0.0
        for ml_id in mls_pz[p.id][de]:
            zona_ml[ml_id] = a
        mls_pz[p.id][a].extend(mls_pz[p.id][de])
        mls_pz[p.id][de] = []

# ---------------- 3. Plan por OUT ----------------------------------------------
datos_zona = {}
for zn in ZONAS:
    datos_zona[zn] = {'uds': 0.0, 'vol': 0.0, 'cajas': 0, 'outs': 0, 'huecos': {}, 'sitios': {}}
plan = []            # (p, uds_z, vol_z, huecos_z, tramo_z, principal, sin reserva, caja)
i = 0
for p in elegidas:
    uds_z = {}
    vol_z = {}
    huecos_z = {}
    sit_z = {}
    reservado = 0.0
    for ml in p.move_line_ids:
        if ml.id not in zona_ml:
            continue
        zn = zona_ml[ml.id]
        q = ml.product_uom_qty
        uds_z[zn] = uds_z.get(zn, 0.0) + q
        vol_z[zn] = vol_z.get(zn, 0.0) + q * (ml.product_id.volume or 0.0)
        huecos_z.setdefault(zn, {})[(ml.location_id.id, ml.product_id.id)] = 1
        s = sitio(ml.location_id)
        if s:
            sit_z.setdefault(zn, {})[s] = 1
            datos_zona[zn]['sitios'][s] = 1
        datos_zona[zn]['huecos'][(p.id, ml.location_id.id, ml.product_id.id)] = 1
        reservado += q
    demanda = 0.0
    for m in p.move_lines:
        if m.state not in ('done', 'cancel'):
            demanda += m.product_uom_qty
    principal = ''
    mejor = -1.0
    for zn in ZONAS:
        if uds_z.get(zn, 0.0) > mejor and uds_z.get(zn, 0.0) > 0:
            mejor = uds_z[zn]
            principal = zn
    tramo_z = {}
    for zn in sit_z:
        tramo_z[zn] = tramo_txt(sorted(sit_z[zn].keys()))
    for zn in uds_z:
        if uds_z[zn] > 0:
            datos_zona[zn]['uds'] += uds_z[zn]
            datos_zona[zn]['vol'] += vol_z[zn]
            datos_zona[zn]['outs'] += 1
            cj = int(vol_z[zn] / VOL_CAJA)
            if vol_z[zn] / VOL_CAJA - cj > 0.05:
                cj += 1
            datos_zona[zn]['cajas'] += max(cj, 1)
    plan.append((p, uds_z, vol_z, huecos_z, tramo_z, principal or ZONAS[0], demanda - reservado, i + 1))
    i += 1

existentes = Batch.search([('name', '=like', 'Z-%s-%%' % hoy)]).mapped('name')
prefijo = 'Z-%s-' % hoy
if existentes:
    n_r = 2
    hay = True
    while hay:
        hay = False
        for nb in existentes:
            if nb.startswith('Z-%s-R%d-' % (hoy, n_r)):
                hay = True
        if hay:
            n_r += 1
    prefijo = 'Z-%s-R%d-' % (hoy, n_r)

# ---------------- Resumen -------------------------------------------------------
lineas.append('KOROSHI PARTIR OUT ZONAS v11 PRUEBA 4 ZONAS CON MUELLE - %s' % MODO)
lineas.append('OUT: %d validas de %d | saltadas %d | agrupaciones %s<zona> (MU, A <=L%d, B L%d-L%d, C >L%d)' % (
    len(elegidas), len(IDS_OUT), len(saltadas), prefijo, LIMITE_A, LIMITE_A + 1, LIMITE_B, LIMITE_B))
lineas.append('')
tot_u = 0.0
tot_v = 0.0
tot_c = 0
for zn in ZONAS:
    d = datos_zona[zn]
    ss = sorted(d['sitios'].keys())
    tot_u += d['uds']
    tot_v += d['vol']
    tot_c += d['cajas']
    lineas.append('Zona %s | %s | %d uds | %d OUT | %d lecturas | %.2f m3 | ~%d cajas | %d sitios' % (
        zn, tramo_txt(ss), d['uds'], d['outs'], len(d['huecos']), d['vol'], d['cajas'], len(ss)))
lineas.append('TOTAL | %d uds | %.2f m3 | ~%d cajas (caja llena = %.3f m3) | uds juntadas con la zona de al lado: %d' % (
    tot_u, tot_v, tot_c, VOL_CAJA, uds_juntadas))
lineas.append('')
lineas.append('Caja | tienda | OUT | pedido | por zona: uds / m3 / cajas / lecturas / tramo (* = se queda la OUT original) | sin reserva')
n_nuevas = 0
for p, uds_z, vol_z, huecos_z, tramo_z, principal, sin_res, caja in plan:
    lineas.append('   %02d %s | %s | %s | sin reserva %d' % (caja, p.partner_id.name or '', p.name, p.origin or '', sin_res))
    for zn in ZONAS:
        if uds_z.get(zn, 0.0) <= 0:
            continue
        if zn != principal:
            n_nuevas += 1
        cj = vol_z[zn] / VOL_CAJA
        lineas.append('        %s%s: %d uds / %.3f m3 / %.1f cajas / %d lecturas / %s' % (
            zn, zn == principal and '*' or '', uds_z[zn], vol_z[zn], cj, len(huecos_z[zn]), tramo_z.get(zn, '')))
lineas.append('OUT nuevas que se crearan: %d | OUT en total: %d' % (n_nuevas, n_nuevas + len(plan)))
if saltadas:
    lineas.append('')
    lineas.append('Saltadas (%d):' % len(saltadas))
    for s in saltadas:
        lineas.append('   %s' % s)

if not elegidas:
    lineas.append('No hay OUT para partir.')
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
out_de = {}
uds_antes = {}
for p, uds_z, vol_z, huecos_z, tramo_z, principal, sin_res, caja in plan:
    total_p = 0.0
    for m in p.move_lines:
        if m.state not in ('done', 'cancel'):
            total_p += m.product_uom_qty
    uds_antes[p.id] = total_p
    out_de[(p.id, principal)] = p
    for zn in ZONAS:
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
        for zn in ZONAS:
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
    for zn in ZONAS:
        if (p.id, zn) not in out_de:
            continue
        o = out_de[(p.id, zn)]
        nl = prefijo + zn
        if nl not in lotes:
            lotes[nl] = Batch.create({'name': nl, 'company_id': COMPANY_ID, 'batch_type': 'normal'})
        o.write({
            'batch_id': lotes[nl].id,
            'note': '%s | CAJA %02d | %s | PEDIDO %s' % (nl, caja, p.partner_id.name or '', p.origin or ''),
        })
        todas_out |= o
for nl in lotes:
    lotes[nl].write({'state': 'in_progress'})
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

# ---------------- 5. Comprobaciones --------------------------------------------
fallos = []
despues = []
for p, uds_z, vol_z, huecos_z, tramo_z, principal, sin_res, caja in plan:
    total_d = 0.0
    for zn in ZONAS:
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
        fallos.append('%s %s: antes %d uds, despues %d' % (p.origin or '', p.name, uds_antes[p.id], total_d))

lineas.append('')
lineas.append('Despues de partir (OUT | zona | estado | uds reservadas | agrupacion):')
for d in despues:
    lineas.append(d)
lineas.append('OUT nuevas: %d | agrupaciones: %d | fallos: %d' % (len(todas_out) - len(plan), len(lotes), len(fallos)))
if fallos:
    lineas.append('')
    lineas.append('FALLOS:')
    for f in fallos[:60]:
        lineas.append('   %s' % f)
    lineas.insert(0, 'NO SE HA HECHO NADA (se ha deshecho todo)')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

if MODO != 'REAL':
    lineas.append('')
    lineas.append('SIMULACION: al lanzar este aviso Odoo deshace todo. Para hacerlo de verdad: MODO = REAL.')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

lineas[0] = 'KOROSHI PARTIR OUT ZONAS v11 PRUEBA - HECHO'
log('\n'.join(lineas), level='info')
action = {
    'type': 'ir.actions.act_window',
    'name': 'OUT por zonas %s (%d OUT)' % (prefijo, len(todas_out)),
    'res_model': 'stock.picking',
    'view_mode': 'tree,form',
    'domain': [('id', 'in', todas_out.ids)],
    'target': 'current',
}

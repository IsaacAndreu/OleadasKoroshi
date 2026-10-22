# KOROSHI - Deshacer el reparto de OUT por zonas (agrupaciones Z-ddmm-...)
# Devuelve todos los movimientos de las OUT nuevas a la OUT original de cada pedido (S-...),
# quita la agrupación y la nota de zona de la original, y borra las OUT nuevas vacías y las agrupaciones Z-.
# Acción de servidor sobre stock.picking (Odoo 13, safe_eval: sin f-strings, sin import, sin comprensiones).
#
# MODO = 'DIAGNOSTICO' -> no escribe nada, acaba con raise Warning
# MODO = 'REAL'        -> hace el cambio y deja el resultado en Registro (ir.logging), sin raise
#
# No hace nada si alguna OUT del reparto tiene unidades leídas o está hecha/cancelada.

MODO = 'DIAGNOSTICO'
PREFIJO = 'Z-2210-'
VACIAS = 'BORRAR'   # 'BORRAR' o 'DEJAR' (las OUT nuevas que se quedan sin movimientos)
COMPANY_ID = 8

ctx = dict(env.context)
ctx['allowed_company_ids'] = [COMPANY_ID]
Picking = env['stock.picking'].with_context(ctx)
Batch = env['stock.picking.batch'].with_context(ctx)

lotes = Batch.search([('name', '=like', PREFIJO + '%')], order='name')
pickings = Picking.search([('batch_id', 'in', lotes.ids)], order='id')

lineas = []
lineas.append('KOROSHI DESHACER ZONAS %s - %s' % (PREFIJO, MODO))
lineas.append('Agrupaciones: %s | OUT en ellas: %s' % (len(lotes), len(pickings)))

# Agrupar por pedido (origin). La OUT original es la de id más bajo.
por_origen = {}
orden_origenes = []
for p in pickings:
    o = p.origin or ('SIN ORIGEN %s' % p.name)
    if o not in por_origen:
        por_origen[o] = []
        orden_origenes.append(o)
    por_origen[o].append(p)

originales = Picking.browse()
nuevas = Picking.browse()
bloqueos = []
detalle = []
n_movs = 0
n_dup = 0
n_no_cuadra = 0
ud_total = 0.0
for o in orden_origenes:
    lista = por_origen[o]
    orig = lista[0]
    for p in lista:
        if p.id < orig.id:
            orig = p
    originales |= orig
    ud = 0.0
    hecho = 0.0
    productos = {}
    for p in lista:
        if p.state in ('done', 'cancel'):
            bloqueos.append('%s esta %s' % (p.name, p.state))
        if p.id != orig.id:
            nuevas |= p
        for m in p.move_lines:
            if m.state in ('done', 'cancel'):
                continue
            ud += m.product_uom_qty
            if p.id != orig.id:
                n_movs += 1
            productos[m.product_id.id] = productos.get(m.product_id.id, 0) + 1
        for ml in p.move_line_ids:
            hecho += ml.qty_done
    dup = 0
    for k in productos:
        if productos[k] > 1:
            dup += 1
    n_dup += dup
    if hecho > 0:
        bloqueos.append('%s (%s): %s uds ya leidas' % (o, orig.name, hecho))
    # Comprobar contra el pedido de venta (solo productos almacenables)
    pedido = 0.0
    if orig.sale_id:
        for sl in orig.sale_id.order_line:
            if sl.product_id.type == 'product':
                pedido += sl.product_uom_qty
    marca = ''
    if orig.sale_id and pedido != ud:
        marca = ' <-- NO CUADRA con pedido (%s)' % pedido
        n_no_cuadra += 1
    ud_total += ud
    detalle.append('%s | %s | %s OUT | %s uds | prod. repetidos %s%s' % (
        orig.name, o, len(lista), ud, dup, marca))

lineas.append('Pedidos: %s | OUT originales: %s | OUT nuevas: %s | movimientos a devolver: %s' % (
    len(orden_origenes), len(originales), len(nuevas), n_movs))
lineas.append('Uds totales: %s | pedidos que no cuadran: %s | productos repetidos tras juntar: %s' % (
    ud_total, n_no_cuadra, n_dup))

# Nota actual de la primera original (para ver qué se borra)
if originales:
    nota = originales[0].note or ''
    lineas.append('Nota de %s ahora: %s' % (originales[0].name, nota[:120]))

# Matrículas CJ ya reservadas para estas OUT (nota ETQ ZONA <OUT>)
nombres = {}
for p in pickings:
    nombres['ETQ ZONA %s' % p.name] = p.id
n_cj = 0
try:
    cjs = env['zebra.label'].search([('note', '=like', 'ETQ ZONA %')])
    for c in cjs:
        if (c.note or '') in nombres:
            n_cj += 1
    lineas.append('Matriculas CJ reservadas para estas OUT: %s' % n_cj)
except:
    lineas.append('No he podido mirar las CJ (zebra.label.note)')

if bloqueos:
    lineas.append('')
    lineas.append('BLOQUEOS (%s) - NO SE PUEDE DESHACER:' % len(bloqueos))
    for b in bloqueos[:40]:
        lineas.append('   %s' % b)

lineas.append('')
lineas.append('OUT original | pedido | OUT ahora | uds | repetidos')
for d in detalle:
    lineas.append('   %s' % d)

if MODO != 'REAL':
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

# ---------------- REAL ----------------
if bloqueos:
    log('\n'.join(lineas), level='info')
    raise Warning('NO SE HA HECHO NADA\n' + '\n'.join(lineas))

for o in orden_origenes:
    lista = por_origen[o]
    orig = lista[0]
    for p in lista:
        if p.id < orig.id:
            orig = p
    for p in lista:
        if p.id == orig.id:
            continue
        movs = p.move_lines.filtered(lambda m: m.state not in ('done', 'cancel'))
        p.move_line_ids.write({'picking_id': orig.id})
        movs.write({'picking_id': orig.id})

# Quitar la agrupación y la nota de zona de las originales
originales.write({'batch_id': False})
for p in originales:
    if (p.note or '').find(PREFIJO) >= 0:
        p.write({'note': False})

vacias = nuevas.filtered(lambda p: not p.move_lines)
n_vacias = len(vacias)
if VACIAS == 'BORRAR':
    vacias.write({'batch_id': False})
    vacias.unlink()
lotes_vacios = lotes.filtered(lambda b: not b.picking_ids)
n_lotes = len(lotes_vacios)
lotes_vacios.unlink()

lineas.insert(1, 'HECHO: OUT vacias %s (%s) | agrupaciones borradas %s' % (n_vacias, VACIAS, n_lotes))
log('\n'.join(lineas), level='info')

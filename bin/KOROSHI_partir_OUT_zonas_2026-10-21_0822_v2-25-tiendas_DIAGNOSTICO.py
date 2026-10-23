# =============================================================================
# KOROSHI - PARTIR LOS PEDIDOS DE TIENDA EN UNA OUT POR ZONA (SIN OLEADA, SIN U)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Cada operario coge SU zona con una caja por tienda; no pasa por el SORTER ni por la U.
#   1. Coge las OUT de tienda (PED. TIENDAS) creadas HOY, Preparadas, SIN NINGUNA unidad leida
#      y sin agrupacion o en la del dia (TIENDA dd-mm). Nunca toca las de una oleada B-KOR-...,
#      ni las de PENDIENTE TIENDA ni las de dias anteriores:
#      - si OUT_NOMBRES tiene nombres: solo esas;
#      - si se lanza desde la lista de albaranes con OUT seleccionadas: esas;
#      - si no: N_PEDIDOS, las mas grandes (ELEGIR = 'GRANDES') o las ultimas (ELEGIR = 'ULTIMAS').
#        Las demas se quedan como estan y se hacen individuales, como siempre.
#      Si hay mas de TIENDAS_POR_RONDA tiendas, se parten en rondas (Z-ddmm-R1-D1, Z-ddmm-R2-D1...).
#   2. Reparte los lineales en N_ZONAS zonas seguidas con el mismo tiempo de trabajo
#      (SEG_HUECO por hueco + SEG_UD por unidad + SEG_LINEAL por lineal). Lo que no esta
#      en un lineal (NAVE2...) va a la zona ZX.
#   3. Cada OUT se queda en la zona donde tiene mas unidades (con lo que no tiene reserva,
#      que pasa a pedido pendiente al validar, como ahora). Para cada otra zona se crea
#      una OUT nueva con el mismo Origen (pedido S-...) y se le pasan sus lineas reservadas.
#   4. Una agrupacion por zona Z-ddmm-D1, Z-ddmm-D2... (en borrador: es solo la lista del
#      operario, no es una oleada). En la nota de cada OUT: zona, numero de tienda y pedido.
#
# MODO = 'DIAGNOSTICO': NO escribe nada, solo calcula el reparto y lo ensena en un aviso.
# MODO = 'SIMULAR': parte las OUT de verdad, comprueba que cuadra y lanza un aviso que lo DESHACE TODO.
# MODO = 'REAL': lo hace.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
ZONA_HORARIA = 'Europe/Madrid'
N_PEDIDOS = 25                    # cuantas OUT (tiendas) se parten por zonas; el resto, individuales
ELEGIR = 'GRANDES'                # 'GRANDES': las N_PEDIDOS con mas uds reservadas. 'ULTIMAS': las ultimas
TIENDAS_POR_RONDA = 25            # cajas (tiendas) que lleva cada operario a la vez; mas tiendas = mas rondas
N_ZONAS = 5                       # operarios
OUT_NOMBRES = []                  # p. ej. ['EFFEC/OUT/20099', ...]. Vacio = ver arriba
PREFIJO_ZONA = 'Z-'               # agrupacion por zona: Z-ddmm-D1...
PREFIJO_AGRUPACION = 'TIENDA'     # se pueden coger OUT de la agrupacion del dia (TIENDA dd-mm) si no estan empezadas
SEG_HUECO = 20                    # segundos por hueco (llegar, leer, coger)
SEG_UD = 4                        # segundos por unidad
SEG_LINEAL = 15                   # segundos por lineal (andar)
MODO = 'DIAGNOSTICO'              # 'DIAGNOSTICO' (no escribe), 'SIMULAR' (hace y deshace) o 'REAL'
# -----------------------------------------------------------------------------

DIAGNOSTICO = MODO == 'DIAGNOSTICO'
if MODO not in ('DIAGNOSTICO', 'SIMULAR', 'REAL'):
    log('KOROSHI PARTIR OUT ZONAS - MODO desconocido: %s' % MODO)
    raise Warning("MODO tiene que ser 'DIAGNOSTICO', 'SIMULAR' o 'REAL'")

ahora_local = datetime.datetime.now(timezone(ZONA_HORARIA))
hoy = ahora_local.strftime('%d%m')
medianoche_local = timezone(ZONA_HORARIA).localize(datetime.datetime(ahora_local.year, ahora_local.month, ahora_local.day))
desde_dt = medianoche_local.astimezone(timezone('UTC')).replace(tzinfo=None)
desde = desde_dt.strftime('%Y-%m-%d %H:%M:%S')
sorter = env['stock.location'].search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)

# ---------------- 1. OUT a partir ---------------------------------------------
errores = []
explicitas = False
if OUT_NOMBRES:
    candidatas = env['stock.picking'].search([('name', 'in', OUT_NOMBRES), ('company_id', '=', COMPANY_ID)], order='name desc')
    explicitas = True
elif env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    candidatas = env['stock.picking'].browse(env.context.get('active_ids')).sorted('name', reverse=True)
    explicitas = True
else:
    candidatas = env['stock.picking'].search([
        ('company_id', '=', COMPANY_ID),
        ('picking_type_code', '=', 'outgoing'),
        ('state', '=', 'assigned'),
        ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO),
        ('create_date', '>=', desde),
        '|', ('batch_id', '=', False), ('batch_id.name', '=like', PREFIJO_AGRUPACION + '%'),
    ], order='name desc', limit=200)

validas = []          # (uds reservadas, id)
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
    elif p.create_date < desde_dt:
        motivo = 'es de un dia anterior'
    elif p.batch_id and not (p.batch_id.name or '').startswith(PREFIJO_AGRUPACION):
        motivo = 'esta en la agrupacion %s' % p.batch_id.name
    elif sorter and p.location_id.id == sorter.id:
        motivo = 'sale del SORTER (es de una oleada)'
    else:
        for ml in p.move_line_ids:
            if ml.qty_done > 0:
                motivo = 'ya tiene unidades leidas (la estan cogiendo)'
                break
            if not ml.move_id:
                motivo = 'tiene lineas sin movimiento (escaneos de la PDA)'
                break
    if motivo:
        saltadas.append('%s (%s): %s' % (p.name, p.origin or '', motivo))
        if explicitas:
            errores.append('%s: %s' % (p.name, motivo))
    else:
        uds_p = 0.0
        for ml in p.move_line_ids:
            uds_p += ml.product_uom_qty
        validas.append((uds_p, p.id))

# Eleccion: explicitas todas; si no, las mas grandes o las ultimas (la busqueda viene por nombre desc)
if explicitas:
    if len(validas) > N_PEDIDOS:
        errores.append('Hay %d OUT y el maximo es %d (N_PEDIDOS)' % (len(validas), N_PEDIDOS))
    ids_elegidas = []
    for v in validas:
        ids_elegidas.append(v[1])
elif ELEGIR == 'GRANDES':
    ids_elegidas = []
    for v in sorted(validas, reverse=True):
        if len(ids_elegidas) < N_PEDIDOS:
            ids_elegidas.append(v[1])
else:
    ids_elegidas = []
    for v in validas:
        if len(ids_elegidas) < N_PEDIDOS:
            ids_elegidas.append(v[1])
individuales = []
for v in validas:
    if v[1] not in ids_elegidas:
        individuales.append(v)

# numero de tienda 01, 02... por orden de OUT, dentro de cada ronda
elegidas = env['stock.picking'].browse(ids_elegidas).sorted('name')
ronda_de = {}
seq_de = {}
n_rondas = 0
i = 0
for p in elegidas:
    ronda_de[p.id] = i // TIENDAS_POR_RONDA + 1
    seq_de[p.id] = i % TIENDAS_POR_RONDA + 1
    n_rondas = ronda_de[p.id]
    i += 1
if not elegidas:
    errores.append('No hay OUT de tienda para partir')
prefijo_ronda = {}   # ronda -> 'Z-ddmm-' o 'Z-ddmm-R1-'
for r in range(1, n_rondas + 1):
    prefijo_ronda[r] = n_rondas > 1 and ('%s%s-R%d-' % (PREFIJO_ZONA, hoy, r)) or ('%s%s-' % (PREFIJO_ZONA, hoy))
if not DIAGNOSTICO:
    n_ya = env['stock.picking.batch'].search_count([('name', '=like', '%s%s-%%' % (PREFIJO_ZONA, hoy))])
    if n_ya:
        errores.append('Ya existen agrupaciones %s%s-...: borralas o cambia PREFIJO_ZONA' % (PREFIJO_ZONA, hoy))

if errores:
    log('KOROSHI PARTIR OUT ZONAS - ABORTADO\n' + '\n'.join(errores))
    raise Warning('PARTIR OUT POR ZONAS - NO SE HA HECHO NADA\n\n' + '\n'.join(errores))

# ---------------- 2. Lineas reservadas y zonas --------------------------------
# lineas: (ml, out, lineal, hueco)
lineas = []
por_lineal = {}      # lineal -> [uds, {huecos}]
for p in elegidas:
    for ml in p.move_line_ids:
        if ml.product_uom_qty <= 0:
            continue
        lineal = 0
        hueco = ''
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
                lineal = int(num)
                hueco = texto
                break
        lineas.append((ml, p, lineal, hueco))
        if lineal:
            if lineal not in por_lineal:
                por_lineal[lineal] = [0.0, {}]
            por_lineal[lineal][0] += ml.product_uom_qty
            por_lineal[lineal][1][hueco] = 1

lineales = sorted(por_lineal.keys())
trabajo = {}
total_seg = 0.0
for l in lineales:
    trabajo[l] = SEG_HUECO * len(por_lineal[l][1]) + SEG_UD * por_lineal[l][0] + SEG_LINEAL
    total_seg += trabajo[l]
objetivo = total_seg / N_ZONAS
zona_de = {}
n_zona = 1
acumulado = 0.0
for l in lineales:
    if acumulado >= objetivo * 0.98 and n_zona < N_ZONAS:
        n_zona += 1
        acumulado = 0.0
    zona_de[l] = 'D%d' % n_zona
    acumulado += trabajo[l]
nombres_zona = []
for i in range(1, n_zona + 1):
    nombres_zona.append('D%d' % i)
nombres_zona.append('ZX')

# uds por OUT y zona
reparto = {}         # out.id -> {zona: uds}
for t in lineas:
    z = t[2] and zona_de[t[2]] or 'ZX'
    if t[1].id not in reparto:
        reparto[t[1].id] = {}
    reparto[t[1].id][z] = reparto[t[1].id].get(z, 0.0) + t[0].product_uom_qty

# zona que se queda la OUT original: la de mas unidades (ZX solo si no tiene otra)
zona_original = {}
for p in elegidas:
    mejor = ''
    mejor_u = 0.0
    for z in nombres_zona:
        u = reparto.get(p.id, {}).get(z, 0.0)
        if z != 'ZX' and u > mejor_u:
            mejor = z
            mejor_u = u
    if not mejor:
        mejor = reparto.get(p.id, {}).get('ZX', 0.0) > 0 and 'ZX' or 'D1'
    zona_original[p.id] = mejor

# ---------------- 3. Partir (solo si DIAGNOSTICO = False) ----------------------
agrupacion = {}      # (ronda, zona) -> agrupacion Z-...
nuevas = {}          # (out.id, zona) -> picking
if not DIAGNOSTICO:
    for r in range(1, n_rondas + 1):
        for z in nombres_zona:
            agrupacion[(r, z)] = env['stock.picking.batch'].create({
                'name': prefijo_ronda[r] + z, 'company_id': COMPANY_ID, 'batch_type': 'normal'})
    for p in elegidas:
        seq = seq_de[p.id]
        ronda = ronda_de[p.id]
        tienda = p.partner_id and p.partner_id.name or ''
        z0 = zona_original[p.id]
        # lineas de cada move por zona
        por_move = {}
        for t in lineas:
            if t[1].id != p.id:
                continue
            z = t[2] and zona_de[t[2]] or 'ZX'
            if z == z0 or not t[0].move_id:
                continue
            clave = (t[0].move_id.id, z)
            if clave not in por_move:
                por_move[clave] = []
            por_move[clave].append(t[0])
        for clave in por_move:
            move = env['stock.move'].browse(clave[0])
            z = clave[1]
            if (p.id, z) not in nuevas:
                nuevas[(p.id, z)] = p.copy({
                    'move_lines': [], 'move_ids_without_package': [], 'move_line_ids': [],
                    'move_line_ids_without_package': [], 'origin': p.origin,
                    'batch_id': agrupacion[(ronda, z)].id,
                    'note': '%s%s | CAJA %02d | %s | PEDIDO %s | sale de %s' % (prefijo_ronda[ronda], z, seq, tienda, p.origin or '', p.name)})
            nueva = nuevas[(p.id, z)]
            mls = env['stock.move.line']
            qty = 0.0
            for ml in por_move[clave]:
                mls |= ml
                qty += ml.product_uom_qty
            if qty >= move.product_uom_qty and len(mls) == len(move.move_line_ids):
                # el move entero es de esta zona: se cambia de OUT
                move.write({'picking_id': nueva.id})
                mls.write({'picking_id': nueva.id})
            else:
                # parte del move: move nuevo con esas uds y sus lineas reservadas (sin fusionar)
                nuevo = move.copy({'picking_id': nueva.id, 'product_uom_qty': qty, 'move_line_ids': []})
                nuevo._action_confirm(merge=False)
                mls.write({'move_id': nuevo.id, 'picking_id': nueva.id})
                move.with_context(do_not_unreserve=True).write({'product_uom_qty': move.product_uom_qty - qty})
                (move | nuevo)._recompute_state()
        p.write({'batch_id': agrupacion[(ronda, z0)].id,
                 'note': '%s%s | CAJA %02d | %s | PEDIDO %s' % (prefijo_ronda[ronda], z0, seq, tienda, p.origin or '')})
    for clave in agrupacion:
        if not agrupacion[clave].picking_ids:
            agrupacion[clave].unlink()

# ---------------- 4. Resumen ---------------------------------------------------
titulo = {'DIAGNOSTICO': 'DIAGNOSTICO (NO SE HA ESCRITO NADA)', 'SIMULAR': 'SIMULACION (SE HA DESHECHO TODO)', 'REAL': 'HECHO'}
texto = ['KOROSHI PARTIR OUT ZONAS - ' + titulo[MODO],
         'OUT de tienda: %d | lineas reservadas: %d' % (len(elegidas), len(lineas)), '']
for z in nombres_zona:
    l_z = []
    u_z = 0.0
    seg_z = 0.0
    for l in lineales:
        if zona_de[l] == z:
            l_z.append(l)
            seg_z += trabajo[l]
    outs_z = 0
    for p in elegidas:
        u = reparto.get(p.id, {}).get(z, 0.0)
        if u > 0:
            outs_z += 1
            u_z += u
    if not outs_z:
        continue
    tramo = l_z and ('L%d-L%d' % (l_z[0], l_z[-1])) or 'fuera de lineal'
    texto.append('Zona %s | %s | %d uds | %d OUT (cajas) | ~%d min' % (z, tramo, u_z, outs_z, seg_z / 60))
texto.append('Rondas: %d (%d tiendas por ronda). Agrupaciones: %s<zona>' % (
    n_rondas, TIENDAS_POR_RONDA, n_rondas > 1 and ('%s%s-R<n>-' % (PREFIJO_ZONA, hoy)) or ('%s%s-' % (PREFIJO_ZONA, hoy))))
texto.append('')
texto.append('Caja | tienda | OUT | pedido | uds por zona (* = se queda la OUT original) | sin reserva')
for p in elegidas:
    seq = seq_de[p.id]
    pedido = 0.0
    reservado = 0.0
    for m in p.move_lines:
        if m.state != 'cancel':
            pedido += m.product_uom_qty
    partes = []
    for z in nombres_zona:
        u = reparto.get(p.id, {}).get(z, 0.0)
        if u > 0:
            reservado += u
            partes.append('%s%s:%d' % (z, z == zona_original[p.id] and '*' or '', u))
    texto.append('   %s%02d %s | %s | %s | %s | %d' % (
        n_rondas > 1 and ('R%d-' % ronda_de[p.id]) or '', seq, p.partner_id and p.partner_id.name or '',
        p.name, p.origin or '', '  '.join(partes), pedido - reservado))
if individuales:
    texto.append('')
    texto.append('Se quedan individuales (no se tocan): %d' % len(individuales))
    for v in individuales:
        o = env['stock.picking'].browse(v[1])
        texto.append('   %s | %s | %d uds' % (o.name, o.partner_id and o.partner_id.name or '', v[0]))
if not DIAGNOSTICO:
    # Comprobacion: lo reservado de cada pedido (original + nuevas) tiene que ser lo mismo que antes
    texto.append('')
    texto.append('Despues de partir (OUT | zona | estado | uds reservadas):')
    descuadres = 0
    for p in elegidas:
        antes = 0.0
        for z in reparto.get(p.id, {}):
            antes += reparto[p.id][z]
        despues = 0.0
        grupo = [(p, zona_original[p.id])]
        for clave in nuevas:
            if clave[0] == p.id:
                grupo.append((nuevas[clave], clave[1]))
        for g in grupo:
            res_g = 0.0
            for ml in g[0].move_line_ids:
                res_g += ml.product_uom_qty
            despues += res_g
            texto.append('   %s | %s | %s | %d uds | %s' % (g[0].name, g[1], g[0].state, res_g, g[0].batch_id.name or ''))
        if abs(antes - despues) > 0.001:
            descuadres += 1
            texto.append('   OJO %s: antes %d uds reservadas, despues %d' % (p.name, antes, despues))
    texto.append('OUT nuevas: %d | pedidos que no cuadran: %d' % (len(nuevas), descuadres))
if saltadas:
    texto.append('')
    texto.append('Saltadas: %d (las primeras 15)' % len(saltadas))
    n = 0
    for s in saltadas:
        n += 1
        if n > 15:
            break
        texto.append('   ' + s)
mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + "\n\nEs un diagnostico: no se ha escrito nada. Siguiente paso: MODO = 'SIMULAR'.")
if MODO == 'SIMULAR':
    raise Warning(mensaje + "\n\nEs una simulacion: Odoo deshace todo. Para hacerlo de verdad: MODO = 'REAL'.")

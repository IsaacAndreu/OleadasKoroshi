# =============================================================================
# KOROSHI - REPARTIR OUT EN INT POR ZONA - DIAGNOSTICO (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Simula lo que hara la accion real (KOROSHI_crear_INT_zonas.py):
#   1. OUT a repartir: las seleccionadas en la lista (Accion > ...) o, si no hay
#      seleccion, las OUT de tienda (PED. TIENDAS) preparadas, sin agrupacion,
#      sin backorder y sin nada leido.
#   2. Cada linea reservada se clasifica en una ZONA segun su ubicacion
#      (lado izquierdo P01-P17 / derecho P18-P36 y tramo de lineales).
#   3. Por zona se crean INT de como maximo MAX_UDS_INT uds, en trozos iguales y
#      en orden de recorrido. Cada INT: EFFEC/Stock -> SORTER, un movimiento por
#      producto y ubicacion, con origen = el hueco exacto donde estaba reservada
#      la OUT (asi el INT reserva del mismo sitio).
#   4. Las OUT pasarian a tener origen SORTER y se les quitaria la reserva
#      (quedan en espera hasta que se validan los INT).
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
MAX_UDS_INT = 500
# Zonas: (nombre, lado, lineal desde, lineal hasta). Lado 'I' = P01-P17, 'D' = P18-P36.
ZONAS = [
    ('Z1', 'I', 1, 79),
    ('Z2', 'I', 80, 136),
    ('Z3', 'D', 1, 83),
    ('Z4', 'D', 84, 95),
    ('Z5', 'D', 96, 136),
]
ZONA_OTRAS = 'ZX'                # lineas en ubicaciones sin lineal (MU, etc.)
# Simulacion con albaranes concretos (ids). Con SIMULAR_HECHAS se aceptan OUT ya
# validadas y se usa la cantidad hecha y el hueco del que salio cada linea.
IDS_SIMULAR = []
SIMULAR_HECHAS = False
MAX_OUT_SIN_SELECCION = 300
MOSTRAR_LINEAS_POR_INT = 0       # >0 = ensena las primeras N lineas de cada INT
MAX_LINEAS_MENSAJE = 250
# -----------------------------------------------------------------------------

lineas = []
lineas.append('REPARTIR OUT EN INT POR ZONA - DIAGNOSTICO - NO SE HA CREADO NADA')

sorter = env['stock.location'].search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)
stock_loc = env['stock.location'].search([('barcode', '=', 'EFFEC-STOCK'), ('company_id', '=', COMPANY_ID)], limit=1)
tipo_int = env['stock.picking.type'].search([('barcode', '=', 'EFFEC-INTERNAL'), ('company_id', '=', COMPANY_ID)], limit=1)
lineas.append('INT: %s | %s -> %s' % (tipo_int.display_name or 'NO EXISTE', stock_loc.complete_name or 'NO EXISTE',
                                      sorter.complete_name or 'NO EXISTE'))

# ---------------- 1. OUT a repartir ------------------------------------------
if IDS_SIMULAR:
    candidatos = env['stock.picking'].browse(IDS_SIMULAR).exists()
    origen_sel = 'ids de IDS_SIMULAR (%d)' % len(candidatos)
elif env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    candidatos = env['stock.picking'].browse(env.context.get('active_ids'))
    origen_sel = 'seleccion (%d)' % len(candidatos)
else:
    candidatos = env['stock.picking'].search([
        ('company_id', '=', COMPANY_ID),
        ('picking_type_code', '=', 'outgoing'),
        ('state', '=', 'assigned'),
        ('batch_id', '=', False),
        ('backorder_id', '=', False),
    ], order='name asc', limit=MAX_OUT_SIN_SELECCION)
    origen_sel = 'busqueda automatica (%d)' % len(candidatos)
lineas.append('OUT candidatas: %s' % origen_sel)

validas = env['stock.picking']
descartes = {}
for p in candidatos:
    motivo = ''
    tipo = p.sale_id and p.sale_id.s_order_type_id and p.sale_id.s_order_type_id.name or ''
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing':
        motivo = 'no es OUT de la empresa %d' % COMPANY_ID
    elif tipo != TIPO_PEDIDO:
        motivo = 'tipo de pedido %s' % (tipo or 'sin tipo')
    elif SIMULAR_HECHAS and p.state in ('assigned', 'done'):
        motivo = ''
    elif p.state != 'assigned':
        motivo = 'no esta Preparada (%s)' % p.state
    elif p.batch_id:
        motivo = 'ya esta en la agrupacion %s' % p.batch_id.name
    elif p.backorder_id:
        motivo = 'es un backorder'
    elif sorter and p.location_id.id == sorter.id:
        motivo = 'ya sale del SORTER'
    else:
        for ml in p.move_line_ids:
            if ml.qty_done > 0:
                motivo = 'ya tiene unidades leidas'
                break
    if motivo:
        descartes[motivo] = descartes.get(motivo, 0) + 1
    else:
        validas |= p

# ---------------- 2. Lineas por zona -----------------------------------------
por_zona = {}      # zona -> lista de (pasillo, pos, lineal, nivel, ubicacion, producto, uds, out)
lineas_en_sorter = 0
uds_en_sorter = 0.0
for p in validas:
    for ml in p.move_line_ids:
        if p.state == 'done':
            qty = ml.qty_done
        else:
            qty = ml.product_uom_qty
        if qty <= 0:
            continue
        if sorter and ml.location_id.id == sorter.id:
            # Ya salio del SORTER: no se sabe de que hueco, no entra en ningun INT
            lineas_en_sorter += 1
            uds_en_sorter += qty
            continue
        lineal = 0
        pos = 0
        nivel = 0
        segmentos = (ml.location_id.complete_name or '').split('/')
        for idx in range(len(segmentos) - 1, -1, -1):
            texto = segmentos[idx].strip()
            if ' - ' in texto:
                texto = texto.split(' - ', 1)[1]
            if len(texto) > 1 and texto[0] == 'L' and texto[1].isdigit():
                partes = texto.split(' ')
                for parte in partes:
                    num = ''
                    for ch in parte[1:]:
                        if ch.isdigit():
                            num += ch
                        else:
                            break
                    if num and parte[0] == 'L':
                        lineal = int(num)
                    elif num and parte[0] == 'P':
                        pos = int(num)
                    elif num and parte[0] == 'C':
                        nivel = int(num)
                break
        zona = ZONA_OTRAS
        if lineal:
            # P00 (cabecera del lineal) va con el lado izquierdo, como P01-P17
            lado = pos <= 17 and 'I' or 'D'
            for z in ZONAS:
                if z[1] == lado and z[2] <= lineal <= z[3]:
                    zona = z[0]
                    break
        if zona not in por_zona:
            por_zona[zona] = []
        por_zona[zona].append((lineal // 2, pos, lineal, nivel, ml.location_id, ml.product_id, qty, p))

# ---------------- 3. INT por zona en trozos iguales ---------------------------
ints = []   # dicts: nombre, zona, lineas (lista), uds
orden_zonas = []
for z in ZONAS:
    orden_zonas.append(z[0])
orden_zonas.append(ZONA_OTRAS)
for zona in orden_zonas:
    sel = por_zona.get(zona, [])
    if not sel:
        continue
    sel = sorted(sel, key=lambda x: (x[0], x[1], x[2], x[3]))
    total_zona = 0.0
    for x in sel:
        total_zona += x[6]
    n_trozos = int(total_zona // MAX_UDS_INT)
    if n_trozos * MAX_UDS_INT < total_zona:
        n_trozos += 1
    if n_trozos < 1:
        n_trozos = 1
    objetivo = total_zona / n_trozos
    trozos = []
    actual = []
    uds_act = 0.0
    for x in sel:
        if actual and uds_act + x[6] > objetivo + 0.5 and len(trozos) < n_trozos - 1:
            trozos.append(actual)
            actual = []
            uds_act = 0.0
        actual.append(x)
        uds_act += x[6]
    if actual:
        trozos.append(actual)
    letras = 'abcdefghijklmnopqrstuvwxyz'
    for i in range(len(trozos)):
        t = trozos[i]
        uds_t = 0.0
        movs = {}
        outs_t = {}
        lin_min = 9999
        lin_max = 0
        for x in t:
            uds_t += x[6]
            movs[(x[5].id, x[4].id)] = movs.get((x[5].id, x[4].id), 0.0) + x[6]
            outs_t[x[7].id] = 1
            if x[2] and x[2] < lin_min:
                lin_min = x[2]
            if x[2] > lin_max:
                lin_max = x[2]
        ints.append({'nombre': '%s-%s' % (zona, letras[i]), 'zona': zona, 'lineas': t, 'uds': uds_t,
                     'movs': len(movs), 'outs': len(outs_t),
                     'tramo': lin_max and ('L%02d-L%02d' % (lin_min, lin_max)) or 'sin lineal'})

# ----------------------------- MENSAJE ---------------------------------------
total_uds = 0.0
for i in ints:
    total_uds += i['uds']
lineas.append('OUT a repartir: %d | uds: %d | INT que se crearian: %d (max %d uds por INT)'
              % (len(validas), total_uds, len(ints), MAX_UDS_INT))
for k in sorted(descartes.keys()):
    lineas.append('   Descartadas, %s: %d' % (k, descartes[k]))
if lineas_en_sorter:
    lineas.append('   Lineas que ya salian del SORTER (no entran en ningun INT): %d (%d uds)' % (lineas_en_sorter, uds_en_sorter))

lineas.append('')
lineas.append('ZONAS')
for z in ZONAS:
    uds_z = 0.0
    n_z = 0
    for i in ints:
        if i['zona'] == z[0]:
            uds_z += i['uds']
            n_z += 1
    lineas.append('   %s: %s, L%02d-L%02d | %d uds | %d INT'
                  % (z[0], z[1] == 'I' and 'izquierda P01-P17' or 'derecha P18-P36', z[2], z[3], uds_z, n_z))
uds_otras = 0.0
for i in ints:
    if i['zona'] == ZONA_OTRAS:
        uds_otras += i['uds']
if uds_otras:
    lineas.append('   %s: ubicaciones sin lineal (MU, etc.) | %d uds' % (ZONA_OTRAS, uds_otras))

lineas.append('')
lineas.append('INT: nombre | tramo | uds | movimientos | lineas | OUT implicadas')
for i in ints:
    lineas.append('   %s | %s | %d | %d | %d | %d' % (i['nombre'], i['tramo'], i['uds'], i['movs'], len(i['lineas']), i['outs']))
    if MOSTRAR_LINEAS_POR_INT:
        for x in i['lineas'][:MOSTRAR_LINEAS_POR_INT]:
            lineas.append('      %s | %s | %d | %s' % (x[4].name, x[5].default_code or x[5].name, x[6], x[7].name))

lineas.append('')
lineas.append('La accion real: crearia estos INT (EFFEC/Stock -> SORTER, origen de cada movimiento = su hueco),')
lineas.append('quitaria la reserva de las %d OUT, les pondria origen SORTER y reservaria los INT.' % len(validas))

texto_completo = '\n'.join(lineas)
log('KOROSHI REPARTIR INT ZONAS DIAGNOSTICO\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

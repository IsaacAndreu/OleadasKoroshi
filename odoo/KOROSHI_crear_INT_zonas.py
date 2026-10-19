# =============================================================================
# KOROSHI - REPARTIR OUT EN INT POR ZONA - ACCION REAL (ESCRIBE EN ODOO)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
# Se lanza desde la lista de albaranes: seleccionar las OUT > Accion > ...
#
# Hace lo mismo que el diagnostico (KOROSHI_crear_INT_zonas_DIAGNOSTICO.py), pero de verdad:
#   1. Comprueba TODAS las OUT seleccionadas. Si alguna no vale, no hace nada y avisa.
#   2. Quita la reserva de las OUT (asi quedan libres las unidades de los huecos).
#   3. Crea los INT por zona (max MAX_UDS_INT uds, trozos iguales, orden de recorrido):
#      EFFEC/Stock -> SORTER, un movimiento por producto y hueco, con origen = el hueco
#      exacto donde estaba reservada la OUT.
#   4. Confirma y reserva los INT y comprueba que cada movimiento queda reservado
#      entero y del mismo hueco. Si no, deshace TODO (no queda nada a medias).
#   5. Pone origen SORTER a las OUT, que quedan en espera hasta que se validen los INT.
#      Despues: validar los INT y hacer "Comprobar disponibilidad" en las OUT.
# Todo va en una sola transaccion: cualquier error deja Odoo como estaba.
# Al acabar abre la lista de los INT creados.
#
# MODO PLANIFICADO (para usarla como accion planificada, sin seleccion):
#   con MODO_PLANIFICADO = True busca sola las OUT de tienda entradas en las ultimas
#   PLAN_HORAS horas que se pueden repartir y coge las PLAN_MAX_OUT mas pequenas.
#   Las que no valen se saltan (no se para). El resultado queda en el registro
#   (Ajustes > Tecnico > Registros), en el chat de cada OUT y en el origen de los INT (KOR-...).
#
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
MAX_UDS_INT = 500
ZONAS = [
    ('Z1', 'I', 1, 79),
    ('Z2', 'I', 80, 136),
    ('Z3', 'D', 1, 83),
    ('Z4', 'D', 84, 95),
    ('Z5', 'D', 96, 136),
]
ZONA_OTRAS = 'ZX'                # huecos sin lineal (MU, cajas sueltas...): van en su propio INT
# Para la prueba: ids de OUT concretas. Vacio = las OUT seleccionadas en la lista.
IDS_PRUEBA = []
MAX_OUT = 80                     # tope de OUT por ejecucion
PREFIJO = 'KOR'
# Modo planificado (accion planificada): elige sola las OUT
MODO_PLANIFICADO = False
PLAN_MAX_OUT = 3                 # cuantas OUT coge (las mas pequenas)
PLAN_HORAS = 10                  # OUT creadas en las ultimas N horas
# -----------------------------------------------------------------------------

errores = []
sorter = env['stock.location'].search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)
stock_loc = env['stock.location'].search([('barcode', '=', 'EFFEC-STOCK'), ('company_id', '=', COMPANY_ID)], limit=1)
tipo_int = env['stock.picking.type'].search([('barcode', '=', 'EFFEC-INTERNAL'), ('company_id', '=', COMPANY_ID)], limit=1)
if not sorter:
    errores.append('No existe la ubicacion SORTER')
if not stock_loc:
    errores.append('No existe la ubicacion EFFEC/Stock')
if not tipo_int:
    errores.append('No existe el tipo de operacion EFFEC-INTERNAL')

# ---------------- 1. OUT seleccionadas y comprobaciones -----------------------
if IDS_PRUEBA:
    outs = env['stock.picking'].browse(IDS_PRUEBA).exists()
elif env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    outs = env['stock.picking'].browse(env.context.get('active_ids'))
elif MODO_PLANIFICADO:
    desde = (datetime.datetime.now() - datetime.timedelta(hours=PLAN_HORAS)).strftime('%Y-%m-%d %H:%M:%S')
    outs = env['stock.picking'].search([
        ('company_id', '=', COMPANY_ID),
        ('picking_type_code', '=', 'outgoing'),
        ('state', '=', 'assigned'),
        ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO),
        ('create_date', '>=', desde),
        ('batch_id', '=', False),
        ('backorder_id', '=', False),
        ('name', 'not like', '-O'),
    ], order='name asc', limit=200)
else:
    outs = env['stock.picking']
if not outs and not MODO_PLANIFICADO:
    errores.append('No hay OUT seleccionadas (o IDS_PRUEBA vacio)')
if len(outs) > MAX_OUT and not MODO_PLANIFICADO:
    errores.append('Hay %d OUT seleccionadas y el maximo es %d' % (len(outs), MAX_OUT))

validas = []      # modo planificado: (uds, out) de las que se pueden repartir
saltadas = []
for p in outs:
    motivo = ''
    tipo = p.sale_id and p.sale_id.s_order_type_id and p.sale_id.s_order_type_id.name or ''
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing':
        motivo = 'no es una OUT de la empresa %d' % COMPANY_ID
    elif tipo != TIPO_PEDIDO:
        motivo = 'tipo de pedido %s' % (tipo or 'sin tipo')
    elif p.state != 'assigned':
        motivo = 'no esta Preparada (%s)' % p.state
    elif p.batch_id:
        motivo = 'esta en la agrupacion %s' % p.batch_id.name
    elif sorter and p.location_id.id == sorter.id:
        motivo = 'ya sale del SORTER'
    else:
        for m in p.move_lines:
            if m.state not in ('assigned', 'cancel', 'done'):
                motivo = 'no esta reservada entera (%s)' % m.product_id.display_name
                break
        if not motivo:
            for ml in p.move_line_ids:
                if ml.qty_done > 0:
                    motivo = 'ya tiene unidades leidas'
                    break
                if sorter and ml.location_id.id == sorter.id:
                    motivo = 'tiene lineas reservadas en el SORTER'
                    break
    if MODO_PLANIFICADO:
        if motivo:
            saltadas.append('%s: %s' % (p.name, motivo))
        else:
            uds_p = 0.0
            for m in p.move_lines:
                uds_p += m.product_uom_qty
            validas.append((uds_p, p.id))
    elif motivo:
        errores.append('%s: %s' % (p.name, motivo))

if MODO_PLANIFICADO:
    # Se cogen las mas pequenas, para la prueba
    validas = sorted(validas, key=lambda x: (x[0], x[1]))
    elegidas = []
    for v in validas[:PLAN_MAX_OUT]:
        elegidas.append(v[1])
    outs = env['stock.picking'].browse(elegidas)
    texto_plan = 'KOROSHI REPARTIR INT ZONAS - PLANIFICADA: %d candidatas, %d validas, elegidas: %s' % (
        len(validas) + len(saltadas), len(validas), ', '.join(outs.mapped('name')) or 'ninguna')
    if saltadas:
        texto_plan += '\nSaltadas:\n' + '\n'.join(saltadas[:40])
    log(texto_plan)

if errores:
    texto = 'REPARTIR INT POR ZONA - NO SE HA HECHO NADA\n\n' + '\n'.join(errores)
    log('KOROSHI REPARTIR INT ZONAS - ABORTADO\n%s' % texto)
    raise Warning(texto)

# ---------------- 2. Lineas reservadas por zona -------------------------------
# Se leen ANTES de quitar la reserva: (pasillo, posicion, lineal, nivel, ubicacion, producto, uds, out)
por_zona = {}
for p in outs:
    for ml in p.move_line_ids:
        qty = ml.product_uom_qty
        if qty <= 0:
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
                for parte in texto.split(' '):
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

# ---------------- 3. Trozos iguales por zona (igual que el diagnostico) -------
orden_zonas = []
for z in ZONAS:
    orden_zonas.append(z[0])
orden_zonas.append(ZONA_OTRAS)
letras = 'abcdefghijklmnopqrstuvwxyz'
hoy = datetime.date.today().strftime('%d%m')
trozos_int = []   # (etiqueta, lista de lineas)
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
    for i in range(len(trozos)):
        trozos_int.append(('%s-%s-%s-%s' % (PREFIJO, hoy, zona, letras[i]), trozos[i]))

# ---------------- 4. Quitar la reserva de las OUT ----------------------------
outs.do_unreserve()

# ---------------- 5. Crear, confirmar y reservar los INT ----------------------
ints = env['stock.picking']
resumen = []
for etiqueta, lineas_t in trozos_int:
    # Un movimiento por (producto, hueco)
    movs = {}
    orden_movs = []
    uds_t = 0.0
    outs_t = {}
    for x in lineas_t:
        clave = (x[5].id, x[4].id)
        if clave not in movs:
            movs[clave] = [x[5], x[4], 0.0]
            orden_movs.append(clave)
        movs[clave][2] += x[6]
        uds_t += x[6]
        outs_t[x[7].id] = 1
    picking = env['stock.picking'].create({
        'picking_type_id': tipo_int.id,
        'location_id': stock_loc.id,
        'location_dest_id': sorter.id,
        'company_id': COMPANY_ID,
        'origin': etiqueta,
    })
    for clave in orden_movs:
        producto = movs[clave][0]
        hueco = movs[clave][1]
        movimiento = env['stock.move'].create({
            'name': producto.display_name,
            'picking_id': picking.id,
            'picking_type_id': tipo_int.id,
            'company_id': COMPANY_ID,
            'product_id': producto.id,
            'product_uom': producto.uom_id.id,
            'product_uom_qty': movs[clave][2],
            'location_id': hueco.id,
            'location_dest_id': sorter.id,
        })
        # Al crear, el movimiento puede heredar las ubicaciones del albaran:
        # se vuelven a fijar el hueco exacto y el SORTER antes de confirmar
        if movimiento.location_id.id != hueco.id or movimiento.location_dest_id.id != sorter.id:
            movimiento.write({'location_id': hueco.id, 'location_dest_id': sorter.id})
    picking.action_confirm()
    picking.action_assign()
    ints |= picking
    resumen.append((etiqueta, picking, uds_t, len(orden_movs), len(outs_t)))

# ---------------- 6. Comprobar que todo ha quedado reservado del hueco exacto --
fallos = []
for etiqueta, picking, uds_t, n_movs, n_outs in resumen:
    for m in picking.move_lines:
        reservado = 0.0
        for ml in m.move_line_ids:
            if ml.location_id.id != m.location_id.id:
                fallos.append('%s: %s reservado en %s y no en %s' % (etiqueta, m.product_id.display_name,
                                                                     ml.location_id.complete_name, m.location_id.complete_name))
            reservado += ml.product_uom_qty
        if abs(reservado - m.product_uom_qty) > 0.001:
            fallos.append('%s: %s en %s - reservado %d de %d' % (etiqueta, m.product_id.display_name,
                                                                m.location_id.complete_name, reservado, m.product_uom_qty))
        if m.location_dest_id.id != sorter.id:
            fallos.append('%s: %s con destino %s' % (etiqueta, m.product_id.display_name, m.location_dest_id.complete_name))
if fallos:
    texto = 'REPARTIR INT POR ZONA - NO SE HA HECHO NADA (se ha deshecho todo)\n\n'
    texto += 'Estos movimientos no han quedado reservados del hueco exacto:\n' + '\n'.join(fallos[:60])
    if len(fallos) > 60:
        texto += '\n... y %d mas' % (len(fallos) - 60)
    log('KOROSHI REPARTIR INT ZONAS - DESHECHO\n%s' % texto)
    raise Warning(texto)

# ---------------- 7. Las OUT pasan a salir del SORTER --------------------------
outs.write({'location_id': sorter.id})
for p in outs:
    for m in p.move_lines:
        if m.state not in ('done', 'cancel') and m.location_id.id != sorter.id:
            m.write({'location_id': sorter.id})
    nombres = ''
    for etiqueta, picking, uds_t, n_movs, n_outs in resumen:
        nombres += ' %s (%s)' % (picking.name, etiqueta)
    p.message_post(body='Repartida en INT por zona. Ahora sale del SORTER. INT:%s' % nombres)

# ---------------- 8. Resumen y lista de los INT --------------------------------
lineas_log = ['KOROSHI REPARTIR INT ZONAS - HECHO', 'OUT: %d (%s)' % (len(outs), ', '.join(outs.mapped('name')))]
total = 0.0
for etiqueta, picking, uds_t, n_movs, n_outs in resumen:
    total += uds_t
    lineas_log.append('   %s | %s | %d uds | %d movimientos | %d OUT' % (picking.name, etiqueta, uds_t, n_movs, n_outs))
lineas_log.append('Total: %d INT, %d uds' % (len(resumen), total))
log('\n'.join(lineas_log))

action = {
    'type': 'ir.actions.act_window',
    'name': 'INT por zona %s (%d INT, %d uds)' % (hoy, len(resumen), total),
    'res_model': 'stock.picking',
    'view_mode': 'tree,form',
    'domain': [('id', 'in', ints.ids)],
    'target': 'current',
}

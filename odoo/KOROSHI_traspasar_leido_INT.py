# =============================================================================
# KOROSHI - TRASPASAR AL SORTER LO YA LEIDO DE LOS INT Y PREPARAR LAS OUT
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Para que la U pueda empezar a leer la oleada mientras los pickers siguen cogiendo:
#   1. Coge los INT de la oleada (origen KOR-ddmm-...) que tienen unidades leidas.
#      - si se lanza desde la lista de albaranes con INT seleccionados: solo esos;
#      - si INT_NOMBRES tiene nombres: solo esos;
#      - si no: todos los INT KOR del dia (hora local) que esten Preparados.
#   2. Valida cada INT con lo leido y crea el pedido pendiente con lo que falta
#      (igual que Validar > "Crear pedido pendiente"). Lo leido pasa al SORTER.
#      OJO: el picker sigue con el INT NUEVO (el pendiente, mismo origen KOR-ddmm-Dn).
#   3. "Comprobar disponibilidad" en las OUT de la oleada del dia (B-KOR-ddmm-..):
#      reservan lo que ya esta en el SORTER y quedan Preparadas.
#   4. Resumen: por INT, lo traspasado y el INT pendiente; por OUT, estado y uds reservadas.
# Despues, en el programa de la U: cerrar las cajas abiertas y volver a cargar la oleada.
#
# SIMULAR = True: lo hace todo y al final lanza un aviso que DESHACE TODO.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
PREFIJO_INT = 'KOR-'              # origen de los INT de zona: KOR-ddmm-D1...
PREFIJO_OLEADA = 'B-KOR-'         # oleadas del dia: B-KOR-ddmm-01...
ZONA_HORARIA = 'Europe/Madrid'
INT_NOMBRES = []                  # p. ej. ['EFFEC/INT/66207'] para hacer solo ese. Vacio = ver arriba
SIMULAR = True                    # True: prueba que lo deshace todo. False: lo hace de verdad
# -----------------------------------------------------------------------------

ahora_local = datetime.datetime.now(timezone(ZONA_HORARIA))
hoy = ahora_local.strftime('%d%m')
sorter = env['stock.location'].search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)

# ---------------- 1. INT a traspasar ------------------------------------------
if INT_NOMBRES:
    ints = env['stock.picking'].search([('name', 'in', INT_NOMBRES), ('company_id', '=', COMPANY_ID)])
elif env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    ints = env['stock.picking'].browse(env.context.get('active_ids'))
else:
    ints = env['stock.picking'].search([
        ('company_id', '=', COMPANY_ID),
        ('picking_type_code', '=', 'internal'),
        ('origin', '=like', '%s%s-%%' % (PREFIJO_INT, hoy)),
        ('state', '=', 'assigned'),
    ], order='name asc')

errores = []
if not sorter:
    errores.append('No existe la ubicacion SORTER')
validos = []
saltados = []
for p in ints:
    motivo = ''
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'internal':
        motivo = 'no es un INT de la empresa %d' % COMPANY_ID
    elif not (p.origin or '').startswith(PREFIJO_INT):
        motivo = 'su origen no es %s... (%s)' % (PREFIJO_INT, p.origin or '')
    elif p.state != 'assigned':
        motivo = 'no esta Preparado (%s)' % p.state
    elif sorter and p.location_dest_id.id != sorter.id:
        motivo = 'su destino no es el SORTER'
    else:
        leido = 0.0
        for ml in p.move_line_ids:
            leido += ml.qty_done
        if leido <= 0:
            motivo = 'no tiene unidades leidas'
    if motivo:
        saltados.append('%s (%s): %s' % (p.name, p.origin or '', motivo))
    else:
        validos.append(p)

if errores:
    log('KOROSHI TRASPASAR LEIDO - ABORTADO\n' + '\n'.join(errores))
    raise Warning('TRASPASAR LEIDO - NO SE HA HECHO NADA\n\n' + '\n'.join(errores))

# ---------------- 2. Validar lo leido y crear el pendiente ---------------------
lineas = []
total_traspasado = 0.0
for p in validos:
    leido = 0.0
    pedido = 0.0
    for ml in p.move_line_ids:
        leido += ml.qty_done
    for m in p.move_lines:
        pedido += m.product_uom_qty
    nombre = p.name
    origen = p.origin
    wiz = env['stock.backorder.confirmation'].create({'pick_ids': [(4, p.id)]})
    wiz.process()
    pendiente = env['stock.picking'].search([('backorder_id', '=', p.id)], limit=1)
    total_traspasado += leido
    lineas.append('   %s (%s): %d de %d uds al SORTER -> %s | sigue en %s (%d uds)' % (
        nombre, origen, leido, pedido, p.state,
        pendiente and pendiente.name or 'sin pendiente (estaba todo leido)',
        pendiente and (pedido - leido) or 0))

# ---------------- 3. Comprobar disponibilidad de las OUT de la oleada ----------
outs = env['stock.picking'].search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('batch_id.name', '=like', '%s%s-%%' % (PREFIJO_OLEADA, hoy)),
    ('state', 'in', ('confirmed', 'waiting', 'assigned')),
], order='name asc')
if outs:
    outs.action_assign()
lineas_out = []
preparadas = 0
for o in outs:
    reservado = 0.0
    pedido = 0.0
    for ml in o.move_line_ids:
        reservado += ml.product_uom_qty
    for m in o.move_lines:
        if m.state != 'cancel':
            pedido += m.product_uom_qty
    if o.state == 'assigned':
        preparadas += 1
    lineas_out.append('   %s | %s | %s | %d de %d uds reservadas' % (
        o.name, o.batch_id.name, o.state, reservado, pedido))

# ---------------- 4. Resumen ---------------------------------------------------
texto = ['KOROSHI TRASPASAR LEIDO - ' + (SIMULAR and 'SIMULACION (SE HA DESHECHO TODO)' or 'HECHO'),
         'INT traspasados: %d (%d uds al SORTER)' % (len(validos), total_traspasado)]
texto += lineas
if saltados:
    texto.append('INT saltados:')
    for s in saltados:
        texto.append('   ' + s)
texto.append('')
texto.append('OUT de la oleada: %d, Preparadas: %d (el programa solo carga las Preparadas)' % (len(outs), preparadas))
texto += lineas_out
if outs and preparadas < len(outs):
    texto.append('OJO: si no estan todas Preparadas, los SEQ del programa no coinciden con las bahias. Esperar a traspasar mas.')
texto.append('')
texto.append('Despues: en la U cerrar las cajas abiertas (CAMBIAR-CAJA) y volver a cargar la oleada en el programa.')
mensaje = '\n'.join(texto)
log(mensaje)
if SIMULAR:
    raise Warning(mensaje + '\n\nEs una simulacion: Odoo deshace todo. Para hacerlo de verdad: SIMULAR = False.')

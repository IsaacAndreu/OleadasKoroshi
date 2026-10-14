# =============================================================================
# KOROSHI - CREAR OLEADAS                                              v1
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Reparte las OUT de tiendas KOROSHI de EFFEC (company_id 8) en oleadas
# (stock.picking.batch), una por "U":
#   1. OUT de tienda (origen S-66..., destinatario "K<numero> - ...") creadas en
#      las ultimas HORAS_ATRAS horas, reservadas y sin oleada.
#   2. Todas las OUT de una tienda van a la misma oleada.
#   3. Tiempo estimado de cada tienda segun el volumen de cada articulo
#      (UDS_HORA_PEQUENO para articulos pequenos, UDS_HORA_GRANDE para grandes).
#   4. Tiendas de mas a menos tiempo; cada tienda va a la oleada que lleva menos
#      tiempo acumulado (asi las oleadas acaban a la vez).
#
# ESCRIBIR = False (por defecto): NO crea nada, termina con un Warning con el plan.
# ESCRIBIR = True: crea las oleadas en estado 'in_progress' (sin reservar ni
# tocar las lineas) y abre la lista de oleadas creadas.
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
ESCRIBIR = False
COMPANY_ID = 8
PREFIJO_ORIGEN = 'S-66'
# Solo destinatarios "K<numero> - ..." (deja fuera ZALANDO, ABOUT YOU, muestras...).
SOLO_TIENDAS_K = True
# Excluir tiendas concretas (nombre exacto del destinatario).
EXCLUIR_TIENDAS = ['K7777 MUESTRAS']
# Solo OUT creadas en las ultimas X horas (los pedidos de la noche, no restos antiguos).
HORAS_ATRAS = 12
# 'COMPLETA': solo OUT reservadas del todo. 'PARCIAL': tambien con reserva parcial.
MODO_RESERVA = 'PARCIAL'
# Numero de oleadas (una por "U").
NUM_OLEADAS = 5
# Solo crear las N primeras oleadas (0 = todas). Para una prueba con una sola "U": 1.
SOLO_PRIMERAS = 0
# Maximo de unidades por oleada (0 = sin limite). Para la prueba de ~2.000 uds: 2000.
MAX_UNIDADES_OLEADA = 0
# Posiciones (cajas/tiendas) por "U": solo avisa si se supera.
POSICIONES_U = 12
# Ritmo segun volumen del articulo (m3). Sin volumen se usa UDS_HORA_DEFECTO.
UDS_HORA_PEQUENO = 500
UDS_HORA_GRANDE = 300
VOLUMEN_PEQUENO = 0.002
VOLUMEN_GRANDE = 0.015
UDS_HORA_DEFECTO = 425
# Nombre: B-KOR-MMDD-NN (el prefijo B- lo acepta el programa PedidosMultiples).
PREFIJO_NOMBRE = 'B-KOR-'
MAX_LINEAS_MENSAJE = 200
# -----------------------------------------------------------------------------

Picking = env['stock.picking']
Batch = env['stock.picking.batch']
ahora_utc = datetime.datetime.utcnow()
desde_txt = (ahora_utc - datetime.timedelta(hours=HORAS_ATRAS)).strftime('%Y-%m-%d %H:%M:%S')
try:
    ahora_local = timezone('UTC').localize(ahora_utc).astimezone(timezone('Europe/Madrid'))
except:
    ahora_local = ahora_utc + datetime.timedelta(hours=2)
fecha_nombre = ahora_local.strftime('%m%d')

candidatos = Picking.search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('origin', '=like', PREFIJO_ORIGEN + '%'),
    ('batch_id', '=', False),
    ('state', '=', 'assigned'),
    ('create_date', '>=', desde_txt),
], order='name asc')

tiendas = {}
excluidas = []
for p in candidatos:
    nombre = p.partner_id.name or ''
    if nombre in EXCLUIR_TIENDAS:
        excluidas.append((p, 'tienda excluida'))
        continue
    if SOLO_TIENDAS_K and not (len(nombre) > 1 and nombre[0] == 'K' and nombre[1].isdigit()):
        excluidas.append((p, 'no es tienda K'))
        continue
    moves = p.move_lines.filtered(lambda m: m.state != 'cancel')
    pedido = sum(moves.mapped('product_uom_qty'))
    reservado = sum(moves.mapped('reserved_availability'))
    if MODO_RESERVA == 'COMPLETA' and reservado < pedido:
        excluidas.append((p, 'reserva parcial %d/%d' % (reservado, pedido)))
        continue
    if reservado <= 0:
        excluidas.append((p, 'sin reserva'))
        continue
    # Tiempo estimado (horas) segun el volumen de cada articulo reservado
    horas = 0.0
    uds_sin_volumen = 0.0
    for m in moves:
        qty = m.reserved_availability
        if qty <= 0:
            continue
        vol = m.product_id.volume or 0.0
        if vol <= 0:
            ritmo = UDS_HORA_DEFECTO
            uds_sin_volumen += qty
        elif vol <= VOLUMEN_PEQUENO:
            ritmo = UDS_HORA_PEQUENO
        elif vol >= VOLUMEN_GRANDE:
            ritmo = UDS_HORA_GRANDE
        else:
            ritmo = UDS_HORA_PEQUENO - (UDS_HORA_PEQUENO - UDS_HORA_GRANDE) * (vol - VOLUMEN_PEQUENO) / (VOLUMEN_GRANDE - VOLUMEN_PEQUENO)
        horas += qty / ritmo
    clave = p.partner_id.id
    if clave not in tiendas:
        tiendas[clave] = {'nombre': nombre, 'outs': [], 'uds': 0.0, 'horas': 0.0, 'sin_vol': 0.0}
    tiendas[clave]['outs'].append(p)
    tiendas[clave]['uds'] += reservado
    tiendas[clave]['horas'] += horas
    tiendas[clave]['sin_vol'] += uds_sin_volumen

# Tiendas de mas a menos tiempo; cada una a la oleada con menos tiempo acumulado
ranking = sorted(tiendas.values(), key=lambda t: (-t['horas'], t['nombre']))
oleadas = []
for i in range(NUM_OLEADAS):
    oleadas.append({'num': i + 1, 'tiendas': [], 'uds': 0.0, 'horas': 0.0, 'outs': 0})
sin_sitio = []
for t in ranking:
    elegida = False
    for o in sorted(oleadas, key=lambda x: (x['horas'], x['num'])):
        if MAX_UNIDADES_OLEADA and o['uds'] + t['uds'] > MAX_UNIDADES_OLEADA:
            continue
        elegida = o
        break
    if not elegida:
        sin_sitio.append(t)
        continue
    elegida['tiendas'].append(t)
    elegida['uds'] += t['uds']
    elegida['horas'] += t['horas']
    elegida['outs'] += len(t['outs'])

oleadas_a_crear = []
for o in oleadas:
    if o['tiendas'] and (not SOLO_PRIMERAS or len(oleadas_a_crear) < SOLO_PRIMERAS):
        o['nombre'] = '%s%s-%02d' % (PREFIJO_NOMBRE, fecha_nombre, o['num'])
        oleadas_a_crear.append(o)

# Nombres ya existentes: no se crea nada
repetidos = []
for o in oleadas_a_crear:
    if Batch.search_count([('name', '=', o['nombre'])]):
        repetidos.append(o['nombre'])

# ----------------------------- RESUMEN ---------------------------------------
lineas = []
lineas.append('KOROSHI CREAR OLEADAS v1 - %s - %s' % ('ESCRIBIR' if ESCRIBIR else 'SIMULACION (NO SE HA CREADO NADA)', ahora_local.strftime('%d/%m/%Y %H:%M')))
lineas.append('Parametros: HORAS_ATRAS=%d, MODO_RESERVA=%s, NUM_OLEADAS=%d, SOLO_PRIMERAS=%d, MAX_UNIDADES_OLEADA=%d, POSICIONES_U=%d'
              % (HORAS_ATRAS, MODO_RESERVA, NUM_OLEADAS, SOLO_PRIMERAS, MAX_UNIDADES_OLEADA, POSICIONES_U))
lineas.append('OUT candidatas: %d | tiendas: %d | excluidas: %d | tiendas sin sitio: %d' % (len(candidatos), len(ranking), len(excluidas), len(sin_sitio)))
for o in oleadas_a_crear:
    aviso = ''
    if o['outs'] > POSICIONES_U:
        aviso = '  <-- AVISO: %d OUT y la U tiene %d posiciones' % (o['outs'], POSICIONES_U)
    lineas.append('')
    lineas.append('%s: %d tiendas, %d OUT, %d uds, ~%.1f h de U%s' % (o['nombre'], len(o['tiendas']), o['outs'], o['uds'], o['horas'], aviso))
    for t in o['tiendas']:
        nombres_out = []
        for p in t['outs']:
            nombres_out.append(p.name)
        lineas.append('   %s | %d uds | %.2f h | %s%s' % (t['nombre'], t['uds'], t['horas'], ', '.join(nombres_out),
                                                    t['sin_vol'] and ' | %d uds sin volumen' % t['sin_vol'] or ''))
if sin_sitio:
    lineas.append('')
    lineas.append('TIENDAS QUE NO CABEN (MAX_UNIDADES_OLEADA):')
    for t in sin_sitio:
        lineas.append('   %s | %d uds' % (t['nombre'], t['uds']))
if excluidas:
    lineas.append('')
    lineas.append('OUT EXCLUIDAS:')
    for item in excluidas:
        lineas.append('   %s | %s | %s' % (item[0].name, item[0].partner_id.name or '-', item[1]))

if repetidos:
    lineas.append('')
    lineas.append('ERROR: ya existen oleadas con estos nombres, no se crea nada: %s' % ', '.join(repetidos))

texto = '\n'.join(lineas)

if not ESCRIBIR or repetidos or not oleadas_a_crear:
    log('KOROSHI CREAR OLEADAS (sin escribir)\n%s' % texto)
    if len(lineas) > MAX_LINEAS_MENSAJE:
        lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
    if not oleadas_a_crear:
        lineas.append('')
        lineas.append('No hay ninguna oleada que crear.')
    raise Warning('\n'.join(lineas))

# ----------------------------- CREAR -----------------------------------------
creadas = env['stock.picking.batch']
for o in oleadas_a_crear:
    ids_outs = []
    for t in o['tiendas']:
        for p in t['outs']:
            ids_outs.append(p.id)
    batch = Batch.create({
        'name': o['nombre'],
        'company_id': COMPANY_ID,
        'picking_ids': [(6, 0, ids_outs)],
    })
    # Se pasa a 'in_progress' escribiendo el estado: no se llama a confirm_picking
    # para no volver a reservar ni cambiar el estado de los albaranes.
    batch.write({'state': 'in_progress'})
    creadas = creadas | batch

log('KOROSHI CREAR OLEADAS: creadas %s\n%s' % (', '.join(creadas.mapped('name')), texto))

action = {
    'type': 'ir.actions.act_window',
    'name': 'Oleadas KOROSHI creadas',
    'res_model': 'stock.picking.batch',
    'view_mode': 'tree,form',
    'domain': [('id', 'in', creadas.ids)],
}

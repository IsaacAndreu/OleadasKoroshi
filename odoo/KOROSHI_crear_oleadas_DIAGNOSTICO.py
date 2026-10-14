# =============================================================================
# KOROSHI - CREAR OLEADAS - DIAGNOSTICO (NO ESCRIBE NADA)          version 3
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Simula la creacion automatica de oleadas (stock.picking.batch) para los
# pedidos de tiendas KOROSHI de EFFEC (company_id 8):
#   1. Busca las OUT de tienda (origen S-66...) sin oleada.
#   2. Agrupa por tienda (destinatario): todas las OUT de una tienda van juntas.
#   3. Ordena las tiendas por volumen historico (unidades enviadas en los
#      ultimos DIAS_HISTORICO dias), de mas a menos.
#   4. Reparte las tiendas, en ese orden, en NUM_OLEADAS oleadas con un numero
#      de unidades parecido, y estima el tiempo a UNIDADES_HORA.
# No crea batches, no modifica pickings, no reserva y no consume la secuencia
# de batches. La unica escritura es el log() en ir.logging (cursor propio).
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
# Solo pedidos cuyo origen empieza por alguno de estos prefijos (tiendas KOROSHI).
PREFIJOS_ORIGEN = ['S-66']
# Numero de oleadas en las que repartir las tiendas.
NUM_OLEADAS = 5
# Ritmo de preparacion para estimar el tiempo de cada oleada.
UNIDADES_HORA = 500
# Huecos de la "U": solo avisa si una oleada tiene mas OUT. VALOR PROVISIONAL: confirmar.
MAX_PEDIDOS = 40
# Dias de historico para el ranking de tiendas.
DIAS_HISTORICO = 30
# Que pedidos entran segun la reserva:
#   'COMPLETA' -> solo 'assigned' reservados del todo
#   'PARCIAL'  -> tambien 'assigned' con reserva parcial (se cuentan las unidades reservadas)
#   'MINIMO'   -> 'assigned' con al menos PORCENTAJE_MINIMO % reservado
MODO_RESERVA = 'PARCIAL'
PORCENTAJE_MINIMO = 80
# Lineas maximas en el mensaje final (el detalle completo va al log).
MAX_LINEAS_MENSAJE = 160
# -----------------------------------------------------------------------------

Picking = env['stock.picking']
ahora = datetime.datetime.now()
desde = ahora - datetime.timedelta(days=DIAS_HISTORICO)

# Dominio de origen: ('origin' =like 'S-66%') para cada prefijo, unidos con OR
dominio_origen = []
for i in range(len(PREFIJOS_ORIGEN) - 1):
    dominio_origen.append('|')
for prefijo in PREFIJOS_ORIGEN:
    dominio_origen.append(('picking_id.origin', '=like', prefijo + '%'))

# ---------------- 1. Historico de unidades enviadas por tienda ---------------
historico = {}
grupos_hist = env['stock.move.line'].read_group(
    [('company_id', '=', COMPANY_ID),
     ('state', '=', 'done'),
     ('picking_id.picking_type_code', '=', 'outgoing'),
     ('date', '>=', desde.strftime('%Y-%m-%d %H:%M:%S'))] + dominio_origen,
    ['picking_id', 'qty_done'], ['picking_id'])
pickings_hist = 0
for g in grupos_hist:
    if not g.get('picking_id'):
        continue
    pickings_hist += 1
    socio = Picking.browse(g['picking_id'][0]).partner_id
    historico[socio.id] = historico.get(socio.id, 0.0) + (g.get('qty_done') or 0.0)

# ---------------- 2. Pedidos de tienda pendientes sin oleada -----------------
candidatos = Picking.search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('batch_id', '=', False),
    ('state', 'in', ['confirmed', 'waiting', 'assigned']),
], order='scheduled_date asc, name asc')

tiendas = {}
no_entran = []
descartados_origen = 0
for p in candidatos:
    origen = p.origin or ''
    origen_valido = not PREFIJOS_ORIGEN
    for prefijo in PREFIJOS_ORIGEN:
        if origen.startswith(prefijo):
            origen_valido = True
    if not origen_valido:
        descartados_origen += 1
        continue
    moves = p.move_lines.filtered(lambda m: m.state != 'cancel')
    unidades = sum(moves.mapped('product_uom_qty'))
    reservado = sum(moves.mapped('reserved_availability'))
    porcentaje = unidades and (reservado * 100.0 / unidades) or 0.0

    motivo = ''
    if p.state != 'assigned' or reservado <= 0:
        motivo = 'sin reservar (%s, %d/%d)' % (p.state, reservado, unidades)
    elif MODO_RESERVA == 'COMPLETA' and reservado < unidades:
        motivo = 'reserva parcial (%d/%d)' % (reservado, unidades)
    elif MODO_RESERVA == 'MINIMO' and porcentaje < PORCENTAJE_MINIMO:
        motivo = 'reserva %d %% < %d %%' % (int(round(porcentaje)), PORCENTAJE_MINIMO)
    if motivo:
        no_entran.append((p, motivo))
        continue

    a_preparar = reservado if MODO_RESERVA != 'COMPLETA' else unidades
    socio = p.partner_id
    if socio.id not in tiendas:
        tiendas[socio.id] = {
            'nombre': socio.name or socio.display_name or 'SIN DESTINATARIO',
            'ciudad': socio.city or '-',
            'historico': historico.get(socio.id, 0.0),
            'outs': [],
            'pedido': 0.0,
            'a_preparar': 0.0,
        }
    t = tiendas[socio.id]
    t['outs'].append(p)
    t['pedido'] += unidades
    t['a_preparar'] += a_preparar

# ---------------- 3. Ranking de tiendas (mas volumen primero) ----------------
ranking = sorted(tiendas.values(), key=lambda t: (-t['historico'], -t['a_preparar'], t['nombre']))

# ---------------- 4. Reparto en NUM_OLEADAS con unidades parecidas -----------
total = 0.0
for t in ranking:
    total += t['a_preparar']
objetivo = NUM_OLEADAS and (total / NUM_OLEADAS) or total
oleadas = []
actual = {'tiendas': [], 'unidades': 0.0, 'outs': 0}
for t in ranking:
    actual['tiendas'].append(t)
    actual['unidades'] += t['a_preparar']
    actual['outs'] += len(t['outs'])
    if actual['unidades'] >= objetivo and len(oleadas) < NUM_OLEADAS - 1:
        oleadas.append(actual)
        actual = {'tiendas': [], 'unidades': 0.0, 'outs': 0}
if actual['tiendas']:
    oleadas.append(actual)

# ----------------------------- MENSAJE ---------------------------------------
lineas = []
lineas.append('DIAGNOSTICO CREAR OLEADAS KOROSHI v3 (company_id %d) - NO SE HA CREADO NADA' % COMPANY_ID)
lineas.append('Fecha: %s' % ahora.strftime('%d/%m/%Y %H:%M:%S'))
lineas.append('Parametros: PREFIJOS_ORIGEN=%s, NUM_OLEADAS=%d, UNIDADES_HORA=%d, MAX_PEDIDOS=%d, DIAS_HISTORICO=%d, MODO_RESERVA=%s'
              % (', '.join(PREFIJOS_ORIGEN) or 'todos', NUM_OLEADAS, UNIDADES_HORA, MAX_PEDIDOS, DIAS_HISTORICO, MODO_RESERVA))
lineas.append('Historico: %d albaranes de tienda enviados en %d dias, %d tiendas con historico'
              % (pickings_hist, DIAS_HISTORICO, len(historico)))
lineas.append('')
lineas.append('OUT sin oleada: %d (descartadas por origen: %d, no entran por reserva: %d)'
              % (len(candidatos), descartados_origen, len(no_entran)))
lineas.append('Tiendas con pedidos que entran: %d, unidades a preparar: %d, tiempo total estimado: %.1f h'
              % (len(ranking), total, UNIDADES_HORA and (total / UNIDADES_HORA) or 0.0))
lineas.append('')
lineas.append('OLEADAS QUE SE CREARIAN: %d (objetivo ~%d uds por oleada)' % (len(oleadas), objetivo))
n = 0
for o in oleadas:
    n += 1
    minutos = UNIDADES_HORA and (o['unidades'] * 60.0 / UNIDADES_HORA) or 0.0
    aviso = ''
    if o['outs'] > MAX_PEDIDOS:
        aviso = '  <-- AVISO: %d OUT y la U tiene %d huecos' % (o['outs'], MAX_PEDIDOS)
    lineas.append('')
    lineas.append('OLEADA %d: %d tiendas, %d OUT, %d uds, ~%d min a %d u/h%s'
                  % (n, len(o['tiendas']), o['outs'], o['unidades'], int(round(minutos)), UNIDADES_HORA, aviso))
    seq = 0
    for t in o['tiendas']:
        for p in t['outs']:
            seq += 1
            lineas.append('   %03d  %s | %s | %s (%s) | historico %d uds/%d dias'
                          % (seq, p.name, p.origin or '-', t['nombre'], t['ciudad'], t['historico'], DIAS_HISTORICO))
        lineas.append('        -> tienda: %d uds a preparar de %d pedidas' % (t['a_preparar'], t['pedido']))

if no_entran:
    lineas.append('')
    lineas.append('NO ENTRAN EN NINGUNA OLEADA:')
    for item in no_entran:
        p = item[0]
        lineas.append('   %s | %s | %s | %s' % (p.name, p.origin or '-', (p.partner_id and p.partner_id.name) or '-', item[1]))

lineas.append('')
lineas.append('RANKING COMPLETO DE TIENDAS CON HISTORICO (uds enviadas en %d dias, media diaria):' % DIAS_HISTORICO)
socios_hist = env['res.partner'].browse(list(historico.keys()))
ranking_hist = sorted(socios_hist, key=lambda s: -historico.get(s.id, 0.0))
pos = 0
for s in ranking_hist:
    pos += 1
    lineas.append('   %2d. %s: %d uds (%.1f/dia)' % (pos, s.name or s.display_name, historico.get(s.id, 0.0), historico.get(s.id, 0.0) / DIAS_HISTORICO))

texto_completo = '\n'.join(lineas)
log('KOROSHI CREAR OLEADAS DIAGNOSTICO v3: %d tiendas, %d oleadas simuladas\n%s' % (len(ranking), len(oleadas), texto_completo))

if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver el detalle completo en Ajustes > Tecnico > Registros / ir.logging)' % (len(lineas) - MAX_LINEAS_MENSAJE)]

raise Warning('\n'.join(lineas))

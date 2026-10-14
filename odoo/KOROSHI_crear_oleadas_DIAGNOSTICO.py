# =============================================================================
# KOROSHI - CREAR OLEADAS - DIAGNOSTICO (NO ESCRIBE NADA)          version 2
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Simula la creacion automatica de oleadas (stock.picking.batch) para los
# pedidos de tiendas KOROSHI de EFFEC (company_id 8): busca las OUT, las filtra
# por origen, las clasifica por reserva, las agrupa y termina con un Warning
# explicando que oleadas crearia. No crea batches, no modifica pickings y no
# consume la secuencia de batches. La unica escritura es el log() en
# ir.logging, que Odoo hace con su propio cursor.
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
# Solo pedidos cuyo origen empieza por alguno de estos prefijos (tiendas KOROSHI).
PREFIJOS_ORIGEN = ['S-66']
# Maximo de pedidos por oleada (huecos de la "U"). VALOR PROVISIONAL: confirmar.
MAX_PEDIDOS = 40
# Maximo de unidades por oleada. 0 = sin limite.
MAX_UNIDADES = 0
# Que pedidos entran segun la reserva:
#   'COMPLETA' -> solo 'assigned' reservados del todo
#   'PARCIAL'  -> tambien 'assigned' con reserva parcial
#   'MINIMO'   -> 'assigned' con al menos PORCENTAJE_MINIMO % reservado
MODO_RESERVA = 'COMPLETA'
PORCENTAJE_MINIMO = 80
# Criterio para separar oleadas: '' (ninguno), 'TIENDA', 'CIUDAD', 'TRANSPORTISTA' o 'FECHA'.
SEPARAR_POR = ''
# Lineas maximas en el mensaje final (el detalle completo va al log).
MAX_LINEAS_MENSAJE = 150
# -----------------------------------------------------------------------------

Picking = env['stock.picking']

candidatos = Picking.search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('batch_id', '=', False),
    ('state', 'in', ['confirmed', 'waiting', 'assigned']),
], order='priority desc, scheduled_date asc, name asc')
ya_en_oleada = Picking.search_count([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('batch_id', '!=', False),
    ('state', 'in', ['confirmed', 'waiting', 'assigned']),
])

descartados_origen = 0
todos = []
entran = []
no_entran = []

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
    socio = p.partner_id
    datos = {
        'picking': p,
        'unidades': unidades,
        'reservado': reservado,
        'porcentaje': porcentaje,
        'tienda': (socio and socio.display_name) or 'SIN DESTINATARIO',
        'ciudad': (socio and socio.city) or 'SIN CIUDAD',
        'transportista': (p.carrier_id and p.carrier_id.name) or 'SIN TRANSPORTISTA',
        'fecha': p.scheduled_date and p.scheduled_date.strftime('%d/%m/%Y') or 'SIN FECHA',
    }
    todos.append(datos)

    motivo = ''
    if p.state != 'assigned':
        motivo = 'sin reservar (%s)' % p.state
    elif MODO_RESERVA == 'COMPLETA' and reservado < unidades:
        motivo = 'reserva parcial'
    elif MODO_RESERVA == 'MINIMO' and porcentaje < PORCENTAJE_MINIMO:
        motivo = 'reserva por debajo del %d %%' % PORCENTAJE_MINIMO
    if motivo:
        datos['motivo'] = motivo
        no_entran.append(datos)
    else:
        entran.append(datos)

# Agrupar respetando el orden (prioridad, fecha prevista, nombre)
grupos = {}
orden_grupos = []
for d in entran:
    clave = 'TODOS'
    if SEPARAR_POR == 'TIENDA':
        clave = d['tienda']
    elif SEPARAR_POR == 'CIUDAD':
        clave = d['ciudad']
    elif SEPARAR_POR == 'TRANSPORTISTA':
        clave = d['transportista']
    elif SEPARAR_POR == 'FECHA':
        clave = d['fecha']
    if clave not in grupos:
        grupos[clave] = []
        orden_grupos.append(clave)
    grupos[clave].append(d)

# Partir cada grupo en oleadas segun MAX_PEDIDOS y MAX_UNIDADES
oleadas = []
for clave in orden_grupos:
    actual = []
    unidades_actual = 0
    for d in grupos[clave]:
        excede_pedidos = len(actual) >= MAX_PEDIDOS
        excede_unidades = MAX_UNIDADES and actual and (unidades_actual + d['unidades'] > MAX_UNIDADES)
        if excede_pedidos or excede_unidades:
            oleadas.append({'grupo': clave, 'pedidos': actual, 'unidades': unidades_actual})
            actual = []
            unidades_actual = 0
        actual.append(d)
        unidades_actual += d['unidades']
    if actual:
        oleadas.append({'grupo': clave, 'pedidos': actual, 'unidades': unidades_actual})

# ----------------------------- MENSAJE ---------------------------------------
lineas = []
lineas.append('DIAGNOSTICO CREAR OLEADAS KOROSHI v2 (company_id %d) - NO SE HA CREADO NADA' % COMPANY_ID)
lineas.append('Fecha: %s' % datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
lineas.append('Parametros: PREFIJOS_ORIGEN=%s, MAX_PEDIDOS=%d, MAX_UNIDADES=%d, MODO_RESERVA=%s (%d %%), SEPARAR_POR=%s'
              % (', '.join(PREFIJOS_ORIGEN) or 'todos', MAX_PEDIDOS, MAX_UNIDADES, MODO_RESERVA, PORCENTAJE_MINIMO, SEPARAR_POR or 'ninguno'))
lineas.append('')
lineas.append('OUT sin oleada de la empresa: %d' % len(candidatos))
lineas.append('  - Descartadas por origen: %d' % descartados_origen)
lineas.append('  - Pedidos de tienda: %d (entran: %d, no entran: %d)' % (len(todos), len(entran), len(no_entran)))
lineas.append('OUT pendientes que ya estan en una oleada: %d' % ya_en_oleada)
lineas.append('')
lineas.append('OLEADAS QUE SE CREARIAN: %d' % len(oleadas))
n = 0
for o in oleadas:
    n += 1
    lineas.append('')
    lineas.append('OLEADA %d [%s]: %d pedidos, %d unidades' % (n, o['grupo'], len(o['pedidos']), o['unidades']))
    seq = 0
    for d in o['pedidos']:
        seq += 1
        p = d['picking']
        lineas.append('   %03d  %s | %s | %s | %d / %d uds reservadas' % (seq, p.name, p.origin or '-', d['tienda'], d['reservado'], d['unidades']))

lineas.append('')
lineas.append('DETALLE DE TODOS LOS PEDIDOS DE TIENDA (para decidir como separar):')
lineas.append('   OUT | origen | estado | reservado/pedido (%) | tienda | ciudad | transportista | fecha prevista | entra?')
for d in todos:
    p = d['picking']
    lineas.append('   %s | %s | %s | %d/%d (%d %%) | %s | %s | %s | %s | %s'
                  % (p.name, p.origin or '-', p.state, d['reservado'], d['unidades'], int(round(d['porcentaje'])),
                     d['tienda'], d['ciudad'], d['transportista'], d['fecha'], d.get('motivo') and ('NO: ' + d['motivo']) or 'SI'))

texto_completo = '\n'.join(lineas)
log('KOROSHI CREAR OLEADAS DIAGNOSTICO v2: %d pedidos de tienda, %d oleadas simuladas\n%s' % (len(todos), len(oleadas), texto_completo))

if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver el detalle completo en Ajustes > Tecnico > Registros / ir.logging)' % (len(lineas) - MAX_LINEAS_MENSAJE)]

raise Warning('\n'.join(lineas))

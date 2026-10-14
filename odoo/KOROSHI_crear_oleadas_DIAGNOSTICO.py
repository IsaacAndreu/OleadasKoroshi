# =============================================================================
# KOROSHI - CREAR OLEADAS - DIAGNOSTICO (NO ESCRIBE NADA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Simula la creacion automatica de oleadas (stock.picking.batch) para EFFEC
# (company_id 8): busca las OUT, las clasifica, las agrupa y termina con un
# Warning explicando que oleadas crearia. No crea batches, no modifica pickings
# y no consume la secuencia de batches. La unica escritura es el log() en
# ir.logging, que Odoo hace con su propio cursor.
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
# Maximo de pedidos por oleada (huecos de la "U"). VALOR PROVISIONAL: confirmar.
MAX_PEDIDOS = 40
# Maximo de unidades por oleada. 0 = sin limite.
MAX_UNIDADES = 0
# Separar tiendas (CJ) y marketplace (PACK) en oleadas distintas.
SEPARAR_POR_CANAL = True
# Separar por transportista.
SEPARAR_POR_TRANSPORTISTA = False
# Incluir pedidos 'assigned' con reserva parcial (algun movimiento sin reservar del todo).
INCLUIR_PARCIALES = False
# Texto que identifica el canal tiendas (se busca en tipo de operacion, equipo de venta y origen).
TEXTO_TIENDAS = 'TIENDA'
# Lineas maximas en el mensaje final (el detalle completo va al log).
MAX_LINEAS_MENSAJE = 120
# -----------------------------------------------------------------------------

Picking = env['stock.picking']

dominio_base = [
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('batch_id', '=', False),
]
candidatos = Picking.search(dominio_base + [('state', 'in', ['confirmed', 'waiting', 'assigned'])],
                            order='priority desc, scheduled_date asc, name asc')
ya_en_oleada = Picking.search_count([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('batch_id', '!=', False),
    ('state', 'in', ['confirmed', 'waiting', 'assigned']),
])

no_reservados = []
parciales = []
listos = []

# Estadisticas para decidir como detectar el canal
stats_tipo = {}
stats_equipo = {}
stats_origen = {}

for p in candidatos:
    moves = p.move_lines.filtered(lambda m: m.state != 'cancel')
    unidades = sum(moves.mapped('product_uom_qty'))
    reservado = sum(moves.mapped('reserved_availability'))
    tipo = p.picking_type_id.name or ''
    equipo = (p.sale_id and p.sale_id.team_id and p.sale_id.team_id.name) or ''
    origen = p.origin or ''
    prefijo_origen = origen[:4]
    stats_tipo[tipo] = stats_tipo.get(tipo, 0) + 1
    stats_equipo[equipo] = stats_equipo.get(equipo, 0) + 1
    stats_origen[prefijo_origen] = stats_origen.get(prefijo_origen, 0) + 1

    texto_canal = ('%s %s %s' % (tipo, equipo, origen)).upper()
    canal = 'TIENDAS' if TEXTO_TIENDAS in texto_canal else 'MARKETPLACE'
    transportista = (p.carrier_id and p.carrier_id.name) or 'SIN TRANSPORTISTA'

    datos = {
        'picking': p,
        'unidades': unidades,
        'reservado': reservado,
        'canal': canal,
        'transportista': transportista,
    }
    if p.state != 'assigned':
        no_reservados.append(datos)
    elif reservado < unidades:
        parciales.append(datos)
        if INCLUIR_PARCIALES:
            listos.append(datos)
    else:
        listos.append(datos)

# Agrupar respetando el orden (prioridad, fecha prevista, nombre)
grupos = {}
orden_grupos = []
for d in listos:
    clave = 'TODOS'
    if SEPARAR_POR_CANAL and SEPARAR_POR_TRANSPORTISTA:
        clave = '%s / %s' % (d['canal'], d['transportista'])
    elif SEPARAR_POR_CANAL:
        clave = d['canal']
    elif SEPARAR_POR_TRANSPORTISTA:
        clave = d['transportista']
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
lineas.append('DIAGNOSTICO CREAR OLEADAS KOROSHI (company_id %d) - NO SE HA CREADO NADA' % COMPANY_ID)
lineas.append('Fecha: %s' % datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
lineas.append('Parametros: MAX_PEDIDOS=%d, MAX_UNIDADES=%d, SEPARAR_POR_CANAL=%s, SEPARAR_POR_TRANSPORTISTA=%s, INCLUIR_PARCIALES=%s'
              % (MAX_PEDIDOS, MAX_UNIDADES, SEPARAR_POR_CANAL, SEPARAR_POR_TRANSPORTISTA, INCLUIR_PARCIALES))
lineas.append('')
lineas.append('OUT sin oleada encontradas: %d' % len(candidatos))
lineas.append('  - Listas (assigned y reservadas del todo): %d' % (len(listos) - (len(parciales) if INCLUIR_PARCIALES else 0)))
lineas.append('  - Reserva parcial: %d (%s)' % (len(parciales), 'SE INCLUYEN' if INCLUIR_PARCIALES else 'NO se incluyen'))
lineas.append('  - Sin reservar (confirmed/waiting): %d (NO se incluyen)' % len(no_reservados))
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
        lineas.append('   %03d  %s  | %s | %s | %d uds' % (seq, p.name, p.origin or '-', (p.partner_id and p.partner_id.name) or '-', d['unidades']))

if parciales:
    lineas.append('')
    lineas.append('RESERVA PARCIAL (reservado / pedido):')
    for d in parciales:
        lineas.append('   %s | %s | %d / %d' % (d['picking'].name, d['picking'].origin or '-', d['reservado'], d['unidades']))

lineas.append('')
lineas.append('PARA DECIDIR COMO DETECTAR EL CANAL (pedidos por valor):')
lineas.append('  Tipo de operacion:')
for k in sorted(stats_tipo.keys()):
    lineas.append('     %s: %d' % (k or '(vacio)', stats_tipo[k]))
lineas.append('  Equipo de venta:')
for k in sorted(stats_equipo.keys()):
    lineas.append('     %s: %d' % (k or '(vacio)', stats_equipo[k]))
lineas.append('  Prefijo del origen (4 caracteres):')
for k in sorted(stats_origen.keys()):
    lineas.append('     %s: %d' % (k or '(vacio)', stats_origen[k]))

texto_completo = '\n'.join(lineas)
log('KOROSHI CREAR OLEADAS DIAGNOSTICO: %d candidatos, %d oleadas simuladas\n%s' % (len(candidatos), len(oleadas), texto_completo))

if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver el detalle completo en Ajustes > Tecnico > Registros / ir.logging)' % (len(lineas) - MAX_LINEAS_MENSAJE)]

raise Warning('\n'.join(lineas))

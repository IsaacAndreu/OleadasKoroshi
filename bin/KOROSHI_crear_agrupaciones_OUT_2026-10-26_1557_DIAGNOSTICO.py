# =============================================================================
# KOROSHI - CREAR AGRUPACIONES DE OUT DE TIENDA (una persona hace 10 pedidos de una vez)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Para la prueba de Lluis: pedidos normales (una OUT por pedido), sin INT ni SORTER, pero en "oleadas":
# se juntan TAMANO OUT en una agrupacion (stock.picking.batch) y una persona las coge todas a la vez
# desde la PDA (Codigo de barras > Agrupaciones): ve las lineas de las TAMANO OUT ordenadas por
# ubicacion y cada prenda va a la caja de su tienda (carro o palet con una caja por tienda).
#
# OUT: las seleccionadas en la lista; sin seleccion, las de PED. TIENDAS Preparadas (todo reservado),
# sin agrupacion y creadas hoy (hora local).
# Reparto: se empieza por la OUT con mas ubicaciones y se le van sumando las que mas ubicaciones
# comparten con lo que ya lleva la agrupacion (asi se pasa menos veces por el mismo hueco).
# Cada agrupacion se llama PREFIJO-ddmm-01, -02...; RESPONSABLE (id de usuario) opcional.
#
# MODO = 'DIAGNOSTICO': no crea nada; ensena las agrupaciones que haria, con uds, lineas y cuantas
#   paradas en ubicaciones se ahorran (suma de ubicaciones de cada OUT frente a las de la agrupacion).
# MODO = 'REAL': crea las agrupaciones y las deja En curso para que salgan en la PDA.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
MODO = 'DIAGNOSTICO'               # 'DIAGNOSTICO' (no crea nada) o 'REAL'
TAMANO = 10                        # OUT por agrupacion
MAX_AGRUPACIONES = 0               # 0 = todas las que salgan; p. ej. 1 para la primera prueba
TIPO_PEDIDO = 'PED. TIENDAS'
PREFIJO = 'B-10'                   # nombre: B-10-2710-01 (no B-KOR, que es la oleada con U)
RESPONSABLE = False                # id de usuario (res.users) o False
ZONA_HORARIA = 'Europe/Madrid'
# -----------------------------------------------------------------------------

if MODO not in ('DIAGNOSTICO', 'REAL'):
    log('KOROSHI AGRUPACIONES OUT - MODO desconocido: %s' % MODO)
    raise Warning("MODO tiene que ser 'DIAGNOSTICO' o 'REAL'")

Picking = env['stock.picking']
ahora = datetime.datetime.now(timezone(ZONA_HORARIA))
if env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    outs = Picking.browse(env.context.get('active_ids'))
else:
    medianoche = timezone(ZONA_HORARIA).localize(datetime.datetime(ahora.year, ahora.month, ahora.day))
    desde = medianoche.astimezone(timezone('UTC')).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    outs = Picking.search([('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                           ('state', '=', 'assigned'), ('batch_id', '=', False), ('create_date', '>=', desde),
                           ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO)])

# Solo OUT de salida de la empresa, preparadas y sin agrupacion
validas = Picking.browse()
saltadas = []
for p in outs:
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing':
        saltadas.append('%s: no es una OUT de la empresa %d' % (p.name, COMPANY_ID))
    elif p.state != 'assigned':
        saltadas.append('%s: no esta Preparada (%s)' % (p.name, p.state))
    elif p.batch_id:
        saltadas.append('%s: ya esta en la agrupacion %s' % (p.name, p.batch_id.name))
    else:
        validas |= p

# Ubicaciones y uds de cada OUT (lo reservado)
info = {}
for p in validas:
    ubis = {}
    uds = 0
    for ml in p.move_line_ids:
        ubis[ml.location_id.id] = 1
        uds += ml.product_uom_qty
    tienda = (p.partner_id.name or '').split(', ')[-1]
    info[p.id] = {'p': p, 'ubis': ubis, 'uds': uds, 'lineas': len(p.move_line_ids), 'tienda': tienda}

# Reparto: OUT con mas ubicaciones primero y despues las que mas ubicaciones comparten
pendientes = sorted(info.keys(), key=lambda i: -len(info[i]['ubis']))
grupos = []
while pendientes and (not MAX_AGRUPACIONES or len(grupos) < MAX_AGRUPACIONES):
    primero = pendientes.pop(0)
    grupo = [primero]
    ubis_grupo = dict(info[primero]['ubis'])
    while pendientes and len(grupo) < TAMANO:
        mejor = None
        mejor_comun = -1
        for i in pendientes:
            comun = 0
            for u in info[i]['ubis']:
                if u in ubis_grupo:
                    comun += 1
            if comun > mejor_comun:
                mejor = i
                mejor_comun = comun
        pendientes.remove(mejor)
        grupo.append(mejor)
        for u in info[mejor]['ubis']:
            ubis_grupo[u] = 1
    grupos.append((grupo, ubis_grupo))

hoy = ahora.strftime('%d%m')
Batch = env['stock.picking.batch']
ya = Batch.search_count([('name', '=like', '%s-%s-%%' % (PREFIJO, hoy))])
texto = ['KOROSHI AGRUPACIONES OUT - %s' % (MODO == 'REAL' and 'HECHO' or 'DIAGNOSTICO (NO SE HA CREADO NADA)'),
         'OUT preparadas sin agrupacion: %d | agrupaciones: %d de hasta %d OUT' % (len(validas), len(grupos), TAMANO), '']
creadas = []
n = ya
for grupo, ubis_grupo in grupos:
    n += 1
    nombre = '%s-%s-%02d' % (PREFIJO, hoy, n)
    uds = 0
    lineas = 0
    paradas_sueltas = 0
    tiendas = []
    for i in grupo:
        uds += info[i]['uds']
        lineas += info[i]['lineas']
        paradas_sueltas += len(info[i]['ubis'])
        tiendas.append(info[i]['tienda'].split(' - ')[0])
    paradas = len(ubis_grupo)
    ahorro = paradas_sueltas and 100.0 * (paradas_sueltas - paradas) / paradas_sueltas or 0
    texto.append('%s | %d OUT | %d uds | %d lineas | %d ubicaciones (sueltas %d: %.0f%% menos paradas) | %s' % (
        nombre, len(grupo), uds, lineas, paradas, paradas_sueltas, ahorro, ', '.join(tiendas)))
    if MODO == 'REAL':
        ids = []
        for i in grupo:
            ids.append(i)
        vals = {'name': nombre, 'picking_ids': [(6, 0, ids)]}
        if RESPONSABLE:
            vals['user_id'] = RESPONSABLE
        b = Batch.create(vals)
        b.action_confirm()
        creadas.append('%s (%s)' % (b.name, b.state))
if saltadas:
    texto.append('')
    texto.append('Se saltan %d:' % len(saltadas))
    for s in saltadas[:20]:
        texto.append('   ' + s)
if creadas:
    texto.append('')
    texto.append('Creadas: %s' % ', '.join(creadas))

mensaje = '\n'.join(texto)
log(mensaje)
if MODO == 'DIAGNOSTICO':
    raise Warning(mensaje + "\n\nEs un diagnostico: no se ha creado nada. Para crearlas: MODO = 'REAL'.")

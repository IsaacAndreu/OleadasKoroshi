# =============================================================================
# KOROSHI - COMPROBAR LOS BULTOS ANTES DE SACAR LA ETIQUETA GLS / XPO
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
# Se lanza desde la lista de albaranes: seleccionar las OUT de la tienda (o de varias) >
# Accion > "KOROSHI Comprobar bultos". Sin seleccion: todas las OUT validadas de hoy
# sin etiqueta de transportista.
#
# Por que: GLS y XPO juntan en un solo envio todas las OUT validadas de la tienda y suman
# su campo "Numero de bultos" (number_of_packages). Si alguien lo escribe a mano, la
# etiqueta sale con bultos que no existen (21/10: K69 con 11 en vez de 3, K77 con 6 en vez
# de 2: en una OUT se puso 9 y en otra 5 con una sola caja).
#
# Que hace, por tienda (las OUT validadas de esa tienda que aun no tienen etiqueta):
#   - Cajas reales: matriculas CJ distintas con uds. Cada caja cuenta en una sola OUT, la que
#     tiene mas uds dentro (igual que "Juntar matriculas" y "Recalcular bultos").
#   - Compara con el campo "Numero de bultos" de cada OUT y con la suma de la tienda.
#   - Avisa tambien de uds sin caja (lineas hechas sin matricula, que no cuentan como bulto).
# MODO = 'DIAGNOSTICO': no cambia nada, ensena lo que no cuadra (y acaba con un aviso).
# MODO = 'REAL': pone en cada OUT los bultos reales (solo en las que no cuadran y no tienen
#   etiqueta). El registro guarda "OUT: antes -> despues" para poder deshacerlo.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
MODO = 'DIAGNOSTICO'              # 'DIAGNOSTICO' (no cambia nada) o 'REAL'
SOLO_SIN_ETIQUETA = True          # True: solo OUT sin numero de seguimiento (las que van a la etiqueta)
TIPO_PEDIDO = 'PED. TIENDAS'      # sin seleccion: OUT de este tipo validadas hoy
ZONA_HORARIA = 'Europe/Madrid'
# -----------------------------------------------------------------------------

if MODO not in ('DIAGNOSTICO', 'REAL'):
    log('KOROSHI COMPROBAR BULTOS - MODO desconocido: %s' % MODO)
    raise Warning("MODO tiene que ser 'DIAGNOSTICO' o 'REAL'")

Picking = env['stock.picking']
Linea = env['stock.move.line']

# ---------------- 1. OUT de partida y tiendas ---------------------------------
if env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    elegidas = Picking.browse(env.context.get('active_ids'))
else:
    ahora = datetime.datetime.now(timezone(ZONA_HORARIA))
    medianoche = timezone(ZONA_HORARIA).localize(datetime.datetime(ahora.year, ahora.month, ahora.day))
    desde = medianoche.astimezone(timezone('UTC')).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    elegidas = Picking.search([('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                               ('state', '=', 'done'), ('date_done', '>=', desde),
                               ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO)])

tiendas = []                       # partner ids en orden
for p in elegidas:
    if p.company_id.id == COMPANY_ID and p.picking_type_code == 'outgoing' and p.partner_id.id not in tiendas:
        tiendas.append(p.partner_id.id)

if not tiendas:
    log('KOROSHI COMPROBAR BULTOS - no hay OUT')
    raise Warning('No hay OUT de salida de la empresa %d para comprobar.' % COMPANY_ID)

# ---------------- 2. Por tienda: cajas reales contra el campo -----------------
texto = ['KOROSHI COMPROBAR BULTOS - %s' % (MODO == 'REAL' and 'HECHO' or 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)'),
         'Tiendas: %d%s' % (len(tiendas), SOLO_SIN_ETIQUETA and ' (solo OUT validadas sin etiqueta)' or ''), '']
n_mal = 0
n_cambios = 0
for partner_id in tiendas:
    dominio = [('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
               ('state', '=', 'done'), ('partner_id', '=', partner_id)]
    if SOLO_SIN_ETIQUETA:
        dominio.append(('carrier_tracking_ref', '=', False))
    outs = Picking.search(dominio, order='id asc')
    if not outs:
        continue
    lineas = Linea.search([('picking_id', 'in', outs.ids), ('state', '!=', 'cancel'), ('qty_done', '>', 0)])
    reparto = {}                   # caja -> {out: uds}
    sin_caja = {}                  # out -> uds sin matricula
    for ml in lineas:
        pi = ml.picking_id.id
        if ml.result_package_id:
            pq = ml.result_package_id.id
            if pq not in reparto:
                reparto[pq] = {}
            reparto[pq][pi] = reparto[pq].get(pi, 0) + ml.qty_done
        else:
            sin_caja[pi] = sin_caja.get(pi, 0) + ml.qty_done
    cuenta = {}                    # out -> cajas que le tocan
    for pq in reparto:
        dueno = 0
        mejor = -1
        for pi in sorted(reparto[pq].keys()):
            if reparto[pq][pi] > mejor:
                dueno = pi
                mejor = reparto[pq][pi]
        cuenta[dueno] = cuenta.get(dueno, 0) + 1
    campo = sum(outs.mapped('number_of_packages'))
    reales = len(reparto)
    nombre = (outs[:1].partner_id.name or '').split(', ')[-1]
    malas = []
    for p in outs:
        n = cuenta.get(p.id, 0)
        if p.number_of_packages != n:
            malas.append((p, p.number_of_packages, n))
    estado = (campo == reales and not malas) and 'OK' or 'NO CUADRA'
    texto.append('%s | %s | %d OUT | bultos en Odoo %d | cajas reales %d' % (estado, nombre, len(outs), campo, reales))
    for c in malas:
        texto.append('   %s: pone %d bultos, tiene %d caja(s)%s' % (
            c[0].name, c[1], c[2], c[0].carrier_tracking_ref and ' (ya tiene etiqueta %s)' % c[0].carrier_tracking_ref or ''))
        if MODO == 'REAL' and not c[0].carrier_tracking_ref:
            c[0].write({'number_of_packages': c[2]})
            c[0].message_post(body='Comprobar bultos: %d -> %d (cajas reales con matricula)' % (c[1], c[2]))
            n_cambios += 1
    for pi in sin_caja:
        texto.append('   %s: %d uds sin matricula (no cuentan como bulto: meterlas en una caja o Juntar)' % (
            Picking.browse(pi).name, sin_caja[pi]))
    if malas or sin_caja:
        n_mal += 1
texto.append('')
texto.append('Tiendas que no cuadran: %d%s' % (n_mal, MODO == 'REAL' and (' | OUT corregidas: %d' % n_cambios) or ''))

mensaje = '\n'.join(texto)
log(mensaje)
if MODO == 'DIAGNOSTICO':
    raise Warning(mensaje + "\n\nEs un diagnostico: no se ha cambiado nada. Para corregir: MODO = 'REAL'.")
# Sin aviso al final en REAL: un raise Warning desharia el cambio. El resultado queda en el registro.

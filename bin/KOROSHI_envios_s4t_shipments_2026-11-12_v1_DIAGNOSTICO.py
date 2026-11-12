# =============================================================================
# KOROSHI - ENVIOS A S4T (POST /shipments) - DIAGNOSTICO          v1 12/11/2026
# Accion de servidor NUEVA (modelo sale.order). Se lanza a mano.
#
# NO ENVIA NADA A S4T. No escribe en pedidos ni en OUT. Solo deja en el
# Registro (Ajustes > Tecnico > Registro, nombre de la accion) lo que se
# enviaria a POST /shipments para cada pedido.
#
# Regla (12/11/2026):
#   - Un POST por cada tracking distinto (carrier_tracking_ref) de las OUT
#     hechas del pedido.
#   - carrier: XPO o GLS segun el transportista de la OUT.
#   - packages: cajas destino DISTINTAS (result_package_id) de esas OUT,
#     no la suma de number_of_packages (las cajas compartidas cuentan 1 vez).
#   - volume_m3: packages x 0,084 (caja plena), mientras no haya volumen real.
#   - weight_kg: peso de las OUT (shipping_weight si lo hay, si no weight).
#   - is_final: true solo en el ultimo tracking (por fecha de la OUT).
#   - Solo pedidos ya READY en S4T y con TODAS las OUT con tracking.
# =============================================================================

DESDE = '2026-11-01 00:00:00'   # fecha del pedido
LIMITE = 200                    # pedidos por pasada
VOLUMEN_CAJA = 0.084            # m3 de una caja plena
MAX_LINEAS_LOG = 120            # para no hacer un Registro enorme


# Campos de peso que existen en stock.picking (no se puede usar _fields).
campos_peso = env['ir.model.fields'].search([
    ('model', '=', 'stock.picking'),
    ('name', 'in', ['shipping_weight', 'weight']),
]).mapped('name')


def transportista_s4t(carrier):
    if not carrier:
        return ''
    texto = ((carrier.delivery_type or '') + ' ' + (carrier.name or '')).upper()
    if 'XPO' in texto:
        return 'XPO'
    if 'GLS' in texto:
        return 'GLS'
    return ''


def peso_out(p):
    for campo in ['shipping_weight', 'weight']:
        if campo in campos_peso and p[campo]:
            return p[campo]
    return 0.0


pedidos = env['sale.order'].search([
    ('name', 'like', 'S-6665%'),
    ('state', 'in', ['sale', 'done']),
    ('date_order', '>=', DESDE),
], order='date_order asc', limit=LIMITE)

lineas_ok = []
lineas_problema = []
n_pedidos_ok = 0
n_posts = 0
n_esperando_ready = 0
n_pendientes = 0
n_sin_tracking = 0
n_problema = 0

for order in pedidos:

    picks = order.picking_ids.filtered(
        lambda p: p.picking_type_id.code == 'outgoing' and p.state != 'cancel')
    if not picks:
        continue

    # OUT sin terminar: aun no toca.
    if any(p.state != 'done' for p in picks):
        n_pendientes += 1
        continue

    # Todas las OUT tienen que tener etiqueta.
    sin_tracking = picks.filtered(lambda p: not p.carrier_tracking_ref)
    if sin_tracking:
        n_sin_tracking += 1
        continue

    if order.x_s4t_status != 'READY':
        n_esperando_ready += 1
        lineas_problema.append('%s: OUT con etiqueta pero en S4T esta %s (primero batch-update)' % (
            order.name, order.x_s4t_status or 'VACIO'))
        continue

    problemas = []
    if not order.s4t_order_number:
        problemas.append('sin s4t_order_number')

    # Agrupar las OUT por tracking.
    grupos = {}
    for p in picks:
        ref = p.carrier_tracking_ref.strip()
        if ref not in grupos:
            grupos[ref] = env['stock.picking']
        grupos[ref] |= p

    # Orden de los envios: por la fecha de la OUT mas reciente de cada tracking.
    def fecha_grupo(ref):
        fechas = [str(x.date_done or x.write_date) for x in grupos[ref]]
        return max(fechas)
    refs = sorted(grupos.keys(), key=fecha_grupo)

    envios = []
    for i, ref in enumerate(refs):
        outs = grupos[ref]
        carriers = set([transportista_s4t(p.carrier_id) for p in outs])
        carrier = len(carriers) == 1 and list(carriers)[0] or ''
        cajas = outs.mapped('move_line_ids').filtered(
            lambda ml: ml.qty_done > 0 and ml.result_package_id).mapped('result_package_id')
        bultos = len(cajas)
        volumen = round(bultos * VOLUMEN_CAJA, 3)
        peso = round(sum([peso_out(p) for p in outs]), 2)

        if not carrier:
            problemas.append('%s: transportista no es GLS/XPO (%s)' % (
                ref, ', '.join(set([p.carrier_id.name or 'SIN TRANSPORTISTA' for p in outs]))))
        if bultos <= 0:
            problemas.append('%s: 0 cajas' % ref)
        if peso <= 0:
            problemas.append('%s: peso 0' % ref)
        if len(ref) > 50:
            problemas.append('%s: tracking de mas de 50 caracteres' % ref)

        envios.append('%s %s | %d bultos | %.3f m3 | %.2f kg | is_final=%s | %s' % (
            carrier or '???', ref, bultos, volumen, peso,
            i == len(refs) - 1 and 'true' or 'false',
            ', '.join(outs.mapped('name'))))

    if problemas:
        n_problema += 1
        lineas_problema.append('%s: %s' % (order.name, '; '.join(problemas)))
        continue

    n_pedidos_ok += 1
    n_posts += len(envios)
    lineas_ok.append('%s (order_number %s): %s' % (
        order.name, order.s4t_order_number, ' || '.join(envios)))


resumen = ('ENVIOS S4T (DIAGNOSTICO, NO SE HA ENVIADO NADA) desde %s: %d pedidos mirados. '
           '%d listos (%d POST), %d con problemas, %d con etiqueta pero sin READY, '
           '%d con OUT pendientes, %d con alguna OUT sin etiqueta. Campos de peso: %s'
           % (DESDE, len(pedidos), n_pedidos_ok, n_posts, n_problema, n_esperando_ready,
              n_pendientes, n_sin_tracking, ', '.join(campos_peso) or 'NINGUNO'))
if lineas_ok:
    resumen += '\n\nSE ENVIARIAN (%d):\n' % len(lineas_ok) + '\n'.join(lineas_ok[:MAX_LINEAS_LOG])
if lineas_problema:
    resumen += '\n\nNO SE ENVIARIAN (%d):\n' % len(lineas_problema) + '\n'.join(lineas_problema[:MAX_LINEAS_LOG])
log(resumen)

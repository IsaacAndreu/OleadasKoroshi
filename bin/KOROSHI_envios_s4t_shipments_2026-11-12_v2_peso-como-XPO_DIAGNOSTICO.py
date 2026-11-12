# =============================================================================
# KOROSHI - ENVIOS A S4T (POST /shipments) - DIAGNOSTICO          v2 12/11/2026
# Accion de servidor NUEVA (modelo sale.order). Se lanza a mano.
# Version anterior: KOROSHI_envios_s4t_shipments_2026-11-12_v1_DIAGNOSTICO.py
#
# NO ENVIA NADA A S4T. No escribe en pedidos ni en OUT. Solo deja en el
# Registro lo que se enviaria a POST /shipments para cada pedido.
#
# v2: peso y volumen calculados como delivery_xpo (EFFEC) al registrar la
#   expedicion, porque en Odoo no hay ningun peso (OUT, productos y cajas a 0):
#   - delivery_xpo: Peso = 15 + por cada OUT (shipping_weight si > 0, si no
#     sus bultos) -> en la practica 15 kg + 1 kg por caja.
#     Volumen = suma de volumen del producto x unidades (0,09 m3/ud si no tiene).
#   - delivery_gls_asm manda peso = suma de shipping_weight = 0 (GLS no usa
#     nuestro peso), asi que para GLS se usa la misma regla que XPO.
#   Aqui: weight_kg = PESO_BASE + PESO_CAJA x cajas distintas del tracking.
#   volume_m3 = suma volumen producto x unidades hechas de esas OUT.
#   Ademas mira los pedidos mas recientes primero.
# =============================================================================

DESDE = '2026-11-01 00:00:00'   # fecha del pedido
LIMITE = 200                    # pedidos por pasada (los mas recientes)
PESO_BASE = 15.0                # kg por envio (igual que delivery_xpo)
PESO_CAJA = 1.0                 # kg por caja (igual que delivery_xpo sin peso)
VOLUMEN_SIN_DATO = 0.09         # m3 por unidad si el producto no tiene volumen (delivery_xpo)
MAX_LINEAS_LOG = 120


def transportista_s4t(carrier):
    if not carrier:
        return ''
    texto = ((carrier.delivery_type or '') + ' ' + (carrier.name or '')).upper()
    if 'XPO' in texto:
        return 'XPO'
    if 'GLS' in texto:
        return 'GLS'
    return ''


pedidos = env['sale.order'].search([
    ('name', 'like', 'S-6665%'),
    ('state', 'in', ['sale', 'done']),
    ('date_order', '>=', DESDE),
], order='date_order desc', limit=LIMITE)

lineas_ok = []
lineas_problema = []
n_pedidos_ok = 0
n_posts = 0
n_esperando_ready = 0
n_pendientes = 0
n_sin_tracking = 0
n_problema = 0
n_varios_tracking = 0
n_sin_volumen = 0

for order in pedidos:

    picks = order.picking_ids.filtered(
        lambda p: p.picking_type_id.code == 'outgoing' and p.state != 'cancel')
    if not picks:
        continue

    if any(p.state != 'done' for p in picks):
        n_pendientes += 1
        continue

    if picks.filtered(lambda p: not p.carrier_tracking_ref):
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

    grupos = {}
    for p in picks:
        ref = p.carrier_tracking_ref.strip()
        if ref not in grupos:
            grupos[ref] = env['stock.picking']
        grupos[ref] |= p

    def fecha_grupo(ref):
        return max([str(x.date_done or x.write_date) for x in grupos[ref]])
    refs = sorted(grupos.keys(), key=fecha_grupo)
    if len(refs) > 1:
        n_varios_tracking += 1

    envios = []
    for i, ref in enumerate(refs):
        outs = grupos[ref]
        carriers = set([transportista_s4t(p.carrier_id) for p in outs])
        carrier = len(carriers) == 1 and list(carriers)[0] or ''
        lineas = outs.mapped('move_line_ids').filtered(lambda ml: ml.qty_done > 0)
        bultos = len(lineas.filtered(lambda ml: ml.result_package_id).mapped('result_package_id'))
        volumen = 0.0
        for ml in lineas:
            v = ml.product_id.volume
            if not v or v <= 0:
                v = VOLUMEN_SIN_DATO
                n_sin_volumen += 1
            volumen += v * ml.qty_done
        volumen = round(volumen, 3)
        peso = PESO_BASE + PESO_CAJA * bultos

        if not carrier:
            problemas.append('%s: transportista no es GLS/XPO (%s)' % (
                ref, ', '.join(set([p.carrier_id.name or 'SIN TRANSPORTISTA' for p in outs]))))
        if bultos <= 0:
            problemas.append('%s: 0 cajas' % ref)
        if volumen <= 0:
            problemas.append('%s: volumen 0' % ref)
        if len(ref) > 50:
            problemas.append('%s: tracking de mas de 50 caracteres' % ref)

        envios.append('%s %s | %d bultos | %.3f m3 | %.1f kg | is_final=%s | %s' % (
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


resumen = ('ENVIOS S4T v2 (DIAGNOSTICO, NO SE HA ENVIADO NADA) desde %s, recientes primero: %d pedidos mirados. '
           '%d listos (%d POST; %d con varios trackings), %d con problemas, %d con etiqueta pero sin READY, '
           '%d con OUT pendientes, %d con alguna OUT sin etiqueta. Lineas sin volumen de producto: %d. '
           'Peso = %.0f + %.0f kg/caja.'
           % (DESDE, len(pedidos), n_pedidos_ok, n_posts, n_varios_tracking, n_problema, n_esperando_ready,
              n_pendientes, n_sin_tracking, n_sin_volumen, PESO_BASE, PESO_CAJA))
if lineas_ok:
    resumen += '\n\nSE ENVIARIAN (%d):\n' % len(lineas_ok) + '\n'.join(lineas_ok[:MAX_LINEAS_LOG])
if lineas_problema:
    resumen += '\n\nNO SE ENVIARIAN (%d):\n' % len(lineas_problema) + '\n'.join(lineas_problema[:MAX_LINEAS_LOG])
log(resumen)

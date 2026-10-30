# Enviar al Expedidor (multiple) · acción de servidor 1834 (stock.picking)
# v2 (28/10/2026 15:13): a GLS solo se mandan las OUT con bultos. Las OUT juntadas
#   (0 bultos, sus prendas van dentro de la caja de otra OUT) no se mandan: el envío
#   agrupado de GLS las contaba como 1 bulto cada una (K85: 3 cajas -> 8 bultos).
#   Al acabar, las juntadas reciben el mismo tracking que la OUT con bultos de su
#   mismo cliente, para que también queden como enviadas.
#   Si un cliente no tiene ninguna OUT con bultos, sus OUT se mandan como antes.
# Versión anterior: bin/accion_1834_enviar_expedidor_2026-10-28_1513_ANTES.py

if any(records.mapped('carrier_tracking_ref')):
    raise Warning("Hay transferencias con TRACKING!!!")

carriers = records.mapped('carrier_id')
if len(carriers) != 1 or carriers[0].delivery_type != 'gls_asm':
    raise Warning("Solo disponible para GLS.")

# Clientes que tienen alguna OUT con bultos
partners_con = env['res.partner']
for p in records:
    if p.number_of_packages > 0:
        partners_con |= p.partner_id

enviar = env['stock.picking']
juntadas = env['stock.picking']
for p in records:
    if p.number_of_packages > 0 or p.partner_id not in partners_con:
        enviar |= p
    else:
        juntadas |= p

res = carriers[0].gls_asm_send_shipping(enviar)
track = {}
for picking, vals in zip(enviar, res):
    if vals.get('tracking_number') and not picking.carrier_tracking_ref:
        picking.write({
            'carrier_tracking_ref': vals['tracking_number'],
            'carrier_id': carriers[0].id,
        })
    if picking.carrier_tracking_ref and picking.partner_id.id not in track:
        track[picking.partner_id.id] = picking.carrier_tracking_ref

for p in juntadas:
    t = track.get(p.partner_id.id)
    if t:
        p.write({'carrier_tracking_ref': t, 'carrier_id': carriers[0].id})
        p.message_post(body='GLS: esta OUT no tiene bultos propios (juntada). Va dentro de la expedición ' + t + '.')

log('Enviar al Expedidor: %d OUT enviadas a GLS, %d juntadas con el mismo tracking' % (len(enviar), len(juntadas)))

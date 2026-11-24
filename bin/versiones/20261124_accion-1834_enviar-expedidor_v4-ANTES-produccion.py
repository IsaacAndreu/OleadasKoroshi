# Enviar al Expedidor (multiple) · acción de servidor 1834 (stock.picking)
# v2 (28/10/2026 15:13): a GLS solo se mandan las OUT con bultos. Las OUT juntadas
#   (0 bultos, sus prendas van dentro de la caja de otra OUT) no se mandan: el envío
#   agrupado de GLS las contaba como 1 bulto cada una (K85: 3 cajas -> 8 bultos).
#   Al acabar, las juntadas reciben el mismo tracking que la OUT con bultos de su
#   mismo cliente, para que también queden como enviadas.
#   Si un cliente no tiene ninguna OUT con bultos, sus OUT se mandan como antes.
# Versión anterior: bin/accion_1834_enviar_expedidor_2026-10-28_1513_ANTES.py

# if any(records.mapped('carrier_tracking_ref')):
#     raise Warning("Hay transferencias con TRACKING!!!")

# carriers = records.mapped('carrier_id')
# if len(carriers) != 1 or carriers[0].delivery_type != 'gls_asm':
#     raise Warning("Solo disponible para GLS.")

# # Clientes que tienen alguna OUT con bultos
# partners_con = env['res.partner']
# for p in records:
#     if p.number_of_packages > 0:
#         partners_con |= p.partner_id

# enviar = env['stock.picking']
# juntadas = env['stock.picking']
# for p in records:
#     if p.number_of_packages > 0 or p.partner_id not in partners_con:
#         enviar |= p
#     else:
#         juntadas |= p

# res = carriers[0].gls_asm_send_shipping(enviar)
# track = {}
# for picking, vals in zip(enviar, res):
#     if vals.get('tracking_number') and not picking.carrier_tracking_ref:
#         picking.write({
#             'carrier_tracking_ref': vals['tracking_number'],
#             'carrier_id': carriers[0].id,
#         })
#     if picking.carrier_tracking_ref and picking.partner_id.id not in track:
#         track[picking.partner_id.id] = picking.carrier_tracking_ref

# for p in juntadas:
#     t = track.get(p.partner_id.id)
#     if t:
#         p.write({'carrier_tracking_ref': t, 'carrier_id': carriers[0].id})
#         p.message_post(body='GLS: esta OUT no tiene bultos propios (juntada). Va dentro de la expedición ' + t + '.')

# log('Enviar al Expedidor: %d OUT enviadas a GLS, %d juntadas con el mismo tracking' % (len(enviar), len(juntadas)))

# Enviar al Expedidor (multiple) · acción de servidor 1834 (stock.picking)
# v2 (28/10/2026 15:13): a GLS solo se mandan las OUT con bultos. Las OUT juntadas
#   (0 bultos, sus prendas van dentro de la caja de otra OUT) no se mandan: el envío
#   agrupado de GLS las contaba como 1 bulto cada una (K85: 3 cajas -> 8 bultos).
#   Al acabar, las juntadas reciben el mismo tracking que la OUT con bultos de su
#   mismo cliente, para que también queden como enviadas.
#   Si un cliente no tiene ninguna OUT con bultos, sus OUT se mandan como antes.
# v3: si GLS no devuelve tracking_number se usa el código de barras; aviso en las OUT sin tracking.
# Versión anterior: bin/accion_1834_enviar_expedidor_2026-10-28_1513_ANTES.py

# Enviar al Expedidor (multiple) · acción de servidor 1834 (stock.picking)
# v2 (28/10/2026 15:13): a GLS solo se mandan las OUT con bultos. Las OUT juntadas
#   (0 bultos, sus prendas van dentro de la caja de otra OUT) no se mandan: el envío
#   agrupado de GLS las contaba como 1 bulto cada una (K85: 3 cajas -> 8 bultos).
#   Al acabar, las juntadas reciben el mismo tracking que la OUT con bultos de su
#   mismo cliente, para que también queden como enviadas.
#   Si un cliente no tiene ninguna OUT con bultos, sus OUT se mandan como antes.
# v3 (03/11/2026): envío de una en una; un error en una OUT no deshace las demás.
#   Si no llega tracking_number se usa el código de barras. Al final se abre la
#   lista de OUT con problemas.
# v4 (03/11/2026): error -70 (ya existe en GLS): se busca la expedición en el
#   manifiesto de GLS (7 días, mismo CP) y, si queda una sola candidata, se pone
#   su codexp como tracking. Si no, el chatter explica por qué.
#   Necesita carrier.gls_asm_manifiesto() en delivery_gls_asm/models/delivery_carrier.py.
# Versión anterior: bin/accion_1834_enviar_expedidor_2026-10-28_1513_ANTES.py

if any(records.mapped('carrier_tracking_ref')):
    raise Warning("Hay transferencias con TRACKING!!!")

campo_barras = 'gls_asm_public_tracking_ref'
if any(records.mapped(campo_barras)):
    raise Warning("Hay transferencias que ya se enviaron a GLS (tienen código de barras).")

carriers = records.mapped('carrier_id')
if len(carriers) != 1 or carriers[0].delivery_type != 'gls_asm':
    raise Warning("Solo disponible para GLS.")
carrier = carriers[0]

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

# Un envío (una expedición) por cliente
partner_ids = []
for p in enviar:
    if p.partner_id.id not in partner_ids:
        partner_ids.append(p.partner_id.id)

track = {}
sin_tracking = env['stock.picking']
con_error = env['stock.picking']
grupos_70 = []

for pid in partner_ids:
    grupo = enviar.filtered(lambda x: x.partner_id.id == pid)
    try:
        res = carrier.gls_asm_send_shipping(grupo)
    except Exception as e:
        msg = str(e.args[0]) if e.args else str(e)
        if msg.strip().endswith('-70'):
            grupos_70.append(grupo)
        else:
            con_error |= grupo
            for p in grupo:
                p.message_post(body='GLS: error al enviar. ' + msg)
        continue

    vals = res[0] if res else {}
    # TEMPORAL: ver qué devuelve el módulo
    grupo[0].message_post(body='DEBUG GLS tracking_number = %r' % (vals.get('tracking_number'),))

    ref = vals.get('tracking_number') or grupo[0][campo_barras] or False
    if ref:
        grupo.write({'carrier_tracking_ref': str(ref), 'carrier_id': carrier.id})
        track[pid] = str(ref)
    else:
        sin_tracking |= grupo
        for p in grupo:
            p.message_post(body='GLS: enviada pero NO se ha recibido tracking. Revisar en GLS antes de reenviar.')

# -70: ya estaba en GLS. Buscar la expedición en el manifiesto.
recuperadas = env['stock.picking']
ya_en_gls = env['stock.picking']
if grupos_70:
    manifiesto = []
    error_manifiesto = ''
    desde = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%d/%m/%Y')
    try:
        manifiesto = carrier.gls_asm_manifiesto(desde)
    except Exception as e:
        error_manifiesto = str(e.args[0]) if e.args else str(e)

    usados = set(track.values())
    for grupo in grupos_70:
        p0 = grupo[0]
        if error_manifiesto:
            ya_en_gls |= grupo
            for p in grupo:
                p.message_post(body='GLS -70: ya existe en GLS. NO reenviar. No se ha podido leer el manifiesto: ' + error_manifiesto)
            continue

        cp = (p0.partner_id.zip or '').strip().lstrip('0')
        bultos = sum([len(x.package_ids) if x.has_packages else 1 for x in grupo])
        mismo_cp = [x for x in manifiesto if (x.get('cp_dst') or '').strip().lstrip('0') == cp]
        cands = []
        for x in mismo_cp:
            codexp = x.get('codexp') or ''
            if not codexp or codexp in usados:
                continue
            if x.get('codestado') == '5':  # ANULADA
                continue
            if env['stock.picking'].search_count([('carrier_tracking_ref', '=', codexp)]):
                continue
            cands.append(x)
        cands_inicio = list(cands)

        if len(cands) > 1:
            nombre = (p0.partner_id.name or '').upper()[:12]
            filtro = [x for x in cands if nombre and nombre in (x.get('nombre_dst') or '').upper()]
            if filtro:
                cands = filtro
        if len(cands) > 1:
            filtro = [x for x in cands if x.get('bultos') == str(bultos)]
            if filtro:
                cands = filtro

        if len(cands) == 1:
            ref = cands[0].get('codexp')
            grupo.write({'carrier_tracking_ref': ref, 'carrier_id': carrier.id})
            usados.add(ref)
            track[p0.partner_id.id] = ref
            recuperadas |= grupo

            adjuntos = []
            try:
                pdf = carrier.gls_asm_get_label(ref)
                if pdf:
                    adjuntos = [('gls_label_' + ref + '.pdf', pdf)]
            except Exception:
                adjuntos = []

            texto = 'GLS -70: ya existía en GLS. Tracking recuperado del manifiesto: ' + ref + '. '
            texto += 'Etiqueta adjunta.' if adjuntos else 'GLS no ha devuelto la etiqueta con este código.'
            otras = [x for x in cands_inicio if x.get('codexp') != ref]
            if otras:
                texto += '<br/>OJO: en este CP hay otras expediciones sin OUT en Odoo, revisar si sobra alguna: ' + ', '.join(
                    ['%s (%s, %s bultos, %s)' % (x.get('codexp'), x.get('nombre_dst'), x.get('bultos'), x.get('estado')) for x in otras])
            for p in grupo:
                p.message_post(body=texto, attachments=adjuntos)
        else:
            ya_en_gls |= grupo
            vistos = ', '.join(['%s (%s, %s bultos, %s)' % (
                x.get('codexp'), x.get('nombre_dst'), x.get('bultos'), x.get('estado')) for x in mismo_cp[:10]])
            texto = ('GLS -70: ya existe en GLS pero no se ha podido identificar la expedición. NO reenviar.<br/>'
                     'Manifiesto desde %s: %d expediciones; %d al CP %s: %s.<br/>Candidatas: %d. Bultos del envío: %d.' % (
                         desde, len(manifiesto), len(mismo_cp), cp or '(vacío)', vistos or 'ninguna', len(cands), bultos))
            for p in grupo:
                p.message_post(body=texto)

# Juntadas: mismo tracking que la expedición de su cliente
juntadas_sin = env['stock.picking']
for p in juntadas:
    t = track.get(p.partner_id.id)
    if t:
        p.write({'carrier_tracking_ref': t, 'carrier_id': carrier.id})
        p.message_post(body='GLS: esta OUT no tiene bultos propios (juntada). Va dentro de la expedición ' + t + '.')
    else:
        juntadas_sin |= p

log('Enviar al Expedidor: %d OUT enviadas en %d expediciones, %d sin tracking, %d recuperadas (-70), %d -70 sin identificar, %d con error, %d juntadas' % (
    len(enviar), len(partner_ids), len(sin_tracking), len(recuperadas), len(ya_en_gls), len(con_error), len(juntadas)))

# Si algo ha ido mal, abrir la lista de OUT con problemas
problemas = sin_tracking | ya_en_gls | con_error | juntadas_sin
if problemas:
    action = {
        'type': 'ir.actions.act_window',
        'name': 'OUT con problemas en GLS',
        'res_model': 'stock.picking',
        'view_mode': 'tree,form',
        'views': [(False, 'tree'), (False, 'form')],
        'domain': [('id', 'in', problemas.ids)],
    }
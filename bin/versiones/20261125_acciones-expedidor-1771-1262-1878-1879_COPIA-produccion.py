# COPIA de produccion (solo lectura, 25/11/2026, leida por XML-RPC con Departament IT).
# Acciones de servidor de stock.picking que usa Expediciones para sacar etiquetas. NO se ha cambiado nada.
# La 1834 (GLS, v5) esta en 20261124_accion-1834_enviar-expedidor_v5-cajas-compartidas-APLICADA-produccion.py.

# ====================================================================================================
# Accion 1771: Enviar al Expedidor (multiple) (modificada 2026-07-09 07:28:27)
# ====================================================================================================
trackings = records.mapped('carrier_tracking_ref')
trackings = set(trackings)
if len(trackings) >= 1 and list(trackings)[0] != False:
  raise Warning("Hay transferencias con TRACKING!!!")
  
carrier_id = records.mapped('carrier_id')
carrier_id = set(carrier_id)

if len(carrier_id) >= 1 and list(carrier_id)[0].id != 173:
  raise Warning("Solo disponible para XPO.")
  
carrier = list(carrier_id)[0]

if carrier:
  carrier.xpo_es_send_shipping(records)
  trackings = records.mapped('carrier_tracking_ref')
  trackings = set(trackings)
  if len(trackings) == 1:
    records.write({'carrier_id': carrier.id})

# ====================================================================================================
# Accion 1262: Print Shipping Label (modificada 2022-09-25 06:53:20)
# ====================================================================================================
action = records.shipping_label_pdf()

# ====================================================================================================
# Accion 1878: Enviar al Expedidor (multiple) (modificada 2026-11-03 15:34:15)
# ====================================================================================================
carrier = records.mapped('carrier_id').filtered(lambda c: c.delivery_type == 'gls_asm')[:1]
if not carrier:
    carrier = env['delivery.carrier'].search([('delivery_type', '=', 'gls_asm')], limit=1)
hoy = datetime.date.today()
desde = (hoy - datetime.timedelta(days=7)).strftime('%d/%m/%Y')
hasta = hoy.strftime('%d/%m/%Y')
for p in records:
    texto = carrier.gls_asm_diagnostico(desde, hasta, [p.name, p.name[:15]])
    texto = texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    p.message_post(body='<pre>' + texto + '</pre>')

# ====================================================================================================
# Accion 1879: Enviar al Expedidor (multiple) (modificada 2026-11-03 15:39:05)
# ====================================================================================================
# Recuperar etiqueta GLS (stock.picking). Solo lectura en GLS: no envía nada.
campo_barras = 'gls_asm_public_tracking_ref'
carrier = records.mapped('carrier_id').filtered(lambda c: c.delivery_type == 'gls_asm')[:1]
if not carrier:
    carrier = env['delivery.carrier'].search([('delivery_type', '=', 'gls_asm')], limit=1)

for p in records:
    codigos = []
    info = []
    if p[campo_barras]:
        codigos.append(p[campo_barras])

    # Buscar la expedición por la referencia que guarda GLS (15 caracteres)
    exps = []
    try:
        exps = carrier.gls_asm_buscar_expedicion(p.name[:15])
    except Exception as ex:
        info.append('No se ha podido buscar la expedición: ' + (str(ex.args[0]) if ex.args else str(ex)))
    for e in exps:
        if e.get('codbar') and e.get('codbar') not in codigos:
            codigos.append(e.get('codbar'))
        info.append('Expedición %s, código de barras %s, %s bultos, %s, borrado=%s' % (
            e.get('codexp'), e.get('codbar'), e.get('bultos'), e.get('estado'), e.get('borrado')))
        if e.get('borrado') == 'S':
            info.append('OJO: GLS la marca como borrada. Comprobar en el portal antes de usar la etiqueta.')
    if p.name[:15] not in codigos:
        codigos.append(p.name[:15])

    pdf = False
    usado = ''
    for c in codigos:
        if not pdf:
            try:
                pdf = carrier.gls_asm_get_label(c)
                usado = c
            except Exception as ex:
                info.append('Etiqueta con %s: error %s' % (c, str(ex.args[0]) if ex.args else str(ex)))

    detalle = '<br/>'.join(info)
    if pdf:
        p.message_post(
            body='GLS: etiqueta recuperada con ' + usado + '.' + ('<br/>' + detalle if detalle else ''),
            attachments=[('gls_label_' + usado + '.pdf', pdf)],
        )
    else:
        p.message_post(body='GLS: no ha devuelto etiqueta. Probado con: ' + ', '.join(codigos) + ('<br/>' + detalle if detalle else ''))


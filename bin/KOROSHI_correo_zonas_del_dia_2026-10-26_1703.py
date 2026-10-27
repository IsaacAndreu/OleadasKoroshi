# =============================================================================
# KOROSHI - CORREO CON EL MAPA Y LAS LINEAS DE CADA ZONA DEL DIA
# Accion planificada de Odoo 13 (modelo stock.picking). Se lanza despues de partir las OUT por zonas.
#
# Busca las agrupaciones de zona de hoy (Z-ddmm-...) y envia un correo con:
#   - el resultado de la accion de partir (lo que apunto en el registro: hecho o fallo);
#   - el mapa: cada lineal con el color de su zona;
#   - por zona: uds, OUT, tiendas y lineales;
#   - por zona: las lineas a coger, ordenadas por ubicacion (ubicacion, articulo, uds, caja y tienda).
# Si no hay agrupaciones de hoy, el correo lo dice (y trae el registro de la accion de partir).
# PRUEBA = True: no envia nada, ensena el tamano del correo en un aviso.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
EMAIL = 'isaac.andreu@nath.es'
ZONA_HORARIA = 'Europe/Madrid'
DIA = ''                          # '' = hoy; 'ddmm' para otro dia (pruebas)
PRUEBA = False
COLORES = ['#2f7d4f', '#1f5fbf', '#b5562a', '#7a4bb0', '#b08a12', '#0e7c86', '#b03a6c', '#5b6b1e', '#6b6a65']
# -----------------------------------------------------------------------------


def lineal(nombre):
    # '07859 - L94 P27 C2' -> 94; sin lineal -> 0
    for t in (nombre or '').replace('/', ' ').split(' '):
        if len(t) > 1 and t[0] == 'L' and t[1:].isdigit():
            return int(t[1:])
    return 0


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


ahora = datetime.datetime.now(timezone(ZONA_HORARIA))
dia = DIA or ahora.strftime('%d%m')
lotes = env['stock.picking.batch'].search([('name', '=like', 'Z-%s-%%' % dia), ('company_id', '=', COMPANY_ID)], order='name')
desde = (datetime.datetime.now() - datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
reg = env['ir.logging'].search([('message', 'like', 'KOROSHI PARTIR OUT ZONAS'), ('create_date', '>=', desde)],
                               order='id desc', limit=1)

color = {}
mapa = {}                          # lineal -> zona
resumen = []
detalle = []
total_uds = 0
for i, lote in enumerate(lotes):
    zona = lote.name[len('Z-%s-' % dia):].strip() or lote.name
    color[zona] = COLORES[i % len(COLORES)]
    filas = []
    uds = 0
    tiendas = {}
    lineales = {}
    for o in lote.picking_ids:
        nota = o.note or ''
        caja = ''
        if 'CAJA ' in nota:
            caja = nota.split('CAJA ')[1].split(' ')[0]
        tienda = (o.partner_id.name or '').split(', ')[-1].split(' - ')[0]
        tiendas[tienda] = 1
        for ml in o.move_line_ids:
            q = ml.product_uom_qty or ml.qty_done
            if not q:
                continue
            loc = ml.location_id
            if (loc.name or '')[:3] in ('KO_', 'TT_') and loc.location_id:
                loc = loc.location_id
            ln = lineal(loc.name)
            if ln:
                lineales[ln] = 1
                mapa[ln] = zona
            uds += q
            filas.append((loc.complete_name or '', loc.name or '', ml.product_id.display_name or '', q, caja, tienda))
    total_uds += uds
    lin = sorted(lineales.keys())
    resumen.append('<tr><td style="padding:4px 8px"><b style="color:%s">%s</b></td><td style="padding:4px 8px;text-align:right">%d</td>'
                   '<td style="padding:4px 8px;text-align:right">%d</td><td style="padding:4px 8px;text-align:right">%d</td>'
                   '<td style="padding:4px 8px">%s</td></tr>' % (
                       color[zona], esc(lote.name), uds, len(lote.picking_ids), len(tiendas),
                       lin and ('L%d - L%d' % (lin[0], lin[-1])) or 'fuera de lineal'))
    filas = sorted(filas, key=lambda f: f[0])
    t = ['<h3 style="color:%s;margin:22px 0 6px">%s · %d uds · %d lineas</h3>' % (color[zona], esc(lote.name), uds, len(filas)),
         '<table style="border-collapse:collapse;font-size:12px"><tr style="background:#eee"><th style="padding:3px 6px;text-align:left">Ubicacion</th>'
         '<th style="padding:3px 6px;text-align:left">Articulo</th><th style="padding:3px 6px">Uds</th><th style="padding:3px 6px">Caja</th>'
         '<th style="padding:3px 6px;text-align:left">Tienda</th></tr>']
    for f in filas:
        t.append('<tr><td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td><td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td>'
                 '<td style="padding:2px 6px;border-bottom:1px solid #eee;text-align:right">%d</td><td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td>'
                 '<td style="padding:2px 6px;border-bottom:1px solid #eee">%s</td></tr>' % (esc(f[1]), esc(f[2]), f[3], esc(f[4]), esc(f[5])))
    t.append('</table>')
    detalle.append(''.join(t))

# Mapa: lineales del 1 al maximo, 20 por fila, con el color de su zona
celdas = []
maxl = mapa and max(mapa.keys()) or 0
fila = []
for n in range(1, maxl + 1):
    z = mapa.get(n)
    if z:
        fila.append('<td title="L%d %s" style="width:30px;height:24px;text-align:center;font-size:10px;color:#fff;background:%s">%d<br>%s</td>' % (n, z, color[z], n, z))
    else:
        fila.append('<td style="width:30px;height:24px;text-align:center;font-size:10px;color:#999;background:#f2f2f2">%d</td>' % n)
    if len(fila) == 20:
        celdas.append('<tr>%s</tr>' % ''.join(fila))
        fila = []
if fila:
    celdas.append('<tr>%s</tr>' % ''.join(fila))

estado = reg and reg.message.split('\n')[0] or 'No hay registro de la accion de partir en las ultimas 8 horas'
partes = ['<div style="font-family:Arial,sans-serif;color:#222">',
          '<h2 style="margin:0 0 4px">Zonas de picking %s/%s</h2>' % (dia[:2], dia[2:]),
          '<p style="margin:0 0 12px;color:#555">Accion de partir: <b>%s</b></p>' % esc(estado)]
if lotes:
    partes.append('<p>%d zonas · %d uds</p>' % (len(lotes), total_uds))
    partes.append('<table style="border-collapse:collapse;font-size:13px"><tr style="background:#eee"><th style="padding:4px 8px;text-align:left">Zona</th>'
                  '<th style="padding:4px 8px">Uds</th><th style="padding:4px 8px">OUT</th><th style="padding:4px 8px">Tiendas</th>'
                  '<th style="padding:4px 8px;text-align:left">Lineales</th></tr>%s</table>' % ''.join(resumen))
    partes.append('<h3 style="margin:22px 0 6px">Mapa de lineales</h3><table style="border-collapse:separate;border-spacing:2px">%s</table>' % ''.join(celdas))
    partes.append(''.join(detalle))
else:
    partes.append('<p><b>No hay agrupaciones de zona de hoy (Z-%s-...).</b></p>' % dia)
    if reg:
        partes.append('<pre style="font-size:12px">%s</pre>' % esc(reg.message[:6000]))
partes.append('</div>')
html = ''.join(partes)

if PRUEBA:
    log('KOROSHI CORREO ZONAS - PRUEBA: %d zonas, %d uds, %d caracteres' % (len(lotes), total_uds, len(html)))
    raise Warning('PRUEBA (no se ha enviado): %d zonas, %d uds, correo de %d caracteres a %s.\n\n%s' % (
        len(lotes), total_uds, len(html), EMAIL, estado))

correo = env['mail.mail'].create({
    'subject': 'KOROSHI zonas de picking %s/%s: %d zonas, %d uds' % (dia[:2], dia[2:], len(lotes), total_uds),
    'email_to': EMAIL,
    'body_html': html,
    'auto_delete': False,
})
correo.send()
log('KOROSHI CORREO ZONAS - enviado a %s: %d zonas, %d uds (estado %s)' % (EMAIL, len(lotes), total_uds, correo.state))

# =============================================================================
# KOROSHI - RECOGIDA DE INFORMACION 2 (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Completa la informacion para el diseno de matriculas y oleadas de EFFEC:
#   K. Que hacen los modulos propios (sorter_batch, koroshi_zebra, ...).
#   L. Validaciones existentes (acciones de servidor y automatizadas).
#   M. Como se han preparado las ultimas OUT de tienda (usuarios, cajas, tiempo).
#   N. Unidades por caja (matriculas CJ) en las OUT de tienda.
#   O. Campos propios de agrupaciones, paquetes y lineas.
#   P. URL de Odoo.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

COMPANY_ID = 8
PREFIJO_TIENDAS = 'S-66'
DIAS = 14
MAX_LINEAS_MENSAJE = 260

ahora_utc = datetime.datetime.utcnow()
desde_txt = (ahora_utc - datetime.timedelta(days=DIAS)).strftime('%Y-%m-%d %H:%M:%S')
lineas = []
lineas.append('INFO 2 KOROSHI (company_id %d) - SOLO LECTURA - %s UTC' % (COMPANY_ID, ahora_utc.strftime('%d/%m/%Y %H:%M')))

# ---------------- K. Modulos propios -----------------------------------------
lineas.append('')
lineas.append('K. MODULOS (nombre | descripcion | autor | modelos que definen)')
modulos = ['sorter_batch', 'barcode_batch_process', 'koroshi_zebra', 'api_s4t_batch_update_PROD',
           'dms_package_consume', 'delivery_package_number', 'bs_batch_shipment_label_print',
           'custom_reports_koroshi_v2', 'koroshi_sale_order', 'barcode_location_process', 'stock_barcode_optimization']
for nombre in modulos:
    mod = env['ir.module.module'].search([('name', '=', nombre)], limit=1)
    if not mod:
        continue
    # Modelos definidos por el modulo (ir.model.data: el campo ir.model.modules no se puede filtrar)
    datos_modelo = env['ir.model.data'].search([('module', '=', nombre), ('model', '=', 'ir.model')])
    modelos = env['ir.model'].browse(datos_modelo.mapped('res_id')).mapped('model')
    lineas.append('   %s [%s] | %s | %s | %s' % (nombre, mod.state, (mod.shortdesc or '-')[:80], (mod.author or '-')[:40], ', '.join(modelos[:8]) or '-'))
    if mod.summary:
        lineas.append('      resumen: %s' % mod.summary[:150])

# ---------------- L. Validaciones existentes ---------------------------------
lineas.append('')
lineas.append('L. ACCIONES DE SERVIDOR Y AUTOMATIZADAS SOBRE ALBARANES / PAQUETES / AGRUPACIONES')
modelos_l = ['stock.picking', 'stock.quant.package', 'stock.picking.batch', 'stock.move.line']
acciones = env['ir.actions.server'].search([('model_id.model', 'in', modelos_l)], order='id asc')
automatizadas = {}
if 'base.automation' in env:
    for a in env['base.automation'].search([('model_id.model', 'in', modelos_l)]):
        automatizadas[a.action_server_id.id] = '%s (activa=%s)' % (a.trigger, a.active)
for a in acciones:
    disparo = automatizadas.get(a.id, 'manual/contextual')
    lineas.append('   id %d | %s | %s | %s | %s' % (a.id, a.name, a.model_id.model, a.state, disparo))
    if a.state == 'code' and a.code:
        for linea_codigo in a.code.split('\n'):
            texto = linea_codigo.strip()
            if 'raise' in texto or 'Warning(' in texto or 'UserError(' in texto:
                lineas.append('        > %s' % texto[:160])

# ---------------- M. Ultimas OUT de tienda hechas ----------------------------
lineas.append('')
lineas.append('M. ULTIMAS 5 OUT DE TIENDA HECHAS (como se han preparado)')
hechas = env['stock.picking'].search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('origin', '=like', PREFIJO_TIENDAS + '%'),
    ('state', '=', 'done'),
    ('partner_id.name', '=like', 'K%'),
], order='date_done desc', limit=5)
for p in hechas:
    mls = p.move_line_ids
    paquetes = mls.mapped('result_package_id')
    usuarios = {}
    for ml in mls:
        usuarios[ml.write_uid.name or '-'] = usuarios.get(ml.write_uid.name or '-', 0) + 1
    fechas = mls.mapped('write_date')
    duracion = ''
    if fechas:
        duracion = '%s -> %s' % (min(fechas).strftime('%d/%m %H:%M'), max(fechas).strftime('%d/%m %H:%M'))
    texto_usuarios = []
    for u in usuarios.keys():
        texto_usuarios.append('%s:%d' % (u, usuarios[u]))
    lineas.append('   %s | %s | oleada %s | %d uds | %d cajas | lineas escritas por %s | %s | validado por %s'
                  % (p.name, p.partner_id.name, p.batch_id.name or '-', sum(mls.mapped('qty_done')), len(paquetes),
                     ', '.join(texto_usuarios), duracion, p.write_uid.name or '-'))

# ---------------- N. Unidades por caja ---------------------------------------
lineas.append('')
lineas.append('N. UNIDADES POR CAJA (matriculas en OUT de tienda hechas, ultimos %d dias)' % DIAS)
grupos = env['stock.move.line'].read_group([
    ('state', '=', 'done'),
    ('picking_id.company_id', '=', COMPANY_ID),
    ('picking_id.origin', '=like', PREFIJO_TIENDAS + '%'),
    ('picking_id.partner_id.name', '=like', 'K%'),
    ('result_package_id', '!=', False),
    ('date', '>=', desde_txt),
], ['result_package_id', 'qty_done'], ['result_package_id'])
tramos = {'01-05': 0, '06-10': 0, '11-15': 0, '16-20': 0, '21-30': 0, '31+': 0}
total_uds = 0.0
prefijos_caja = {}
for g in grupos:
    q = g.get('qty_done') or 0.0
    total_uds += q
    nombre_paquete = g['result_package_id'] and g['result_package_id'][1] or ''
    pref = nombre_paquete[:2]
    prefijos_caja[pref] = prefijos_caja.get(pref, 0) + 1
    if q <= 5:
        tramos['01-05'] += 1
    elif q <= 10:
        tramos['06-10'] += 1
    elif q <= 15:
        tramos['11-15'] += 1
    elif q <= 20:
        tramos['16-20'] += 1
    elif q <= 30:
        tramos['21-30'] += 1
    else:
        tramos['31+'] += 1
n_cajas = len(grupos)
lineas.append('   Cajas: %d | unidades: %d | media %.1f uds/caja' % (n_cajas, total_uds, n_cajas and total_uds / n_cajas or 0.0))
texto_tramos = []
for k in sorted(tramos.keys()):
    texto_tramos.append('%s uds: %d' % (k, tramos[k]))
lineas.append('   Reparto: %s' % ', '.join(texto_tramos))
texto_pref = []
for k in sorted(prefijos_caja.keys()):
    texto_pref.append('%s: %d' % (k, prefijos_caja[k]))
lineas.append('   Prefijo de las cajas: %s' % ', '.join(texto_pref))

# ---------------- O. Campos propios ------------------------------------------
lineas.append('')
lineas.append('O. CAMPOS PROPIOS (x_ y de modulos no estandar)')
for modelo in ['stock.picking.batch', 'stock.quant.package', 'stock.move.line', 'stock.picking']:
    texto_campos = []
    # Campos creados a mano (x_...)
    for c in env['ir.model.fields'].search([('model', '=', modelo), ('state', '=', 'manual')]):
        texto_campos.append('%s(%s)' % (c.name, c.ttype))
    # Campos anadidos por modulos no estandar (por su xmlid field_<modelo>__<campo>)
    prefijo_xmlid = 'field_' + modelo.replace('.', '_') + '__%'
    estandar = ['stock', 'stock_picking_batch', 'delivery', 'base', 'mail', 'product', 'sale_stock', 'purchase_stock',
                'stock_account', 'mrp', 'point_of_sale', 'stock_barcode', 'sale', 'purchase', 'web', 'portal']
    for d in env['ir.model.data'].search([('model', '=', 'ir.model.fields'), ('name', '=like', prefijo_xmlid), ('module', 'not in', estandar)]):
        c = env['ir.model.fields'].browse(d.res_id)
        texto_campos.append('%s(%s, %s)' % (c.name, c.ttype, d.module))
    lineas.append('   %s: %s' % (modelo, ', '.join(texto_campos[:40]) or '-'))
tiene_company = env['ir.model.fields'].search_count([('model', '=', 'stock.picking.batch'), ('name', '=', 'company_id')])
lineas.append('   stock.picking.batch tiene company_id: %s' % (tiene_company and 'si' or 'no'))

# ---------------- P. URL de Odoo ---------------------------------------------
lineas.append('')
lineas.append('P. URL BASE DE ODOO: %s' % env['ir.config_parameter'].sudo().get_param('web.base.url'))

texto_completo = '\n'.join(lineas)
log('KOROSHI INFO 2 DIAGNOSTICO\n%s' % texto_completo)

if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]

raise Warning('\n'.join(lineas))

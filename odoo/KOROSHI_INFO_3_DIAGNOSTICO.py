# =============================================================================
# KOROSHI - RECOGIDA DE INFORMACION 3 (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
#   Q. Codigo de las acciones clave (reglas automaticas de matriculas, sorter,
#      oleadas). Las lineas con claves/contrasenas se tapan con ***.
#   R. Cuando se disparan las acciones automatizadas (dominios).
#   S. Etiquetas de matricula (koroshi_zebra): campos, secuencia y ultimos registros.
#   T. Sorter (sorter_batch): campos y ultimos registros.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# Acciones de servidor cuyo codigo se muestra
IDS_ACCIONES = [1705, 1789, 1812, 1632, 1633, 1644, 1804, 1786, 1811]
MAX_LINEAS_CODIGO = 90
MAX_LINEAS_MENSAJE = 400
PALABRAS_SECRETAS = ['password', 'passwd', 'pwd', 'api_key', 'apikey', 'token', 'secret', 'x-api-key', 'authorization']

lineas = []
lineas.append('INFO 3 KOROSHI - SOLO LECTURA - %s UTC' % datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M'))

# ---------------- R. Disparadores de las acciones automatizadas ---------------
lineas.append('')
lineas.append('R. ACCIONES AUTOMATIZADAS (base.automation) SOBRE stock.picking / stock.move.line / stock.quant.package')
if 'base.automation' in env:
    tiene_campos_disparo = env['ir.model.fields'].search_count([('model', '=', 'base.automation'), ('name', '=', 'trigger_field_ids')])
    for a in env['base.automation'].search([('model_id.model', 'in', ['stock.picking', 'stock.move.line', 'stock.quant.package', 'stock.picking.batch'])]):
        lineas.append('   accion %d | %s | trigger=%s | activa=%s' % (a.action_server_id.id, a.name, a.trigger, a.active))
        lineas.append('      antes (filter_pre_domain): %s' % (a.filter_pre_domain or '-'))
        lineas.append('      despues (filter_domain): %s' % (a.filter_domain or '-'))
        if tiene_campos_disparo:
            lineas.append('      campos que la disparan: %s' % (', '.join(a.trigger_field_ids.mapped('name')) or 'todos'))

# ---------------- Q. Codigo de las acciones clave ----------------------------
lineas.append('')
lineas.append('Q. CODIGO DE LAS ACCIONES CLAVE')
for accion in env['ir.actions.server'].browse(IDS_ACCIONES).exists():
    lineas.append('')
    lineas.append('   ===== id %d | %s | modelo %s =====' % (accion.id, accion.name, accion.model_id.model))
    codigo = (accion.code or '').split('\n')
    n = 0
    for linea_codigo in codigo:
        texto = linea_codigo.rstrip()
        sin_espacios = texto.strip()
        if not sin_espacios or sin_espacios.startswith('#'):
            continue
        minus = texto.lower()
        secreta = False
        for palabra in PALABRAS_SECRETAS:
            if palabra in minus:
                secreta = True
        if secreta:
            texto = texto[:texto.find(sin_espacios[0])] + '*** (linea tapada: contiene credenciales)'
        n += 1
        if n > MAX_LINEAS_CODIGO:
            lineas.append('   ... (%d lineas mas)' % (len(codigo) - MAX_LINEAS_CODIGO))
            break
        lineas.append('   ' + texto[:170])

# ---------------- S. Etiquetas de matricula (koroshi_zebra) ------------------
lineas.append('')
lineas.append('S. KOROSHI ZEBRA (zebra.label)')
if 'zebra.label' in env:
    campos = env['ir.model.fields'].search([('model', '=', 'zebra.label')])
    texto_campos = []
    for c in campos:
        if c.name not in ['create_uid', 'create_date', 'write_uid', 'write_date', '__last_update', 'display_name']:
            texto_campos.append('%s(%s)' % (c.name, c.ttype))
    lineas.append('   Campos: %s' % ', '.join(texto_campos))
    lineas.append('   Registros: %d' % env['zebra.label'].search_count([]))
    for r in env['zebra.label'].search([], order='id desc', limit=5):
        valores = []
        for c in campos:
            if c.ttype in ['char', 'integer', 'boolean', 'selection', 'float', 'datetime', 'date'] and c.name not in ['__last_update']:
                valores.append('%s=%s' % (c.name, r[c.name]))
            elif c.ttype == 'many2one':
                valores.append('%s=%s' % (c.name, r[c.name].display_name))
        lineas.append('   - %s' % ' | '.join(valores)[:300])
for s in env['ir.sequence'].search(['|', ('prefix', 'ilike', 'CJ'), ('code', 'ilike', 'zebra')]):
    lineas.append('   Secuencia: %s | code %s | prefijo %s | relleno %d | siguiente %d' % (s.name, s.code or '-', s.prefix or '', s.padding, s.number_next_actual))

# ---------------- T. Sorter (sorter_batch) -----------------------------------
lineas.append('')
lineas.append('T. SORTER (sorter.batch)')
if 'sorter.batch' in env:
    campos = env['ir.model.fields'].search([('model', '=', 'sorter.batch')])
    texto_campos = []
    for c in campos:
        if c.name not in ['create_uid', 'create_date', 'write_uid', 'write_date', '__last_update', 'display_name']:
            texto_campos.append('%s(%s)' % (c.name, c.ttype))
    lineas.append('   Campos: %s' % ', '.join(texto_campos))
    lineas.append('   Registros: %d' % env['sorter.batch'].search_count([]))
    for r in env['sorter.batch'].search([], order='id desc', limit=5):
        valores = []
        for c in campos:
            if c.ttype in ['char', 'integer', 'boolean', 'selection', 'float', 'datetime', 'date'] and c.name not in ['__last_update']:
                valores.append('%s=%s' % (c.name, r[c.name]))
            elif c.ttype == 'many2one':
                valores.append('%s=%s' % (c.name, r[c.name].display_name))
            elif c.ttype in ['one2many', 'many2many']:
                valores.append('%s=%d' % (c.name, len(r[c.name])))
        lineas.append('   - %s' % ' | '.join(valores)[:300])
campos_sorter_picking = env['ir.model.data'].search([('module', '=', 'sorter_batch'), ('model', '=', 'ir.model.fields')])
texto_sp = []
for d in campos_sorter_picking:
    c = env['ir.model.fields'].browse(d.res_id)
    texto_sp.append('%s.%s(%s)' % (c.model, c.name, c.ttype))
lineas.append('   Campos que anade el modulo: %s' % (', '.join(texto_sp) or '-'))
for ubic in env['stock.location'].search([('name', 'ilike', 'SORTER')], limit=10):
    lineas.append('   Ubicacion: %s (empresa %s)' % (ubic.complete_name, ubic.company_id.name or '-'))

texto_completo = '\n'.join(lineas)
log('KOROSHI INFO 3 DIAGNOSTICO\n%s' % texto_completo)

if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]

raise Warning('\n'.join(lineas))

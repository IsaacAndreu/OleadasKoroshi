# =============================================================================
# KOROSHI - DIAGNOSTICO PARA LA PANTALLA DE PREPARACION EN LECTURAS (opcion B)
# SOLO LECTURA. 10/11/2026.
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Saca los datos que necesita el plan 20261110_PLAN_preparacion_en_lecturas_v1.md
# (supuestos X1-X12 y preguntas S1-S10):
#   A. Modulos instalados y versiones            J. Que anaden stock_barcode_optimization y cia
#   K. Acciones automaticas, crones y colas      B. Tipos de operacion de la company 8
#   C. Ajustes globales y nomenclatura           D. Usuarios, PDA y operarios
#   P. Tareas dejada/otro con la OUT validada    I. Productos y codigos de barras
#   L. Ubicaciones                               E. Volumen y forma de las OUT del tipo 45
#   F. Paquetes, lotes y propietarios            G. Comportamiento de la app actual
#   H. Lotes de zona Z- (stock.picking.batch)
#
# REGLAS:
#   - NO ESCRIBE NADA. Solo search/search_count/read_group/search_read.
#     Termina siempre con un Warning. La unica escritura es el log() en
#     ir.logging, que Odoo hace con su propio cursor.
#   - Sin f-strings, sin import, sin nombres con doble guion bajo.
#   - log() SIEMPRE antes del raise.
#   - Nunca se leen login ni email de usuarios/empleados: solo id, nombre y recuentos.
#   - Las lineas con palabras de credenciales se tapan con ***.
#
# PARTE: el mensaje completo es largo. Para leerlo por partes en pantalla,
# poner PARTE = '1' (A, J, K), '2' (B, C, D, P, I, L) o '3' (E, F, G, H).
# Con 'TODO' saca todo; el detalle completo siempre queda en
# Ajustes > Tecnico > Registros (ir.logging). Cambiar PARTE solo cambia
# que se lee: el script no escribe en ningun caso.
# =============================================================================

PARTE = 'TODO'
COMPANY_ID = 8
PREFIJO_TIENDAS = 'S-66'
TIPO_OUT_TIENDAS = 45
DIAS = 14
DIAS_DETALLE = 3
LIMITE_DETALLE = 30000
MAX_LINEAS_MENSAJE = 400
PALABRAS_SECRETAS = ['password', 'passwd', 'pwd', 'api_key', 'apikey', 'token', 'secret', 'x-api-key', 'authorization']
LISTA_MODULOS = ['stock_barcode', 'stock_barcode_optimization', 'barcode_batch_process', 'barcode_location_process',
                 'barcode_archive_location', 'stock_picking_batch', 'sorter_batch', 'koroshi_zebra', 'koroshi_operarios',
                 'koroshi_faltantes', 'koroshi_caja_existente', 'koroshi_monitor', 'koroshi_xpo_bultos', 'koroshi_kpi',
                 'delivery_package_number', 'dms_package_consume', 'api_s4t_batch_update_PROD', 'queue_job',
                 'stock_barcode_mobile', 'web_mobile', 'delivery_xpo']
MODULOS_TERCEROS = ['stock_barcode_optimization', 'barcode_batch_process', 'barcode_location_process', 'barcode_archive_location']
MODELOS_STOCK = ['stock.picking', 'stock.move', 'stock.move.line', 'stock.quant.package', 'stock.picking.batch', 'stock.production.lot']
MODULOS_BASE_TIPO = ['base', 'stock', 'stock_barcode', 'mail', 'stock_account', 'stock_picking_batch', 'mrp', 'purchase_stock', 'sale_stock', 'delivery']

ahora_utc = datetime.datetime.utcnow()
desde_txt = (ahora_utc - datetime.timedelta(days=DIAS)).strftime('%Y-%m-%d %H:%M:%S')
desde_detalle_txt = (ahora_utc - datetime.timedelta(days=DIAS_DETALLE)).strftime('%Y-%m-%d %H:%M:%S')
desde_2d_txt = (ahora_utc - datetime.timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')

try:
    tz_local = timezone('Europe/Madrid')
    tz_utc = timezone('UTC')
except:
    tz_local = False
    tz_utc = False

lineas = []


def tapar(texto):
    texto = '%s' % (texto,)
    minus = texto.lower()
    for palabra in PALABRAS_SECRETAS:
        if palabra in minus:
            return '*** (tapado: contiene credenciales)'
    if '@' in texto and '.' in texto:
        return '*** (tapado: parece un email)'
    return texto


def campo_existe(modelo, campo):
    return env['ir.model.fields'].search_count([('model', '=', modelo), ('name', '=', campo)]) > 0


def ref_id(modulo, nombre):
    d = env['ir.model.data'].search([('module', '=', modulo), ('name', '=', nombre)], limit=1)
    return d and d.res_id or False


def xmlid(modelo, res_id):
    d = env['ir.model.data'].search([('model', '=', modelo), ('res_id', '=', res_id)], limit=1)
    return d and (d.module + '.' + d.name) or '-'


def resumen(valores, formato):
    if not valores:
        return 'sin datos'
    v = sorted(valores)
    n = len(v)
    p50 = v[int(0.5 * (n - 1))]
    p90 = v[int(0.9 * (n - 1))]
    return 'n=%d | min %s | p50 %s | p90 %s | max %s' % (n, formato % v[0], formato % p50, formato % p90, formato % v[-1])


def hora_local(dt):
    if not dt:
        return False
    if tz_local:
        return tz_utc.localize(dt).astimezone(tz_local)
    return dt + datetime.timedelta(hours=1)


def valor(registro, campo, ttype):
    v = registro[campo]
    if ttype == 'many2one':
        return v.display_name or '-'
    if ttype in ['one2many', 'many2many']:
        return '%d' % len(v)
    return tapar(v)


def trozos(texto, marca, maximo):
    # Devuelve los valores entre comillas que siguen a marca (src=", expr=")
    salida = []
    partes = (texto or '').split(marca)
    for parte in partes[1:]:
        fin = parte.find('"')
        if fin > 0:
            salida.append(parte[:fin])
        if len(salida) >= maximo:
            break
    return salida


def toca(parte):
    return PARTE == 'TODO' or PARTE == parte


def error_bloque(bloque, e):
    lineas.append('   ERROR en el bloque %s (no se ha escrito nada): %s' % (bloque, tapar(e)))
    lineas.append('   Si el error es de base de datos, los bloques siguientes pueden fallar: volver a lanzar con otra PARTE.')


lineas.append('KOROSHI PREPARACION EN LECTURAS - DIAGNOSTICO (company %d) - SOLO LECTURA - %s UTC - PARTE %s'
              % (COMPANY_ID, ahora_utc.strftime('%d/%m/%Y %H:%M'), PARTE))

dom_out_done = [('picking_id.picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done'), ('date', '>=', desde_txt)]

# =============================================================================
# PARTE 1: A, J, K
# =============================================================================

# ---------------- A. Modulos instalados ----------------------------------------
if toca('1'):
    lineas.append('')
    lineas.append('A1. MODULOS DE LA LISTA (nombre | estado | instalada | ultima | autor | depende de)')
    try:
        tiene_published = campo_existe('ir.module.module', 'published_version')
        encontrados = []
        for m in env['ir.module.module'].search([('name', 'in', LISTA_MODULOS)], order='name'):
            encontrados.append(m.name)
            extra = ''
            if tiene_published:
                extra = ' | publicada %s' % (m.published_version or '-')
            lineas.append('   %s | %s | %s | %s%s | %s | %s' % (m.name, m.state, m.installed_version or '-', m.latest_version or '-',
                                                              extra, (m.author or '-')[:40], ', '.join(m.dependencies_id.mapped('name'))[:160]))
        no_estan = []
        for n in LISTA_MODULOS:
            if n not in encontrados:
                no_estan.append(n)
        lineas.append('   No existen en el servidor: %s' % (', '.join(no_estan) or '-'))
        lineas.append('   (comparar koroshi_* con local: operarios 2.3, faltantes 1.3.1, caja_existente 1.3, monitor 1.18.2)')

        lineas.append('')
        lineas.append('A2. MODULOS QUE DEPENDEN DE stock_barcode')
        for d in env['ir.module.module.dependency'].search([('name', '=', 'stock_barcode')]):
            lineas.append('   %s (%s)' % (d.module_id.name, d.module_id.state))

        lineas.append('')
        lineas.append('A3. MODULOS INSTALADOS CON barcode/batch/picking/scan/pda/package/lot/wave EN EL NOMBRE')
        palabras = ['barcode', 'batch', 'picking', 'scan', 'pda', 'package', 'lot', 'wave']
        dominio_mod = [('state', '=', 'installed')]
        for i in range(len(palabras) - 1):
            dominio_mod.append('|')
        for pal in palabras:
            dominio_mod.append(('name', 'ilike', pal))
        lineas.append('   %s' % ', '.join(sorted(env['ir.module.module'].search(dominio_mod).mapped('name'))))
    except Exception as e:
        error_bloque('A', e)

# ---------------- J. Que anaden los modulos de terceros ------------------------
if toca('1'):
    lineas.append('')
    lineas.append('J. QUE ANADEN LOS MODULOS DE TERCEROS (S1, X1, X2, X8)')
    try:
        for MOD in MODULOS_TERCEROS:
            lineas.append('')
            lineas.append('   ===== %s =====' % MOD)
            grupos = env['ir.model.data'].read_group([('module', '=', MOD)], ['model'], ['model'])
            if not grupos:
                lineas.append('   (sin registros en ir.model.data: no instalado o sin datos)')
                continue
            texto = []
            for g in grupos:
                texto.append('%s=%d' % (g['model'], g['model_count']))
            lineas.append('   J1 registros por modelo: %s' % ', '.join(texto))

            # J2 vistas
            ids_vistas = env['ir.model.data'].search([('module', '=', MOD), ('model', '=', 'ir.ui.view')]).mapped('res_id')
            for v in env['ir.ui.view'].with_context(active_test=False).browse(ids_vistas).exists():
                padre = v.inherit_id and xmlid('ir.ui.view', v.inherit_id.id) or '-'
                arch = v.arch_db or ''
                lineas.append('   J2 vista %d | %s | key %s | %s | modelo %s | modo %s | hereda %s | activa %s | prioridad %d | %d car.'
                              % (v.id, v.name, v.key or '-', v.type, v.model or '-', v.mode, padre, v.active, v.priority, len(arch)))
                if padre in ['web.assets_backend', 'web.assets_common', 'web.assets_frontend']:
                    for ruta in trozos(arch, 'src="', 40) + trozos(arch, 'href="', 20):
                        lineas.append('        fichero: %s' % ruta)
                elif v.type == 'qweb' or v.model in ['stock.picking', 'stock.move.line', 'stock.picking.type', 'stock.picking.batch']:
                    exprs = trozos(arch, 'expr="', 25)
                    if exprs:
                        lineas.append('        expr: %s' % ' || '.join(exprs)[:600])
                    nombres = trozos(arch, 'name="', 25)
                    if nombres:
                        lineas.append('        name: %s' % ', '.join(nombres)[:400])

            # J3 campos
            ids_campos = env['ir.model.data'].search([('module', '=', MOD), ('model', '=', 'ir.model.fields')]).mapped('res_id')
            for c in env['ir.model.fields'].browse(ids_campos).exists():
                lineas.append('   J3 campo %s.%s (%s) store=%s relacion=%s compute=%s depends=%s'
                              % (c.model, c.name, c.ttype, c.store, c.relation or '-', c.compute and 'si' or 'no', (c.depends or '-')[:80]))

            # J5 permisos y reglas
            ids_acc = env['ir.model.data'].search([('module', '=', MOD), ('model', '=', 'ir.model.access')]).mapped('res_id')
            for a in env['ir.model.access'].browse(ids_acc).exists():
                lineas.append('   J5 acceso %s | grupo %s | r%d w%d c%d u%d' % (a.model_id.model, a.group_id.name or 'todos',
                                                                          a.perm_read, a.perm_write, a.perm_create, a.perm_unlink))
            ids_reg = env['ir.model.data'].search([('module', '=', MOD), ('model', '=', 'ir.rule')]).mapped('res_id')
            for r in env['ir.rule'].browse(ids_reg).exists():
                lineas.append('   J5 regla %s | %s | %s' % (r.model_id.model, r.name, (r.domain_force or '-')[:150]))

            # H5 (parte): acciones de servidor del modulo
            ids_srv = env['ir.model.data'].search([('module', '=', MOD), ('model', '=', 'ir.actions.server')]).mapped('res_id')
            for s in env['ir.actions.server'].browse(ids_srv).exists():
                lineas.append('   accion servidor %d | %s | modelo %s | estado %s' % (s.id, s.name, s.model_id.model, s.state))

        lineas.append('')
        lineas.append('J4. ACCIONES CLIENTE CON tag barcode / picking / batch')
        for a in env['ir.actions.client'].search(['|', '|', ('tag', 'ilike', 'barcode'), ('tag', 'ilike', 'picking'), ('tag', 'ilike', 'batch')]):
            lineas.append('   %d | %s | tag %s | modelo %s | xml_id %s | context %s'
                          % (a.id, a.name, a.tag, a.res_model or '-', xmlid('ir.actions.client', a.id), tapar(a.context or '-')[:120]))

        lineas.append('')
        lineas.append('J6. VISTAS DE stock_barcode HEREDADAS POR OTROS MODULOS (huella sobre Enterprise)')
        ids_sb = env['ir.model.data'].search([('module', '=', 'stock_barcode'), ('model', '=', 'ir.ui.view')]).mapped('res_id')
        herederas = env['ir.ui.view'].with_context(active_test=False).search([('inherit_id', 'in', ids_sb)])
        for v in herederas:
            propia = xmlid('ir.ui.view', v.id)
            if propia.startswith('stock_barcode.'):
                continue
            lineas.append('   %s (activa %s) hereda %s' % (propia, v.active, xmlid('ir.ui.view', v.inherit_id.id)))
    except Exception as e:
        error_bloque('J', e)

# ---------------- K. Acciones automaticas, crones y colas ----------------------
if toca('1'):
    lineas.append('')
    lineas.append('K1. ACCIONES AUTOMATICAS SOBRE LOS MODELOS DE STOCK (S3, X11)')
    try:
        if 'base.automation' in env:
            tiene_disparo = campo_existe('base.automation', 'trigger_field_ids')
            for a in env['base.automation'].with_context(active_test=False).search([('model_id.model', 'in', MODELOS_STOCK)]):
                marca = ''
                if a.model_id.model == 'stock.move.line' and a.trigger in ['on_write', 'on_create_or_write']:
                    marca = '  <== SE DISPARARIA EN CADA LECTURA'
                lineas.append('   %d | %s | modelo %s | trigger=%s | activa=%s | accion servidor %d%s'
                              % (a.id, a.name, a.model_id.model, a.trigger, a.active, a.action_server_id.id, marca))
                lineas.append('      antes: %s | despues: %s' % ((a.filter_pre_domain or '-')[:150], (a.filter_domain or '-')[:150]))
                if tiene_disparo:
                    lineas.append('      campos que la disparan: %s' % (', '.join(a.trigger_field_ids.mapped('name')) or 'todos'))
        else:
            lineas.append('   base.automation no instalado')

        lineas.append('')
        lineas.append('K2. CRONES ACTIVOS SOBRE STOCK O CON koroshi / S4T / batch / zona EN EL NOMBRE')
        dom_cron = ['|', '|', '|', '|', ('model_id.model', 'in', MODELOS_STOCK), ('name', 'ilike', 'koroshi'),
                    ('name', 'ilike', 'S4T'), ('name', 'ilike', 'batch'), ('name', 'ilike', 'zona')]
        for c in env['ir.cron'].search(dom_cron):
            lineas.append('   %d | %s | cada %d %s | proxima %s UTC' % (c.id, c.name, c.interval_number, c.interval_type, c.nextcall))
        c186 = env['ir.cron'].with_context(active_test=False).browse(186).exists()
        if c186:
            lineas.append('   (cron 186: %s, activo=%s)' % (c186.name, c186.active))

        lineas.append('')
        lineas.append('K3. COLAS (queue.job) DE LOS ULTIMOS 2 DIAS (X7)')
        if 'queue.job' in env:
            Job = env['queue.job']
            for g in Job.read_group([('date_created', '>=', desde_2d_txt)], ['channel'], ['channel']):
                estados = Job.read_group([('date_created', '>=', desde_2d_txt), ('channel', '=', g['channel'])], ['state'], ['state'])
                texto = []
                for s in estados:
                    texto.append('%s=%d' % (s['state'], s['state_count']))
                lineas.append('   canal %s: %s' % (g['channel'] or '-', ', '.join(texto)))
            for g in Job.read_group([('date_created', '>=', desde_2d_txt), ('model_name', '=', 'stock.picking')], ['method_name'], ['method_name']):
                lineas.append('   stock.picking.%s: %d trabajos' % (g['method_name'] or '-', g['method_name_count']))
        else:
            lineas.append('   queue.job no instalado')
    except Exception as e:
        error_bloque('K', e)

# =============================================================================
# PARTE 2: B, C, D, P, I, L
# =============================================================================

# ---------------- B. Tipos de operacion ----------------------------------------
if toca('2'):
    lineas.append('')
    lineas.append('B1. TIPOS DE OPERACION DE LA COMPANY %d (S4, X9)' % COMPANY_ID)
    try:
        estandar = ['code', 'active', 'sequence_code', 'use_create_lots', 'use_existing_lots', 'show_operations',
                    'show_reserved', 'show_entire_packs', 'barcode']
        presentes = []
        for c in estandar:
            if campo_existe('stock.picking.type', c):
                presentes.append(c)
        extras = []
        for f in env['ir.model.fields'].search([('model', '=', 'stock.picking.type')]):
            mods = [x.strip() for x in (f.modules or '').split(',') if x.strip()]
            ajenos = [x for x in mods if x not in MODULOS_BASE_TIPO]
            if ajenos and f.name not in presentes:
                extras.append((f.name, f.ttype, ', '.join(ajenos)))
        lineas.append('   Campos de otros modulos en stock.picking.type: %s'
                      % (', '.join(['%s(%s, %s)' % (e[0], e[1], e[2]) for e in extras]) or '-'))
        tipos = env['stock.picking.type'].with_context(active_test=False).search([('company_id', '=', COMPANY_ID)], order='id')
        for t in tipos:
            datos = []
            for c in presentes:
                datos.append('%s=%s' % (c, tapar(t[c])))
            lineas.append('   %d | %s | almacen %s | origen %s | destino %s | devolucion %s | prefijo %s'
                          % (t.id, t.name, t.warehouse_id.code or '-', t.default_location_src_id.complete_name or '-',
                             t.default_location_dest_id.complete_name or '-', t.return_picking_type_id.name or '-',
                             t.sequence_id.prefix or '-'))
            lineas.append('      %s' % ' '.join(datos))
            if extras:
                datos_extra = []
                for e in extras:
                    try:
                        datos_extra.append('%s=%s' % (e[0], valor(t, e[0], e[1])))
                    except Exception:
                        datos_extra.append('%s=?' % e[0])
                lineas.append('      terceros: %s' % ' '.join(datos_extra)[:400])
            if t.code in ['outgoing', 'internal']:
                n_assigned = env['stock.picking'].search_count([('picking_type_id', '=', t.id), ('state', '=', 'assigned')])
                n_espera = env['stock.picking'].search_count([('picking_type_id', '=', t.id), ('state', 'in', ['waiting', 'confirmed'])])
                n_done = env['stock.picking'].search_count([('picking_type_id', '=', t.id), ('state', '=', 'done'), ('date_done', '>=', desde_txt)])
                lineas.append('      B2: assigned %d | waiting/confirmed %d | done %d dias %d' % (n_assigned, n_espera, DIAS, n_done))
        ejemplo = env['stock.picking'].search([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done')], order='id desc', limit=3)
        lineas.append('   Tipo %d: ultimas OUT %s | origen %s' % (TIPO_OUT_TIENDAS, ', '.join(ejemplo.mapped('name')) or '-',
                                                            ', '.join([(o or '-')[:12] for o in ejemplo.mapped('origin')]) or '-'))
        n_s66 = env['stock.picking'].search_count([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('origin', '=like', PREFIJO_TIENDAS + '%'), ('date_done', '>=', desde_txt)])
        lineas.append('   Tipo %d con origen %s... validadas en %d dias: %d' % (TIPO_OUT_TIENDAS, PREFIJO_TIENDAS, DIAS, n_s66))
    except Exception as e:
        error_bloque('B', e)

# ---------------- C. Ajustes globales ------------------------------------------
if toca('2'):
    lineas.append('')
    lineas.append('C1. GRUPOS DE AJUSTES (implicado en Usuario interno | usuarios internos que lo tienen)')
    try:
        id_user = ref_id('base', 'group_user')
        implicados = id_user and env['res.groups'].browse(id_user).implied_ids.ids or []
        for xid in ['stock.group_tracking_lot', 'stock.group_production_lot', 'stock.group_tracking_owner',
                    'stock.group_stock_multi_locations', 'stock.group_adv_location', 'product.group_stock_packaging',
                    'uom.group_uom', 'stock.group_stock_multi_warehouses']:
            partes = xid.split('.')
            gid = ref_id(partes[0], partes[1])
            if not gid:
                lineas.append('   %s: no existe' % xid)
                continue
            n_us = env['res.users'].search_count([('groups_id', 'in', [gid]), ('share', '=', False)])
            lineas.append('   %s: implicado=%s | usuarios=%d' % (xid, gid in implicados, n_us))

        lineas.append('')
        lineas.append('C2. NOMENCLATURA DE CODIGOS DE BARRAS (S6)')
        if campo_existe('res.company', 'nomenclature_id'):
            nom = env['res.company'].browse(COMPANY_ID).nomenclature_id
            lineas.append('   Nomenclatura: %s (upc_ean_conv=%s)' % (nom.name or '-', nom.upc_ean_conv if nom else '-'))
            for r in env['barcode.rule'].search([('barcode_nomenclature_id', '=', nom.id)], order='sequence'):
                lineas.append('   regla %d | %s | tipo %s | codif %s | patron %s' % (r.sequence, r.name, r.type, r.encoding, r.pattern))
        else:
            lineas.append('   res.company no tiene nomenclature_id')

        lineas.append('')
        lineas.append('C3. PARAMETROS DEL SISTEMA (barcode / stock / koroshi / operario / faltante / preparacion)')
        for p in env['ir.config_parameter'].sudo().search(['|', '|', '|', '|', '|', ('key', 'ilike', 'barcode'), ('key', 'ilike', 'stock'),
                                                           ('key', 'ilike', 'koroshi'), ('key', 'ilike', 'operario'),
                                                           ('key', 'ilike', 'faltante'), ('key', 'ilike', 'preparacion')], order='key'):
            lineas.append('   %s = %s' % (p.key, tapar(p.value)[:120]))
        if env['ir.config_parameter'].sudo().search_count([('key', 'ilike', 'koroshi_preparacion')]):
            lineas.append('   OJO: ya existe algun parametro koroshi_preparacion.*')
    except Exception as e:
        error_bloque('C', e)

# ---------------- D. Usuarios, PDA y operarios ---------------------------------
if toca('2'):
    lineas.append('')
    lineas.append('D1. USUARIOS INTERNOS DE LA COMPANY %d CON GRUPO USUARIO DE INVENTARIO (id | nombre | accion inicio | company | responsable)' % COMPANY_ID)
    try:
        g_user = ref_id('stock', 'group_stock_user')
        g_mgr = ref_id('stock', 'group_stock_manager')
        usuarios = env['res.users'].search([('share', '=', False), ('company_ids', 'in', [COMPANY_ID]), ('groups_id', 'in', [g_user])], order='id', limit=80)
        for u in usuarios:
            lineas.append('   %d | %s | %s | %d | %s' % (u.id, u.name, u.action_id.name or '-', u.company_id.id, g_mgr in u.groups_id.ids))
        lineas.append('   Total: %d (maximo 80 listados)' % len(usuarios))

        lineas.append('')
        lineas.append('D2. QUIEN ESCRIBE LAS move.line DE LAS OUT DEL TIPO %d (%d dias, done) (S5, X10)' % (TIPO_OUT_TIENDAS, DIAS))
        grupos = env['stock.move.line'].read_group(dom_out_done, ['write_uid'], ['write_uid'], orderby='write_uid')
        grupos = sorted(grupos, key=lambda g: -g['write_uid_count'])
        for g in grupos[:40]:
            lineas.append('   usuario %s: %d lineas' % (g['write_uid'] and ('%d %s' % (g['write_uid'][0], g['write_uid'][1])) or '-', g['write_uid_count']))
        lineas.append('   Usuarios distintos: %d' % len(grupos))

        lineas.append('')
        lineas.append('D3. MODELOS koroshi.* (registros y campos)')
        for m in env['ir.model'].search([('model', '=like', 'koroshi.%')], order='model'):
            try:
                n = env[m.model].search_count([])
            except Exception:
                n = -1
            lineas.append('   %s: %d registros' % (m.model, n))
            if m.model.startswith('koroshi.operario') or m.model.startswith('koroshi.faltante') or m.model.startswith('koroshi.preparacion'):
                campos = env['ir.model.fields'].search([('model', '=', m.model), ('name', 'not in', ['create_uid', 'create_date', 'write_uid', 'write_date', 'display_name', 'id'])])
                lineas.append('      %s' % ', '.join(['%s(%s)' % (c.name, c.ttype) for c in campos])[:500])

        lineas.append('')
        lineas.append('D4. EMPLEADOS DE LA COMPANY %d' % COMPANY_ID)
        Emp = env['hr.employee']
        lineas.append('   total %d | con tarjeta (barcode) %d | con usuario %d'
                      % (Emp.search_count([('company_id', '=', COMPANY_ID)]),
                         campo_existe('hr.employee', 'barcode') and Emp.search_count([('company_id', '=', COMPANY_ID), ('barcode', '!=', False)]) or 0,
                         Emp.search_count([('company_id', '=', COMPANY_ID), ('user_id', '!=', False)])))
    except Exception as e:
        error_bloque('D', e)

# ---------------- P. Tareas dejada/otro con la OUT validada (S8) ---------------
if toca('2'):
    lineas.append('')
    lineas.append('P. TAREAS DE OPERARIOS CERRADAS COMO dejada/otro CON LA OUT YA VALIDADA (S8, fallo de empezar)')
    try:
        if 'koroshi.operario.tarea' in env:
            Tarea = env['koroshi.operario.tarea']
            dom_t = [('company_id', '=', COMPANY_ID), ('estado', '=', 'dejada'), ('motivo_fin', '=', 'otro'), ('inicio', '>=', desde_txt)]
            total = Tarea.search_count(dom_t)
            con_done = Tarea.search_count(dom_t + [('picking_id.state', '=', 'done')])
            lineas.append('   dejada/otro en %d dias: %d | con la OUT done: %d' % (DIAS, total, con_done))
            antes = 0
            ejemplos = []
            for t in Tarea.search(dom_t + [('picking_id.state', '=', 'done')], limit=2000):
                if t.fin and t.picking_id.date_done and t.picking_id.date_done <= t.fin:
                    antes += 1
                    if len(ejemplos) < 5:
                        ejemplos.append('%s (tarea %d)' % (t.picking_id.name, t.id))
            lineas.append('   ... de ellas, la OUT se valido ANTES de cerrar la tarea: %d | ejemplos: %s' % (antes, ', '.join(ejemplos) or '-'))
            for g in Tarea.read_group([('company_id', '=', COMPANY_ID), ('inicio', '>=', desde_txt)], ['estado'], ['estado']):
                lineas.append('   estado %s: %d' % (g['estado'], g['estado_count']))
        else:
            lineas.append('   koroshi.operario.tarea no existe')
    except Exception as e:
        error_bloque('P', e)

# ---------------- I. Productos y codigos de barras -----------------------------
if toca('2'):
    lineas.append('')
    lineas.append('I1. PRODUCTOS DE LAS OUT DEL TIPO %d (%d dias, done) (S6, S7)' % (TIPO_OUT_TIENDAS, DIAS))
    try:
        grupos = env['stock.move'].read_group([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done'), ('date', '>=', desde_txt)],
                                              ['product_id', 'product_uom_qty'], ['product_id'])
        ids_prod = []
        uds_prod = {}
        for g in grupos:
            if g.get('product_id'):
                ids_prod.append(g['product_id'][0])
                uds_prod[g['product_id'][0]] = g.get('product_uom_qty') or 0.0
        productos = env['product.product'].with_context(active_test=False).browse(ids_prod)
        n = len(productos)
        n_bar = 0
        uds_bar = 0.0
        uds_tot = 0.0
        n_ref = 0
        tracking = {}
        uoms = {}
        tipos = {}
        for p in productos:
            q = uds_prod.get(p.id, 0.0)
            uds_tot += q
            if p.barcode:
                n_bar += 1
                uds_bar += q
            if p.default_code:
                n_ref += 1
            tracking[p.tracking] = tracking.get(p.tracking, 0) + 1
            uoms[p.uom_id.name] = uoms.get(p.uom_id.name, 0) + 1
            tipos[p.type] = tipos.get(p.type, 0) + 1
        if n:
            lineas.append('   productos %d | con barcode %d (%.1f %%) | uds con barcode %.1f %% | con referencia %d (%.1f %%)'
                          % (n, n_bar, 100.0 * n_bar / n, uds_tot and 100.0 * uds_bar / uds_tot or 0.0, n_ref, 100.0 * n_ref / n))
        lineas.append('   tracking: %s | uom: %s | tipo: %s' % (tracking, uoms, tipos))

        lineas.append('')
        lineas.append('I2. CODIGOS DUPLICADOS Y CHOQUES CON CAJAS / UBICACIONES / TARJETAS (S6)')
        barcodes = [b for b in productos.mapped('barcode') if b]
        dup = 0
        ej_dup = []
        choque_paq = 0
        choque_ubi = 0
        choque_emp = 0
        tiene_emp_bar = campo_existe('hr.employee', 'barcode')
        i = 0
        while i < len(barcodes):
            tanda = barcodes[i:i + 500]
            i += 500
            cuenta = {}
            for pr in env['product.product'].with_context(active_test=False).search_read([('barcode', 'in', tanda)], ['barcode']):
                cuenta[pr['barcode']] = cuenta.get(pr['barcode'], 0) + 1
            for k in cuenta:
                if cuenta[k] > 1:
                    dup += 1
                    if len(ej_dup) < 5:
                        ej_dup.append('%s x%d' % (k, cuenta[k]))
            choque_paq += env['stock.quant.package'].search_count([('name', 'in', tanda)])
            choque_ubi += env['stock.location'].with_context(active_test=False).search_count([('barcode', 'in', tanda)])
            if tiene_emp_bar:
                choque_emp += env['hr.employee'].with_context(active_test=False).search_count([('barcode', 'in', tanda)])
        lineas.append('   barcodes revisados %d | repetidos en varios productos %d %s' % (len(barcodes), dup, ej_dup))
        lineas.append('   coinciden con nombre de paquete %d | con barcode de ubicacion %d | con tarjeta de empleado %d'
                      % (choque_paq, choque_ubi, choque_emp))
        refs = [r for r in productos.mapped('default_code') if r]
        n_ref_bar = 0
        i = 0
        while i < len(refs):
            n_ref_bar += env['product.product'].with_context(active_test=False).search_count([('barcode', 'in', refs[i:i + 500])])
            i += 500
        lineas.append('   referencias (default_code) que son el barcode de algun producto: %d' % n_ref_bar)

        lineas.append('')
        lineas.append('I3. OTROS CODIGOS DEL PRODUCTO (X6)')
        if 'product.packaging' in env:
            Pack = env['product.packaging']
            dom_pk = [('product_id', 'in', ids_prod), ('barcode', '!=', False)]
            lineas.append('   embalajes con barcode de estos productos: %d' % Pack.search_count(dom_pk))
            for pk in Pack.search(dom_pk, limit=5):
                lineas.append('      %s | qty %s | barcode %s' % (pk.name, pk.qty, pk.barcode))
        for modelo in ['product.barcode', 'product.multi.barcode', 'product.barcode.multi', 'product.template.barcode']:
            if modelo in env:
                lineas.append('   modelo %s: %d registros' % (modelo, env[modelo].search_count([])))

        lineas.append('')
        lineas.append('I4. EJEMPLOS DE FORMATO')
        lineas.append('   barcodes de producto: %s' % ', '.join(barcodes[:10]))
        ml_pend = env['stock.move.line'].search([('picking_id.picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', 'in', ['assigned', 'partially_available'])], limit=300)
        ubis = []
        for ml in ml_pend:
            texto = '%s [%s]' % (ml.location_id.name, ml.location_id.barcode or 'sin barcode')
            if texto not in ubis:
                ubis.append(texto)
            if len(ubis) >= 10:
                break
        lineas.append('   ubicaciones de OUT pendientes: %s' % ' | '.join(ubis))
        cajas = env['stock.quant.package'].search([('name', '=like', 'CJ%')], order='id desc', limit=10).mapped('name')
        lineas.append('   ultimas cajas CJ: %s' % ', '.join(cajas))
    except Exception as e:
        error_bloque('I', e)

# ---------------- L. Ubicaciones -----------------------------------------------
if toca('2'):
    lineas.append('')
    lineas.append('L1. UBICACIONES INTERNAS DE LA COMPANY %d' % COMPANY_ID)
    try:
        for w in env['stock.warehouse'].search([('company_id', '=', COMPANY_ID)]):
            raiz = w.lot_stock_id
            dom_l = [('usage', '=', 'internal'), ('id', 'child_of', raiz.id)]
            Loc = env['stock.location']
            lineas.append('   %s (%s): total %d | con barcode %d | sin barcode %d'
                          % (w.code, raiz.complete_name, Loc.search_count(dom_l), Loc.search_count(dom_l + [('barcode', '!=', False)]),
                             Loc.search_count(dom_l + [('barcode', '=', False)])))
            for l in Loc.search(dom_l + [('barcode', '!=', False)], limit=5):
                lineas.append('      %s [%s]' % (l.complete_name, l.barcode))
        lineas.append('')
        lineas.append('L2. UBICACIONES ESPECIALES (FALTANT, SORTER, MU*, Clientes)')
        for l in env['stock.location'].with_context(active_test=False).search(['|', '|', '|', ('name', 'ilike', 'FALTANT'), ('name', 'ilike', 'SORTER'),
                                                                               ('name', '=like', 'MU%'), ('name', '=', 'Customers')], limit=40):
            lineas.append('   %d | %s | %s | barcode %s | company %s' % (l.id, l.complete_name, l.usage, l.barcode or '-', l.company_id.id or '-'))
    except Exception as e:
        error_bloque('L', e)

# =============================================================================
# PARTE 3: E, F, G, H
# =============================================================================

if toca('3'):
    # Detalle de las move.line de los ultimos DIAS_DETALLE dias (una sola consulta)
    detalle = []
    moves_det = {}
    try:
        detalle = env['stock.move.line'].search_read(
            [('picking_id.picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done'), ('date', '>=', desde_detalle_txt)],
            ['picking_id', 'move_id', 'product_id', 'location_id', 'result_package_id', 'qty_done', 'write_date', 'write_uid'],
            limit=LIMITE_DETALLE)
        ids_moves = list(set([d['move_id'][0] for d in detalle if d['move_id']]))
        i = 0
        while i < len(ids_moves):
            for mv in env['stock.move'].search_read([('id', 'in', ids_moves[i:i + 2000])], ['product_id', 'product_uom_qty', 'picking_id']):
                moves_det[mv['id']] = mv
            i += 2000
    except Exception as e:
        error_bloque('detalle', e)

    # ---------------- E. Volumen y forma de las OUT ----------------------------
    lineas.append('')
    lineas.append('E1. OUT DEL TIPO %d VALIDADAS POR DIA (hora Madrid, %d dias)' % (TIPO_OUT_TIENDAS, DIAS))
    try:
        outs = env['stock.picking'].search_read([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done'), ('date_done', '>=', desde_txt)],
                                                ['date_done'])
        ids_outs = [o['id'] for o in outs]
        dia_de = {}
        por_dia = {}
        for o in outs:
            dia = hora_local(o['date_done']).strftime('%Y-%m-%d')
            dia_de[o['id']] = dia
            if dia not in por_dia:
                por_dia[dia] = [0, 0, 0, 0.0]
            por_dia[dia][0] += 1
        lin_por_out = {}
        for g in env['stock.move'].read_group([('picking_id', 'in', ids_outs)], ['picking_id'], ['picking_id']):
            lin_por_out[g['picking_id'][0]] = g['picking_id_count']
        ml_por_out = {}
        uds_por_out = {}
        for g in env['stock.move.line'].read_group([('picking_id', 'in', ids_outs)], ['picking_id', 'qty_done'], ['picking_id']):
            ml_por_out[g['picking_id'][0]] = g['picking_id_count']
            uds_por_out[g['picking_id'][0]] = g.get('qty_done') or 0.0
        for pid in ids_outs:
            d = dia_de[pid]
            por_dia[d][1] += lin_por_out.get(pid, 0)
            por_dia[d][2] += ml_por_out.get(pid, 0)
            por_dia[d][3] += uds_por_out.get(pid, 0.0)
        for d in sorted(por_dia.keys()):
            lineas.append('   %s: %d OUT | %d lineas | %d move.line | %d uds' % (d, por_dia[d][0], por_dia[d][1], por_dia[d][2], por_dia[d][3]))

        lineas.append('')
        lineas.append('E2. FORMA DE CADA OUT (%d dias)' % DIAS)
        lineas.append('   lineas (moves) por OUT: %s' % resumen(list(lin_por_out.values()), '%d'))
        lineas.append('   move.line por OUT: %s' % resumen(list(ml_por_out.values()), '%d'))
        lineas.append('   uds por OUT: %s' % resumen(list(uds_por_out.values()), '%d'))
        ubis_out = {}
        for d in detalle:
            if d['picking_id'] and d['location_id']:
                ubis_out.setdefault(d['picking_id'][0], {})[d['location_id'][0]] = 1
        lineas.append('   ubicaciones de origen distintas por OUT (%d dias): %s' % (DIAS_DETALLE, resumen([len(v) for v in ubis_out.values()], '%d')))
        uds_linea = [mv['product_uom_qty'] for mv in moves_det.values()]
        lineas.append('   uds por linea (%d dias): %s' % (DIAS_DETALLE, resumen(uds_linea, '%d')))
        if uds_linea:
            lineas.append('   lineas de 1 unidad: %.1f %%' % (100.0 * len([u for u in uds_linea if u == 1]) / len(uds_linea)))
        if len(detalle) >= LIMITE_DETALLE:
            lineas.append('   OJO: el detalle llego al limite de %d move.line; bajar DIAS_DETALLE' % LIMITE_DETALLE)

        lineas.append('')
        lineas.append('E3. OUT DEL TIPO %d PENDIENTES AHORA' % TIPO_OUT_TIENDAS)
        pend = env['stock.picking'].search([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', 'in', ['assigned', 'confirmed'])])
        lineas.append('   assigned %d | confirmed %d' % (len(pend.filtered(lambda p: p.state == 'assigned')), len(pend.filtered(lambda p: p.state == 'confirmed'))))
        ml_pend = [g['picking_id_count'] for g in env['stock.move.line'].read_group([('picking_id', 'in', pend.ids)], ['picking_id'], ['picking_id'])]
        lin_pend = [g['picking_id_count'] for g in env['stock.move'].read_group([('picking_id', 'in', pend.ids)], ['picking_id'], ['picking_id'])]
        lineas.append('   lineas por OUT: %s' % resumen(lin_pend, '%d'))
        lineas.append('   move.line por OUT (lo que pintaria la PDA): %s' % resumen(ml_pend, '%d'))
        en_lote = len(pend.filtered(lambda p: p.batch_id and (p.batch_id.name or '').startswith('Z-')))
        lineas.append('   de ellas dentro de un lote Z-: %d' % en_lote)

        lineas.append('')
        lineas.append('E4. TIEMPO DE PREPARACION POR OUT (primera a ultima escritura de sus move.line, %d dias)' % DIAS_DETALLE)
        tiempos = {}
        for d in detalle:
            if d['picking_id'] and d['write_date']:
                pid = d['picking_id'][0]
                if pid not in tiempos:
                    tiempos[pid] = [d['write_date'], d['write_date']]
                else:
                    if d['write_date'] < tiempos[pid][0]:
                        tiempos[pid][0] = d['write_date']
                    if d['write_date'] > tiempos[pid][1]:
                        tiempos[pid][1] = d['write_date']
        minutos = [(t[1] - t[0]).total_seconds() / 60.0 for t in tiempos.values()]
        lineas.append('   minutos: %s' % resumen(minutos, '%.1f'))
        lineas.append('   (la app actual guarda de golpe: es una cota inferior. Para lecturas/minuto, uds de E2 / minutos)')
    except Exception as e:
        error_bloque('E', e)

    # ---------------- F. Paquetes, lotes y propietarios ------------------------
    lineas.append('')
    lineas.append('F1. move.line DONE DEL TIPO %d EN %d DIAS (S9, X2)' % (TIPO_OUT_TIENDAS, DIAS))
    try:
        ML = env['stock.move.line']
        lineas.append('   total %d' % ML.search_count(dom_out_done))
        for etiqueta, extra in [('con lote (lot_id)', [('lot_id', '!=', False)]),
                                ('con lot_name', [('lot_name', '!=', False)]),
                                ('sale de un paquete (package_id)', [('package_id', '!=', False)]),
                                ('con package_level_id', [('package_level_id', '!=', False)]),
                                ('con caja destino (result_package_id)', [('result_package_id', '!=', False)]),
                                ('caja destino CJ%', [('result_package_id.name', '=like', 'CJ%')]),
                                ('caja destino PACK%', [('result_package_id.name', '=like', 'PACK%')]),
                                ('con propietario (owner_id)', [('owner_id', '!=', False)]),
                                ('F3 sin caja destino', [('result_package_id', '=', False)])]:
            lineas.append('   %s: %d' % (etiqueta, ML.search_count(dom_out_done + extra)))

        lineas.append('')
        lineas.append('F2. CAJAS POR OUT (%d dias)' % DIAS_DETALLE)
        cajas_out = {}
        uds_caja = {}
        outs_de_caja = {}
        for d in detalle:
            if d['picking_id'] and d['result_package_id']:
                pid = d['picking_id'][0]
                cid = d['result_package_id'][0]
                cajas_out.setdefault(pid, {})[cid] = 1
                uds_caja[cid] = uds_caja.get(cid, 0.0) + (d['qty_done'] or 0.0)
                outs_de_caja.setdefault(cid, {})[pid] = 1
        lineas.append('   cajas por OUT: %s' % resumen([len(v) for v in cajas_out.values()], '%d'))
        lineas.append('   uds por caja: %s' % resumen(list(uds_caja.values()), '%d'))
        compartidas = [c for c in outs_de_caja if len(outs_de_caja[c]) > 1]
        outs_comp = {}
        for c in compartidas:
            for pid in outs_de_caja[c]:
                outs_comp[pid] = 1
        lineas.append('   cajas usadas en mas de una OUT: %d | OUT afectadas: %d (caso koroshi_caja_existente v1.3)' % (len(compartidas), len(outs_comp)))
        n_pk = env['stock.picking'].search_count([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done'), ('date_done', '>=', desde_detalle_txt)])
        if campo_existe('stock.picking', 'number_of_packages'):
            muestra = env['stock.picking'].search_read([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done'), ('date_done', '>=', desde_detalle_txt)],
                                                       ['number_of_packages'], limit=5000)
            iguales = 0
            vacios = 0
            for m in muestra:
                if not m['number_of_packages']:
                    vacios += 1
                elif m['number_of_packages'] == len(cajas_out.get(m['id'], {})):
                    iguales += 1
            lineas.append('   number_of_packages (X1): OUT %d | igual a cajas distintas %d | vacio/0 %d | distinto %d'
                          % (len(muestra), iguales, vacios, len(muestra) - iguales - vacios))
        else:
            lineas.append('   stock.picking no tiene number_of_packages (%d OUT)' % n_pk)

        lineas.append('')
        lineas.append('F4. STOCK EMPAQUETADO EN LAS UBICACIONES DE ORIGEN DE LAS OUT PENDIENTES')
        ubis_pend = env['stock.move.line'].search([('picking_id.picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', 'in', ['assigned', 'partially_available'])]).mapped('location_id').ids
        lineas.append('   ubicaciones %d | quants con paquete en ellas %d'
                      % (len(ubis_pend), env['stock.quant'].search_count([('location_id', 'in', ubis_pend), ('package_id', '!=', False)])))
    except Exception as e:
        error_bloque('F', e)

    # ---------------- G. Comportamiento de la app actual -----------------------
    lineas.append('')
    lineas.append('G1. PEDIDOS PENDIENTES (backorders) DEL TIPO %d CREADOS EN %d DIAS' % (TIPO_OUT_TIENDAS, DIAS))
    try:
        Pick = env['stock.picking']
        for g in Pick.read_group([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('backorder_id', '!=', False), ('create_date', '>=', desde_txt)], ['state'], ['state']):
            lineas.append('   estado %s: %d' % (g['state'], g['state_count']))
        ids_done = Pick.search([('picking_type_id', '=', TIPO_OUT_TIENDAS), ('state', '=', 'done'), ('date_done', '>=', desde_txt)]).ids
        con_cancel = [g['picking_id'][0] for g in env['stock.move'].read_group([('picking_id', 'in', ids_done), ('state', '=', 'cancel')], ['picking_id'], ['picking_id']) if g['picking_id']]
        con_bo = Pick.search([('backorder_id', 'in', con_cancel)]).mapped('backorder_id').ids
        lineas.append('   OUT done con algun move cancelado: %d | de ellas sin pedido pendiente: %d' % (len(con_cancel), len([x for x in con_cancel if x not in con_bo])))

        lineas.append('')
        lineas.append('G2/G3. SOBRELECTURA Y PRODUCTOS ANADIDOS (%d dias)' % DIAS_DETALLE)
        hecho_move = {}
        sin_move = 0
        otro_prod = 0
        for d in detalle:
            if not d['move_id']:
                sin_move += 1
                continue
            mid = d['move_id'][0]
            hecho_move[mid] = hecho_move.get(mid, 0.0) + (d['qty_done'] or 0.0)
            mv = moves_det.get(mid)
            if mv and d['product_id'] and mv['product_id'] and mv['product_id'][0] != d['product_id'][0]:
                otro_prod += 1
        de_mas = []
        for mid in hecho_move:
            mv = moves_det.get(mid)
            if mv and hecho_move[mid] > mv['product_uom_qty'] + 0.0001:
                de_mas.append('%s (%d de %d)' % (mv['picking_id'] and mv['picking_id'][1] or '-', hecho_move[mid], mv['product_uom_qty']))
        lineas.append('   lineas con mas leido que pedido: %d | ejemplos: %s' % (len(de_mas), ', '.join(de_mas[:5]) or '-'))
        lineas.append('   move.line sin move: %d | move.line con producto distinto del move: %d' % (sin_move, otro_prod))

        lineas.append('')
        lineas.append('G4. CAMBIOS DE UBICACION Y FALTANTES')
        lineas.append('   move.line done desde una ubicacion FALTANT (%d dias): %d'
                      % (DIAS, env['stock.move.line'].search_count(dom_out_done + [('location_id.name', 'ilike', 'FALTANT')])))
        if 'koroshi.faltante' in env:
            Falt = env['koroshi.faltante']
            lineas.append('   koroshi.faltante creados en %d dias: %d' % (DIAS, Falt.search_count([('create_date', '>=', desde_txt)])))
            if campo_existe('koroshi.faltante', 'estado'):
                for g in Falt.read_group([('create_date', '>=', desde_txt)], ['estado'], ['estado']):
                    lineas.append('      estado %s: %d' % (g['estado'], g['estado_count']))

        lineas.append('')
        lineas.append('G5/G6. QUIEN PREPARA Y QUIEN VALIDA (%d dias)' % DIAS_DETALLE)
        uids_out = {}
        ultima = {}
        for d in detalle:
            if d['picking_id']:
                pid = d['picking_id'][0]
                if d['write_uid']:
                    uids_out.setdefault(pid, {})[d['write_uid'][0]] = 1
                if d['write_date'] and (pid not in ultima or d['write_date'] > ultima[pid]):
                    ultima[pid] = d['write_date']
        lineas.append('   OUT con mas de un usuario en sus move.line: %d de %d' % (len([1 for v in uids_out.values() if len(v) > 1]), len(uids_out)))
        difs = []
        sin_user = 0
        for o in Pick.search_read([('id', 'in', list(ultima.keys()))], ['date_done', 'user_id']):
            if not o['user_id']:
                sin_user += 1
            if o['date_done'] and o['id'] in ultima:
                difs.append((o['date_done'] - ultima[o['id']]).total_seconds())
        lineas.append('   segundos entre la ultima escritura de las lineas y date_done: %s' % resumen(difs, '%.0f'))
        lineas.append('   OUT sin responsable (user_id): %d' % sin_user)

        lineas.append('')
        lineas.append('G7. INFORMES DE stock.picking Y stock.quant.package (impresion al validar o cerrar caja)')
        for r in env['ir.actions.report'].search([('model', 'in', ['stock.picking', 'stock.quant.package', 'stock.picking.batch'])]):
            lineas.append('   %d | %s | %s | %s | %s' % (r.id, r.name, r.model, r.report_name, xmlid('ir.actions.report', r.id)))
    except Exception as e:
        error_bloque('G', e)

    # ---------------- H. Lotes de zona Z- --------------------------------------
    lineas.append('')
    lineas.append('H1. LOTES Z- DE LA COMPANY %d (%d dias)' % (COMPANY_ID, DIAS))
    try:
        Batch = env['stock.picking.batch']
        dom_b = [('company_id', '=', COMPANY_ID), ('name', '=like', 'Z-%'), ('create_date', '>=', desde_txt)]
        for g in Batch.read_group(dom_b, ['state'], ['state']):
            lineas.append('   estado %s: %d' % (g['state'], g['state_count']))
        por_dia_b = {}
        for b in Batch.search_read(dom_b, ['create_date']):
            d = hora_local(b['create_date']).strftime('%Y-%m-%d')
            por_dia_b[d] = por_dia_b.get(d, 0) + 1
        lineas.append('   por dia: %s' % ', '.join(['%s:%d' % (k, por_dia_b[k]) for k in sorted(por_dia_b.keys())]))
        campos_b = []
        for f in env['ir.model.fields'].search([('model', '=', 'stock.picking.batch')]):
            campos_b.append('%s(%s,%s)' % (f.name, f.ttype, f.modules or '-'))
        lineas.append('   campos: %s' % ', '.join(campos_b)[:900])

        lineas.append('')
        lineas.append('H2/H3/H4. FORMA DE LOS LOTES Z- (ultimos 60)')
        lotes = Batch.search(dom_b, order='id desc', limit=60)
        n_out = []
        n_tiendas = []
        n_ml = []
        n_uds = []
        n_ubis = []
        n_prods = []
        pct_rep = []
        mezclados = 0
        ejemplos = []
        for b in lotes:
            picks = b.picking_ids
            n_out.append(len(picks))
            n_tiendas.append(len(set(picks.mapped('partner_id').ids)))
            if len(set(picks.mapped('state'))) > 1:
                mezclados += 1
            mls = env['stock.move.line'].search_read([('picking_id', 'in', picks.ids)], ['picking_id', 'product_id', 'location_id', 'qty_done', 'product_uom_qty'])
            n_ml.append(len(mls))
            n_uds.append(sum([(m['qty_done'] or m['product_uom_qty'] or 0.0) for m in mls]))
            n_ubis.append(len(set([m['location_id'][0] for m in mls if m['location_id']])))
            prod_out = {}
            for m in mls:
                if m['product_id'] and m['picking_id']:
                    prod_out.setdefault(m['product_id'][0], {})[m['picking_id'][0]] = 1
            n_prods.append(len(prod_out))
            if prod_out:
                pct_rep.append(100.0 * len([1 for v in prod_out.values() if len(v) > 1]) / len(prod_out))
            if len(ejemplos) < 5:
                ejemplos.append('%s (%s, %d OUT, %d lineas)' % (b.name, b.state, len(picks), len(mls)))
        lineas.append('   OUT por lote: %s' % resumen(n_out, '%d'))
        lineas.append('   tiendas por lote: %s' % resumen(n_tiendas, '%d'))
        lineas.append('   move.line por lote: %s' % resumen(n_ml, '%d'))
        lineas.append('   uds por lote: %s' % resumen(n_uds, '%d'))
        lineas.append('   ubicaciones por lote: %s' % resumen(n_ubis, '%d'))
        lineas.append('   productos por lote: %s' % resumen(n_prods, '%d'))
        lineas.append('   %% de productos que van a mas de una OUT del lote: %s' % resumen(pct_rep, '%.0f'))
        lineas.append('   lotes con OUT en estados distintos: %d' % mezclados)
        lineas.append('   ejemplos: %s' % ' | '.join(ejemplos))
        if 'mail.tracking.value' in env and campo_existe('mail.tracking.value', 'field'):
            n_track = env['mail.tracking.value'].search_count([('field.model', '=', 'stock.picking'), ('field.name', '=', 'batch_id'),
                                                               ('create_date', '>=', desde_txt)])
            lineas.append('   cambios de batch_id registrados en el seguimiento (%d dias): %d' % (DIAS, n_track))

        lineas.append('')
        lineas.append('H5. COMO SE ABRE Y VALIDA UN LOTE (S10, X8)')
        for s in env['ir.actions.server'].search(['|', '|', ('name', 'ilike', 'start_batch'), ('code', 'ilike', 'start_batch_processing'),
                                                  ('code', 'ilike', 'action_validate')], limit=20):
            lineas.append('   accion servidor %d | %s | modelo %s | %s' % (s.id, s.name, s.model_id.model, xmlid('ir.actions.server', s.id)))
        ids_cli = env['ir.model.data'].search([('module', '=', 'barcode_batch_process'), ('model', '=', 'ir.actions.client')]).mapped('res_id')
        for a in env['ir.actions.client'].browse(ids_cli).exists():
            lineas.append('   accion cliente %d | %s | tag %s' % (a.id, a.name, a.tag))
        for v in env['ir.ui.view'].search([('model', '=', 'stock.picking.batch'), ('arch_db', 'ilike', 'start_batch_processing')], limit=10):
            lineas.append('   vista con start_batch_processing: %s' % xmlid('ir.ui.view', v.id))
    except Exception as e:
        error_bloque('H', e)

# ---------------- Lo que este diagnostico no puede dar -------------------------
lineas.append('')
lineas.append('NO SE PUEDE SACAR DESDE AQUI (otra via, siempre de solo lectura):')
lineas.append('   1. Python de stock_barcode_optimization / barcode_batch_process (put_in_pack, button_validate, start_batch_processing): custom_addons o Brain Station.')
lineas.append('   2. Su JS: bundle web.assets_backend desde el navegador, con las rutas de J2 (como el informe del 09/11).')
lineas.append('   3. Latencia real de la PDA y eco bus/campo (X12): medir en la PDA con la pantalla nueva en simulacion.')

texto_completo = '\n'.join(lineas)
log('KOROSHI PREPARACION LECTURAS DIAGNOSTICO\n%s' % texto_completo)

if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver el detalle completo en Ajustes > Tecnico > Registros / ir.logging, o lanzar con PARTE = 1, 2 o 3)' % (len(lineas) - MAX_LINEAS_MENSAJE)]

raise Warning('\n'.join(lineas))

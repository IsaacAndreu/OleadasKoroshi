# =============================================================================
# KOROSHI - RECOGIDA DE INFORMACION (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Saca la informacion necesaria para disenar el cron de oleadas y las
# matriculas de EFFEC (company_id 8): almacenes y pasos de entrega, tipos de
# operacion, horas de entrada de pedidos, lineas con qty_done antes de la "U",
# formato de ubicaciones, volumen de productos, matriculas (paquetes CJ/PACK),
# agrupaciones existentes, acciones planificadas y modulos instalados.
# No escribe nada: termina con un Warning. La unica escritura es el log()
# en ir.logging, que Odoo hace con su propio cursor.
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

COMPANY_ID = 8
PREFIJO_TIENDAS = 'S-66'
DIAS = 14
MAX_LINEAS_MENSAJE = 260

ahora_utc = datetime.datetime.utcnow()
desde_utc = ahora_utc - datetime.timedelta(days=DIAS)
desde_txt = desde_utc.strftime('%Y-%m-%d %H:%M:%S')

try:
    tz_local = timezone('Europe/Madrid')
    tz_utc = timezone('UTC')
except:
    tz_local = False
    tz_utc = False

lineas = []
lineas.append('INFO KOROSHI (company_id %d) - SOLO LECTURA - %s UTC' % (COMPANY_ID, ahora_utc.strftime('%d/%m/%Y %H:%M')))

# ---------------- A. Almacenes y tipos de operacion --------------------------
lineas.append('')
lineas.append('A. ALMACENES (delivery_steps: ship_only=1 paso, pick_ship=2 pasos, pick_pack_ship=3 pasos)')
for w in env['stock.warehouse'].search([('company_id', '=', COMPANY_ID)]):
    lineas.append('   %s [%s] delivery_steps=%s stock=%s' % (w.name, w.code, w.delivery_steps, w.lot_stock_id.complete_name))
lineas.append('   Tipos de operacion (nombre | codigo | prefijo | origen por defecto | pendientes assigned):')
for t in env['stock.picking.type'].search([('company_id', '=', COMPANY_ID)]):
    pendientes = env['stock.picking'].search_count([('picking_type_id', '=', t.id), ('state', '=', 'assigned')])
    lineas.append('   %s | %s | %s | %s | %d' % (t.name, t.code, t.sequence_code or '-', t.default_location_src_id.complete_name or '-', pendientes))

# ---------------- B. Hora de entrada de los pedidos de tienda ----------------
lineas.append('')
lineas.append('B. OUT DE TIENDA (origen %s...) CREADAS EN LOS ULTIMOS %d DIAS, POR DIA Y HORA LOCAL' % (PREFIJO_TIENDAS, DIAS))
outs_recientes = env['stock.picking'].search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('origin', '=like', PREFIJO_TIENDAS + '%'),
    ('create_date', '>=', desde_txt),
], order='create_date asc')
por_dia = {}
por_hora = {}
for p in outs_recientes:
    if tz_local:
        local = tz_utc.localize(p.create_date).astimezone(tz_local)
    else:
        local = p.create_date + datetime.timedelta(hours=2)
    dia = local.strftime('%Y-%m-%d')
    hora = local.strftime('%H')
    unidades = sum(p.move_lines.mapped('product_uom_qty'))
    if dia not in por_dia:
        por_dia[dia] = {'outs': 0, 'uds': 0.0, 'tiendas': {}}
    por_dia[dia]['outs'] += 1
    por_dia[dia]['uds'] += unidades
    por_dia[dia]['tiendas'][p.partner_id.id] = 1
    por_hora[hora] = por_hora.get(hora, 0) + 1
for dia in sorted(por_dia.keys()):
    lineas.append('   %s: %d OUT, %d tiendas, %d uds' % (dia, por_dia[dia]['outs'], len(por_dia[dia]['tiendas']), por_dia[dia]['uds']))
texto_horas = []
for h in sorted(por_hora.keys()):
    texto_horas.append('%s:%d' % (h, por_hora[h]))
lineas.append('   Por hora de creacion (hora local: num OUT): %s' % ', '.join(texto_horas))

# ---------------- C. qty_done antes de la "U" (picking con app) ---------------
lineas.append('')
lineas.append('C. OUT DE TIENDA PENDIENTES (assigned) CON qty_done YA PUESTO')
pendientes = env['stock.picking'].search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('origin', '=like', PREFIJO_TIENDAS + '%'),
    ('state', '=', 'assigned'),
])
con_hecho = 0
for p in pendientes:
    hecho = sum(p.move_line_ids.mapped('qty_done'))
    reservado = sum(p.move_line_ids.mapped('product_uom_qty'))
    if hecho > 0:
        con_hecho += 1
        lineas.append('   %s | %s | hecho %d de %d reservadas | en oleada: %s' % (p.name, p.partner_id.name or '-', hecho, reservado, p.batch_id.name or 'no'))
lineas.append('   Total: %d de %d OUT pendientes tienen qty_done > 0' % (con_hecho, len(pendientes)))

# ---------------- D. Formato de ubicaciones --------------------------------
lineas.append('')
lineas.append('D. UBICACIONES DE ORIGEN DE LAS LINEAS RESERVADAS (OUT de tienda pendientes)')
ml_pend = env['stock.move.line'].search([('picking_id', 'in', pendientes.ids)])
por_padre = {}
ejemplos = []
for ml in ml_pend:
    padre = ml.location_id.location_id.complete_name or '-'
    por_padre[padre] = por_padre.get(padre, 0) + ml.product_uom_qty
    if len(ejemplos) < 15 and ml.location_id.complete_name not in ejemplos:
        ejemplos.append(ml.location_id.complete_name)
lineas.append('   Ejemplos: %s' % ' || '.join(ejemplos))
lineas.append('   Unidades reservadas por ubicacion padre:')
for k in sorted(por_padre.keys()):
    lineas.append('      %s: %d' % (k, por_padre[k]))

# ---------------- E. Volumen y peso de los productos ------------------------
lineas.append('')
lineas.append('E. VOLUMEN / PESO DE LOS PRODUCTOS ENVIADOS A TIENDAS (ultimos %d dias)' % DIAS)
grupos = env['stock.move'].read_group([
    ('company_id', '=', COMPANY_ID),
    ('picking_code', '=', 'outgoing'),
    ('picking_id.origin', '=like', PREFIJO_TIENDAS + '%'),
    ('create_date', '>=', desde_txt),
], ['product_id', 'product_uom_qty'], ['product_id'])
n_prod = 0
n_vol = 0
n_peso = 0
uds_total = 0.0
uds_con_vol = 0.0
vol_min = 0.0
vol_max = 0.0
for g in grupos:
    if not g.get('product_id'):
        continue
    prod = env['product.product'].browse(g['product_id'][0])
    qty = g.get('product_uom_qty') or 0.0
    n_prod += 1
    uds_total += qty
    if prod.volume and prod.volume > 0:
        n_vol += 1
        uds_con_vol += qty
        if vol_min == 0.0 or prod.volume < vol_min:
            vol_min = prod.volume
        if prod.volume > vol_max:
            vol_max = prod.volume
    if prod.weight and prod.weight > 0:
        n_peso += 1
lineas.append('   Productos distintos: %d | con volumen: %d | con peso: %d' % (n_prod, n_vol, n_peso))
lineas.append('   Unidades: %d | unidades con volumen: %d | volumen min %.5f, max %.5f (m3)' % (uds_total, uds_con_vol, vol_min, vol_max))

# ---------------- F. Matriculas (paquetes) ---------------------------------
lineas.append('')
lineas.append('F. MATRICULAS (stock.quant.package)')
Package = env['stock.quant.package']
for prefijo in ['CJ', 'PACK']:
    # Consultas ligeras: contar con search_count y read_group (sin domains sobre one2many)
    total = Package.search_count([('name', '=like', prefijo + '%')])
    primero = Package.search([('name', '=like', prefijo + '%')], order='name asc', limit=1).name or '-'
    ultimo = Package.search([('name', '=like', prefijo + '%')], order='name desc', limit=1).name or '-'
    con_stock = len(env['stock.quant'].read_group([('package_id.name', '=like', prefijo + '%')], ['package_id'], ['package_id']))
    lineas.append('   %s: %d paquetes (primero %s, ultimo %s), %d con stock, %d sin stock'
                  % (prefijo, total, primero, ultimo, con_stock, total - con_stock))
    ultimos_usados = env['stock.move.line'].search([('result_package_id.name', '=like', prefijo + '%'), ('state', '=', 'done')], order='id desc', limit=5)
    ejemplos_usados = []
    for ml in ultimos_usados:
        ejemplos_usados.append('%s (%s)' % (ml.result_package_id.name, ml.picking_id.name or '-'))
    lineas.append('      Ultimas usadas: %s' % (', '.join(ejemplos_usados) or '-'))

# ---------------- G. Agrupaciones (oleadas) existentes -----------------------
lineas.append('')
lineas.append('G. ULTIMAS AGRUPACIONES (stock.picking.batch) DE LA EMPRESA')
for b in env['stock.picking.batch'].search([('company_id', '=', COMPANY_ID)], order='id desc', limit=15):
    lineas.append('   %s | %s | %s | %d albaranes | creada %s'
                  % (b.name, b.state, b.user_id.name or '-', len(b.picking_ids), b.create_date and b.create_date.strftime('%d/%m %H:%M') or '-'))
for s in env['ir.sequence'].search([('code', '=', 'picking.batch')]):
    lineas.append('   Secuencia picking.batch: prefijo "%s", siguiente %d, empresa %s' % (s.prefix or '', s.number_next_actual, s.company_id.name or 'todas'))

# ---------------- H. Acciones planificadas ----------------------------------
lineas.append('')
lineas.append('H. ACCIONES PLANIFICADAS RELACIONADAS (activas)')
crones = env['ir.cron'].search(['|', '|', '|', ('name', 'ilike', 'S4T'), ('name', 'ilike', 'koroshi'), ('name', 'ilike', 'pedido'), ('name', 'ilike', 'order')])
for c in crones:
    lineas.append('   %s | cada %d %s | proxima %s UTC' % (c.name, c.interval_number, c.interval_type, c.nextcall))

# ---------------- I. Modulos instalados relacionados ------------------------
lineas.append('')
lineas.append('I. MODULOS INSTALADOS RELACIONADOS (picking / app / lector)')
dominio_mod = [('state', '=', 'installed')]
palabras = ['barcode', 'batch', 'picking', 'wms', 'pda', 'scan', 's4t', 'koroshi', 'mobile', 'package', 'delivery', 'wave']
for i in range(len(palabras) - 1):
    dominio_mod.append('|')
for pal in palabras:
    dominio_mod.append(('name', 'ilike', pal))
nombres = env['ir.module.module'].search(dominio_mod).mapped('name')
lineas.append('   %s' % ', '.join(sorted(nombres)))

# ---------------- J. Destinatarios de los pedidos de tienda -----------------
lineas.append('')
lineas.append('J. DESTINATARIOS DE OUT DE TIENDA (ultimos %d dias) QUE NO EMPIEZAN POR "K<numero>"' % DIAS)
otros = {}
n_k = {}
for p in outs_recientes:
    nombre = p.partner_id.name or '-'
    if len(nombre) > 1 and nombre[0] == 'K' and nombre[1].isdigit():
        n_k[nombre] = 1
    else:
        otros[nombre] = otros.get(nombre, 0) + 1
lineas.append('   Tiendas K: %d distintas' % len(n_k))
for k in sorted(otros.keys()):
    lineas.append('   %s: %d OUT' % (k, otros[k]))

texto_completo = '\n'.join(lineas)
log('KOROSHI INFO DIAGNOSTICO\n%s' % texto_completo)

if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver el detalle completo en Ajustes > Tecnico > Registros / ir.logging)' % (len(lineas) - MAX_LINEAS_MENSAJE)]

raise Warning('\n'.join(lineas))

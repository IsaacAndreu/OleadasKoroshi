# ================================================================
# RECUPERACION MANUAL KOROSHI - PEDIDO 0000055796-02 (20/10/2026)
# Misma accion que "Recuperar Pedidos Online" (id 1827) sobre s4t.order.feed,
# con el pedido de hoy. Las lineas (SKU y unidades) y el cliente los pasa Betty
# desde S4T: desde Odoo no se puede leer la API (en las acciones no hay 'requests').
#
# SIMULACION = True -> solo valida duplicados y SKU, no crea nada
# CANTIDADES_CONFIRMADAS -> True solo tras validar unidades con Betty
# IDs S4T negativos = PROVISIONALES (Koroshi no los devuelve por API).
#   El ultimo usado es -900023 (W-0000053993-02, 29/09): este pedido usa -900024.
# ================================================================
SIMULACION = True
CANTIDADES_CONFIRMADAS = False

PEDIDOS = [
    (
        '0000055796-02',
        '2026-10-15',          # fecha original del pedido en S4T (confirmar con Betty)
        'CLIENTE',             # nombre del cliente que sale en S4T
        -900024,
        [
            # ('SKU-COLOR-TALLA', unidades),  <- lineas que pase Betty
            ('XXXXXXXX-000000-XX', 1),
        ]
    ),
]

if not SIMULACION and not CANTIDADES_CONFIRMADAS:
    log('Recuperacion abortada: cantidades sin confirmar', level='warning')
    raise Warning('Cantidades sin confirmar con Betty.')

config = env['s4t.config'].sudo().search([('state', '=', 'valid')], limit=1)
if not config:
    log('Recuperacion: no hay configuracion S4T valida', level='error')
    raise Warning('No existe una configuracion S4T valida.')

sync = env['s4t.order.sync'].sudo()
Feed = env['s4t.order.feed'].sudo()
Sale = env['sale.order'].sudo()
Product = env['product.product'].sudo()

creados = []
saltados = []
sin_sku = []
errores = []
numeros = []

for item in PEDIDOS:

    numero = item[0]
    fecha_original = item[1]
    nombre_cliente = item[2]
    remote_id = item[3]
    lineas = item[4]

    numeros.append(numero)
    base = numero.split('-')[0]

    # ------------------------------------------------------------
    # PROTECCION DUPLICADOS (por numero base, incluye sufijos)
    # ------------------------------------------------------------
    existing_order = Sale.search([('name', 'ilike', base)], limit=1)
    if existing_order:
        saltados.append('%s -> ya existe sale.order %s (estado %s)' % (
            numero, existing_order.name, existing_order.state))
        continue

    existing_feed = Feed.search([('s4t_order_number', 'ilike', base)], limit=1)
    if existing_feed:
        saltados.append('%s -> ya existe feed ID %s (%s)' % (
            numero, existing_feed.id, existing_feed.s4t_order_number))
        continue

    existing_remote = Feed.search([('s4t_remote_id', '=', str(remote_id))], limit=1)
    if existing_remote:
        saltados.append('%s -> ID provisional %s ya usado por feed %s' % (
            numero, remote_id, existing_remote.id))
        continue

    # ------------------------------------------------------------
    # VALIDACION SKU ANTES DE CREAR NADA
    # ------------------------------------------------------------
    api_lines = []
    missing = []
    for linea in lineas:
        product = Product.search([('style_code', '=', linea[0])], limit=1)
        if not product:
            missing.append(linea[0])
        api_lines.append({'sku': linea[0], 'quantity': linea[1]})

    if missing:
        sin_sku.append('%s -> %s' % (numero, ', '.join(missing)))
        continue

    if SIMULACION:
        creados.append('%s -> SIMULACION OK (%s lineas, %s uds, remote_id %s)' % (
            numero, len(api_lines), sum([l['quantity'] for l in api_lines]), remote_id))
        continue

    # ------------------------------------------------------------
    # MISMO FORMATO QUE LLEGA DESDE S4T
    # ------------------------------------------------------------
    order_data = {
        'id': remote_id,
        'order_number': numero,
        'client': False,
        'client_name': nombre_cliente,
    }

    try:
        feed = sync._create_odoo_order_feed(order_data, api_lines, 'b2c', config)

        if not feed:
            errores.append('%s -> _create_odoo_order_feed no creo el feed' % numero)
            continue

        feed.write({
            'response_msg': 'RECUPERACION MANUAL KOROSHI\n'
                            'Fecha original del listado: %s\n'
                            'ID remoto S4T REAL no disponible.\n'
                            'ID provisional usado: %s' % (fecha_original, remote_id)
        })

        feed.action_create_sale_order()

        if feed.sale_order_id:
            creados.append('%s -> %s' % (numero, feed.sale_order_id.name))
            feed.sale_order_id.message_post(
                body='RECUPERACION MANUAL KOROSHI. Pedido original del %s. '
                     'El ID remoto S4T del feed es provisional: %s' % (
                         fecha_original, remote_id)
            )
        else:
            errores.append('%s -> feed creado pero sin sale.order asociado' % numero)

    except Exception as e:
        errores.append('%s -> %s' % (numero, str(e)))


# ================================================================
# LOG FINAL (siempre antes de cualquier raise)
# ================================================================
log('RECUPERACION KOROSHI | simulacion=%s | creados=%s | saltados=%s | SKU faltantes=%s | errores=%s' % (
    SIMULACION, len(creados), len(saltados), len(sin_sku), len(errores)), level='warning')

for t in creados:
    log('RECUPERADO: %s' % t, level='info')
for t in saltados:
    log('SALTADO: %s' % t, level='warning')
for t in sin_sku:
    log('SKU NO ENCONTRADO: %s' % t, level='warning')
for t in errores:
    log('ERROR RECUPERACION: %s' % t, level='error')

if SIMULACION:
    texto = 'SIMULACION (no se ha creado nada)\n\n'
    texto += 'OK (%s):\n%s\n\n' % (len(creados), '\n'.join(creados) or '-')
    texto += 'SALTADOS (%s):\n%s\n\n' % (len(saltados), '\n'.join(saltados) or '-')
    texto += 'SKU FALTANTES (%s):\n%s\n\n' % (len(sin_sku), '\n'.join(sin_sku) or '-')
    texto += 'ERRORES (%s):\n%s\n' % (len(errores), '\n'.join(errores) or '-')
    raise Warning(texto)

action = {
    'type': 'ir.actions.act_window',
    'name': 'Recuperacion Koroshi',
    'res_model': 's4t.order.feed',
    'view_mode': 'tree,form',
    'domain': [('s4t_order_number', 'in', numeros)],
    'target': 'current',
}

# =============================================================================
# KOROSHI - BUSCAR PEDIDOS ONLINE QUE NO HAN ENTRADO EN LA API DE S4T (SOLO LECTURA) - 19/11/2026
# Accion de servidor nueva sobre s4t.order.feed, sin boton. Copia de la busqueda del 20/10/2026
# (odoo/KOROSHI_buscar_pedido_online_DIAGNOSTICO_2026-10-20.py) para los pedidos del 12/11 que KOROSHI (Sonia) dice
# que no han salido: entre el 0000058545 y el 0000058555 no entro ninguno en Odoo.
#
# 1. Mira si existen en Odoo (sale.order y s4t.order.feed).
# 2. Busca en la API SOLO con viewed=true (pedidos ya descargados). NUNCA viewed=false o vacio: marcaria como
#    vistos los pedidos nuevos y no entrarian.
# 3. Ensena el pedido entero (id remoto, cliente, lineas) para la accion «Recuperar Pedidos Online» (1827).
# No crea ni cambia nada. Acaba siempre con un aviso. La clave de la API no se ensena.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

PEDIDOS_BUSCADOS = ['0000058546', '0000058547', '0000058548', '0000058549', '0000058550', '0000058551',
                    '0000058552', '0000058553', '0000058554']
TIPOS = ['b2c']
TAMANO_PAGINA = 500
MAX_PAGINAS = 30
CARACTERES_POR_PEDIDO = 1500

lineas = ['=== EN ODOO ===']
for num in PEDIDOS_BUSCADOS:
    pedidos = env['sale.order'].sudo().search([('name', 'like', num)])
    feeds = env['s4t.order.feed'].sudo().search([('s4t_order_number', 'like', num)])
    lineas.append('%s -> pedido: %s | feed: %s' % (
        num, ', '.join(pedidos.mapped('name')) or 'ninguno',
        ', '.join(['%s (%s)' % (f.s4t_order_number, f.state) for f in feeds]) or 'ninguno'))

config = env['s4t.config'].sudo().search([], limit=1)
campos_cfg = env['ir.model.fields'].sudo().search([('model', '=', 's4t.config'), ('ttype', '=', 'char')])
campo_key = False
campo_url = False
for c in campos_cfg:
    n = c.name.lower()
    if not campo_key and ('key' in n or 'token' in n):
        campo_key = c.name
    if not campo_url and ('url' in n or 'host' in n or 'endpoint' in n):
        campo_url = c.name
api_key = config[campo_key] if (config and campo_key) else False
if not api_key:
    log('Buscar pedidos online: sin API key en s4t.config')
    raise Warning('No se encuentra la API key en s4t.config.')
base = ((config[campo_url] if campo_url else False) or '').rstrip('/')
if '/api/service' not in base:
    base = base + '/api/service'

lineas.append('')
lineas.append('=== API (viewed=true) ===')
encontrados = {}
for tipo in TIPOS:
    total = 0
    for pagina in range(MAX_PAGINAS):
        r = requests.get('%s/orders/%s' % (base, tipo), headers={'x-api-key': api_key},
                         params={'viewed': 'true', 'skip': pagina * TAMANO_PAGINA, 'limit': TAMANO_PAGINA}, timeout=60)
        if r.status_code != 200:
            lineas.append('%s pagina %s -> HTTP %s: %s' % (tipo, pagina, r.status_code, r.text[:200]))
            break
        datos = r.json()
        items = datos
        if isinstance(datos, dict):
            items = []
            for v in datos.values():
                if isinstance(v, list):
                    items = v
                    break
        if not items:
            break
        total += len(items)
        for it in items:
            texto = str(it)
            for num in PEDIDOS_BUSCADOS:
                if num in texto:
                    encontrados.setdefault(num, []).append(texto[:CARACTERES_POR_PEDIDO])
        if len(items) < TAMANO_PAGINA:
            break
    lineas.append('%s: %s pedidos vistos leidos' % (tipo, total))

lineas.append('')
lineas.append('=== BUSQUEDA ===')
for num in PEDIDOS_BUSCADOS:
    res = encontrados.get(num, [])
    if not res:
        lineas.append('%s: NO ENCONTRADO' % num)
    for x in res:
        lineas.append('%s: %s' % (num, x))

mensaje = '\n'.join(lineas)
log(mensaje[:2000])
raise Warning(mensaje)

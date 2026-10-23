# =============================================================================
# KOROSHI - BUSCAR UN PEDIDO ONLINE QUE NO HA ENTRADO - DIAGNOSTICO (SOLO LECTURA)
# Copia de la accion "Errores Online" (id 1833) para el pedido 0000055796-02 (20/10/2026).
# Se puede pegar en la accion de pruebas 1837: no usa los registros seleccionados.
#
# 1. Mira si el pedido ya existe en Odoo (sale.order y s4t.order.feed).
# 2. Busca el pedido en la API de Koroshi SOLO con viewed=true (pedidos ya descargados).
#    NUNCA viewed=false o vacio: marcaria como vistos los pedidos nuevos.
# 3. Muestra el pedido entero que devuelve la API (id remoto, lineas, SKU y cantidades),
#    que es lo que hace falta para la accion de recuperacion (Recuperar Pedidos Online, id 1827).
# No crea ni cambia nada. Acaba siempre con un aviso.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

PEDIDOS_BUSCADOS = ['0000055796-02', '0000055796']   # con y sin sufijo, por si llega con otro -0X
TAMANO_PAGINA = 500
MAX_PAGINAS = 20
CARACTERES_POR_PEDIDO = 3000                          # para ver todas las lineas del pedido encontrado

lineas = []

# 1. Comprobar primero si ya existe en Odoo
lineas.append('=== EN ODOO ===')
for num in PEDIDOS_BUSCADOS:
    pedidos = env['sale.order'].search([('name', 'like', num)])
    feeds = env['s4t.order.feed'].search([('name', 'like', num)])
    lineas.append('%s -> sale.order: %s | feed: %s' % (
        num,
        ', '.join(['%s (%s)' % (p.name, p.state) for p in pedidos]) or 'ninguno',
        ', '.join(['%s id %s (%s)' % (f.name, f.id, f.state) for f in feeds]) or 'ninguno',
    ))

# 2. Leer API key y URL de la configuracion S4T sin mostrarlas
config = env['s4t.config'].search([], limit=1)
campos_cfg = env['ir.model.fields'].search([('model', '=', 's4t.config'), ('ttype', '=', 'char')])
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
    log('No se encuentra API key en s4t.config. Campos char: %s' % ', '.join(campos_cfg.mapped('name')))
    raise Warning('No se encuentra API key en s4t.config. Campos char disponibles: %s' % ', '.join(campos_cfg.mapped('name')))

base = (config[campo_url] if campo_url else False) or 'http://82.223.131.45:3232'
base = base.rstrip('/')
if '/api/service' not in base:
    base = base + '/api/service'

lineas.append('')
lineas.append('=== API (viewed=true) ===')
lineas.append('Config: campo key=%s | campo url=%s' % (campo_key, campo_url))
encontrados = {}

for tipo in ['b2c', 'b2b']:
    total = 0
    claves = ''
    for pagina in range(MAX_PAGINAS):
        r = requests.get(
            '%s/orders/%s' % (base, tipo),
            headers={'x-api-key': api_key},
            params={'viewed': 'true', 'skip': pagina * TAMANO_PAGINA, 'limit': TAMANO_PAGINA},
            timeout=60,
        )
        if r.status_code != 200:
            lineas.append('%s pagina %s -> HTTP %s: %s' % (tipo, pagina, r.status_code, r.text[:200]))
            break
        datos = r.json()
        items = datos
        if isinstance(datos, dict):
            if pagina == 0:
                lineas.append('%s: claves de la respuesta = %s' % (tipo, ', '.join(datos.keys())))
            items = []
            for v in datos.values():
                if isinstance(v, list):
                    items = v
                    break
        if not items:
            break
        if not claves:
            claves = ', '.join(items[0].keys()) if isinstance(items[0], dict) else str(items[0])[:100]
        total += len(items)
        for it in items:
            texto = str(it)
            for num in PEDIDOS_BUSCADOS:
                if num in texto:
                    encontrados.setdefault(num, []).append('%s -> %s' % (tipo, texto[:CARACTERES_POR_PEDIDO]))
        if len(items) < TAMANO_PAGINA:
            break
    lineas.append('%s: %s pedidos vistos leidos | campos de cada pedido: %s' % (tipo, total, claves))

lineas.append('')
lineas.append('=== BUSQUEDA ===')
for num in PEDIDOS_BUSCADOS:
    resultados = encontrados.get(num, [])
    if not resultados:
        lineas.append('%s: NO ENCONTRADO' % num)
    for res in resultados:
        lineas.append('%s: %s' % (num, res))

mensaje = '\n'.join(lineas)
log(mensaje[:2000])
raise Warning(mensaje)

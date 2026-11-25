# =============================================================================
# KOROSHI - PEDIDOS DEL DIA EN LA API DE S4T: CANCELADOS Y NO (SOLO LECTURA) - 24/11/2026
# Misma accion 1987 (sin boton). Antes: 20261124_accion-1987_buscar-api_ANTES.py.
# Lee SOLO viewed=true (NUNCA viewed=false: marcaria como vistos los pedidos nuevos).
# Saca los pedidos con alguna fecha del DIA y, de cada uno, numero, campos de estado/cancelacion y si esta en Odoo.
# No crea ni cambia nada. Acaba siempre con un aviso. La clave de la API no se ensena.
# =============================================================================

DIA = '2026-11-24'
TIPOS = ['b2c', 'b2b']
TAMANO_PAGINA = 500
MAX_PAGINAS = 40

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
    log('Pedidos del dia: sin API key en s4t.config')
    raise Warning('No se encuentra la API key en s4t.config.')
base = ((config[campo_url] if campo_url else False) or '').rstrip('/')
if '/api/service' not in base:
    base = base + '/api/service'

lineas = []
for tipo in TIPOS:
    total = 0
    del_dia = 0
    claves = False
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
            if not isinstance(it, dict):
                continue
            if not claves:
                claves = ', '.join(sorted(it.keys()))
            fechas = []
            estado = []
            numero = ''
            for k in it:
                v = it[k]
                kl = k.lower()
                if isinstance(v, str) and v[:10] == DIA:
                    fechas.append('%s=%s' % (k, v[:19]))
                if 'status' in kl or 'state' in kl or 'cancel' in kl or 'estado' in kl:
                    estado.append('%s=%s' % (k, str(v)[:60]))
                if not numero and ('number' in kl or 'numero' in kl or kl == 'order' or kl == 'name'):
                    numero = str(v)
            if not fechas:
                continue
            del_dia += 1
            en_odoo = 'no'
            if numero:
                so = env['sale.order'].sudo().search([('name', 'like', numero)], limit=1)
                if so:
                    en_odoo = '%s (%s)' % (so.name, so.state)
            lineas.append('%s | %s | %s | Odoo: %s | %s' % (tipo, numero, ' '.join(estado) or 'sin campo estado',
                                                          en_odoo, ' '.join(fechas)))
        if len(items) < TAMANO_PAGINA:
            break
    lineas.insert(0, '%s: %s leidos, %s del %s. Campos: %s' % (tipo, total, del_dia, DIA, claves or '-'))

mensaje = '\n'.join(lineas)
log(mensaje[:2000])
raise Warning(mensaje)

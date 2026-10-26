# =============================================================================
# KOROSHI - VOLVER A CREAR PEDIDOS ONLINE CUYA OUT SE CANCELO
# Para ejecutar en la accion planificada "Claude - Diagnostico" (desactivada, modelo s4t.order.feed):
# pegar este codigo en "Codigo Python" y pulsar "Ejecutar manualmente".
#
# Caso (26/10/2026): Koroshi pide volver a descargar 4 pedidos online que tienen la OUT cancelada
# en Odoo (se cancelo por falta de stock). Los pedidos W-... siguen en Odoo con su OUT cancelada:
# NO se tocan. Se crea un pedido NUEVO por cada uno, con el nombre W-<numero><SUFIJO>, el mismo
# numero y el mismo id de Koroshi (s4t_remote_id), y SOLO las lineas del correo de Koroshi.
# Se crea igual que los que entran solos: un feed s4t.order.feed y action_create_sale_order().
#
# SIMULACION = True: no crea nada. Comprueba cada pedido y cada linea (producto, stock libre en
#   EFFEC) y lo ensena; acaba con un aviso.
# SIMULACION = False: crea los pedidos. Si algo falla (producto que no existe, linea sin stock,
#   pedido que no se crea), se deshace TODO y no queda nada creado.
# Reglas de safe_eval: sin f-strings, sin import, log() antes de raise; sin raise al final en real.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
SIMULACION = True
SUFIJO = '-R'                     # nombre del pedido nuevo: W-0000056132-R
UBICACION_RAIZ = 84               # EFFEC (vista)
# Lineas del correo de Koroshi (26/10/2026): numero -> [(sku, cantidad)]
PEDIDOS = [
    ('0000055825-02', [('1922VS21-000003-M', 1), ('1922VS91-000158-M', 1), ('2411SU18-000014-L', 1),
                       ('2511TR08-000030-L', 1), ('2521SU22-000030-L', 1), ('2522ML21-000039-M', 1),
                       ('2522TR15-000017-M', 1)]),
    ('0000056077-02', [('2511PT85-000306-XXL', 1), ('2522ML79-000003-L', 1), ('2622ML00-000017-L', 1),
                       ('2622ML51-000005-L', 1), ('2622ML79-000019-L', 1)]),
    ('0000056132', [('2622PT41-000003-36', 1), ('2622PT44-000003-36', 1), ('2622PT61-000306-36', 1),
                    ('2622SU07-000003-M', 1)]),
    ('0000056220', [('1822JA07-000003-S', 1)]),
]
# -----------------------------------------------------------------------------

Pedido = env['sale.order']
Feed = env['s4t.order.feed']


def buscar_producto(sku):
    # El SKU esta en product.template.style_code / name (default_code esta vacio)
    producto = env['product.product'].search([('product_tmpl_id.style_code', '=', sku)], limit=1)
    if not producto:
        producto = env['product.product'].search([('product_tmpl_id.name', '=', sku)], limit=1)
    return producto


texto = ['KOROSHI RECREAR PEDIDOS ONLINE - %s' % (SIMULACION and 'SIMULACION (NO SE HA CREADO NADA)' or 'REAL'), '']
errores = []
plan = []                          # (numero, nombre nuevo, remote_id, lineas)
pedir = {}                         # producto id -> uds pedidas en esta accion (para el stock)

for numero, lineas in PEDIDOS:
    original = Pedido.search([('name', '=', 'W-%s' % numero)], limit=1)
    nombre = 'W-%s%s' % (numero, SUFIJO)
    if not original:
        errores.append('%s: no existe el pedido original W-%s' % (numero, numero))
        texto.append('%s: NO EXISTE EL ORIGINAL' % numero)
        continue
    outs = original.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')
    abiertas = outs.filtered(lambda p: p.state != 'cancel')
    texto.append('%s | original %s (%s) id Koroshi %s | OUT: %s' % (
        numero, original.name, original.state, original.s4t_remote_id,
        ', '.join(outs.mapped(lambda p: '%s %s' % (p.name, p.state))) or 'ninguna'))
    if abiertas:
        errores.append('%s: el original tiene OUT sin cancelar (%s): no se crea otro' % (
            numero, ', '.join(abiertas.mapped('name'))))
    if not original.s4t_remote_id:
        errores.append('%s: el original no tiene id de Koroshi' % numero)
    if Pedido.search([('name', '=', nombre)], limit=1) or Feed.search([('name', '=', nombre)], limit=1):
        errores.append('%s: ya existe %s (pedido o feed): no se duplica' % (numero, nombre))
    otros = Pedido.search([('s4t_remote_id', '=', original.s4t_remote_id), ('id', '!=', original.id)])
    if otros:
        texto.append('   ojo: ya hay otros pedidos con este id de Koroshi: %s' % ', '.join(otros.mapped('name')))
    for sku, cantidad in lineas:
        producto = buscar_producto(sku)
        if not producto:
            errores.append('%s: no existe el producto %s' % (numero, sku))
            texto.append('   %s x%d -> PRODUCTO NO ENCONTRADO' % (sku, cantidad))
            continue
        pedir[producto.id] = pedir.get(producto.id, 0) + cantidad
        libre = producto.with_context(location=UBICACION_RAIZ).free_qty
        aviso = ''
        if libre < pedir[producto.id]:
            aviso = '  <-- SIN STOCK LIBRE SUFICIENTE'
            errores.append('%s: %s sin stock libre (hay %.0f)' % (numero, sku, libre))
        texto.append('   %s x%d -> OK (id %d) | libre en EFFEC: %.0f%s' % (sku, cantidad, producto.id, libre, aviso))
    texto.append('   se crearia: %s con %d linea(s)' % (nombre, len(lineas)))
    plan.append((numero, nombre, original.s4t_remote_id, lineas))

texto.append('')
if errores:
    texto.append('PROBLEMAS (%d):' % len(errores))
    for e in errores:
        texto.append(' - ' + e)
else:
    texto.append('Todo correcto: %d pedido(s) listos para crear.' % len(plan))
mensaje = '\n'.join(texto)

if SIMULACION or errores:
    log(mensaje)
    raise Warning(mensaje + (SIMULACION and '\n\nEs una SIMULACION: no se ha creado nada.' or
                             '\n\nNO SE HA CREADO NADA: corrige los problemas y vuelve a ejecutar.'))

# ----------------------------- CREAR -----------------------------------------
ref = Feed.search([('name', 'like', 'W-'), ('state', '=', 'done')], order='id desc', limit=1)
campo_rid = env['ir.model.fields'].search([('model', '=', 's4t.order.feed'), ('name', '=', 's4t_remote_id')], limit=1)
creados = []
nombres = []
for numero, nombre, remote_id, lineas in plan:
    vals_lineas = []
    for sku, cantidad in lineas:
        vals_lineas.append((0, 0, {'s4t_sku': sku, 's4t_quantity': cantidad}))
    feed = Feed.create({
        'name': nombre,
        'company_id': ref.company_id.id,
        's4t_client': '00005555',
        's4t_mode': 'b2c',
        's4t_order_number': numero,
        's4t_remote_id': campo_rid.ttype == 'integer' and remote_id or str(remote_id),
        'state': 'draft',
        'line_ids': vals_lineas,
    })
    feed.action_create_sale_order()
    nuevo = Pedido.search([('name', '=', nombre)], limit=1)
    if not nuevo:
        # Falla: se deshace todo, tambien los pedidos ya creados en esta ejecucion
        log('RECREAR %s FALLIDO. Feed %s: %s' % (nombre, feed.state, feed.response_msg))
        raise Warning('No se ha creado %s (feed %s: %s). No se ha creado NADA.' % (nombre, feed.state, feed.response_msg))
    outs = nuevo.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')
    nuevo.message_post(body='Creado de nuevo a peticion de Koroshi (26/10/2026): el original W-%s tiene la OUT cancelada. '
                            'Lineas segun su correo.' % numero)
    nombres.append(nombre)
    creados.append('%s (id %d, %s) OUT: %s' % (nombre, nuevo.id, nuevo.state,
                                               ', '.join(outs.mapped(lambda p: '%s %s' % (p.name, p.state))) or 'ninguna'))

log('KOROSHI RECREAR PEDIDOS ONLINE - CREADOS: %s' % ' | '.join(creados))
action = {
    'type': 'ir.actions.act_window',
    'name': 'Pedidos recreados',
    'res_model': 'sale.order',
    'view_mode': 'tree,form',
    'domain': [('name', 'in', nombres)],
    'target': 'current',
}

# =============================================================================
# KOROSHI - ¿CUÁNTAS NOCHES TIENE UNA TIENDA MÁS DE UN PEDIDO S-? (SOLO LECTURA) - 24/11/2026
# Para decidir la regla de «duplicados» del diseño bin/versiones/diseno-retener-pedidos-tienda_2026-11-24.md.
# Acción de servidor nueva (modelo sale.order), lanzarla una vez a mano. No crea ni cambia nada: acaba con un aviso.
# Noche = pedidos creados desde las HORA_CORTE del día anterior hasta las HORA_CORTE del día (hora del almacén).
# Saca, por noche, las tiendas con más de un pedido, con número, hora de entrada (local) y unidades de cada uno.
# =============================================================================

DIAS = 90
HORA_CORTE = 14          # 14:00 hora local: lo de la tarde cuenta para la noche siguiente
TIPO_PEDIDO = 'PED. TIENDAS'
COMPANIA = 8

tz = timezone('Europe/Madrid')
desde = datetime.datetime.utcnow() - datetime.timedelta(days=DIAS)
pedidos = env['sale.order'].sudo().with_context(active_test=False).search_read(
    [('company_id', '=', COMPANIA), ('name', '=like', 'S-%'), ('s_order_type_id.name', '=', TIPO_PEDIDO),
     ('create_date', '>=', desde.strftime('%Y-%m-%d %H:%M:%S'))],
    ['name', 'create_date', 'partner_shipping_id', 'state', 'amount_untaxed'], order='create_date asc')

uds = {}
for l in env['sale.order.line'].sudo().read_group([('order_id', 'in', [p['id'] for p in pedidos])],
                                                   ['order_id', 'product_uom_qty'], ['order_id']):
    uds[l['order_id'][0]] = l['product_uom_qty']

por_noche = {}
for p in pedidos:
    local = timezone('UTC').localize(p['create_date']).astimezone(tz)
    noche = local.date()
    if local.hour >= HORA_CORTE:
        noche = noche + datetime.timedelta(days=1)
    tienda = (p['partner_shipping_id'] and p['partner_shipping_id'][1] or '?').split(' ')[0]
    por_noche.setdefault(noche, {}).setdefault(tienda, []).append(
        '%s %s %s uds (%s)' % (p['name'], local.strftime('%H:%M'), int(uds.get(p['id'], 0)), p['state']))

lineas = []
noches_con = 0
pares = 0
for noche in sorted(por_noche):
    dobles = dict((t, v) for t, v in por_noche[noche].items() if len(v) > 1)
    if not dobles:
        continue
    noches_con += 1
    pares += len(dobles)
    lineas.append('%s: %s tiendas con más de un pedido (de %s tiendas esa noche)' % (
        noche.strftime('%d/%m'), len(dobles), len(por_noche[noche])))
    for t in sorted(dobles):
        lineas.append('   %s: %s' % (t, ' | '.join(dobles[t])))

cabecera = '%s pedidos S- de tienda en %s días, %s noches. Noches con alguna tienda repetida: %s (%s tienda-noche).' % (
    len(pedidos), DIAS, len(por_noche), noches_con, pares)
mensaje = cabecera + '\n' + '\n'.join(lineas)
log(mensaje[:4000])
raise Warning(mensaje[:12000])

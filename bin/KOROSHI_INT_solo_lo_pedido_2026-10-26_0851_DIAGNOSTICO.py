# =============================================================================
# KOROSHI - INT: SOLO LO PEDIDO (DIAGNOSTICO)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
# Para probar en la accion de pruebas (id 1837). NO CAMBIA NADA: acaba siempre con un aviso.
#
# Que mira: en los INT que van al SORTER (KOR-..., WEB_...), si se ha leido
#   - un articulo que el INT no pide, o
#   - mas unidades de un articulo de las que pide el INT.
# Es lo mismo que comprobara la regla automatica "KOROSHI INT solo lo pedido", que impedira
# guardar o validar el INT cuando pase. Este diagnostico sirve para ver antes a que INT
# afectaria (los abiertos ahora y los de los ultimos DIAS).
#
# INT: los seleccionados en la lista; sin seleccion, los abiertos y los validados en los
# ultimos DIAS que van al SORTER.
# En los INT ya validados Odoo ya ha sumado lo de mas a lo pedido: solo se ve lo de articulos
# que no estaban (movimientos "anadidos despues"), no las unidades de mas.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
DESTINO = 'SORTER'                # solo INT cuyo destino contiene este texto
DIAS = 7                          # sin seleccion: tambien los validados en los ultimos DIAS
# -----------------------------------------------------------------------------

Picking = env['stock.picking']
if env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    ints = Picking.browse(env.context.get('active_ids'))
else:
    desde = (datetime.datetime.now() - datetime.timedelta(days=DIAS)).strftime('%Y-%m-%d %H:%M:%S')
    ints = Picking.search([('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'internal'),
                           ('location_dest_id.complete_name', 'ilike', DESTINO), '|',
                           ('state', 'not in', ('done', 'cancel', 'draft')), ('date_done', '>=', desde)],
                          order='id desc')

texto = ['KOROSHI INT SOLO LO PEDIDO - DIAGNOSTICO (NO SE HA CAMBIADO NADA)', 'INT mirados: %d' % len(ints), '']
n_mal = 0
n_bien = 0
for p in ints:
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'internal':
        texto.append('%s: se salta (no es un INT de la empresa %d)' % (p.name, COMPANY_ID))
        continue
    if DESTINO.lower() not in (p.location_dest_id.complete_name or '').lower():
        texto.append('%s: se salta (no va a %s, la regla no lo miraria)' % (p.name, DESTINO))
        continue
    pedido = {}                   # producto -> uds que pide el INT (movimientos no cancelados ni anadidos)
    anadidos = {}                 # producto -> uds de movimientos anadidos al validar (no estaban)
    for m in p.move_lines:
        if m.state == 'cancel':
            continue
        if m.additional:
            anadidos[m.product_id.id] = anadidos.get(m.product_id.id, 0) + m.quantity_done
        else:
            pedido[m.product_id.id] = pedido.get(m.product_id.id, 0) + m.product_uom_qty
    leido = {}                    # producto -> uds leidas
    for ml in p.move_line_ids:
        if ml.qty_done > 0:
            leido[ml.product_id.id] = leido.get(ml.product_id.id, 0) + ml.qty_done
    fallos = []
    for pid in leido:
        if pid not in pedido:
            fallos.append('   %s: leidas %d, el INT no lo pide' % (
                env['product.product'].browse(pid).display_name, leido[pid]))
        elif p.state != 'done' and leido[pid] > pedido[pid]:
            fallos.append('   %s: leidas %d, el INT pide %d' % (
                env['product.product'].browse(pid).display_name, leido[pid], pedido[pid]))
    for pid in anadidos:
        if pid in pedido:
            continue
        fallos.append('   %s: %d uds anadidas al validar (el INT no lo pedia)' % (
            env['product.product'].browse(pid).display_name, anadidos[pid]))
    if fallos:
        n_mal += 1
        texto.append('NO PASARIA | %s | %s | %s' % (p.name, p.origin or '', p.state))
        for f in fallos[:15]:
            texto.append(f)
        if len(fallos) > 15:
            texto.append('   ... y %d mas' % (len(fallos) - 15))
    else:
        n_bien += 1

texto.append('')
texto.append('INT que la regla bloquearia: %d | INT bien: %d' % (n_mal, n_bien))
mensaje = '\n'.join(texto)
log(mensaje)
raise Warning(mensaje + '\n\nEs un diagnostico: no se ha cambiado nada.')

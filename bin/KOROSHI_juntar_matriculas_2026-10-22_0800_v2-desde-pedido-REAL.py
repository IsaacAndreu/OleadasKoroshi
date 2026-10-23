# =============================================================================
# KOROSHI - JUNTAR MATRICULAS (meter una caja pequena dentro de otra en expediciones)
# Accion de servidor de Odoo 13. Modelo: sale.order. Tipo: Ejecutar codigo Python.
#
# v2 (22/10/2026): se usa DESDE EL PEDIDO (S-6665...), pestana "Juntar cajas":
#   1. Escanear la CJ pequena en la casilla "CJ pequena" (x_cj_pequena). Se pueden escanear
#      varias seguidas en la misma casilla: todas van a la misma CJ destino.
#   2. Escanear la CJ grande, donde se meten sus uds, en "CJ destino" (x_cj_destino).
#   3. Boton "Juntar". Es REAL: si todo cuadra, junta, vacia las casillas y deja una nota
#      en el historial del pedido. Si algo no cuadra sale un aviso y no se cambia nada.
#   Con las dos casillas vacias, el boton ensena las cajas pequenas del pedido (no cambia nada).
#
# Cada caja es un paquete (stock.quant.package) con el nombre de su matricula CJ, y
# los bultos del envio salen de las CJ. Al meter una caja pequena dentro de otra de la
# MISMA tienda y el MISMO pedido, la CJ pequena deja de contar como bulto:
#   - Lineas de la CJ pequena con la OUT sin validar: pasan a la CJ destino
#     (result_package_id). Al validar, todo queda en la CJ destino.
#   - Lineas de la CJ pequena con la OUT ya validada: pasan a la CJ destino y el
#     stock (quants en Clientes) tambien.
#   - La CJ pequena queda vacia y no se puede volver a usar (Empaquetar caja no deja
#     usar una matricula que ya existe como paquete).
#   No toca number_of_packages ni el envio.
#
# Tambien se puede llamar sin pedido (programa, XML-RPC) con el contexto
# cj_origen / cj_destino (y real = True), o a mano con JUNTAR = [('CJ pequena', 'CJ destino')].
# Sin pedido y sin parejas: PROPUESTA de las agrupaciones AGRUPACION (no cambia nada).
#
# Para deshacer: el registro guarda que lineas y quants se han movido de que CJ a que CJ.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
DIAGNOSTICO = False               # REAL. True: solo comprueba (a mano, sin pedido)
JUNTAR = []                       # a mano: [('CJ665004410', 'CJ665004406'), ...]
AGRUPACION = 'Z-2210-'            # prefijo de las agrupaciones para la propuesta sin pedido
MAX_UDS = 3                       # caja pequena: esta cantidad de uds o menos
# -----------------------------------------------------------------------------

Paquete = env['stock.quant.package']
Linea = env['stock.move.line']


def lineas_de(paquete):
    return Linea.search([('result_package_id', '=', paquete.id), ('state', '!=', 'cancel'), ('qty_done', '>', 0)])


def uds_de(lineas):
    return int(sum(lineas.mapped('qty_done')))


def bultos_pedido(origen):
    outs = env['stock.picking'].search([('origin', '=', origen), ('picking_type_code', '=', 'outgoing'),
                                         ('company_id', '=', COMPANY_ID), ('state', '!=', 'cancel')])
    lin = Linea.search([('picking_id', 'in', outs.ids), ('result_package_id', '!=', False),
                        ('state', '!=', 'cancel'), ('qty_done', '>', 0)])
    return len(lin.mapped('result_package_id'))


def tienda_de(partner):
    nombre = partner and partner.name or ''
    return nombre.split(', ')[-1]


def zonas_de(lineas):
    return ', '.join(sorted(set(lineas.mapped('picking_id.batch_id.name')))) or '-'


texto = []
parejas = list(JUNTAR)
AGRUPACION = env.context.get('agrupacion') or AGRUPACION
if env.context.get('real'):
    DIAGNOSTICO = False
if env.context.get('cj_origen') and env.context.get('cj_destino'):
    parejas = [(env.context.get('cj_origen'), env.context.get('cj_destino'))]

pedido = env['sale.order']
if env.context.get('active_model') == 'sale.order' and env.context.get('active_id'):
    pedido = env['sale.order'].browse(env.context.get('active_id')).exists()
if pedido:
    cj_p = (pedido.x_cj_pequena or '').strip().upper()
    cj_g = (pedido.x_cj_destino or '').strip().upper()
    # Varias CJ pequenas en la misma casilla: escaneadas seguidas (CJ...CJ...) o con espacios/comas
    pequenas = []
    for trozo in cj_p.replace(',', ' ').replace(';', ' ').split('CJ'):
        trozo = trozo.strip()
        if trozo:
            cj = 'CJ' + trozo.split()[0]
            if cj not in pequenas:
                pequenas.append(cj)
    if pequenas and cj_g:
        parejas = []
        for cj in pequenas:
            parejas.append((cj, cj_g))
        DIAGNOSTICO = False
    elif cj_p or cj_g:
        log('KOROSHI JUNTAR MATRICULAS: %s falta una CJ (pequena %s, destino %s)' % (pedido.name, cj_p or '-', cj_g or '-'))
        raise Warning('Falta escanear la %s.\n\nCJ pequena: %s\nCJ destino: %s'
                      % (cj_p and 'CJ destino (la caja grande)' or 'CJ pequena', cj_p or '-', cj_g or '-'))

if not parejas:
    # ------------------------------ PROPUESTA ---------------------------------
    if pedido:
        outs = env['stock.picking'].search([('origin', '=', pedido.name), ('picking_type_code', '=', 'outgoing'),
                                             ('company_id', '=', COMPANY_ID), ('state', '!=', 'cancel')])
        texto.append('CAJAS DEL PEDIDO %s - %s' % (pedido.name, tienda_de(pedido.partner_shipping_id)))
    else:
        outs = env['stock.picking'].search([('batch_id.name', '=like', AGRUPACION + '%'),
                                             ('company_id', '=', COMPANY_ID), ('state', '!=', 'cancel')])
        texto.append('KOROSHI JUNTAR MATRICULAS - PROPUESTA (NO SE HA CAMBIADO NADA)')
        texto.append('Agrupaciones %s*' % AGRUPACION)
    lin = Linea.search([('picking_id', 'in', outs.ids), ('result_package_id', '!=', False),
                        ('state', '!=', 'cancel'), ('qty_done', '>', 0)])
    texto.append('Cajas cerradas (CJ): %d | pequena: %d uds o menos' % (len(lin.mapped('result_package_id')), MAX_UDS))
    texto.append('')
    por_pedido = {}
    for ml in lin:
        origen = ml.picking_id.origin or ml.picking_id.name
        if origen not in por_pedido:
            por_pedido[origen] = {}
        pid = ml.result_package_id.id
        por_pedido[origen][pid] = por_pedido[origen].get(pid, 0) + ml.qty_done
    n_peq = 0
    for origen in sorted(por_pedido.keys()):
        cajas = por_pedido[origen]
        grande_id = 0
        grande_uds = -1
        for pid in cajas:
            if cajas[pid] > grande_uds:
                grande_id = pid
                grande_uds = cajas[pid]
        peq = []
        for pid in cajas:
            if pid != grande_id and cajas[pid] <= MAX_UDS:
                peq.append(pid)
        if not peq:
            continue
        grande = Paquete.browse(grande_id)
        for pid in peq:
            p = Paquete.browse(pid)
            lp = lineas_de(p)
            texto.append('   %s | %s | %s (%d uds, %s) -> %s (%d uds, %s)' % (
                origen, tienda_de(lp[:1].picking_id.partner_id), p.name, cajas[pid], zonas_de(lp),
                grande.name, grande_uds, zonas_de(lineas_de(grande))))
            n_peq += 1
        texto.append('      bultos del pedido: %d -> %d' % (len(cajas), len(cajas) - len(peq)))
    texto.append('')
    texto.append('Cajas pequenas que se pueden juntar: %d' % n_peq)
    if pedido:
        texto.append('Para juntar: escanear la CJ pequena y la CJ destino y pulsar Juntar.')
    mensaje = '\n'.join(texto)
    log(mensaje)
    raise Warning(mensaje)

# --------------------------------- JUNTAR -------------------------------------
texto.append('KOROSHI JUNTAR MATRICULAS - %s%s' % (DIAGNOSTICO and 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)' or 'HECHO',
                                                  pedido and (' - ' + pedido.name) or ''))
errores = []
trabajo = []      # (pequena, destino, lineas)
usadas = {}
for par in parejas:
    cj_o = (par[0] or '').strip().upper()
    cj_d = (par[1] or '').strip().upper()
    if cj_o == cj_d:
        errores.append('%s: la CJ pequena y la destino son la misma' % cj_o)
        continue
    if cj_o in usadas or cj_d in usadas and usadas[cj_d] == 'origen':
        errores.append('%s / %s: una CJ sale dos veces o se junta en una que ya se vacia' % (cj_o, cj_d))
        continue
    usadas[cj_o] = 'origen'
    usadas[cj_d] = usadas.get(cj_d) or 'destino'
    po = Paquete.search([('name', '=', cj_o)])
    pd = Paquete.search([('name', '=', cj_d)])
    if len(po) != 1:
        errores.append('%s: no es una caja cerrada (paquetes con ese nombre: %d)' % (cj_o, len(po)))
        continue
    if len(pd) != 1:
        errores.append('%s: no es una caja cerrada (paquetes con ese nombre: %d)' % (cj_d, len(pd)))
        continue
    lo = lineas_de(po)
    ld = lineas_de(pd)
    if not lo:
        errores.append('%s: esta vacia (ya juntada?)' % cj_o)
        continue
    if not ld:
        errores.append('%s: la caja destino esta vacia' % cj_d)
        continue
    ped_o = set(lo.mapped('picking_id.origin'))
    ped_d = set(ld.mapped('picking_id.origin'))
    cli_o = set(lo.mapped('picking_id.partner_id.id'))
    cli_d = set(ld.mapped('picking_id.partner_id.id'))
    if len(ped_o) != 1 or ped_o != ped_d:
        errores.append('%s (%s) -> %s (%s): no son del mismo pedido'
                       % (cj_o, ', '.join(sorted(lo.mapped('picking_id.name'))), cj_d, ', '.join(sorted(ld.mapped('picking_id.name')))))
        continue
    if pedido and ped_o != set([pedido.name]):
        errores.append('%s y %s son del pedido %s, no de %s' % (cj_o, cj_d, ', '.join(ped_o), pedido.name))
        continue
    if cli_o != cli_d:
        errores.append('%s -> %s: no son de la misma tienda' % (cj_o, cj_d))
        continue
    if lo.mapped('picking_id.company_id').ids != [COMPANY_ID]:
        errores.append('%s: no es de la empresa %d' % (cj_o, COMPANY_ID))
        continue
    trabajo.append((po, pd, lo))

texto.append('Parejas: %d | correctas: %d | con error: %d' % (len(parejas), len(trabajo), len(errores)))
pedidos = {}
for t in trabajo:
    po, pd, lo = t
    hechas = lo.filtered(lambda ml: ml.state == 'done')
    quants = env['stock.quant'].sudo().search([('package_id', '=', po.id)])
    origen = lo[:1].picking_id.origin
    if origen not in pedidos:
        pedidos[origen] = bultos_pedido(origen)
    texto.append('   %s (%d uds, %s) -> %s | %s | %s | lineas %d (sin validar %d / validadas %d) | quants %d' % (
        po.name, uds_de(lo), zonas_de(lo), pd.name, origen, tienda_de(lo[:1].picking_id.partner_id),
        len(lo), len(lo) - len(hechas), len(hechas), len(quants)))
if errores:
    texto.append('')
    texto.append('No se puede juntar:')
    for e in errores:
        texto.append('   ' + e)

if errores:
    mensaje = '\n'.join(texto)
    log(mensaje + '\nNO SE HA CAMBIADO NADA')
    raise Warning(mensaje + '\n\nNO SE HA CAMBIADO NADA.')

if not DIAGNOSTICO:
    texto.append('Movido (para deshacer):')
    fallos = []
    for t in trabajo:
        po, pd, lo = t
        quants = env['stock.quant'].sudo().search([('package_id', '=', po.id)])
        texto.append('   %s -> %s | lineas %s | quants %s' % (po.name, pd.name, str(lo.ids), str(quants.ids)))
        lo.write({'result_package_id': pd.id})
        if quants:
            quants.write({'package_id': pd.id})
        if lineas_de(po) or env['stock.quant'].sudo().search_count([('package_id', '=', po.id)]):
            fallos.append('%s sigue teniendo lineas o stock' % po.name)
    for origen in sorted(pedidos.keys()):
        texto.append('Bultos del pedido %s: %d -> %d' % (origen, pedidos[origen], bultos_pedido(origen)))
    if fallos:
        mensaje = '\n'.join(texto)
        log(mensaje + '\nFALLOS: ' + ' | '.join(fallos) + '\nSE DESHACE TODO')
        raise Warning('No cuadra, no se ha cambiado nada:\n' + '\n'.join(fallos))
    texto.append('fallos: 0')
    if pedido:
        pedido.write({'x_cj_pequena': False, 'x_cj_destino': False})
        resumen = []
        for t in trabajo:
            resumen.append('%s (%d uds) metida en %s' % (t[0].name, uds_de(t[2]), t[1].name))
        pedido.message_post(body='Juntar cajas: ' + '; '.join(resumen) + '. Bultos del pedido: %d -> %d'
                            % (pedidos[pedido.name], bultos_pedido(pedido.name)))

mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + '\n\nEs un diagnostico: no se ha cambiado nada. Para juntar: DIAGNOSTICO = False.')
action = {'type': 'ir.actions.act_window_close', 'juntadas': len(trabajo)}
# Sin aviso al final: un raise Warning desharia el cambio. El resultado queda en el registro
# y en el historial del pedido.

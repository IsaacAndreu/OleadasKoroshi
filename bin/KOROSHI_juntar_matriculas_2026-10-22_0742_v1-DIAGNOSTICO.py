# =============================================================================
# KOROSHI - JUNTAR MATRICULAS (meter una caja pequena dentro de otra en expediciones)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Cada caja es un paquete (stock.quant.package) con el nombre de su matricula CJ, y
# los bultos del envio salen de las CJ. Si en expediciones se mete una caja pequena
# dentro de otra de la MISMA tienda y el MISMO pedido, hay que decirselo a Odoo para
# que la CJ pequena deje de contar como bulto.
#
# Que hace con cada pareja (CJ pequena -> CJ destino):
#   - Lineas de la CJ pequena con la OUT sin validar: pasan a la CJ destino
#     (result_package_id). Al validar, todo queda en la CJ destino.
#   - Lineas de la CJ pequena con la OUT ya validada: pasan a la CJ destino y el
#     stock (quants en Clientes) tambien.
#   - La CJ pequena queda vacia y no se puede volver a usar (Empaquetar caja no deja
#     usar una matricula que ya existe como paquete).
#   No toca number_of_packages ni el envio: ensena los bultos del pedido antes y despues.
#
# Dos formas de usarla:
#   1. JUNTAR vacio: PROPUESTA. Busca en las agrupaciones AGRUPACION (prefijo) las CJ
#      cerradas con MAX_UDS uds o menos y propone meterlas en la CJ mas grande del
#      mismo pedido. No cambia nada.
#   2. JUNTAR = [('CJ pequena', 'CJ destino'), ...] (o en el contexto cj_origen /
#      cj_destino, para llamarla desde el programa): comprueba y, con
#      DIAGNOSTICO = False, junta. Si algo no cuadra no se cambia nada.
#
# Para deshacer: el registro guarda que lineas y quants se han movido de que CJ a que CJ.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
DIAGNOSTICO = True                # True: solo comprueba. False: junta
JUNTAR = []                       # [('CJ665004410', 'CJ665004406'), ...]; vacio = propuesta
AGRUPACION = 'Z-2210-'            # prefijo de las agrupaciones para la propuesta
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


texto = []
parejas = list(JUNTAR)
AGRUPACION = env.context.get('agrupacion') or AGRUPACION
if env.context.get('real'):
    DIAGNOSTICO = False           # el programa la llama con real = True
if env.context.get('cj_origen') and env.context.get('cj_destino'):
    parejas = [(env.context.get('cj_origen'), env.context.get('cj_destino'))]

if not parejas:
    # ------------------------------ PROPUESTA ---------------------------------
    texto.append('KOROSHI JUNTAR MATRICULAS - PROPUESTA (NO SE HA CAMBIADO NADA)')
    texto.append('Agrupaciones %s* | caja pequena: %d uds o menos' % (AGRUPACION, MAX_UDS))
    outs = env['stock.picking'].search([('batch_id.name', '=like', AGRUPACION + '%'),
                                         ('company_id', '=', COMPANY_ID), ('state', '!=', 'cancel')])
    lin = Linea.search([('picking_id', 'in', outs.ids), ('result_package_id', '!=', False),
                        ('state', '!=', 'cancel'), ('qty_done', '>', 0)])
    texto.append('OUT: %d | cajas cerradas (CJ): %d' % (len(outs), len(lin.mapped('result_package_id'))))
    texto.append('')
    # pedido -> {paquete id: uds}
    por_pedido = {}
    for ml in lin:
        origen = ml.picking_id.origin or ml.picking_id.name
        if origen not in por_pedido:
            por_pedido[origen] = {}
        pid = ml.result_package_id.id
        por_pedido[origen][pid] = por_pedido[origen].get(pid, 0) + ml.qty_done
    n_peq = 0
    n_sin = 0
    texto.append('Pedido | tienda | CJ pequena (uds, zona) -> CJ destino (uds, zona) | bultos pedido antes -> despues')
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
        lg = lineas_de(grande)
        zona_g = ', '.join(sorted(set(lg.mapped('picking_id.batch_id.name')))).replace(AGRUPACION, '')
        for pid in peq:
            p = Paquete.browse(pid)
            lp = lineas_de(p)
            zona_p = ', '.join(sorted(set(lp.mapped('picking_id.batch_id.name')))).replace(AGRUPACION, '')
            texto.append('   %s | %s | %s (%d, %s) -> %s (%d, %s)' % (
                origen, tienda_de(lp[:1].picking_id.partner_id), p.name, cajas[pid], zona_p,
                grande.name, grande_uds, zona_g))
            n_peq += 1
        texto.append('      bultos del pedido: %d -> %d' % (len(cajas), len(cajas) - len(peq)))
    for origen in por_pedido:
        if len(por_pedido[origen]) == 1:
            for pid in por_pedido[origen]:
                if por_pedido[origen][pid] <= MAX_UDS:
                    n_sin += 1
    texto.append('')
    texto.append('Total: %d cajas pequenas se pueden juntar' % n_peq)
    if n_sin:
        texto.append('%d pedidos tienen una sola caja y es pequena: no hay donde meterla' % n_sin)
    texto.append('Para juntar: JUNTAR = [(\'CJ pequena\', \'CJ destino\'), ...] y DIAGNOSTICO = False')
    mensaje = '\n'.join(texto)
    log(mensaje)
    raise Warning(mensaje)

# --------------------------------- JUNTAR -------------------------------------
texto.append('KOROSHI JUNTAR MATRICULAS - %s' % (DIAGNOSTICO and 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)' or 'HECHO'))
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
    if cli_o != cli_d:
        errores.append('%s -> %s: no son de la misma tienda' % (cj_o, cj_d))
        continue
    if lo.mapped('picking_id.company_id').ids != [COMPANY_ID]:
        errores.append('%s: no es de la empresa %d' % (cj_o, COMPANY_ID))
        continue
    trabajo.append((po, pd, lo))

texto.append('Parejas: %d | correctas: %d | con error: %d' % (len(parejas), len(trabajo), len(errores)))
texto.append('')
texto.append('CJ pequena -> CJ destino | pedido | tienda | uds | lineas (sin validar / validadas) | quants | bultos pedido antes')
pedidos = {}
for t in trabajo:
    po, pd, lo = t
    hechas = lo.filtered(lambda ml: ml.state == 'done')
    quants = env['stock.quant'].sudo().search([('package_id', '=', po.id)])
    origen = lo[:1].picking_id.origin
    if origen not in pedidos:
        pedidos[origen] = bultos_pedido(origen)
    texto.append('   %s -> %s | %s | %s | %d | %d (%d / %d) | %d | %d' % (
        po.name, pd.name, origen, tienda_de(lo[:1].picking_id.partner_id), uds_de(lo),
        len(lo), len(lo) - len(hechas), len(hechas), len(quants), pedidos[origen]))
if errores:
    texto.append('')
    texto.append('No se pueden juntar:')
    for e in errores:
        texto.append('   ' + e)

if not DIAGNOSTICO:
    if errores:
        mensaje = '\n'.join(texto)
        log(mensaje + '\nNO SE HA CAMBIADO NADA: hay parejas con error')
        raise Warning(mensaje + '\n\nNO SE HA CAMBIADO NADA: corregir las parejas con error.')
    texto.append('')
    texto.append('Movido (para deshacer):')
    fallos = []
    for t in trabajo:
        po, pd, lo = t
        quants = env['stock.quant'].sudo().search([('package_id', '=', po.id)])
        texto.append('   %s -> %s | lineas %s | quants %s' % (po.name, pd.name, str(lo.ids), str(quants.ids)))
        lo.write({'result_package_id': pd.id})
        if quants:
            quants.write({'package_id': pd.id})
        # Comprobacion
        if lineas_de(po) or env['stock.quant'].sudo().search_count([('package_id', '=', po.id)]):
            fallos.append('%s sigue teniendo lineas o stock' % po.name)
    texto.append('')
    texto.append('Bultos del pedido despues:')
    for origen in sorted(pedidos.keys()):
        texto.append('   %s: %d -> %d' % (origen, pedidos[origen], bultos_pedido(origen)))
    if fallos:
        mensaje = '\n'.join(texto)
        log(mensaje + '\nFALLOS: ' + ' | '.join(fallos) + '\nSE DESHACE TODO')
        raise Warning('No cuadra, se deshace todo:\n' + '\n'.join(fallos))
    texto.append('fallos: 0')

mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + '\n\nEs un diagnostico: no se ha cambiado nada. Para juntar: DIAGNOSTICO = False.')
action = {'type': 'ir.actions.act_window_close', 'juntadas': len(trabajo)}
# Sin aviso al final: un raise Warning desharia el cambio. El resultado queda en el registro.

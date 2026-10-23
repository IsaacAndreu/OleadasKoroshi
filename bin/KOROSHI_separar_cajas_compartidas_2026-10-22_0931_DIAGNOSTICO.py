# =============================================================================
# KOROSHI - SEPARAR CAJAS COMPARTIDAS ENTRE OUT (despues de "Juntar matriculas" v2/v3)
# Accion de servidor de Odoo 13. Modelo: sale.order. Tipo: Ejecutar codigo Python.
#
# "Juntar matriculas" v2/v3 metia las lineas de la caja pequena en la caja grande aunque fueran
# de OUT distintas. Asi la misma matricula salia en las dos OUT (p.ej. CJ665004135 en la 20225 y
# en la 20226 de K40) y, al contar las matriculas de cada OUT para las etiquetas del
# transportista, esa caja salia dos veces.
#
# Esta accion, en los pedidos juntados (registro "JUNTAR MATRICULAS - HECHO" sin fallos, o los de
# PEDIDOS), busca las cajas con lineas de mas de una OUT. Cada caja se queda en su OUT duena (la
# que tiene mas uds dentro; si empatan, la OUT mas antigua). En las otras OUT:
#   - quita la matricula a sus lineas (result_package_id). El stock (quants) se queda en la caja
#     grande: la caja sigue diciendo que lleva esas prendas, pero la OUT pequena no tiene matricula,
#   - borra su registro de paquete (stock.package_level) de esa caja (las lineas no se borran:
#     el enlace es "set null"),
#   - deja una nota en la OUT: "sus N uds van dentro de la caja CJ... (OUT ...)".
# Despues pone "Numero de bultos" (number_of_packages) de cada OUT validada o con cajas = sus cajas.
# Solo lineas de OUT VALIDADAS (las no validadas se dejan y se avisa).
#
# DIAGNOSTICO = True: no cambia nada, ensena lo que haria. Con real = True en el contexto: REAL.
# Si en REAL algo no cuadra al final, raise: no se cambia nada.
# Para deshacer: el registro guarda las lineas (ids) y la caja de cada una.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
DIAGNOSTICO = True                # True: solo ensena. False: separa
PEDIDOS = []                      # vacio = los juntados segun el registro; o ['S-6665003328', ...]
DESDE = '2026-10-22 00:00:00'     # registro de Juntar desde esta fecha (UTC)
# -----------------------------------------------------------------------------

if env.context.get('real'):
    DIAGNOSTICO = False

Linea = env['stock.move.line']
Quant = env['stock.quant'].sudo()


def outs_de(origen):
    return env['stock.picking'].search([('origin', '=', origen), ('picking_type_code', '=', 'outgoing'),
                                        ('company_id', '=', COMPANY_ID), ('state', '!=', 'cancel')])


def lineas_en_caja(outs):
    return Linea.search([('picking_id', 'in', outs.ids), ('result_package_id', '!=', False),
                         ('state', '!=', 'cancel'), ('qty_done', '>', 0)])


def sacar_de_caja(lineas, paquete):
    # Quita la matricula a estas lineas y borra los registros de paquete que se quedan sin lineas.
    # El stock se queda en la caja grande (las prendas estan dentro). No borra lineas ni cantidades.
    # Odoo, al quitar la caja a una linea validada, saca ese stock de la caja: se vuelve a meter.
    niveles = lineas.mapped('package_level_id')
    lineas.write({'result_package_id': False, 'package_level_id': False})
    for ml in lineas:
        if ml.state == 'done':
            Quant._update_available_quantity(ml.product_id, ml.location_dest_id, -ml.qty_done,
                                             lot_id=ml.lot_id, package_id=None, owner_id=ml.owner_id)
            Quant._update_available_quantity(ml.product_id, ml.location_dest_id, ml.qty_done,
                                             lot_id=ml.lot_id, package_id=paquete, owner_id=ml.owner_id)
    for nv in niveles:
        if not nv.move_line_ids:
            nv.unlink()


def bultos_reales(outs):
    # Numero de bultos de cada OUT validada o con cajas = cajas distintas en sus lineas.
    # Si una caja aun saliera en varias OUT, cuenta solo en la de mas uds.
    lin = lineas_en_caja(outs)
    reparto = {}
    for ml in lin:
        pq = ml.result_package_id.id
        if pq not in reparto:
            reparto[pq] = {}
        reparto[pq][ml.picking_id.id] = reparto[pq].get(ml.picking_id.id, 0) + ml.qty_done
    cuenta = {}
    con_caja = {}
    for pq in reparto:
        dueno = 0
        mejor = -1
        for pi in sorted(reparto[pq].keys()):
            con_caja[pi] = 1
            if reparto[pq][pi] > mejor:
                dueno = pi
                mejor = reparto[pq][pi]
        cuenta[dueno] = cuenta.get(dueno, 0) + 1
    res = []
    for p in outs:
        if p.id in con_caja or p.state == 'done':
            res.append((p, cuenta.get(p.id, 0)))
    return res


pedidos = list(PEDIDOS)
if not pedidos:
    regs = env['ir.logging'].search([('message', 'like', 'KOROSHI JUNTAR MATRICULAS - HECHO - S-'),
                                     ('message', 'like', 'fallos: 0'),
                                     ('create_date', '>=', DESDE)], order='id asc')
    for r in regs:
        nombre = r.message.split('HECHO - ')[1].split('\n')[0].strip()
        if nombre and nombre not in pedidos:
            pedidos.append(nombre)

texto = ['KOROSHI SEPARAR CAJAS COMPARTIDAS - %s' % (DIAGNOSTICO and 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)' or 'HECHO')]
texto.append('Pedidos: %d (%s)' % (len(pedidos), ', '.join(pedidos)))
fallos = []
n_lineas = 0
for origen in pedidos:
    outs = outs_de(origen)
    lin = lineas_en_caja(outs)
    tienda = (outs[:1].partner_id.name or '').split(', ')[-1]
    texto.append('')
    texto.append('%s | %s | %d OUT | cajas %d | suma bultos OUT antes %d' % (
        origen, tienda, len(outs), len(lin.mapped('result_package_id')), sum(outs.mapped('number_of_packages'))))
    # caja -> {OUT id: uds}; y stock de cada caja antes (no debe cambiar)
    stock_antes = {}
    for pq in lin.mapped('result_package_id').ids:
        stock_antes[pq] = sum(Quant.search([('package_id', '=', pq)]).mapped('quantity'))
    reparto = {}
    for ml in lin:
        pq = ml.result_package_id.id
        if pq not in reparto:
            reparto[pq] = {}
        reparto[pq][ml.picking_id.id] = reparto[pq].get(ml.picking_id.id, 0) + ml.qty_done
    for pq in sorted(reparto.keys()):
        if len(reparto[pq]) < 2:
            continue
        caja = env['stock.quant.package'].browse(pq)
        dueno = 0
        mejor = -1
        for pi in sorted(reparto[pq].keys()):
            if reparto[pq][pi] > mejor:
                dueno = pi
                mejor = reparto[pq][pi]
        out_d = env['stock.picking'].browse(dueno)
        texto.append('   Caja %s compartida: se queda en %s (%d uds)' % (caja.name, out_d.name, mejor))
        for pi in sorted(reparto[pq].keys()):
            if pi == dueno:
                continue
            p = env['stock.picking'].browse(pi)
            lp = lin.filtered(lambda ml: ml.picking_id.id == pi and ml.result_package_id.id == pq)
            sin_validar = lp.filtered(lambda ml: ml.state != 'done')
            if sin_validar:
                texto.append('      %s: %d uds SIN VALIDAR, no se toca (validarla y repetir)' % (p.name, reparto[pq][pi]))
                continue
            texto.append('      %s: se le quita la caja a %d lineas (%d uds) | lineas %s' % (
                p.name, len(lp), reparto[pq][pi], str(lp.ids)))
            n_lineas += len(lp)
            if not DIAGNOSTICO:
                sacar_de_caja(lp, caja)
                p.message_post(body='Juntar cajas: las %d uds de esta OUT van dentro de la caja %s (OUT %s), que es la que lleva la matricula. '
                                    'Esta OUT no tiene bultos propios.' % (reparto[pq][pi], caja.name, out_d.name))
    # Numero de bultos
    for c in bultos_reales(outs):
        if not DIAGNOSTICO and c[0].number_of_packages != c[1]:
            texto.append('   Numero de bultos %s: %d -> %d' % (c[0].name, c[0].number_of_packages, c[1]))
            c[0].write({'number_of_packages': c[1]})
    if DIAGNOSTICO:
        texto.append('   Numero de bultos despues: cada OUT = sus cajas propias; la OUT que se queda sin caja -> 0')
    else:
        # Comprobaciones
        lin2 = lineas_en_caja(outs)
        rep2 = {}
        for ml in lin2:
            pq = ml.result_package_id.id
            if pq not in rep2:
                rep2[pq] = {}
            rep2[pq][ml.picking_id.id] = 1
        for pq in rep2:
            if len(rep2[pq]) > 1:
                fallos.append('%s: la caja %s sigue en %d OUT' % (origen, env['stock.quant.package'].browse(pq).name, len(rep2[pq])))
        for pq in stock_antes:
            uds_q = sum(Quant.search([('package_id', '=', pq)]).mapped('quantity'))
            if uds_q != stock_antes[pq]:
                fallos.append('%s: el stock de la caja %s ha cambiado (%d -> %d)' % (
                    origen, env['stock.quant.package'].browse(pq).name, stock_antes[pq], uds_q))
        texto.append('   Despues: cajas %d | suma bultos OUT %d' % (len(lin2.mapped('result_package_id')),
                                                                   sum(outs.mapped('number_of_packages'))))
texto.append('')
texto.append('Lineas a separar: %d' % n_lineas)
if fallos:
    mensaje = '\n'.join(texto)
    log(mensaje + '\nFALLOS: ' + ' | '.join(fallos) + '\nSE DESHACE TODO')
    raise Warning('No cuadra, no se ha cambiado nada:\n' + '\n'.join(fallos))
if not DIAGNOSTICO:
    texto.append('fallos: 0')

mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + '\n\nEs un diagnostico: no se ha cambiado nada. Para separar: DIAGNOSTICO = False.')
# Sin aviso al final: un raise Warning desharia el cambio. El resultado queda en el registro.

# =============================================================================
# KOROSHI - RECALCULAR EL NUMERO DE BULTOS DE LOS PEDIDOS YA JUNTADOS
# Accion de servidor de Odoo 13. Modelo: sale.order. Tipo: Ejecutar codigo Python.
#
# "Juntar matriculas" v2 movia las uds de la CJ pequena a la grande, pero no tocaba el campo
# "Numero de bultos" (number_of_packages) de las OUT. Asi, por ejemplo, en K40 (S-6665003328)
# la OUT 20225 seguia con 2 bultos aunque su caja ya estaba dentro de la de la 20226, y la
# caja compartida contaba en las dos OUT: suma 12 y son 10.
#
# Esta accion, para los pedidos que salen en el registro como "JUNTAR MATRICULAS - HECHO" sin
# fallos (o los de PEDIDOS si se rellena), recalcula number_of_packages de cada OUT con las
# cajas reales: cada caja CJ cuenta en una sola OUT, la que tiene mas uds dentro (si empatan,
# la OUT mas antigua). Solo toca OUT que tienen alguna linea en caja. Igual que Juntar v3.
#
# DIAGNOSTICO = True: no cambia nada, ensena lo que haria.
# Para deshacer: el registro guarda "OUT: antes -> despues".
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
DIAGNOSTICO = True                # True: solo ensena. False: corrige
PEDIDOS = []                      # vacio = los juntados segun el registro; o ['S-6665003328', ...]
DESDE = '2026-10-22 00:00:00'     # registro de Juntar desde esta fecha (UTC)
# -----------------------------------------------------------------------------

if env.context.get('real'):
    DIAGNOSTICO = False           # lanzada con real = True en el contexto

Linea = env['stock.move.line']


def recalcular_bultos(origen):
    # Igual que en "Juntar matriculas" v3
    outs = env['stock.picking'].search([('origin', '=', origen), ('picking_type_code', '=', 'outgoing'),
                                         ('company_id', '=', COMPANY_ID), ('state', '!=', 'cancel')])
    lin = Linea.search([('picking_id', 'in', outs.ids), ('result_package_id', '!=', False),
                        ('state', '!=', 'cancel'), ('qty_done', '>', 0)])
    reparto = {}
    con_caja = {}
    for ml in lin:
        pq = ml.result_package_id.id
        pi = ml.picking_id.id
        con_caja[pi] = 1
        if pq not in reparto:
            reparto[pq] = {}
        reparto[pq][pi] = reparto[pq].get(pi, 0) + ml.qty_done
    cuenta = {}
    for pq in reparto:
        dueno = 0
        mejor = -1
        for pi in sorted(reparto[pq].keys()):
            if reparto[pq][pi] > mejor:
                dueno = pi
                mejor = reparto[pq][pi]
        cuenta[dueno] = cuenta.get(dueno, 0) + 1
    cambios = []
    for p in outs:
        if p.id not in con_caja:
            continue
        n = cuenta.get(p.id, 0)
        if p.number_of_packages != n:
            cambios.append((p, p.number_of_packages, n))
    return outs, len(reparto), cambios


pedidos = list(PEDIDOS)
if not pedidos:
    regs = env['ir.logging'].search([('message', 'like', 'KOROSHI JUNTAR MATRICULAS - HECHO - S-'),
                                     ('message', 'like', 'fallos: 0'),
                                     ('create_date', '>=', DESDE)], order='id asc')
    for r in regs:
        nombre = r.message.split('HECHO - ')[1].split('\n')[0].strip()
        if nombre and nombre not in pedidos:
            pedidos.append(nombre)

texto = ['KOROSHI RECALCULAR BULTOS PEDIDOS JUNTADOS - %s' % (DIAGNOSTICO and 'DIAGNOSTICO (NO SE HA CAMBIADO NADA)' or 'HECHO')]
texto.append('Pedidos: %d (%s)' % (len(pedidos), ', '.join(pedidos)))
texto.append('')
n_cambios = 0
for origen in pedidos:
    outs, n_cajas, cambios = recalcular_bultos(origen)
    antes = sum(outs.mapped('number_of_packages'))
    tienda = outs[:1].partner_id.name or ''
    total = antes
    for c in cambios:
        total += c[2] - c[1]
    texto.append('%s | %s | cajas reales %d | suma de bultos de las OUT %d -> %d' % (
        origen, tienda.split(', ')[-1], n_cajas, antes, total))
    for c in cambios:
        texto.append('   %s: %d -> %d' % (c[0].name, c[1], c[2]))
        n_cambios += 1
        if not DIAGNOSTICO:
            c[0].write({'number_of_packages': c[2]})
    if not cambios:
        texto.append('   (ya cuadra)')
texto.append('')
texto.append('OUT a cambiar: %d' % n_cambios)

mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + '\n\nEs un diagnostico: no se ha cambiado nada. Para corregir: DIAGNOSTICO = False.')
# Sin aviso al final: un raise Warning desharia el cambio. El resultado queda en el registro.

# =============================================================================
# KOROSHI - INT: SOLO LO PEDIDO (REGLA AUTOMATICA)
# Odoo 13: Ajustes > Tecnico > Automatizacion > Acciones automatizadas > Crear
#   Nombre:      KOROSHI INT solo lo pedido
#   Modelo:      Movimientos de stock - lineas (stock.move.line)
#   Disparador:  Al crear y actualizar
#   Campos que disparan: Hecho (qty_done) y Producto (product_id)
#   Dominio (filtro):  [("picking_id.company_id", "=", 8),
#                       ("picking_id.picking_type_code", "=", "internal"),
#                       ("picking_id.location_dest_id.complete_name", "ilike", "SORTER"),
#                       ("qty_done", ">", 0)]
#   Accion:      Ejecutar codigo Python (este codigo)
#
# Que hace: cuando en un INT que va al SORTER (KOR-..., WEB_...) se guarda una lectura de
#   - un articulo que el INT no pide, o
#   - mas unidades de un articulo de las que pide el INT,
# con BLOQUEAR = True no deja guardar (ni validar): sale el aviso en la PDA y no se hace nada.
# Con BLOQUEAR = False solo lo apunta en el registro (Tecnico > Registro, "KOROSHI INT SOLO LO
# PEDIDO") y deja seguir: para ver unos dias a quien le saltaria antes de bloquear.
# La PDA guarda las lecturas al validar (y a veces antes), asi que el aviso sale como muy
# tarde al pulsar Validar, con el INT aun sin validar.
#
# Lo pedido = movimientos del INT no cancelados y no anadidos despues. Las acciones KOROSHI que
# ponen cantidades en los INT (crear INT por zonas) ponen lo reservado, nunca mas: no saltan.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

BLOQUEAR = False                  # False: solo apunta en el registro. True: no deja guardar ni validar

hechos = []
for ml in records:
    p = ml.picking_id
    if p and p.id not in hechos and p.state not in ('done', 'cancel'):
        hechos.append(p.id)

for p in env['stock.picking'].browse(hechos):
    pedido = {}
    for m in p.move_lines:
        if m.state != 'cancel' and not m.additional:
            pedido[m.product_id.id] = pedido.get(m.product_id.id, 0) + m.product_uom_qty
    leido = {}
    for l in p.move_line_ids:
        if l.qty_done > 0:
            leido[l.product_id.id] = leido.get(l.product_id.id, 0) + l.qty_done
    fallos = []
    for pid in leido:
        nombre = env['product.product'].browse(pid).display_name
        if pid not in pedido:
            fallos.append('%s: has leido %d y este INT no lo pide' % (nombre, leido[pid]))
        elif leido[pid] > pedido[pid]:
            fallos.append('%s: has leido %d y el INT pide %d' % (nombre, leido[pid], pedido[pid]))
    if not fallos:
        continue
    log('KOROSHI INT SOLO LO PEDIDO - %s %s (%s) usuario %s: %s' % (
        BLOQUEAR and 'BLOQUEADO' or 'AVISO', p.name, p.origin or '', env.user.name, ' | '.join(fallos)))
    if BLOQUEAR:
        raise Warning('%s: solo se puede coger lo que pide el INT.\n\n%s\n\n'
                      'Quita lo que sobra (devuelvelo a su hueco) y vuelve a guardar o validar.'
                      % (p.name, '\n'.join(fallos[:10])))

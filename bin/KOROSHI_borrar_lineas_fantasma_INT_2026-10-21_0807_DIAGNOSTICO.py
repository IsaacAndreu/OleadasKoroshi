# =============================================================================
# KOROSHI - BORRAR LAS LINEAS "FANTASMA" DE LOS INT ANTES DE VALIDAR
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Cuando el picker escanea con la PDA un articulo que no es el del hueco, queda en el INT
# una linea sin movimiento, con 0 reservado y 0 hecho. Al validar, Odoo crea un movimiento
# para esa linea, junta los movimientos del mismo articulo, borra uno y da el error
# "El registro no existe o ha sido eliminado (stock.move ...)". Esto pasaba el 21/10.
# Esta accion borra esas lineas (no tocan stock: no tienen nada reservado ni hecho).
#
# INT: los de INT_NOMBRES; si esta vacio, los seleccionados en la lista; si no hay
# seleccion, los INT KOR del dia (origen KOR-ddmm-...) que no estan hechos.
# DIAGNOSTICO = True: no borra nada, solo las lista.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
PREFIJO_INT = 'KOR-'
ZONA_HORARIA = 'Europe/Madrid'
INT_NOMBRES = []                  # p. ej. ['EFFEC/INT/66208']
DIAGNOSTICO = True                # True: solo lista. False: borra
# -----------------------------------------------------------------------------

hoy = datetime.datetime.now(timezone(ZONA_HORARIA)).strftime('%d%m')
if INT_NOMBRES:
    ints = env['stock.picking'].search([('name', 'in', INT_NOMBRES), ('company_id', '=', COMPANY_ID)])
elif env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    ints = env['stock.picking'].browse(env.context.get('active_ids'))
else:
    ints = env['stock.picking'].search([
        ('company_id', '=', COMPANY_ID),
        ('picking_type_code', '=', 'internal'),
        ('origin', '=like', '%s%s-%%' % (PREFIJO_INT, hoy)),
        ('state', 'not in', ('done', 'cancel')),
    ], order='name asc')

texto = ['KOROSHI BORRAR LINEAS FANTASMA - ' + (DIAGNOSTICO and 'DIAGNOSTICO (NO SE HA BORRADO NADA)' or 'HECHO')]
total = 0
for p in ints:
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'internal' or p.state in ('done', 'cancel'):
        texto.append('%s: se salta (no es un INT abierto de la empresa %d)' % (p.name, COMPANY_ID))
        continue
    fantasma = env['stock.move.line'].search([
        ('picking_id', '=', p.id),
        ('move_id', '=', False),
        ('qty_done', '=', 0),
        ('product_uom_qty', '=', 0),
    ])
    texto.append('%s (%s): %d lineas fantasma' % (p.name, p.origin or '', len(fantasma)))
    for ml in fantasma:
        texto.append('   %s | %s' % (ml.location_id.name, ml.product_id.default_code or ml.product_id.display_name))
    total += len(fantasma)
    if not DIAGNOSTICO and fantasma:
        fantasma.unlink()
texto.append('Total: %d lineas' % total)
mensaje = '\n'.join(texto)
log(mensaje)
if DIAGNOSTICO:
    raise Warning(mensaje + '\n\nEs un diagnostico: no se ha borrado nada. Para borrarlas: DIAGNOSTICO = False.')
# Sin aviso al final: un raise Warning desharia el borrado. El resultado queda en el registro.

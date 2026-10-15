# =============================================================================
# KOROSHI - EMPAQUETAR CAJA CON MATRICULA (ESCRIBE)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# La llama el programa Pedidos Multiples (modo matricula, EFFE) al cerrar una
# caja, por XML-RPC (ir.actions.server.run) con el contexto:
#   active_model = 'stock.picking', active_id / active_ids = la OUT,
#   matricula = 'CJ...', allowed_company_ids = [8]
# Pone las lineas leidas (qty_done > 0) que aun no tienen paquete en un paquete
# nuevo con el nombre de la matricula, con put_in_pack(package_name=...) del
# modulo stock_barcode_optimization. Odoo parte las lineas leidas a medias.
# Si algo no cuadra, raise Warning: no se escribe nada (rollback) y el programa
# muestra el mensaje al operario y deja la caja abierta.
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
PREFIJO = 'CJ'
# Solo para probar a mano desde el boton "Ejecutar" de la accion (sin programa).
# En produccion: False (el albaran y la matricula vienen del contexto).
PRUEBA_MANUAL = False
PICKING_NOMBRE = 'EFFEC/OUT/19385'
MATRICULA_PRUEBA = 'CJ665002800'
# -----------------------------------------------------------------------------

pick = env['stock.picking']
if env.context.get('active_model') == 'stock.picking' and env.context.get('active_id'):
    pick = env['stock.picking'].browse(env.context.get('active_id')).exists()
elif PRUEBA_MANUAL and PICKING_NOMBRE:
    pick = env['stock.picking'].search([('name', '=', PICKING_NOMBRE), ('company_id', '=', COMPANY_ID)], limit=1)
matricula = env.context.get('matricula') or (PRUEBA_MANUAL and MATRICULA_PRUEBA) or ''
matricula = matricula.strip().upper()

errores = []
if not pick:
    errores.append('No se ha recibido el albaran')
else:
    if pick.company_id.id != COMPANY_ID:
        errores.append('El albaran %s no es de la empresa %d' % (pick.name, COMPANY_ID))
    if pick.picking_type_code != 'outgoing':
        errores.append('El albaran %s no es de salida (OUT)' % pick.name)
    if pick.state != 'assigned':
        errores.append('El albaran %s no esta Preparado (estado %s)' % (pick.name, pick.state))

formato_ok = len(matricula) > len(PREFIJO) and matricula[:len(PREFIJO)] == PREFIJO
for ch in matricula[len(PREFIJO):]:
    if not (ch.isdigit() or ('A' <= ch <= 'Z')):
        formato_ok = False
if not formato_ok:
    errores.append('Matricula "%s" no valida (debe ser %s...)' % (matricula, PREFIJO))
elif not env['zebra.label'].search_count([('name', '=', matricula)]):
    errores.append('La matricula %s no existe en Etiquetas Zebra' % matricula)
else:
    existentes = env['stock.quant.package'].search([('name', '=', matricula)])
    if existentes:
        usado_en = existentes.mapped('quant_ids.location_id.complete_name')
        errores.append('La matricula %s ya esta usada (paquete existente%s). Usar otra matricula.'
                       % (matricula, usado_en and (' en ' + ', '.join(usado_en[:3])) or ''))

a_empaquetar = env['stock.move.line']
destinos = {}
if pick:
    for ml in pick.move_line_ids:
        if ml.qty_done > 0 and not ml.result_package_id:
            a_empaquetar |= ml
            destinos[ml.location_dest_id.id] = 1
    if not a_empaquetar:
        errores.append('La caja esta vacia: no hay unidades leidas sin caja en %s' % pick.name)
    if len(destinos) > 1:
        errores.append('Las lineas de %s tienen %d ubicaciones destino distintas' % (pick.name, len(destinos)))

if errores:
    log('KOROSHI EMPAQUETAR CAJA: NO empaquetado %s con %s -> %s'
        % (pick and pick.name or '-', matricula or '-', ' | '.join(errores)))
    raise Warning('No se ha cerrado la caja.\n\n%s' % '\n'.join(errores))

uds = sum(a_empaquetar.mapped('qty_done'))
pick.put_in_pack(package_name=matricula)

# Comprobacion: un unico paquete con ese nombre y con todas las unidades leidas.
paquete = env['stock.quant.package'].search([('name', '=', matricula)])
lineas_paquete = pick.move_line_ids.filtered(lambda ml: ml.result_package_id.name == matricula)
uds_paquete = sum(lineas_paquete.mapped('qty_done'))
pendientes = pick.move_line_ids.filtered(lambda ml: ml.qty_done > 0 and not ml.result_package_id)
if len(paquete) != 1 or uds_paquete != uds or pendientes:
    log('KOROSHI EMPAQUETAR CAJA: comprobacion fallida %s %s (paquetes %d, uds %d de %d, sin caja %d)'
        % (pick.name, matricula, len(paquete), uds_paquete, uds, len(pendientes)))
    raise Warning('No se ha cerrado la caja %s en %s: el resultado no cuadra (paquetes %d, uds %d de %d). '
                  'No se ha guardado nada.' % (matricula, pick.name, len(paquete), uds_paquete, uds))

log('KOROSHI EMPAQUETAR CAJA: %s caja %s con %d uds en %d lineas'
    % (pick.name, matricula, uds_paquete, len(lineas_paquete)))

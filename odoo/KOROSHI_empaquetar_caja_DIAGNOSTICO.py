# =============================================================================
# KOROSHI - EMPAQUETAR CAJA CON MATRICULA - DIAGNOSTICO (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Simula lo que hara la accion real KOROSHI_empaquetar_caja.py sobre un albaran:
#   - comprobaciones del albaran (empresa, tipo, estado) y de la matricula
#     (formato, zebra.label, paquetes que ya tengan ese nombre);
#   - lineas que se empaquetarian (qty_done > 0 y sin paquete) y cuales se
#     partirian;
#   - ubicaciones destino (si hay mas de una, put_in_pack abre un asistente);
#   - codigo de las reglas automaticas de control de matriculas/cajas.
# La matricula sale del contexto ('matricula', como la mandara el programa)
# o, si no hay, de MATRICULA_PRUEBA.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
PREFIJO = 'CJ'
MATRICULA_PRUEBA = 'CJ665002800'
MOSTRAR_CODIGO_REGLAS = True
MAX_LINEAS_MENSAJE = 250
# -----------------------------------------------------------------------------

lineas = []
errores = []
pick = env['stock.picking']
if env.context.get('active_id'):
    pick = env['stock.picking'].browse(env.context.get('active_id'))
elif records:
    pick = records[0]
matricula = (env.context.get('matricula') or MATRICULA_PRUEBA or '').strip().upper()

lineas.append('EMPAQUETAR CAJA KOROSHI - DIAGNOSTICO - NO SE HA MODIFICADO NADA')
lineas.append('Matricula: %s (%s)' % (matricula, env.context.get('matricula') and 'del contexto' or 'MATRICULA_PRUEBA'))

# ---------------- 1. Albaran -------------------------------------------------
lineas.append('')
lineas.append('ALBARAN')
if not pick:
    errores.append('No hay albaran (ejecutar desde un albaran o con active_id)')
else:
    lineas.append('   %s | empresa %s | tipo %s (%s) | estado %s | origen %s'
                  % (pick.name, pick.company_id.id, pick.picking_type_id.display_name, pick.picking_type_code,
                     pick.state, pick.origin or '-'))
    lineas.append('   Ubicacion origen %s | destino %s | agrupacion %s'
                  % (pick.location_id.complete_name, pick.location_dest_id.complete_name, pick.batch_id.name or '-'))
    lineas.append('   Tipo de operacion show_reserved=%s' % pick.picking_type_id.show_reserved)
    if pick.company_id.id != COMPANY_ID:
        errores.append('El albaran no es de la empresa %d' % COMPANY_ID)
    if pick.picking_type_code != 'outgoing':
        errores.append('El albaran no es de salida (OUT)')
    if pick.state != 'assigned':
        errores.append('El albaran no esta Preparado (estado %s)' % pick.state)

# ---------------- 2. Matricula -----------------------------------------------
lineas.append('')
lineas.append('MATRICULA')
formato_ok = len(matricula) > len(PREFIJO) and matricula[:len(PREFIJO)] == PREFIJO
for ch in matricula[len(PREFIJO):]:
    if not (ch.isdigit() or ('A' <= ch <= 'Z')):
        formato_ok = False
lineas.append('   Formato %s...: %s' % (PREFIJO, formato_ok and 'OK' or 'NO VALIDO'))
if not formato_ok:
    errores.append('Formato de matricula no valido')
n_zebra = env['zebra.label'].search_count([('name', '=', matricula)])
lineas.append('   En zebra.label: %s' % (n_zebra and 'existe' or 'NO EXISTE'))
if not n_zebra:
    errores.append('La matricula no existe en zebra.label')
paquetes = env['stock.quant.package'].search([('name', '=', matricula)])
lineas.append('   Paquetes con este nombre: %d' % len(paquetes))
for pk in paquetes:
    cantidad = sum(pk.quant_ids.mapped('quantity'))
    usos = env['stock.move.line'].search([('result_package_id', '=', pk.id)])
    lineas.append('      id %d | ubicacion %s | uds en quants %d | lineas que lo usan %d'
                  % (pk.id, pk.location_id.complete_name or '-', cantidad, len(usos)))
    vistos = {}
    for ml in usos:
        clave = '%s (%s)' % (ml.picking_id.name or '-', ml.state)
        vistos[clave] = vistos.get(clave, 0) + 1
    for k in sorted(vistos.keys()):
        lineas.append('         %s: %d lineas' % (k, vistos[k]))
if paquetes:
    errores.append('Ya existe un paquete con el nombre %s: la accion real lo rechazara' % matricula)

# ---------------- 3. Lineas que se empaquetarian -----------------------------
lineas.append('')
lineas.append('LINEAS (producto | reservado | hecho | paquete | destino | que pasaria)')
a_empaquetar = env['stock.move.line']
destinos = {}
if pick:
    for ml in pick.move_line_ids:
        if ml.result_package_id:
            que = 'ya en paquete'
        elif ml.qty_done > 0:
            a_empaquetar |= ml
            destinos[ml.location_dest_id.complete_name] = 1
            if ml.qty_done < ml.product_uom_qty:
                que = 'SE PARTE: %d al paquete, %d quedan en una linea nueva' % (ml.qty_done, ml.product_uom_qty - ml.qty_done)
            else:
                que = 'al paquete'
        else:
            que = 'no (sin leer)'
        lineas.append('   %s | %d | %d | %s | %s | %s'
                      % (ml.product_id.default_code or ml.product_id.name, ml.product_uom_qty, ml.qty_done,
                         ml.result_package_id.name or '-', ml.location_dest_id.name, que))
lineas.append('   Se empaquetarian %d lineas, %d uds'
              % (len(a_empaquetar), sum(a_empaquetar.mapped('qty_done'))))
if pick and not a_empaquetar:
    errores.append('No hay lineas leidas (qty_done > 0) sin paquete: caja vacia')
if len(destinos) > 1:
    errores.append('Las lineas tienen %d ubicaciones destino: put_in_pack abriria un asistente' % len(destinos))

# ---------------- 4. Reglas automaticas --------------------------------------
lineas.append('')
lineas.append('REGLAS AUTOMATICAS DE CONTROL')
reglas = env['base.automation'].search(['|', ('name', 'ilike', 'matr'), ('name', 'ilike', 'cajas')])
for r in reglas:
    lineas.append('   [%d] %s | modelo %s | disparador %s | activa %s'
                  % (r.id, r.name, r.model_id.model, r.trigger, r.active))
    lineas.append('      Filtro antes: %s' % (r.filter_pre_domain or '-'))
    lineas.append('      Filtro: %s' % (r.filter_domain or '-'))
    if MOSTRAR_CODIGO_REGLAS:
        for linea_codigo in (r.code or '').split('\n'):
            lineas.append('      | %s' % linea_codigo.rstrip())

# ----------------------------- RESULTADO -------------------------------------
lineas.insert(2, '')
if errores:
    lineas.insert(3, 'RESULTADO: LA ACCION REAL NO EMPAQUETARIA (%d errores)' % len(errores))
    for i in range(len(errores)):
        lineas.insert(4 + i, '   - %s' % errores[i])
else:
    lineas.insert(3, 'RESULTADO: OK, la accion real llamaria a put_in_pack(package_name=%s)' % matricula)

texto_completo = '\n'.join(lineas)
log('KOROSHI EMPAQUETAR CAJA DIAGNOSTICO\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

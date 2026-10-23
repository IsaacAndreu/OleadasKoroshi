# =============================================================================
# KOROSHI - ETIQUETAS OUT + MATRICULA POR ZONA (picking por zonas, sin U)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
# Se lanza desde la lista de albaranes: filtrar por la agrupacion (Z-ddmm-D3...),
# seleccionar las OUT > Accion > "KOROSHI Etiquetas zona".
#
# Sustituye al "Picking Sticker": por cada OUT saca una etiqueta por caja prevista
# (por volumen: LITROS_CAJA por caja, minimo 1), cada una con el codigo de la OUT
# (para abrirla en la PDA), su matricula CJ (para cerrar la caja), zona, numero de
# caja de la tienda, delegacion, tienda, pedido y "caja i de n".
#   1. Reserva las matriculas de la secuencia de Etiquetas Zebra (zebra.label, CJ...)
#      con la nota "ETQ ZONA <OUT>" y las deja como impresas. Si la OUT ya tiene sus
#      matriculas (se vuelve a imprimir), las reutiliza: no gasta matriculas nuevas.
#   2. Abre la impresion del informe "KOROSHI Etiqueta zona" (vista
#      koroshi.report_etiqueta_zona), que pinta una etiqueta por matricula.
# Si una OUT necesita mas cajas de las previstas, se usan las CJ preimpresas de siempre.
#
# OUT: las seleccionadas; si no hay seleccion, las de AGRUPACIONES (para probar a mano).
# MODO = 'DIAGNOSTICO': no escribe nada; dice cuantas etiquetas saldrian y que matriculas.
# MODO = 'REAL': reserva las matriculas que falten e imprime.
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
AGRUPACIONES = ['Z-2110-D4']       # solo si no se lanza con OUT seleccionadas
INFORME = 'koroshi.report_etiqueta_zona'
NOTA = 'ETQ ZONA '                 # nota de las matriculas reservadas: 'ETQ ZONA EFFEC/OUT/20215'
LITROS_CAJA = 80.0                 # litros (segun el volumen de Odoo) por caja 60x40x40. Calibrado con el 21/10:
                                   # con 80 ninguna OUT se quedo corta y 2/3 salieron exactas (con 75: 61 de 97)
MAX_CAJAS_OUT = 12                 # tope de etiquetas por OUT
LITROS_TIPO = {'JA': 8.0, 'XC': 12.0, 'ZB': 14.0, 'SU': 4.0, 'TR': 3.7, 'CL': 3.0, 'PT': 2.2, 'PL': 2.1,
               'ML': 1.9, 'VS': 1.8, 'FA': 1.6, 'TP': 1.2, 'BL': 0.8, 'ZC': 0.6}
LITROS_DEFECTO = 3.0
MODO = 'DIAGNOSTICO'               # 'DIAGNOSTICO' (no escribe) o 'REAL'
# -----------------------------------------------------------------------------

if MODO not in ('DIAGNOSTICO', 'REAL'):
    log('KOROSHI ETIQUETAS ZONA - MODO desconocido: %s' % MODO)
    raise Warning("MODO tiene que ser 'DIAGNOSTICO' o 'REAL'")

if env.context.get('active_model') == 'stock.picking' and env.context.get('active_ids'):
    outs = env['stock.picking'].browse(env.context.get('active_ids'))
else:
    outs = env['stock.picking'].search([('batch_id.name', 'in', AGRUPACIONES), ('company_id', '=', COMPANY_ID)])
informe = env['ir.actions.report'].search([('report_name', '=', INFORME)], limit=1)
errores = []
if not outs:
    errores.append('No hay OUT: seleccionalas en la lista o pon AGRUPACIONES')
if not informe:
    errores.append('No existe el informe %s (crearlo antes, ver instrucciones)' % INFORME)
if errores:
    log('KOROSHI ETIQUETAS ZONA - ABORTADO\n' + '\n'.join(errores))
    raise Warning('ETIQUETAS DE ZONA - NO SE HA HECHO NADA\n\n' + '\n'.join(errores))

# ---------------- 1. Cajas previstas por volumen ------------------------------
plan = []          # ((zona, caja tienda, nombre), (zona, caja tienda, out, cajas, litros, uds, ya_reservadas))
saltadas = []
for p in outs:
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing' or p.state in ('done', 'cancel'):
        saltadas.append('%s: %s' % (p.name, p.state))
        continue
    litros = 0.0
    uds = 0.0
    for ml in p.move_line_ids:
        q = ml.product_uom_qty
        if q <= 0:
            continue
        v = (ml.product_id.volume or 0.0) * 1000.0
        if v <= 0:
            codigo = ml.product_id.default_code or ''
            v = LITROS_TIPO.get(codigo[4:6], LITROS_DEFECTO)
        litros += v * q
        uds += q
    cajas = int(litros / LITROS_CAJA)
    if cajas * LITROS_CAJA < litros:
        cajas += 1
    cajas = max(1, min(cajas, MAX_CAJAS_OUT))
    nota = p.note or ''
    pos = nota.find('CAJA ')
    caja_tienda = pos >= 0 and nota[pos + 5:pos + 7] or ''
    zona = p.batch_id and p.batch_id.name.split('-')[-1] or ''
    ya = env['zebra.label'].search([('note', '=', NOTA + p.name)])
    plan.append(((zona, caja_tienda, p.name), (zona, caja_tienda, p, cajas, litros, uds, ya)))
plan = sorted(plan)

# ---------------- 2. Matriculas -----------------------------------------------
secuencia = env['ir.sequence'].search([('code', '=', 'zebra.label.code')], limit=1)
siguiente = secuencia and secuencia.number_next_actual or 0
nuevas_total = 0
texto = ['KOROSHI ETIQUETAS ZONA - ' + (MODO == 'REAL' and 'HECHO' or 'DIAGNOSTICO (NO SE HA ESCRITO NADA)'),
         'OUT: %d' % len(plan), '', 'Zona | caja | OUT | tienda | pedido | uds | litros | etiquetas | matriculas']
imprimir = env['stock.picking']
for k, t in plan:
    zona, caja_tienda, p, cajas, litros, uds, ya = t
    faltan = max(0, cajas - len(ya))
    cjs = ya.sorted('sequence_number').mapped('name')
    if faltan and MODO == 'REAL':
        nuevas = env['zebra.label'].create_next_labels(quantity=faltan, note=NOTA + p.name)
        nuevas.write({'state': 'printed', 'print_date': datetime.datetime.now()})
        cjs += nuevas.sorted('sequence_number').mapped('name')
        p.message_post(body='Etiquetas de zona %s: %s' % (zona, ', '.join(cjs)))
    elif faltan:
        i = 0
        while i < faltan:
            cjs.append('CJ%09d*' % (siguiente + nuevas_total + i))
            i += 1
    nuevas_total += faltan
    imprimir |= p
    nombre = p.partner_id.name or ''
    texto.append('   %s | %s | %s | %s | %s | %d | %d | %d | %s' % (
        zona, caja_tienda, p.name, nombre[:1] == 'K' and nombre or nombre.split(', ')[-1], p.origin or '', uds, litros,
        max(cajas, len(ya)), ', '.join(cjs)))
texto.append('')
texto.append('Matriculas nuevas: %d%s' % (nuevas_total, MODO == 'DIAGNOSTICO' and ' (las marcadas con * se crearian; no se ha gastado ninguna)' or ''))
if saltadas:
    texto.append('No se imprimen (hechas o canceladas): ' + ', '.join(saltadas))
mensaje = '\n'.join(texto)
log(mensaje)
if MODO == 'DIAGNOSTICO':
    raise Warning(mensaje + "\n\nEs un diagnostico: no se ha creado ninguna matricula. Para hacerlo de verdad: MODO = 'REAL'.")
# imprimir ya va en el orden de plan (zona, caja de tienda, OUT)
action = informe.report_action(imprimir)

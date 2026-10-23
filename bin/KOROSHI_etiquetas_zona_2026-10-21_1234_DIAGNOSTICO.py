# =============================================================================
# KOROSHI - ETIQUETAS OUT + MATRICULA POR ZONA (picking por zonas, sin U)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Para no imprimir por un lado la etiqueta de la OUT y por otro las matriculas CJ:
# por cada OUT de la agrupacion de zona (Z-ddmm-D1...) saca tantas etiquetas como
# cajas va a necesitar (por volumen: LITROS_CAJA por caja, minimo 1), cada una con
#   - el codigo de la OUT (para abrirla en la PDA),
#   - su matricula CJ (para cerrar la caja en la PDA),
#   - zona, numero de caja de la tienda (01..), tienda, pedido y "caja i de n".
# Las matriculas salen de la secuencia de Etiquetas Zebra (CJ...), igual que las
# que genera el programa de la U: se crean los zebra.label y quedan como impresas.
# Si una OUT necesita mas cajas de las previstas, se usan las CJ preimpresas de siempre.
#
# Agrupacion: la del contexto 'agrupacion' (cuando la llame el programa), o AGRUPACIONES.
# MODO = 'DIAGNOSTICO': no escribe nada; dice cuantas etiquetas saldrian y con que
#        matriculas (las siguientes de la secuencia, sin gastarlas).
# MODO = 'REAL': crea las matriculas y devuelve la lista de etiquetas para imprimir:
#        action = {'type': 'ir.actions.act_window_close', 'etiquetas': [...]}
#        cada etiqueta: 'OUT|CJ|zona|caja tienda|tienda|pedido|i|n'
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
AGRUPACIONES = ['Z-2110-D4']       # para probar a mano; el programa la manda en el contexto
LITROS_CAJA = 75.0                 # litros utiles de una caja 60x40x40
MAX_CAJAS_OUT = 12                 # tope de etiquetas por OUT
SOLO_PENDIENTES = True             # True: solo OUT Preparadas sin nada leido (no reimprime las empezadas)
LITROS_TIPO = {'JA': 8.0, 'XC': 12.0, 'ZB': 14.0, 'SU': 4.0, 'TR': 3.7, 'CL': 3.0, 'PT': 2.2, 'PL': 2.1,
               'ML': 1.9, 'VS': 1.8, 'FA': 1.6, 'TP': 1.2, 'BL': 0.8, 'ZC': 0.6}
LITROS_DEFECTO = 3.0
MODO = 'DIAGNOSTICO'               # 'DIAGNOSTICO' (no escribe) o 'REAL'
# -----------------------------------------------------------------------------

if MODO not in ('DIAGNOSTICO', 'REAL'):
    log('KOROSHI ETIQUETAS ZONA - MODO desconocido: %s' % MODO)
    raise Warning("MODO tiene que ser 'DIAGNOSTICO' o 'REAL'")
nombres = env.context.get('agrupacion') and [env.context.get('agrupacion')] or AGRUPACIONES
agrupaciones = env['stock.picking.batch'].search([('name', 'in', nombres), ('company_id', '=', COMPANY_ID)])
errores = []
if not agrupaciones:
    errores.append('No existe la agrupacion %s' % ', '.join(nombres))
if errores:
    log('KOROSHI ETIQUETAS ZONA - ABORTADO\n' + '\n'.join(errores))
    raise Warning('ETIQUETAS DE ZONA - NO SE HA HECHO NADA\n\n' + '\n'.join(errores))

# ---------------- 1. OUT y cajas previstas por volumen -------------------------
plan = []          # (agrupacion, caja tienda, out, cajas, litros, uds)
saltadas = []
for b in agrupaciones:
    zona = b.name.split('-')[-1]
    for p in b.picking_ids.sorted('name'):
        leido = 0.0
        for ml in p.move_line_ids:
            leido += ml.qty_done
        if p.picking_type_code != 'outgoing' or p.state in ('done', 'cancel'):
            saltadas.append('%s: %s' % (p.name, p.state))
            continue
        if SOLO_PENDIENTES and (p.state != 'assigned' or leido > 0):
            saltadas.append('%s: ya empezada o no Preparada (%s, %d leidas)' % (p.name, p.state, leido))
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
        caja_tienda = ''
        nota = p.note or ''
        pos = nota.find('CAJA ')
        if pos >= 0:
            caja_tienda = nota[pos + 5:pos + 7]
        plan.append((zona, caja_tienda, p, cajas, litros, uds))

# orden: zona y numero de caja de la tienda (01, 02...), para repartirlas en orden
ordenadas = []
for t in plan:
    ordenadas.append(((t[0], t[1], t[2].name), t))
ordenadas = sorted(ordenadas)
total_etiquetas = 0
for o in ordenadas:
    total_etiquetas += o[1][3]

# ---------------- 2. Matriculas ------------------------------------------------
secuencia = env['ir.sequence'].search([('code', '=', 'zebra.label.code')], limit=1)
etiquetas = []
texto = ['KOROSHI ETIQUETAS ZONA - ' + (MODO == 'REAL' and 'HECHO' or 'DIAGNOSTICO (NO SE HA ESCRITO NADA)'),
         'Agrupaciones: %s | OUT: %d | etiquetas: %d' % (', '.join(agrupaciones.mapped('name')), len(ordenadas), total_etiquetas)]
if MODO == 'DIAGNOSTICO':
    siguiente = secuencia and secuencia.number_next_actual or 0
    texto.append('Matriculas que se usarian: CJ%09d a CJ%09d (siguientes de la secuencia, sin gastarlas)' % (siguiente, siguiente + total_etiquetas - 1))
texto.append('')
texto.append('Zona | caja | OUT | tienda | pedido | uds | litros | etiquetas')
for o in ordenadas:
    zona, caja_tienda, p, cajas, litros, uds = o[1]
    tienda = p.partner_id and p.partner_id.name or ''
    cjs = []
    if MODO == 'REAL':
        nuevas = env['zebra.label'].create_next_labels(quantity=cajas, note='Zona %s %s' % (zona, p.name))
        nuevas.write({'state': 'printed', 'print_date': datetime.datetime.now()})
        i = 0
        for cj in nuevas.sorted('sequence_number'):
            i += 1
            cjs.append(cj.name)
            etiquetas.append('%s|%s|%s|%s|%s|%s|%d|%d' % (p.name, cj.name, zona, caja_tienda, tienda, p.origin or '', i, cajas))
        p.message_post(body='Etiquetas de zona %s: %s' % (zona, ', '.join(cjs)))
    texto.append('   %s | %s | %s | %s | %s | %d | %d | %d%s' % (
        zona, caja_tienda, p.name, tienda, p.origin or '', uds, litros, cajas, cjs and (' (' + ', '.join(cjs) + ')') or ''))
if saltadas:
    texto.append('')
    texto.append('No se imprimen (%d): ya hechas, empezadas o no Preparadas' % len(saltadas))
    n = 0
    for s in saltadas:
        n += 1
        if n > 15:
            texto.append('   ...')
            break
        texto.append('   ' + s)
mensaje = '\n'.join(texto)
log(mensaje)
if MODO == 'DIAGNOSTICO':
    raise Warning(mensaje + "\n\nEs un diagnostico: no se ha creado ninguna matricula. Para hacerlo de verdad: MODO = 'REAL'.")
action = {'type': 'ir.actions.act_window_close', 'etiquetas': etiquetas}

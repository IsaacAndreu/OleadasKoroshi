# =============================================================================
# KOROSHI - SIMULACION OLEADAS v5: 10 TIENDAS POR OLEADA, 1 OLEADA POR U,
# PICKING POR ZONAS CON BOLSAS DE COLOR (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Esquema que se simula (no se crea nada):
#   1. OUT de tiendas (PED. TIENDAS) de las ultimas HORAS_ATRAS horas.
#   2. Oleadas de TIENDAS_POR_OLEADA tiendas (las 10 posiciones de una U),
#      equilibradas por unidades. Cada RONDA tiene una oleada por U (U1..U5).
#   3. Zonas por lineales (una por PDA), fijas (ZONAS_FIJAS) o equilibradas.
#   4. Cada PDA hace su zona ronda a ronda:
#        RUTA = 'conjunta'   -> una sola pasada por ronda con una bolsa de color
#                               por U (necesita que la PDA diga a que U va cada pieza)
#        RUTA = 'secuencial' -> los INT de su zona uno detras de otro (U1, U2...)
#   5. Una oleada esta lista cuando todas las zonas han terminado su parte; la
#      U la lee cuando esta lista y la U esta libre.
# Resultado: zonas, oleadas (con INT por zona), hora de cada PDA y de cada U.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
HORAS_ATRAS = 16
NUM_U = 5
TIENDAS_POR_OLEADA = 10
NUM_PDA = 5                      # una zona por PDA
# Zonas fijas por lineales, p.ej. [[1, 65], [66, 85], [86, 97], [98, 107], [108, 136]].
# Vacio = zonas equilibradas con los datos de esta simulacion.
ZONAS_FIJAS = []
RUTA = 'secuencial'              # 'conjunta' o 'secuencial'
HORA_INICIO_PICKING = '06:00'
HORA_INICIO_U = '06:00'
HORA_LIMITE = '13:00'
T_PARADA_SEG = 20
T_UD_SEG = 4
UDS_HORA_U = 425
LINEAL_MAX = 136
# Solo para simular (no se tocan):
INCLUIR_YA_EN_OLEADA = True
INCLUIR_RESERVA_PARCIAL = True
INCLUIR_HECHAS = False
MAX_LINEAS_MENSAJE = 250
# -----------------------------------------------------------------------------

Picking = env['stock.picking']
ahora_utc = datetime.datetime.utcnow()
desde_txt = (ahora_utc - datetime.timedelta(hours=HORAS_ATRAS)).strftime('%Y-%m-%d %H:%M:%S')
hhmm = lambda m: '%02d:%02d' % (int(m // 60) % 24, int(m % 60))
minutos = lambda h: float(int(h.split(':')[0]) * 60 + int(h.split(':')[1]))
seg_carga = lambda uds, paradas: uds * T_UD_SEG + paradas * T_PARADA_SEG
inicio_pick = minutos(HORA_INICIO_PICKING)
inicio_u = minutos(HORA_INICIO_U)
limite = minutos(HORA_LIMITE)

lineas = []
lineas.append('SIMULACION OLEADAS KOROSHI v5 - NO SE HA CREADO NADA - %s UTC' % ahora_utc.strftime('%d/%m/%Y %H:%M'))
lineas.append('Parametros: %d tiendas por oleada, %d U, %d PDA, ruta %s, zonas %s'
              % (TIENDAS_POR_OLEADA, NUM_U, NUM_PDA, RUTA, ZONAS_FIJAS and 'fijas' or 'equilibradas'))
lineas.append('Horas: picking desde %s, U desde %s, limite %s | %d s/parada, %d s/ud, %d uds/h por U (sin pausas)'
              % (HORA_INICIO_PICKING, HORA_INICIO_U, HORA_LIMITE, T_PARADA_SEG, T_UD_SEG, UDS_HORA_U))

# ---------------- 1. OUT de tiendas ------------------------------------------
estados = ['confirmed', 'waiting', 'assigned']
if INCLUIR_HECHAS:
    estados.append('done')
candidatos = Picking.search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('state', 'in', estados),
    ('create_date', '>=', desde_txt),
], order='name asc')
tiendas = {}
motivos = {}
for p in candidatos:
    tipo = p.sale_id and p.sale_id.s_order_type_id and p.sale_id.s_order_type_id.name or ''
    if tipo != TIPO_PEDIDO:
        continue
    if p.batch_id and not INCLUIR_YA_EN_OLEADA:
        motivos['ya en una oleada'] = motivos.get('ya en una oleada', 0) + 1
        continue
    uds = 0.0
    for ml in p.move_line_ids:
        if p.state == 'done':
            uds += ml.qty_done
        else:
            uds += ml.product_uom_qty
    if uds <= 0:
        motivos['sin nada reservado'] = motivos.get('sin nada reservado', 0) + 1
        continue
    if p.state not in ('assigned', 'done') and not INCLUIR_RESERVA_PARCIAL:
        motivos['reserva parcial'] = motivos.get('reserva parcial', 0) + 1
        continue
    clave = p.partner_id.id
    if clave not in tiendas:
        tiendas[clave] = {'nombre': p.partner_id.name or '-', 'outs': [], 'uds': 0.0}
    tiendas[clave]['outs'].append(p)
    tiendas[clave]['uds'] += uds

# ---------------- 2. Oleadas de N tiendas, rondas de NUM_U oleadas -----------
total_uds = 0.0
for t in tiendas.values():
    total_uds += t['uds']
# Como maximo TIENDAS_POR_OLEADA tiendas por oleada, y rondas completas (una oleada
# por U) para que ninguna U se quede sin trabajo: 34 tiendas -> 5 oleadas de ~7.
num_oleadas = int(len(tiendas) / TIENDAS_POR_OLEADA)
if num_oleadas * TIENDAS_POR_OLEADA < len(tiendas):
    num_oleadas += 1
if num_oleadas % NUM_U:
    num_oleadas += NUM_U - (num_oleadas % NUM_U)
if num_oleadas > len(tiendas):
    num_oleadas = max(1, len(tiendas))
oleadas = []
for i in range(num_oleadas):
    oleadas.append({'num': i + 1, 'ronda': (i // NUM_U) + 1, 'u': (i % NUM_U) + 1,
                    'tiendas': [], 'uds': 0.0, 'outs': 0})
# Tienda mas grande a la oleada con menos unidades que aun tenga posiciones libres
for t in sorted(tiendas.values(), key=lambda x: (-x['uds'], x['nombre'])):
    libres = sorted(oleadas, key=lambda x: (len(x['tiendas']) >= TIENDAS_POR_OLEADA, x['uds'], x['num']))
    o = libres[0]
    o['tiendas'].append(t)
    o['uds'] += t['uds']
    o['outs'] += len(t['outs'])
num_rondas = 0
for o in oleadas:
    if o['ronda'] > num_rondas:
        num_rondas = o['ronda']

# ---------------- 3. Lineas por pasillo --------------------------------------
lineas_sin_l = 0
sin_lineal = {}   # ubicacion -> [lineas, uds]
detalle = []   # (oleada, pasillo, ubicacion_id, uds, ronda)
for o in oleadas:
    for t in o['tiendas']:
        for p in t['outs']:
            for ml in p.move_line_ids:
                if p.state == 'done':
                    qty = ml.qty_done
                else:
                    qty = ml.product_uom_qty
                if qty <= 0:
                    continue
                lineal = 0
                segmentos = (ml.location_id.complete_name or '').split('/')
                for idx in range(len(segmentos) - 1, -1, -1):
                    texto = segmentos[idx].strip()
                    if ' - ' in texto:
                        texto = texto.split(' - ', 1)[1]
                    if len(texto) > 1 and texto[0] == 'L' and texto[1].isdigit():
                        num = ''
                        for ch in texto[1:]:
                            if ch.isdigit():
                                num += ch
                            else:
                                break
                        lineal = int(num)
                        break
                if not lineal:
                    lineas_sin_l += 1
                    nombre_ubic = ml.location_id.complete_name or '-'
                    if nombre_ubic not in sin_lineal:
                        sin_lineal[nombre_ubic] = [0, 0.0]
                    sin_lineal[nombre_ubic][0] += 1
                    sin_lineal[nombre_ubic][1] += qty
                    continue
                detalle.append((o['num'], lineal // 2, ml.location_id.id, qty, o['ronda']))

# ---------------- 4. Zonas -----------------------------------------------------
# Peso de cada pasillo con las paradas de la ruta elegida
uds_pasillo = {}
paradas_pasillo = {}
for item in detalle:
    k = item[1]
    uds_pasillo[k] = uds_pasillo.get(k, 0.0) + item[3]
    if k not in paradas_pasillo:
        paradas_pasillo[k] = {}
    if RUTA == 'secuencial':
        paradas_pasillo[k][(item[0], item[2])] = 1
    else:
        paradas_pasillo[k][(item[4], item[2])] = 1
zona_de_pasillo = {}
rangos = []
if ZONAS_FIJAS:
    z = 0
    for rango in ZONAS_FIJAS:
        z += 1
        rangos.append((z, rango[0], rango[1]))
        for lin in range(rango[0], rango[1] + 1):
            zona_de_pasillo[lin // 2] = z
else:
    total_p = 0.0
    for k in uds_pasillo.keys():
        total_p += seg_carga(uds_pasillo[k], len(paradas_pasillo[k]))
    objetivo = NUM_PDA and total_p / NUM_PDA or total_p
    z = 1
    acumulado = 0.0
    inicio = None
    ordenados = sorted(uds_pasillo.keys())
    for k in ordenados:
        if inicio is None:
            inicio = k
        zona_de_pasillo[k] = z
        acumulado += seg_carga(uds_pasillo[k], len(paradas_pasillo[k]))
        if acumulado >= objetivo * z and z < NUM_PDA and k != ordenados[-1]:
            rangos.append((z, max(1, inicio * 2), min(LINEAL_MAX, k * 2 + 1)))
            z += 1
            inicio = None
    if inicio is not None:
        rangos.append((z, max(1, inicio * 2), min(LINEAL_MAX, ordenados[-1] * 2 + 1)))

# ---------------- 5. Cargas: INT (oleada x zona) y pasadas de cada PDA --------
matriz = {}      # (oleada, zona) -> {'uds', 'ubic'}   = un INT
pasada = {}      # (ronda, zona)  -> {'uds', 'ubic'}   = ruta conjunta de la ronda
fuera_zona = 0.0
for item in detalle:
    zona = zona_de_pasillo.get(item[1], 0)
    if not zona:
        fuera_zona += item[3]
        continue
    c = (item[0], zona)
    if c not in matriz:
        matriz[c] = {'uds': 0.0, 'ubic': {}}
    matriz[c]['uds'] += item[3]
    matriz[c]['ubic'][item[2]] = 1
    c = (item[4], zona)
    if c not in pasada:
        pasada[c] = {'uds': 0.0, 'ubic': {}}
    pasada[c]['uds'] += item[3]
    pasada[c]['ubic'][item[2]] = 1

# ---------------- 6. Horario --------------------------------------------------
fin_pda = {}
seg_pda = {}
for r in rangos:
    fin_pda[r[0]] = inicio_pick
    seg_pda[r[0]] = 0.0
lista = {}
for nr in range(1, num_rondas + 1):
    de_la_ronda = []
    for o in oleadas:
        if o['ronda'] == nr:
            de_la_ronda.append(o)
    if RUTA == 'secuencial':
        for o in sorted(de_la_ronda, key=lambda x: x['num']):
            mx = inicio_pick
            for r in rangos:
                m = matriz.get((o['num'], r[0]))
                if m:
                    s = seg_carga(m['uds'], len(m['ubic']))
                    fin_pda[r[0]] += s / 60.0
                    seg_pda[r[0]] += s
                    if fin_pda[r[0]] > mx:
                        mx = fin_pda[r[0]]
            lista[o['num']] = mx
    else:
        mx = inicio_pick
        for r in rangos:
            c = pasada.get((nr, r[0]))
            if c:
                s = seg_carga(c['uds'], len(c['ubic']))
                fin_pda[r[0]] += s / 60.0
                seg_pda[r[0]] += s
                if fin_pda[r[0]] > mx:
                    mx = fin_pda[r[0]]
        for o in de_la_ronda:
            lista[o['num']] = mx
libre_u = {}
uds_u = {}
for i in range(NUM_U):
    libre_u[i + 1] = inicio_u
    uds_u[i + 1] = 0.0
espera_total = 0.0
for o in sorted(oleadas, key=lambda x: x['num']):
    o['lista'] = lista.get(o['num'], inicio_pick)
    o['ini'] = max(o['lista'], libre_u[o['u']])
    o['espera'] = o['ini'] - libre_u[o['u']]
    o['fin'] = o['ini'] + o['uds'] * 60.0 / UDS_HORA_U
    libre_u[o['u']] = o['fin']
    uds_u[o['u']] += o['uds']
    espera_total += o['espera']

# ----------------------------- MENSAJE ---------------------------------------
total_outs = 0
for o in oleadas:
    total_outs += o['outs']
lineas.append('')
lineas.append('Tiendas: %d | OUT: %d | uds: %d | oleadas: %d | rondas: %d | lineas sin lineal: %d'
              % (len(tiendas), total_outs, total_uds, num_oleadas, num_rondas, lineas_sin_l))
for k in sorted(motivos.keys()):
    lineas.append('   Descartadas, %s: %d OUT' % (k, motivos[k]))
if sin_lineal:
    lineas.append('   Ubicaciones sin lineal (no cuentan en ninguna zona): %d. Las %d con mas uds:'
                  % (len(sin_lineal), min(15, len(sin_lineal))))
    for nombre_ubic in sorted(sin_lineal.keys(), key=lambda x: -sin_lineal[x][1])[:15]:
        lineas.append('      %s | %d lineas | %d uds' % (nombre_ubic, sin_lineal[nombre_ubic][0], sin_lineal[nombre_ubic][1]))

lineas.append('')
lineas.append('ZONAS / PDA: lineales | uds | paradas | horas | termina')
for r in rangos:
    uds_z = 0.0
    paradas_z = 0
    for nr in range(1, num_rondas + 1):
        c = pasada.get((nr, r[0]))
        if c:
            uds_z += c['uds']
            if RUTA != 'secuencial':
                paradas_z += len(c['ubic'])
    if RUTA == 'secuencial':
        for o in oleadas:
            m = matriz.get((o['num'], r[0]))
            if m:
                paradas_z += len(m['ubic'])
    lineas.append('   PDA %d: L%02d-L%02d | %d uds | %d paradas | %.1f h | %s'
                  % (r[0], r[1], r[2], uds_z, paradas_z, seg_pda[r[0]] / 3600.0, hhmm(fin_pda[r[0]])))
if fuera_zona:
    lineas.append('   Fuera de las zonas fijas: %d uds' % fuera_zona)

lineas.append('')
lineas.append('OLEADAS (cada celda = 1 INT hacia SORTER/U<n>: uds/paradas)')
cabecera = '   %-6s %-3s %-3s %5s %6s |' % ('Oleada', 'R', 'U', 'Tiend', 'Uds')
for r in rangos:
    cabecera += ' %-9s' % ('PDA%d' % r[0])
lineas.append(cabecera)
num_int = 0
for o in oleadas:
    fila = '   %-6s %-3s %-3s %5d %6d |' % ('O%d' % o['num'], 'R%d' % o['ronda'], 'U%d' % o['u'], len(o['tiendas']), o['uds'])
    for r in rangos:
        m = matriz.get((o['num'], r[0]))
        if m:
            num_int += 1
        fila += ' %-9s' % (m and ('%d/%d' % (m['uds'], len(m['ubic']))) or '-')
    lineas.append(fila)
lineas.append('   %d INT en total' % num_int)

lineas.append('')
lineas.append('HORARIO DE LAS U (picking desde %s, lectura desde %s)' % (HORA_INICIO_PICKING, HORA_INICIO_U))
lineas.append('   %-6s %-3s %6s | %-5s %-6s %-5s %s' % ('Oleada', 'U', 'Uds', 'Lista', 'Inicio', 'Fin', 'Espera U'))
fin_ultima = inicio_u
for o in oleadas:
    lineas.append('   %-6s %-3s %6d | %-5s %-6s %-5s %d min'
                  % ('O%d' % o['num'], 'U%d' % o['u'], o['uds'], hhmm(o['lista']), hhmm(o['ini']), hhmm(o['fin']), o['espera']))
    if o['fin'] > fin_ultima:
        fin_ultima = o['fin']
for i in range(NUM_U):
    lineas.append('   U%d: %d uds, termina a las %s' % (i + 1, uds_u[i + 1], hhmm(libre_u[i + 1])))
total_pick = 0.0
for k in seg_pda.keys():
    total_pick += seg_pda[k]
lineas.append('   Picking: %.1f h de PDA | Lectura: %.1f h de U | Espera de las U: %d min'
              % (total_pick / 3600.0, total_uds / UDS_HORA_U, espera_total))
lineas.append('   Ultima U termina a las %s%s' % (hhmm(fin_ultima), fin_ultima > limite and (' - PASA DEL LIMITE %s' % HORA_LIMITE) or ''))

lineas.append('')
lineas.append('TIENDAS POR OLEADA')
for o in oleadas:
    nombres = []
    for t in o['tiendas']:
        nombres.append('%s (%d)' % (t['nombre'], t['uds']))
    lineas.append('   O%d (R%d, U%d): %s' % (o['num'], o['ronda'], o['u'], ', '.join(nombres) or '-'))

texto_completo = '\n'.join(lineas)
log('KOROSHI SIMULACION OLEADAS v5\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

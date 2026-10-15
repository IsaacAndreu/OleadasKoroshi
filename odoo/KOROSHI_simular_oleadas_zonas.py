# =============================================================================
# KOROSHI - SIMULACION OLEADAS + PICKING POR ZONAS v4 (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Simula lo que haria el cron de la noche, sin crear nada:
#   1. OUT de tiendas (tipo de pedido 'PED. TIENDAS') de las ultimas HORAS_ATRAS
#      horas. Opcional: las que ya estan en una oleada, las de reserva parcial y
#      las ya hechas (se cuentan con qty_done).
#   2. Reparte las tiendas en oleadas equilibradas por unidades. Todas las OUT
#      de una tienda van a la misma oleada. Con MAX_UDS_OLEADA = 0 hay una
#      oleada por U; si no, oleadas de ~MAX_UDS_OLEADA uds.
#   3. Agrupa las oleadas en RONDAS de OLEADAS_POR_RONDA. En cada ronda cada
#      PDA pica a la vez todas las oleadas de la ronda en su zona (un carro por
#      oleada, una sola ruta). La ronda esta lista cuando todas las zonas la
#      han terminado.
#   4. Asigna cada linea a un pasillo segun el lineal (Lnn) de su ubicacion.
#      Un pasillo da servicio a L(2k) y L(2k+1).
#   5. Parte los pasillos en NUM_ZONAS zonas (una por PDA): seguidas y con
#      coste parecido (paradas y uds) esta noche, o fijas si se indican.
#   6. Cada oleada va a la U que antes queda libre. Muestra INT, cargas,
#      tiempos de cada PDA y horario estimado de cada U.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
HORAS_ATRAS = 16
NUM_U = 5
NUM_ZONAS = 5
# 0 = una oleada por U. >0 = oleadas de como maximo ~N uds (una tienda mayor va sola).
MAX_UDS_OLEADA = 150
# Oleadas que cada PDA pica a la vez (carros por PDA). 0 = NUM_U.
# 1 = oleada a oleada (como la v3 'oleada a oleada'). 99 = todo junto (v3 'conjunta').
OLEADAS_POR_RONDA = 0
# Zonas fijas por lineales, p.ej. [[1, 69], [70, 87], [88, 99], [100, 109], [110, 136]].
# Vacio = zonas equilibradas esta noche. Los cortes deben caer entre pasillos
# (acabar en lineal impar), para que un pasillo no quede partido entre dos PDA.
ZONAS_FIJAS = []
# 'coste' = equilibrar por paradas y uds (T_PARADA_SEG, T_UD_SEG). 'uds' = solo uds.
EQUILIBRAR_ZONAS_POR = 'coste'
T_PARADA_SEG = 20
T_UD_SEG = 4
UDS_HORA_U = 425
HORA_INICIO = '06:00'
HORA_LIMITE = '13:00'
LINEAL_MAX = 136
# Solo para simular (no se tocan):
INCLUIR_YA_EN_OLEADA = True
INCLUIR_RESERVA_PARCIAL = True
INCLUIR_HECHAS = False
MAX_DESCARTADAS_LISTA = 30
MAX_LINEAS_MENSAJE = 250
# -----------------------------------------------------------------------------

Picking = env['stock.picking']
ahora_utc = datetime.datetime.utcnow()
desde_txt = (ahora_utc - datetime.timedelta(hours=HORAS_ATRAS)).strftime('%Y-%m-%d %H:%M:%S')
hhmm = lambda m: '%02d:%02d' % (int(m // 60) % 24, int(m % 60))
inicio_min = float(int(HORA_INICIO.split(':')[0]) * 60 + int(HORA_INICIO.split(':')[1]))
limite_min = float(int(HORA_LIMITE.split(':')[0]) * 60 + int(HORA_LIMITE.split(':')[1]))
seg_carga = lambda uds, paradas: uds * T_UD_SEG + paradas * T_PARADA_SEG
por_ronda = OLEADAS_POR_RONDA or NUM_U

lineas = []
lineas.append('SIMULACION OLEADAS + ZONAS KOROSHI v4 - NO SE HA CREADO NADA - %s UTC' % ahora_utc.strftime('%d/%m/%Y %H:%M'))
lineas.append('Parametros: HORAS_ATRAS=%d, NUM_U=%d, NUM_ZONAS=%d, MAX_UDS_OLEADA=%s, OLEADAS_POR_RONDA=%d, ZONAS=%s'
              % (HORAS_ATRAS, NUM_U, NUM_ZONAS, MAX_UDS_OLEADA or 'una por U', por_ronda,
                 ZONAS_FIJAS and 'fijas' or ('equilibradas por %s' % EQUILIBRAR_ZONAS_POR)))
lineas.append('Tiempos: %d s/parada, %d s/ud, %d uds/h por U, inicio %s, limite %s (sin pausas)'
              % (T_PARADA_SEG, T_UD_SEG, UDS_HORA_U, HORA_INICIO, HORA_LIMITE))

# ---------------- Requisitos del circuito SORTER -----------------------------
lineas.append('')
lineas.append('REQUISITOS')
sorter = env['stock.location'].search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)
stock_loc = env['stock.location'].search([('barcode', '=', 'EFFEC-STOCK'), ('company_id', '=', COMPANY_ID)], limit=1)
tipo_int = env['stock.picking.type'].search([('barcode', '=', 'EFFEC-INTERNAL'), ('company_id', '=', COMPANY_ID)], limit=1)
lineas.append('   Ubicacion SORTER: %s' % (sorter.complete_name or 'NO EXISTE'))
lineas.append('   Ubicacion EFFEC-STOCK: %s' % (stock_loc.complete_name or 'NO EXISTE'))
lineas.append('   Tipo de operacion EFFEC-INTERNAL: %s' % (tipo_int.display_name or 'NO EXISTE'))
for i in range(NUM_U):
    nombre_u = 'U%d' % (i + 1)
    sub = sorter and env['stock.location'].search([('location_id', '=', sorter.id), ('name', '=', nombre_u)], limit=1)
    lineas.append('   Sububicacion %s/%s: %s' % (sorter.complete_name or 'SORTER', nombre_u, sub and 'existe' or 'habria que crearla'))

# ---------------- 1. OUT candidatas ------------------------------------------
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
descartadas = 0
motivos = {}
oleadas_existentes = {}
sin_reserva = []
for p in candidatos:
    tipo = p.sale_id and p.sale_id.s_order_type_id and p.sale_id.s_order_type_id.name or ''
    if tipo != TIPO_PEDIDO:
        descartadas += 1
        clave_m = 'otro tipo de pedido (%s)' % (tipo or 'sin tipo')
        motivos[clave_m] = motivos.get(clave_m, 0) + 1
        continue
    if p.batch_id:
        oleadas_existentes[p.batch_id.name] = oleadas_existentes.get(p.batch_id.name, 0) + 1
        if not INCLUIR_YA_EN_OLEADA:
            descartadas += 1
            motivos['ya en una oleada'] = motivos.get('ya en una oleada', 0) + 1
            continue
    uds = 0.0
    for ml in p.move_line_ids:
        if p.state == 'done':
            uds += ml.qty_done
        else:
            uds += ml.product_uom_qty
    if uds <= 0:
        descartadas += 1
        clave_m = 'sin nada reservado (%s)' % p.state
        motivos[clave_m] = motivos.get(clave_m, 0) + 1
        sin_reserva.append('%s - %s (%s)' % (p.name, p.partner_id.name or '-', p.state))
        continue
    if p.state == 'done':
        motivos['incluida ya hecha'] = motivos.get('incluida ya hecha', 0) + 1
    elif p.state != 'assigned':
        if not INCLUIR_RESERVA_PARCIAL:
            descartadas += 1
            motivos['reserva parcial'] = motivos.get('reserva parcial', 0) + 1
            continue
        motivos['incluida con reserva parcial'] = motivos.get('incluida con reserva parcial', 0) + 1
    clave = p.partner_id.id
    if clave not in tiendas:
        tiendas[clave] = {'nombre': p.partner_id.name or '-', 'outs': [], 'uds': 0.0}
    tiendas[clave]['outs'].append(p)
    tiendas[clave]['uds'] += uds

# ---------------- 2. Oleadas equilibradas y rondas ---------------------------
total_uds = 0.0
for t in tiendas.values():
    total_uds += t['uds']
num_oleadas = NUM_U
if MAX_UDS_OLEADA > 0:
    n = int(total_uds / MAX_UDS_OLEADA)
    if n * MAX_UDS_OLEADA < total_uds:
        n += 1
    if n > num_oleadas:
        num_oleadas = n
if num_oleadas > len(tiendas):
    num_oleadas = max(1, len(tiendas))
oleadas = []
for i in range(num_oleadas):
    oleadas.append({'num': i + 1, 'ronda': (i // por_ronda) + 1, 'u': 0, 'tiendas': [], 'uds': 0.0, 'outs': 0})
for t in sorted(tiendas.values(), key=lambda x: (-x['uds'], x['nombre'])):
    o = sorted(oleadas, key=lambda x: (x['uds'], x['num']))[0]
    o['tiendas'].append(t)
    o['uds'] += t['uds']
    o['outs'] += len(t['outs'])
num_rondas = 0
for o in oleadas:
    if o['ronda'] > num_rondas:
        num_rondas = o['ronda']

# ---------------- 3. Lineas por pasillo --------------------------------------
# pasillo = lineal // 2  (L1 -> 0, L2-L3 -> 1, ..., L136 -> 68)
lineas_sin_l = 0
uds_sin_l = 0.0
detalle = []   # (oleada, pasillo, lineal, ubicacion_id, uds, ronda)
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
                    uds_sin_l += qty
                    continue
                detalle.append((o['num'], lineal // 2, lineal, ml.location_id.id, qty, o['ronda']))

# Una parada = una ubicacion dentro de una ronda (en una ronda se pasa una vez).
uds_pasillo = {}
paradas_pasillo = {}   # pasillo -> {(ronda, ubicacion): 1}
for item in detalle:
    k = item[1]
    uds_pasillo[k] = uds_pasillo.get(k, 0.0) + item[4]
    if k not in paradas_pasillo:
        paradas_pasillo[k] = {}
    paradas_pasillo[k][(item[5], item[3])] = 1
peso_pasillo = {}
for k in uds_pasillo.keys():
    if EQUILIBRAR_ZONAS_POR == 'uds':
        peso_pasillo[k] = uds_pasillo[k]
    else:
        peso_pasillo[k] = seg_carga(uds_pasillo[k], len(paradas_pasillo[k]))

# ---------------- 4. Zonas -----------------------------------------------------
# zona_de_pasillo[pasillo] = numero de zona (1..NUM_ZONAS)
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
    for k in peso_pasillo.keys():
        total_p += peso_pasillo[k]
    objetivo = NUM_ZONAS and total_p / NUM_ZONAS or total_p
    z = 1
    acumulado = 0.0
    inicio = None
    pasillos_ordenados = sorted(peso_pasillo.keys())
    for k in pasillos_ordenados:
        if inicio is None:
            inicio = k
        zona_de_pasillo[k] = z
        acumulado += peso_pasillo[k]
        if acumulado >= objetivo * z and z < NUM_ZONAS and k != pasillos_ordenados[-1]:
            rangos.append((z, max(1, inicio * 2), min(LINEAL_MAX, k * 2 + 1)))
            z += 1
            inicio = None
    if inicio is not None:
        rangos.append((z, max(1, inicio * 2), min(LINEAL_MAX, pasillos_ordenados[-1] * 2 + 1)))

# ---------------- 5. INT (oleada x zona) y cargas -----------------------------
matriz = {}      # (oleada, zona) -> {'uds', 'ubic': {}}
carga_rz = {}    # (ronda, zona) -> {'uds', 'ubic': {}}
carga_zona = {}  # zona -> {'uds', 'ubic': {}, 'ubic_r': {}}
fuera_zona = 0.0
for item in detalle:
    zona = zona_de_pasillo.get(item[1], 0)
    if not zona:
        fuera_zona += item[4]
        continue
    clave = (item[0], zona)
    if clave not in matriz:
        matriz[clave] = {'uds': 0.0, 'ubic': {}}
    matriz[clave]['uds'] += item[4]
    matriz[clave]['ubic'][item[3]] = 1
    clave = (item[5], zona)
    if clave not in carga_rz:
        carga_rz[clave] = {'uds': 0.0, 'ubic': {}}
    carga_rz[clave]['uds'] += item[4]
    carga_rz[clave]['ubic'][item[3]] = 1
    if zona not in carga_zona:
        carga_zona[zona] = {'uds': 0.0, 'ubic': {}, 'ubic_r': {}}
    carga_zona[zona]['uds'] += item[4]
    carga_zona[zona]['ubic'][item[3]] = 1
    carga_zona[zona]['ubic_r'][(item[5], item[3])] = 1

# ---------------- 6. Horario estimado ---------------------------------------
# Cada PDA hace sus rondas en orden; la ronda esta lista cuando todas las
# zonas la han terminado. Cada oleada va a la U que antes queda libre.
fin_zona = {}
for r in rangos:
    fin_zona[r[0]] = inicio_min
rondas = []
for nr in range(1, num_rondas + 1):
    ronda = {'num': nr, 'oleadas': 0, 'uds': 0.0, 'paradas': 0, 'listo': inicio_min}
    for r in rangos:
        c = carga_rz.get((nr, r[0]))
        if c:
            fin_zona[r[0]] += seg_carga(c['uds'], len(c['ubic'])) / 60.0
            ronda['uds'] += c['uds']
            ronda['paradas'] += len(c['ubic'])
            if fin_zona[r[0]] > ronda['listo']:
                ronda['listo'] = fin_zona[r[0]]
    for o in oleadas:
        if o['ronda'] == nr:
            ronda['oleadas'] += 1
    rondas.append(ronda)
libre_u = {}
uds_u = {}
for i in range(NUM_U):
    libre_u[i + 1] = inicio_min
    uds_u[i + 1] = 0.0
espera_total = 0.0
for o in sorted(oleadas, key=lambda x: x['num']):
    o['listo'] = rondas[o['ronda'] - 1]['listo']
    u = sorted(libre_u.keys(), key=lambda x: (libre_u[x], x))[0]
    o['u'] = u
    o['ini'] = max(o['listo'], libre_u[u])
    o['espera'] = o['ini'] - libre_u[u]
    o['fin'] = o['ini'] + o['uds'] * 60.0 / UDS_HORA_U
    libre_u[u] = o['fin']
    uds_u[u] += o['uds']
    espera_total += o['espera']

# ----------------------------- MENSAJE ---------------------------------------
lineas.append('')
lineas.append('OUT pendientes: %d | de tienda simuladas: %d | descartadas: %d | tiendas: %d | uds: %d'
              % (len(candidatos), len(candidatos) - descartadas, descartadas, len(tiendas), total_uds))
lineas.append('Lineas sin lineal reconocible: %d (%d uds)' % (lineas_sin_l, uds_sin_l))
for k in sorted(motivos.keys()):
    lineas.append('   %s: %d OUT' % (k, motivos[k]))
for k in sorted(oleadas_existentes.keys()):
    lineas.append('   Ya estan en la oleada %s: %d OUT de tienda%s' % (k, oleadas_existentes[k], INCLUIR_YA_EN_OLEADA and ' (incluidas en la simulacion)' or ''))
if sin_reserva:
    lineas.append('   OUT de tienda sin nada reservado (no entrarian en ninguna oleada):')
    for s in sin_reserva[:MAX_DESCARTADAS_LISTA]:
        lineas.append('      %s' % s)
    if len(sin_reserva) > MAX_DESCARTADAS_LISTA:
        lineas.append('      ... y %d mas' % (len(sin_reserva) - MAX_DESCARTADAS_LISTA))

lineas.append('')
lineas.append('ZONAS (una por PDA): lineales | uds | paradas (distintas / sumando rondas, solape) | tiempo | fin')
tiempo_total_pick = 0.0
for r in rangos:
    c = carga_zona.get(r[0], {'uds': 0.0, 'ubic': {}, 'ubic_r': {}})
    p_dist = len(c['ubic'])
    p_r = len(c['ubic_r'])
    seg = seg_carga(c['uds'], p_r)
    tiempo_total_pick += seg
    solape = p_dist and (p_r - p_dist) * 100.0 / p_dist or 0.0
    lineas.append('   Z%d: L%02d-L%02d | %d uds | %d / %d paradas (+%d%%) | %.1f h | %s'
                  % (r[0], r[1], r[2], c['uds'], p_dist, p_r, solape, seg / 3600.0, hhmm(fin_zona.get(r[0], inicio_min))))
if fuera_zona:
    lineas.append('   Fuera de las zonas fijas: %d uds' % fuera_zona)

lineas.append('')
lineas.append('RONDAS (cada PDA pica a la vez las oleadas de la ronda, un carro por oleada)')
lineas.append('   %-5s %7s %6s %8s | %s' % ('Ronda', 'Oleadas', 'Uds', 'Paradas', 'Lista'))
for ronda in rondas:
    lineas.append('   R%-4d %7d %6d %8d | %s' % (ronda['num'], ronda['oleadas'], ronda['uds'], ronda['paradas'], hhmm(ronda['listo'])))

lineas.append('')
lineas.append('OLEADAS e INT que se crearian (uds / paradas por zona)')
cabecera = '   %-6s %-3s %-3s %5s %4s %6s |' % ('Oleada', 'R', 'U', 'Tiend', 'OUT', 'Uds')
for r in rangos:
    cabecera += ' %-10s' % ('Z%d' % r[0])
lineas.append(cabecera)
num_int = 0
for o in oleadas:
    fila = '   %-6s %-3s %-3s %5d %4d %6d |' % ('O%d' % o['num'], 'R%d' % o['ronda'], 'U%d' % o['u'], len(o['tiendas']), o['outs'], o['uds'])
    for r in rangos:
        m = matriz.get((o['num'], r[0]))
        if m:
            num_int += 1
        fila += ' %-10s' % (m and ('%d/%d' % (m['uds'], len(m['ubic']))) or '-')
    lineas.append(fila)
lineas.append('   (%d INT hacia SORTER/U<n>; cada PDA hace su columna, ronda a ronda)' % num_int)

lineas.append('')
lineas.append('HORARIO ESTIMADO (lectura a %d uds/h; cada oleada a la U que antes queda libre)' % UDS_HORA_U)
lineas.append('   %-6s %-3s %-3s %6s | %-5s %-6s %-5s %s' % ('Oleada', 'R', 'U', 'Uds', 'Lista', 'Inicio', 'Fin', 'Espera U'))
fin_ultima = inicio_min
for o in oleadas:
    lineas.append('   %-6s %-3s %-3s %6d | %-5s %-6s %-5s %d min'
                  % ('O%d' % o['num'], 'R%d' % o['ronda'], 'U%d' % o['u'], o['uds'], hhmm(o['listo']), hhmm(o['ini']), hhmm(o['fin']), o['espera']))
    if o['fin'] > fin_ultima:
        fin_ultima = o['fin']
for i in range(NUM_U):
    lineas.append('   U%d: %d uds, termina a las %s' % (i + 1, uds_u[i + 1], hhmm(libre_u[i + 1])))
lineas.append('   Picking total: %.1f h de PDA | Lectura total: %.1f h de U | Espera total de las U: %d min'
              % (tiempo_total_pick / 3600.0, total_uds / UDS_HORA_U, espera_total))
lineas.append('   Ultima U termina a las %s%s' % (hhmm(fin_ultima), fin_ultima > limite_min and (' - PASA DEL LIMITE %s' % HORA_LIMITE) or ''))

lineas.append('')
lineas.append('TIENDAS POR OLEADA')
for o in oleadas:
    nombres = []
    for t in o['tiendas']:
        nombres.append('%s (%d)' % (t['nombre'], t['uds']))
    lineas.append('   O%d (R%d, U%d): %s' % (o['num'], o['ronda'], o['u'], ', '.join(nombres) or '-'))

texto_completo = '\n'.join(lineas)
log('KOROSHI SIMULACION OLEADAS ZONAS v4\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

# =============================================================================
# KOROSHI - SIMULACION OLEADAS v6: RONDAS + PICKERS QUE SE AYUDAN (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Esquema que se simula (no se crea nada):
#   1. Las OUT de tienda (PED. TIENDAS) del dia. Con ESCENARIO_UDS > 0 se
#      escalan a ese volumen (p.ej. 10.000 uds): las uds en proporcion y las
#      paradas con EXP_PARADAS (con mas volumen se repiten ubicaciones).
#   2. NUM_RONDAS rondas; cada ronda tiene una oleada por U (NUM_U), cada oleada
#      como maximo TIENDAS_POR_OLEADA tiendas, equilibradas por uds.
#   3. Picking por tareas de pasillo (L2k/L2k+1, o modulo MU):
#        RUTA = 'conjunta'   -> tarea = pasillo x ronda (una pasada, bolsa por U)
#        RUTA = 'secuencial' -> tarea = pasillo x oleada
#      MODO_PDA = 'cola'  -> los pickers se ayudan: cada uno empieza en su tramo
#                            y al acabar coge la siguiente tarea pendiente
#      MODO_PDA = 'fijas' -> cada PDA solo hace su zona (ZONAS_FIJAS o equilibradas)
#   4. Las rondas se pican en orden; una ronda esta lista cuando estan hechas
#      todas sus tareas y entonces sus oleadas pasan a las U (packing), mientras
#      los pickers siguen con la ronda siguiente.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
HORAS_ATRAS = 16
ESCENARIO_UDS = 10000            # 0 = volumen real del dia
EXP_PARADAS = 0.35               # paradas ~ (volumen relativo) ^ EXP_PARADAS
NUM_U = 5
NUM_RONDAS = 2
TIENDAS_POR_OLEADA = 10
NUM_PDA = 10
MODO_PDA = 'cola'                # 'cola' o 'fijas'
RUTA = 'conjunta'                # 'conjunta' o 'secuencial'
# Solo con MODO_PDA = 'fijas': [[1, 49], [50, 57], ...]. Vacio = equilibradas.
ZONAS_FIJAS = []
HORA_INICIO_PICKING = '06:00'
HORA_INICIO_U = '06:00'
HORA_LIMITE = '13:00'
T_PARADA_SEG = 20
T_UD_SEG = 4
T_CAMBIO_TAREA_SEG = 60          # ir de un pasillo a otro / abrir la siguiente tarea
UDS_HORA_U = 425
LINEAL_MAX = 136
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
inicio_pick = minutos(HORA_INICIO_PICKING)
inicio_u = minutos(HORA_INICIO_U)
limite = minutos(HORA_LIMITE)

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
for p in candidatos:
    tipo = p.sale_id and p.sale_id.s_order_type_id and p.sale_id.s_order_type_id.name or ''
    if tipo != TIPO_PEDIDO:
        continue
    if p.batch_id and not INCLUIR_YA_EN_OLEADA:
        continue
    if p.state not in ('assigned', 'done') and not INCLUIR_RESERVA_PARCIAL:
        continue
    uds = 0.0
    for ml in p.move_line_ids:
        if p.state == 'done':
            uds += ml.qty_done
        else:
            uds += ml.product_uom_qty
    if uds <= 0:
        continue
    clave = p.partner_id.id
    if clave not in tiendas:
        tiendas[clave] = {'nombre': p.partner_id.name or '-', 'outs': [], 'uds': 0.0}
    tiendas[clave]['outs'].append(p)
    tiendas[clave]['uds'] += uds

total_real = 0.0
for t in tiendas.values():
    total_real += t['uds']
factor = 1.0
if ESCENARIO_UDS > 0 and total_real > 0:
    factor = ESCENARIO_UDS / total_real
factor_paradas = factor ** EXP_PARADAS

# ---------------- 2. Oleadas y rondas -----------------------------------------
num_oleadas = NUM_U * NUM_RONDAS
while num_oleadas * TIENDAS_POR_OLEADA < len(tiendas):
    num_oleadas += NUM_U
if num_oleadas > len(tiendas):
    num_oleadas = max(1, len(tiendas))
oleadas = []
for i in range(num_oleadas):
    oleadas.append({'num': i + 1, 'ronda': (i // NUM_U) + 1, 'u': (i % NUM_U) + 1, 'tiendas': [], 'uds': 0.0})
for t in sorted(tiendas.values(), key=lambda x: (-x['uds'], x['nombre'])):
    o = sorted(oleadas, key=lambda x: (len(x['tiendas']) >= TIENDAS_POR_OLEADA, x['uds'], x['num']))[0]
    o['tiendas'].append(t)
    o['uds'] += t['uds']
num_rondas = 0
for o in oleadas:
    if o['ronda'] > num_rondas:
        num_rondas = o['ronda']

# ---------------- 3. Lineas -> pasillo / modulo MU ---------------------------
# pasillo: L(2k)/L(2k+1) -> k ; MU-nn -> 1000 + nn ; resto -> 9999
cache_pasillo = {}
detalle = []   # (oleada, ronda, pasillo, ubicacion_id, uds)
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
                loc = ml.location_id
                if loc.id not in cache_pasillo:
                    pasillo = 9999
                    segmentos = (loc.complete_name or '').split('/')
                    for idx in range(len(segmentos) - 1, -1, -1):
                        texto = segmentos[idx].strip()
                        if ' - ' in texto:
                            texto = texto.split(' - ', 1)[1]
                        if texto[:3] == 'MU-':
                            num = ''
                            for ch in texto[3:]:
                                if ch.isdigit():
                                    num += ch
                                else:
                                    break
                            if num:
                                pasillo = 1000 + int(num)
                                break
                        if len(texto) > 1 and texto[0] == 'L' and texto[1].isdigit():
                            num = ''
                            for ch in texto[1:]:
                                if ch.isdigit():
                                    num += ch
                                else:
                                    break
                            pasillo = int(num) // 2
                            break
                    cache_pasillo[loc.id] = pasillo
                detalle.append((o['num'], o['ronda'], cache_pasillo[loc.id], loc.id, qty))

nombre_pasillo = lambda k: (k == 9999 and 'OTRAS') or (k >= 1000 and ('MU-%02d' % (k - 1000))) or ('L%02d-L%02d' % (max(1, k * 2), min(LINEAL_MAX, k * 2 + 1)))

# ---------------- 4. Tareas de picking ----------------------------------------
tareas = {}   # (ronda, oleada o 0, pasillo) -> {'uds', 'ubic'}
for item in detalle:
    if RUTA == 'secuencial':
        c = (item[1], item[0], item[2])
    else:
        c = (item[1], 0, item[2])
    if c not in tareas:
        tareas[c] = {'uds': 0.0, 'ubic': {}}
    tareas[c]['uds'] += item[4]
    tareas[c]['ubic'][item[3]] = 1
seg_tarea = {}
for c in tareas.keys():
    seg_tarea[c] = (tareas[c]['uds'] * factor * T_UD_SEG + len(tareas[c]['ubic']) * factor_paradas * T_PARADA_SEG
                    + T_CAMBIO_TAREA_SEG)

# Tramo de inicio de cada PDA (y zona si MODO_PDA = 'fijas'): cortes por tiempo
peso_pasillo = {}
for c in tareas.keys():
    peso_pasillo[c[2]] = peso_pasillo.get(c[2], 0.0) + seg_tarea[c]
zona_de_pasillo = {}
rangos = []
pasillos_l = sorted(peso_pasillo.keys())   # L por orden, despues MU (1000+) y OTRAS (9999)
if ZONAS_FIJAS:
    z = 0
    for rango in ZONAS_FIJAS:
        z += 1
        rangos.append((z, rango[0] // 2, rango[1] // 2))   # en pasillos
        for lin in range(rango[0], rango[1] + 1):
            zona_de_pasillo[lin // 2] = z
else:
    total_p = 0.0
    for k in pasillos_l:
        total_p += peso_pasillo[k]
    objetivo = total_p / NUM_PDA
    z = 1
    acumulado = 0.0
    inicio = None
    for k in pasillos_l:
        if inicio is None:
            inicio = k
        zona_de_pasillo[k] = z
        acumulado += peso_pasillo[k]
        if acumulado >= objetivo * z and z < NUM_PDA and k != pasillos_l[-1]:
            rangos.append((z, inicio, k))
            z += 1
            inicio = None
    if inicio is not None:
        rangos.append((z, inicio, pasillos_l[-1]))
# MU y OTRAS sin zona fija: a la ultima zona
for k in peso_pasillo.keys():
    if k not in zona_de_pasillo:
        zona_de_pasillo[k] = len(rangos) or 1

# ---------------- 5. Reparto de tareas y horario de las rondas ---------------
libre_pda = {}
seg_pda = {}
for i in range(NUM_PDA):
    libre_pda[i + 1] = inicio_pick
    seg_pda[i + 1] = 0.0
lista_ronda = {}
for nr in range(1, num_rondas + 1):
    de_la_ronda = []
    for c in tareas.keys():
        if c[0] == nr:
            de_la_ronda.append(c)
    fin_ronda = inicio_pick
    if MODO_PDA == 'fijas':
        for c in sorted(de_la_ronda, key=lambda x: (x[2], x[1])):
            pda = zona_de_pasillo.get(c[2], 1)
            if pda > NUM_PDA:
                pda = NUM_PDA
            libre_pda[pda] += seg_tarea[c] / 60.0
            seg_pda[pda] += seg_tarea[c]
            if libre_pda[pda] > fin_ronda:
                fin_ronda = libre_pda[pda]
    else:
        # Cola: cada PDA hace primero las tareas de su tramo; cuando no le quedan,
        # ayuda con la tarea pendiente mas cercana de otro tramo.
        pendientes = sorted(de_la_ronda, key=lambda x: (x[2], x[1]))
        posicion = {}
        for i in range(NUM_PDA):
            posicion[i + 1] = rangos[min(i, len(rangos) - 1)][1]
        while pendientes:
            pda = sorted(libre_pda.keys(), key=lambda x: (libre_pda[x], x))[0]
            propias = []
            for x in pendientes:
                if zona_de_pasillo.get(x[2], 0) == pda:
                    propias.append(x)
            if propias:
                c = propias[0]
            else:
                c = sorted(pendientes, key=lambda x: (abs(x[2] - posicion[pda]), -seg_tarea[x], x[2]))[0]
            pendientes.remove(c)
            libre_pda[pda] += seg_tarea[c] / 60.0
            seg_pda[pda] += seg_tarea[c]
            posicion[pda] = c[2]
            if libre_pda[pda] > fin_ronda:
                fin_ronda = libre_pda[pda]
    lista_ronda[nr] = fin_ronda
    # La ronda siguiente empieza cuando cada PDA acaba (no se esperan entre ellas)

libre_u = {}
uds_u = {}
for i in range(NUM_U):
    libre_u[i + 1] = inicio_u
    uds_u[i + 1] = 0.0
for o in sorted(oleadas, key=lambda x: x['num']):
    o['lista'] = lista_ronda.get(o['ronda'], inicio_pick)
    o['ini'] = max(o['lista'], libre_u[o['u']])
    o['espera'] = o['ini'] - libre_u[o['u']]
    o['fin'] = o['ini'] + o['uds'] * factor * 60.0 / UDS_HORA_U
    libre_u[o['u']] = o['fin']
    uds_u[o['u']] += o['uds'] * factor

# ----------------------------- MENSAJE ---------------------------------------
lineas = []
lineas.append('SIMULACION OLEADAS KOROSHI v6 - NO SE HA CREADO NADA - %s UTC' % ahora_utc.strftime('%d/%m/%Y %H:%M'))
lineas.append('Escenario: %s | %d tiendas | %d rondas x %d U | %d PDA en modo %s | ruta %s'
              % (ESCENARIO_UDS and ('%d uds (real %d, x%.2f)' % (ESCENARIO_UDS, total_real, factor)) or ('real %d uds' % total_real),
                 len(tiendas), num_rondas, NUM_U, NUM_PDA, MODO_PDA, RUTA))
lineas.append('Horas: picking desde %s, U desde %s, limite %s | %d s/parada, %d s/ud, %d s/cambio, %d uds/h por U (sin pausas)'
              % (HORA_INICIO_PICKING, HORA_INICIO_U, HORA_LIMITE, T_PARADA_SEG, T_UD_SEG, T_CAMBIO_TAREA_SEG, UDS_HORA_U))

lineas.append('')
lineas.append('RONDAS: ronda | oleadas | tiendas | uds | tareas | lista (pasa a las U)')
for nr in range(1, num_rondas + 1):
    n_ol = 0
    n_ti = 0
    u_r = 0.0
    for o in oleadas:
        if o['ronda'] == nr:
            n_ol += 1
            n_ti += len(o['tiendas'])
            u_r += o['uds'] * factor
    n_ta = 0
    for c in tareas.keys():
        if c[0] == nr:
            n_ta += 1
    lineas.append('   R%d | %d | %d | %d | %d | %s' % (nr, n_ol, n_ti, u_r, n_ta, hhmm(lista_ronda[nr])))

lineas.append('')
lineas.append('PDA: tramo de inicio | horas | termina')
total_pick = 0.0
for i in range(NUM_PDA):
    r = rangos[min(i, len(rangos) - 1)]
    total_pick += seg_pda[i + 1]
    lineas.append('   PDA %d: %s a %s | %.1f h | %s'
                  % (i + 1, nombre_pasillo(r[1]), nombre_pasillo(r[2]), seg_pda[i + 1] / 3600.0, hhmm(libre_pda[i + 1])))

lineas.append('')
lineas.append('U (packing): oleada | ronda | uds | lista | inicio | fin | espera')
fin_ultima = inicio_u
for o in oleadas:
    lineas.append('   U%d O%d | R%d | %d | %s | %s | %s | %d min'
                  % (o['u'], o['num'], o['ronda'], o['uds'] * factor, hhmm(o['lista']), hhmm(o['ini']), hhmm(o['fin']), o['espera']))
    if o['fin'] > fin_ultima:
        fin_ultima = o['fin']
lineas.append('   Picking: %.1f h de PDA (sumando todas) | Lectura: %.1f h de U (sumando todas) | Ultima U termina a las %s%s'
              % (total_pick / 3600.0, total_real * factor / UDS_HORA_U, hhmm(fin_ultima),
                 fin_ultima > limite and (' - PASA DEL LIMITE %s' % HORA_LIMITE) or ''))

lineas.append('')
lineas.append('TIENDAS POR OLEADA (uds del escenario)')
for o in oleadas:
    nombres = []
    for t in o['tiendas']:
        nombres.append('%s (%d)' % (t['nombre'], t['uds'] * factor))
    lineas.append('   O%d (R%d, U%d): %s' % (o['num'], o['ronda'], o['u'], ', '.join(nombres) or '-'))

texto_completo = '\n'.join(lineas)
log('KOROSHI SIMULACION OLEADAS v6\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

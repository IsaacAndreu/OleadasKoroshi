# =============================================================================
# KOROSHI - ANALISIS DE ZONAS DE PICKING CON VARIOS DIAS (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Mira las lineas ya servidas (OUT validadas) de los pedidos de tienda
# (PED. TIENDAS) de los ultimos DIAS dias y calcula, de media por dia:
#   - volumen de cada dia (uds, lineas, paradas = ubicaciones distintas);
#   - carga de cada pasillo (un pasillo da servicio a L(2k) y L(2k+1)) y de
#     cada modulo MU-nn;
#   - una propuesta de ZONAS FIJAS para NUM_PDA pickers, equilibradas por
#     tiempo medio (paradas y uds), con los cortes en lineal impar, lista para
#     pegar en la simulacion v5.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
DIAS = 30
NUM_PDA = 5
# True = la zona MU la hace una PDA sola y los pasillos L se reparten entre las
# demas (NUM_PDA - 1). False = los pasillos L entre las NUM_PDA y MU aparte.
MU_ZONA_PROPIA = True
T_PARADA_SEG = 20
T_UD_SEG = 4
LINEAL_MAX = 136
MAX_LINEAS_MENSAJE = 250
# -----------------------------------------------------------------------------

ahora = datetime.datetime.utcnow()
desde_txt = (ahora - datetime.timedelta(days=DIAS)).strftime('%Y-%m-%d 00:00:00')
seg_carga = lambda uds, paradas: uds * T_UD_SEG + paradas * T_PARADA_SEG

# Una fila por ubicacion y dia: numero de lineas y uds servidas
grupos = env['stock.move.line'].read_group(
    [
        ('company_id', '=', COMPANY_ID),
        ('state', '=', 'done'),
        ('date', '>=', desde_txt),
        ('location_dest_id.usage', '=', 'customer'),
        ('picking_id.sale_id.s_order_type_id.name', '=', TIPO_PEDIDO),
    ],
    ['location_id', 'qty_done'],
    ['location_id', 'date:day'],
    lazy=False,
)

nombres = {}
for g in grupos:
    if g['location_id']:
        nombres[g['location_id'][0]] = 1
ubicaciones = env['stock.location'].browse(list(nombres.keys()))
clave_ubic = {}   # id -> ('L', pasillo) / ('MU', n) / ('OTRO', nombre)
for loc in ubicaciones:
    clave = None
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
                clave = ('MU', int(num))
                break
        if len(texto) > 1 and texto[0] == 'L' and texto[1].isdigit():
            num = ''
            for ch in texto[1:]:
                if ch.isdigit():
                    num += ch
                else:
                    break
            clave = ('L', int(num) // 2)
            break
    if not clave:
        clave = ('OTRO', loc.complete_name or '-')
    clave_ubic[loc.id] = clave

# ---------------- Acumulados --------------------------------------------------
dias = {}        # dia -> [uds, lineas, paradas]
carga = {}       # clave -> [uds, lineas, paradas]
for g in grupos:
    if not g['location_id']:
        continue
    # La etiqueta de 'date:day' viene traducida ('16 oct. 2026'); la fecha ordenable
    # se saca del dominio del grupo (date >= 'AAAA-MM-DD ...').
    # El dominio del grupo incluye tambien el date >= de la busqueda: se coge el mayor.
    dia = ''
    for cond in g.get('__domain', []):
        if isinstance(cond, (list, tuple)) and len(cond) == 3 and cond[0] == 'date' and cond[1] == '>=':
            if str(cond[2])[:10] > dia:
                dia = str(cond[2])[:10]
    if not dia:
        dia = g['date:day']
    uds = g['qty_done'] or 0.0
    lineas_g = g['__count']
    if dia not in dias:
        dias[dia] = [0.0, 0, 0]
    dias[dia][0] += uds
    dias[dia][1] += lineas_g
    dias[dia][2] += 1
    clave = clave_ubic.get(g['location_id'][0], ('OTRO', '-'))
    if clave not in carga:
        carga[clave] = [0.0, 0, 0]
    carga[clave][0] += uds
    carga[clave][1] += lineas_g
    carga[clave][2] += 1
n_dias = len(dias) or 1
total_uds = 0.0
total_seg = 0.0
for k in carga.keys():
    total_uds += carga[k][0]
    total_seg += seg_carga(carga[k][0], carga[k][2])

lineas = []
lineas.append('ANALISIS DE ZONAS KOROSHI - NO SE HA MODIFICADO NADA - %s UTC' % ahora.strftime('%d/%m/%Y %H:%M'))
lineas.append('Lineas servidas de %s de los ultimos %d dias (%d dias con salidas) | %d s/parada, %d s/ud'
              % (TIPO_PEDIDO, DIAS, len(dias), T_PARADA_SEG, T_UD_SEG))

lineas.append('')
lineas.append('VOLUMEN POR DIA: dia | uds | lineas | paradas | horas de picking')
for dia in sorted(dias.keys()):
    d = dias[dia]
    lineas.append('   %-12s | %6d | %6d | %6d | %5.1f h' % (dia, d[0], d[1], d[2], seg_carga(d[0], d[2]) / 3600.0))
lineas.append('   Media: %d uds/dia, %.1f h de picking/dia' % (total_uds / n_dias, total_seg / 3600.0 / n_dias))

# ---------------- Carga por zona fisica ---------------------------------------
lineas.append('')
lineas.append('CARGA MEDIA POR DIA: zona | uds/dia | paradas/dia | min/dia | % del tiempo')
total_l = 0.0
total_mu = 0.0
total_otro = 0.0
pasillos = []
mus = []
otros = []
for k in carga.keys():
    s = seg_carga(carga[k][0], carga[k][2])
    if k[0] == 'L':
        pasillos.append(k)
        total_l += s
    elif k[0] == 'MU':
        mus.append(k)
        total_mu += s
    else:
        otros.append(k)
        total_otro += s
for k in sorted(pasillos, key=lambda x: x[1]):
    c = carga[k]
    s = seg_carga(c[0], c[2])
    lineas.append('   L%02d-L%02d   | %6.0f | %5.0f | %5.0f | %4.1f%%'
                  % (max(1, k[1] * 2), min(LINEAL_MAX, k[1] * 2 + 1), c[0] / n_dias, c[2] / float(n_dias),
                     s / 60.0 / n_dias, total_seg and s * 100.0 / total_seg or 0))
for k in sorted(mus, key=lambda x: x[1]):
    c = carga[k]
    s = seg_carga(c[0], c[2])
    lineas.append('   MU-%02d     | %6.0f | %5.0f | %5.0f | %4.1f%%'
                  % (k[1], c[0] / n_dias, c[2] / float(n_dias), s / 60.0 / n_dias, total_seg and s * 100.0 / total_seg or 0))
lineas.append('   Total pasillos L: %.1f h/dia (%d%%) | MU: %.1f h/dia (%d%%) | otras: %.1f h/dia (%d%%)'
              % (total_l / 3600.0 / n_dias, total_seg and total_l * 100.0 / total_seg or 0,
                 total_mu / 3600.0 / n_dias, total_seg and total_mu * 100.0 / total_seg or 0,
                 total_otro / 3600.0 / n_dias, total_seg and total_otro * 100.0 / total_seg or 0))
if otros:
    lineas.append('   Otras ubicaciones (ni L ni MU), las 10 con mas uds:')
    for k in sorted(otros, key=lambda x: -carga[x][0])[:10]:
        lineas.append('      %s | %d uds/dia' % (k[1], carga[k][0] / n_dias))

# ---------------- Propuesta de zonas fijas ------------------------------------
pda_l = NUM_PDA
if MU_ZONA_PROPIA and mus:
    pda_l = NUM_PDA - 1
lineas.append('')
lineas.append('PROPUESTA DE ZONAS FIJAS (%d PDA en pasillos L%s), equilibradas por tiempo medio'
              % (pda_l, (MU_ZONA_PROPIA and mus) and ' + 1 PDA en MU' or ''))
objetivo = pda_l and total_l / pda_l or total_l
z = 1
acumulado = 0.0
inicio = None
cortes = []
tramo = 0.0
ordenados = sorted(pasillos, key=lambda x: x[1])
for k in ordenados:
    if inicio is None:
        inicio = k[1]
        tramo = 0.0
    s = seg_carga(carga[k][0], carga[k][2])
    acumulado += s
    tramo += s
    if acumulado >= objetivo * z and z < pda_l and k != ordenados[-1]:
        cortes.append((max(1, inicio * 2), min(LINEAL_MAX, k[1] * 2 + 1), tramo))
        z += 1
        inicio = None
if inicio is not None:
    cortes.append((max(1, inicio * 2), min(LINEAL_MAX, ordenados[-1][1] * 2 + 1), tramo))
# La primera zona empieza en L01 y la ultima acaba en el ultimo lineal, para cubrir toda la nave
if cortes:
    cortes[0] = (1, cortes[0][1], cortes[0][2])
    cortes[-1] = (cortes[-1][0], LINEAL_MAX, cortes[-1][2])
texto_zonas = []
n = 0
for c in cortes:
    n += 1
    lineas.append('   PDA %d: L%02d-L%02d | %.1f h/dia' % (n, c[0], c[1], c[2] / 3600.0 / n_dias))
    texto_zonas.append('[%d, %d]' % (c[0], c[1]))
if MU_ZONA_PROPIA and mus:
    lineas.append('   PDA %d: MU-%02d a MU-%02d | %.1f h/dia' % (n + 1, sorted(mus, key=lambda x: x[1])[0][1],
                                                               sorted(mus, key=lambda x: x[1])[-1][1], total_mu / 3600.0 / n_dias))
lineas.append('   Para la simulacion v5: ZONAS_FIJAS = [%s]' % ', '.join(texto_zonas))

texto_completo = '\n'.join(lineas)
log('KOROSHI ANALISIS ZONAS\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

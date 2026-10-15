# =============================================================================
# KOROSHI - CALIBRAR TIEMPOS DE PICKING (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Estima los segundos por parada (T_PARADA_SEG) y por unidad (T_UD_SEG) de
# la simulacion de oleadas, a partir del picking real de las agrupaciones de
# tienda (TIENDA dd-mm) con la PDA:
#   - Lineas de OUT de esas agrupaciones con qty_done > 0.
#   - Se ordenan por write_date (hora del ultimo escaneo de la linea) y por
#     usuario. Hueco = segundos entre una linea y la anterior del mismo usuario.
#   - Hueco en la misma ubicacion -> tiempo de coger las uds (T_UD).
#   - Hueco con cambio de ubicacion -> andar + coger (T_PARADA + qty * T_UD).
# OJO: al validar el albaran Odoo reescribe las lineas y write_date pasa a ser
# la hora de validacion. Por eso, por defecto, solo se miran OUT NO validadas:
# ejecutar mientras se esta picando (o antes de validar).
# Si varias PDA usan el mismo usuario, las secuencias se mezclan: se avisa
# por los saltos grandes de lineal.
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
PREFIJO_AGRUPACION = 'TIENDA'
DIAS_ATRAS = 2
INCLUIR_VALIDADAS = False
# Huecos mayores se consideran pausa y no cuentan.
MAX_HUECO_SEG = 300
# Salto de lineales entre dos lineas seguidas que se considera "raro"
# (otra persona con el mismo usuario).
SALTO_LINEALES = 20
# Si se sabe cuantas personas han picado a la vez, estimacion global.
NUM_PICKERS = 0
EJEMPLO_LINEAS = 25
MAX_LINEAS_MENSAJE = 250
# -----------------------------------------------------------------------------

ahora_utc = datetime.datetime.utcnow()
desde_txt = (ahora_utc - datetime.timedelta(days=DIAS_ATRAS)).strftime('%Y-%m-%d %H:%M:%S')
mediana = lambda l: l and sorted(l)[len(l) // 2] or 0.0
lineas = []
lineas.append('CALIBRAR TIEMPOS PICKING KOROSHI - NO SE HA MODIFICADO NADA - %s UTC' % ahora_utc.strftime('%d/%m/%Y %H:%M'))
lineas.append('Parametros: PREFIJO=%s, DIAS_ATRAS=%d, INCLUIR_VALIDADAS=%s, MAX_HUECO_SEG=%d, NUM_PICKERS=%d'
              % (PREFIJO_AGRUPACION, DIAS_ATRAS, INCLUIR_VALIDADAS, MAX_HUECO_SEG, NUM_PICKERS))

# ---------------- 1. Agrupaciones y lineas -----------------------------------
batches = env['stock.picking.batch'].search([
    ('name', '=ilike', PREFIJO_AGRUPACION + '%'),
    ('create_date', '>=', desde_txt),
], order='id asc')
lineas.append('')
lineas.append('AGRUPACIONES')
datos = []   # (write_date, usuario_id, usuario, batch, ubicacion_id, lineal, qty, ubicacion)
for b in batches:
    n_out = 0
    n_lin = 0
    uds_b = 0.0
    for p in b.picking_ids:
        if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing':
            continue
        if p.state == 'cancel':
            continue
        if p.state == 'done' and not INCLUIR_VALIDADAS:
            continue
        n_out += 1
        for ml in p.move_line_ids:
            if ml.qty_done <= 0:
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
            n_lin += 1
            uds_b += ml.qty_done
            datos.append((ml.write_date, ml.write_uid.id, ml.write_uid.name or '-', b.name, ml.location_id.id,
                          lineal, ml.qty_done, ml.location_id.name or '-'))
    lineas.append('   %s (%s): %d OUT %s, %d lineas picadas, %d uds'
                  % (b.name, b.state, n_out, INCLUIR_VALIDADAS and 'no canceladas' or 'sin validar', n_lin, uds_b))
if not batches:
    lineas.append('   No hay agrupaciones %s... en los ultimos %d dias' % (PREFIJO_AGRUPACION, DIAS_ATRAS))

# ---------------- 2. Fiabilidad de write_date --------------------------------
horas_distintas = {}
for d in datos:
    horas_distintas[d[0]] = horas_distintas.get(d[0], 0) + 1
lineas.append('')
lineas.append('FIABILIDAD')
lineas.append('   Lineas picadas: %d | horas (write_date) distintas: %d' % (len(datos), len(horas_distintas)))
if datos:
    max_misma = 0
    for k in horas_distintas.keys():
        if horas_distintas[k] > max_misma:
            max_misma = horas_distintas[k]
    ratio = len(horas_distintas) * 100.0 / len(datos)
    lineas.append('   %d%% de lineas con hora propia; maximo %d lineas con la misma hora' % (ratio, max_misma))
    if ratio < 50:
        lineas.append('   *** NO FIABLE: muchas lineas se guardan a la vez (la PDA guarda en bloque o se ha validado).')

# ---------------- 3. Huecos por usuario ---------------------------------------
por_usuario = {}
for d in datos:
    if d[1] not in por_usuario:
        por_usuario[d[1]] = {'nombre': d[2], 'datos': []}
    por_usuario[d[1]]['datos'].append(d)

seg_ud_misma = []     # hueco / qty, misma ubicacion
seg_parada = []       # hueco con cambio de ubicacion (sin restar uds)
qty_parada = []       # qty de esas lineas
tot_activo = 0.0
tot_uds = 0.0
tot_paradas = 0
lineas.append('')
lineas.append('POR USUARIO (huecos <= %d s)' % MAX_HUECO_SEG)
lineas.append('   %-22s %6s %6s %8s %7s %7s %6s %7s' % ('Usuario', 'Lineas', 'Uds', 'Paradas', 'Activo', 'Uds/h', 'Par/h', 'Saltos'))
ejemplo = []
for uid in por_usuario.keys():
    lista = sorted(por_usuario[uid]['datos'], key=lambda x: x[0])
    activo = 0.0
    uds = 0.0
    paradas = 0
    saltos = 0
    anterior = None
    for d in lista:
        uds += d[6]
        nueva = anterior is None or anterior[4] != d[4]
        if nueva:
            paradas += 1
        if anterior is not None:
            hueco = (d[0] - anterior[0]).total_seconds()
            if nueva and d[5] and anterior[5] and abs(d[5] - anterior[5]) > SALTO_LINEALES:
                saltos += 1
            if 0 < hueco <= MAX_HUECO_SEG:
                activo += hueco
                if nueva:
                    seg_parada.append(hueco)
                    qty_parada.append(d[6])
                else:
                    seg_ud_misma.append(hueco / d[6])
        anterior = d
    if len(lista) > len(ejemplo):
        ejemplo = lista
    tot_activo += activo
    tot_uds += uds
    tot_paradas += paradas
    horas = activo / 3600.0
    lineas.append('   %-22s %6d %6d %8d %6.1fh %7d %6d %6d%%'
                  % (por_usuario[uid]['nombre'][:22], len(lista), uds, paradas, horas,
                     horas and uds / horas or 0, horas and paradas / horas or 0,
                     paradas and saltos * 100.0 / paradas or 0))
lineas.append('   (Saltos = cambios de mas de %d lineales entre dos lineas seguidas. Si es alto,'
              ' varias personas usan el mismo usuario y los huecos no sirven por usuario.)' % SALTO_LINEALES)

# ---------------- 4. Estimacion de tiempos ------------------------------------
lineas.append('')
lineas.append('ESTIMACION (medianas)')
t_ud = mediana(seg_ud_misma)
restos = []
for i in range(len(seg_parada)):
    restos.append(seg_parada[i] - qty_parada[i] * t_ud)
t_par = mediana(restos)
lineas.append('   Huecos misma ubicacion: %d -> T_UD_SEG ~ %.1f s/ud' % (len(seg_ud_misma), t_ud))
lineas.append('   Huecos cambio ubicacion: %d -> hueco mediano %.1f s -> T_PARADA_SEG ~ %.1f s'
              % (len(seg_parada), mediana(seg_parada), t_par))
if tot_activo:
    lineas.append('   Global (tiempo activo de todos los usuarios): %d uds, %d paradas en %.1f h -> %.1f s/ud o %.1f s/parada (todo incluido)'
                  % (tot_uds, tot_paradas, tot_activo / 3600.0, tot_activo / (tot_uds or 1), tot_activo / (tot_paradas or 1)))
if NUM_PICKERS and datos:
    primera = sorted(horas_distintas.keys())[0]
    ultima = sorted(horas_distintas.keys())[-1]
    ventana = (ultima - primera).total_seconds()
    lineas.append('   Con %d pickers entre %s y %s UTC (%.1f h): %.1f s de picker por ud, %.1f s por parada (todo incluido)'
                  % (NUM_PICKERS, primera.strftime('%H:%M'), ultima.strftime('%H:%M'), ventana / 3600.0,
                     ventana * NUM_PICKERS / (tot_uds or 1), ventana * NUM_PICKERS / (tot_paradas or 1)))

# ---------------- 5. Uds por hora (UTC) ---------------------------------------
lineas.append('')
lineas.append('UDS PICADAS POR HORA (UTC; en Espana +2 en verano, +1 en invierno)')
por_hora = {}
for d in datos:
    h = d[0].strftime('%d/%m %H:00')
    por_hora[h] = por_hora.get(h, 0.0) + d[6]
for h in sorted(por_hora.keys()):
    lineas.append('   %s  %5d uds' % (h, por_hora[h]))

# ---------------- 6. Ejemplo de secuencia -------------------------------------
lineas.append('')
lineas.append('EJEMPLO: primeras %d lineas del usuario con mas lineas (hora UTC | hueco | lineal | ubicacion | uds)' % EJEMPLO_LINEAS)
anterior = None
for d in ejemplo[:EJEMPLO_LINEAS]:
    hueco = anterior and (d[0] - anterior[0]).total_seconds() or 0
    lineas.append('   %s | %5d s | L%-3s | %-28s | %d' % (d[0].strftime('%H:%M:%S'), hueco, d[5] or '?', d[7][:28], d[6]))
    anterior = d

texto_completo = '\n'.join(lineas)
log('KOROSHI CALIBRAR TIEMPOS\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

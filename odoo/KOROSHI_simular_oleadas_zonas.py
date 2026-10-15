# =============================================================================
# KOROSHI - SIMULACION OLEADAS + PICKING POR ZONAS (SOLO LECTURA)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
#
# Simula lo que haria el cron de la noche, sin crear nada:
#   1. OUT de tiendas (tipo de pedido 'PED. TIENDAS') de las ultimas HORAS_ATRAS
#      horas, reservadas y sin oleada.
#   2. Reparte las tiendas en NUM_OLEADAS oleadas (una por "U"), equilibradas
#      por unidades. Todas las OUT de una tienda van a la misma oleada.
#   3. Asigna cada linea reservada a un pasillo segun el lineal (Lnn) de su
#      ubicacion. Un pasillo da servicio a L(2k) y L(2k+1).
#   4. Parte los pasillos en NUM_ZONAS zonas (una por PDA): seguidas y con
#      unidades parecidas esta noche, o fijas si se indican en ZONAS_FIJAS.
#   5. Muestra los INT que se crearian (oleada x zona), la carga de cada PDA y
#      la de cada "U", y comprueba que existen SORTER / EFFEC-STOCK /
#      EFFEC-INTERNAL y las sububicaciones SORTER/U1...
# No escribe nada: termina con un Warning. La unica escritura es el log().
#
# Reglas de safe_eval: sin f-strings, sin import, log() siempre antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
HORAS_ATRAS = 16
NUM_OLEADAS = 5
NUM_ZONAS = 5
# Zonas fijas por lineales, p.ej. [[1, 47], [48, 71], [72, 89], [90, 107], [108, 136]].
# Vacio = zonas equilibradas esta noche. Los cortes deben caer entre pasillos
# (acabar en lineal impar), para que un pasillo no quede partido entre dos PDA.
ZONAS_FIJAS = []
# Solo para simular (no se tocan): incluir OUT que ya estan en una oleada y
# OUT con reserva parcial (se cuentan solo las unidades reservadas).
INCLUIR_YA_EN_OLEADA = True
INCLUIR_RESERVA_PARCIAL = True
MAX_LINEAS_MENSAJE = 220
# -----------------------------------------------------------------------------

Picking = env['stock.picking']
ahora_utc = datetime.datetime.utcnow()
desde_txt = (ahora_utc - datetime.timedelta(hours=HORAS_ATRAS)).strftime('%Y-%m-%d %H:%M:%S')
lineas = []
lineas.append('SIMULACION OLEADAS + ZONAS KOROSHI - NO SE HA CREADO NADA - %s UTC' % ahora_utc.strftime('%d/%m/%Y %H:%M'))
lineas.append('Parametros: TIPO_PEDIDO=%s, HORAS_ATRAS=%d, NUM_OLEADAS=%d, NUM_ZONAS=%d, ZONAS=%s'
              % (TIPO_PEDIDO, HORAS_ATRAS, NUM_OLEADAS, NUM_ZONAS, ZONAS_FIJAS and 'fijas' or 'equilibradas esta noche'))

# ---------------- Requisitos del circuito SORTER -----------------------------
lineas.append('')
lineas.append('REQUISITOS')
sorter = env['stock.location'].search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)
stock_loc = env['stock.location'].search([('barcode', '=', 'EFFEC-STOCK'), ('company_id', '=', COMPANY_ID)], limit=1)
tipo_int = env['stock.picking.type'].search([('barcode', '=', 'EFFEC-INTERNAL'), ('company_id', '=', COMPANY_ID)], limit=1)
lineas.append('   Ubicacion SORTER: %s' % (sorter.complete_name or 'NO EXISTE'))
lineas.append('   Ubicacion EFFEC-STOCK: %s' % (stock_loc.complete_name or 'NO EXISTE'))
lineas.append('   Tipo de operacion EFFEC-INTERNAL: %s' % (tipo_int.display_name or 'NO EXISTE'))
for i in range(NUM_OLEADAS):
    nombre_u = 'U%d' % (i + 1)
    sub = sorter and env['stock.location'].search([('location_id', '=', sorter.id), ('name', '=', nombre_u)], limit=1)
    lineas.append('   Sububicacion %s/%s: %s' % (sorter.complete_name or 'SORTER', nombre_u, sub and 'existe' or 'habria que crearla'))

# ---------------- 1. OUT candidatas ------------------------------------------
candidatos = Picking.search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('state', 'in', ['confirmed', 'waiting', 'assigned']),
    ('create_date', '>=', desde_txt),
], order='name asc')
tiendas = {}
descartadas = 0
motivos = {}
oleadas_existentes = {}
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
    uds = sum(p.move_line_ids.mapped('product_uom_qty'))
    if uds <= 0:
        descartadas += 1
        motivos['sin nada reservado (%s)' % p.state] = motivos.get('sin nada reservado (%s)' % p.state, 0) + 1
        continue
    if p.state != 'assigned':
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

# ---------------- 2. Oleadas equilibradas ------------------------------------
oleadas = []
for i in range(NUM_OLEADAS):
    oleadas.append({'num': i + 1, 'tiendas': [], 'uds': 0.0, 'outs': 0})
for t in sorted(tiendas.values(), key=lambda x: (-x['uds'], x['nombre'])):
    o = sorted(oleadas, key=lambda x: (x['uds'], x['num']))[0]
    o['tiendas'].append(t)
    o['uds'] += t['uds']
    o['outs'] += len(t['outs'])

# ---------------- 3. Lineas por pasillo --------------------------------------
# pasillo = lineal // 2  (L1 -> 0, L2-L3 -> 1, ..., L136 -> 68)
uds_pasillo = {}
lineas_sin_l = 0
uds_sin_l = 0.0
detalle = []   # (oleada, pasillo, lineal, ubicacion_id, uds)
for o in oleadas:
    for t in o['tiendas']:
        for p in t['outs']:
            for ml in p.move_line_ids:
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
                pasillo = lineal // 2
                uds_pasillo[pasillo] = uds_pasillo.get(pasillo, 0.0) + qty
                detalle.append((o['num'], pasillo, lineal, ml.location_id.id, qty))

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
    for k in uds_pasillo.keys():
        total_p += uds_pasillo[k]
    objetivo = NUM_ZONAS and total_p / NUM_ZONAS or total_p
    z = 1
    acumulado = 0.0
    inicio = None
    pasillos_ordenados = sorted(uds_pasillo.keys())
    for k in pasillos_ordenados:
        if inicio is None:
            inicio = k
        zona_de_pasillo[k] = z
        acumulado += uds_pasillo[k]
        if acumulado >= objetivo * z and z < NUM_ZONAS and k != pasillos_ordenados[-1]:
            rangos.append((z, max(1, inicio * 2), k * 2 + 1))
            z += 1
            inicio = None
    if inicio is not None:
        rangos.append((z, max(1, inicio * 2), pasillos_ordenados[-1] * 2 + 1))

# ---------------- 5. INT (oleada x zona) y cargas -----------------------------
matriz = {}      # (oleada, zona) -> {'uds', 'ubic': {}}
carga_zona = {}  # zona -> {'uds', 'ubic': {}}
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
    if zona not in carga_zona:
        carga_zona[zona] = {'uds': 0.0, 'ubic': {}}
    carga_zona[zona]['uds'] += item[4]
    carga_zona[zona]['ubic'][item[3]] = 1

# ----------------------------- MENSAJE ---------------------------------------
lineas.append('')
lineas.append('OUT pendientes: %d | de tienda simuladas: %d | descartadas: %d | tiendas: %d'
              % (len(candidatos), len(candidatos) - descartadas, descartadas, len(tiendas)))
lineas.append('Lineas reservadas sin lineal reconocible: %d (%d uds)' % (lineas_sin_l, uds_sin_l))
for k in sorted(motivos.keys()):
    lineas.append('   %s: %d OUT' % (k, motivos[k]))
for k in sorted(oleadas_existentes.keys()):
    lineas.append('   Ya estan en la oleada %s: %d OUT de tienda%s' % (k, oleadas_existentes[k], INCLUIR_YA_EN_OLEADA and ' (incluidas en la simulacion)' or ''))

lineas.append('')
lineas.append('ZONAS (una por PDA): lineales | uds | paradas (ubicaciones distintas)')
for r in rangos:
    c = carga_zona.get(r[0], {'uds': 0.0, 'ubic': {}})
    lineas.append('   Z%d: L%02d-L%02d | %d uds | %d paradas' % (r[0], r[1], r[2], c['uds'], len(c['ubic'])))
if fuera_zona:
    lineas.append('   Fuera de las zonas fijas: %d uds' % fuera_zona)

lineas.append('')
lineas.append('OLEADAS (una por U) e INT que se crearian (uds / paradas por zona)')
cabecera = '   %-8s %5s %4s %6s |' % ('Oleada', 'Tiend', 'OUT', 'Uds')
for r in rangos:
    cabecera += ' %-12s' % ('Z%d' % r[0])
lineas.append(cabecera)
for o in oleadas:
    fila = '   U%-7d %5d %4d %6d |' % (o['num'], len(o['tiendas']), o['outs'], o['uds'])
    for r in rangos:
        m = matriz.get((o['num'], r[0]))
        fila += ' %-12s' % (m and ('%d/%d' % (m['uds'], len(m['ubic']))) or '-')
    lineas.append(fila)
lineas.append('   (cada celda con datos = 1 INT hacia SORTER/U<n>; cada PDA hace su columna con un carro por U)')

lineas.append('')
lineas.append('TIENDAS POR OLEADA')
for o in oleadas:
    nombres = []
    for t in o['tiendas']:
        nombres.append('%s (%d)' % (t['nombre'], t['uds']))
    lineas.append('   U%d: %s' % (o['num'], ', '.join(nombres) or '-'))

texto_completo = '\n'.join(lineas)
log('KOROSHI SIMULACION OLEADAS ZONAS\n%s' % texto_completo)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... (%d lineas mas: ver Ajustes > Tecnico > Registros)' % (len(lineas) - MAX_LINEAS_MENSAJE)]
raise Warning('\n'.join(lineas))

# =============================================================================
# KOROSHI - SIMULACION DE ZONAS CON MINIMO DE 15 UDS POR OUT
#
# Diagnostico para Odoo 13 / accion de servidor. SOLO LECTURA.
# No crea oleadas, INT, cajas ni matriculas.
#
# Compara:
#   A) zonas equilibradas con todas las OUT;
#   B) zonas calculadas priorizando OUT de 15 uds o mas y metiendo las
#      OUT pequeñas en la zona mas cercana.
#
# Importante: una zona no debe crear una matricula. La matricula final debe
# crearse al cerrar la OUT. El informe separa tiempo de picking y numero de
# OUT pequeñas para comprobar este problema.
# =============================================================================

COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
HORAS_ATRAS = 24
MIN_UDS_OUT = 15
NUM_ZONAS = 5
T_UD_SEG = 4
T_PARADA_SEG = 20
UDS_HORA = 425
VOLUMEN_DEFECTO_L = 1.0
MAX_LINEAS_MENSAJE = 300

Picking = env['stock.picking']
ahora = datetime.datetime.utcnow()
desde_txt = (ahora - datetime.timedelta(hours=HORAS_ATRAS)).strftime('%Y-%m-%d %H:%M:%S')

def numero_lineal(location):
    texto = location or ''
    partes = texto.split('/')
    i = len(partes) - 1
    while i >= 0:
        parte = partes[i].strip()
        if ' - ' in parte:
            parte = parte.split(' - ', 1)[1].strip()
        if len(parte) > 1 and parte[0] == 'L' and parte[1].isdigit():
            numero = ''
            j = 1
            while j < len(parte) and parte[j].isdigit():
                numero += parte[j]
                j += 1
            if numero:
                return int(numero)
        i -= 1
    return 0

def texto_estado(picking):
    return picking.state or '-'

def volumen_producto(producto):
    volumen = getattr(producto, 'volume', 0.0) or 0.0
    if volumen > 0:
        return volumen, False
    return VOLUMEN_DEFECTO_L, True

def partir_zonas(pesos, numero_zonas):
    orden = sorted(pesos.keys())
    if not orden:
        return {}, []
    total = 0.0
    for pasillo in orden:
        total += pesos[pasillo]
    objetivo = total / numero_zonas if numero_zonas else total
    mapa = {}
    rangos = []
    zona = 1
    acumulado = 0.0
    inicio = orden[0]
    for pasillo in orden:
        mapa[pasillo] = zona
        acumulado += pesos[pasillo]
        if acumulado >= objetivo * zona and zona < numero_zonas and pasillo != orden[-1]:
            rangos.append((zona, inicio, pasillo))
            zona += 1
            inicio = pasillo + 1
    rangos.append((zona, inicio, orden[-1]))
    return mapa, rangos

def asignar_pasillo_a_rango(pasillo, rangos):
    if not rangos:
        return 1
    for rango in rangos:
        if rango[1] <= pasillo <= rango[2]:
            return rango[0]
    if pasillo < rangos[0][1]:
        return rangos[0][0]
    return rangos[-1][0]

def calcular_zonas(detalle, pesos, numero_zonas):
    mapa, rangos = partir_zonas(pesos, numero_zonas)
    estadisticas = {}
    for item in detalle:
        zona = mapa.get(item['pasillo'])
        if not zona:
            zona = asignar_pasillo_a_rango(item['pasillo'], rangos)
        if zona not in estadisticas:
            estadisticas[zona] = {'uds': 0.0, 'litros': 0.0, 'ubic': {}, 'outs': {}}
        estadisticas[zona]['uds'] += item['uds']
        estadisticas[zona]['litros'] += item['litros']
        estadisticas[zona]['ubic'][item['ubicacion_id']] = 1
        estadisticas[zona]['outs'][item['out_id']] = 1
    return estadisticas, rangos

def segundos_zona(estadistica):
    return estadistica['uds'] * T_UD_SEG + len(estadistica['ubic']) * T_PARADA_SEG

lineas = []
lineas.append('SIMULACION KOROSHI MINIMO %d UDS + VOLUMEN - SOLO LECTURA' % MIN_UDS_OUT)
lineas.append('Ventana: ultimas %d horas | %s UTC' % (HORAS_ATRAS, ahora.strftime('%d/%m/%Y %H:%M')))

estados = ['confirmed', 'waiting', 'assigned']
candidatos = Picking.search([
    ('company_id', '=', COMPANY_ID),
    ('picking_type_code', '=', 'outgoing'),
    ('state', 'in', estados),
    ('create_date', '>=', desde_txt),
], order='name asc')

outs = []
descartadas = 0
motivos = {}
detalle = []
pesos_todos = {}
pesos_grandes = {}
volumenes_faltantes = 0

for picking in candidatos:
    tipo = picking.sale_id and picking.sale_id.s_order_type_id and picking.sale_id.s_order_type_id.name or ''
    if tipo != TIPO_PEDIDO:
        descartadas += 1
        motivos['otro tipo: %s' % (tipo or 'sin tipo')] = motivos.get('otro tipo: %s' % (tipo or 'sin tipo'), 0) + 1
        continue
    solicitado = 0.0
    reservado = 0.0
    hecho = 0.0
    for move in picking.move_ids:
        solicitado += move.product_uom_qty or 0.0
        reservado += move.reserved_availability or 0.0
        hecho += move.quantity_done or 0.0
    disponible = max(reservado, hecho)
    if disponible <= 0:
        descartadas += 1
        motivos['sin unidades reservadas'] = motivos.get('sin unidades reservadas', 0) + 1
        continue
    out = {
        'id': picking.id,
        'name': picking.name,
        'tienda': picking.partner_id.name or '-',
        'solicitado': solicitado,
        'reservado': reservado,
        'hecho': hecho,
        'uds': disponible,
        'litros': 0.0,
        'lineas': 0,
        'ubic': {},
        'pequena': disponible < MIN_UDS_OUT,
    }
    for ml in picking.move_line_ids:
        uds = ml.product_uom_qty or ml.qty_done or 0.0
        if uds <= 0:
            continue
        lineal = numero_lineal(ml.location_id.complete_name or '')
        if not lineal:
            continue
        volumen, es_defecto = volumen_producto(ml.product_id)
        if es_defecto:
            volumenes_faltantes += 1
        litros = uds * volumen
        pasillo = int((lineal - 1) // 2) + 1
        out['litros'] += litros
        out['lineas'] += 1
        out['ubic'][ml.location_id.id] = 1
        item = {
            'out_id': picking.id,
            'pasillo': pasillo,
            'lineal': lineal,
            'ubicacion_id': ml.location_id.id,
            'uds': uds,
            'litros': litros,
            'pequena': out['pequena'],
        }
        detalle.append(item)
        pesos_todos[pasillo] = pesos_todos.get(pasillo, 0.0) + uds * T_UD_SEG + T_PARADA_SEG
        if not out['pequena']:
            pesos_grandes[pasillo] = pesos_grandes.get(pasillo, 0.0) + uds * T_UD_SEG + T_PARADA_SEG
    if out['lineas']:
        outs.append(out)

detalle_grandes = []
for item in detalle:
    if not item['pequena']:
        detalle_grandes.append(item)

zonas_actuales, rangos_actuales = calcular_zonas(detalle, pesos_todos, NUM_ZONAS)
zonas_propuestas, rangos_propuestas = calcular_zonas(detalle, pesos_grandes or pesos_todos, NUM_ZONAS)

lineas.append('')
lineas.append('RESUMEN DE PEDIDOS')
lineas.append('   OUT candidatas: %d | simuladas: %d | descartadas: %d | lineas con ubicacion: %d' %
              (len(candidatos), len(outs), descartadas, len(detalle)))
outs_grandes = 0
outs_pequenas = 0
uds_pequenas = 0.0
litros_pequenas = 0.0
for out in outs:
    if out['pequena']:
        outs_pequenas += 1
        uds_pequenas += out['uds']
        litros_pequenas += out['litros']
    else:
        outs_grandes += 1
lineas.append('   OUT >= %d uds: %d | OUT < %d uds: %d' %
              (MIN_UDS_OUT, outs_grandes, MIN_UDS_OUT, outs_pequenas))
lineas.append('   Unidades OUT pequenas: %d | volumen estimado OUT pequenas: %.1f litros' %
              (uds_pequenas, litros_pequenas))
lineas.append('   Datos de volumen ausentes: %d lineas usan %.1f litro/prenda de respaldo' %
              (volumenes_faltantes, VOLUMEN_DEFECTO_L))
for motivo in sorted(motivos.keys()):
    lineas.append('   %s: %d' % (motivo, motivos[motivo]))

def imprimir_zonas(titulo, zonas, rangos):
    lineas.append('')
    lineas.append(titulo)
    for rango in rangos:
        estadistica = zonas.get(rango[0], {'uds': 0.0, 'litros': 0.0, 'ubic': {}, 'outs': {}})
        segundos = segundos_zona(estadistica)
        lineas.append('   Z%d: pasillos %d-%d | %.0f uds | %.1f litros | %d ubicaciones | %d OUT | %.1f min' %
                      (rango[0], rango[1], rango[2], estadistica['uds'], estadistica['litros'],
                       len(estadistica['ubic']), len(estadistica['outs']), segundos / 60.0))

imprimir_zonas('A) ZONAS ACTUALES: todas las OUT', zonas_actuales, rangos_actuales)
imprimir_zonas('B) ZONAS PROPUESTAS: cortes priorizando OUT >= %d uds' % MIN_UDS_OUT,
               zonas_propuestas, rangos_propuestas)

tiempo_actual = 0.0
tiempo_propuesto = 0.0
max_actual = 0.0
max_propuesto = 0.0
for zona in zonas_actuales.values():
    tiempo = segundos_zona(zona)
    tiempo_actual += tiempo
    max_actual = max(max_actual, tiempo)
for zona in zonas_propuestas.values():
    tiempo = segundos_zona(zona)
    tiempo_propuesto += tiempo
    max_propuesto = max(max_propuesto, tiempo)

lineas.append('')
lineas.append('COMPARACION DE TIEMPO DE PICKING')
lineas.append('   Tiempo total de trabajo de zonas: %.1f h actuales / %.1f h propuestas' %
              (tiempo_actual / 3600.0, tiempo_propuesto / 3600.0))
lineas.append('   Tiempo de la zona critica: %.1f min actuales / %.1f min propuestas' %
              (max_actual / 60.0, max_propuesto / 60.0))
if max_actual:
    mejora = (max_actual - max_propuesto) * 100.0 / max_actual
    lineas.append('   Mejora estimada por equilibrio de recorrido: %.1f%%' % mejora)
lineas.append('   Estas cifras no incluyen pausas, esperas, empaquetado ni desplazamiento hasta SORTER.')

lineas.append('')
lineas.append('MATRICULAS Y CAJAS')
lineas.append('   OUT simuladas: %d | matriculas finales previstas si cada OUT lleva CJ: %d' % (len(outs), len(outs)))
lineas.append('   Las zonas no deben crear matriculas: deben usar carro/tote interno y crear CJ solo al cerrar la OUT.')
lineas.append('   Si se mantiene una caja CJ por OUT, el minimo de %d uds no elimina por si solo las cajas de 1-2 uds.' % MIN_UDS_OUT)
lineas.append('   El minimo sirve para evitar zonas y oleadas demasiado pequenas; el problema de matriculas requiere separar picking y empaquetado.')

lineas.append('')
lineas.append('RECOMENDACION PARA LA PRUEBA')
lineas.append('   1. Mantener OUT y pedido siempre vinculados.')
lineas.append('   2. Picar OUT pequenas en un tote de consolidacion, sin crear CJ durante el recorrido.')
lineas.append('   3. Crear la matricula CJ solamente al cerrar y validar cada OUT.')
lineas.append('   4. Comparar este resultado con tiempos reales de un turno.')

texto = '\n'.join(lineas)
log('KOROSHI SIMULACION MIN15 VOLUMEN\n%s' % texto)
if len(lineas) > MAX_LINEAS_MENSAJE:
    lineas = lineas[:MAX_LINEAS_MENSAJE] + ['', '... resto en Ajustes > Tecnico > Registros']
raise Warning('\n'.join(lineas))

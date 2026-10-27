# v9 (27/10/2026): lo de fuera de lineal (ZX) ya no lo hace una sola persona. El 27/10 la ZX tenia 401 uds y,
# como la hacia solo la zona que acababa antes, a las 13:00 no cabian 22 pedidos aunque las otras 7 personas
# acababan a las 9:30. Ahora la ZX se corta en trozos seguidos por ubicacion (ZX1, ZX2...) y cada trozo lo hace
# una de las personas que acaba antes su zona, llenando hasta HORA_FIN: entran todos los pedidos que caben en el
# tiempo de las 8 personas. Si basta una persona, la agrupacion se sigue llamando ZX.
# v8 (26/10/2026): la v7 con 8 zonas (PERSONAS = 8). En Odoo: accion "KOROSHI Partir OUT zonas v8 (8 zonas)" (id 1866).
# Empieza en DIAGNOSTICO: no escribe nada.
# =============================================================================
# KOROSHI - PARTIR LAS OUT DE TIENDA POR ZONAS PARA ACABAR A UNA HORA (una OUT por tienda y zona)
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
# Se ejecuta sin seleccion: busca sola las OUT de hoy.
#
# v7 (22/10/2026 11:14): UNA SOLA TANDA para que PERSONAS personas (una por zona) esten de
# HORA_INICIO a HORA_FIN (06:00-11:00) cogiendo sin parar: mete todos los pedidos que dan para
# ese tiempo, los parte todos a la vez y corta las zonas para que todas acaben a la vez (corte
# optimo, no a ojo). Lo que no cabe no se toca: queda pendiente para despues de HORA_FIN. Tiempos calibrados con el 22/10 (Z-2210, 5 zonas):
#   SEG_LECTURA por lectura (OUT + hueco + producto) y SEG_LINEAL por cada lineal que visita cada
#   OUT (recorrido). Con 5 personas de 06:00 a 11:00 caben unas 1.800-2.000 uds.
#
# 1. Coge las OUT de "PED. TIENDAS" creadas hoy (hora de Espana), Preparadas, sin ninguna unidad
#    leida, fuera de cualquier agrupacion que no sea la del dia (TIENDA...) y que no salgan del
#    SORTER.
# 2. Las ordena por NUMERO DE TIENDA (K1, K2, K3...) y, dentro de la tienda, por nombre de OUT.
# 3. Busca cuantas (en ese orden) caben: con el corte optimo en PERSONAS zonas, la zona mas larga tiene que
#    acabar antes de HORA_FIN, y lo que no tiene lineal (ZX) tiene que caber, en trozos, en el tiempo que les
#    sobra a las que acaban antes (v9).
# 4. Parte esas OUT por zonas como la v6: cada OUT se queda en su zona principal, por cada otra
#    zona una OUT nueva con sus movimientos y reservas. Una agrupacion por zona: Z-ddmm-D1...
#    (si ya hay Z-ddmm de hoy: Z-ddmm-R2-D1...). Nota: Z-ddmm-D3 | CAJA 05 | K34 ... | PEDIDO S-...
#
# MODO = 'DIAGNOSTICO' -> no escribe nada: ensena que entra, el reparto y la hora de fin por zona
# MODO = 'SIMULAR'     -> lo hace todo, comprueba y al final raise Warning (Odoo lo deshace)
# MODO = 'REAL'        -> lo hace de verdad (si alguna comprobacion falla, deshace todo)
#
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
MODO = 'DIAGNOSTICO'
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
PERSONAS = 8                     # una persona por zona = numero de zonas
MIN_UDS_PEDIDO = 15              # v10b: pedido con menos uds reservadas -> no se coge (queda pendiente)
HORA_INICIO = '08:00'            # cuando empieza el picking ('AHORA' = la hora actual)
HORA_FIN = '13:00'               # cuando tiene que estar acabado
RENDIMIENTO = 1.0                # 1.0 = ritmo del 22/10; 1.2 = un 20 % mas rapido (carros, etc.)
SEG_LECTURA = 52                 # segundos por lectura (OUT + hueco + producto), calibrado 22/10
SEG_LINEAL = 21                  # segundos por cada lineal que visita cada OUT, calibrado 22/10
TIENDAS_48H = [7, 24, 29, 37, 39, 40, 41, 43, 47, 49, 56, 57, 59, 60, 62, 63, 68, 76, 78, 79, 81]
ZONA_OTRAS = 'ZX'                # huecos sin lineal (fuera de lineal)
PREFIJO_AGRUPACION = 'TIENDA'    # agrupacion del dia en la que llegan las OUT: se aceptan
ZONA_HORARIA = 'Europe/Madrid'
IDS_PRUEBA = []                  # ids de OUT concretas para probar; vacio = busca las de hoy
# PRUEBA: con prueba_agrupacion = 'Z-2210-' en el contexto usa las OUT de esas agrupaciones como si
# estuvieran sin empezar (todas sus lineas, leidas o no) y fuerza DIAGNOSTICO: no escribe nada.
# -----------------------------------------------------------------------------

ctx = dict(env.context)
ctx['allowed_company_ids'] = [COMPANY_ID]
Picking = env['stock.picking'].with_context(ctx)
Move = env['stock.move'].with_context(ctx)
MoveLine = env['stock.move.line'].with_context(ctx)
Batch = env['stock.picking.batch'].with_context(ctx)

ahora_local = datetime.datetime.now(timezone(ZONA_HORARIA))
medianoche_local = timezone(ZONA_HORARIA).localize(datetime.datetime(ahora_local.year, ahora_local.month, ahora_local.day))
desde = medianoche_local.astimezone(timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S')
hoy = ahora_local.strftime('%d%m')


def minutos(hhmm):
    return int(hhmm.split(':')[0]) * 60 + int(hhmm.split(':')[1])


def reloj(mins):
    mins = int(round(mins))
    return '%d:%02d' % (mins // 60, mins % 60)


ini_min = HORA_INICIO == 'AHORA' and (ahora_local.hour * 60 + ahora_local.minute) or minutos(HORA_INICIO)
fin_min = minutos(HORA_FIN)
capacidad = (fin_min - ini_min) * 60.0          # segundos por persona
seg_lect = SEG_LECTURA / RENDIMIENTO
seg_lin = SEG_LINEAL / RENDIMIENTO

sorter = env['stock.location'].with_context(ctx).search([('barcode', '=', 'SORTER'), ('company_id', '=', COMPANY_ID)], limit=1)


def numero_k(nombre):
    if nombre[:1] != 'K':
        return 9999
    num = ''
    for ch in nombre[1:]:
        if ch.isdigit():
            num += ch
        else:
            break
    return num and int(num) or 9999


def lineal_de(ubicacion):
    segmentos = (ubicacion.complete_name or '').split('/')
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
            return num and int(num) or 0
    return 0


def particion(pesos, k):
    # Corta la lista de pesos (uno por pasillo, en orden) en k tramos seguidos minimizando el
    # tramo mas pesado. Devuelve (lista de pesos de cada tramo, lista de [desde, hasta) por tramo).
    n = len(pesos)
    if n == 0:
        return [], []
    if k > n:
        k = n
    pre = [0.0]
    for w in pesos:
        pre.append(pre[-1] + w)
    inf = 1e18
    dp = []
    corte = []
    for j in range(k + 1):
        dp.append([inf] * (n + 1))
        corte.append([0] * (n + 1))
    dp[0][0] = 0.0
    for j in range(1, k + 1):
        for i in range(j, n + 1):
            for t in range(j - 1, i):
                v = dp[j - 1][t]
                if pre[i] - pre[t] > v:
                    v = pre[i] - pre[t]
                if v < dp[j][i]:
                    dp[j][i] = v
                    corte[j][i] = t
    tramos = []
    i = n
    for j in range(k, 0, -1):
        t = corte[j][i]
        tramos.insert(0, [t, i])
        i = t
    tiempos = []
    for tr in tramos:
        tiempos.append(pre[tr[1]] - pre[tr[0]])
    return tiempos, tramos


def repartir_zx(tiempos, lista):
    # v9: lo de fuera de lineal (lista de (hueco, segundos), ordenada por ubicacion) se corta en trozos seguidos.
    # Empieza la persona que antes acaba su zona y coge huecos hasta llegar a HORA_FIN; sigue la siguiente.
    # Un hueco que no cabe entero en nadie va a quien acabe antes. Devuelve (duracion, [[zona, huecos, seg]]).
    total = 0.0
    claves = []
    for c in lista:
        total += c[1]
        claves.append(c[0])
    if not tiempos:
        return total, (lista and [[-1, claves, total]] or [])
    mayor = max(tiempos)
    pares_t = []
    for z in range(len(tiempos)):
        pares_t.append((tiempos[z], z))
    pares_t.sort()
    personas = []
    for par in pares_t:
        personas.append(par[1])
    carga = {}
    orden_t = []
    idx = 0
    for z in personas:
        if idx >= len(lista):
            break
        libre = capacidad - tiempos[z]
        cl = []
        seg = 0.0
        while idx < len(lista) and seg + lista[idx][1] <= libre + 0.001:
            cl.append(lista[idx][0])
            seg += lista[idx][1]
            idx += 1
        if cl:
            carga[z] = [cl, seg]
            orden_t.append(z)
    while idx < len(lista):
        mejor = personas[0]
        fin_mejor = 1e18
        for z in personas:
            f = tiempos[z] + (z in carga and carga[z][1] or 0.0)
            if f < fin_mejor:
                fin_mejor = f
                mejor = z
        if mejor not in carga:
            carga[mejor] = [[], 0.0]
            orden_t.append(mejor)
        carga[mejor][0].append(lista[idx][0])
        carga[mejor][1] += lista[idx][1]
        idx += 1
    dur = mayor
    trozos = []
    for z in orden_t:
        if tiempos[z] + carga[z][1] > dur:
            dur = tiempos[z] + carga[z][1]
        trozos.append([z, carga[z][0], carga[z][1]])
    return dur, trozos


# ---------------- 1. OUT candidatas -------------------------------------------
prueba_agr = env.context.get('prueba_agrupacion')
if prueba_agr:
    MODO = 'DIAGNOSTICO'
    PREFIJO_AGRUPACION = prueba_agr
    candidatas = Picking.search([('company_id', '=', COMPANY_ID), ('picking_type_code', '=', 'outgoing'),
                                 ('batch_id.name', '=like', prueba_agr + '%'), ('state', '!=', 'cancel')], order='name asc')
elif IDS_PRUEBA:
    candidatas = Picking.browse(IDS_PRUEBA).exists()
else:
    candidatas = Picking.search([
        ('company_id', '=', COMPANY_ID),
        ('picking_type_code', '=', 'outgoing'),
        ('state', '=', 'assigned'),
        ('sale_id.s_order_type_id.name', '=', TIPO_PEDIDO),
        ('create_date', '>=', desde),
    ], order='name asc')

validas = []
saltadas = []
for p in candidatas:
    motivo = ''
    tipo = p.sale_id and p.sale_id.s_order_type_id and p.sale_id.s_order_type_id.name or ''
    if p.company_id.id != COMPANY_ID or p.picking_type_code != 'outgoing':
        motivo = 'no es una OUT de la empresa %d' % COMPANY_ID
    elif tipo != TIPO_PEDIDO:
        motivo = 'tipo de pedido %s' % (tipo or 'sin tipo')
    elif p.state != 'assigned' and not prueba_agr:
        motivo = 'no esta Preparada (%s)' % p.state
    elif p.batch_id and not (p.batch_id.name or '').startswith(PREFIJO_AGRUPACION):
        motivo = 'esta en la agrupacion %s' % p.batch_id.name
    elif sorter and p.location_id.id == sorter.id:
        motivo = 'sale del SORTER'
    elif not prueba_agr:
        for ml in p.move_line_ids:
            if ml.qty_done > 0:
                motivo = 'ya tiene unidades leidas'
                break
            if sorter and ml.location_id.id == sorter.id:
                motivo = 'tiene lineas reservadas en el SORTER'
                break
    if motivo:
        saltadas.append('%s (%s): %s' % (p.name, p.partner_id.name or '', motivo))
        continue
    validas.append(p)

# ---------------- 2. Prioridad y coste de cada OUT por pasillo -----------------
info_ml = {}        # ml.id -> (pasillo o -1 si no tiene lineal, lineal)
coste_out = {}      # p.id -> {pasillo: segundos}
zx_out = {}         # p.id -> {hueco: segundos fuera de lineal}
uds_out = {}        # p.id -> uds reservadas
prio = []
for p in validas:
    knum = numero_k(p.partner_id.name or '')
    fecha = p.sale_id and p.sale_id.date_order and str(p.sale_id.date_order) or ''
    cp = {}
    zx = {}
    uds = 0.0
    vistos_lect = {}
    vistos_lin = {}
    for ml in p.move_line_ids:
        qty = ml.product_uom_qty
        if prueba_agr and ml.qty_done > qty:
            qty = ml.qty_done
        if qty <= 0:
            continue
        uds += qty
        lineal = lineal_de(ml.location_id)
        seg = 0.0
        clave_lect = (ml.location_id.id, ml.product_id.id)
        if clave_lect not in vistos_lect:
            vistos_lect[clave_lect] = 1
            seg += seg_lect
        if lineal:
            pasillo = lineal // 2
            if lineal not in vistos_lin:
                vistos_lin[lineal] = 1
                seg += seg_lin
            cp[pasillo] = cp.get(pasillo, 0.0) + seg
            info_ml[ml.id] = (pasillo, lineal, '')
        else:
            # cada unidad tiene su sububicacion (KO_/TT_): el hueco es la ubicacion padre. La clave lleva
            # tambien el articulo: un hueco muy grande (NAVE...) se puede repartir entre varias personas
            hueco = ml.location_id
            if (hueco.name or '')[:3] in ('KO_', 'TT_') and hueco.location_id:
                hueco = hueco.location_id
            clave_h = '%s | %s' % (hueco.complete_name or '', ml.product_id.default_code or ml.product_id.id)
            zx[clave_h] = zx.get(clave_h, 0.0) + seg
            info_ml[ml.id] = (-1, 0, clave_h)
    coste_out[p.id] = cp
    zx_out[p.id] = zx
    uds_out[p.id] = uds
    prio.append((knum, '', 0, p.name, p.id))      # orden por numero de tienda (K1, K2...)
prio.sort()
orden = []
for x in prio:
    orden.append(x[4])

# v10b (27/10/2026): nunca un pedido de menos de MIN_UDS_PEDIDO uds (reservadas): no se toca, queda pendiente
uds_por_pedido = {}
for p in validas:
    clave_p = p.origin or p.name
    uds_por_pedido[clave_p] = uds_por_pedido.get(clave_p, 0.0) + uds_out[p.id]
orden_ok = []
for pid in orden:
    q = Picking.browse(pid)
    if uds_por_pedido[q.origin or q.name] < MIN_UDS_PEDIDO:
        saltadas.append('%s (%s): pedido de %d uds (menos de %d)' % (
            q.name, q.partner_id.name or '', uds_por_pedido[q.origin or q.name], MIN_UDS_PEDIDO))
        continue
    orden_ok.append(pid)
orden = orden_ok


def evaluar(k):
    peso = {}
    zx = {}
    for pid in orden[:k]:
        for pa in coste_out[pid]:
            peso[pa] = peso.get(pa, 0.0) + coste_out[pid][pa]
        for h in zx_out[pid]:
            zx[h] = zx.get(h, 0.0) + zx_out[pid][h]
    pas = sorted(peso.keys())
    lista = []
    for pa in pas:
        lista.append(peso[pa])
    tiempos, tramos = particion(lista, PERSONAS)
    lista_zx = []
    for h in sorted(zx.keys()):
        lista_zx.append((h, zx[h]))
    dur, trozos = repartir_zx(tiempos, lista_zx)
    return dur, pas, tiempos, tramos, trozos


# ---------------- 3. Cuantas caben antes de HORA_FIN --------------------------
lo = 0
hi = len(orden)
while lo < hi:
    mid = (lo + hi + 1) // 2
    if evaluar(mid)[0] <= capacidad:
        lo = mid
    else:
        hi = mid - 1
n_entran = lo
dur, pasillos, tiempos, tramos, trozos_zx = evaluar(n_entran)
entran = orden[:n_entran]
no_entran = orden[n_entran:]

# Orden de las tiendas que entran: por numero de tienda (K1, K7...) y despues por nombre de OUT
pares = []
for p in Picking.browse(entran):
    pares.append((numero_k(p.partner_id.name or ''), p.name, p.id))
pares.sort()
elegidas = Picking.browse()
for par in pares:
    elegidas |= Picking.browse(par[2])

# Zonas por pasillo segun el corte optimo
zona_pas = {}
orden_zonas = []
for z in range(len(tramos)):
    nombre_z = 'D%d' % (z + 1)
    orden_zonas.append(nombre_z)
    for idx in range(tramos[z][0], tramos[z][1]):
        zona_pas[pasillos[idx]] = nombre_z
# v9: la ZX en trozos (ZX1, ZX2...; ZX si solo hay uno); hace_zx: zona ZX -> zona D que la hace
zona_hueco = {}
hace_zx = {}
for t in range(len(trozos_zx)):
    nombre_x = len(trozos_zx) > 1 and ('%s%d' % (ZONA_OTRAS, t + 1)) or ZONA_OTRAS
    orden_zonas.append(nombre_x)
    hace_zx[nombre_x] = trozos_zx[t][0] >= 0 and ('D%d' % (trozos_zx[t][0] + 1)) or ''
    for h in trozos_zx[t][1]:
        zona_hueco[h] = nombre_x

zona_ml = {}
n_lineas = 0
for p in elegidas:
    for ml in p.move_line_ids:
        if ml.id not in info_ml:
            continue
        n_lineas += 1
        pa = info_ml[ml.id][0]
        zona_ml[ml.id] = pa < 0 and zona_hueco[info_ml[ml.id][2]] or zona_pas[pa]

# Datos por zona: segundos, uds, OUT, lineales; quien hace ZX (la zona que acaba antes)
datos_zona = {}
for zn in orden_zonas:
    datos_zona[zn] = {'seg': 0.0, 'uds': 0.0, 'outs': {}, 'lmin': 9999, 'lmax': 0}
for z in range(len(tramos)):
    datos_zona['D%d' % (z + 1)]['seg'] = tiempos[z]
for t in range(len(trozos_zx)):
    datos_zona[orden_zonas[len(tramos) + t]]['seg'] = trozos_zx[t][2]
for ml_id in zona_ml:
    zn = zona_ml[ml_id]
    if zn.startswith(ZONA_OTRAS):
        continue
    lin = info_ml[ml_id][1]
    if lin < datos_zona[zn]['lmin']:
        datos_zona[zn]['lmin'] = lin
    if lin > datos_zona[zn]['lmax']:
        datos_zona[zn]['lmax'] = lin
zx_de = {}          # zona D -> segundos de ZX que hace al acabar la suya
for zn in hace_zx:
    if hace_zx[zn]:
        zx_de[hace_zx[zn]] = zx_de.get(hace_zx[zn], 0.0) + datos_zona[zn]['seg']

# Plan por OUT: uds por zona, zona principal y uds sin reserva
plan = []           # (p, uds por zona, principal, sin reserva, caja)
i = 0
for p in elegidas:
    uds_z = {}
    reservado = 0.0
    for ml in p.move_line_ids:
        if ml.id not in zona_ml:
            continue
        zn = zona_ml[ml.id]
        q = ml.product_uom_qty
        if prueba_agr and ml.qty_done > q:
            q = ml.qty_done
        uds_z[zn] = uds_z.get(zn, 0.0) + q
        reservado += q
        datos_zona[zn]['uds'] += q
        datos_zona[zn]['outs'][p.id] = 1
    demanda = 0.0
    for m in p.move_lines:
        if m.state not in ('done', 'cancel'):
            demanda += m.product_uom_qty
    principal = ''
    mejor = -1.0
    for zn in orden_zonas:
        if zn.startswith(ZONA_OTRAS):
            continue
        if uds_z.get(zn, 0.0) > mejor and uds_z.get(zn, 0.0) > 0:
            mejor = uds_z[zn]
            principal = zn
    if not principal:
        for zn in orden_zonas:
            if uds_z.get(zn, 0.0) > 0:
                principal = zn
                break
        principal = principal or orden_zonas[0]
    plan.append((p, uds_z, principal, demanda - reservado, i + 1))
    i += 1

# Nombre de la agrupacion: Z-ddmm- o, si ya hay de hoy, Z-ddmm-R2-, R3-...
existentes = Batch.search([('name', '=like', 'Z-%s-%%' % hoy)]).mapped('name')
prefijo = 'Z-%s-' % hoy
if existentes:
    n_r = 2
    hay = True
    while hay:
        hay = False
        for nb in existentes:
            if nb.startswith('Z-%s-R%d-' % (hoy, n_r)):
                hay = True
        if hay:
            n_r += 1
    prefijo = 'Z-%s-R%d-' % (hoy, n_r)
lote_de = {}
caja_de = {}
for p, uds_z, principal, sin_res, caja in plan:
    lote_de[p.id] = prefijo
    caja_de[p.id] = '%02d' % caja

# ---------------- Resumen del reparto ------------------------------------------
uds_entran = 0.0
for pid in entran:
    uds_entran += uds_out[pid]
uds_fuera = 0.0
for pid in no_entran:
    uds_fuera += uds_out[pid]
lineas = []
lineas.append('KOROSHI PARTIR OUT ZONAS v9 - %s' % MODO)
lineas.append('Objetivo: %d personas de %s a %s (%d min cada una) | ritmo x%.2f (%d s/lectura, %d s/lineal por OUT)' % (
    PERSONAS, reloj(ini_min), reloj(fin_min), (fin_min - ini_min), RENDIMIENTO, SEG_LECTURA, SEG_LINEAL))
lineas.append('OUT validas: %d (%d uds) | ENTRAN: %d (%d uds) | no entran (pendientes para despues): %d (%d uds) | saltadas %d' % (
    len(orden), uds_entran + uds_fuera, len(entran), uds_entran, len(no_entran), uds_fuera, len(saltadas)))
lineas.append('Acaba previsto: %s (la zona mas larga) | agrupaciones %s<zona>' % (reloj(ini_min + dur / 60.0), prefijo))
lineas.append('')
for zn in orden_zonas:
    d = datos_zona[zn]
    if zn.startswith(ZONA_OTRAS):
        if not d['uds']:
            continue
        lineas.append('Zona %s | fuera de lineal | %d uds | %d OUT | ~%d min (la hace %s al acabar la suya)' % (
            zn, d['uds'], len(d['outs']), round(d['seg'] / 60.0), hace_zx.get(zn) or '-'))
        continue
    tramo = d['lmax'] and ('L%d-L%d' % (d['lmin'], d['lmax'])) or 'sin lineas'
    fin_z = ini_min + d['seg'] / 60.0
    fin_z += zx_de.get(zn, 0.0) / 60.0
    lineas.append('Zona %s | %s | %d uds | %d OUT (cajas) | ~%d min | acaba ~%s' % (
        zn, tramo, d['uds'], len(d['outs']), round(d['seg'] / 60.0), reloj(fin_z)))
lineas.append('')
lineas.append('Caja | tienda | OUT | pedido | uds por zona (* = se queda la OUT original) | sin reserva')
n_nuevas_plan = 0
for p, uds_z, principal, sin_res, caja in plan:
    trozos = ''
    for zn in orden_zonas:
        if uds_z.get(zn, 0.0) > 0:
            marca = ''
            if zn == principal:
                marca = '*'
            else:
                n_nuevas_plan += 1
            trozos += '%s%s:%d  ' % (zn, marca, uds_z[zn])
    lineas.append('   %s %s%s | %s | %s | %s| %d' % (
        caja_de[p.id], p.partner_id.name or '', numero_k(p.partner_id.name or '') in TIENDAS_48H and ' (48h)' or '',
        p.name, p.origin or '', trozos, sin_res))
lineas.append('OUT nuevas que se crearan: %d' % n_nuevas_plan)
if no_entran:
    lineas.append('')
    lineas.append('NO ENTRAN (no se tocan, quedan pendientes): %d OUT, %d uds' % (len(no_entran), uds_fuera))
    for pid in no_entran[:40]:
        q = Picking.browse(pid)
        lineas.append('   %s | %s | %s | %d uds' % (q.partner_id.name or '', q.name, q.origin or '', uds_out[pid]))
    if len(no_entran) > 40:
        lineas.append('   ... y %d mas' % (len(no_entran) - 40))
if saltadas:
    lineas.append('')
    lineas.append('Saltadas (%d):' % len(saltadas))
    for s in saltadas[:40]:
        lineas.append('   %s' % s)
    if len(saltadas) > 40:
        lineas.append('   ... y %d mas' % (len(saltadas) - 40))

if not elegidas:
    lineas.append('')
    lineas.append('No entra ninguna OUT (o no hay OUT para partir).')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

if MODO == 'DIAGNOSTICO':
    lineas.append('')
    lineas.append('DIAGNOSTICO: no se ha escrito nada. Siguiente paso: MODO = SIMULAR.')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

# ---------------- 4. Partir (SIMULAR y REAL) -----------------------------------
lotes = {}
todas_out = Picking.browse()
out_de = {}         # (p.id, zona) -> OUT
uds_antes = {}
for p, uds_z, principal, sin_res, caja in plan:
    total_p = 0.0
    for m in p.move_lines:
        if m.state not in ('done', 'cancel'):
            total_p += m.product_uom_qty
    uds_antes[p.id] = total_p
    out_de[(p.id, principal)] = p
    for zn in orden_zonas:
        if zn == principal or uds_z.get(zn, 0.0) <= 0:
            continue
        nueva = p.copy({
            'move_lines': [],
            'move_line_ids': [],
            'package_level_ids': [],
            'batch_id': False,
            'backorder_id': False,
            'origin': p.origin,
        })
        out_de[(p.id, zn)] = nueva
    # Repartir cada movimiento segun la zona de sus lineas reservadas
    for m in p.move_lines:
        if m.state in ('done', 'cancel'):
            continue
        por_z = {}
        reservado_m = 0.0
        for ml in m.move_line_ids:
            if ml.id not in zona_ml:
                continue
            zn = zona_ml[ml.id]
            if zn not in por_z:
                por_z[zn] = [0.0, MoveLine.browse()]
            por_z[zn][0] += ml.product_uom_qty
            por_z[zn][1] = por_z[zn][1] | ml
            reservado_m += ml.product_uom_qty
        zs = []
        for zn in orden_zonas:
            if zn in por_z:
                zs.append(zn)
        if not zs:
            continue
        # El movimiento original se queda en la zona principal si tiene algo de ella o algo sin reserva
        if principal in zs or m.product_uom_qty - reservado_m > 0.001:
            guarda = principal
        else:
            guarda = zs[0]
        for zn in zs:
            if zn == guarda:
                continue
            destino = out_de[(p.id, zn)]
            nuevo = Move.browse(m._split(por_z[zn][0]))
            nuevo.write({'picking_id': destino.id})
            por_z[zn][1].write({'move_id': nuevo.id, 'picking_id': destino.id})
            nuevo._recompute_state()
        if guarda != principal:
            destino = out_de[(p.id, guarda)]
            m.write({'picking_id': destino.id})
            por_z[guarda][1].write({'picking_id': destino.id})
        m._recompute_state()
    # Agrupacion y nota de cada OUT de esta tienda
    for zn in orden_zonas:
        if (p.id, zn) not in out_de:
            continue
        o = out_de[(p.id, zn)]
        nl = lote_de[p.id] + zn
        if nl not in lotes:
            lotes[nl] = Batch.create({'name': nl, 'company_id': COMPANY_ID, 'batch_type': 'normal'})
        o.write({
            'batch_id': lotes[nl].id,
            'note': '%s | CAJA %s | %s | PEDIDO %s' % (nl, caja_de[p.id], p.partner_id.name or '', p.origin or ''),
        })
        todas_out |= o
for nl in lotes:
    lotes[nl].write({'state': 'in_progress'})
# v9: contadores de la lista de Transferencias (modulo stock_picking_date, no se recalculan solos): las OUT
# nuevas se copian con los del pedido entero y cada agrupacion parecia llevar ~600 uds (27/10)
for o in todas_out:
    dem_o = 0.0
    res_o = 0.0
    hecho_o = 0.0
    for m in o.move_lines:
        if m.state == 'cancel':
            continue
        dem_o += m.product_uom_qty
        res_o += m.reserved_availability
        hecho_o += m.quantity_done
    o.write({'count_demand': dem_o, 'count_reserve': res_o, 'count_done': hecho_o})

# ---------------- 5. Comprobaciones --------------------------------------------
fallos = []
n_no_cuadra = 0
despues = []
for p, uds_z, principal, sin_res, caja in plan:
    total_d = 0.0
    for zn in orden_zonas:
        if (p.id, zn) not in out_de:
            continue
        o = out_de[(p.id, zn)]
        res_o = 0.0
        for m in o.move_lines:
            if m.state not in ('done', 'cancel'):
                total_d += m.product_uom_qty
        for ml in o.move_line_ids:
            res_o += ml.product_uom_qty
            if zona_ml.get(ml.id, zn) != zn:
                fallos.append('%s (%s): linea de %s reservada en otra zona (%s)' % (
                    o.name, zn, ml.product_id.display_name, ml.location_id.complete_name))
        if zn != principal and abs(res_o - uds_z.get(zn, 0.0)) > 0.001:
            fallos.append('%s (%s): %d uds reservadas y deberian ser %d' % (o.name, zn, res_o, uds_z.get(zn, 0.0)))
        if o.state != 'assigned':
            fallos.append('%s (%s): estado %s' % (o.name, zn, o.state))
        despues.append('   %s | %s | %s | %d uds | %s' % (o.name, zn, o.state, res_o, o.batch_id.name or ''))
    if abs(total_d - uds_antes[p.id]) > 0.001:
        n_no_cuadra += 1
        fallos.append('%s %s: antes %d uds, despues %d' % (p.origin or '', p.name, uds_antes[p.id], total_d))

lineas.append('')
lineas.append('Despues de partir (OUT | zona | estado | uds reservadas | agrupacion):')
for d in despues:
    lineas.append(d)
lineas.append('OUT nuevas: %d | agrupaciones: %d | pedidos que no cuadran: %d | fallos: %d' % (
    len(todas_out) - len(plan), len(lotes), n_no_cuadra, len(fallos)))
if fallos:
    lineas.append('')
    lineas.append('FALLOS:')
    for f in fallos[:60]:
        lineas.append('   %s' % f)

if fallos:
    lineas.insert(0, 'NO SE HA HECHO NADA (se ha deshecho todo)')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

if MODO != 'REAL':
    lineas.append('')
    lineas.append('SIMULACION: al lanzar este aviso Odoo deshace todo. Para hacerlo de verdad: MODO = REAL.')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

lineas[0] = 'KOROSHI PARTIR OUT ZONAS v9 - HECHO'
log('\n'.join(lineas), level='info')
action = {
    'type': 'ir.actions.act_window',
    'name': 'OUT por zonas %s (%d OUT)' % (prefijo, len(todas_out)),
    'res_model': 'stock.picking',
    'view_mode': 'tree,form',
    'domain': [('id', 'in', todas_out.ids)],
    'target': 'current',
}

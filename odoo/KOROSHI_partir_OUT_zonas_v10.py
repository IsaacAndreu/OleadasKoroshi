# v10 (27/10/2026): menos cajas pequenas ("picos"). El 27/10 salieron 390 OUT de 4,9 uds de media (361 con menos
# de 15 uds). Tres cambios, con parametros:
#   - ENTERA_MENOS_DE: los pedidos con menos uds no se parten: una sola OUT que coge una persona entera
#     (agrupaciones T1, T2...; las hacen las personas que acaban antes, como la ZX).
#   - ZONAS: zonas de lineal (D1..), menos que personas: cada trozo de tienda lleva mas uds. Las personas que
#     no tienen zona (P5, P6...) hacen la ZX y los pedidos enteros.
#   - MIN_UDS_OUT: ningun trozo de tienda por debajo: se junta con la zona de al lado de esa tienda (la
#     persona de esa zona coge tambien esas pocas uds, unos lineales mas alla de su zona).
# Simulado con el 27/10 (35 uds / 4 zonas / 15 uds): 75 OUT de 25,6 uds en vez de 390 de 4,9.
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
PERSONAS = 8                     # personas cogiendo
ZONAS = 4                        # v10: zonas de lineal (D1..D4); las demas personas hacen ZX y pedidos enteros
ENTERA_MENOS_DE = 35             # v10: pedido con menos uds -> no se parte (una OUT, agrupacion T)
MIN_UDS_OUT = 15                 # v10: ningun trozo de tienda con menos uds: se junta con la zona de al lado
ZONA_ENTERAS = 'T'               # v10: agrupaciones de pedidos enteros (T1, T2...)
FACTOR_ENTERO = 1.25             # v10: un pedido entero cuesta mas por ud (tradicional 48 s/ud 23/10 vs zonas 38 s/ud 22/10)
AUTO = True                      # v10: prueba cada combinacion de ZONAS_PRUEBA x ENTERA_PRUEBA y se queda con la que
#   mete mas pedidos antes de HORA_FIN y, entre esas, la que hace menos cajas (ENTERA 100000 = todo tradicional)
ZONAS_PRUEBA = [2, 3, 4, 5, 6, 7, 8]
ENTERA_PRUEBA = [0, 25, 35, 50, 75, 100000]
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
uds_pas = {}        # v10: p.id -> {pasillo: uds}
uds_h = {}          # v10: p.id -> {hueco: uds fuera de lineal}
prio = []
for p in validas:
    knum = numero_k(p.partner_id.name or '')
    fecha = p.sale_id and p.sale_id.date_order and str(p.sale_id.date_order) or ''
    cp = {}
    zx = {}
    up = {}
    uh = {}
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
            up[pasillo] = up.get(pasillo, 0.0) + qty
            info_ml[ml.id] = (pasillo, lineal, '')
        else:
            # cada unidad tiene su sububicacion (KO_/TT_): el hueco es la ubicacion padre. La clave lleva
            # tambien el articulo: un hueco muy grande (NAVE...) se puede repartir entre varias personas
            hueco = ml.location_id
            if (hueco.name or '')[:3] in ('KO_', 'TT_') and hueco.location_id:
                hueco = hueco.location_id
            clave_h = '%s | %s' % (hueco.complete_name or '', ml.product_id.default_code or ml.product_id.id)
            zx[clave_h] = zx.get(clave_h, 0.0) + seg
            uh[clave_h] = uh.get(clave_h, 0.0) + qty
            info_ml[ml.id] = (-1, 0, clave_h)
    coste_out[p.id] = cp
    zx_out[p.id] = zx
    uds_out[p.id] = uds
    uds_pas[p.id] = up
    uds_h[p.id] = uh
    prio.append((knum, '', 0, p.name, p.id))      # orden por numero de tienda (K1, K2...)
prio.sort()
orden = []
for x in prio:
    orden.append(x[4])

# v10: pedido de cada OUT (en la prueba con agrupaciones ya partidas, un pedido son varias OUT) y sus uds
ped_de = {}
uds_ped = {}
for p in validas:
    ped_de[p.id] = p.origin or p.name
    uds_ped[ped_de[p.id]] = uds_ped.get(ped_de[p.id], 0.0) + uds_out[p.id]


def es_entero(pid):
    return uds_ped[ped_de[pid]] < ENTERA_MENOS_DE


def evaluar(k):
    peso = {}
    zx = {}
    seg_ped = {}        # v10: pedidos enteros -> segundos de todo el pedido
    lista_ped = []
    for pid in orden[:k]:
        if es_entero(pid):
            pd = ped_de[pid]
            if pd not in seg_ped:
                seg_ped[pd] = 0.0
                lista_ped.append(pd)
            for pa in coste_out[pid]:
                seg_ped[pd] += coste_out[pid][pa] * FACTOR_ENTERO
            for h in zx_out[pid]:
                seg_ped[pd] += zx_out[pid][h] * FACTOR_ENTERO
            continue
        for pa in coste_out[pid]:
            peso[pa] = peso.get(pa, 0.0) + coste_out[pid][pa]
        for h in zx_out[pid]:
            zx[h] = zx.get(h, 0.0) + zx_out[pid][h]
    pas = sorted(peso.keys())
    lista = []
    for pa in pas:
        lista.append(peso[pa])
    tiempos, tramos = particion(lista, ZONAS)
    base = list(tiempos)
    while len(base) < PERSONAS:
        base.append(0.0)
    lista_zx = []
    for h in sorted(zx.keys()):
        lista_zx.append((h, zx[h]))
    dur1, trozos = repartir_zx(base, lista_zx)
    carga = list(base)
    for tr in trozos:
        if tr[0] >= 0:
            carga[tr[0]] += tr[2]
    lista_t = []
    for pd in lista_ped:
        lista_t.append((pd, seg_ped[pd]))
    dur2, trozos_t = repartir_zx(carga, lista_t)
    return max(dur1, dur2), pas, tiempos, tramos, trozos, trozos_t


def cuantas_caben():
    lo = 0
    hi = len(orden)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if evaluar(mid)[0] <= capacidad:
            lo = mid
        else:
            hi = mid - 1
    return lo


def juntar_chicos(uz):
    # v10: uz = {orden de zona: uds} de un pedido. Junta los trozos de menos de MIN_UDS_OUT con el de al lado que
    # menos uds tenga. Devuelve (trozos que quedan, uds juntadas)
    junt = 0.0
    while True:
        zs = []
        for z in uz:
            if uz[z] > 0:
                zs.append(z)
        zs.sort()
        if len(zs) < 2:
            return len(zs), junt
        chica = -1
        for idx in range(len(zs)):
            if uz[zs[idx]] < MIN_UDS_OUT and (chica < 0 or uz[zs[idx]] < uz[zs[chica]]):
                chica = idx
        if chica < 0:
            return len(zs), junt
        if chica == 0:
            destino = 1
        elif chica == len(zs) - 1:
            destino = chica - 1
        elif uz[zs[chica - 1]] <= uz[zs[chica + 1]]:
            destino = chica - 1
        else:
            destino = chica + 1
        junt += uz[zs[chica]]
        uz[zs[destino]] += uz[zs[chica]]
        uz[zs[chica]] = 0.0


def estimar_cajas(k):
    # v10: cajas (OUT por pedido y zona) que saldrian con los k primeros pedidos, sin partir nada
    res = evaluar(k)
    pas = res[1]
    tramos_e = res[3]
    zona_de_pas = {}
    for z in range(len(tramos_e)):
        for idx in range(tramos_e[z][0], tramos_e[z][1]):
            zona_de_pas[pas[idx]] = z
    zona_de_h = {}
    for t in range(len(res[4])):
        for h in res[4][t][1]:
            zona_de_h[h] = 100 + t
    uz_ped = {}
    enteros = {}
    for pid in orden[:k]:
        pd = ped_de[pid]
        if es_entero(pid):
            enteros[pd] = 1
            continue
        d = uz_ped.setdefault(pd, {})
        for pa in uds_pas[pid]:
            d[zona_de_pas[pa]] = d.get(zona_de_pas[pa], 0.0) + uds_pas[pid][pa]
        for h in uds_h[pid]:
            d[zona_de_h[h]] = d.get(zona_de_h[h], 0.0) + uds_h[pid][h]
    cajas = len(enteros)
    junt = 0.0
    for pd in uz_ped:
        n_t, j = juntar_chicos(uz_ped[pd])
        cajas += n_t
        junt += j
    return cajas, junt, res[0]


# v10: AUTO: prueba las combinaciones y se queda con la mejor (mas pedidos dentro, menos cajas, acaba antes)
pruebas_auto = []
if AUTO:
    for zz in ZONAS_PRUEBA:
        if zz > PERSONAS:
            continue
        for ee in ENTERA_PRUEBA:
            ZONAS = zz
            ENTERA_MENOS_DE = ee
            k_p = cuantas_caben()
            cajas_p, junt_p, dur_p = estimar_cajas(k_p)
            pruebas_auto.append(((-k_p, cajas_p, dur_p), zz, ee, k_p, cajas_p, junt_p, dur_p))
    pruebas_auto.sort()
    ZONAS = pruebas_auto[0][1]
    ENTERA_MENOS_DE = pruebas_auto[0][2]


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
dur, pasillos, tiempos, tramos, trozos_zx, trozos_t = evaluar(n_entran)
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


def quien(z):
    # v10: persona z: las primeras tienen zona (D1..), las demas no (P5, P6...)
    if z < 0:
        return ''
    return z < len(tramos) and ('D%d' % (z + 1)) or ('P%d' % (z + 1))


# v9: la ZX en trozos (ZX1, ZX2...; ZX si solo hay uno); hace_zx: zona ZX/T -> persona que la hace
zona_hueco = {}
hace_zx = {}
for t in range(len(trozos_zx)):
    nombre_x = len(trozos_zx) > 1 and ('%s%d' % (ZONA_OTRAS, t + 1)) or ZONA_OTRAS
    orden_zonas.append(nombre_x)
    hace_zx[nombre_x] = quien(trozos_zx[t][0])
    for h in trozos_zx[t][1]:
        zona_hueco[h] = nombre_x
# v10: pedidos enteros en T1, T2... (una agrupacion por persona)
zona_ped = {}
for t in range(len(trozos_t)):
    nombre_t = len(trozos_t) > 1 and ('%s%d' % (ZONA_ENTERAS, t + 1)) or ZONA_ENTERAS
    orden_zonas.append(nombre_t)
    hace_zx[nombre_t] = quien(trozos_t[t][0])
    for pd in trozos_t[t][1]:
        zona_ped[pd] = nombre_t

zona_ml = {}
n_lineas = 0
for p in elegidas:
    for ml in p.move_line_ids:
        if ml.id not in info_ml:
            continue
        n_lineas += 1
        if es_entero(p.id):
            zona_ml[ml.id] = zona_ped[ped_de[p.id]]
            continue
        pa = info_ml[ml.id][0]
        zona_ml[ml.id] = pa < 0 and zona_hueco[info_ml[ml.id][2]] or zona_pas[pa]

# v10: ningun trozo de tienda con menos de MIN_UDS_OUT: se junta con la zona de al lado (en el orden D1, D2...,
# ZX...) que menos uds tenga de esa tienda, hasta que todos lleguen o quede un solo trozo
pos_zona = {}
for idx in range(len(orden_zonas)):
    pos_zona[orden_zonas[idx]] = idx
mls_ped = {}        # pedido -> {zona: [ml.id...]}
uds_pz = {}         # pedido -> {zona: uds}
for p in elegidas:
    if es_entero(p.id):
        continue
    pd = ped_de[p.id]
    if pd not in mls_ped:
        mls_ped[pd] = {}
        uds_pz[pd] = {}
    for ml in p.move_line_ids:
        if ml.id not in zona_ml:
            continue
        zn = zona_ml[ml.id]
        q = ml.product_uom_qty
        if prueba_agr and ml.qty_done > q:
            q = ml.qty_done
        mls_ped[pd].setdefault(zn, []).append(ml.id)
        uds_pz[pd][zn] = uds_pz[pd].get(zn, 0.0) + q
uds_juntadas = 0.0
for pd in mls_ped:
    while True:
        zs = []
        for zn in uds_pz[pd]:
            if uds_pz[pd][zn] > 0:
                zs.append((pos_zona[zn], zn))
        zs.sort()
        if len(zs) < 2:
            break
        chica = -1
        for idx in range(len(zs)):
            if uds_pz[pd][zs[idx][1]] < MIN_UDS_OUT and (chica < 0 or uds_pz[pd][zs[idx][1]] < uds_pz[pd][zs[chica][1]]):
                chica = idx
        if chica < 0:
            break
        if chica == 0:
            destino = 1
        elif chica == len(zs) - 1:
            destino = chica - 1
        elif uds_pz[pd][zs[chica - 1][1]] <= uds_pz[pd][zs[chica + 1][1]]:
            destino = chica - 1
        else:
            destino = chica + 1
        de = zs[chica][1]
        a = zs[destino][1]
        uds_juntadas += uds_pz[pd][de]
        uds_pz[pd][a] += uds_pz[pd][de]
        uds_pz[pd][de] = 0.0
        for ml_id in mls_ped[pd][de]:
            zona_ml[ml_id] = a
        mls_ped[pd].setdefault(a, []).extend(mls_ped[pd][de])
        mls_ped[pd][de] = []

# Datos por zona: segundos (v10: recalculados con el reparto final: lecturas y lineales de cada OUT en cada
# zona), uds, OUT y lineales
datos_zona = {}
for zn in orden_zonas:
    datos_zona[zn] = {'seg': 0.0, 'uds': 0.0, 'outs': {}, 'lmin': 9999, 'lmax': 0}
vistos_l = {}
vistos_n = {}
for p in elegidas:
    for ml in p.move_line_ids:
        if ml.id not in zona_ml:
            continue
        zn = zona_ml[ml.id]
        clave = (p.id, zn, ml.location_id.id, ml.product_id.id)
        if clave not in vistos_l:
            vistos_l[clave] = 1
            datos_zona[zn]['seg'] += seg_lect
        lin = info_ml[ml.id][1]
        if lin:
            if (p.id, zn, lin) not in vistos_n:
                vistos_n[(p.id, zn, lin)] = 1
                datos_zona[zn]['seg'] += seg_lin
            # tramo de la zona: solo sus lineales propios (no lo que se le ha juntado de la de al lado)
            zp = info_ml[ml.id][0] in zona_pas and zona_pas[info_ml[ml.id][0]] or ''
            if zp:
                if lin < datos_zona[zp]['lmin']:
                    datos_zona[zp]['lmin'] = lin
                if lin > datos_zona[zp]['lmax']:
                    datos_zona[zp]['lmax'] = lin
for zn in orden_zonas:
    if zn.startswith(ZONA_ENTERAS):
        datos_zona[zn]['seg'] = datos_zona[zn]['seg'] * FACTOR_ENTERO
zx_de = {}          # persona -> segundos de ZX y pedidos enteros que hace (despues de su zona, si tiene)
for zn in hace_zx:
    if hace_zx[zn]:
        zx_de[hace_zx[zn]] = zx_de.get(hace_zx[zn], 0.0) + datos_zona[zn]['seg']
dur = 0.0
for z in range(PERSONAS):
    nz = quien(z)
    s = (nz in datos_zona and nz.startswith('D')) and datos_zona[nz]['seg'] or 0.0
    s += zx_de.get(nz, 0.0)
    if s > dur:
        dur = s

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
lineas.append('KOROSHI PARTIR OUT ZONAS v10 - %s' % MODO)
lineas.append('Objetivo: %d personas de %s a %s (%d min cada una) | ritmo x%.2f (%d s/lectura, %d s/lineal por OUT)' % (
    PERSONAS, reloj(ini_min), reloj(fin_min), (fin_min - ini_min), RENDIMIENTO, SEG_LECTURA, SEG_LINEAL))
lineas.append('OUT validas: %d (%d uds) | ENTRAN: %d (%d uds) | no entran (pendientes para despues): %d (%d uds) | saltadas %d' % (
    len(orden), uds_entran + uds_fuera, len(entran), uds_entran, len(no_entran), uds_fuera, len(saltadas)))
lineas.append('Acaba previsto: %s (la zona mas larga) | agrupaciones %s<zona>' % (reloj(ini_min + dur / 60.0), prefijo))
lineas.append('Reparto: %d zonas de lineal | pedidos de menos de %s uds enteros | trozos de tienda de %d uds como minimo%s' % (
    ZONAS, ENTERA_MENOS_DE >= 100000 and 'TODOS (tradicional)' or ('%d' % ENTERA_MENOS_DE), MIN_UDS_OUT,
    AUTO and ' (elegido solo)' or ''))
if pruebas_auto:
    lineas.append('Opciones probadas (las 8 mejores): zonas | enteros si < uds | pedidos dentro | cajas | uds juntadas | acaba')
    for pr in pruebas_auto[:8]:
        lineas.append('   %d | %s | %d | %d | %d | %s' % (pr[1], pr[2] >= 100000 and 'todos' or pr[2], pr[3], pr[4], pr[5],
                                                    reloj(ini_min + pr[6] / 60.0)))
lineas.append('')
for zn in orden_zonas:
    d = datos_zona[zn]
    if zn.startswith(ZONA_OTRAS) or zn.startswith(ZONA_ENTERAS):
        if not d['uds']:
            continue
        lineas.append('Zona %s | %s | %d uds | %d OUT | ~%d min (la hace %s)' % (
            zn, zn.startswith(ZONA_OTRAS) and 'fuera de lineal' or 'pedidos enteros', d['uds'], len(d['outs']),
            round(d['seg'] / 60.0), hace_zx.get(zn) or '-'))
        continue
    tramo = d['lmax'] and ('L%d-L%d' % (d['lmin'], d['lmax'])) or 'sin lineas'
    fin_z = ini_min + d['seg'] / 60.0
    fin_z += zx_de.get(zn, 0.0) / 60.0
    lineas.append('Zona %s | %s | %d uds | %d OUT (cajas) | ~%d min | acaba ~%s' % (
        zn, tramo, d['uds'], len(d['outs']), round(d['seg'] / 60.0), reloj(fin_z)))
# v10: personas sin zona (hacen ZX y pedidos enteros)
for z in range(len(tramos), PERSONAS):
    nz = quien(z)
    hace = []
    for zn in orden_zonas:
        if hace_zx.get(zn) == nz and datos_zona[zn]['uds']:
            hace.append(zn)
    lineas.append('Persona %s (sin zona) | hace %s | ~%d min | acaba ~%s' % (
        nz, ', '.join(hace) or 'nada', round(zx_de.get(nz, 0.0) / 60.0), reloj(ini_min + zx_de.get(nz, 0.0) / 60.0)))
# v10: cajas (OUT por tienda y zona) que saldran
n_cajas = 0
n_chicas = 0
uds_cajas = 0.0
cajas_ped = {}
for p, uds_z, principal, sin_res, caja in plan:
    pd = ped_de[p.id]
    for zn in uds_z:
        if uds_z[zn] > 0:
            cajas_ped.setdefault(pd, {})
            cajas_ped[pd][zn] = cajas_ped[pd].get(zn, 0.0) + uds_z[zn]
for pd in cajas_ped:
    for zn in cajas_ped[pd]:
        n_cajas += 1
        uds_cajas += cajas_ped[pd][zn]
        if cajas_ped[pd][zn] < MIN_UDS_OUT:
            n_chicas += 1
n_enteros = len(zona_ped)
lineas.append('')
lineas.append('CAJAS: %d OUT (tienda x zona) de %.1f uds de media | con menos de %d uds: %d | pedidos enteros (< %d uds): %d | '
              'uds juntadas con la zona de al lado: %d (%d %%)' % (
                  n_cajas, n_cajas and uds_cajas / n_cajas or 0, MIN_UDS_OUT, n_chicas, ENTERA_MENOS_DE, n_enteros,
                  uds_juntadas, uds_cajas and round(100.0 * uds_juntadas / uds_cajas) or 0))
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

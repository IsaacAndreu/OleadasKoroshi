# v12f (10/11/2026): TODAS las zonas empiezan a la vez y acaban a la vez. El muelle (MU1 = N1-L.., MU2 = MU-xx)
#   tiene su propio equipo desde el principio: nadie hace su zona de lineal y luego se va al muelle. Las PERSONAS
#   se reparten entre las zonas segun el trabajo de cada una (minimo 1), para que todas acaben lo mas a la vez
#   posible. ZONAS = 5 (3 de lineal + MU1 + MU2).
# v12e (10/11/2026): el muelle (fuera de lineal) en 2 zonas FIJAS por ubicacion: MU1 = huecos N1-L.. y
#   MU2 = huecos MU-00..MU-14 (y cualquier otro fuera de lineal). Antes (v12d) salian ZX1, ZX2, ZX3 cortadas por
#   tiempo y, al cerrar cajas, se movian lineas entre ellas: las 3 recorrian todo el N1. Ahora no se mueven lineas
#   entre MU1 y MU2. Cada zona de muelle entera la hace el equipo de lineal que antes acaba.
# v12d (09/11/2026 17:30): ZONAS 6 -> 3 y horario 06:00-12:00 (antes 08:00-13:00). Prueba DIAGNOSTICO del 09/11
#   con los 62 pedidos de tiendas: 1-12 zonas dan 81-83% de cajas cerradas; 3 zonas = 590 cajas y acaba antes que 6 (607).
# v12 (08/11/2026): CAJA CERRADA POR OUT. Lo que manda en almacen: que las OUT no sean pequenas y que (casi)
# todas salgan en caja cerrada. Las cajas se llenan de una en una (se llena, se cierra, se abre otra), asi que una
# OUT esta en caja cerrada si su ULTIMA caja llega a CIERRE_MIN (80 %) de LITROS_CAJA.
#   - Por cada OUT de tienda, sus lineas en orden de recorrido se cortan por zona (como la v9c). Zona a zona, si un
#     trozo dejaria la ultima caja a medias, se mueven las lineas de la frontera: o EMPUJA sus ultimas lineas a la
#     zona siguiente o TIRA de las primeras de la siguiente hasta cerrar la caja (lo que mueva menos litros,
#     pesando la carga de cada zona). La persona camina unos lineales mas alla de su zona.
#   - Lo que sobra al final de la tienda (la ultima caja del pedido, que tampoco cerraria si lo cogiera una
#     sola persona entero) se pega a una OUT con cajas llenas: nunca queda una OUT pequena.
#   - Cajas por OUT = litros / LITROS_CAJA hacia arriba: lo mismo que cuenta la accion de etiquetas (1843).
#   - Despues de mover lineas se rehace el corte de zonas (ITER_EQUILIBRIO) para que sigan acabando a la vez.
#   - Cada linea reservada va entera a una zona: el partir (SIMULAR/REAL) es el de la v9c tal cual. La nota
#     de cada OUT lleva al final '| CAJAS n'.
#   Probado en Odoo con las 67 OUT de 05/10 + 12/10 (9.770 uds, 10 personas 06-22): ver informe de la v12.
# v11 (08/11/2026): cajas igual de llenas por OUT. Se descarto: medida con cajas llenadas de una en una seguia
#   dejando ultimas cajas a medias y desbordaba cajas con lineas enteras.
# Base: v9c (27/10/2026), la que hay en Odoo (accion 1866). La v9c ya traia: ZX repartida en trozos
# (v9), contadores (v9b) y minimo MIN_UDS_PEDIDO uds por pedido (v9c).
# =============================================================================
# KOROSHI - PARTIR LAS OUT DE TIENDA POR ZONAS EN CAJA CERRADA PARA ACABAR A UNA HORA
# Accion de servidor de Odoo 13. Modelo: stock.picking. Tipo: Ejecutar codigo Python.
# Se ejecuta sin seleccion: busca sola las OUT de hoy.
#
# 1. Coge las OUT de "PED. TIENDAS" creadas hoy (hora de Espana), Preparadas, sin ninguna unidad
#    leida, fuera de cualquier agrupacion que no sea la del dia (TIENDA...) y que no salgan del
#    SORTER. Pedidos de menos de MIN_UDS_PEDIDO uds: no se cogen.
# 2. Las ordena por NUMERO DE TIENDA (K1, K2, K3...) y, dentro de la tienda, por nombre de OUT.
# 3. Corte optimo en PERSONAS zonas (como la v9c); v12: mueve las lineas de frontera para que cada OUT de
#    zona salga en caja cerrada y calcula el tiempo de cada zona con lo que coge de verdad.
# 4. Busca cuantas OUT (en ese orden) caben antes de HORA_FIN. Lo que no cabe queda para otra tanda
#    (volver a lanzarla: agrupaciones Z-ddmm-R2-...).
#
# MODO = 'DIAGNOSTICO' -> no escribe nada: ensena que entra, las cajas, el reparto y la hora de fin por zona
# MODO = 'SIMULAR'     -> lo hace todo, comprueba y al final raise Warning (Odoo lo deshace)
# MODO = 'REAL'        -> lo hace de verdad (si alguna comprobacion falla, deshace todo)
#
# Reglas de safe_eval: sin f-strings, sin import, sin comprensiones, log() antes de raise.
# =============================================================================

# ----------------------------- PARAMETROS ------------------------------------
MODO = 'REAL'
COMPANY_ID = 8
TIPO_PEDIDO = 'PED. TIENDAS'
PERSONAS = 12                    # v12: TOTAL de personas cogiendo; se reparten igual entre las ZONAS (12 / 6 = 2 por zona)
ZONAS = 5                        # v12f: TOTAL de zonas: 3 de lineal + 2 de muelle (MU1, MU2). Menos zonas = menos OUT
MIN_UDS_PEDIDO = 15              # v9c: pedido con menos uds reservadas -> no se coge (queda pendiente)
HORA_INICIO = '06:00'            # cuando empieza el picking ('AHORA' = la hora actual)
HORA_FIN = '12:00'               # cuando tiene que estar acabado
RENDIMIENTO = 1.0                # 1.0 = ritmo del 22/10; 1.2 = un 20 % mas rapido (carros, etc.)
SEG_LECTURA = 52                 # segundos por lectura (OUT + hueco + producto), calibrado 22/10
SEG_LINEAL = 21                  # segundos por cada lineal que visita cada OUT, calibrado 22/10
TIENDAS_48H = [7, 24, 29, 37, 39, 40, 41, 43, 47, 49, 56, 57, 59, 60, 62, 63, 68, 76, 78, 79, 81]
LITROS_CAJA = 80.0               # v11: litros por caja 60x40x40 (el mismo que la accion de etiquetas 1843)
LITROS_TIPO = {'JA': 8.0, 'XC': 12.0, 'ZB': 14.0, 'SU': 4.0, 'TR': 3.7, 'CL': 3.0, 'PT': 2.2, 'PL': 2.1,
               'ML': 1.9, 'VS': 1.8, 'FA': 1.6, 'TP': 1.2, 'BL': 0.8, 'ZC': 0.6}
LITROS_DEFECTO = 3.0
CIERRE_MIN = 0.8                 # v12: una OUT esta en caja cerrada si su ultima caja llega a este % de LITROS_CAJA
PESO_CARGA = 2.0                 # v12: al cerrar cajas, cuanto pesa la carga de la zona que recibe las lineas
ITER_EQUILIBRIO = 4              # v12: veces que se rehace el corte de zonas para igualarlas despues de cerrar cajas
UNA_RONDA = True                 # v12: True = entran TODAS las OUT en la misma ronda (sin R2); el informe dice a que hora
                                 #   acabarian PERSONAS personas. False = solo las que caben antes de HORA_FIN
MIN_UDS_ZONAS = 2000             # v12: si entran menos uds, NO se parte nada por zonas (picking tradicional): solo avisa
ZONAS_MUELLE = 'AUTO'            # v12: de las ZONAS, cuantas son de fuera de lineal (muelle MU-01...), con su equipo fijo
                                 #   (ni ayudan en lineales ni los de lineales en el muelle). 0 = el muelle lo hacen los
                                 #   equipos que acaban antes su zona (como la v9). 'AUTO' = prueba 0, 1, 2... y se queda con
                                 #   el reparto que acaba antes
VER_OUT = 400                    # v11: cuantas OUT de tienda se listan en el informe
ZONA_OTRAS = 'MU'                # v12e: huecos sin lineal (fuera de lineal): zonas MU1, MU2
MUELLE_FIJO = [('1', '/N1-'), ('2', '')]   # v12e: zonas fijas del muelle (sufijo, texto en la ubicacion;
                                 #   '' = todo lo demas). [] = como la v12d (trozos por tiempo)
MUELLE_EQUIPO_PROPIO = True      # v12f: True = cada zona de muelle con su equipo desde el principio y las
                                 #   personas repartidas por trabajo (todas acaban a la vez). False = v12e
PREFIJO_AGRUPACION = 'TIENDA'    # agrupacion del dia en la que llegan las OUT: se aceptan
ZONA_HORARIA = 'Europe/Madrid'
IDS_PRUEBA = []                  # ids de OUT concretas para probar; vacio = busca las de hoy
# PRUEBA: con prueba_agrupacion = 'Z-2210-' en el contexto usa las OUT de esas agrupaciones como si
# estuvieran sin empezar (todas sus lineas, leidas o no) y fuerza DIAGNOSTICO: no escribe nada.
# v11: con prueba_ids = [ids de OUT] en el contexto hace lo mismo con esas OUT (pedidos enteros de otro dia).
PERSONAS = env.context.get('personas') or PERSONAS        # se puede pasar al lanzarla
HORA_INICIO = env.context.get('hora_inicio') or HORA_INICIO
HORA_FIN = env.context.get('hora_fin') or HORA_FIN
if 'una_ronda' in env.context:
    UNA_RONDA = env.context.get('una_ronda')
ZONAS = env.context.get('zonas') or ZONAS
if 'zonas_muelle' in env.context:
    ZONAS_MUELLE = env.context.get('zonas_muelle')
if ZONAS > PERSONAS:
    ZONAS = PERSONAS
POR_ZONA = float(PERSONAS) / ZONAS   # personas por zona: los tiempos de cada zona son de su equipo
if MUELLE_FIJO and MUELLE_EQUIPO_PROPIO:
    POR_ZONA = 1.0   # v12f: tiempos en segundos de UNA persona; luego se dividen por las personas de cada zona
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
seg_lect = SEG_LECTURA / RENDIMIENTO / POR_ZONA
seg_lin = SEG_LINEAL / RENDIMIENTO / POR_ZONA

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
prueba_ids = env.context.get('prueba_ids')
if prueba_ids:
    # v11: OUT concretas (aunque ya esten hechas) como si estuvieran sin empezar; fuerza DIAGNOSTICO
    MODO = 'DIAGNOSTICO'
    prueba_agr = 'IDS'
    PREFIJO_AGRUPACION = ''
    candidatas = Picking.browse(prueba_ids).exists()
elif prueba_agr:
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
qty_ml = {}         # v11: ml.id -> uds
seg_ml = {}         # v11: ml.id -> segundos que cuesta (lectura + lineal nuevo)
ml_rec = {}         # v11: ml.id -> linea reservada
mls_out = {}        # v11: p.id -> [ml.id] en uso
prio = []
for p in validas:
    knum = numero_k(p.partner_id.name or '')
    fecha = p.sale_id and p.sale_id.date_order and str(p.sale_id.date_order) or ''
    cp = {}
    zx = {}
    uds = 0.0
    vistos_lect = {}
    vistos_lin = {}
    mls_out[p.id] = []
    for ml in p.move_line_ids:
        qty = ml.product_uom_qty
        if prueba_agr and ml.qty_done > qty:
            qty = ml.qty_done
        if qty <= 0:
            continue
        uds += qty
        qty_ml[ml.id] = qty
        ml_rec[ml.id] = ml
        mls_out[p.id].append(ml.id)
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
        seg_ml[ml.id] = seg
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


def evaluar(k, wm):
    peso = {}
    zx = {}
    for pid in orden[:k]:
        for pa in coste_out[pid]:
            peso[pa] = peso.get(pa, 0.0) + coste_out[pid][pa] * wm.get(pa, 1.0)
        for h in zx_out[pid]:
            zx[h] = zx.get(h, 0.0) + zx_out[pid][h]
    pas = sorted(peso.keys())
    lista = []
    for pa in pas:
        lista.append(peso[pa])
    tiempos, tramos = particion(lista, ZONAS - ZONAS_MUELLE)
    lista_zx = []
    for h in sorted(zx.keys()):
        lista_zx.append((h, zx[h]))
    if ZONAS_MUELLE > 0 and not MUELLE_FIJO:   # v12f: con MUELLE_FIJO las zonas de muelle van por ubicacion
        # v12: lo de fuera de lineal (muelle MU-01...) son ZONAS_MUELLE zonas con equipo fijo, en trozos seguidos
        pesos_zx = []
        for c in lista_zx:
            pesos_zx.append(c[1])
        t_zx, tr_zx = particion(pesos_zx, ZONAS_MUELLE)
        dur = 0.0
        for t in tiempos:
            if t > dur:
                dur = t
        trozos = []
        for j in range(len(tr_zx)):
            claves = []
            for idx in range(tr_zx[j][0], tr_zx[j][1]):
                claves.append(lista_zx[idx][0])
            trozos.append([-1, claves, t_zx[j]])
            if t_zx[j] > dur:
                dur = t_zx[j]
        return dur, pas, tiempos, tramos, trozos
    if MUELLE_FIJO:
        # v12e: cada zona fija del muelle entera a la persona de lineal que antes acaba
        grupos_m = []
        for suf, txt in MUELLE_FIJO:
            grupos_m.append([suf, txt, [], 0.0])
        for c in lista_zx:
            g = grupos_m[-1]
            for gm in grupos_m:
                if gm[1] and gm[1] in c[0]:
                    g = gm
                    break
            g[2].append(c[0])
            g[3] += c[1]
        fin_p = list(tiempos)
        trozos = []
        for g in sorted(grupos_m, key=lambda x: -x[3]):
            if not g[2]:
                continue
            z = -1
            if fin_p and not MUELLE_EQUIPO_PROPIO:
                z = fin_p.index(min(fin_p))
                fin_p[z] += g[3]
            trozos.append([z, g[2], g[3], g[0]])
        trozos.sort(key=lambda x: x[3])
        dur = fin_p and max(fin_p) or sum([t[2] for t in trozos])
        return dur, pas, tiempos, tramos, trozos
    dur, trozos = repartir_zx(tiempos, lista_zx)
    return dur, pas, tiempos, tramos, trozos



# ---------------- 3. v12: OUT en cajas cerradas y zonas para las k primeras OUT ----
def cajas_de(litros):
    n = int(litros / LITROS_CAJA)
    if n * LITROS_CAJA < litros - 0.001:
        n += 1
    return max(1, n)


def cerrada(litros):
    # la OUT se coge llenando una caja, cerrandola y abriendo otra: esta en caja cerrada si la ULTIMA caja
    # llega a CIERRE_MIN (las anteriores van llenas)
    if litros <= 0.001:
        return True
    return litros - LITROS_CAJA * (cajas_de(litros) - 1) >= CIERRE_MIN * LITROS_CAJA - 0.001


def litros_ud(producto):
    v = (producto.volume or 0.0) * 1000.0
    if v <= 0:
        codigo = producto.default_code or ''
        v = LITROS_TIPO.get(codigo[4:6], LITROS_DEFECTO)
    return v


lit_cache = {}


def lit_ml(ml_id):
    if ml_id not in lit_cache:
        lit_cache[ml_id] = litros_ud(ml_rec[ml_id].product_id) * qty_ml[ml_id]
    return lit_cache[ml_id]


def litros_de(ml_ids):
    t = 0.0
    for x in ml_ids:
        t += lit_ml(x)
    return t


def segundos_de(ml_ids):
    t = 0.0
    for x in ml_ids:
        t += seg_ml[x]
    return t


def tiempo_grupo(ml_ids):
    # lo que tarda una persona en coger estas lineas para una OUT: lecturas (hueco + articulo) y lineales
    lect = {}
    lins = {}
    for x in ml_ids:
        ml = ml_rec[x]
        lect[(ml.location_id.id, ml.product_id.id)] = 1
        if info_ml[x][1]:
            lins[info_ml[x][1]] = 1
    return len(lect) * seg_lect + len(lins) * seg_lin


def repartir_personas(seg_z, zonas):
    # v12f: todas las zonas empiezan a la vez con su equipo fijo. Minimo 1 persona por zona; cada persona que
    # queda va a la zona que mas tardaria. Asi todas acaban lo mas a la vez posible.
    pers = {}
    for zn in zonas:
        pers[zn] = 1
    for i in range(PERSONAS - len(zonas)):
        peor = zonas[0]
        for zn in zonas:
            if seg_z[zn] / pers[zn] > seg_z[peor] / pers[peor]:
                peor = zn
        pers[peor] += 1
    return pers


def montar_una(k, wm):
    dur9, pasillos, tiempos, tramos, trozos_zx = evaluar(k, wm)
    pares = []
    for pid in orden[:k]:
        q = Picking.browse(pid)
        pares.append((numero_k(q.partner_id.name or ''), q.name, pid))
    pares.sort()
    pids = []
    for par in pares:
        pids.append(par[2])
    # Zonas por pasillo (corte optimo) y trozos de ZX, como la v9c
    zona_pas = {}
    orden_zonas = []
    obj_z = {}
    for z in range(len(tramos)):
        nombre_z = 'D%d' % (z + 1)
        orden_zonas.append(nombre_z)
        obj_z[nombre_z] = max(tiempos[z], 1.0)
        for idx in range(tramos[z][0], tramos[z][1]):
            zona_pas[pasillos[idx]] = nombre_z
    zona_hueco = {}
    hace_zx = {}
    for t in range(len(trozos_zx)):
        nombre_x = len(trozos_zx) > 1 and ('%s%d' % (ZONA_OTRAS, t + 1)) or ZONA_OTRAS
        if len(trozos_zx[t]) > 3:
            nombre_x = ZONA_OTRAS + trozos_zx[t][3]     # v12e: MU1, MU2 siempre con su numero
        orden_zonas.append(nombre_x)
        obj_z[nombre_x] = max(trozos_zx[t][2], 1.0)
        hace_zx[nombre_x] = trozos_zx[t][0] >= 0 and ('D%d' % (trozos_zx[t][0] + 1)) or ''
        for h in trozos_zx[t][1]:
            zona_hueco[h] = nombre_x
    pos_zona = {}
    for idx in range(len(orden_zonas)):
        pos_zona[orden_zonas[idx]] = idx
    zona_ml = {}
    for pid in pids:
        for x in mls_out[pid]:
            pa = info_ml[x][0]
            zona_ml[x] = pa < 0 and zona_hueco[info_ml[x][2]] or zona_pas[pa]
    # v12: por cada OUT de tienda, sus lineas en orden de recorrido cortadas por zona (trozos). Zona a zona: si el
    # trozo dejaria la ultima caja por debajo de CIERRE_MIN, o EMPUJA sus ultimas lineas a la zona siguiente o
    # TIRA de las primeras de la zona siguiente hasta cerrarla: lo que mueva menos litros (pesando la carga de la
    # zona que lo recibe). Son lineas de la frontera entre zonas: la persona camina unos lineales mas alla.
    # Lo que sobra al final de la tienda (su ultima caja, que tampoco cerraria cogiendo el pedido entero) se pega
    # al trozo anterior si es menos de una caja: nunca queda una OUT pequena.
    carga = {}
    for zn in orden_zonas:
        carga[zn] = 0.0
    grupos = {}         # (pid, zona) -> [ml.id]
    zona_fin = {}       # ml.id -> zona que la coge
    fuera = 0.0
    for pid in pids:
        rec = []
        for x in mls_out[pid]:
            ml = ml_rec[x]
            rec.append((pos_zona[zona_ml[x]], info_ml[x][0], info_ml[x][1],
                        ml.location_id.complete_name or '', ml.product_id.default_code or '', x))
        rec.sort()
        trozos = []     # [zona, [ml.id]] en orden de recorrido
        for r in rec:
            zn = zona_ml[r[5]]
            if not trozos or trozos[-1][0] != zn:
                trozos.append([zn, []])
            trozos[-1][1].append(r[5])
        # v12: lineales y fuera de lineal (muelle) son dos cadenas separadas: nunca se mueven lineas entre ellas
        cadenas = [[], []]
        cad_mu = {}     # v12e: con MUELLE_FIJO cada zona de muelle es su propia cadena (no se mueven lineas)
        for tz in trozos:
            if tz[0].startswith(ZONA_OTRAS):
                if MUELLE_FIJO:
                    if tz[0] not in cad_mu:
                        cad_mu[tz[0]] = []
                        cadenas.append(cad_mu[tz[0]])
                    cad_mu[tz[0]].append(tz)
                else:
                    cadenas[1].append(tz)
            else:
                cadenas[0].append(tz)
        for cadena in cadenas:
            cerrar_cadena(cadena, carga, obj_z)
        for tz in trozos:
            if not tz[1]:
                continue
            grupos[(pid, tz[0])] = tz[1]
            for x in tz[1]:
                zona_fin[x] = tz[0]
                if zona_ml[x] != tz[0]:
                    fuera += qty_ml[x]
    # Tiempo real de cada zona con lo que coge (lecturas y lineales de cada OUT de tienda en esa zona)
    seg_z = {}
    for zn in orden_zonas:
        seg_z[zn] = 0.0
    for clave in grupos:
        seg_z[clave[1]] += tiempo_grupo(grupos[clave])
    pers = {}
    if MUELLE_FIJO and MUELLE_EQUIPO_PROPIO and orden_zonas:
        pers = repartir_personas(seg_z, orden_zonas)
        for zn in orden_zonas:
            seg_z[zn] = seg_z[zn] / pers[zn]     # v12f: tiempo de la zona con su equipo
    zx_de = {}
    for zn in hace_zx:
        if hace_zx[zn]:
            zx_de[hace_zx[zn]] = zx_de.get(hace_zx[zn], 0.0) + seg_z[zn]
    fin = 0.0
    for zn in orden_zonas:
        if zn.startswith(ZONA_OTRAS):
            if not hace_zx.get(zn) and seg_z[zn] > fin:
                fin = seg_z[zn]
            continue
        if seg_z[zn] + zx_de.get(zn, 0.0) > fin:
            fin = seg_z[zn] + zx_de.get(zn, 0.0)
    return {'k': k, 'pids': pids, 'orden_zonas': orden_zonas, 'hace_zx': hace_zx, 'zx_de': zx_de,
            'zona_pas': zona_pas, 'zona_ml': zona_ml, 'zona_fin': zona_fin, 'grupos': grupos, 'seg_z': seg_z,
            'fin': fin, 'fuera': fuera, 'dur9': dur9, 'pers': pers}


def cerrar_cadena(trozos, carga, obj_z):
    # v12: trozos seguidos de una tienda ([zona, [ml.id]] en orden de recorrido): zona a zona cierra cajas moviendo
    # las lineas de la frontera; el resto final de menos de una caja se pega al trozo anterior
    if True:
        for i in range(len(trozos) - 1):
            tz = trozos[i]
            sig = trozos[i + 1]
            l_tz = litros_de(tz[1])
            if cerrada(l_tz):
                carga[tz[0]] += segundos_de(tz[1])
                continue
            # empujar: las ultimas lineas de este trozo pasan a la zona siguiente
            queda = list(tz[1])
            empuja = []
            l_q = l_tz
            while queda and not cerrada(l_q):
                x = queda.pop()
                l_q -= lit_ml(x)
                empuja.insert(0, x)
            # tirar: las primeras lineas de la zona siguiente pasan a esta
            coge = list(tz[1])
            resto = list(sig[1])
            tira = []
            l_c = l_tz
            while resto and not cerrada(l_c):
                x = resto.pop(0)
                l_c += lit_ml(x)
                coge.append(x)
                tira.append(x)
            c_emp = litros_de(empuja) * (1.0 + PESO_CARGA * (carga[sig[0]] + 1.0) / obj_z[sig[0]])
            c_tir = 1e18
            if cerrada(l_c):
                c_tir = litros_de(tira) * (1.0 + PESO_CARGA * (carga[tz[0]] + 1.0) / obj_z[tz[0]])
            if c_emp <= c_tir:
                tz[1] = queda
                sig[1] = empuja + sig[1]
            else:
                tz[1] = coge
                sig[1] = resto
            carga[tz[0]] += segundos_de(tz[1])
        con_lineas = []
        for tz in trozos:
            if tz[1]:
                con_lineas.append(tz)
        if len(con_lineas) > 1 and litros_de(con_lineas[-1][1]) < CIERRE_MIN * LITROS_CAJA:
            con_lineas[-2][1] = con_lineas[-2][1] + con_lineas[-1][1]
            con_lineas[-1][1] = []
        if con_lineas and con_lineas[-1][1]:
            carga[con_lineas[-1][0]] += segundos_de(con_lineas[-1][1])


def montar(k):
    # v12: mover lineas entre zonas para cerrar cajas desequilibra las zonas. Se repite el corte de zonas dando mas
    # peso a los pasillos de las zonas que han quedado largas (ITER_EQUILIBRIO veces) y se queda el que acaba antes.
    wm = {}
    mejor = None
    for it in range(ITER_EQUILIBRIO):
        r = montar_una(k, wm)
        if mejor is None or r['fin'] < mejor['fin']:
            mejor = r
        total = 0.0
        n_d = 0
        for zn in r['orden_zonas']:
            if not zn.startswith(ZONA_OTRAS):
                total += r['seg_z'][zn]
                n_d += 1
        if not n_d or total <= 0:
            break
        media = total / n_d
        nuevo = {}
        for pa in r['zona_pas']:
            zn = r['zona_pas'][pa]
            nuevo[pa] = wm.get(pa, 1.0) * ((r['seg_z'][zn] + 1.0) / media) ** 0.7
        wm = nuevo
    return mejor


# v12: cuantas de las ZONAS son de muelle (fuera de lineal)
if MUELLE_FIJO:
    ZONAS_MUELLE = MUELLE_EQUIPO_PROPIO and len(MUELLE_FIJO) or 0   # v12f: MU1, MU2 con equipo propio
if ZONAS_MUELLE == 'AUTO':
    hay_zx = False
    for pid in orden:
        if zx_out[pid]:
            hay_zx = True
            break
    mejor_m = 0
    if hay_zx and ZONAS > 1:
        mejor_d = 0.0
        for m in range(0, ZONAS):
            ZONAS_MUELLE = m
            d = evaluar(len(orden), {})[0]
            if m == 0 or d < mejor_d - 0.001:
                mejor_d = d
                mejor_m = m
    ZONAS_MUELLE = mejor_m
if ZONAS_MUELLE >= ZONAS:
    ZONAS_MUELLE = ZONAS - 1

# ---------------- 4. Cuantas caben antes de HORA_FIN (con las cajas cerradas) -----
lo = 0
hi = len(orden)
if UNA_RONDA:
    lo = hi             # v12: todo en la misma ronda; HORA_FIN solo sirve para el aviso de la hora de fin
while lo < hi:
    mid = (lo + hi + 1) // 2
    if montar(mid)['fin'] <= capacidad:
        lo = mid
    else:
        hi = mid - 1
R = montar(lo)
entran = orden[:lo]
no_entran = orden[lo:]
elegidas = Picking.browse(R['pids'])
orden_zonas = R['orden_zonas']
hace_zx = R['hace_zx']
zona_ml = R['zona_ml']
grupos = R['grupos']

# ---------------- 5. Plan por OUT y comparacion con la v9c ------------------------
datos_zona = {}
for zn in orden_zonas:
    datos_zona[zn] = {'seg': R['seg_z'][zn], 'uds': 0.0, 'cajas': 0, 'outs': {}, 'fuera': 0.0, 'lmin': 9999, 'lmax': 0}
plan = []           # (p, {zona: [cajas, uds, litros, cerrada]}, principal, sin reserva, numero de caja de tienda)
v9 = {'outs': 0, 'cerradas': 0, 'peq': 0}
v12 = {'outs': 0, 'cerradas': 0, 'cajas': 0, 'peq': 0, 'tiendas_resto': 0}
i = 0
for p in elegidas:
    por_z = {}
    for zn in orden_zonas:
        if (p.id, zn) not in grupos:
            continue
        mls_z = grupos[(p.id, zn)]
        l_z = litros_de(mls_z)
        u_z = 0.0
        for x in mls_z:
            u_z += qty_ml[x]
            if zona_ml[x] != zn:
                datos_zona[zn]['fuera'] += qty_ml[x]
            lin = info_ml[x][1]
            if lin and not zn.startswith(ZONA_OTRAS):
                if lin < datos_zona[zn]['lmin']:
                    datos_zona[zn]['lmin'] = lin
                if lin > datos_zona[zn]['lmax']:
                    datos_zona[zn]['lmax'] = lin
        por_z[zn] = [cajas_de(l_z), u_z, l_z, cerrada(l_z)]
        datos_zona[zn]['uds'] += u_z
        datos_zona[zn]['cajas'] += por_z[zn][0]
        datos_zona[zn]['outs'][p.id] = 1
        v12['outs'] += 1
        v12['cajas'] += por_z[zn][0]
        if por_z[zn][3]:
            v12['cerradas'] += 1
        if l_z < CIERRE_MIN * LITROS_CAJA:
            v12['peq'] += 1
    if not cerrada(litros_de(mls_out[p.id])):
        v12['tiendas_resto'] += 1
    # v9c: cada trozo de zona (por linea, sin mirar cajas)
    trozo = {}
    for x in mls_out[p.id]:
        zn = zona_ml[x]
        trozo[zn] = trozo.get(zn, 0.0) + lit_ml(x)
    for zn in trozo:
        v9['outs'] += 1
        if cerrada(trozo[zn]):
            v9['cerradas'] += 1
        if trozo[zn] < CIERRE_MIN * LITROS_CAJA:
            v9['peq'] += 1
    reservado = 0.0
    for x in mls_out[p.id]:
        reservado += qty_ml[x]
    demanda = 0.0
    for m in p.move_lines:
        if m.state not in ('done', 'cancel'):
            demanda += m.product_uom_qty
    principal = ''
    mejor = -1.0
    for zn in orden_zonas:
        if zn in por_z and por_z[zn][1] > mejor:
            mejor = por_z[zn][1]
            principal = zn
    plan.append((p, por_z, principal, demanda - reservado, i + 1))
    i += 1


def pct(a, b):
    return b and round(100.0 * a / b) or 0


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

# ---------------- Resumen ------------------------------------------------------
uds_entran = 0.0
for pid in entran:
    uds_entran += uds_out[pid]
uds_fuera = 0.0
for pid in no_entran:
    uds_fuera += uds_out[pid]
lineas = []
lineas.append('KOROSHI PARTIR OUT ZONAS v12 CAJA CERRADA - %s' % MODO)
lineas.append('Objetivo: %d personas en %d zonas (%d de lineal + %d de muelle, ~%.1f personas por zona) de %s a %s (%d min) | ritmo x%.2f (%d s/lectura, %d s/lineal por OUT)' % (
    PERSONAS, ZONAS, ZONAS - ZONAS_MUELLE, ZONAS_MUELLE, POR_ZONA, reloj(ini_min), reloj(fin_min), (fin_min - ini_min), RENDIMIENTO, SEG_LECTURA, SEG_LINEAL))
lineas.append('OUT validas: %d (%d uds) | ENTRAN: %d (%d uds) | no entran (pendientes para otra tanda): %d (%d uds) | saltadas %d' % (
    len(orden), uds_entran + uds_fuera, len(entran), uds_entran, len(no_entran), uds_fuera, len(saltadas)))
lineas.append('Acaba previsto: %s (la zona mas larga; con la v9c seria %s) | agrupaciones %s<zona>' % (
    reloj(ini_min + R['fin'] / 60.0), reloj(ini_min + R['dur9'] / 60.0), prefijo))
if R.get('pers'):
    # v12f: los tiempos de la v9c no valen con equipos distintos por zona; se quitan del resumen
    lineas[-1] = 'Acaba previsto: %s (la zona mas larga) | agrupaciones %s<zona>' % (reloj(ini_min + R['fin'] / 60.0), prefijo)
    lineas[1] = lineas[1].replace(', ~%.1f personas por zona' % POR_ZONA, ', personas segun el trabajo de cada zona')
    reparto_txt = []
    for zn in orden_zonas:
        reparto_txt.append('%s %d' % (zn, R['pers'][zn]))
    lineas.append('Personas por zona (todas empiezan a la vez): %s' % ', '.join(reparto_txt))
lineas.append('')
lineas.append('CAJA CERRADA (cajas de %d L; una OUT esta en caja cerrada si su ultima caja llega al %d%%):' % (
    LITROS_CAJA, round(CIERRE_MIN * 100)))
lineas.append('   v9c (zonas sin mirar cajas): %d OUT | en caja cerrada %d (%d%%) | OUT pequenas (menos de una caja): %d' % (
    v9['outs'], v9['cerradas'], pct(v9['cerradas'], v9['outs']), v9['peq']))
lineas.append('   v12 (caja cerrada):          %d OUT | en caja cerrada %d (%d%%) | OUT pequenas: %d | cajas %d, cerradas %d%%' % (
    v12['outs'], v12['cerradas'], pct(v12['cerradas'], v12['outs']), v12['peq'], v12['cajas'],
    pct(v12['cajas'] - (v12['outs'] - v12['cerradas']), v12['cajas'])))
lineas.append('   Tiendas cuyo pedido entero ya deja la ultima caja sin llenar: %d de %d (esa caja va en una de sus OUT)' % (
    v12['tiendas_resto'], len(plan)))
lineas.append('   %d uds se cogen fuera de su zona (lineas de la frontera movidas para cerrar cajas)' % R['fuera'])
lineas.append('')
for zn in orden_zonas:
    d = datos_zona[zn]
    if zn.startswith(ZONA_OTRAS):
        if not d['uds']:
            continue
        quien = hace_zx.get(zn) and ('la hace %s al acabar la suya' % hace_zx[zn]) or ('equipo fijo del muelle, acaba ~%s' % reloj(
            ini_min + d['seg'] / 60.0))
        lineas.append('Zona %s | fuera de lineal | %d uds | %d cajas | %d OUT | ~%d min (%s)' % (
            zn, d['uds'], d['cajas'], len(d['outs']), round(d['seg'] / 60.0), quien))
        if R.get('pers'):
            lineas[-1] += ' | %d personas' % R['pers'].get(zn, 0)
        continue
    tramo = d['lmax'] and ('L%d-L%d' % (d['lmin'], d['lmax'])) or 'sin lineas'
    fin_z = ini_min + (d['seg'] + R['zx_de'].get(zn, 0.0)) / 60.0
    lineas.append('Zona %s | %s | %d uds | %d cajas | %d OUT | %d uds de fuera | ~%d min | acaba ~%s' % (
        zn, tramo, d['uds'], d['cajas'], len(d['outs']), d['fuera'], round(d['seg'] / 60.0), reloj(fin_z)))
    if R.get('pers'):
        lineas[-1] += ' | %d personas' % R['pers'].get(zn, 0)
lineas.append('')
lineas.append('Caja | tienda | OUT | pedido | zona:cajas/uds (* = se queda la OUT original, ! = ultima caja sin llenar) | sin reserva')
n_nuevas_plan = 0
n_vistas = 0
for p, por_z, principal, sin_res, caja in plan:
    n_vistas += 1
    trozos = ''
    for zn in orden_zonas:
        if zn in por_z:
            marca = ''
            if zn == principal:
                marca = '*'
            else:
                n_nuevas_plan += 1
            if not por_z[zn][3]:
                marca += '!'
            trozos += '%s%s:%dc/%du  ' % (zn, marca, por_z[zn][0], por_z[zn][1])
    if n_vistas <= VER_OUT:
        lineas.append('   %02d %s%s | %s | %s | %s| %d' % (
            caja, p.partner_id.name or '', numero_k(p.partner_id.name or '') in TIENDAS_48H and ' (48h)' or '',
            p.name, p.origin or '', trozos, sin_res))
if len(plan) > VER_OUT:
    lineas.append('   ... y %d OUT mas' % (len(plan) - VER_OUT))
lineas.append('OUT nuevas que se crearian: %d' % n_nuevas_plan)
if no_entran:
    lineas.append('')
    lineas.append('NO ENTRAN (no se tocan, quedan para otra tanda): %d OUT, %d uds' % (len(no_entran), uds_fuera))
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

if uds_entran < MIN_UDS_ZONAS:
    lineas.insert(0, 'NO SE PARTE POR ZONAS: entran %d uds, menos de %d. Picking tradicional (OUT enteras). No se ha tocado nada.' % (
        uds_entran, MIN_UDS_ZONAS))
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

if MODO == 'DIAGNOSTICO':
    lineas.append('')
    lineas.append('DIAGNOSTICO v12: no se ha escrito nada. Siguiente paso: MODO = SIMULAR.')
    log('\n'.join(lineas), level='info')
    raise Warning('\n'.join(lineas))

# v12: a partir de aqui el partir de la v9c tal cual, con la zona final de cada linea (zona_fin) en vez de
# la zona de su pasillo. Cada linea reservada va entera a una zona: no se parte ninguna reserva.
zona_ml = R['zona_fin']
lote_de = {}
caja_de = {}
cajas_zona = {}     # (p.id, zona) -> cajas previstas
plan_v11 = plan
plan = []
for p, por_z, principal, sin_res, caja in plan_v11:
    uds_z = {}
    for zn in por_z:
        uds_z[zn] = por_z[zn][1]
        cajas_zona[(p.id, zn)] = por_z[zn][0]
    lote_de[p.id] = prefijo
    caja_de[p.id] = '%02d' % caja
    plan.append((p, uds_z, principal, sin_res, caja))

# ---------------- 6. Partir (SIMULAR y REAL), como la v9c -----------------------
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
            'note': '%s | CAJA %s | %s | PEDIDO %s | CAJAS %d' % (
                nl, caja_de[p.id], p.partner_id.name or '', p.origin or '', cajas_zona.get((p.id, zn), 0)),
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

# ---------------- 7. Comprobaciones --------------------------------------------
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

lineas[0] = 'KOROSHI PARTIR OUT ZONAS v12 CAJA CERRADA - HECHO'
log('\n'.join(lineas), level='info')
action = {
    'type': 'ir.actions.act_window',
    'name': 'OUT por zonas %s (%d OUT)' % (prefijo, len(todas_out)),
    'res_model': 'stock.picking',
    'view_mode': 'tree,form',
    'domain': [('id', 'in', todas_out.ids)],
    'target': 'current',
}
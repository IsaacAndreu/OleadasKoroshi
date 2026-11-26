# -*- coding: utf-8 -*-
# =============================================================================
# v1.8.0 (26/11/2026). Zonas que aprenden (bin/versiones/diseno-zonas-que-aprenden_2026-11-26.md). Python puro.
#
# 1) Ver que entra: que parte de las uds del reparto son articulos que van a casi todas las tiendas (dia de
#    implantacion) y cuales son. Solo texto en el informe: el reparto no cambia.
#    El 26/11 (6.192 uds) el 10 % eran 2621SU60 y 2621PL50 a 49 tiendas en L51-L52: D2 se quedo en L42-L79 y D3
#    se estiro de L70 a L136.
# 2) Aprender cada noche: segundos-persona reales de cada zona (lecturas de la PDA) contra su trabajo (lecturas y
#    lineales por OUT). Con varios dias sale el ritmo real del almacen (segundos por lectura y por lineal) para
#    proponerlo en la configuracion. No se aplica solo: lo aplica un jefe con un boton.
# =============================================================================

PCT_TIENDAS = 0.5           # articulo compartido: va al 50 % o mas de las tiendas del reparto
PCT_TIENDAS_CASI = 0.8      # ... casi todas
DIA_IMPLANTACION = 50.0     # % de uds en articulos compartidos para llamarlo dia de implantacion (memoria 23/10)
DIA_MIXTO = 5.0             # desde aqui se avisa de la parte de implantacion
VER_ARTICULOS = 8
HUECO_MAX = 600             # s: entre dos lecturas del mismo operario, mas de esto es pausa u otra tarea: no cuenta
MIN_FILAS = 6               # zonas-dia para proponer un ritmo


def modelo_de(codigo):
    """'2621SU60-000003-XL' -> '2621SU60-000003' (sin la talla). Sin guion: el codigo entero."""
    codigo = codigo or ''
    return '-' in codigo and codigo.rsplit('-', 1)[0] or codigo


def codigo_de_nombre(nombre):
    """El 26/11 las prendas nuevas (2621SU60, 2621PL50) no tenian referencia interna: el codigo va en el nombre,
    '[2621SU60-000003-L] 2621SU60-...' -> '2621SU60-000003-L'. Sin corchetes: la primera palabra."""
    nombre = (nombre or '').strip()
    if nombre.startswith('[') and ']' in nombre:
        return nombre[1:nombre.index(']')].strip()
    return nombre.split(' ')[0] if nombre else ''


def clasificar(rep):
    """Que entra en el reparto. rep: motor.modelo.Reparto listo. Devuelve {'tipo': 'reposicion'|'mixto'|'implantacion',
    'pct': % de uds en articulos que van a >= 50 % de las tiendas, 'pct_casi': >= 80 %, 'tiendas', 'uds',
    'articulos': [(modelo, uds, tiendas, lineal_min, lineal_max)] los de >= 80 %, de mas a menos uds}."""
    calc = rep.calc
    pids = rep.R['pids']
    tiendas_de = {}             # producto -> tiendas
    uds_de = {}
    codigo_de = {}
    lineales_de = {}
    todas = set()
    total = 0.0
    for pid in pids:
        tienda = calc.out_rec[pid].get('partner_name') or str(pid)
        todas.add(tienda)
        for x in calc.mls_out[pid]:
            ml = calc.ml_rec[x]
            prod = ml['product_id']
            q = calc.qty_ml[x]
            total += q
            tiendas_de.setdefault(prod, set()).add(tienda)
            uds_de[prod] = uds_de.get(prod, 0.0) + q
            codigo_de[prod] = ml.get('default_code') or codigo_de_nombre(ml.get('nombre')) or str(prod)
            lin = calc.info_ml[x][1]
            if lin:
                lineales_de.setdefault(prod, set()).add(lin)
    n = len(todas)
    if not n or not total:
        return {'tipo': 'reposicion', 'pct': 0.0, 'pct_casi': 0.0, 'tiendas': n, 'uds': total, 'articulos': []}
    comp = casi = 0.0
    por_modelo = {}
    for prod, ts in tiendas_de.items():
        if len(ts) >= n * PCT_TIENDAS:
            comp += uds_de[prod]
        if len(ts) >= n * PCT_TIENDAS_CASI:
            casi += uds_de[prod]
            m = por_modelo.setdefault(modelo_de(codigo_de[prod]), {'uds': 0.0, 'tiendas': set(), 'lin': set()})
            m['uds'] += uds_de[prod]
            m['tiendas'] |= ts
            m['lin'] |= lineales_de.get(prod, set())
    pct = round(100.0 * comp / total, 1)
    articulos = []
    for mod, m in sorted(por_modelo.items(), key=lambda kv: (-kv[1]['uds'], kv[0])):
        articulos.append((mod, m['uds'], len(m['tiendas']), m['lin'] and min(m['lin']) or 0,
                          m['lin'] and max(m['lin']) or 0))
    tipo = pct >= DIA_IMPLANTACION and 'implantacion' or pct >= DIA_MIXTO and 'mixto' or 'reposicion'
    return {'tipo': tipo, 'pct': pct, 'pct_casi': round(100.0 * casi / total, 1), 'tiendas': n, 'uds': total,
            'articulos': articulos}


def lineas_clasificar(cls):
    """Lineas 'TIPO DE DIA: ...' para el informe y el correo."""
    nombre = {'reposicion': 'REPOSICION', 'mixto': 'REPOSICION CON PARTE DE IMPLANTACION',
              'implantacion': 'IMPLANTACION'}[cls['tipo']]
    lineas = ['TIPO DE DIA: %s. %s %% de las uds en articulos que van a la mitad o mas de las %d tiendas (%s %% a '
              'casi todas).' % (nombre, _num(cls['pct']), cls['tiendas'], _num(cls['pct_casi']))]
    if cls['articulos']:
        partes = []
        for mod, uds, tiendas, lmin, lmax in cls['articulos'][:VER_ARTICULOS]:
            sitio = lmin and (lmin == lmax and 'L%d' % lmin or 'L%d-L%d' % (lmin, lmax)) or 'fuera de lineal'
            partes.append('%s %d uds a %d tiendas en %s' % (mod, uds, tiendas, sitio))
        mas = len(cls['articulos']) > VER_ARTICULOS and ' y %d mas' % (len(cls['articulos']) - VER_ARTICULOS) or ''
        lineas.append('TIPO DE DIA: a casi todas las tiendas: %s%s.' % ('; '.join(partes), mas))
        if cls['tipo'] != 'reposicion':
            lineas.append('TIPO DE DIA: si estan juntos en pocos lineales, la zona que los lleva sale corta y las de '
                          'al lado se estiran. Mejor cogerlos por articulo y repartirlos en las cajas.')
    return lineas


def _num(x):
    return ('%.1f' % x).replace('.', ',').replace(',0', '')


# ------------------------------------------------------------------ aprender el ritmo

def segundos_persona(lecturas):
    """lecturas: [(segundo, operario, zona)] de un dia (todas las de esos operarios, con zona '' si no es de una
    zona). Para cada operario, el tiempo entre dos lecturas seguidas (si es de HUECO_MAX o menos) se apunta a la
    zona de la segunda. Devuelve {zona: segundos-persona}. Lo de zona '' no se devuelve."""
    por_op = {}
    for seg, quien, zona in lecturas:
        por_op.setdefault(quien, []).append((seg, zona))
    res = {}
    for quien, ls in por_op.items():
        ls.sort()
        for i in range(1, len(ls)):
            hueco = ls[i][0] - ls[i - 1][0]
            if 0 <= hueco <= HUECO_MAX and ls[i][1]:
                res[ls[i][1]] = res.get(ls[i][1], 0.0) + hueco
    return res


def trabajo_zona(outs):
    """outs: {OUT: [(hueco, producto, lineal, uds)]} de una zona. Devuelve {'lecturas': hueco x producto distintos por
    OUT (como el motor), 'lineales_out': lineales distintos por OUT, sumados, 'uds', 'anchura': lineales distintos
    de la zona, 'lineal_min', 'lineal_max'}."""
    lect = lin_out = 0
    uds = 0.0
    todos = set()
    for lineas in outs.values():
        vistos = set()
        lins = set()
        for hueco, prod, lineal, q in lineas:
            if q <= 0:
                continue
            uds += q
            vistos.add((hueco, prod))
            if lineal:
                lins.add(lineal)
        lect += len(vistos)
        lin_out += len(lins)
        todos |= lins
    return {'lecturas': lect, 'lineales_out': lin_out, 'uds': uds, 'anchura': len(todos),
            'lineal_min': todos and min(todos) or 0, 'lineal_max': todos and max(todos) or 0}


def ajustar(filas):
    """filas: [(lecturas, lineales_out, segundos_persona)] de zonas-dia. Ajuste por minimos cuadrados (sin termino
    fijo, sin valores negativos) de segundos = a x lecturas + b x lineales_out. Devuelve {'seg_lectura': a,
    'seg_lineal': b, 'n', 'error_pct': error medio absoluto en %} o None si hay menos de MIN_FILAS."""
    filas = [f for f in filas if f[0] > 0 and f[2] > 0]
    if len(filas) < MIN_FILAS:
        return None
    s11 = sum(f[0] * f[0] for f in filas)
    s22 = sum(f[1] * f[1] for f in filas)
    s12 = sum(f[0] * f[1] for f in filas)
    s1y = sum(f[0] * f[2] for f in filas)
    s2y = sum(f[1] * f[2] for f in filas)
    det = s11 * s22 - s12 * s12
    a = b = None
    if abs(det) > 1e-9:
        a = (s1y * s22 - s2y * s12) / det
        b = (s2y * s11 - s1y * s12) / det
    if a is None or a < 0 or b < 0:
        # una sola variable: la que mejor explique
        a1 = s1y / s11
        b2 = s22 and s2y / s22 or 0.0
        e1 = sum(abs(f[2] - a1 * f[0]) for f in filas)
        e2 = sum(abs(f[2] - b2 * f[1]) for f in filas)
        a, b = (a1, 0.0) if e1 <= e2 or not s22 else (0.0, b2)
    err = sum(abs(f[2] - a * f[0] - b * f[1]) / f[2] for f in filas) / len(filas)
    return {'seg_lectura': round(a, 1), 'seg_lineal': round(b, 1), 'n': len(filas), 'error_pct': round(100 * err, 1)}


def error_con(filas, seg_lectura, seg_lineal):
    """Error medio (%) y sesgo (%: positivo = lo real tarda mas) de un ritmo dado sobre las filas."""
    filas = [f for f in filas if f[0] > 0 and f[2] > 0]
    if not filas:
        return None, None
    err = sum(abs(f[2] - seg_lectura * f[0] - seg_lineal * f[1]) / f[2] for f in filas) / len(filas)
    prev = sum(seg_lectura * f[0] + seg_lineal * f[1] for f in filas)
    real = sum(f[2] for f in filas)
    return round(100 * err, 1), round(100.0 * (real - prev) / prev, 1) if prev else None


def proponer(filas, seg_lectura, seg_lineal):
    """Ritmo propuesto para la configuracion. El ajuste da el PESO de cada cosa (lectura contra andar), pero los
    segundos-persona que se miden no cuentan pausas, cerrar cajas ni lo que no es leer (huecos de mas de HUECO_MAX):
    sus valores, tal cual, adelantarian la hora de fin. Por eso se escalan para que, en estas filas, el trabajo
    total sea el mismo que con el ritmo de ahora (que acierta la hora de fin: 19/11 previsto 9:49, real 9:31).
    Cambia el reparto de las fronteras (las zonas anchas pesan mas), no la hora de fin.
    Devuelve el ajuste con 'seg_lectura_prop', 'seg_lineal_prop', 'error_ahora', 'error_prop', 'sesgo_ahora'
    o None si no hay bastantes filas."""
    aj = ajustar(filas)
    if not aj:
        return None
    filas = [f for f in filas if f[0] > 0 and f[2] > 0]
    ahora = sum(seg_lectura * f[0] + seg_lineal * f[1] for f in filas)
    puro = sum(aj['seg_lectura'] * f[0] + aj['seg_lineal'] * f[1] for f in filas)
    k = puro and ahora / puro or 1.0
    res = dict(aj)
    res['seg_lectura_prop'] = round(aj['seg_lectura'] * k)
    res['seg_lineal_prop'] = round(aj['seg_lineal'] * k)
    res['error_ahora'], res['sesgo_ahora'] = error_con(filas, seg_lectura, seg_lineal)
    # error de la forma (sin la escala): el del ajuste puro
    res['error_prop'] = aj['error_pct']
    return res

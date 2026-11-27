# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Contenedores - lógica sin Odoo (se prueba con tests/test_logica.py, sin servidor).
# v1.13.0: repartir() dice cuántas uds de cada línea reservada pasan a Faltantes.
# =============================================================================
import re


def repartir(reservas, sobra, precision=0.001):
    """Cuántas uds quitar a cada línea reservada para que, en total, salgan `sobra` uds (lo reservado que no está).

    reservas: uds reservadas de cada línea, en el orden en que se quitan (las pequeñas primero: así una OUT pasa
    entera antes que partir dos).
    Devuelve una lista con lo que se quita a cada línea (0 = no se toca). Nunca más de lo que tiene la línea, ni
    más de `sobra` en total. Con sobra >= todo lo reservado («Poner a cero») se quitan todas enteras."""
    res = []
    queda = sobra
    for r in reservas:
        if queda <= precision or r <= precision:
            res.append(0.0)
            continue
        q = round(min(r, queda), 6)
        res.append(q)
        queda = round(queda - q, 6)
    return res


# -----------------------------------------------------------------------------
# v1.14.0 (R23): «Es otro» (cambiar artículo). Errores de talla: lo que Odoo llama A en el contenedor es B.
# -----------------------------------------------------------------------------
def modelo(nombre):
    """Modelo de un artículo por su nombre: la referencia sin la talla del final. En KOROSHI cada talla es un artículo
    (y una plantilla) aparte: 2621PT01-000014-34 y 2621PT01-000014-36 son el modelo 2621PT01-000014. Si el nombre no
    tiene esa forma (menos de dos guiones), el modelo es el nombre entero."""
    n = (nombre or '').strip().upper()
    if n.startswith('['):           # display_name: «[REF] nombre»
        n = n.split(']', 1)[-1].strip()
    if n.count('-') >= 2:
        return n.rsplit('-', 1)[0]
    return n


def mismo_modelo(nombre_a, nombre_b):
    """True si los dos artículos son el mismo modelo en otra talla."""
    a, b = modelo(nombre_a), modelo(nombre_b)
    return bool(a) and a == b


def error_uds_cambio(uds, actual, maximo):
    """Texto del error si no se pueden pasar `uds` de A a B ('' = se puede). actual = uds de A en el contenedor."""
    if uds is None or uds < 1:
        return 'Pon cuántas uds son del otro artículo (1 o más).'
    if uds > actual + 0.001:
        return 'Solo hay %s uds en el contenedor: no se pueden cambiar %s.' % (_n(actual), _n(uds))
    if uds > maximo:
        return 'Más de %d uds de una vez: revisa la cantidad.' % maximo
    return ''


def reservas_a_faltantes(uds, actual, reservadas):
    """Uds reservadas de A que pasan a Faltantes al cambiar `uds` de A a B: las que no caben en lo que queda de A."""
    return max(0.0, round(reservadas - (actual - uds), 6))


def _n(x):
    x = round(x or 0, 2)
    return ('%d' % x) if x == int(x) else ('%s' % x).replace('.', ',')


# -----------------------------------------------------------------------------
# v1.16.0: «Retirar cajas a 0» (ronda por lineal y hueco). Diseño aprobado por Isaac el 26/11:
# bin/versiones/diseno-compactacion-odoo-retirar-vacias-juntar-cajas_2026-11-26_v2.md, parte 1.
# -----------------------------------------------------------------------------
RANGO_LINEALES = (44, 136)          # zona 0: palés de L44 a L136
_RE_RANGO = re.compile(r'^\s*L?(\d{1,4})\s*-\s*L?(\d{1,4})\s*$', re.I)
_RE_LINEAL = re.compile(r'(?:^|\s)L(\d{1,4})(?=\s|$)', re.I)
_RE_P = re.compile(r'(?:^|\s)P(\d{1,4})(?=\s|$)', re.I)
_RE_C = re.compile(r'(?:^|\s)C(\d{1,3})(?=\s|$)', re.I)


def rango_lineales(texto):
    """«44-136» (o «L44-L136») -> (44, 136). Vacío o mal escrito: el de siempre (44, 136)."""
    m = _RE_RANGO.match(texto or '')
    if not m:
        return RANGO_LINEALES
    a, b = int(m.group(1)), int(m.group(2))
    return (a, b) if a <= b else (b, a)


def lineal_de(nombre_hueco):
    """Número del lineal sacado del nombre del hueco: «07828 - L67 P16 C1» -> 67. Sin lineal L (MU-01…) -> None."""
    m = _RE_LINEAL.search(nombre_hueco or '')
    return int(m.group(1)) if m else None


def orden_hueco(nombre_hueco):
    """Clave para ordenar los huecos como se recorren: lineal, P, C (números, no texto: P2 antes que P10)."""
    n = nombre_hueco or ''
    num = [int(m.group(1)) if m else 9999 for m in (_RE_LINEAL.search(n), _RE_P.search(n), _RE_C.search(n))]
    return tuple(num) + (n,)


def clasificar(activos, negativos, descuadres, abierta):
    """Estado de una caja para la ronda.
    activos = quants con cantidad o con reserva; negativos = quants con cantidad < 0; descuadres = quants con más
    reservado que cantidad; abierta = tiene líneas de movimiento sin hacer (IN, INT u OUT que salen o entran).
    'revisar': negativo o descuadre (solo Isaac, Betty y José Luis); 'stock': tiene prendas; 'abierta': a 0 pero con
    una recepción o un traslado sin validar (no se retira); 'cero': se puede retirar."""
    if negativos or descuadres:
        return 'revisar'
    if activos:
        return 'stock'
    if abierta:
        return 'abierta'
    return 'cero'


def ids_tarjetas(texto):
    """«12, 34; 56» -> {12, 34, 56}: ids de empleado (hr.employee) de un parámetro. Lo que no es número se ignora."""
    return {int(x) for x in re.findall(r'\d+', texto or '')}


def con_prendas_pendiente(ultima_marca, ultimo_cambio):
    """Una caja marcada «Tiene prendas» sigue pendiente si después no se ha hecho nada con su stock. Ids crecientes
    del registro (koroshi.contenedor.movimiento): la marca más nueva y el último cambio (añadir, cambiar, a cero…)."""
    if not ultima_marca:
        return False
    return not ultimo_cambio or ultima_marca > ultimo_cambio


def repartir_encontrados(uds, faltantes, precision=0.001):
    """Prendas leídas de un artículo en una caja «con prendas» y faltantes pendientes de ese artículo con vuelta a la
    caja o a su hueco [(id, cantidad)], en orden. Cada faltante se da por encontrado entero si las uds que quedan lo
    cubren (un faltante no se parte: marcar_encontrado lo devuelve entero). Devuelve (ids encontrados, uds que
    sobran = ajuste +)."""
    queda = uds
    usados = []
    for fid, cant in faltantes:
        if cant <= precision:
            continue
        if cant <= queda + precision:
            usados.append(fid)
            queda = round(queda - cant, 6)
    return usados, max(0.0, queda)


# -----------------------------------------------------------------------------
# v1.17.0: «Compactar» (fase 1): juntar cada modelo-color moviendo KO enteras y decir qué caja va abajo o arriba en la
# columna. Diseño v6 aprobado por Isaac el 26/11: bin/versiones/diseno-compactacion-odoo-retirar-vacias-juntar-cajas_
# 2026-11-26_v6.md. Hueco de Odoo = columna (C1–C4 son columnas); una columna = medio palé = 8 cajas (4 alto × 2 fondo).
# Las reglas de tallas por altura son las del programa de redistribución (redistrib/compactar.py, tallas_por_altura).
# -----------------------------------------------------------------------------
_RE_COLOR_ANTIGUO = re.compile(r'^\d{6}$')
RESTO_UDS = 2           # resto de talla: la talla tiene ≤ 2 uds ...
RESTO_PCT = 0.05        # ... o ≤ 5 % de la talla más fuerte del modelo-color (50 de la L y 2 de la XS)
MITAD_ABAJO = 0.5       # abajo, las tallas más pedidas hasta más o menos la mitad de las uds del modelo-color


def partir_codigo(default_code, nombre):
    """(modelo, color, talla) en mayúsculas, como el programa (redistrib/productos.py, partir_codigo).
    «2621JA67-NEGRO-M» -> ('2621JA67', 'NEGRO', 'M'). Referencia vacía o EAN: la primera palabra del nombre.
    Formato antiguo con color de 6 cifras en penúltimo lugar: «001-3-000003-36» -> ('001-3', '000003', '36')."""
    codigo = (default_code or '').strip()
    if not codigo or codigo.isdigit():
        codigo = (nombre or '').split(' ')[0].strip('[]') if nombre else codigo
    t = codigo.upper().split('-')
    if len(t) >= 4 and _RE_COLOR_ANTIGUO.match(t[-2]):
        return '-'.join(t[:-2]), t[-2], t[-1]
    return t[0], (t[1] if len(t) > 1 else ''), '-'.join(t[2:])


def mc_de(modelo, color):
    return '%s-%s' % (modelo, color) if color else modelo


def tallas_por_altura(stock, lineas):
    """Bandas de las tallas de UN modelo-color, como el programa. stock = {talla: uds en la zona 0};
    lineas = {talla: líneas de salida de 28 días}. Orden: por líneas (si no tiene ninguna, por stock). La primera
    talla, abajo; los restos (≤ 2 uds o ≤ 5 % de la más fuerte), «restos» (arriba del todo); las demás, abajo mientras
    abajo se acerque más a la mitad de las uds y, desde la primera que no, todo arriba.
    Devuelve {talla: 'abajo'|'arriba'|'restos'}."""
    stock = {t: u for t, u in (stock or {}).items() if u > 0}
    if not stock:
        return {}
    lt = {t: (lineas or {}).get(t, 0) for t in stock}
    por = lt if sum(lt.values()) else stock
    total = float(sum(stock.values()))
    fuerte = max(stock.values())
    orden = sorted(stock, key=lambda t: (-por[t], -stock[t], t))
    res, acum, lleno = {}, 0.0, False
    for i, t in enumerate(orden):
        resto = stock[t] < fuerte and (stock[t] <= RESTO_UDS or stock[t] <= RESTO_PCT * fuerte)
        if i == 0:
            a = 'abajo'
        elif resto:
            a = 'restos'
        elif not lleno and abs((acum + stock[t]) / total - MITAD_ABAJO) < abs(acum / total - MITAD_ABAJO):
            a = 'abajo'
        else:
            a, lleno = 'arriba', True
        if a == 'abajo':
            acum += stock[t]
        res[t] = a
    return res


def banda_caja(tallas_caja, bandas):
    """Banda de una caja: la de su talla principal (la que más uds tiene en la caja). tallas_caja = {talla: uds}.
    Los restos van arriba. Sin datos: arriba."""
    if not tallas_caja:
        return 'arriba'
    principal = sorted(tallas_caja.items(), key=lambda x: (-x[1], x[0]))[0][0]
    return 'abajo' if bandas.get(principal) == 'abajo' else 'arriba'


def clases_abc(lineas_mc, corte_a=0.8):
    """{mc: 'A'|'otra'}: A = los modelos-color que suman hasta el 80 % de las líneas (de más a menos)."""
    total = float(sum(lineas_mc.values()))
    res, acum = {}, 0.0
    for mc, n in sorted(lineas_mc.items(), key=lambda x: (-x[1], x[0])):
        res[mc] = 'A' if total and n > 0 and acum / total < corte_a else 'otra'
        acum += n
    return res


def plan_lineal(lineal, columnas, abc=None, capacidad=8, vaciar=4, distancia=2):
    """Plan de la fase 1 para un lineal: qué columnas se vacían y adónde va cada caja (KO entera).

    columnas: [{'id', 'nombre', 'lineal', 'z' (tiene algo de zona Z), 'extra' (cajas que ya llegarán: pasos
      pendientes de otros lineales), 'cajas': [{'id', 'mc', 'modelo', 'movible'}]}] del lineal y de los de alrededor.
    abc: {mc: 'A'|'otra'}. Lo de clase A, al destino del lineal con número más bajo (más cerca del muelle, que está
      antes de L01); lo demás, al más alto.
    Reglas (Isaac 26/11): se vacía una columna de zona 0 del lineal con menos de `vaciar` cajas solo si caben TODAS sus
    cajas; destino del mismo lineal o hasta ±distancia, sin pasar de `capacidad`, sin dos colores del mismo modelo, con
    las cajas del mismo modelo-color juntas (mejor donde ya está ese modelo-color); solo destinos que ya tienen cajas (a
    una columna vacía no se gana nada); una columna vaciada no recibe y una que recibe no se vacía. Primero las que se
    vacían moviendo menos cajas.
    Devuelve (pasos, resumen). pasos = [{'orden', 'origen_id', 'caja_id', 'destino_id', 'mc'}]."""
    abc = abc or {}
    ocup = {c['id']: len(c['cajas']) + (c.get('extra') or 0) for c in columnas}
    mcs = {c['id']: {} for c in columnas}            # columna -> {modelo: set(mc)}
    for c in columnas:
        for k in c['cajas']:
            mcs[c['id']].setdefault(k['modelo'], set()).add(k['mc'])
    origenes = [c for c in columnas if c['lineal'] == lineal and not c.get('z') and 0 < len(c['cajas']) < vaciar]
    origenes.sort(key=lambda c: (len(c['cajas']), orden_hueco(c['nombre'])))
    vaciadas, reciben = set(), set()
    pasos, sin_sitio = [], 0

    def candidatos(origen, mc, modelo, n, ocup_t, mcs_t):
        res = []
        for d in columnas:
            did = d['id']
            if did == origen['id'] or did in vaciadas or d.get('z') or abs(d['lineal'] - lineal) > distancia:
                continue
            if ocup_t[did] <= 0 or ocup_t[did] + n > capacidad:
                continue
            if mcs_t[did].get(modelo, set()) - {mc}:      # otro color del mismo modelo
                continue
            mismo = mc in mcs_t[did].get(modelo, set())
            cerca = d['lineal'] if abc.get(mc) == 'A' else -d['lineal']
            res.append(((0 if mismo else 1), cerca, -ocup_t[did], orden_hueco(d['nombre']), did))
        res.sort()
        return [r[-1] for r in res]

    for o in origenes:
        if o['id'] in reciben:
            continue
        if not all(k['movible'] for k in o['cajas']):
            sin_sitio += 1
            continue
        grupos = {}
        for k in o['cajas']:
            grupos.setdefault((k['modelo'], k['mc']), []).append(k)
        # tentativo: si un grupo no cabe, la columna no se vacía
        ocup_t = dict(ocup)
        mcs_t = {i: {m: set(s) for m, s in v.items()} for i, v in mcs.items()}
        asign, ok = [], True
        for (modelo, mc), ks in sorted(grupos.items(), key=lambda x: (-len(x[1]), x[0])):
            cand = candidatos(o, mc, modelo, len(ks), ocup_t, mcs_t)
            if not cand:
                ok = False
                break
            did = cand[0]
            ocup_t[did] += len(ks)
            mcs_t[did].setdefault(modelo, set()).add(mc)
            asign += [(k, did) for k in ks]
        if not ok:
            sin_sitio += 1
            continue
        ocup, mcs = ocup_t, mcs_t
        ocup[o['id']] = 0
        mcs[o['id']] = {}
        vaciadas.add(o['id'])
        for k, did in asign:
            reciben.add(did)
            pasos.append({'orden': len(pasos) + 1, 'origen_id': o['id'], 'caja_id': k['id'], 'destino_id': did,
                          'mc': k['mc']})
    resumen = {'columnas_lineal': len([c for c in columnas if c['lineal'] == lineal]),
               'candidatas': len(origenes), 'vaciadas': len(vaciadas), 'cajas': len(pasos), 'sin_sitio': sin_sitio}
    return pasos, resumen


def aviso_destino(destino_cajas, mc, modelo, n, capacidad=8):
    """v1.17.0: el operario deja la caja en otra columna (no la del plan): qué hay que avisar ('' = nada).
    destino_cajas = [(modelo, mc)] de las cajas que ya tiene."""
    avisos = []
    otros = sorted({c for m, c in destino_cajas if m == modelo and c != mc})
    if otros:
        avisos.append('ya tiene otro color del mismo modelo (%s)' % ', '.join(otros))
    if len(destino_cajas) + n > capacidad:
        avisos.append('pasaría de %d cajas (tendría %d)' % (capacidad, len(destino_cajas) + n))
    return '; '.join(avisos)

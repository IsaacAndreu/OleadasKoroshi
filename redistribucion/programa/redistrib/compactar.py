# -*- coding: utf-8 -*-
"""Compactación de la zona 0 (fase 2b, 26/11/2026). Funciones puras sobre la copia SQLite y el MASTER; no habla con
Odoo.

Dos partes:
1. Clasificación de cada modelo-color de la zona 0:
   - líneas de salida en `dias` días (pares distintos albarán–producto de las órdenes de entrega). Son líneas, no
     unidades: un artículo con mucha profundidad da muchas más líneas que uno con poca (criterio de Isaac, 26/11);
   - profundidad (uds en la nave) y tallas;
   - litros por unidad: los del MASTER (packing list) si el modelo está; si no, los de la copia (ficha o media de
     la familia), marcados;
   - uds por caja y tamaño con las reglas del MASTER v7 («Parámetros»): grande si caben < 15, pequeño si > 40;
   - ABC por líneas acumuladas: A hasta el 80 %, B hasta el 95 %, C el resto; «sin salidas» si no tiene líneas.
2. Propuesta de compactación: vaciar huecos poco llenos de la zona 0 metiendo sus cajas en otros huecos de la zona 0
   cercanos (mismo lineal o próximos), con estas reglas:
   - en un hueco compartido, modelos lo más distintos posible (otra familia, otro color) para que el picker los
     distinga rápido;
   - el mismo artículo no se mezcla: no se juntan dos colores del mismo modelo en un hueco (el mismo modelo-color sí,
     eso es juntar lo suyo);
   - restos de talla (pocas uds de una talla cuando el modelo-color tiene mucho más) y lo de clase C o sin salidas,
     al fondo (más metros); lo de clase A, lo más cerca posible;
   - un hueco solo se da por liberado si caben todas sus cajas; si no, no se toca.
   Orden de la lista: por beneficio, el hueco que se libera moviendo menos cajas primero.

En la zona de palés, C1–C4 de Odoo son COLUMNAS, no alturas (Isaac 26/11): cada columna tiene 4 alturas, 4 cajas de
alto. Hasta el 26/11 se trataba C1–C4 como alturas y lo de clase A solo iba a C1–C2; esa regla se ha quitado.
Las alturas no existen en Odoo (Isaac quiere cambiarlo): «abajo» son las alturas 1–2 de la columna y «arriba» la 3–4.

Capacidad de un hueco (una columna): 770 L calculados en Odoo (huecos llenos el 23/11), no medida física: FALTA
MEDIDA. Una caja ocupa al menos una caja entera: 84 L, confirmado por Isaac el 26/11 (el MASTER dice 93 L, por fuera).
"""
import collections
import dataclasses
import datetime
import math

from . import mapa_json

FALTA_MEDIDA = 'FALTA MEDIDA'


@dataclasses.dataclass
class ReglasCompactar:
    dias: int = 28
    corte_a: float = 0.80
    corte_b: float = 0.95
    litros_caja: float = 84.0            # confirmado por Isaac el 26/11
    grande_si_menos_de: int = 15         # uds por caja (MASTER v7, «Parámetros»)
    pequeno_si_mas_de: int = 40
    litros_hueco: float = 770.0          # medido en Odoo, no físico: FALTA MEDIDA
    llenado: float = 0.9                 # el destino no pasa del 90 %
    poco_lleno: float = 0.5              # candidato a vaciar si ocupa menos de la mitad
    distancia_lineales: int = 2          # destino en el mismo lineal o hasta 2 lineales más allá
    resto_uds: int = 2                   # resto de talla: la talla tiene ≤ 2 uds ...
    resto_pct: float = 0.05              # ... o ≤ 5 % de la talla más fuerte del modelo-color (50 L y 2 XS)
    litros_por_ud_sin_dato: float = 2.5
    lineales: tuple = (1, 136)
    altura_c1: float = 0.50              # tallas por altura dentro de la columna: abajo (alturas 1–2, el suelo es lo
                                         # cómodo: Isaac 26/11) las más pedidas hasta la mitad de las uds del
                                         # modelo-color; el resto arriba (3–4); los restos de talla arriba del todo.
                                         # Con un corte por líneas (60 %) abajo se llevaba el 74 % y no cabía (23/11)
    ko_sku_cajas: int = 3                # KO mixta (Isaac 26/11): un SKU con stock para 3 cajas o más lleva su KO;
                                         # las demás tallas del modelo-color comparten una KO por hueco
    primer_lineal_zona0: int = 44      # solo para contar huecos con solo cajas a 0 (sin zona propia): copia 23/11,
                                         # el 98,6 % de las uds de la 0 está de L44 en adelante (palés, Isaac 26/11)


def leer_master(ruta):
    """{modelo: litros por ud} de la hoja «MASTER por modelo» (cabecera con «Modelo» y «Litros / ud»)."""
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas = wb['MASTER por modelo'].iter_rows(values_only=True)
    col_mod = col_lt = None
    res = {}
    for f in filas:
        if col_mod is None:
            nombres = [str(c or '').replace('\n', ' ').strip() for c in f]
            if 'Modelo' in nombres and any(n.startswith('Litros / ud') for n in nombres):
                col_mod = nombres.index('Modelo')
                col_lt = next(i for i, n in enumerate(nombres) if n.startswith('Litros / ud'))
            continue
        mod, lt = f[col_mod], f[col_lt]
        if mod and isinstance(lt, (int, float)) and lt > 0:
            res[str(mod).strip()] = float(lt)
    wb.close()
    return res


def cargar(ruta_copia, carpeta_v2, master, r=ReglasCompactar()):
    """Cajas de cada hueco de la nave, con sus líneas (modelo-color, talla, uds, litros, zona), y las salidas."""
    G = mapa_json._geometria(carpeta_v2)
    bd = mapa_json.abrir_copia(ruta_copia)
    meta = dict(bd.execute('SELECT clave, valor FROM meta').fetchall())
    fecha = datetime.datetime.fromisoformat(meta['fecha_descarga'])
    ub = {f[0]: f for f in bd.execute('SELECT id, tipo, lineal, posicion, nivel, en_nave, hueco_id, nombre FROM ubicaciones')}
    prod = {f[0]: f for f in bd.execute('SELECT id, modelo, color, talla, familia, zona, litros FROM productos')}

    def litros_ud(p):
        if p[1] in master:
            return master[p[1]], 'MASTER'
        if p[6]:
            return p[6], 'copia'
        return r.litros_por_ud_sin_dato, 'sin dato'

    cajas = {}                                  # clave -> {'hueco', 'nombre', 'lineas': [...]}
    for loc, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock WHERE cantidad > 0'):
        u, p = ub.get(loc), prod.get(pid)
        if not u or not u[5] or not p:
            continue
        h = u if u[1] == 'hueco' else (ub.get(u[6]) if u[6] else None)
        if not h or h[1] != 'hueco' or not h[2] or not (r.lineales[0] <= h[2] <= r.lineales[1]):
            continue
        hueco = (h[2], h[3], h[4])
        mc = mapa_json.mc_de(p[1], p[2])
        clave = loc if u[1] == 'contenedor' else ('suelto', loc, mc)
        c = cajas.setdefault(clave, {'hueco': hueco, 'nombre': u[7] if u[1] == 'contenedor' else 'suelto', 'lineas': []})
        lt, fuente = litros_ud(p)
        c['lineas'].append({'mc': mc, 'modelo': p[1], 'talla': p[3] or '', 'familia': p[4] or '', 'uds': cant,
                            'litros': cant * lt, 'zona': p[5], 'fuente': fuente, 'lt_ud': lt})
    desde = (fecha - datetime.timedelta(days=r.dias)).strftime('%Y-%m-%d %H:%M:%S')
    lineas = collections.Counter()
    lineas_talla = collections.Counter()            # (modelo-color, talla) -> líneas
    uds_salida = collections.Counter()
    for pid, n, u in bd.execute(
            "SELECT s.producto_id, COUNT(DISTINCT s.albaran), SUM(s.cantidad) FROM salidas s "
            "JOIN tipos_operacion t ON t.id = s.tipo_operacion_id AND t.codigo = 'outgoing' "
            'WHERE s.fecha >= ? GROUP BY 1', (desde,)):
        p = prod.get(pid)
        if p:
            mc = mapa_json.mc_de(p[1], p[2])
            lineas[mc] += n
            lineas_talla[(mc, p[3] or '')] += n
            uds_salida[mc] += u
    bd.close()
    return {'cajas': cajas, 'lineas': lineas, 'lineas_talla': lineas_talla, 'uds_salida': uds_salida, 'fecha': fecha,
            'metros': G.metros_a_expedicion}


def cajas_a_cero(ruta_copia, datos, r=ReglasCompactar()):
    """Contenedores de la nave que en Odoo están a 0 (sin stock, o con stock que suma 0 o menos), por hueco.

    En la foto de L67 P16 C1 (26/11) había cajas a 0 que seguían en el palé, vacías y ocupando sitio. Isaac (26/11):
    «confirmar que están a 0 y retirarlas». Esta lista es para comprobarlas en la nave antes de retirarlas: una caja
    a 0 en Odoo puede tener prendas (la KO_090726_045 tenía una). La compactación no las cuenta, así que supone que
    ya se han retirado. Un contenedor con stock negativo no se da por vacío: va aparte, marcado.
    """
    bd = mapa_json.abrir_copia(ruta_copia)
    ub = {f[0]: f for f in bd.execute('SELECT id, tipo, lineal, posicion, nivel, en_nave, hueco_id, nombre, activa '
                                      'FROM ubicaciones')}
    suma = collections.Counter()
    for loc, cant in bd.execute('SELECT ubicacion_id, SUM(cantidad) FROM stock GROUP BY 1'):
        suma[loc] = cant or 0
    bd.close()
    con_stock = collections.Counter()                   # hueco -> cajas con stock
    uds = collections.defaultdict(collections.Counter)  # hueco -> uds por zona
    for c in datos['cajas'].values():
        if c['nombre'] != 'suelto':
            con_stock[c['hueco']] += 1
        for x in c['lineas']:
            uds[c['hueco']]['0' if x['zona'] == '0' else 'Z'] += x['uds']
    res = []
    for u in ub.values():
        if u[1] != 'contenedor' or not u[8] or not u[5] or not u[6] or suma[u[0]] > 0:
            continue
        h = ub.get(u[6])
        if not h or h[1] != 'hueco' or not h[2] or not (r.lineales[0] <= h[2] <= r.lineales[1]):
            continue
        hueco = (h[2], h[3], h[4])
        u0, uz = uds[hueco]['0'], uds[hueco]['Z']
        res.append({'hueco': hueco, 'caja': u[7], 'negativo': suma[u[0]] < 0,
                    'zona': mapa_json.zona_de(u0, uz) if (u0 or uz) else 'solo cajas a 0',
                    'cajas_con_stock': con_stock[hueco], 'metros': datos['metros'](hueco[0], hueco[1])})
    a_cero = collections.Counter(v['hueco'] for v in res)
    for v in res:
        v['cajas_a_cero_hueco'] = a_cero[v['hueco']]
    res.sort(key=lambda v: (v['zona'] != '0', v['hueco'], v['caja']))
    return res


def ocupa(caja, r):
    """Litros que ocupa una caja en el hueco: un contenedor, al menos una caja entera; lo suelto, sus litros."""
    lt = sum(x['litros'] for x in caja['lineas'])
    return max(lt, r.litros_caja) if caja['nombre'] != 'suelto' else lt


def clasificar(datos, r=ReglasCompactar()):
    """Una fila por modelo-color con stock de zona 0 en huecos."""
    mcs = {}
    for c in datos['cajas'].values():
        for x in c['lineas']:
            if x['zona'] != '0':
                continue
            m = mcs.setdefault(x['mc'], {'mc': x['mc'], 'modelo': x['modelo'], 'familia': x['familia'], 'uds': 0.0,
                                         'litros': 0.0, 'tallas': collections.Counter(), 'cajas': set(),
                                         'huecos': set(), 'fuente': x['fuente'], 'lt_ud': x['lt_ud']})
            m['uds'] += x['uds']
            m['litros'] += x['litros']
            m['tallas'][x['talla']] += x['uds']
            m['huecos'].add(c['hueco'])
    for clave, c in datos['cajas'].items():
        for x in c['lineas']:
            if x['mc'] in mcs:
                mcs[x['mc']]['cajas'].add(clave)
    total = sum(datos['lineas'][k] for k in mcs)
    acum = 0
    for m in sorted(mcs.values(), key=lambda m: (-datos['lineas'][m['mc']], m['mc'])):
        n = datos['lineas'][m['mc']]
        m['lineas'] = n
        m['uds_salida'] = datos['uds_salida'][m['mc']]
        acum += n
        if n == 0:
            m['abc'] = 'sin salidas'
        else:
            pct = acum / total
            m['abc'] = 'A' if pct <= r.corte_a or acum == n else ('B' if pct <= r.corte_b else 'C')
        m['uds_caja'] = max(1, math.floor(r.litros_caja / m['lt_ud'])) if m['lt_ud'] else None
        m['tamano'] = ('grande' if m['uds_caja'] < r.grande_si_menos_de else
                       'pequeño' if m['uds_caja'] > r.pequeno_si_mas_de else 'mediano')
        m['lineas_por_100_uds'] = round(100.0 * n / m['uds'], 1) if m['uds'] else 0.0
    return mcs


def tallas_por_altura(datos, mcs, r=ReglasCompactar()):
    """A qué altura de la columna va cada talla de cada modelo-color (propuesta del 26/11, idea de Andrés + Isaac).

    Las alturas son las 4 cajas de alto de cada columna (C1–C4 de Odoo son columnas, no alturas). Las tallas de cada
    modelo-color se ordenan por sus propias líneas de salida (28 días; si no tiene, por stock). Abajo (alturas 1–2; el
    suelo es lo cómodo, Isaac 26/11) van las más pedidas hasta la mitad de las uds del modelo-color; el resto, arriba
    (alturas 3–4). Los restos de talla (≤ 2 uds o ≤ 5 % de la talla más fuerte), arriba del todo. La primera talla
    siempre va abajo. El corte es por unidades (lo que ocupa), no por líneas: por líneas, abajo se llevaba el 74 %.
    Devuelve {mc: {'abajo': [tallas], 'arriba': [...], 'restos': [...], 'uds': {altura: uds}, 'cajas': {altura: cajas}}}.
    """
    res = {}
    for mc, m in mcs.items():
        stock = m['tallas']
        lt = {t: datos['lineas_talla'].get((mc, t), 0) for t in stock}
        por = lt if sum(lt.values()) else stock
        total = sum(stock.values()) or 1
        fuerte = max(stock.values()) if stock else 0
        orden = sorted(stock, key=lambda t: (-por[t], -stock[t], t))
        alt = {'abajo': [], 'arriba': [], 'restos': []}
        acum, lleno = 0.0, False
        for i, t in enumerate(orden):
            resto = stock[t] < fuerte and (stock[t] <= r.resto_uds or stock[t] <= r.resto_pct * fuerte)
            if i == 0:
                a = 'abajo'
            elif resto:
                a = 'restos'
            elif not lleno and abs((acum + stock[t]) / total - r.altura_c1) < abs(acum / total - r.altura_c1):
                a = 'abajo'          # con esta talla, abajo se queda más cerca de la mitad que sin ella
            else:
                a, lleno = 'arriba', True   # a partir de aquí, todo arriba (no se salta el orden de lo más pedido)
            if a == 'abajo':
                acum += stock[t]
            alt[a].append(t)
        uds = {a: sum(stock[t] for t in ts) for a, ts in alt.items()}
        por_caja = m.get('uds_caja') or 1
        res[mc] = dict(alt, uds=uds, cajas={a: math.ceil(u / por_caja) if u else 0 for a, u in uds.items()})
    return res


def ko_mixta(datos, mcs, r=ReglasCompactar()):
    """KO mixta (decisión de Isaac del 26/11, idea de Andrés): en cada hueco, una KO por SKU si ese SKU tiene en la
    zona 0 stock para `ko_sku_cajas` cajas o más; las demás tallas del modelo-color, juntas en una KO.
    Con la ubicación de hoy (antes de mover nada). Devuelve (skus_propios, {lineal: [KO hoy, KO después]})."""
    uds = collections.Counter()
    for c in datos['cajas'].values():
        for x in c['lineas']:
            if x['zona'] == '0':
                uds[(x['mc'], x['talla'])] += x['uds']
    propios = {s for s, u in uds.items() if s[0] in mcs and u >= (mcs[s[0]]['uds_caja'] or 1) * r.ko_sku_cajas}
    hoy = collections.Counter()
    despues = collections.defaultdict(set)
    for c in datos['cajas'].values():
        z = [x for x in c['lineas'] if x['zona'] == '0']
        if not z or c['nombre'] == 'suelto':
            continue
        hoy[c['hueco'][0]] += 1
        for x in z:
            s = (x['mc'], x['talla'])
            despues[c['hueco'][0]].add((c['hueco'], s if s in propios else (x['mc'], '*')))
    return propios, {l: [hoy[l], len(despues[l])] for l in hoy}


def _es_resto(caja, mcs, r):
    """Caja que solo lleva tallas con muy poco stock (en toda la nave) comparadas con la talla más fuerte de su
    modelo-color, y ese modelo-color tiene más cajas. Ejemplo de Isaac: 50 de la L y 2 de la XS → las XS son resto."""
    for x in caja['lineas']:
        m = mcs.get(x['mc'])
        if not m or len(m['cajas']) < 2:
            return False
        talla, fuerte = m['tallas'][x['talla']], max(m['tallas'].values())
        if talla >= fuerte or not (talla <= r.resto_uds or talla <= r.resto_pct * fuerte):
            return False
    return True


def compactar(datos, mcs, r=ReglasCompactar()):
    """Propuesta de vaciado de huecos poco llenos de la zona 0. Devuelve (pasos, resumen)."""
    cap = r.litros_hueco
    tope = cap * r.llenado
    metros = datos['metros']
    contenido = collections.defaultdict(list)          # hueco -> [clave de caja]
    for clave, c in datos['cajas'].items():
        contenido[c['hueco']].append(clave)
    lleno = {h: sum(ocupa(datos['cajas'][k], r) for k in ks) for h, ks in contenido.items()}

    def zona_hueco(h):
        u = collections.Counter()
        for k in contenido[h]:
            for x in datos['cajas'][k]['lineas']:
                u['0' if x['zona'] == '0' else 'Z'] += x['uds']
        return mapa_json.zona_de(u['0'], u['Z'])

    huecos0 = {h for h in contenido if zona_hueco(h) == '0'}
    solo0 = {h for h in huecos0 if all(x['zona'] == '0' for k in contenido[h] for x in datos['cajas'][k]['lineas'])}
    por_lineal = collections.defaultdict(list)
    for h in huecos0:
        por_lineal[h[0]].append(h)

    def clase_caja(caja):
        orden = {'A': 0, 'B': 1, 'C': 2, 'sin salidas': 3}
        return min((mcs[x['mc']]['abc'] for x in caja['lineas'] if x['mc'] in mcs), key=lambda a: orden[a], default='sin salidas')

    vaciados, destinos = set(), set()
    pasos = []
    candidatos = sorted((h for h in solo0 if lleno[h] < cap * r.poco_lleno),
                        key=lambda h: (len(contenido[h]), lleno[h], h))
    for h in candidatos:
        if h in destinos or h in vaciados:
            continue
        plan, extra = [], collections.Counter()
        ok = True
        grupos = collections.defaultdict(list)          # mismo modelo-color (o mismos), mismo destino
        for k in contenido[h]:
            grupos[tuple(sorted({x['mc'] for x in datos['cajas'][k]['lineas']}))].append(k)
        for ks in sorted(grupos.values(), key=lambda ks: -sum(ocupa(datos['cajas'][k], r) for k in ks)):
            lineas_g = [x for k in ks for x in datos['cajas'][k]['lineas']]
            lt = sum(ocupa(datos['cajas'][k], r) for k in ks)
            clase = min((clase_caja(datos['cajas'][k]) for k in ks), key=['A', 'B', 'C', 'sin salidas'].index)
            resto = all(_es_resto(datos['cajas'][k], mcs, r) for k in ks)
            al_fondo = resto or clase in ('C', 'sin salidas')
            modelos = {x['modelo'] for x in lineas_g}
            mcs_caja = {x['mc'] for x in lineas_g}
            familias = {x['familia'] for x in lineas_g}
            mejor = None
            for l in range(h[0] - r.distancia_lineales, h[0] + r.distancia_lineales + 1):
                for d in por_lineal.get(l, ()):
                    if d == h or d in vaciados or lleno[d] + extra[d] + lt > tope:
                        continue
                    # (hasta el 26/11: lo de clase A solo a C1–C2; quitado porque C1–C4 son columnas, no alturas)
                    dentro = [x for kk in contenido[d] for x in datos['cajas'][kk]['lineas']] + \
                             [x for kk, dd in plan if dd == d for x in datos['cajas'][kk]['lineas']]
                    # el mismo artículo no se mezcla: otro color del mismo modelo, no
                    if any(x['modelo'] in modelos and x['mc'] not in mcs_caja for x in dentro):
                        continue
                    mismo_mc = any(x['mc'] in mcs_caja for x in dentro)
                    misma_familia = sum(1 for x in dentro if x['familia'] in familias)
                    m = metros(d[0], d[1])
                    puntos = (0 if mismo_mc else 1, misma_familia, -m if al_fondo else m, -(lleno[d] + extra[d]), d)
                    if mejor is None or puntos < mejor[0]:
                        mejor = (puntos, d)
            if mejor is None:
                ok = False
                break
            d = mejor[1]
            plan.extend((k, d) for k in ks)
            extra[d] += lt
        if not ok:
            continue
        vaciados.add(h)
        for k, d in plan:
            caja = datos['cajas'][k]
            lleno[d] += ocupa(caja, r)
            destinos.add(d)
            contenido[d].append(k)
            pasos.append({'hueco_origen': h, 'caja': caja['nombre'], 'clave': k, 'destino': d,
                          'mc': ', '.join(sorted({x['mc'] for x in caja['lineas']})),
                          'tallas': ', '.join('%s:%g' % (x['talla'] or '-', x['uds']) for x in caja['lineas']),
                          'uds': sum(x['uds'] for x in caja['lineas']), 'litros': round(sum(x['litros'] for x in caja['lineas']), 1),
                          'clase': clase_caja(caja), 'resto_talla': _es_resto(caja, mcs, r),
                          'metros_origen': metros(h[0], h[1]), 'metros_destino': metros(d[0], d[1])})
        contenido[h] = []
        lleno[h] = 0.0
    # cajas medio vacías del mismo modelo-color que acaban en el mismo hueco: se pueden juntar
    cajas_juntables = 0
    for d, ks in contenido.items():
        if d not in huecos0:
            continue
        por_mc = collections.defaultdict(list)
        for k in ks:
            c = datos['cajas'][k]
            if c['nombre'] != 'suelto' and len({x['mc'] for x in c['lineas']}) == 1:
                por_mc[c['lineas'][0]['mc']].append(sum(x['litros'] for x in c['lineas']))
        for lts in por_mc.values():
            if len(lts) > 1:
                cajas_juntables += max(0, len(lts) - max(1, math.ceil(sum(lts) / (r.litros_caja * 0.95))))
    pos_antes = {(h[0], h[1]) for h, ks in contenido.items() if ks or h in vaciados}
    pos_despues = {(h[0], h[1]) for h, ks in contenido.items() if ks}
    pos0_antes = {(h[0], h[1]) for h in huecos0}
    resumen = {
        'fecha_copia': datos['fecha'].strftime('%d/%m/%Y %H:%M'),
        'huecos_zona0_con_stock': len(huecos0),
        'huecos_candidatos': len(candidatos),
        'huecos_liberados': len(vaciados),
        'pct_huecos_zona0_liberados': round(100.0 * len(vaciados) / len(huecos0), 1) if huecos0 else 0.0,
        'posiciones_zona0': len(pos0_antes),
        'posiciones_libres_enteras': len(pos_antes - pos_despues),
        'cajas_a_mover': len(pasos),
        'uds_a_mover': round(sum(p['uds'] for p in pasos)),
        'cajas_juntables_despues': cajas_juntables,
        'capacidad_hueco': '%g L (%s)' % (cap, FALTA_MEDIDA),
        'caja': '%g L (confirmado por Isaac el 26/11)' % r.litros_caja,
    }
    return pasos, resumen


def _h(h):
    return 'L%02d P%02d C%d' % h


# Estado de cada posición en el mapa (v4), de más a menos ganancia
ESTADOS_MAPA = ('libre entera', 'libera niveles', 'recibe cajas', 'retirar cajas a 0', 'sin cambios', 'fuera')


def para_mapa(ruta_copia, datos, mcs, pasos, resumen, vacias, r=ReglasCompactar()):
    """Datos de la compactación para el mapa v4 (compactacion.json). No habla con Odoo.

    - por posición: estado (ESTADOS_MAPA) y, por nivel, qué le pasa;
    - por lineal: cómo queda tras retirar las cajas a 0 y compactar, y qué lineales se podrían vaciar enteros
      (ESTIMACIÓN por volumen: cabe lo suyo en el sitio que queda libre en los demás; no mira distancias ni reglas
      de mezcla, y depende de la capacidad del hueco, que es FALTA MEDIDA);
    - listas: huecos liberados por paso, cajas a mover y cajas a 0.
    """
    bd = mapa_json.abrir_copia(ruta_copia)
    huecos_lineal = collections.Counter()
    for l, in bd.execute("SELECT lineal FROM ubicaciones WHERE tipo = 'hueco' AND en_nave AND activa AND lineal IS NOT NULL"):
        if r.lineales[0] <= l <= r.lineales[1]:
            huecos_lineal[l] += 1
    bd.close()
    cap, tope = r.litros_hueco, r.litros_hueco * r.llenado
    movida = {p['clave']: p['destino'] for p in pasos}
    paso_de, n = {}, 0
    for p in pasos:
        if p['hueco_origen'] not in paso_de:
            n += 1
            paso_de[p['hueco_origen']] = n
    recibe = collections.Counter(p['destino'] for p in pasos)
    sale = collections.Counter(p['hueco_origen'] for p in pasos)
    hoy, despues = collections.Counter(), collections.Counter()           # hueco -> litros
    uds0 = collections.Counter()                                           # hueco -> uds de zona 0 hoy
    for k, c in datos['cajas'].items():
        hoy[c['hueco']] += ocupa(c, r)
        despues[movida.get(k, c['hueco'])] += ocupa(c, r)
        uds0[c['hueco']] += sum(x['uds'] for x in c['lineas'] if x['zona'] == '0')
    ceros = collections.Counter(v['hueco'] for v in vacias if not v['negativo'])
    huecos = set(hoy) | set(ceros)
    por_pos = collections.defaultdict(list)
    for h in huecos:
        por_pos[(h[0], h[1])].append(h)

    def es_de_la_0(pos, hs):
        return any(uds0[h] for h in hs) or (pos[0] >= r.primer_lineal_zona0 and not any(hoy[h] for h in hs))

    posiciones, lin = {}, collections.defaultdict(collections.Counter)
    for pos, hs in por_pos.items():
        de0 = es_de_la_0(pos, hs)
        vacio_despues = {h: despues[h] == 0 for h in hs}
        if not de0:
            e = 'fuera'
        elif all(vacio_despues.values()):
            e = 'libre entera'
        elif any(vacio_despues[h] and (hoy[h] or ceros[h]) for h in hs):
            e = 'libera niveles'
        elif any(recibe[h] for h in hs):
            e = 'recibe cajas'
        elif any(ceros[h] for h in hs):
            e = 'retirar cajas a 0'
        else:
            e = 'sin cambios'
        niv = [[h[2], paso_de.get(h, 0), sale[h], recibe[h], ceros[h], round(hoy[h]), round(despues[h])]
               for h in sorted(hs)]
        posiciones['L%02d|%d' % pos] = {'e': e, 'n': niv}
        if not de0 and pos[0] >= r.primer_lineal_zona0:
            # posición con Z, pero con huecos que solo tienen cajas a 0: también salen en la lista de retirar
            c = lin[pos[0]]
            for h in hs:
                if ceros[h] and not hoy[h]:
                    c['huecos_hoy'] += 1
                    c['solo_cajas_a_0'] += 1
                    c['cajas_a_0'] += ceros[h]
        if de0:
            c = lin[pos[0]]
            c['posiciones'] += 1
            c['libres_enteras'] += e == 'libre entera'
            for h in hs:
                c['huecos_hoy'] += bool(hoy[h] or ceros[h])
                c['huecos_con_stock_hoy'] += bool(hoy[h])
                c['huecos_despues'] += bool(despues[h])
                c['se_vacian_compactando'] += h in paso_de
                c['solo_cajas_a_0'] += bool(ceros[h] and not hoy[h])
                c['cajas_a_0'] += ceros[h]
                c['cajas_a_mover'] += sale[h]
                c['litros_hoy'] += hoy[h]
                c['litros_despues'] += despues[h]
    uds_mover = collections.Counter()
    for p in pasos:
        uds_mover[p['hueco_origen'][0]] += p['uds']
    filas = []
    for l, c in lin.items():
        # Capacidad con los huecos que se usan hoy (con stock o con cajas a 0), no con todos los de Odoo: Odoo tiene
        # C1–C4 en casi todas las posiciones, pero C3–C4 casi no se usan y no sé si existen físicamente (FALTA MEDIDA)
        capacidad = c['huecos_hoy'] * cap
        filas.append({'l': 'L%02d' % l, 'huecos_odoo': huecos_lineal[l], 'posiciones': c['posiciones'],
                      'huecos_hoy': c['huecos_hoy'], 'huecos_con_stock_hoy': c['huecos_con_stock_hoy'],
                      'solo_cajas_a_0': c['solo_cajas_a_0'], 'cajas_a_0': c['cajas_a_0'],
                      'se_vacian_compactando': c['se_vacian_compactando'], 'cajas_a_mover': c['cajas_a_mover'],
                      'uds_a_mover': round(uds_mover[l]), 'huecos_despues': c['huecos_despues'],
                      'libres_enteras': c['libres_enteras'],
                      'pct_hoy': round(c['litros_hoy'] / capacidad, 3) if capacidad else None,
                      'pct_despues': round(c['litros_despues'] / capacidad, 3) if capacidad else None,
                      'litros_despues': round(c['litros_despues']), 'capacidad': round(capacidad)})
    # ¿Qué lineales se podrían vaciar enteros? Del menos lleno al más lleno, mientras lo suyo quepa en el hueco
    # libre (hasta el 90 %) de los lineales que se quedan. Estimación por volumen.
    orden = sorted((f for f in filas if f['capacidad']), key=lambda f: (f['litros_despues'], f['l']))
    libre_total = sum(max(0.0, f['capacidad'] * r.llenado - f['litros_despues']) for f in orden)
    acum = 0.0
    for f in orden:
        libre_total -= max(0.0, f['capacidad'] * r.llenado - f['litros_despues'])
        if acum + f['litros_despues'] <= libre_total:
            acum += f['litros_despues']
            f['vaciar_entero'] = True
        else:
            libre_total += max(0.0, f['capacidad'] * r.llenado - f['litros_despues'])
            f['vaciar_entero'] = False
    # comprobación final: lo de los que se vacían cabe en el sitio libre de los que se quedan; si no, se quita el
    # último vaciado hasta que quepa
    def cabe():
        va = sum(f['litros_despues'] for f in orden if f['vaciar_entero'])
        queda = sum(max(0.0, f['capacidad'] * r.llenado - f['litros_despues']) for f in orden if not f['vaciar_entero'])
        return va <= queda
    while not cabe():
        next(f for f in reversed(orden) if f['vaciar_entero'])['vaciar_entero'] = False
    for f in filas:
        f.setdefault('vaciar_entero', False)
    filas.sort(key=lambda f: (not f['vaciar_entero'], f['pct_despues'] if f['pct_despues'] is not None else 9, f['l']))
    lista_pasos = [[paso_de[p['hueco_origen']], _h(p['hueco_origen']), p['caja'], p['mc'], p['tallas'], round(p['uds']),
                    p['clase'], 'sí' if p['resto_talla'] else '', _h(p['destino']), p['metros_origen'],
                    p['metros_destino']] for p in pasos]
    lista_ceros = [[_h(v['hueco']), v['zona'], v['caja'], 'NEGATIVO' if v['negativo'] else '', v['cajas_a_cero_hueco'],
                    v['cajas_con_stock'], 'paso %d' % paso_de[v['hueco']] if v['hueco'] in paso_de else
                    ('recibe' if recibe[v['hueco']] else ''), v['metros']]
                   for v in vacias if v['zona'] == '0' or v['negativo'] or
                   (v['zona'] == 'solo cajas a 0' and v['hueco'][0] >= r.primer_lineal_zona0)]
    return {
        'fecha_copia': resumen['fecha_copia'],
        'reglas': {k: (list(v) if isinstance(v, tuple) else v) for k, v in dataclasses.asdict(r).items()},
        'falta_medida': ['Capacidad de un hueco: %g L, calculada en Odoo (9 cajas de 84 L son 756 L)' % cap,
                         'Columnas C3 y C4: Odoo las tiene en casi todas las posiciones, pero casi no se usan. La capacidad '
                         'de cada lineal se cuenta solo con los huecos que se usan hoy.'],
        'resumen': dict(resumen, **resumen_cajas_a_cero(vacias, r),
                        lineales_vaciables=sum(f['vaciar_entero'] for f in filas)),
        'estados': list(ESTADOS_MAPA),
        'posiciones': posiciones,
        'lineales': filas,
        'pasos': lista_pasos,
        'ceros': lista_ceros,
    }


def resumen_cajas_a_cero(vacias, r=ReglasCompactar()):
    """Cifras de la lista de cajas a 0 para la hoja Resumen. Un hueco que solo tiene cajas a 0 no tiene zona por su
    stock: se cuenta aparte, según esté de `primer_lineal_zona0` en adelante (palés de la 0) o antes."""
    ok = [v for v in vacias if not v['negativo']]
    solo = [v for v in ok if v['zona'] == 'solo cajas a 0']
    solo_0 = [v for v in solo if v['hueco'][0] >= r.primer_lineal_zona0]
    return {
        'cajas_a_cero_zona0': sum(1 for v in ok if v['zona'] == '0'),
        'huecos_con_cajas_a_cero_zona0': len({v['hueco'] for v in ok if v['zona'] == '0'}),
        'cajas_solo_a_cero_desde_l44': len(solo_0),
        'huecos_solo_a_cero_desde_l44': len({v['hueco'] for v in solo_0}),
        'cajas_solo_a_cero_antes_l44': len(solo) - len(solo_0),
        'huecos_solo_a_cero_antes_l44': len({v['hueco'] for v in solo}) - len({v['hueco'] for v in solo_0}),
        'cajas_a_cero_otras_zonas': sum(1 for v in ok if v['zona'] in ('Z', 'M')),
        'cajas_stock_negativo': sum(1 for v in vacias if v['negativo']),
    }


def exportar_excel(ruta, mcs, pasos, resumen, r=ReglasCompactar(), vacias=None):
    """Excel con el resumen, la clasificación, la matriz ABC × tamaño, los huecos liberados (por beneficio), las
    cajas a mover y, si se da `vacias`, las cajas a 0 que hay que comprobar y retirar. No sobrescribe: si el fichero
    existe, se para."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    from pathlib import Path
    ruta = Path(ruta)
    if ruta.exists():
        raise FileExistsError('%s ya existe; no se sobrescribe' % ruta)
    wb = openpyxl.Workbook()
    negrita = Font(bold=True)
    aviso = PatternFill('solid', fgColor='FFE0B2')

    def hoja(titulo, cab, filas, primera=False):
        ws = wb.active if primera else wb.create_sheet()
        ws.title = titulo
        ws.append(cab)
        for c in ws[1]:
            c.font = negrita
        for f in filas:
            ws.append(list(f))
        ws.freeze_panes = 'A2'
        for i, c in enumerate(cab, 1):
            ws.column_dimensions[get_column_letter(i)].width = max(10, min(40, len(str(c)) + 4))
        return ws

    textos = {
        'fecha_copia': 'Datos de Odoo (copia)', 'huecos_zona0_con_stock': 'Huecos de zona 0 con stock',
        'huecos_candidatos': 'Huecos de zona 0 llenos a menos del %d %%' % round(100 * r.poco_lleno),
        'huecos_liberados': 'Huecos que se liberan', 'pct_huecos_zona0_liberados': '% de huecos de zona 0 liberados',
        'posiciones_zona0': 'Posiciones (suelo) con zona 0',
        'posiciones_libres_enteras': 'Posiciones que quedan vacías del todo (suelo libre)',
        'cajas_a_mover': 'Cajas a mover', 'uds_a_mover': 'Unidades a mover',
        'cajas_juntables_despues': 'Cajas medio vacías del mismo modelo-color que después se pueden juntar',
        'capacidad_hueco': 'Capacidad de un hueco', 'caja': 'Caja',
        'cajas_a_cero_zona0': 'Paso 0 · cajas a 0 en Odoo, en huecos de zona 0 (comprobar y retirar)',
        'huecos_con_cajas_a_cero_zona0': 'Paso 0 · huecos de zona 0 con alguna caja a 0',
        'cajas_solo_a_cero_desde_l44': 'Paso 0 · cajas a 0 en huecos sin stock, de L%d en adelante' % r.primer_lineal_zona0,
        'huecos_solo_a_cero_desde_l44': 'Paso 0 · huecos sin stock, solo cajas a 0, de L%d en adelante (libres al retirarlas)' % r.primer_lineal_zona0,
        'cajas_solo_a_cero_antes_l44': 'Cajas a 0 en huecos sin stock, antes de L%d (zona Z)' % r.primer_lineal_zona0,
        'huecos_solo_a_cero_antes_l44': 'Huecos sin stock, solo cajas a 0, antes de L%d (zona Z)' % r.primer_lineal_zona0,
        'cajas_a_cero_otras_zonas': 'Cajas a 0 en huecos de zona Z o mixtos (no son de esta propuesta)',
        'cajas_stock_negativo': 'Cajas con stock negativo en Odoo (revisar; no se retiran)'}
    if vacias is not None:
        resumen = dict(resumen, **resumen_cajas_a_cero(vacias, r))
    ws = hoja('Resumen', ['Concepto', 'Valor'], [(textos.get(k, k), v) for k, v in resumen.items()], primera=True)
    for fila in ws.iter_rows(min_row=2):
        if FALTA_MEDIDA in str(fila[1].value):
            fila[1].fill = aviso
    ws.append([])
    ws.append(['Reglas', ''])
    ws.cell(ws.max_row, 1).font = negrita
    for k, v in dataclasses.asdict(r).items():
        ws.append([k, str(v)])
    ws.column_dimensions['A'].width = 70
    ws.column_dimensions['B'].width = 30

    orden_abc = {'A': 0, 'B': 1, 'C': 2, 'sin salidas': 3}
    filas = []
    for m in sorted(mcs.values(), key=lambda m: (orden_abc[m['abc']], -m['lineas'], m['mc'])):
        tallas = ', '.join('%s:%g' % (t or '-', u) for t, u in sorted(m['tallas'].items(), key=lambda x: -x[1]))
        filas.append((m['mc'], m['modelo'], m['familia'], m['abc'], m['tamano'], m['lineas'], round(m['uds_salida']),
                      round(m['uds']), m['lineas_por_100_uds'], len(m['tallas']), tallas, round(m['lt_ud'], 2),
                      m['fuente'], m['uds_caja'], len(m['cajas']), len(m['huecos'])))
    hoja('Clasificación', ['Modelo-color', 'Modelo', 'Familia', 'ABC (líneas)', 'Tamaño', 'Líneas %d días' % r.dias,
                           'Uds salidas %d días' % r.dias, 'Profundidad (uds en nave)', 'Líneas por 100 uds',
                           'Nº tallas', 'Tallas (uds)', 'Litros/ud', 'Origen litros', 'Uds por caja', 'Cajas', 'Huecos'],
         filas)

    filas = []
    for a in ['A', 'B', 'C', 'sin salidas']:
        for t in ['pequeño', 'mediano', 'grande']:
            gg = [m for m in mcs.values() if m['abc'] == a and m['tamano'] == t]
            filas.append((a, t, len(gg), sum(m['lineas'] for m in gg), round(sum(m['uds'] for m in gg)),
                          round(sum(m['litros'] for m in gg) / 1000, 1)))
    hoja('Matriz ABC × tamaño', ['ABC', 'Tamaño', 'Modelos-color', 'Líneas', 'Uds en nave', 'm³'], filas)

    por_hueco = collections.OrderedDict()
    for p in pasos:
        por_hueco.setdefault(p['hueco_origen'], []).append(p)
    filas, acum_u = [], 0
    for i, (h, ps) in enumerate(por_hueco.items(), 1):
        u = sum(p['uds'] for p in ps)
        acum_u += u
        filas.append((i, _h(h), len(ps), round(u), ', '.join(sorted({_h(p['destino']) for p in ps})), i, round(acum_u)))
    hoja('Huecos liberados', ['Paso', 'Hueco que se vacía', 'Cajas', 'Uds', 'Destinos', 'Huecos liberados (acum.)',
                              'Uds movidas (acum.)'], filas)

    paso_de = {h: i for i, h in enumerate(por_hueco, 1)}
    filas = [(paso_de[p['hueco_origen']], _h(p['hueco_origen']), p['caja'], p['mc'], p['tallas'], round(p['uds']),
              p['litros'], p['clase'], 'sí' if p['resto_talla'] else '', _h(p['destino']), p['metros_origen'],
              p['metros_destino']) for p in pasos]
    hoja('Cajas a mover', ['Paso', 'Desde', 'Caja', 'Modelo-color', 'Tallas (uds)', 'Uds', 'Litros', 'Clase',
                           'Resto de talla', 'Hasta', 'Metros a expedición (desde)', 'Metros a expedición (hasta)'],
         filas)

    if vacias is not None:
        en_pasos = {}
        for p in pasos:
            en_pasos.setdefault(p['hueco_origen'], 'se vacía (paso %d)' % paso_de[p['hueco_origen']])
            en_pasos.setdefault(p['destino'], 'recibe cajas')
        filas = [(i, _h(v['hueco']), v['zona'], v['caja'], 'NEGATIVO: revisar' if v['negativo'] else '',
                  v['cajas_a_cero_hueco'], v['cajas_con_stock'], en_pasos.get(v['hueco'], ''), v['metros'], '', '')
                 for i, v in enumerate(vacias, 1)]
        ws = hoja('Cajas a 0 (retirar)', ['Orden', 'Hueco', 'Zona del hueco', 'Caja', 'Aviso',
                                          'Cajas a 0 en el hueco', 'Cajas con stock en el hueco',
                                          'En la compactación', 'Metros a expedición',
                                          'Comprobado vacía (sí/no)', 'Nota'], filas)
        ws.column_dimensions['D'].width = 22
    wb.save(ruta)
    return ruta

# -*- coding: utf-8 -*-
"""Escenario de redistribución (fase 2, BORRADOR para decidir reglas). Funciones puras sobre la copia SQLite.

No es la propuesta: sirve para ver qué dan unas reglas y elegir. Cada regla es un parámetro de `Reglas`.

Unidad que se coloca: el modelo-color entero (todos sus contenedores), para que quede junto.
Capacidad: en litros por hueco (~770 L: p95-p99 de los huecos llenos el 23/11; cuadra con 10 cajas de 84 L). Lo que
ocupa un modelo-color: sus cajas, cada una como mínimo una caja entera aunque vaya medio vacía (los cartones de
proveedor de la zona 0 rondan los 600 L y ocupan casi un hueco).
Recorrido: los lineales se ordenan por metros a expedición (geometría de kpi.py) y se llenan uno detrás de otro;
dentro del lineal, posición más cercana primero y nivel según las reglas.
Picks: pares distintos albarán–modelo-color de las órdenes de entrega de los últimos `dias` días.
Metros por pick: metros de ida a expedición del hueco donde está el modelo-color (si está en varios, la media
ponderada por unidades). Antes y después se calculan igual.
"""
import collections
import dataclasses
import datetime
import math
import re

from . import mapa_json


@dataclasses.dataclass
class Reglas:
    niveles_0: tuple = (1, 2)            # niveles donde va la zona 0 (picking)
    niveles_z: tuple = (1, 2, 3, 4)      # niveles donde va la zona Z
    litros_hueco: float = 770.0          # volumen útil de un hueco (p95-p99 de los huecos llenos el 23/11)
    llenado: float = 0.9                 # no llenar más del 90 % (sitio para reponer)
    juntar_z: bool = True                # juntar las cajas medio vacías de Z del mismo modelo-color
    litros_caja: float = 84.0            # caja llena (memoria koroshi-caixa-plena-volum)
    litros_por_ud_sin_dato: float = 2.5
    orden_0: str = 'picks_por_caja'      # 'picks_por_caja' (COI) o 'picks'
    separar_por_lineal: bool = True      # la zona Z empieza en un lineal nuevo (frontera limpia)
    lineales: tuple = (1, 136)
    incluir_pendiente: bool = True       # lo pendiente de ubicar también se coloca
    dias: int = 28


def _cap(nivel, r):
    return r.litros_hueco * r.llenado


def cargar(ruta_copia, carpeta_v2, r=Reglas()):
    """Modelos-color con sus cajas, picks y huecos de hoy; y los huecos de la nave con sus metros."""
    G = mapa_json._geometria(carpeta_v2)
    bd = mapa_json.abrir_copia(ruta_copia)
    fecha = datetime.datetime.fromisoformat(dict(bd.execute('SELECT clave, valor FROM meta').fetchall())['fecha_descarga'])
    ub = {f[0]: f for f in bd.execute(
        'SELECT id, tipo, lineal, posicion, nivel, en_nave, hueco_id, activa FROM ubicaciones')}
    prod = {f[0]: f for f in bd.execute('SELECT id, modelo, color, zona, litros FROM productos')}
    mc = collections.defaultdict(lambda: {'zona': collections.Counter(), 'cajas': set(), 'sueltas': 0.0, 'litros': 0.0,
                                          'uds': 0.0, 'huecos': collections.Counter(), 'picks': 0, 'pendiente': 0.0,
                                          'lt_caja': collections.Counter()})
    lt_caja = collections.Counter()          # litros de cada contenedor (todos sus modelos-color)
    for loc, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock WHERE cantidad > 0'):
        p = prod.get(pid)
        if p:
            lt_caja[loc] += cant * (p[4] or r.litros_por_ud_sin_dato)
    for loc, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock WHERE cantidad > 0'):
        u = ub.get(loc)
        if not u or not u[5]:
            continue
        p = prod.get(pid)
        if not p:
            continue
        clave = mapa_json.mc_de(p[1], p[2])
        m = mc[clave]
        m['zona'][p[3]] += cant
        m['uds'] += cant
        m['litros'] += cant * (p[4] or r.litros_por_ud_sin_dato)
        m['lt_caja'][loc] += cant * (p[4] or r.litros_por_ud_sin_dato)
        hueco = ub.get(u[6]) if u[6] else None
        if hueco and hueco[1] == 'hueco' and hueco[2] and r.lineales[0] <= hueco[2] <= r.lineales[1]:
            m['huecos'][(hueco[2], hueco[3], hueco[4])] += cant
            if u[1] == 'contenedor':
                m['cajas'].add(loc)
            else:
                m['sueltas'] += cant
        else:
            m['pendiente'] += cant
            if u[1] == 'contenedor':
                m['cajas'].add(loc)
    desde = (fecha - datetime.timedelta(days=r.dias)).strftime('%Y-%m-%d %H:%M:%S')
    for clave, n in bd.execute(
            "SELECT p.modelo || CASE WHEN p.color <> '' THEN '-' || p.color ELSE '' END, COUNT(DISTINCT s.albaran) "
            "FROM salidas s JOIN tipos_operacion t ON t.id = s.tipo_operacion_id AND t.codigo = 'outgoing' "
            'JOIN productos p ON p.id = s.producto_id WHERE s.fecha >= ? GROUP BY 1', (desde,)):
        if clave in mc:
            mc[clave]['picks'] = n
    huecos = [(f[2], f[3], f[4]) for f in ub.values()
              if f[1] == 'hueco' and f[7] and f[5] and r.lineales[0] <= f[2] <= r.lineales[1]]
    bd.close()
    # volumen que ocupa hoy cada modelo-color: cada caja ocupa al menos una caja entera (84 L) aunque vaya medio
    # vacía; si la comparte con otros modelos-color, se reparte por litros
    for m in mc.values():
        m['ocupa_hoy'] = sum(max(lt_caja[c], r.litros_caja) * (x / lt_caja[c]) for c, x in m['lt_caja'].items() if lt_caja[c] > 0)
    metros = lambda l, p: G.metros_a_expedicion(l, p)
    return dict(mc), huecos, metros


def cajas_necesarias(m, r):
    """Litros que ocupará el modelo-color: lo que ocupa hoy, o juntando las cajas medio vacías de Z (cajas llenas
    al 95 %) si la regla lo dice."""
    hoy = max(m['ocupa_hoy'], r.litros_caja)
    if r.juntar_z and zona_mc(m) == 'Z':
        return min(hoy, math.ceil(m['litros'] / (r.litros_caja * 0.95)) * r.litros_caja)
    return hoy


def zona_mc(m):
    return '0' if m['zona'].get('0', 0) >= sum(m['zona'].values()) / 2 else 'Z'


def metros_por_pick(mc, sitio, metros):
    """Media de metros por pick: cada modelo-color, en la media (por uds) de los metros de sus huecos."""
    tot = picks = 0.0
    for clave, m in mc.items():
        hs = sitio(clave, m)
        if not hs or not m['picks']:
            continue
        u = sum(hs.values())
        tot += m['picks'] * sum(metros(l, p) * x for (l, p, _), x in hs.items()) / u
        picks += m['picks']
    return tot / picks if picks else None


def simular(mc, huecos, metros, r=Reglas()):
    """Coloca los modelos-color (zona 0 primero, del más «caliente» al más frío; luego Z) en los huecos ordenados
    por recorrido. Devuelve las cifras de antes y después y la asignación."""
    # recorrido: lineales por metros medios; dentro, posición más cercana y nivel más bajo
    por_l = collections.defaultdict(list)
    for h in huecos:
        por_l[h[0]].append(h)
    orden_l = sorted(por_l, key=lambda l: sum(metros(l, p) for _, p, _ in por_l[l]) / len(por_l[l]))
    elegibles = [m for m in mc.items() if r.incluir_pendiente or m[1]['huecos']]
    z0 = [x for x in elegibles if zona_mc(x[1]) == '0']
    zz = [x for x in elegibles if zona_mc(x[1]) == 'Z']
    clave_0 = (lambda x: -x[1]['picks'] / cajas_necesarias(x[1], r)) if r.orden_0 == 'picks_por_caja' else (lambda x: -x[1]['picks'])
    z0.sort(key=clave_0)
    zz.sort(key=lambda x: (-x[1]['picks'], x[0]))     # Z: lo que más sale, más cerca dentro de la zona Z
    asignado, lineales_de = {}, {}
    usados = collections.Counter()
    pos_l = {'i': 0}

    def colocar(lista, niveles, empieza_en):
        i = empieza_en
        cola = []
        for l in orden_l[i:]:
            cola.extend(sorted((h for h in por_l[l] if h[2] in niveles), key=lambda h: (metros(h[0], h[1]), h[2])))
        k = 0
        sin_sitio = []
        ultimo_l = None
        for clave, m in lista:
            falta = cajas_necesarias(m, r)
            hs = collections.Counter()
            while falta > 1e-6 and k < len(cola):
                h = cola[k]
                libre = _cap(h[2], r) - usados[h]
                if libre < min(r.litros_caja, falta) * 0.999:      # no cabe ni una caja: siguiente hueco
                    k += 1
                    continue
                poner = min(libre, falta)
                usados[h] += poner
                falta -= poner
                hs[h] += poner
            if falta > 0:
                sin_sitio.append(clave)
            asignado[clave] = hs
            lineales_de[clave] = {h[0] for h in hs}
            if hs:
                ultimo_l = max(hs, key=lambda h: orden_l.index(h[0]))[0]
        return sin_sitio, (orden_l.index(ultimo_l) + 1 if ultimo_l is not None else empieza_en)

    sin0, sig = colocar(z0, set(r.niveles_0), 0)
    sinz, _ = colocar(zz, set(r.niveles_z), sig if r.separar_por_lineal else 0)

    antes = metros_por_pick(mc, lambda c, m: m['huecos'], metros)
    despues = metros_por_pick(mc, lambda c, m: collections.Counter({h: 1 for h in asignado.get(c, {})}), metros)
    # cajas que cambian de hueco: las de hoy que no caen en uno de sus huecos asignados (aproximado por uds)
    mover_uds = 0.0
    for c, m in mc.items():
        dest = set(asignado.get(c, {}))
        mover_uds += m['pendiente'] + sum(u for h, u in m['huecos'].items() if h not in dest)
    cajas_hoy = sum(max(m['ocupa_hoy'], r.litros_caja) for m in mc.values())
    cajas_desp = sum(cajas_necesarias(m, r) for m in mc.values())
    # movimiento mínimo: con la frontera de zonas de este escenario, solo se mueve lo que está en la zona que no
    # le toca, lo pendiente de ubicar y lo que no está en el lineal principal de su modelo-color
    zona_l = {**{l: 'Z' for l in {h[0] for c, m in zz for h in asignado.get(c, {})}},
              **{l: '0' for l in {h[0] for c, m in z0 for h in asignado.get(c, {})}}}
    minimo = 0.0
    for c, m in mc.items():
        z = zona_mc(m)
        por_l = collections.Counter()
        for (l, p, n), u in m['huecos'].items():
            por_l[l] += u
        bien = {l: u for l, u in por_l.items() if zona_l.get(l, 'Z') == z}
        principal = max(bien.values()) if bien else 0
        minimo += m['pendiente'] + sum(por_l.values()) - principal
    l0 = {h[0] for c, m in z0 for h in asignado.get(c, {})}
    lz = {h[0] for c, m in zz for h in asignado.get(c, {})}
    return {
        'reglas': dataclasses.asdict(r),
        'modelos_color': {'0': len(z0), 'Z': len(zz)},
        'picks': {'0': sum(m['picks'] for _, m in z0), 'Z': sum(m['picks'] for _, m in zz)},
        'metros_por_pick': {'antes': round(antes, 1), 'despues': round(despues, 1)},
        'mc_mas_de_1_lineal': {'antes': sum(1 for m in mc.values() if len({h[0] for h in m['huecos']}) > 1),
                               'despues': sum(1 for c in lineales_de if len(lineales_de[c]) > 1)},
        'm3_ocupados': {'hoy': round(cajas_hoy / 1000), 'despues': round(cajas_desp / 1000)},
        'huecos_usados': len(usados), 'huecos_nave': len(huecos),
        'lineales': {'0': len(l0), 'Z': len(lz), 'libres': len(set(orden_l) - l0 - lz),
                     '0_rango': _rango(l0), 'Z_rango': _rango(lz)},
        'sin_sitio': {'0': len(sin0), 'Z': len(sinz)},
        'uds_a_mover': {'rehacer_todo': round(mover_uds), 'minimo': round(minimo)},
        'uds_total': round(sum(m['uds'] for m in mc.values())),
    }, asignado


def _rango(ls):
    ls = sorted(ls)
    if not ls:
        return ''
    tramos, ini, prev = [], ls[0], ls[0]
    for x in ls[1:]:
        if x != prev + 1:
            tramos.append((ini, prev))
            ini = x
        prev = x
    tramos.append((ini, prev))
    return ', '.join('L%02d' % a if a == b else 'L%02d-L%02d' % (a, b) for a, b in tramos)

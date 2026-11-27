# -*- coding: utf-8 -*-
"""Plan de la zona Z (outlet) de NAU-2: cómo vende y cómo ordenarla. Solo lee la copia de Odoo; no escribe nada.

Criterio que eligió Isaac el 27/11/2026, después de ver cómo vende el outlet:
  1. Lo que más pesa es la TEMPORADA: las que venden, cerca del muelle; las muertas, lejos (o a los palés).
  2. Dentro de la temporada, por FAMILIA: las que más venden, más cerca.
  3. Dentro de la familia, por MODELO-COLOR, con su talla completa junta.

- Ventas = salidas de OUT (órdenes de entrega) de productos de la zona Z, sin PERMANENTE, del último año de la copia.
- Rotación = uds vendidas en el año ÷ stock de hoy en la nave. Grupos (ReglasZ): vivo (≥ 0,5 o la temporada
  más nueva de verano y de invierno, que acaba de llegar al outlet), lento (0,2–0,5) y muerto (< 0,2).
- Estanterías: tipo por posición de las hojas del 02/11/2026 (CSV en redistribucion/, transcrito el 27/11).
  Capacidad de una posición = cajas (KO) que caben. Hay dos cifras:
    · nominal = huecos del tipo según la leyenda de la hoja (A36 = 4 col × 9 pisos = 36…);
    · real = el percentil 90 de KO por posición que tiene hoy Odoo en las posiciones de ese tipo.
  Se usa la mayor de las dos: si hoy caben más KO que huecos (D10, C, E: unas 2 KO por hueco), lo demuestra la
  nave; si hoy hay menos (E2), puede ser que estén medio vacías, no que no quepan. X = 0 siempre.
- La unidad que se mueve es la KO entera (como en la fase 1 de la zona 0). Las KO con varios modelos-color se
  colocan por su modelo-color principal (el de más uds). PERMANENTE no entra en el plan.
- Destino = lineal, no posición: dentro del lineal, el operario elige el hueco. Los lineales se llenan por
  distancia a expedición (metros de kpi.py) y lo que no cabe en las estanterías L01–L43 queda en palés.
"""
import collections
import csv
import dataclasses
import datetime
import re
from pathlib import Path

from . import configuracion
from . import mapa_json

CARPETA_REDIS = configuracion.CARPETA.parent
PREFIJO_CSV = 'estanterias-zona-z_hojas-20261102_transcripcion-'

# Leyenda de las hojas del 02/11/2026: huecos por posición (columnas × pisos [× fondo])
NOMINAL = {'A36': 36, 'A18': 18, 'B24': 24, 'B12': 12, 'B25': 20, 'D10': 10, 'C': 8, 'E': 8, 'E2': 14,
           'F': 24, 'G': 16, 'H14': 14, 'PAL': None, 'X': 0}
DESCRIPCION = {'A36': 'librería 4 col × 9 pisos', 'A18': 'librería 2 col × 9 pisos', 'B24': '4 col × 6 pisos',
               'B12': '2 col × 6 pisos', 'B25': '5 × 2 × 2 (a mano)', 'D10': '2 col × 5 pisos (rectangular)',
               'C': '2 col × 4 pisos (KOROSHI cuadrado)', 'E': '2 col × 4 pisos (alto)', 'E2': '2 col × 7 pisos',
               'F': '6 × 2 × 2, rectangular estrecho (cliente)', 'G': '4 × 2 × 2, rectangular grande (cliente)',
               'H14': '¿? (escrito a mano, sin leyenda)', 'PAL': 'palé / rack', 'X': 'vacío, sin estantería',
               '?': 'casilla en blanco o ilegible en la hoja'}


@dataclasses.dataclass
class ReglasZ:
    lineales: tuple = (1, 43)          # estanterías de la zona Z (hojas del 02/11)
    vivo: float = 0.5                  # rotación (uds vendidas al año ÷ stock) para «vivo»
    lento: float = 0.2                 # por debajo: «muerto»
    minimo_medir: int = 8              # posiciones de un tipo con KO para fiarse de su capacidad real
    percentil: float = 0.9
    llenado: float = 0.9               # parte de la capacidad que se llena (sitio para lo que entre)
    bloque: str = 'temporada+familia'  # una KO no se mueve si ya está en un lineal de su bloque:
                                       # 'temporada+familia', 'temporada' o 'grupo' (vivo/lento/muerto)


def ruta_csv():
    rutas = sorted(CARPETA_REDIS.glob(PREFIJO_CSV + '*.csv'))
    return rutas[-1] if rutas else None


def leer_estanterias(ruta=None):
    """{(lineal, posición): {'tipo', 'lado', 'hoja', 'duda'}} del CSV transcrito de las hojas."""
    ruta = ruta or ruta_csv()
    if not ruta:
        return {}
    # Si encima del número impreso hay otro escrito a mano («número escrito a mano encima: 36»), vale el escrito:
    # Odoo tiene posiciones hasta P42 y las hojas solo imprimían hasta P36. Si choca con una casilla impresa, gana
    # la renumerada y se apunta la duda.
    tipos, renumeradas = {}, set()
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        for fila in csv.DictReader(f, delimiter=';'):
            try:
                lp = (int(fila['lineal']), int(fila['posicion']))
            except (TypeError, ValueError):
                continue
            duda = (fila.get('duda') or '').strip()
            m = re.search(r'escrito a mano encima: (\d+)', duda)
            if m:
                lp = (lp[0], int(m.group(1)))
            elif lp in renumeradas:
                continue
            tipo = (fila.get('tipo') or '').strip().upper()
            if tipo not in NOMINAL:
                duda = ('tipo «%s» no reconocido; ' % tipo if tipo else 'casilla en blanco; ') + duda
                tipo = '?'
            if lp in tipos:
                duda = 'dos casillas para esta posición; ' + duda
            tipos[lp] = {'tipo': tipo, 'lado': fila.get('lado', ''), 'hoja': fila.get('hoja', ''), 'duda': duda}
            if m:
                renumeradas.add(lp)
    return tipos


def _grupo(rot, nueva, r):
    if nueva or rot >= r.vivo:
        return 'vivo'
    return 'lento' if rot >= r.lento else 'muerto'


def _percentil(valores, q):
    v = sorted(valores)
    return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))] if v else 0


def calcular(ruta_copia, carpeta_v2, r=ReglasZ(), ruta_estanterias=None):
    G = mapa_json._geometria(carpeta_v2)
    bd = mapa_json.abrir_copia(ruta_copia)
    meta = dict(bd.execute('SELECT clave, valor FROM meta'))
    prod = {f[0]: f for f in bd.execute(
        "SELECT id, modelo, color, talla, familia, temporada, zona FROM productos")}

    def mc_de(p):
        return '%s-%s' % (p[1], p[2])

    def es_z(p):
        return p and p[6] == 'Z' and p[5] != 'PERMANENTE'

    # ------------------------------------------------------------ ventas (OUT) y stock
    venta = {k: collections.Counter() for k in ('temporada', 'familia', 'talla', 'mc', 'tf')}
    lineas = {k: collections.Counter() for k in ('temporada', 'familia', 'talla', 'mc')}
    pedidos = collections.Counter()
    desde = hasta = None
    for pid, cant, fecha, alb in bd.execute(
            "SELECT s.producto_id, s.cantidad, s.fecha, s.albaran FROM salidas s JOIN tipos_operacion t "
            "ON t.id = s.tipo_operacion_id WHERE t.codigo = 'outgoing'"):
        p = prod.get(pid)
        if not es_z(p):
            continue
        fam = p[4] or '?'
        for k, v in (('temporada', p[5]), ('familia', fam), ('talla', p[3]), ('mc', mc_de(p))):
            venta[k][v] += cant
            lineas[k][v] += 1
        venta['tf'][(p[5], fam)] += cant
        pedidos[alb] += cant
        desde = min(desde or fecha, fecha)
        hasta = max(hasta or fecha, fecha)
    stock = {k: collections.Counter() for k in ('temporada', 'familia', 'talla', 'mc')}

    ub = {f[0]: f for f in bd.execute(
        'SELECT id, tipo, lineal, posicion, nivel, en_nave, hueco_id, nombre, activa FROM ubicaciones')}
    ko = {}                                         # clave -> caja de la Z
    ceros = collections.Counter()                   # (l, p) -> KO a 0 en estanterías Z
    suma_ko = collections.Counter()
    for uid, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock'):
        u = ub.get(uid)
        if not u or not u[5]:
            continue
        if u[1] == 'contenedor':
            suma_ko[uid] += cant
        p = prod.get(pid)
        if not es_z(p) or cant <= 0:
            continue
        for k, v in (('temporada', p[5]), ('familia', p[4] or '?'), ('talla', p[3]), ('mc', mc_de(p))):
            stock[k][v] += cant
        h = u if u[1] == 'hueco' else (ub.get(u[6]) if u[6] else None)
        hueco = (h[2], h[3], h[4]) if h and h[1] == 'hueco' and h[2] else None
        clave = uid if u[1] == 'contenedor' else ('suelto', uid)
        c = ko.setdefault(clave, {'nombre': u[7] if u[1] == 'contenedor' else 'suelto (sin KO)', 'hueco': hueco,
                                  'donde': u[1] if not hueco else 'hueco', 'mcs': collections.Counter(), 'p': {}})
        mc = mc_de(p)
        c['mcs'][mc] += cant
        c['p'][mc] = p
    # KO a 0 dentro de las estanterías de la Z (paso 1)
    for uid, u in ub.items():
        if u[1] == 'contenedor' and u[5] and u[8] and suma_ko.get(uid, 0) <= 0 and u[6]:
            h = ub.get(u[6])
            if h and h[1] == 'hueco' and h[2] and r.lineales[0] <= h[2] <= r.lineales[1]:
                ceros[(h[2], h[3])] += 1
    bd.close()

    # ------------------------------------------------------------ temporadas, familias y orden
    nuevas = set()
    for letra in 'VI':
        ts = [t for t in stock['temporada'] if t and t[0] == letra and t[1:].isdigit()]
        if ts:
            nuevas.add(max(ts, key=lambda t: int(t[1:])))
    temporadas = {}
    for t in set(stock['temporada']) | set(venta['temporada']):
        s, v = stock['temporada'][t], venta['temporada'][t]
        rot = v / s if s else 0
        temporadas[t] = {'temporada': t, 'vendido': v, 'lineas': lineas['temporada'][t], 'stock': s, 'rotacion': rot,
                         'grupo': _grupo(rot, t in nuevas, r), 'nueva': t in nuevas}
    RANGO_GRUPO = {'vivo': 0, 'lento': 1, 'muerto': 2}
    orden_t = sorted(temporadas, key=lambda t: (RANGO_GRUPO[temporadas[t]['grupo']], -temporadas[t]['vendido'],
                                                -temporadas[t]['stock']))
    for i, t in enumerate(orden_t, 1):
        temporadas[t]['orden'] = i

    def clave_ko(c):
        mc = c['mcs'].most_common(1)[0][0]
        p = c['p'][mc]
        t, fam = p[5], p[4] or '?'
        return (temporadas[t]['orden'], fam == '?', -venta['tf'][(t, fam)], -venta['familia'][fam], fam,
                -venta['mc'][mc], mc, p[3] or '')

    # ------------------------------------------------------------ estanterías y capacidad
    tipos = leer_estanterias(ruta_estanterias)
    hoy_pos = collections.Counter()
    for c in ko.values():
        if c['hueco'] and r.lineales[0] <= c['hueco'][0] <= r.lineales[1]:
            hoy_pos[c['hueco'][:2]] += 1
    medidas = collections.defaultdict(list)
    for lp, n in hoy_pos.items():
        if lp in tipos:
            medidas[tipos[lp]['tipo']].append(n)
    cap_tipo = {}
    for t in set(NOMINAL) | {x['tipo'] for x in tipos.values()}:
        n = medidas.get(t, [])
        real = _percentil(n, r.percentil) if len(n) >= r.minimo_medir else None
        nom = NOMINAL.get(t)
        usar = 0 if t == 'X' else max(real or 0, nom or 0)
        cap_tipo[t] = {'tipo': t, 'descripcion': DESCRIPCION.get(t, '¿? sin leyenda'), 'nominal': nom, 'real': real,
                       'usar': usar, 'posiciones': sum(1 for x in tipos.values() if x['tipo'] == t),
                       'medidas': len(n), 'ko_hoy': sum(n)}
    pos_z = sorted(set(tipos) | set(hoy_pos))
    capacidad = {}
    for lp in pos_z:
        if lp in tipos:
            capacidad[lp] = int(cap_tipo[tipos[lp]['tipo']]['usar'] * r.llenado)
        else:
            capacidad[lp] = hoy_pos[lp]          # sin hoja: lo que ya tiene (no se le mete más)
    metros = {lp: G.metros_a_expedicion(*lp) for lp in pos_z}
    por_lineal = collections.defaultdict(list)
    for lp in pos_z:
        por_lineal[lp[0]].append(lp)
    cap_lineal = {l: sum(capacidad[lp] for lp in v) for l, v in por_lineal.items()}
    dist_lineal = {l: sum(metros[lp] for lp in v) / len(v) for l, v in por_lineal.items()}
    orden_l = sorted(por_lineal, key=lambda l: (dist_lineal[l], l))

    # ------------------------------------------------------------ reparto (KO entera → lineal)
    # 1.ª pasada: en fila, de lo que más vende al lineal más cercano → qué lineales le tocan a cada bloque
    #    (bloque = temporada + familia).
    # 2.ª pasada: para mover lo menos posible, una KO que ya está en uno de los lineales de su bloque se queda;
    #    las demás van al primer lineal de su bloque con sitio (y, si no hay, al siguiente lineal libre).
    lista = sorted(ko.items(), key=lambda kv: clave_ko(kv[1]))

    def bloque(c):
        p = c['p'][c['mcs'].most_common(1)[0][0]]
        if r.bloque == 'temporada+familia':
            return (p[5], p[4] or '?')
        return (p[5],) if r.bloque == 'temporada' else (temporadas[p[5]]['grupo'],)

    libre = dict(cap_lineal)
    i_l = 0
    lineales_bloque = collections.defaultdict(list)
    for k, c in lista:
        while i_l < len(orden_l) and libre[orden_l[i_l]] <= 0:
            i_l += 1
        if i_l < len(orden_l):
            l = orden_l[i_l]
            libre[l] -= 1
            if l not in lineales_bloque[bloque(c)]:
                lineales_bloque[bloque(c)].append(l)
    libre = dict(cap_lineal)
    destino = {}
    for k, c in lista:                               # se quedan
        l_hoy = c['hueco'][0] if c['hueco'] else None
        if l_hoy in lineales_bloque.get(bloque(c), ()) and libre.get(l_hoy, 0) > 0:
            destino[k] = l_hoy
            libre[l_hoy] -= 1
    for k, c in lista:                               # el resto, a su bloque o al siguiente lineal libre
        if k in destino:
            continue
        sitio = [l for l in lineales_bloque.get(bloque(c), ()) if libre[l] > 0]
        if not sitio and lineales_bloque.get(bloque(c)):
            primero = orden_l.index(lineales_bloque[bloque(c)][0])
            sitio = [l for l in orden_l[primero:] if libre[l] > 0][:1]
        if sitio:
            destino[k] = sitio[0]
            libre[sitio[0]] -= 1
        else:
            destino[k] = None                        # no cabe en las estanterías: palés

    # ------------------------------------------------------------ resultados
    def lugar(c):
        if c['hueco']:
            return 'L%02d P%02d C%d' % c['hueco']
        return c['nombre'] if c['donde'] == 'hueco' else 'sin hueco (%s)' % c['donde']

    movs, lin = [], {l: {'l': 'L%02d' % l, 'capacidad': cap_lineal[l], 'metros': round(dist_lineal[l], 1),
                         'ko_hoy': 0, 'ko_despues': 0, 'entran': 0, 'salen': 0, 'se_quedan': 0,
                         'cajas_a_0': sum(ceros[lp] for lp in por_lineal[l]), 'contenido': collections.Counter(),
                         'grupos': collections.Counter(),
                         'tipos': collections.Counter(tipos[lp]['tipo'] for lp in por_lineal[l] if lp in tipos)}
                     for l in por_lineal}
    # Lineales que se quedan para lo vivo (cerca del muelle): ahí primero se hace sitio y luego se trae lo vivo.
    zona_viva = set()
    for b, ls in lineales_bloque.items():
        if (b[0] if b[0] in ('vivo', 'lento', 'muerto') else temporadas[b[0]]['grupo']) == 'vivo':
            zona_viva.update(ls)
    pasos = collections.Counter()
    for orden, (k, c) in enumerate(lista, 1):
        mc = c['mcs'].most_common(1)[0][0]
        p = c['p'][mc]
        t = temporadas[p[5]]
        l_hoy = c['hueco'][0] if c['hueco'] and r.lineales[0] <= c['hueco'][0] <= r.lineales[1] else None
        l_d = destino[k]
        if l_hoy:
            lin[l_hoy]['ko_hoy'] += 1
        if l_d:
            lin[l_d]['ko_despues'] += 1
            lin[l_d]['contenido'][(p[5], p[4] or '?')] += 1
            lin[l_d]['grupos'][t['grupo']] += 1
        if l_hoy and l_hoy == l_d:
            lin[l_hoy]['se_quedan'] += 1
            continue
        if l_hoy is None and l_d is None:
            continue                                 # ya está fuera de las estanterías y sigue fuera
        if t['grupo'] == 'vivo':
            paso = 3                                 # traer lo vivo a los lineales cercanos
        elif l_hoy in zona_viva:
            paso = 2                                 # hacer sitio: sacar lo que no vende de los lineales cercanos
        else:
            paso = 4                                 # el resto (lento y muerto), hacia el fondo o a palés: puede esperar
        pasos[paso] += 1
        if l_hoy:
            lin[l_hoy]['salen'] += 1
        if l_d:
            lin[l_d]['entran'] += 1
        movs.append([paso, orden, lugar(c), c['nombre'], mc, ', '.join(sorted({c['p'][m][3] or '' for m in c['mcs']})),
                     round(sum(c['mcs'].values())), p[5], t['grupo'], p[4] or '?',
                     ('L%02d' % l_d) if l_d else 'palés (fondo)', len(c['mcs'])])
    movs.sort(key=lambda m: (m[0], m[10], m[1]))
    for f in lin.values():
        f['que_va'] = ', '.join('%s %s (%d)' % (t, fam, n) for (t, fam), n in f['contenido'].most_common(6))
        f['grupo'] = '/'.join(g for g in ('vivo', 'lento', 'muerto') if f['grupos'][g]) or '—'
    total_ko = len(ko)
    en_estanterias = sum(1 for c in ko.values() if c['hueco'] and r.lineales[0] <= c['hueco'][0] <= r.lineales[1])
    tam = collections.Counter()
    for n in pedidos.values():
        tam['1 ud' if n == 1 else '2–5 uds' if n <= 5 else '6–50 uds' if n <= 50 else 'más de 50 uds'] += 1
    uds_tam = collections.Counter()
    for n in pedidos.values():
        uds_tam['1 ud' if n == 1 else '2–5 uds' if n <= 5 else '6–50 uds' if n <= 50 else 'más de 50 uds'] += n
    resumen = {
        'fecha_copia': datetime.datetime.fromisoformat(meta['fecha_descarga']).strftime('%d/%m/%Y %H:%M'),
        'ventas_desde': (desde or '')[:10], 'ventas_hasta': (hasta or '')[:10],
        'uds_vendidas': round(sum(venta['temporada'].values())), 'stock': round(sum(stock['temporada'].values())),
        'ko_total': total_ko, 'ko_en_estanterias': en_estanterias, 'ko_fuera': total_ko - en_estanterias,
        'capacidad_estanterias': sum(cap_lineal.values()), 'no_caben': sum(1 for v in destino.values() if v is None),
        'cajas_a_0': sum(ceros.values()), 'pasos': dict(pasos), 'lineales_vivo': sorted(zona_viva),
        'mc_con_stock': sum(1 for v in stock['mc'].values() if v > 0),
        'mc_sin_venta': sum(1 for m, v in stock['mc'].items() if v > 0 and not venta['mc'][m]),
        'uds_sin_venta': round(sum(v for m, v in stock['mc'].items() if v > 0 and not venta['mc'][m])),
        'pedidos': len(pedidos), 'pedidos_por_tamano': dict(tam), 'uds_por_tamano': {k: round(v) for k, v in uds_tam.items()},
        'estanterias': str(ruta_csv() if ruta_estanterias is None else ruta_estanterias),
        'posiciones_con_hoja': len(tipos), 'dudas_hoja': sum(1 for x in tipos.values() if x['duda']),
    }

    def tabla(k, extra=None):
        tv = sum(venta[k].values()) or 1
        ts = sum(stock[k].values()) or 1
        filas = []
        for v in sorted(set(venta[k]) | set(stock[k]), key=lambda x: (-venta[k][x], -stock[k][x])):
            s = stock[k][v]
            fila = [v, round(venta[k][v]), round(100 * venta[k][v] / tv, 1), lineas[k][v], round(s),
                    round(100 * s / ts, 1), round(venta[k][v] / s, 2) if s else '']
            filas.append(fila + (extra(v) if extra else []))
        return filas

    ventas = {
        'temporada': [f + [temporadas[f[0]]['grupo'], temporadas[f[0]]['orden']] for f in tabla('temporada')],
        'familia': tabla('familia'), 'talla': tabla('talla')}
    ceros_lista = [['L%02d P%02d' % lp, n, tipos.get(lp, {}).get('tipo', '')] for lp, n in sorted(ceros.items())]
    return {'resumen': resumen, 'temporadas': temporadas, 'orden_temporadas': orden_t, 'ventas': ventas,
            'cap_tipo': cap_tipo, 'tipos': tipos, 'lineales': [lin[l] for l in orden_l], 'orden_lineales': orden_l,
            'movimientos': movs, 'ceros': ceros_lista, 'posiciones': pos_z, 'capacidad': capacidad,
            'hoy_pos': hoy_pos, 'destino_lineal': {l: lin[l] for l in lin}, 'reglas': r}

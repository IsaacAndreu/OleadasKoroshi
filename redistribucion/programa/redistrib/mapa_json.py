# -*- coding: utf-8 -*-
"""Datos del mapa v3 a partir de una copia SQLite de Odoo. No habla con Odoo: solo lee la copia.

Salen cuatro ficheros en la carpeta del mapa:
- datos.json: posiciones (geometría, zona real, medidas y niveles tal como existen en Odoo), lineales, cifras de
  hoy y de dónde sale cada dato. El «Plan Z5+01» se copia del datos.json de la v2 (Excel del 06/11): es una
  ESTIMACIÓN ANTIGUA y va marcada así.
- huecos.json: lo que hay en cada hueco (contenedores con sus modelos-color y tallas, y lo suelto). Se carga al
  abrir un hueco.
- modelos.json: dónde está cada modelo-color (huecos y unidades). Buscador, dispersión y lista 1.
- listas.json: listas 2 a 5 (contenedores a cero, huecos mezclados, stock sin salidas, pendiente de ubicar).

Reglas (las decisiones están en el README del mapa):
- Zona de un producto: productos.zona (0 = I27+V27; Z = el resto, PERMANENTE incluida; «sin temporada» cuenta
  como Z para pintar, y aparte en las cifras).
- Zona de una posición o de un hueco: la de la mayoría de sus unidades; «M» (mezclada) si la otra zona tiene al
  menos UMBRAL_MEZCLA de las unidades. La lista 3 es más estricta: cualquier unidad de las dos zonas.
- Calor: visitas = pares distintos (albarán, hueco) de las salidas de los últimos DIAS_CALOR días que salen de un
  hueco de NAVE2 (órdenes de entrega y traspasos internos hacia fuera de la nave). No son unidades.
- Dispersión de una posición: media, ponderada por unidades, de en cuántos lineales está cada modelo-color que hay
  en ella.
"""
import collections
import datetime
import importlib.util
import json
import re
import sqlite3
from pathlib import Path

from .descarga import clasificar_en_bd

UMBRAL_MEZCLA = 0.10
DIAS_CALOR = 28
RE_MUELLE = re.compile(r'\bMU-?(\d{1,2})\s*P(\d{1,2})\s*C(\d{1,2})\b', re.I)


def _geometria(carpeta_v2):
    """Funciones de geometría de la v2 (copia de kpi.py + supuestos del prototipo), sin copiarlas otra vez."""
    spec = importlib.util.spec_from_file_location('geometria_v2', Path(carpeta_v2) / 'extraer_datos.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def abrir_copia(ruta):
    """Copia en memoria con las reglas de clasificación actuales (la copia bajada no se toca)."""
    origen = sqlite3.connect('file:%s?mode=ro' % Path(ruta).as_posix(), uri=True)
    bd = sqlite3.connect(':memory:')
    origen.backup(bd)
    origen.close()
    clasificar_en_bd(bd)
    return bd


def zona_de(u0, uz):
    t = u0 + uz
    if t <= 0:
        return 'vacía'
    mayor, menor = ('0', uz) if u0 >= uz else ('Z', u0)
    return 'M' if menor / t >= UMBRAL_MEZCLA else mayor


def mc_de(modelo, color):
    return '%s-%s' % (modelo, color) if color else modelo


def generar(ruta_copia, carpeta_v2, carpeta_salida, dias_calor=DIAS_CALOR):
    G = _geometria(carpeta_v2)
    bd = abrir_copia(ruta_copia)
    meta = dict(bd.execute('SELECT clave, valor FROM meta').fetchall())
    fecha = datetime.datetime.fromisoformat(meta['fecha_descarga'])

    # ---------------------------------------------------------------- ubicaciones -> hueco del mapa
    campos_ub = ('id', 'nombre', 'ruta', 'padre', 'tipo', 'lineal', 'pos', 'nivel', 'en_nave', 'hueco', 'activa')
    ub = {f[0]: dict(zip(campos_ub, f)) for f in bd.execute(
        'SELECT id, nombre, ruta, padre_id, tipo, lineal, posicion, nivel, en_nave, hueco_id, activa FROM ubicaciones')}
    clave_hueco = {}           # id de ubicación del hueco -> ('L01', 19, 2)
    for u in ub.values():
        if not u['en_nave'] or not u['activa']:
            continue
        if u['tipo'] == 'hueco':
            clave_hueco[u['id']] = ('L%02d' % u['lineal'], u['pos'], u['nivel'])
        elif u['tipo'] == 'muelle':
            m = RE_MUELLE.search(u['nombre'] or '')
            if m:
                clave_hueco[u['id']] = ('MU-%02d' % int(m.group(1)), int(m.group(2)), int(m.group(3)))

    def donde(loc_id):
        """(clave del hueco, id del contenedor o None) o (None, None) si no está en un hueco del mapa."""
        u = ub.get(loc_id)
        if not u:
            return None, None
        if u['id'] in clave_hueco:
            return clave_hueco[u['id']], None
        if u['tipo'] == 'contenedor' and u['padre'] in clave_hueco:
            return clave_hueco[u['padre']], u['id']
        return None, None

    # ---------------------------------------------------------------- productos
    prod = {}
    for i, ref, nom, mod, col, talla, fam, temp, zona, litros, est in bd.execute(
            'SELECT id, referencia, nombre, modelo, color, talla, familia, temporada, zona, litros, litros_estimado '
            'FROM productos'):
        prod[i] = {'ref': ref or nom, 'mc': mc_de(mod, col), 'talla': talla, 'temp': temp or '', 'fam': fam,
                   'zona': zona, 'litros': litros, 'est': est}

    # ---------------------------------------------------------------- stock por hueco
    H = collections.defaultdict(lambda: {'u': 0.0, 'u0': 0.0, 'uz': 0.0, 'us': 0.0, 'lt': 0.0, 'lt_est': 0.0,
                                         'cont': {}, 'suelto': collections.defaultdict(lambda: collections.Counter()),
                                         'mc': collections.Counter(), 'sku': set(), 'v': 0})
    pendiente = collections.defaultdict(lambda: {'uds': 0.0, 'cont': set()})
    for loc, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock WHERE cantidad > 0'):
        clave, cont = donde(loc)
        p = prod.get(pid) or {'ref': '?', 'mc': '?', 'talla': '', 'zona': 'sin temporada', 'litros': None, 'est': 1}
        if clave is None:
            u = ub.get(loc) or {}
            if u.get('en_nave'):
                padre = ub.get(u['padre']) if u.get('tipo') == 'contenedor' else None
                sitio = padre if padre else u
                pendiente[sitio['id']]['uds'] += cant
                if u.get('tipo') == 'contenedor':
                    pendiente[sitio['id']]['cont'].add(u['id'])
            continue
        h = H[clave]
        h['u'] += cant
        h['u0' if p['zona'] == '0' else 'uz' if p['zona'] == 'Z' else 'us'] += cant
        if p['litros']:
            h['lt'] += cant * p['litros']
            if p['est']:
                h['lt_est'] += cant * p['litros']
        h['mc'][p['mc']] += cant
        h['sku'].add(pid)
        destino = h['cont'].setdefault(cont, collections.defaultdict(collections.Counter)) if cont else h['suelto']
        destino[p['mc']][p['talla']] += cant

    # contenedores activos de cada hueco (también los vacíos)
    cont_hueco = collections.defaultdict(list)
    for u in ub.values():
        if u['tipo'] == 'contenedor' and u['activa'] and u['padre'] in clave_hueco:
            cont_hueco[clave_hueco[u['padre']]].append(u['id'])

    # ---------------------------------------------------------------- calor: visitas por hueco
    desde = (fecha - datetime.timedelta(days=dias_calor)).strftime('%Y-%m-%d %H:%M:%S')
    visitas = set()
    for orig, dest, alb, codigo in bd.execute(
            'SELECT s.origen_id, s.destino_id, s.albaran, t.codigo FROM salidas s '
            'JOIN tipos_operacion t ON t.id = s.tipo_operacion_id WHERE s.fecha >= ?', (desde,)):
        clave, _ = donde(orig)
        if clave is None:
            continue
        if codigo == 'internal' and (ub.get(dest) or {}).get('en_nave'):
            continue                     # reubicación dentro de la nave: no es picking
        visitas.add((alb, clave))
    for alb, clave in visitas:
        H[clave]['v'] += 1

    # ---------------------------------------------------------------- dispersión de cada modelo-color
    modelos = collections.defaultdict(lambda: {'huecos': collections.Counter(), 'lineales': set(), 'zona': set()})
    for clave, h in H.items():
        for mc, u in h['mc'].items():
            m = modelos[mc]
            m['huecos'][clave] += u
            if clave[0].startswith('L'):
                m['lineales'].add(clave[0])
    for pid, p in prod.items():
        if p['mc'] in modelos:
            modelos[p['mc']]['zona'].add(p['zona'])
    n_lineales = {mc: len(m['lineales']) for mc, m in modelos.items()}

    # ---------------------------------------------------------------- posiciones (geometría de la v2 + Excel plan)
    v2 = json.loads((Path(carpeta_v2) / 'datos.json').read_text(encoding='utf-8'))
    plan_v2 = {(p['l'], p['p']): p['plan'] for p in v2['posiciones']}
    geo_v2 = {(p['l'], p['p']): p for p in v2['posiciones']}
    niveles_existentes = collections.defaultdict(set)
    for clave in clave_hueco.values():
        niveles_existentes[(clave[0], clave[1])].add(clave[2])
    for clave in H:
        niveles_existentes[(clave[0], clave[1])].add(clave[2])

    posiciones = []
    for (l, p) in sorted(niveles_existentes, key=lambda k: (k[0].startswith('MU'), int(re.sub(r'\D', '', k[0])), k[1])):
        muelle = l.startswith('MU')
        if muelle:
            num = int(l[3:])
            if (l, p) in geo_v2:
                g = geo_v2[(l, p)]
                caja = dict(x0=g['x0'], x1=g['x1'], y0=g['y0'], y1=g['y1'])
            else:
                x0 = 172 + num * 1.4
                caja = dict(x0=round(x0, 3), x1=round(x0 + 1.0, 3), y0=round(2 + p * 1.25, 3), y1=round(2 + p * 1.25 + 1.1, 3))
        else:
            num = int(l[1:])
            x0, x1 = G._x_celda(num)
            yc, paso = G._y(p), G._paso(p)
            caja = dict(x0=round(x0, 3), x1=round(x1, 3), y0=round(yc - paso / 2 + 0.05, 3), y1=round(yc + paso / 2 - 0.05, 3))
        niv = []
        tot = collections.Counter()
        mcs = collections.Counter()
        skus = set()
        conts = 0
        for n in sorted(niveles_existentes[(l, p)]):
            h = H.get((l, p, n))
            if h:
                c_stock = len(h['cont'])
                niv.append([n, zona_de(h['u0'], h['uz'] + h['us']), round(h['u']), c_stock, len(cont_hueco.get((l, p, n), [])),
                            len(h['mc']), h['v'], round(h['lt'])])
                for k in ('u', 'u0', 'uz', 'us', 'lt', 'lt_est', 'v'):
                    tot[k] += h[k]
                mcs.update(h['mc'])
                skus |= h['sku']
                conts += c_stock
            else:
                niv.append([n, 'vacía', 0, 0, len(cont_hueco.get((l, p, n), [])), 0, 0, 0])
        disp = (sum(n_lineales[mc] * u for mc, u in mcs.items()) / sum(mcs.values())) if mcs else None
        ocupados = sum(1 for x in niv if x[2] > 0)
        d = {'l': l, 'p': p, **caja, 'zona': zona_de(tot['u0'], tot['uz'] + tot['us']),
             'plan': plan_v2.get((l, p), 'sin dato'), 'u': round(tot['u']), 'u0': round(tot['u0']),
             'uz': round(tot['uz'] + tot['us']), 'c': conts, 'lt': round(tot['lt']),
             'lt_est': round(tot['lt_est']), 'mc': len(mcs), 'sku': len(skus), 'v': tot['v'],
             'd': round(disp, 2) if disp is not None else None, 'oc': round(ocupados / len(niv), 3), 'niv': niv}
        if muelle:
            d['muelle'] = True
        else:
            d['m'] = G.metros_a_expedicion(num, p)
        posiciones.append(d)

    # Odoo tiene lineales que no están en el Excel ni tienen stock (L137 en adelante, 39 posiciones cada uno, el
    # 24/11): no se dibujan, pero se cuentan.
    fuera = [d for d in posiciones if d['plan'] == 'sin dato' and d['u'] == 0]
    posiciones = [d for d in posiciones if not (d['plan'] == 'sin dato' and d['u'] == 0)]
    sin_dibujar = {'posiciones': len(fuera), 'lineales': sorted({d['l'] for d in fuera},
                                                               key=lambda l: int(re.sub(r'\D', '', l)))}

    # ---------------------------------------------------------------- lineales
    lineales = {}
    por_l = collections.defaultdict(list)
    for d in posiciones:
        por_l[d['l']].append(d)
    for l, ps in por_l.items():
        uds = sum(d['u'] for d in ps)
        u0 = sum(d['u0'] for d in ps)
        uz = sum(d['uz'] for d in ps)
        mcs, skus = set(), set()
        for d in ps:
            for n in d['niv']:
                h = H.get((l, d['p'], n[0]))
                if h:
                    mcs.update(h['mc'])
                    skus |= h['sku']
        ocup = sum(1 for d in ps if d['u'] > 0)
        lineales[l] = {
            'posiciones': len(ps), 'ubicaciones': sum(len(d['niv']) for d in ps), 'ocupadas': ocup,
            'pct_ocupacion': round(ocup / len(ps), 4) if ps else None, 'uds': uds, 'uds_0': u0, 'uds_z': uz,
            'pct_0': round(u0 / uds, 4) if uds else None, 'pct_z': round(uz / uds, 4) if uds else None,
            'zona': zona_de(u0, uz), 'sku': len(skus), 'modelos_color': len(mcs),
            'litros': sum(d['lt'] for d in ps), 'contenedores': sum(d['c'] for d in ps),
            'visitas': sum(d['v'] for d in ps),
            'uds_por_pos_ocupada': round(uds / ocup, 1) if ocup else None,
            'dispersion': round(sum(n_lineales[mc] for mc in mcs) / len(mcs), 2) if mcs else None,
        }
    # temporadas principales por lineal (uds)
    temp_l = collections.defaultdict(collections.Counter)
    for loc, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock WHERE cantidad > 0'):
        clave, _ = donde(loc)
        if clave and pid in prod:
            temp_l[clave[0]][prod[pid]['temp'] or '(sin)'] += cant
    for l, c in temp_l.items():
        if l in lineales:
            lineales[l]['temporadas'] = ' '.join('%s:%d' % (t, u) for t, u in c.most_common(4))

    # ---------------------------------------------------------------- cifras de hoy
    mc_lineal = [m for m in modelos.values() if m['lineales']]
    cifras = {
        'uds_mapa': round(sum(h['u'] for h in H.values())),
        'uds_pendiente': round(sum(x['uds'] for x in pendiente.values())),
        'modelos_color': len(mc_lineal),
        'mc_mas_de_1_lineal': sum(1 for m in mc_lineal if len(m['lineales']) > 1),
        'mc_3_o_mas_lineales': sum(1 for m in mc_lineal if len(m['lineales']) >= 3),
        'uds_mc_mas_de_1_lineal': round(sum(sum(m['huecos'].values()) for m in mc_lineal if len(m['lineales']) > 1)),
        'odoo_sin_dibujar': {'posiciones': sin_dibujar['posiciones'], 'lineales': len(sin_dibujar['lineales']),
                             'de': sin_dibujar['lineales'][0] if sin_dibujar['lineales'] else '',
                             'a': sin_dibujar['lineales'][-1] if sin_dibujar['lineales'] else ''},
        'huecos': sum(len(d['niv']) for d in posiciones), 'huecos_con_stock': sum(1 for h in H.values() if h['u'] > 0),
        'huecos_mezclados': sum(1 for h in H.values() if h['u0'] > 0 and (h['uz'] + h['us']) > 0),
        'posiciones_por_zona': dict(collections.Counter(d['zona'] for d in posiciones if not d.get('muelle'))),
        'contenedores_a_cero': 0, 'visitas': sum(h['v'] for h in H.values()), 'dias_calor': dias_calor,
        'litros_estimados_pct': round(sum(h['lt_est'] for h in H.values()) / max(1, sum(h['lt'] for h in H.values())), 3),
    }
    # unidades sin litros (producto sin volumen ni familia)
    sin_lt = 0.0
    for loc, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock WHERE cantidad > 0'):
        clave, _ = donde(loc)
        if clave and not (prod.get(pid) or {}).get('litros'):
            sin_lt += cant
    cifras['uds_sin_litros'] = round(sin_lt)

    # ---------------------------------------------------------------- huecos.json
    huecos_json = {}
    nombre_ub = {u['id']: u['nombre'] for u in ub.values()}

    def tallas(cnt):
        return ' '.join('%s:%d' % (t or '—', u) for t, u in sorted(cnt.items(), key=lambda x: x[0] or ''))

    for clave, h in H.items():
        k = '%s|%d|%d' % clave
        conts = []
        for cid, mcs in sorted(h['cont'].items(), key=lambda x: nombre_ub.get(x[0], '')):
            filas = [[mc, tallas(t), round(sum(t.values()))] for mc, t in sorted(mcs.items())]
            conts.append([nombre_ub.get(cid, '?'), round(sum(f[2] for f in filas)), filas])
        vacios = [nombre_ub[c] for c in cont_hueco.get(clave, []) if c not in h['cont']]
        huecos_json[k] = {'c': conts, 's': [[mc, tallas(t), round(sum(t.values()))] for mc, t in sorted(h['suelto'].items())],
                          'v0': sorted(vacios)}
    for clave, ids in cont_hueco.items():
        k = '%s|%d|%d' % clave
        if k not in huecos_json:
            huecos_json[k] = {'c': [], 's': [], 'v0': sorted(nombre_ub[c] for c in ids)}

    # ---------------------------------------------------------------- modelos.json (lista 1 y buscador)
    modelos_json = {}
    for mc, m in modelos.items():
        hs = sorted(m['huecos'].items(), key=lambda x: (-x[1], x[0]))
        zonas = sorted(m['zona'])
        modelos_json[mc] = [len(m['lineales']), len(hs), round(sum(m['huecos'].values())),
                            zonas[0] if len(zonas) == 1 else '/'.join(zonas),
                            [['%s|%d|%d' % k, round(u)] for k, u in hs]]

    # ---------------------------------------------------------------- listas.json
    # 2. contenedores activos a cero (sin stock), por hueco; también los de fuera de los huecos
    con_stock = {loc for (loc,) in bd.execute('SELECT DISTINCT ubicacion_id FROM stock WHERE cantidad != 0')}
    l2 = []
    for u in ub.values():
        if u['tipo'] == 'contenedor' and u['activa'] and u['id'] not in con_stock and (u['en_nave']):
            clave = clave_hueco.get(u['padre'])
            padre = ub.get(u['padre']) or {}
            l2.append([u['nombre'], ('%s P%02d C%d' % clave) if clave else '', padre.get('ruta', '') if not clave else ''])
    l2.sort(key=lambda r: (r[1] == '', r[1], r[0]))
    cifras['contenedores_a_cero'] = len(l2)
    # 3. huecos con unidades de las dos zonas
    l3 = []
    for clave, h in H.items():
        uz = h['uz'] + h['us']
        if h['u0'] > 0 and uz > 0:
            l3.append(['%s P%02d C%d' % clave, round(h['u0']), round(uz), round(min(h['u0'], uz) / (h['u0'] + uz), 3),
                       len(h['mc'])])
    l3.sort(key=lambda r: -r[3])
    # 4. stock por SKU con su última salida (cualquier origen) para «sin salidas en N días»
    ultima = dict(bd.execute("SELECT s.producto_id, MAX(s.fecha) FROM salidas s JOIN tipos_operacion t "
                             "ON t.id = s.tipo_operacion_id WHERE t.codigo = 'outgoing' GROUP BY 1").fetchall())
    stock_sku = collections.defaultdict(lambda: [0.0, set()])
    for loc, pid, cant in bd.execute('SELECT ubicacion_id, producto_id, cantidad FROM stock WHERE cantidad > 0'):
        clave, _ = donde(loc)
        if clave:
            stock_sku[pid][0] += cant
            stock_sku[pid][1].add('%s P%02d C%d' % clave)
    l4 = []
    for pid, (uds, hs) in stock_sku.items():
        p = prod.get(pid) or {}
        f = ultima.get(pid)
        l4.append([p.get('ref', '?'), p.get('mc', '?'), p.get('talla', ''), p.get('temp', ''), p.get('zona', ''),
                   round(uds), len(hs), ' '.join(sorted(hs)[:6]) + (' …' if len(hs) > 6 else ''), (f or '')[:10]])
    l4.sort(key=lambda r: (r[8] or '0000', -r[5]))
    # 5. pendiente de ubicar (en NAVE2 pero no en un hueco del mapa)
    l5 = []
    for loc_id, x in pendiente.items():
        u = ub[loc_id]
        tipo = u['tipo'] if u['tipo'] != 'otra' else ('nave (sin hueco)' if u['nombre'] == 'NAVE2' else 'otra')
        l5.append([u['ruta'].replace('EFFEC/Stock/NAVE2/', '').replace('EFFEC/Stock/', ''), tipo, len(x['cont']), round(x['uds'])])
    # el muelle se dibuja en el mapa, pero no entra en el reparto: también es pendiente de ubicar
    for clave, h in H.items():
        if clave[0].startswith('MU') and h['u'] > 0:
            l5.append(['%s P%02d C%d' % clave, 'muelle', len(h['cont']), round(h['u'])])
    l5.sort(key=lambda r: -r[3])
    listas = {
        'dias_historico': meta.get('desde_salidas', ''),
        'l2': {'cols': ['Contenedor', 'Hueco', 'Fuera de hueco (ruta del padre)'], 'filas': l2},
        'l3': {'cols': ['Hueco', 'Uds zona 0', 'Uds zona Z', '% de la minoría', 'Modelos-color'], 'filas': l3},
        'l4': {'cols': ['Referencia', 'Modelo-color', 'Talla', 'Temporada', 'Zona', 'Uds', 'Huecos', 'Dónde',
                        'Última salida'], 'filas': l4},
        'l5': {'cols': ['Ubicación', 'Tipo', 'Contenedores', 'Uds'], 'filas': l5},
    }

    datos = {
        'fuente': Path(ruta_copia).name,
        'fecha_datos': fecha.strftime('%d/%m/%Y %H:%M'),
        'servidor': meta.get('servidor', ''),
        'salidas_desde': meta.get('desde_salidas', ''),
        'geometria': v2['geometria'],
        'reglas': {'umbral_mezcla': UMBRAL_MEZCLA, 'dias_calor': dias_calor,
                   'zona_0': 'I27 + V27', 'zona_z': 'el resto (PERMANENTE incluida, decisión del 23/11)'},
        'cifras': cifras,
        'posiciones': posiciones,
        'lineales': lineales,
        'ejemplo': {'aviso': v2['ejemplo']['aviso'], 'flechas': v2['ejemplo']['flechas']},
    }
    bd.close()
    salida = Path(carpeta_salida)
    escribir = {'datos.json': datos, 'huecos.json': huecos_json, 'modelos.json': modelos_json, 'listas.json': listas}
    tam = {}
    for nombre, obj in escribir.items():
        texto = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        (salida / nombre).write_text(texto, encoding='utf-8')
        tam[nombre] = len(texto.encode('utf-8'))
    return datos, tam

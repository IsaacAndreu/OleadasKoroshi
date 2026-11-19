# -*- coding: utf-8 -*-
# =============================================================================
# v1.36.0 (19/11/2026): orden de las tiendas por numero de pedido (peticion de Sonia y de Isaac).
#
# Las tiendas se preparan por numero de pedido S4T (origin S-6665..., de menor a mayor), no por K##.
#   - «Siguiente tienda»: los pedidos de tienda abiertos con el numero mas bajo (prioridad 1, 2, 3).
#     Cuando se cierran todas sus OUT, pasa el siguiente.
#   - «Sacar estas antes»: OUT abiertas de pedidos con numero menor que el de un pedido ya cerrado del todo.
#     El 19/11 se quedaron 6 OUT de Z-1911-MU2 leidas enteras, sin caja ni validar, mientras pedidos posteriores
#     ya estaban hechos.
# Python puro (sin Odoo) para poder probarlo: tests/test_prioridad_calc.py. El controlador (main.py, _prioridad)
# le pasa las OUT abiertas y los pedidos con alguna OUT validada estos dias.
# =============================================================================
import re

RE_NUM = re.compile(r'^\s*S-(\d+)')
RE_K = re.compile(r'\b(K\d+)\b')
N_SIGUIENTES = 3


def numero(origin):
    """'S-6665004417' -> 6665004417. Sin numero S-: None (no entra en el orden)."""
    m = RE_NUM.match(origin or '')
    return int(m.group(1)) if m else None


def k_tienda(tienda):
    """'K45 - LOGROÑO ...' -> 'K45' (si no hay K##, la tienda tal cual)."""
    m = RE_K.search(tienda or '')
    return m.group(1) if m else (tienda or '')


def zona_corta(lote):
    """'Z-1911-MU2' -> 'MU2'; 'Z-1911-R2-D1' -> 'R2-D1'; sin agrupacion de zona: ''."""
    m = re.match(r'^Z-\d{4}-(.+)$', lote or '')
    return m.group(1) if m else ''


def prioridad(abiertas, origenes_hechos, n=N_SIGUIENTES):
    """abiertas: OUT de tienda sin validar, cada una {id, out, pedido, tienda, lote, caja, est, u, disp, leido, en_caja}.
    Las 'sinstock' (en espera, sin nada que coger) no cuentan: no son trabajo que se pueda sacar.
    origenes_hechos: origin de las OUT de tienda validadas estos dias. Un pedido esta cerrado del todo si tiene alguna
    OUT validada y ninguna abierta.
    Devuelve {siguiente: [pedido...], sacar_antes: [OUT...], ultimo_cerrado: 'S-...' o '', abiertos: n pedidos}."""
    outs = []
    for a in abiertas:
        num = numero(a.get('pedido'))
        if num is None or a.get('est') == 'sinstock':
            continue
        o = dict(a)
        o['numero'] = num
        o['k'] = k_tienda(a.get('tienda'))
        o['zona'] = zona_corta(a.get('lote'))
        o['sin_caja'] = max((a.get('leido') or 0.0) - (a.get('en_caja') or 0.0), 0.0)
        outs.append(o)
    abiertos = set(o['numero'] for o in outs)

    cerrados = {}
    for origin in origenes_hechos:
        num = numero(origin)
        if num is not None and num not in abiertos:
            cerrados[num] = (origin or '').strip()
    ultimo = max(cerrados) if cerrados else None

    pedidos = {}
    for o in outs:
        p = pedidos.setdefault(o['numero'], {'numero': o['numero'], 'pedido': o['pedido'].strip(), 'k': o['k'],
                                             'tienda': o.get('tienda') or '', 'outs': [], 'u': 0.0, 'disp': 0.0,
                                             'leido': 0.0, 'en_caja': 0.0})
        p['outs'].append({'id': o.get('id'), 'out': o.get('out'), 'zona': o['zona'], 'caja': o.get('caja') or '',
                          'est': o.get('est')})
        for c in ('u', 'disp', 'leido', 'en_caja'):
            p[c] += o.get(c) or 0.0
    for p in pedidos.values():
        p['outs'].sort(key=lambda x: (x['zona'], x['out'] or ''))
    orden = sorted(pedidos.values(), key=lambda p: p['numero'])

    sacar = []
    if ultimo is not None:
        sacar = [o for o in outs if o['numero'] < ultimo]
        sacar.sort(key=lambda o: (o['numero'], o['zona'], o.get('out') or ''))
        for o in sacar:
            o.pop('numero', None)
    for p in orden:
        p.pop('numero', None)
    return {
        'siguiente': orden[:n],
        'sacar_antes': sacar,
        'ultimo_cerrado': cerrados.get(ultimo, '') if ultimo is not None else '',
        'abiertos': len(orden),
    }

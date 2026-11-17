# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Monitor v1.31.0 (17/11/2026): «Producción por hora» - cuentas, en Python puro (sin Odoo).
#
# Lo pidio Isaac (transcript del 17/11): por cada operario, que pedidos ha hecho, cuantas uds de cada uno y las uds
# de CADA HORA (7-8: 80, 8-9: 100...) con su u/h, y el total del equipo hora a hora.
#
# Entrada: una lista de tareas de koroshi_operarios ya medidas con tarea._medir() (la misma cifra que la tabla
# Operarios, Productividad, el correo y el KPI):
#   {op, codigo, ref, out_id, estado, inicio, fin, uds, minutos, efectivo, huecos [(desde, hasta, min)],
#    lecturas [(fecha, cantidad)]}       (fechas en UTC sin zona, como las guarda Odoo)
# - Minutos de cada hora = el tiempo de la tarea (de inicio a fin) menos sus huecos parados (15 min o mas sin leer),
#   partido por horas locales. La suma de las horas = minutos efectivos de la tarea.
# - Uds de cada hora = las uds de la tarea repartidas segun la hora de cada lectura de la PDA (Preparacion en
#   Lecturas). La suma de las horas = uds de la tarea. Sin lecturas (app de codigo de barras de siempre) se reparten
#   por los minutos de cada hora y la tarea sale marcada como «estimada».
# Pruebas: tests/test_produccion_calc.py (sin Odoo).
# =============================================================================
import datetime
import re

import pytz

MIN_UH_HORA = 5     # con menos de 5 min efectivos en una hora no se ensena su u/h (salen cifras sin sentido)


def a_local(dt, tz):
    return pytz.utc.localize(dt).astimezone(tz)


def hhmm(dt, tz):
    if not dt:
        return ''
    loc = a_local(dt, tz)
    return '%d:%02d' % (loc.hour, loc.minute)


def uds_hora_de(uds, efectivo):
    """La misma formula que koroshi_operarios (tarea.uds_hora_de): uds por hora de tiempo efectivo."""
    return efectivo >= 1 and (uds or 0.0) * 60.0 / efectivo or 0.0


def intervalos_activos(inicio, fin, huecos):
    """[(a, b)] de inicio a fin sin los huecos parados."""
    if not inicio or not fin or fin <= inicio:
        return []
    res = []
    cur = inicio
    for h in sorted(huecos or []):
        a, b = max(h[0], inicio), min(h[1], fin)
        if b <= a:
            continue
        if a > cur:
            res.append((cur, a))
        cur = max(cur, b)
    if fin > cur:
        res.append((cur, fin))
    return res


def minutos_por_hora(intervalos, tz):
    """{hora local: minutos} de unos intervalos en UTC sin zona."""
    res = {}
    for a, b in intervalos:
        cur, fin = a_local(a, tz), a_local(b, tz)
        while cur < fin:
            sig = tz.normalize(cur.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1))
            hasta = min(sig, fin)
            res[cur.hour] = res.get(cur.hour, 0.0) + (hasta - cur).total_seconds() / 60.0
            cur = hasta
    return res


def uds_por_hora(uds, lecturas_hora, minutos_hora, hora_inicio):
    """({hora: uds}, estimado). Reparte las uds de la tarea por sus lecturas; sin lecturas, por sus minutos."""
    if not uds or uds <= 0:
        return {}, False
    pesos = dict((h, c) for h, c in (lecturas_hora or {}).items() if c > 0)
    estimado = not pesos
    if estimado:
        pesos = dict((h, m) for h, m in (minutos_hora or {}).items() if m > 0)
    total = sum(pesos.values())
    if total <= 0:
        return {hora_inicio: float(uds)}, estimado
    return dict((h, uds * p / total) for h, p in pesos.items()), estimado


def _orden_codigo(codigo):
    m = re.sub(r'\D', '', codigo or '')
    return (int(m) if m else 0, codigo or '')


def produccion(tareas, tz):
    """Resumen por operario y hora. Devuelve {horas: [7, 8, ...], operarios: [...], equipo: {...}}."""
    ops = {}
    for t in tareas:
        inter = intervalos_activos(t['inicio'], t['fin'], t.get('huecos'))
        mh = minutos_por_hora(inter, tz)
        lh = {}
        for fecha, cant in t.get('lecturas') or []:
            h = a_local(fecha, tz).hour
            lh[h] = lh.get(h, 0.0) + (cant or 0.0)
        hora_ini = a_local(t['inicio'], tz).hour
        uh, estimado = uds_por_hora(t.get('uds') or 0.0, lh, mh, hora_ini)
        o = ops.setdefault(t['op'], {'op': t['op'], 'codigo': t.get('codigo') or '', 'horas': {}, 'pedidos': [],
                                     'uds': 0.0, 'efectivo': 0.0, 'minutos': 0.0, 'estimado': False})
        for h in set(mh) | set(uh):
            c = o['horas'].setdefault(h, {'uds': 0.0, 'min': 0.0})
            c['uds'] += uh.get(h, 0.0)
            c['min'] += mh.get(h, 0.0)
        o['uds'] += t.get('uds') or 0.0
        o['efectivo'] += t.get('efectivo') or 0.0
        o['minutos'] += t.get('minutos') or 0.0
        o['estimado'] = o['estimado'] or (estimado and (t.get('uds') or 0) > 0)
        o['pedidos'].append({
            'ref': t.get('ref') or '', 'out_id': t.get('out_id') or False, 'estado': t.get('estado') or '',
            'ini': hhmm(t['inicio'], tz), 'fin': hhmm(t['fin'], tz),
            'uds': int(round(t.get('uds') or 0.0)), 'min': int(round(t.get('efectivo') or 0.0)),
            'uh': int(round(uds_hora_de(t.get('uds') or 0.0, t.get('efectivo') or 0.0))),
            'estimado': estimado and (t.get('uds') or 0) > 0,
        })

    horas = sorted(set(h for o in ops.values() for h in o['horas']))
    equipo = {'horas': {}, 'uds': 0.0, 'efectivo': 0.0}
    lista = []
    for clave in sorted(ops, key=lambda k: _orden_codigo(ops[k]['codigo'])):
        o = ops[clave]
        celdas = {}
        for h, c in o['horas'].items():
            e = equipo['horas'].setdefault(h, {'uds': 0.0, 'min': 0.0, 'personas': 0})
            e['uds'] += c['uds']
            e['min'] += c['min']
            if c['min'] > 0 or c['uds'] > 0:
                e['personas'] += 1
            celdas[str(h)] = {'uds': int(round(c['uds'])), 'min': int(round(c['min'])),
                              'uh': int(round(c['uds'] * 60.0 / c['min'])) if c['min'] >= MIN_UH_HORA else None}
        equipo['uds'] += o['uds']
        equipo['efectivo'] += o['efectivo']
        lista.append({
            'op': o['op'], 'codigo': o['codigo'], 'celdas': celdas, 'pedidos': o['pedidos'],
            'uds': int(round(o['uds'])), 'efectivo': int(round(o['efectivo'])),
            'horas_ef': round(o['efectivo'] / 60.0, 2), 'uh': int(round(uds_hora_de(o['uds'], o['efectivo']))),
            'n_pedidos': len(o['pedidos']), 'estimado': o['estimado'],
        })
    eq_celdas = {}
    for h, e in equipo['horas'].items():
        eq_celdas[str(h)] = {
            'uds': int(round(e['uds'])), 'min': int(round(e['min'])), 'personas': e['personas'],
            'personas_ef': round(e['min'] / 60.0, 1),
            'uh': int(round(e['uds'] * 60.0 / e['min'])) if e['min'] >= MIN_UH_HORA else None,
        }
    return {
        'horas': horas, 'operarios': lista,
        'equipo': {'celdas': eq_celdas, 'uds': int(round(equipo['uds'])), 'efectivo': int(round(equipo['efectivo'])),
                   'horas_ef': round(equipo['efectivo'] / 60.0, 2),
                   'uh': int(round(uds_hora_de(equipo['uds'], equipo['efectivo']))),
                   'operarios': len(lista)},
        'min_uh_hora': MIN_UH_HORA,
    }

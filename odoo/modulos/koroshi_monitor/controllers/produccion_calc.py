# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Monitor: «Producción por hora» - cuentas, en Python puro (sin Odoo).
#
# v1.31.0 (17/11/2026): por cada operario, sus pedidos y las uds de CADA HORA con su u/h, y el equipo hora a hora.
# v1.32.0 (17/11/2026, revision con el responsable): dos u/h.
#   - u/h efectiva («mientras pica») = uds x 60 / minutos efectivos (sin los parados de 15 min o mas). La de antes.
#   - u/h REAL («Andres paga la hora entera») = uds x 60 / minutos de PRESENCIA. La principal.
#   Presencia de un operario = de su primer inicio de tarea del dia a su ultimo fin (o ahora), con los huecos entre
#   pedidos dentro (cerrar caja, precintar, palé, desayuno). En una hora de reloj: los minutos de esa hora dentro de
#   la presencia (60, salvo la primera, la ultima y la hora en curso). Perdido = presencia - efectivo.
#   Misma formula que el correo de productividad (koroshi_informe), acordada el 17/11.
#   Con un filtro (solo tiendas, solo web, solo las OUT de una agrupacion...) los huecos entre pedidos no son de
#   ningun tipo: la presencia es solo el tiempo dentro de los pedidos de ese filtro (de inicio a fin de cada uno).
#   Color de la u/h real contra el ritmo estandar (100 u/h, «menos de 100 es rojo», Isaac 17/11).
# v1.35.0 (18/11/2026, peticion de Isaac: sesiones olvidadas abiertas daban «0 min leyendo · 60 perd.» cada hora):
#   los ratos de 15 min o mas sin hacer nada ya no son presencia. Presencia = el tiempo leyendo de sus pedidos (sin
#   sus huecos parados ni lo que lleva ahora parado) mas los huecos entre ellos de menos de 15 min (cerrar caja,
#   precintar, palé). Un hueco de 15 min o mas (dentro de un pedido o entre dos, desayuno incluido) no cuenta. Perdido =
#   esos huecos cortos. Con un filtro, solo el tiempo leyendo de esos pedidos. koroshi_operarios 2.19 cierra sola la
#   tarea a los 15 min sin hacer nada (fin = su ultima actividad).
#
# Entrada: tareas de koroshi_operarios ya medidas con tarea._medir() (la misma cifra que la tabla Operarios,
# Productividad, el correo y el KPI):
#   {op, codigo, ref, out_id, estado, tipo, pickings, inicio, fin, uds, minutos, efectivo,
#    huecos [(desde, hasta, min)], lecturas [(fecha, cantidad)]}       (fechas en UTC sin zona, como en Odoo)
# - Minutos efectivos de cada hora = el tiempo de la tarea menos sus huecos parados, partido por horas locales.
# - Uds de cada hora = las uds de la tarea repartidas segun la hora de cada lectura de la PDA. Sin lecturas (app de
#   codigo de barras de siempre) se reparten por los minutos y la tarea sale marcada como «estimada».
# Pruebas: tests/test_produccion_calc.py (sin Odoo).
# =============================================================================
import datetime
import re

import pytz

MIN_UH_HORA = 5         # con menos de 5 min (efectivos o de presencia) en una hora no se ensena esa u/h
# v1.38.0 (20/11/2026, Isaac: descansos de la empresa por turno). turnos = {op: comun.turno_de(entrada)} (koroshi_base
#   1.1): turno de 6 a 14 (un tramo, descanso 15) -> se descuentan 15 min de presencia: primero cuentan los huecos de 15
#   min o mas que ya no eran presencia; lo que falte sale de los huecos cortos entre pedidos (los mas largos, dentro del
#   turno), nunca del tiempo leyendo. Partido (08-13 y 14-17): entre los tramos (la comida) solo cuenta lo leido. Con un
#   filtro no cambia nada (la presencia ya es solo el tiempo leyendo).
MINUTOS_HUECO = 15      # v1.35: hueco sin hacer nada que ya no es presencia (koroshi_operarios.minutos_sin_leer)
RITMO_ESTANDAR = 100    # u/h real: por debajo, en rojo


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


def unir(intervalos):
    """Une intervalos que se solapan o se tocan: [(a, b)] ordenados y sin solapes."""
    res = []
    for a, b in sorted(i for i in intervalos if i[0] and i[1] and i[1] > i[0]):
        if res and a <= res[-1][1]:
            if b > res[-1][1]:
                res[-1] = (res[-1][0], b)
        else:
            res.append((a, b))
    return res


def unir_con_huecos(intervalos, minutos):
    """v1.35: une los intervalos y rellena los huecos de menos de `minutos` entre ellos (cerrar caja, palé...)."""
    res = []
    for a, b in unir(intervalos):
        if res and (a - res[-1][1]).total_seconds() / 60.0 < minutos:
            res[-1] = (res[-1][0], b)
        else:
            res.append((a, b))
    return res


def restar(intervalos, quitar):
    """v1.38.0: intervalos menos los de quitar (los dos ya unidos y ordenados)."""
    res = []
    for a, b in intervalos:
        cur = a
        for qa, qb in quitar:
            if qb <= cur or qa >= b:
                continue
            if qa > cur:
                res.append((cur, qa))
            cur = max(cur, qb)
            if cur >= b:
                break
        if cur < b:
            res.append((cur, b))
    return res


def _minutos(intervalos):
    return sum((b - a).total_seconds() / 60.0 for a, b in intervalos)


def presencia_con_turno(activos, presencia, turno):
    """v1.38.0: presencia (tiempo leyendo + huecos cortos) con los descansos del turno.
    activos y presencia: unidos y ordenados; turno: comun.turno_de() o None (sin turno: sin cambios)."""
    if not turno or not presencia:
        return presencia
    tramos = turno['tramos']
    # partido: entre tramos (la comida) solo cuenta lo leído
    comidas = [(tramos[i][1], tramos[i + 1][0]) for i in range(len(tramos) - 1) if tramos[i + 1][0] > tramos[i][1]]
    if comidas:
        presencia = unir(activos + restar(presencia, comidas))
    descanso = turno.get('descanso') or 0
    if not descanso or not turno.get('continuo'):
        return presencia
    ini_t, fin_t = tramos[0]
    desde, hasta = max(presencia[0][0], ini_t), min(presencia[-1][1], fin_t)
    if hasta <= desde:
        return presencia
    # lo que ya no era presencia dentro del turno (huecos de 15 min o más) cuenta como descanso hecho
    hecho = _minutos(restar([(desde, hasta)], presencia))
    falta = descanso - hecho
    if falta <= 0:
        return presencia
    # el resto, de los huecos cortos (presencia sin leer) más largos dentro del turno
    cortos = [h for h in restar(restar(presencia, activos), [(fin_t, fin_t.replace(year=9999))]) if h[0] >= ini_t]
    quitar = []
    for a, b in sorted(cortos, key=lambda h: (h[0] - h[1], h[0])):
        m = (b - a).total_seconds() / 60.0
        if m <= 0:
            continue
        toma = min(m, falta)
        quitar.append((a, a + (b - a) * (toma / m)))
        falta -= toma
        if falta <= 1e-6:
            break
    return restar(presencia, unir(quitar)) if quitar else presencia


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


def color(uh_real, ritmo):
    """'ok' (verde) si llega al ritmo estandar, 'bajo' (rojo) si no; None si no hay u/h."""
    if uh_real is None:
        return None
    return 'ok' if uh_real >= ritmo else 'bajo'


def max_a_la_vez(intervalos_por_op):
    """Cuantos operarios a la vez como maximo (sus presencias)."""
    eventos = []
    for inters in intervalos_por_op:
        for a, b in inters:
            eventos.append((a, 1))
            eventos.append((b, -1))
    maximo = activos = 0
    for _dt, c in sorted(eventos, key=lambda x: (x[0], x[1])):     # a la misma hora, primero los que acaban
        activos += c
        maximo = max(maximo, activos)
    return maximo


def _orden_codigo(codigo):
    m = re.sub(r'\D', '', codigo or '')
    return (int(m) if m else 0, codigo or '')


def _uh(uds, minutos):
    return int(round(uds * 60.0 / minutos)) if minutos >= MIN_UH_HORA else None


def produccion(tareas, tz, filtrar=None, ritmo=RITMO_ESTANDAR, minutos_hueco=MINUTOS_HUECO, turnos=None):
    """Resumen por operario y hora. filtrar(tarea) -> bool: solo esas tareas (presencia = dentro de sus pedidos).
    minutos_hueco (v1.35): huecos sin hacer nada de estos minutos o mas no son presencia.
    turnos (v1.38.0): {op: comun.turno_de(entrada)}; sin filtro, la presencia descuenta sus descansos.
    Devuelve {horas: [7, 8, ...], operarios: [...], equipo: {...}, tipos: {tipo: n}, ritmo}."""
    tipos = {}
    for t in tareas:
        tipos[t.get('tipo') or 'otros'] = tipos.get(t.get('tipo') or 'otros', 0) + 1
    sel = [t for t in tareas if filtrar(t)] if filtrar else list(tareas)

    # presencia de cada operario (v1.35: tiempo leyendo + huecos cortos entre pedidos; sin filtro)
    por_op = {}
    for t in sel:
        por_op.setdefault(t['op'], []).append(t)
    presencia = {}
    for op, ts in por_op.items():
        activos = []
        for t in ts:
            activos += intervalos_activos(t['inicio'], t['fin'], t.get('huecos'))
        if filtrar:
            presencia[op] = unir(activos)
        else:
            presencia[op] = presencia_con_turno(unir(activos), unir_con_huecos(activos, minutos_hueco),
                                                (turnos or {}).get(op))

    ops = {}
    for t in sel:
        inter = intervalos_activos(t['inicio'], t['fin'], t.get('huecos'))
        mh = minutos_por_hora(inter, tz)
        lh = {}
        for fecha, cant in t.get('lecturas') or []:
            h = a_local(fecha, tz).hour
            lh[h] = lh.get(h, 0.0) + (cant or 0.0)
        uh, estimado = uds_por_hora(t.get('uds') or 0.0, lh, mh, a_local(t['inicio'], tz).hour)
        o = ops.setdefault(t['op'], {'op': t['op'], 'codigo': t.get('codigo') or '', 'horas': {}, 'pedidos': [],
                                     'uds': 0.0, 'efectivo': 0.0, 'estimado': False})
        for h in set(mh) | set(uh):
            c = o['horas'].setdefault(h, {'uds': 0.0, 'min': 0.0, 'pres': 0.0})
            c['uds'] += uh.get(h, 0.0)
            c['min'] += mh.get(h, 0.0)
        o['uds'] += t.get('uds') or 0.0
        o['efectivo'] += t.get('efectivo') or 0.0
        con_uds = (t.get('uds') or 0) > 0
        o['estimado'] = o['estimado'] or (estimado and con_uds)
        o['pedidos'].append({
            'ref': t.get('ref') or '', 'out_id': t.get('out_id') or False, 'estado': t.get('estado') or '',
            'tipo': t.get('tipo') or 'otros', 'ini': hhmm(t['inicio'], tz), 'fin': hhmm(t['fin'], tz),
            'uds': int(round(t.get('uds') or 0.0)), 'min': int(round(t.get('efectivo') or 0.0)),
            'min_total': int(round(t.get('minutos') or 0.0)),
            'uh': int(round(uds_hora_de(t.get('uds') or 0.0, t.get('efectivo') or 0.0))),
            'estimado': estimado and con_uds,
        })
    for op, o in ops.items():
        for h, m in minutos_por_hora(presencia.get(op) or [], tz).items():
            o['horas'].setdefault(h, {'uds': 0.0, 'min': 0.0, 'pres': 0.0})['pres'] += m
        o['presencia'] = sum((b - a).total_seconds() / 60.0 for a, b in presencia.get(op) or [])

    horas = sorted(set(h for o in ops.values() for h in o['horas']))
    equipo = {'horas': {}, 'uds': 0.0, 'efectivo': 0.0, 'presencia': 0.0}
    lista = []
    for clave in sorted(ops, key=lambda k: _orden_codigo(ops[k]['codigo'])):
        o = ops[clave]
        celdas = {}
        for h, c in o['horas'].items():
            pres = max(c['pres'], c['min'])        # presencia >= efectivo (por redondeos de segundos)
            e = equipo['horas'].setdefault(h, {'uds': 0.0, 'min': 0.0, 'pres': 0.0, 'personas': 0})
            e['uds'] += c['uds']
            e['min'] += c['min']
            e['pres'] += pres
            if pres > 0 or c['uds'] > 0:
                e['personas'] += 1
            uh_real = _uh(c['uds'], pres)
            celdas[str(h)] = {'uds': int(round(c['uds'])), 'min': int(round(c['min'])), 'pres': int(round(pres)),
                              'perdido': int(round(max(pres - c['min'], 0.0))), 'uh': _uh(c['uds'], c['min']),
                              'uh_real': uh_real, 'color': color(uh_real, ritmo)}
        pres_tot = max(o['presencia'], o['efectivo'])
        equipo['uds'] += o['uds']
        equipo['efectivo'] += o['efectivo']
        equipo['presencia'] += pres_tot
        uh_real = int(round(uds_hora_de(o['uds'], pres_tot)))
        lista.append({
            'op': o['op'], 'codigo': o['codigo'], 'celdas': celdas, 'pedidos': o['pedidos'],
            'uds': int(round(o['uds'])), 'efectivo': int(round(o['efectivo'])), 'presencia': int(round(pres_tot)),
            'perdido': int(round(max(pres_tot - o['efectivo'], 0.0))),
            'horas_ef': round(o['efectivo'] / 60.0, 2), 'horas_pres': round(pres_tot / 60.0, 2),
            'uh': int(round(uds_hora_de(o['uds'], o['efectivo']))), 'uh_real': uh_real,
            'color': color(uh_real if pres_tot >= MIN_UH_HORA else None, ritmo),
            'n_pedidos': len(o['pedidos']), 'estimado': o['estimado'],
        })
    eq_celdas = {}
    for h, e in equipo['horas'].items():
        uh_real = _uh(e['uds'], e['pres'])
        eq_celdas[str(h)] = {
            'uds': int(round(e['uds'])), 'min': int(round(e['min'])), 'pres': int(round(e['pres'])),
            'perdido': int(round(max(e['pres'] - e['min'], 0.0))), 'personas': e['personas'],
            'uh': _uh(e['uds'], e['min']), 'uh_real': uh_real, 'color': color(uh_real, ritmo),
        }
    todas = [p for p in presencia.values() if p]
    eq_uh_real = int(round(uds_hora_de(equipo['uds'], equipo['presencia'])))
    return {
        'horas': horas, 'operarios': lista, 'tipos': tipos, 'ritmo': ritmo,
        'equipo': {'celdas': eq_celdas, 'uds': int(round(equipo['uds'])),
                   'efectivo': int(round(equipo['efectivo'])), 'presencia': int(round(equipo['presencia'])),
                   'perdido': int(round(max(equipo['presencia'] - equipo['efectivo'], 0.0))),
                   'horas_ef': round(equipo['efectivo'] / 60.0, 2), 'horas_pres': round(equipo['presencia'] / 60.0, 2),
                   'uh': int(round(uds_hora_de(equipo['uds'], equipo['efectivo']))), 'uh_real': eq_uh_real,
                   'color': color(eq_uh_real if equipo['presencia'] >= MIN_UH_HORA else None, ritmo),
                   'operarios': len(lista), 'max_a_la_vez': max_a_la_vez(todas),
                   'inicio': hhmm(min(p[0][0] for p in todas), tz) if todas else '',
                   'fin': hhmm(max(p[-1][1] for p in todas), tz) if todas else ''},
        'min_uh_hora': MIN_UH_HORA,
    }

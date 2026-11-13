# -*- coding: utf-8 -*-
# =============================================================================
# Fase 1 - Medir las cajas REALES de las OUT ya cogidas.
#
# Definicion de "caja cerrada real" (aprobada el 11/11/2026):
# - Caja real: cada matricula (result_package_id) distinta en lineas sin cancelar con uds leidas.
# - Duena: si la usan varias OUT, cuenta UNA vez y para una sola OUT. Regla 'primera_linea' = la OUT de
#   la linea de menor id (la del Monitor, koroshi_monitor/controllers/main.py:143-152, y la de
#   koroshi_caja_existente._koroshi_dueno). Regla 'mas_uds' = la OUT con mas uds dentro (empate: menor id).
# - Caja compartida (la usan 2 o mas OUT): NUNCA es cerrada. Es justo juntar restos. La OUT pequena de
#   koroshi_caja_existente queda con 0 cajas propias y con cajas ajenas: tampoco es una OUT cerrada.
# - Caja cerrada real: no compartida y lo que lleva dentro llega a cierre_min de la caja (litros
#   estimados de lo que hay DE VERDAD dentro, no de lo previsto).
# - OUT cerrada real: tiene cajas propias, todas cerradas, ninguna uds en caja ajena y ninguna sin caja.
# =============================================================================
from . import volumen

REGLAS_DUENO = ('primera_linea', 'mas_uds')


def _nuevo_out():
    return {'uds': 0.0, 'litros': 0.0, 'cajas_reales': 0, 'cajas_cerradas': 0, 'cajas_compartidas': 0,
            'cajas_ajenas': 0, 'uds_en_ajenas': 0.0, 'uds_sin_caja': 0.0}


def medir(lineas, outs_medidas, medidas=None, regla_dueno='primera_linea'):
    """Mide cajas reales.

    lineas: lista de dicts {'id', 'out_id', 'caja_id' (o None), 'uds', 'litros'} con las lineas leidas
        (qty_done > 0, sin cancelar) de las OUT medidas y TAMBIEN las de otras OUT que usan sus cajas
        (si no, una caja compartida con una OUT de fuera pareceria no compartida).
    outs_medidas: ids de las OUT de las que se quiere el resultado.
    Devuelve (por_out, por_caja):
        por_out[out_id] = {'uds', 'litros', 'cajas_reales', 'cajas_cerradas', 'cajas_compartidas',
                           'cajas_ajenas', 'uds_en_ajenas', 'uds_sin_caja', 'cajas_estimadas',
                           'cerrada_estimada', 'cerrada'}
        por_caja[caja_id] = {'dueno', 'outs', 'compartida', 'uds', 'litros', 'llena', 'cerrada'}
    """
    if medidas is None:
        medidas = volumen.Medidas()
    if regla_dueno not in REGLAS_DUENO:
        raise ValueError('Regla de dueno desconocida: %s' % regla_dueno)
    medidas_set = set(outs_medidas)

    # Cajas: quien las usa, cuanto llevan y la primera linea de cada OUT
    por_caja = {}
    for ln in sorted(lineas, key=lambda x: x['id']):
        cid = ln.get('caja_id')
        if not cid:
            continue
        c = por_caja.setdefault(cid, {'uds_out': {}, 'min_id_out': {}, 'uds': 0.0, 'litros': 0.0})
        oid = ln['out_id']
        c['uds_out'][oid] = c['uds_out'].get(oid, 0.0) + ln['uds']
        if oid not in c['min_id_out']:
            c['min_id_out'][oid] = ln['id']
        c['uds'] += ln['uds']
        c['litros'] += ln['litros']

    resultado_cajas = {}
    for cid, c in por_caja.items():
        if regla_dueno == 'primera_linea':
            dueno = min(c['min_id_out'], key=lambda o: c['min_id_out'][o])
        else:
            dueno = min(c['uds_out'], key=lambda o: (-c['uds_out'][o], c['min_id_out'][o]))
        compartida = len(c['uds_out']) > 1
        llena = volumen.caja_llena(c['litros'], medidas)
        resultado_cajas[cid] = {
            'dueno': dueno,
            'outs': sorted(c['uds_out']),
            'compartida': compartida,
            'uds': c['uds'],
            'litros': c['litros'],
            'llena': llena,
            'cerrada': llena and not compartida,
        }

    # OUT medidas
    por_out = {}
    for oid in medidas_set:
        por_out[oid] = _nuevo_out()
    for ln in lineas:
        oid = ln['out_id']
        if oid not in medidas_set:
            continue
        r = por_out[oid]
        r['uds'] += ln['uds']
        r['litros'] += ln['litros']
        cid = ln.get('caja_id')
        if not cid:
            r['uds_sin_caja'] += ln['uds']
        elif resultado_cajas[cid]['dueno'] != oid:
            r['uds_en_ajenas'] += ln['uds']
    for cid, c in resultado_cajas.items():
        for oid in c['outs']:
            if oid not in medidas_set:
                continue
            r = por_out[oid]
            if c['dueno'] == oid:
                r['cajas_reales'] += 1
                if c['cerrada']:
                    r['cajas_cerradas'] += 1
                if c['compartida']:
                    r['cajas_compartidas'] += 1
            else:
                r['cajas_ajenas'] += 1
    for oid, r in por_out.items():
        r['cajas_estimadas'] = r['litros'] > volumen.EPS and volumen.cajas_de(r['litros'], medidas) or 0
        r['cerrada_estimada'] = volumen.cerrada(r['litros'], medidas)
        r['cerrada'] = bool(r['cajas_reales'] and r['cajas_cerradas'] == r['cajas_reales']
                            and not r['cajas_ajenas'] and r['uds_sin_caja'] <= volumen.EPS)
    return por_out, resultado_cajas


def causa_de(medida, prevision_conocida, previstas, estimadas, reales, compartidas, ajenas):
    """Diferencia (reales - previstas) y causa de una OUT medida. Devuelve (diferencia, causa)."""
    diferencia = prevision_conocida and medida and (reales - previstas) or 0
    if not medida:
        return diferencia, 'sin_medir'
    if not prevision_conocida:
        return diferencia, 'sin_prevision'
    if reales == previstas:
        return diferencia, 'ok'
    if compartidas or ajenas:
        return diferencia, 'caja_compartida'
    if estimadas != previstas:
        return diferencia, 'cogido'
    return diferencia, 'litros'


def pct(a, b):
    return b and round(100.0 * a / b, 1) or 0.0


def resumen(por_out, previstas=None):
    """Totales de un grupo de OUT y las causas de la diferencia entre cajas previstas y reales.

    previstas: {out_id: cajas previstas (CAJAS n de la nota o del reparto)} o None si no se sabe.
    Separa las OUT 'limpias' (ni cajas compartidas ni uds en cajas ajenas), donde la diferencia entre
    cajas estimadas con lo cogido y cajas reales es solo del modelo de litros, de las 'con caja
    compartida' (koroshi_caja_existente), donde ademas se juntan restos.
    """
    previstas = previstas or {}
    tot = {'outs': 0, 'outs_cerradas': 0, 'cajas_reales': 0, 'cajas_cerradas': 0, 'cajas_compartidas': 0,
           'uds': 0.0, 'litros': 0.0}
    grupos = {}
    for nombre in ('limpias', 'con_compartida'):
        grupos[nombre] = {'outs': 0, 'outs_con_prevision': 0, 'previstas': 0, 'estimadas': 0, 'reales': 0,
                          'reales_con_prevision': 0, 'estimadas_con_prevision': 0}
    for oid, r in por_out.items():
        if r['uds'] <= volumen.EPS:
            continue
        tot['outs'] += 1
        tot['outs_cerradas'] += r['cerrada'] and 1 or 0
        tot['cajas_reales'] += r['cajas_reales']
        tot['cajas_cerradas'] += r['cajas_cerradas']
        tot['cajas_compartidas'] += r['cajas_compartidas']
        tot['uds'] += r['uds']
        tot['litros'] += r['litros']
        g = grupos[(r['cajas_compartidas'] or r['cajas_ajenas']) and 'con_compartida' or 'limpias']
        g['outs'] += 1
        g['estimadas'] += r['cajas_estimadas']
        g['reales'] += r['cajas_reales']
        if previstas.get(oid) is not None:
            g['outs_con_prevision'] += 1
            g['previstas'] += previstas[oid]
            g['reales_con_prevision'] += r['cajas_reales']
            g['estimadas_con_prevision'] += r['cajas_estimadas']
    tot['pct_cajas_cerradas'] = pct(tot['cajas_cerradas'], tot['cajas_reales'])
    tot['pct_outs_cerradas'] = pct(tot['outs_cerradas'], tot['outs'])
    tot['grupos'] = grupos
    return tot

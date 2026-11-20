# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Base: lo que se repetia en los modulos KOROSHI (auditoria 13/11, fase 6).
# Python puro (sin Odoo) para poder probarlo sin servidor: tests/test_comun.py.
# Uso en un modulo que dependa de koroshi_base:
#     from odoo.addons.koroshi_base import comun
#     comun.COMPANY_ID, comun.TZ, comun.es_matricula(codigo), comun.rango_dia_utc(dia)...
# =============================================================================
import datetime
import re

import pytz

COMPANY_ID = 8                      # EFFECTIVE LOGISTICS, S.L. (KOROSHI, NAU-2)
TZ = 'Europe/Madrid'                # hora del almacen

# Matricula de caja: CJ + 9 cifras. Se compara en mayusculas (como el JS de las pantallas, que usa /i).
RE_CJ = re.compile(r'^CJ\d{9}$')


def es_matricula(codigo):
    """True si el codigo leido es una matricula de caja (CJ123456789), con o sin espacios y en minusculas."""
    return bool(RE_CJ.match((codigo or '').strip().upper()))


def zona():
    return pytz.timezone(TZ)


def ahora_local():
    """Ahora en la hora del almacen (datetime con zona)."""
    return datetime.datetime.now(pytz.utc).astimezone(zona())


def hoy_local():
    """El dia de hoy en la hora del almacen (no el del servidor, que va en UTC)."""
    return ahora_local().date()


def inicio_dia_utc(dia):
    """00:00 del dia en la hora del almacen, pasado a UTC sin zona (como guarda Odoo los Datetime)."""
    return zona().localize(datetime.datetime.combine(dia, datetime.time.min)).astimezone(pytz.utc).replace(tzinfo=None)


def rango_dia_utc(dia):
    """(inicio, fin) del dia en UTC sin zona, para buscar con >= inicio y < fin. El fin es las 00:00 del dia
    siguiente: los dias del cambio de hora duran 23 o 25 horas (no se suma un timedelta de 1 dia)."""
    return inicio_dia_utc(dia), inicio_dia_utc(dia + datetime.timedelta(days=1))


def rango_dias_utc(desde, hasta):
    """(inicio, fin) en UTC sin zona de desde 00:00 a hasta+1 00:00 (los dos dias incluidos)."""
    return inicio_dia_utc(desde), inicio_dia_utc(hasta + datetime.timedelta(days=1))


def a_local(dt_utc):
    """Datetime de Odoo (UTC sin zona) a la hora del almacen (con zona). None/False -> None."""
    if not dt_utc:
        return None
    if dt_utc.tzinfo is None:
        dt_utc = pytz.utc.localize(dt_utc)
    return dt_utc.astimezone(zona())


def dia_local(dt_utc):
    """Dia del almacen de un Datetime de Odoo (UTC sin zona)."""
    loc = a_local(dt_utc)
    return loc and loc.date() or None


# -----------------------------------------------------------------------------
# v1.1.0 (20/11/2026): turno por hora de entrada (Isaac: «si empiezas a las 8 harás de 8 a 13 y de 14 a 17; si
# empiezas a las 6, de 6 a 14 con una pausa de 15 min»). No hay tabla de turnos: lo decide la primera señal del día
# (primera tarea de Lecturas o primer tramo de Actividades). Regla en el parámetro koroshi_base.turnos, con el formato
#     <entra antes de> <tramos> [descanso=<min>]; <entra antes de> <tramos> ...
# Quien entra después de la última hora no tiene turno (camión, refuerzo): sin hora de fin.
# -----------------------------------------------------------------------------
PARAM_TURNOS = 'koroshi_base.turnos'
TURNOS = '07:00 06:00-14:00 descanso=15; 11:00 08:00-13:00,14:00-17:00'


def _hora(texto):
    h, m = (texto or '').strip().split(':')
    return datetime.time(int(h), int(m))


def leer_turnos(texto=None):
    """Texto del parámetro -> [(entra_antes_de, [(ini, fin)], descanso_min)] ordenado. Lo mal escrito se salta.
    Texto vacío o sin ninguna regla buena -> la regla por defecto (TURNOS)."""
    reglas = []
    for parte in (texto if texto is not None else TURNOS).split(';'):
        trozos = parte.split()
        if len(trozos) < 2:
            continue
        try:
            antes = _hora(trozos[0])
            tramos = []
            for t in trozos[1].split(','):
                ini, fin = t.split('-')
                ini, fin = _hora(ini), _hora(fin)
                if fin <= ini:
                    raise ValueError(t)
                tramos.append((ini, fin))
            descanso = 0
            for extra in trozos[2:]:
                if extra.startswith('descanso='):
                    descanso = max(int(extra.split('=', 1)[1]), 0)
        except (ValueError, IndexError):
            continue
        reglas.append((antes, sorted(tramos), descanso))
    if not reglas and texto is not None:
        return leer_turnos(None)
    return sorted(reglas, key=lambda r: r[0])


def texto_turnos(env):
    """El parámetro koroshi_base.turnos (o la regla por defecto). env = el de Odoo."""
    return env['ir.config_parameter'].sudo().get_param(PARAM_TURNOS) or TURNOS


def turno_de(entrada, texto=None):
    """Turno de quien entra a esa hora (Datetime de Odoo, UTC sin zona). None si entra después de la última regla.
    Devuelve, en UTC sin zona y del día de la entrada:
        {'tramos': [(ini, fin)], 'fin': fin del último tramo, 'descanso': min, 'continuo': un solo tramo,
         'nombre': '06:00-14:00' o '08:00-13:00 y 14:00-17:00'}"""
    loc = a_local(entrada)
    if not loc:
        return None
    for antes, tramos, descanso in leer_turnos(texto):
        if loc.time() < antes:
            dia = loc.date()

            def utc(h):
                return zona().localize(datetime.datetime.combine(dia, h)).astimezone(pytz.utc).replace(tzinfo=None)
            res = [(utc(a), utc(b)) for a, b in tramos]
            return {'tramos': res, 'fin': res[-1][1], 'descanso': descanso, 'continuo': len(res) == 1,
                    'nombre': ' y '.join('%s-%s' % (a.strftime('%H:%M'), b.strftime('%H:%M')) for a, b in tramos)}
    return None

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

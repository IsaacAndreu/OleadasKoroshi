# -*- coding: utf-8 -*-
# =============================================================================
# TUCTUC Base: lo común de los módulos de la PDA de la nave de Oriola - Amposta (odoo.tuctuc.com).
# Clon de koroshi_base 1.2.1 (decisión de Isaac del 27/11/2026: módulos nuevos tuctuc_*, los koroshi_* no se tocan).
# Python puro (sin Odoo) para poder probarlo sin servidor: tests/test_comun.py.
#     from odoo.addons.tuctuc_base import comun
#     comun.TZ, comun.rango_dia_utc(dia), comun.nombre_corto(ubicacion), comun.lista(texto)...
#
# Diferencia con koroshi_base: aquí NO hay compañía fija. La nave es una, pero en Odoo son tres compañías con su
# almacén (PRIME COLLECTIONS / WH-OR, MODA INTIMA / MODAI, UNITED BRANDS / UBRAN). La compañía sale siempre del
# documento (albarán, ubicación); los almacenes que usan la PDA están en el modelo tuctuc.almacen (almacen.py).
# =============================================================================
import datetime
import re

import pytz

TZ = 'Europe/Madrid'                # hora del almacén

# Caja de OUT: en Oriola la crea Odoo con la secuencia «Packages» (BOX + 7 cifras). Patrón por defecto; el parámetro
# tuctuc_base.patron_caja lo cambia.
PATRON_CAJA = r'^BOX\d{7}$'

# Valores por defecto de los parámetros (data/parametros.xml los crea con estos mismos valores)
PREFIJOS_EAN = '8447333,8435689'
PREFIJOS_CONTENEDOR = 'KO_,TT_,UB_'
TIPOS_OLEADA = 'WEB,WEB B&B,PED. INICIAL'


def lista(texto):
    """'a, b ,,c' -> ['a', 'b', 'c'] (los parámetros con varios valores van separados por comas)."""
    return [t.strip() for t in (texto or '').split(',') if t.strip()]


def es_caja(codigo, patron=None):
    """True si el código leído es una caja de OUT (BOX0699806), con o sin espacios y en minúsculas."""
    return bool(re.match(patron or PATRON_CAJA, (codigo or '').strip().upper()))


def empieza_por(codigo, prefijos):
    """El prefijo de la lista por el que empieza el código (en mayúsculas), o '' si ninguno."""
    codigo = (codigo or '').strip().upper()
    for p in prefijos or []:
        if p and codigo.startswith(p.upper()):
            return p
    return ''


def nombre_corto(ubicacion):
    """Nombre de una ubicación sin el almacén ni el stock delante, para la pantalla de la PDA:
    'WH-OR/Stock/N1/06298 - L75 P38 C2/KO_300726_755' -> 'N1/06298 - L75 P38 C2/KO_300726_755'.
    UBRAN escribe STOCK en mayúsculas: el corte no distingue mayúsculas. Sin '/Stock/', se quita solo el almacén."""
    nombre = ubicacion or ''
    m = re.search(r'/stock/', nombre, re.IGNORECASE)
    if m:
        return nombre[m.end():]
    return nombre.split('/', 1)[1] if '/' in nombre else nombre


def zona():
    return pytz.timezone(TZ)


def ahora_local():
    """Ahora en la hora del almacén (datetime con zona)."""
    return datetime.datetime.now(pytz.utc).astimezone(zona())


def hoy_local():
    """El día de hoy en la hora del almacén (no el del servidor, que va en UTC)."""
    return ahora_local().date()


def inicio_dia_utc(dia):
    """00:00 del día en la hora del almacén, pasado a UTC sin zona (como guarda Odoo los Datetime)."""
    return zona().localize(datetime.datetime.combine(dia, datetime.time.min)).astimezone(pytz.utc).replace(tzinfo=None)


def rango_dia_utc(dia):
    """(inicio, fin) del día en UTC sin zona, para buscar con >= inicio y < fin. El fin es las 00:00 del día
    siguiente: los días del cambio de hora duran 23 o 25 horas (no se suma un timedelta de 1 día)."""
    return inicio_dia_utc(dia), inicio_dia_utc(dia + datetime.timedelta(days=1))


def rango_dias_utc(desde, hasta):
    """(inicio, fin) en UTC sin zona de desde 00:00 a hasta+1 00:00 (los dos días incluidos)."""
    return inicio_dia_utc(desde), inicio_dia_utc(hasta + datetime.timedelta(days=1))


def a_local(dt_utc):
    """Datetime de Odoo (UTC sin zona) a la hora del almacén (con zona). None/False -> None."""
    if not dt_utc:
        return None
    if dt_utc.tzinfo is None:
        dt_utc = pytz.utc.localize(dt_utc)
    return dt_utc.astimezone(zona())


def dia_local(dt_utc):
    """Día del almacén de un Datetime de Odoo (UTC sin zona)."""
    loc = a_local(dt_utc)
    return loc and loc.date() or None


# -----------------------------------------------------------------------------
# Turno por hora de entrada (como koroshi_base 1.1.0). Lo decide la primera señal del día (primera tarea de Lecturas).
# Regla en el parámetro tuctuc_base.turnos, con el formato
#     <entra antes de> <tramos> [descanso=<min>]; <entra antes de> <tramos> ...
# Quien entra después de la última hora no tiene turno: sin hora de fin.
# OJO: el valor por defecto es el de NAU-2; falta confirmar los turnos de Oriola (se cambia en el parámetro).
# -----------------------------------------------------------------------------
PARAM_TURNOS = 'tuctuc_base.turnos'
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


def variantes_codigo(codigo):
    """El código leído y, si es un UPC de 12 cifras, con un 0 delante; si es un EAN de 13 que empieza por 0, sin él."""
    codigo = (codigo or '').strip()
    if not codigo:
        return []
    variantes = [codigo]
    if codigo.isdigit() and len(codigo) == 12:
        variantes.append('0' + codigo)
    if codigo.isdigit() and len(codigo) == 13 and codigo.startswith('0'):
        variantes.append(codigo[1:])
    return variantes

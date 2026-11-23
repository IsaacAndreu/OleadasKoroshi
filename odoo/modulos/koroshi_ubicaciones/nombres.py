# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Ubicaciones: nombres de huecos y contenedores (Python puro, sin Odoo, para probarlo sin servidor:
# tests/test_nombres.py).
#
# Cómo son en producción (leído el 23/11/2026):
#   - hueco antiguo: nombre «21048 - L142 P00 C1», código de barras «L142 P00 C1» (el número de delante no sirve:
#     se repite en UBRAN y WH). Los nuevos se llaman como los de muelle: «L181 P00 C1» (nombre = código de barras).
#   - hueco de muelle: «MU-04 P18 C1» (nombre = código de barras).
#   - contenedor: «KO_171126_001» (nombre = código de barras); el número vuelve a 001 cada día. También «TT_».
# =============================================================================
import re

PREFIJOS_CONTENEDOR = ('KO_', 'TT_')
MAX_UBICACIONES = 2000          # por tanda: un lineal grande tiene ~200 huecos; una tanda de contenedores, 100-700

RE_LINEAL = re.compile(r'^(?:L\s?(\d{1,4})|MU\s?-?\s?(\d{1,2}))$', re.I)
# hueco: con o sin número delante («21048 - L142 P00 C1», «L181 P00 C1», «MU-04 P18 C1»)
RE_HUECO = re.compile(r'^(?:\d+\s*-\s*)?(L\d{1,4}|MU-\d{2})\s+P(\d{1,3})\s+C(\d{1,2})$', re.I)
# volver a imprimir un lineal entero o un trozo: «L94», «L94 P10-P20», «L94 P10-20», «L94 P7», «MU-01»
RE_REIMP_LINEAL = re.compile(r'^(L\s?\d{1,4}|MU\s?-?\s?\d{1,2})(?:\s+P?(\d{1,3})(?:\s*-\s*P?(\d{1,3}))?)?$', re.I)
# contenedores: «KO_171126» (el día entero), «KO_171126_001-050», «KO_171126_001-KO_171126_050», «KO_171126_007»
RE_REIMP_CONT = re.compile(r'^((?:KO|TT)_\d{6})(?:_(\d{1,4})(?:\s*-\s*(?:(?:KO|TT)_\d{6}_)?(\d{1,4}))?)?$', re.I)


def lineal_normalizado(texto):
    """«l181» -> «L181»; «mu5», «MU 05», «MU-5» -> «MU-05». Si no es un lineal, None."""
    m = RE_LINEAL.match((texto or '').strip())
    if not m:
        return None
    if m.group(1) is not None:
        return 'L%d' % int(m.group(1))
    return 'MU-%02d' % int(m.group(2))


def nombre_hueco(lineal, p, c):
    """«L181», 5, 2 -> «L181 P05 C2» (como los huecos que ya hay: P con dos cifras, C con una)."""
    return '%s P%02d C%d' % (lineal, p, c)


def nombres_lineal(lineal, p_desde, p_hasta, c_desde, c_hasta):
    """Huecos de un lineal, por P y dentro de cada P por C (L181 P00 C1, P00 C2…, P01 C1…).
    Lanza ValueError con el motivo, en castellano, si algo no cuadra."""
    lin = lineal_normalizado(lineal)
    if not lin:
        raise ValueError('«%s» no es un lineal: escribe L181 o MU-05.' % (lineal or ''))
    if not (0 <= p_desde <= p_hasta <= 999):
        raise ValueError('Las posiciones van de P%02d a P%02d: la primera no puede ser mayor que la última.'
                         % (p_desde, p_hasta))
    if not (1 <= c_desde <= c_hasta <= 9):
        raise ValueError('Las alturas van de C1 a C9 y la primera no puede ser mayor que la última.')
    total = (p_hasta - p_desde + 1) * (c_hasta - c_desde + 1)
    if total > MAX_UBICACIONES:
        raise ValueError('Serían %d huecos: como mucho %d de una vez.' % (total, MAX_UBICACIONES))
    return [nombre_hueco(lin, p, c) for p in range(p_desde, p_hasta + 1) for c in range(c_desde, c_hasta + 1)]


def partes_hueco(nombre):
    """(lineal, p, c) de un hueco, con o sin número delante; None si el nombre no es de un hueco."""
    m = RE_HUECO.match((nombre or '').strip())
    if not m:
        return None
    return m.group(1).upper(), int(m.group(2)), int(m.group(3))


def clave_hueco(nombre):
    """Nombre sin el número de delante («21048 - L142 P00 C1» -> «L142 P00 C1»), para comparar viejos y nuevos."""
    partes = partes_hueco(nombre)
    return partes and nombre_hueco(*partes) or None


def prefijo_dia(prefijo, dia):
    """«KO_», 17/11/2026 -> «KO_171126_»."""
    if prefijo not in PREFIJOS_CONTENEDOR:
        raise ValueError('El prefijo de un contenedor es KO_ o TT_.')
    return '%s%s_' % (prefijo, dia.strftime('%d%m%y'))


def numero_contenedor(nombre, pref):
    """Número del contenedor si empieza por el prefijo del día («KO_171126_045» -> 45); None si no."""
    if not nombre or not nombre.upper().startswith(pref.upper()):
        return None
    resto = nombre[len(pref):]
    return int(resto) if resto.isdigit() else None


def siguiente_numero(nombres, pref):
    """El siguiente número libre del día: uno más que el mayor que ya existe (también archivados). 1 si no hay."""
    nums = [n for n in (numero_contenedor(x, pref) for x in nombres) if n is not None]
    return (max(nums) + 1) if nums else 1


def nombres_contenedores(pref, desde, cantidad):
    """«KO_171126_», 101, 3 -> KO_171126_101, _102, _103 (tres cifras, como ahora; a partir de 1000, las que haga falta)."""
    if not (1 <= cantidad <= MAX_UBICACIONES):
        raise ValueError('Se pueden crear de 1 a %d contenedores de una vez.' % MAX_UBICACIONES)
    return ['%s%03d' % (pref, n) for n in range(desde, desde + cantidad)]


def interpretar_reimpresion(texto):
    """Qué quiere volver a imprimir:
      {'tipo': 'lineal', 'lineal': 'L94', 'p_desde': 10, 'p_hasta': 20}   (sin P: p_desde = p_hasta = None)
      {'tipo': 'contenedores', 'prefijo': 'KO_171126_', 'desde': 1, 'hasta': 50}   (el día entero: None, None)
      {'tipo': 'nombre', 'nombre': '…'}   (un nombre o código de barras tal cual)
    """
    t = re.sub(r'\s+', ' ', (texto or '').strip())
    if not t:
        raise ValueError('Escribe qué quieres volver a imprimir: L94, L94 P10-P20, KO_171126_001-050…')
    m = RE_REIMP_LINEAL.match(t)
    if m:
        lin = lineal_normalizado(m.group(1))
        p1 = m.group(2) and int(m.group(2))
        p2 = m.group(3) and int(m.group(3))
        if p1 is not None and p2 is None:
            p2 = p1
        if p1 is not None and p1 > p2:
            p1, p2 = p2, p1
        return {'tipo': 'lineal', 'lineal': lin, 'p_desde': p1, 'p_hasta': p2}
    m = RE_REIMP_CONT.match(t)
    if m:
        pref = m.group(1).upper() + '_'
        n1 = m.group(2) and int(m.group(2))
        n2 = m.group(3) and int(m.group(3))
        if n1 is not None and n2 is None:
            n2 = n1
        if n1 is not None and n1 > n2:
            n1, n2 = n2, n1
        return {'tipo': 'contenedores', 'prefijo': pref, 'desde': n1, 'hasta': n2}
    return {'tipo': 'nombre', 'nombre': t}


def escapar_like(texto):
    """Para buscar con =like: «_» y «%» son comodines en SQL (KO_171126_ cogería KOX171126Y…)."""
    return (texto or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def resumen_lista(nombres, maximo=6):
    """«L181 P00 C1, L181 P00 C2 … L181 P20 C4» para enseñar en pantalla qué se va a crear."""
    if len(nombres) <= maximo:
        return ', '.join(nombres)
    return '%s … %s' % (', '.join(nombres[:maximo - 1]), nombres[-1])

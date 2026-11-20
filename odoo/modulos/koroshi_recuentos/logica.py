# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recuentos: lo que no necesita Odoo (Python puro, se prueba sin servidor: tests/test_logica.py).
# - modelo_de: «2621XC04», «2621XC04-000014-42» o «2621xc04 » -> «2621XC04».
# - partes: «2622JA00-000003-L» -> ('2622JA00', '000003', 'L').
# - clave_talla: orden de las tallas (XS, S, M, L, XL, XXL, 3XL... y las de número de menor a mayor).
# - clave_recorrido y hueco_corto: orden de los huecos por lineal, P y C («21995 - L128 P15 C2», «MU-01 P00 C1»).
# =============================================================================
import re

RE_L = re.compile(r'\bL(\d+)\s+P(\d+)(?:\s+C(\d+))?', re.I)
RE_MU = re.compile(r'\bMU-?(\d+)\s+P(\d+)(?:\s+C(\d+))?', re.I)
RE_DELANTE = re.compile(r'^\d+\s*-\s*')          # «21995 - L128 P15 C2» -> «L128 P15 C2»

TALLAS = ['XXXS', '3XS', 'XXS', '2XS', 'XS', 'XS/S', 'S', 'S/M', 'M', 'M/L', 'L', 'L/XL', 'XL', 'XXL', '2XL',
          'XXXL', '3XL', '4XL', '5XL', '6XL', 'U', 'TU', 'UNICA', 'ÚNICA']
ORDEN_TALLAS = {t: i for i, t in enumerate(TALLAS)}


def modelo_de(texto):
    """El modelo (lo que va antes del primer «-»), en mayúsculas y sin espacios."""
    t = (texto or '').strip().upper()
    return t.split('-')[0].strip()


def partes(nombre):
    """(modelo, color, talla) del nombre o la referencia de una variante. Si no tiene las tres partes, el color es
    lo que haya en medio y la talla lo último (o vacío)."""
    trozos = [p.strip() for p in (nombre or '').strip().upper().split('-')]
    if len(trozos) >= 3:
        return trozos[0], '-'.join(trozos[1:-1]), trozos[-1]
    if len(trozos) == 2:
        return trozos[0], '', trozos[1]
    return trozos[0], '', ''


def clave_talla(talla):
    """Orden de las tallas: primero las de letra en su orden, luego las de número de menor a mayor, luego el resto."""
    t = (talla or '').strip().upper()
    if t in ORDEN_TALLAS:
        return (0, ORDEN_TALLAS[t], '')
    num = t.replace(',', '.')
    try:
        return (1, float(num), '')
    except ValueError:
        pass
    m = re.match(r'^(\d+(?:\.\d+)?)', num)          # «42/44», «38-40»
    if m:
        return (1, float(m.group(1)), t)
    return (2, 0, t)


def clave_recorrido(nombre):
    """Orden del recorrido: lineales L por número, P y C; después los de MU; después el resto por nombre."""
    n = (nombre or '').strip()
    m = RE_L.search(n)
    if m:
        return (0, int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), n)
    m = RE_MU.search(n)
    if m:
        return (1, int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), n)
    return (2, 0, 0, 0, n.upper())


def hueco_corto(nombre):
    """El nombre del hueco sin el número de delante: «21995 - L128 P15 C2» -> «L128 P15 C2»."""
    return RE_DELANTE.sub('', (nombre or '').strip())

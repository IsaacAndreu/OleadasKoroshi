# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Prenda en el suelo - lo que no necesita Odoo (pruebas en tests/test_logica.py, sin servidor).
# Diseño: bin/versiones/diseno-prenda-en-el-suelo_2026-11-20.md
#
# Las «paradas» son las de koroshi_preparacion/models/ruta.py: (pasillo, x en metros) o None si la ubicación no es
# un lineal. La distancia en metros la da ruta.distancia(a, b); aquí se pasa como función para poder probarlo sin
# Odoo.
# =============================================================================

MINUTOS_ACTIVA = 20        # una tarea «en curso» sin leer más de esto no cuenta como «la está haciendo ahora»
MINUTOS_POSICION = 30      # la última lectura de quien la encuentra sirve como «dónde estoy» durante este tiempo
MAX_PERSONAS = 3
MAX_SIN_EMPEZAR = 3
MAX_HUECOS = 3

CASOS = [
    ('A', 'Faltante pendiente'),
    ('B', 'A un compañero (OUT haciéndose)'),
    ('C', 'A su hueco (OUT sin empezar)'),
    ('D', 'A su hueco (no la pide nadie)'),
    ('E', 'Sin hueco en Odoo'),
    ('X', 'Código no encontrado'),
]


def metros(distancia, a, b):
    """Metros entre dos paradas, o None si falta alguna."""
    if not a or not b:
        return None
    return round(distancia(a, b))


def cerca_de(distancia, origen, paradas):
    """Los metros más cortos desde origen a cualquiera de las paradas (None si no se puede saber)."""
    res = [metros(distancia, origen, p) for p in paradas]
    res = [m for m in res if m is not None]
    return min(res) if res else None


def ordenar_personas(personas, distancia, origen):
    """personas: [{'actual': parada|None, 'siguiente': parada|None, 'minutos': min desde su última lectura|None, ...}].
    Añade 'metros' (desde origen hasta donde está o hacia donde va, lo más cerca) y las ordena: primero las que se
    sabe a cuántos metros están (las más cerca antes); después, las de lectura más reciente."""
    for p in personas:
        p['metros'] = cerca_de(distancia, origen, [p.get('actual'), p.get('siguiente')]) if origen else None

    def clave(p):
        m = p['metros']
        minutos = p.get('minutos')
        return (m is None, m if m is not None else 0, minutos is None, minutos if minutos is not None else 0)
    return sorted(personas, key=clave)


def ordenar_huecos(huecos, distancia, origen):
    """huecos: [{'parada': parada|None, 'uds': n, 'nombre': ...}]. Añade 'metros' y ordena: los más cerca primero
    (si se sabe dónde está quien la encontró); si no, los que más uds tienen."""
    for h in huecos:
        h['metros'] = metros(distancia, origen, h.get('parada')) if origen else None

    def clave(h):
        m = h['metros']
        return (m is None, m if m is not None else 0, -(h.get('uds') or 0), h.get('nombre') or '')
    return sorted(huecos, key=clave)


def caso(faltantes, personas, sin_empezar, huecos):
    """La primera orden que se cumple (A-E)."""
    if faltantes:
        return 'A'
    if personas:
        return 'B'
    if sin_empezar:
        return 'C'
    if huecos:
        return 'D'
    return 'E'


def texto_minutos(minutos):
    """3 -> 'hace 3 min'; 0 -> 'ahora mismo'; None -> ''."""
    if minutos is None:
        return ''
    minutos = int(round(minutos))
    if minutos <= 0:
        return 'ahora mismo'
    if minutos < 60:
        return 'hace %d min' % minutos
    return 'hace %d h %02d min' % (minutos // 60, minutos % 60)


def texto_metros(m):
    if m is None:
        return ''
    return 'aquí al lado' if m <= 3 else 'a unos %d m' % m

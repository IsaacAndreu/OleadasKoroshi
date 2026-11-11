# -*- coding: utf-8 -*-
# =============================================================================
# v3.13: RUTA ÓPTIMA por la NAU-2 (menos metros andando).
#
# Geometría de la nave (la del plano de koroshi_warehouse_map, apuntes sobre el plano del 29/10/2026):
#   - Lineales L01-L136 en parejas espalda con espalda (L01-02, L03-04...). Cada pareja ocupa 2 m (estantería
#     doble 1 m + pasillo 1 m). El pasillo de picking queda entre L02|L03, L04|L05...: el lineal l da al pasillo
#     l // 2 (L01 da a la zona de muelles, «pasillo» 0).
#   - Posiciones P01-P36 a lo largo del lineal, 1,2 m cada una. P01 empieza a 5 m de la fachada; pasillos
#     transversales después de P03 (3 m), entre P17 y P18 (pasillo central, 3 m) y después de P24 (3 m), más el
#     espacio delante de P01 y al final de P36.
#   - Los muelles (expedición) están del lado de L01: se sale de ahí y se vuelve ahí.
#   - La altura (C1-C4) no cuenta: es la misma parada.
#
# Distancia andando entre dos paradas:
#   - mismo pasillo: lo que hay en horizontal;
#   - pasillo distinto: ir hasta el transversal que salga más corto, cruzar los pasillos (2 m cada uno) y volver.
# Orden: vecino más cercano desde los muelles y después 2-opt (se deshacen los cruces) con vuelta a muelles.
# =============================================================================
import re

# «28035 - L44 P17 C2» o «L58 P21 C1»; NO «N1-L07 P10 C1» (zona N1: no se sabe dónde está, va al final)
RE_LPC = re.compile(r'(?:^|/|-\s)L(\d+)\s+P(\d+)(?:\s+C(\d+))?')
RE_MU = re.compile(r'(?:^|/)MU-\d+')
ANCHO_P = 1.2
PASILLOS_X = (2.5, 10.1, 29.9, 41.3, 58.5)   # centros de los pasillos transversales (m desde la fachada)
ENTRE_PASILLOS = 2.0                           # m entre un pasillo de picking y el siguiente
MUELLES = (0, 29.9)                            # zona de muelles, por el pasillo central
ZONA_MU = (0, 40.0)                            # ubicaciones MU-: encima de los muelles 15-18 (plano)
_CACHE = {}
_CACHE_MAX = 500


def _x(p):
    """Centro de la posición P (m desde la fachada)."""
    if p <= 17:
        x = 5.0 + (p - 1) * ANCHO_P + (3.0 if p >= 4 else 0.0)
    else:
        x = 31.4 + (p - 18) * ANCHO_P + (3.0 if p >= 25 else 0.0)
    return round(x + ANCHO_P / 2, 2)


def lpc(nombre):
    """'EFFEC/Stock/NAVE2/28035 - L44 P17 C2/KO_110626_032' -> (44, 17, 2); None si no lo tiene."""
    m = RE_LPC.search(nombre or '')
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def parada(nombre):
    """(pasillo, x) donde se para el operario para coger de esa ubicación; None si no es un lineal."""
    t = lpc(nombre)
    if not t:
        return ZONA_MU if RE_MU.search(nombre or '') else None
    return t[0] // 2, _x(t[1])


def distancia(a, b):
    if a[0] == b[0]:
        return abs(a[1] - b[1])
    cruzar = ENTRE_PASILLOS * abs(a[0] - b[0])
    return cruzar + min(abs(a[1] - c) + abs(b[1] - c) for c in PASILLOS_X)


def ordenar(paradas):
    """Las paradas en el orden que menos se anda (saliendo de los muelles y volviendo). Lista de paradas."""
    puntos = sorted(set(p for p in paradas if p))
    if len(puntos) <= 1:
        return puntos
    clave = tuple(puntos)
    if clave in _CACHE:
        return list(_CACHE[clave])
    todos = [MUELLES] + puntos
    n = len(todos)
    d = [[distancia(todos[i], todos[j]) for j in range(n)] for i in range(n)]
    # vecino más cercano desde los muelles (0)
    camino = [0]
    libres = set(range(1, n))
    while libres:
        u = camino[-1]
        v = min(libres, key=lambda j: (d[u][j], j))
        camino.append(v)
        libres.discard(v)
    camino.append(0)
    # 2-opt: dar la vuelta a un tramo si así se anda menos (los muelles quedan fijos al principio y al final)
    mejora = True
    vueltas = 0
    while mejora and vueltas < 60:
        mejora = False
        vueltas += 1
        for i in range(1, n - 1):
            for k in range(i + 1, n):
                a, b, c, e = camino[i - 1], camino[i], camino[k], camino[k + 1]
                if d[a][c] + d[b][e] < d[a][b] + d[c][e] - 1e-9:
                    camino[i:k + 1] = reversed(camino[i:k + 1])
                    mejora = True
    camino = camino[1:-1]
    # la vuelta tiene dos sentidos iguales de largos: se empieza por la punta más cerca de los muelles
    if d[0][camino[-1]] < d[0][camino[0]]:
        camino.reverse()
    res = [todos[i] for i in camino]
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[clave] = tuple(res)
    return res


def metros(paradas_en_orden):
    """Metros de la ruta (muelles -> paradas -> muelles), para comparar."""
    camino = [MUELLES] + [p for p in paradas_en_orden if p] + [MUELLES]
    return round(sum(distancia(camino[i], camino[i + 1]) for i in range(len(camino) - 1)), 1)

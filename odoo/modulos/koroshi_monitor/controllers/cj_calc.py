# -*- coding: utf-8 -*-
# =============================================================================
# v1.45.0 (25/11/2026): «Etiquetas CJ sin leer» (Isaac: «Lo de les etiquetes saltades per al cap de zona al monitor
# m'agradaria que ho pogués veure»). Python puro, sin Odoo: tests/test_cj_calc.py.
#
# Cada etiqueta de zona se imprime para una OUT concreta (zebra.label con la nota 'ETQ ZONA <OUT>', ver
# koroshi_zonas/models/etiquetas.py). Una etiqueta esta «sin leer» si:
#   - su OUT ya esta validada (asi no salen las que aun se estan preparando),
#   - la OUT tiene al menos otra etiqueta suya leida en Odoo (si no tiene ninguna, la OUT no se preparo con estas
#     etiquetas: se reimprimieron, se junto con otra... y no es este caso),
#   - y la CJ no existe en Odoo (ningun paquete con ese nombre) ni la ha quitado un jefe con «La he tirado».
# Caso que lo motivo (25/11, K1 S-6665004772): dos cajas fisicas y en Odoo las 23 uds en la CJ665013811; la
# CJ665013810, pegada en la segunda caja, no se leyo nunca.
#
# v1.46.0 (25/11/2026, aprobado por Isaac: «Lo resto m'agrada»):
#   - «¿Dos cajas en una CJ?»: cajas cuyo volumen (suma de volumen del articulo x uds hechas) pasa el umbral de su
#     tipo de caja. La CJ665013811 de K1 sumaba 0,149 m3; partida, 0,076 + 0,073. Datos 24-25/11, CAJA 600X400X400:
#     p50 0,080, p90 0,098, p98 0,107, max 0,131. Articulos sin volumen: la media de los que si tienen.
#   - En «Etiquetas CJ sin leer», primero las de OUT con una caja leida por encima del umbral (K45 25/11: la 803
#     con 0,131 m3 y la 804 sin leer).
#   - Capacidad real por tipo de caja (7 dias): p50, p90, p98 y maximo, para la barra de llenado de Lecturas.
# =============================================================================
NOTA = 'ETQ ZONA '
UMBRAL_DEFECTO = 0.11


def umbrales(texto, defecto=UMBRAL_DEFECTO):
    """'CAJA 600X400X400=0,11; CAJA KOROSHI MEDIANA=0.10; *=0.11' -> {'CAJA 600X400X400': 0.11, ..., '*': 0.11}.
    Lo que no se entiende se ignora; sin '*' vale `defecto`."""
    res = {'*': defecto}
    for trozo in (texto or '').replace('\n', ';').split(';'):
        if '=' not in trozo:
            continue
        tipo, valor = trozo.rsplit('=', 1)
        try:
            res[tipo.strip().upper() or '*'] = float(valor.strip().replace(',', '.'))
        except ValueError:
            continue
    return res


def umbral_de(tipo, tabla):
    return tabla.get((tipo or '').strip().upper(), tabla.get('*', UMBRAL_DEFECTO))


def volumenes(lineas, vol_producto):
    """lineas: [(caja, id articulo, uds)]; vol_producto: {id: m3 por ud} (0/None = sin volumen).
    Devuelve ({caja: m3}, media usada para los articulos sin volumen)."""
    con = [v for v in vol_producto.values() if v and v > 0]
    media = con and sum(con) / len(con) or 0.0
    res = {}
    for caja, prod, uds in lineas:
        v = vol_producto.get(prod)
        res[caja] = res.get(caja, 0.0) + (v if v and v > 0 else media) * (uds or 0)
    return res, media


def percentil(valores, q):
    """Por rango mas cercano (el mismo que se uso para sacar los datos del 25/11)."""
    if not valores:
        return 0.0
    v = sorted(valores)
    return v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]


def capacidad(vol_caja, tipo_caja):
    """[{tipo, n, p50, p90, p98, max}] por tipo de caja, de mas a menos cajas."""
    por_tipo = {}
    for caja, m3 in vol_caja.items():
        por_tipo.setdefault(tipo_caja.get(caja) or '(sin tipo)', []).append(m3)
    res = [{'tipo': t, 'n': len(v), 'p50': round(percentil(v, .5), 3), 'p90': round(percentil(v, .9), 3),
            'p98': round(percentil(v, .98), 3), 'max': round(max(v), 3)} for t, v in por_tipo.items()]
    res.sort(key=lambda r: (-r['n'], r['tipo']))
    return res


def dos_cajas(vol_caja, tipo_caja, tabla, info_caja):
    """Cajas por encima del umbral de su tipo: [{cj, tipo, m3, umbral, tienda, pedido, zona, hora}], la mas llena
    primero. info_caja: {cj: {tienda, pedido, zona, hora}}."""
    res = []
    for caja, m3 in vol_caja.items():
        tipo = tipo_caja.get(caja) or ''
        u = umbral_de(tipo, tabla)
        if m3 > u:
            i = info_caja.get(caja) or {}
            res.append({'cj': caja, 'tipo': tipo, 'm3': round(m3, 3), 'umbral': u, 'tienda': i.get('tienda') or '',
                        'pedido': i.get('pedido') or '', 'zona': i.get('zona') or '', 'hora': i.get('hora') or ''})
    res.sort(key=lambda r: (-r['m3'], r['cj']))
    return res


def saltadas(etiquetas, leidas, outs, descartadas, uds_caja, vol_caja=None, llenas=None):
    """etiquetas: [(cj, nota)]; leidas: set de CJ que existen como paquete; outs: {nombre OUT: dict con 'id',
    'estado', 'tienda', 'pedido', 'zona', 'hora'}; descartadas: set de CJ quitadas a mano; uds_caja: {cj: uds};
    vol_caja: {cj: m3}; llenas: set de CJ por encima de su umbral.
    Devuelve [{cj, out, out_id, tienda, pedido, zona, hora, leidas: [(cj, uds, m3, llena)], max_uds, max_m3, llena}]:
    primero las de OUT con una caja leida por encima del umbral, luego de mas a menos llena."""
    vol_caja = vol_caja or {}
    llenas = llenas or set()
    por_out = {}
    for cj, nota in etiquetas:
        if not (nota or '').startswith(NOTA):
            continue
        por_out.setdefault(nota[len(NOTA):].strip(), []).append(cj)
    res = []
    for nombre, cjs in por_out.items():
        o = outs.get(nombre)
        if not o or o.get('estado') != 'done':
            continue
        si = sorted([c for c in cjs if c in leidas])
        if not si:
            continue
        cajas = [(c, uds_caja.get(c, 0), round(vol_caja.get(c, 0.0), 3), c in llenas) for c in si]
        max_uds = max([c[1] for c in cajas] or [0])
        max_m3 = max([c[2] for c in cajas] or [0.0])
        llena = any([c[3] for c in cajas])
        for cj in sorted(cjs):
            if cj in leidas or cj in descartadas:
                continue
            res.append({'cj': cj, 'out': nombre, 'out_id': o.get('id'), 'tienda': o.get('tienda') or '',
                        'pedido': o.get('pedido') or '', 'zona': o.get('zona') or '', 'hora': o.get('hora') or '',
                        'leidas': cajas, 'max_uds': max_uds, 'max_m3': max_m3, 'llena': llena})
    res.sort(key=lambda r: (not r['llena'], -r['max_m3'], -r['max_uds'], r['zona'], r['cj']))
    return res

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
# CJ665013810, pegada en la segunda caja, no se leyo nunca. Por eso salen primero las que tienen la caja leida mas
# llena: es lo mas probable que esconda una segunda caja.
# =============================================================================
NOTA = 'ETQ ZONA '


def saltadas(etiquetas, leidas, outs, descartadas, uds_caja):
    """etiquetas: [(cj, nota)]; leidas: set de CJ que existen como paquete; outs: {nombre OUT: dict con 'id',
    'estado', 'tienda', 'pedido', 'zona', 'hora'}; descartadas: set de CJ quitadas a mano; uds_caja: {cj: uds}.
    Devuelve [{cj, out, out_id, tienda, pedido, zona, hora, leidas: [(cj, uds)], max_uds}] de mas a menos llena."""
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
        cajas = [(c, uds_caja.get(c, 0)) for c in si]
        maximo = max([u for _c, u in cajas] or [0])
        for cj in sorted(cjs):
            if cj in leidas or cj in descartadas:
                continue
            res.append({'cj': cj, 'out': nombre, 'out_id': o.get('id'), 'tienda': o.get('tienda') or '',
                        'pedido': o.get('pedido') or '', 'zona': o.get('zona') or '', 'hora': o.get('hora') or '',
                        'leidas': cajas, 'max_uds': maximo})
    res.sort(key=lambda r: (-r['max_uds'], r['zona'], r['cj']))
    return res

# -*- coding: utf-8 -*-
# =============================================================================
# Anonimiza un fichero de "Datos de entrada" de una ejecucion (campo datos_entrada) para guardarlo en
# tests/datos/. Cambia el nombre de la tienda (K12 - LO QUE SEA -> K12 - TIENDA12) y el pedido (S-... ->
# PED-0001) de forma consistente. No cambia nada que use el calculo: el numero K, las OUT, ubicaciones,
# articulos, cantidades y el orden se quedan igual.
#   python tests/anonimizar.py entrada.json tests/datos/AAAAMMDD_descripcion.json
# =============================================================================
import json
import re
import sys

RE_K = re.compile(r'^K(\d+)')


def anonimizar(datos):
    tiendas = {}
    pedidos = {}
    for o in datos['outs']:
        nombre = o.get('partner_name') or ''
        if nombre not in tiendas:
            m = RE_K.match(nombre)
            tiendas[nombre] = m and 'K%s - TIENDA%s' % (m.group(1), m.group(1)) or (
                nombre and 'CLIENTE%d' % (len(tiendas) + 1) or '')
        o['partner_name'] = tiendas[nombre]
        origen = o.get('origin') or ''
        if origen and origen not in pedidos:
            pedidos[origen] = 'PED-%04d' % (len(pedidos) + 1)
        o['origin'] = origen and pedidos[origen] or ''
    return datos


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as f:
        d = json.load(f)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(anonimizar(d), f, ensure_ascii=False)

# -*- coding: utf-8 -*-
# =============================================================================
# Fase 3, modo sombra: compara el reparto que ha calculado el modulo (zona de cada linea reservada) con el
# que ha hecho de verdad el cron 202 (accion 1883): la zona de la agrupacion donde ha quedado cada linea.
# Las lineas conservan su id al partir (la 1883 cambia su picking_id, no las recrea).
# =============================================================================


def comparar(modulo, real):
    """modulo: {ml_id: zona} del modulo. real: {ml_id: zona} de lo partido por el 202 (las lineas de las
    agrupaciones de zona de hoy). Devuelve dict con iguales, distintas [(ml, zona_modulo, zona_202)],
    solo_modulo [ml] y solo_202 [ml]."""
    iguales = 0
    distintas = []
    solo_modulo = []
    for ml, zona in modulo.items():
        if ml not in real:
            solo_modulo.append(ml)
        elif real[ml] == zona:
            iguales += 1
        else:
            distintas.append((ml, zona, real[ml]))
    solo_202 = [ml for ml in real if ml not in modulo]
    return {'iguales': iguales, 'distintas': sorted(distintas), 'solo_modulo': sorted(solo_modulo),
            'solo_202': sorted(solo_202)}


def es_igual(res):
    return not res['distintas'] and not res['solo_modulo'] and not res['solo_202'] and res['iguales'] > 0


def texto(res, prefijo_modulo, prefijos_202):
    lin = []
    estado = es_igual(res) and 'IGUAL' or 'DISTINTO'
    lin.append('KOROSHI ZONAS - SOMBRA: el modulo comparado con el cron 202 -> %s' % estado)
    lin.append('Agrupaciones: modulo %s<zona> | cron 202 %s' % (prefijo_modulo, ', '.join(prefijos_202) or 'ninguna'))
    lin.append('Lineas reservadas: misma zona %d | zona distinta %d | solo en el modulo %d | solo en el 202 %d' % (
        res['iguales'], len(res['distintas']), len(res['solo_modulo']), len(res['solo_202'])))
    if res['distintas']:
        lin.append('')
        lin.append('Zona distinta (linea | modulo | cron 202):')
        for ml, zm, zr in res['distintas'][:40]:
            lin.append('   %s | %s | %s' % (ml, zm, zr))
        if len(res['distintas']) > 40:
            lin.append('   ... y %d mas' % (len(res['distintas']) - 40))
    if res['solo_modulo'] or res['solo_202']:
        lin.append('')
        lin.append('Lineas que solo estan en uno de los dos (OUT que entraron o salieron entre los dos calculos): '
                   'modulo %s | 202 %s' % (res['solo_modulo'][:20], res['solo_202'][:20]))
    return '\n'.join(lin)

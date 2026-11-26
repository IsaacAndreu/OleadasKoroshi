# -*- coding: utf-8 -*-
# =============================================================================
# v1.9.0 (26/11/2026). Cuantas zonas de lineal hacer cada dia. Python puro.
# Isaac (26/11): «lo que de verdad decidiria el numero de zonas cada dia [...] probar 3, 4 y 5 zonas a las 04:50 y
# quedarse con la que acaba antes». Se calcula el reparto (en DIAGNOSTICO, no escribe) con cada numero y se elige
# el que acaba antes. Si otro con MENOS zonas acaba casi igual (MARGEN_MIN), ese: menos zonas = menos fronteras y
# menos lineas fuera de su zona. Con los datos del 26/11: ritmo 52/21 -> 4 zonas (13:51); ritmo 31/53 -> 3 (12:42).
# Las zonas de muelle (MU1, MU2) no cambian: se suman a las de lineal.
# =============================================================================
from . import v12f

MARGEN_MIN = 10


def zonas_muelle(cambios):
    """Zonas de muelle que lleva el total de 'Zonas' de la configuracion (2 con el muelle fijo MU1 + MU2)."""
    fijo = cambios.get('MUELLE_FIJO', [('1', '/N1-'), ('2', '')])
    return fijo and len(fijo) or 0


def candidatos(texto):
    """'3, 4,5' -> [3, 4, 5] (sin repetidos, de menor a mayor, solo de 1 a 9)."""
    res = set()
    for t in (texto or '').replace(';', ',').split(','):
        t = t.strip()
        if t.isdigit() and 1 <= int(t) <= 9:
            res.add(int(t))
    return sorted(res)


def elegir(datos, cambios, contexto, lineales, margen=MARGEN_MIN):
    """Prueba el reparto con cada numero de zonas de lineal de 'lineales'. Devuelve (zonas totales elegidas o None,
    [{'lineal', 'zonas', 'fin' (min desde las 00:00), 'cajas' (% cerradas), 'estado'}])."""
    muelle = zonas_muelle(cambios)
    opciones = []
    for n in lineales:
        cam = dict(cambios, MODO='DIAGNOSTICO', ZONAS=n + muelle)
        ctx = dict(contexto or {})
        ctx.pop('zonas', None)
        rep = v12f.repartir(datos, cam, ctx)
        op = {'lineal': n, 'zonas': n + muelle, 'estado': rep.estado, 'fin': None, 'cajas': None}
        if rep.estado == 'listo':
            op['fin'] = rep.ini_min + rep.fin / 60.0
            for l in rep.lineas:
                if 'v12 (caja cerrada)' in l and 'cerradas' in l:
                    try:
                        op['cajas'] = int(l.rsplit('cerradas', 1)[1].strip().rstrip('%'))
                    except ValueError:
                        pass
        opciones.append(op)
    buenas = [o for o in opciones if o['fin'] is not None]
    if not buenas:
        return None, opciones
    mejor = min(buenas, key=lambda o: (o['fin'], o['lineal']))
    for o in sorted(buenas, key=lambda o: o['lineal']):
        if o['lineal'] < mejor['lineal'] and o['fin'] <= mejor['fin'] + margen:
            mejor = o
            break
    return mejor['zonas'], opciones


def lineas_elegir(elegidas, opciones):
    """Lineas 'ZONAS DEL DIA: ...' para el informe y el correo."""
    if not opciones:
        return []
    partes = []
    for o in opciones:
        if o['fin'] is None:
            partes.append('%d de lineal: %s' % (o['lineal'], o['estado']))
        else:
            partes.append('%d de lineal: acaba %s, %s%% cajas cerradas%s' % (
                o['lineal'], v12f.reloj(o['fin']), o['cajas'] if o['cajas'] is not None else '?',
                o['zonas'] == elegidas and ' <- ELEGIDA' or ''))
    if elegidas is None:
        return ['ZONAS DEL DIA: ninguna opcion se puede partir (%s). Se usa la configuracion.' % '; '.join(partes)]
    lineal = [o['lineal'] for o in opciones if o['zonas'] == elegidas][0]
    return ['ZONAS DEL DIA: %d de lineal (la que acaba antes; con menos zonas si acaba a menos de %d min). %s.' % (
        lineal, MARGEN_MIN, '; '.join(partes))]

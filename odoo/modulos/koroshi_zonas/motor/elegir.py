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
# v1.10.0 (Isaac 26/11: «No vull picos ni caixes que no estiguen tancades»)
PICO_MAX = 30                # min entre la primera y la ultima zona de lineal que acaban
MARGEN_CAJAS = 5             # cajas abiertas por partir de mas que la mejor opcion


def pico_y_cajas(rep):
    """v1.10.0. (pico en min entre la zona de lineal que acaba antes y la que acaba despues, cajas abiertas por
    partir). Abiertas por partir = trozos de OUT cuya ultima caja no se llena, menos las tiendas cuyo pedido entero
    ya no la llena (esas salen abiertas se reparta como se reparta)."""
    otras = rep.parametros.get('ZONA_OTRAS', 'MU')
    zx = rep.R.get('zx_de', {}) if getattr(rep, 'R', None) else {}
    fines = [rep.seg_z[zn] + zx.get(zn, 0.0) for zn in rep.orden_zonas
             if not zn.startswith(otras) and zn in rep.seg_z and rep.seg_z[zn] > 0]
    pico = fines and (max(fines) - min(fines)) / 60.0 or 0.0
    abiertas = inevitables = 0
    c = rep.calc
    for pid, por_z, _principal, _sin, _caja in rep.plan:
        abiertas += len([zn for zn in por_z if not por_z[zn][3]])
        if not c.cerrada(c.litros_de(c.mls_out[pid])):
            inevitables += 1
    return pico, max(abiertas - inevitables, 0)


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
        op = {'lineal': n, 'zonas': n + muelle, 'estado': rep.estado, 'fin': None, 'cajas': None, 'pico': None,
              'por_partir': None}
        if rep.estado == 'listo':
            op['fin'] = rep.ini_min + rep.fin / 60.0
            op['pico'], op['por_partir'] = pico_y_cajas(rep)
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
    # v1.10.0: primero cajas (no mas de MARGEN_CAJAS abiertas por partir que la mejor) y sin picos (PICO_MAX); de
    # las que quedan, la que acaba antes. Si ninguna queda sin pico, la de menos pico (y se avisa).
    min_cajas = min(o['por_partir'] for o in buenas)
    for o in opciones:
        o['fuera'] = ''
        if o['fin'] is None:
            continue
        if o['por_partir'] > min_cajas + MARGEN_CAJAS:
            o['fuera'] = 'cajas'
        elif o['pico'] > PICO_MAX:
            o['fuera'] = 'pico'
    validas = [o for o in buenas if not o['fuera']]
    if not validas:
        cajas_ok = [o for o in buenas if o['fuera'] != 'cajas'] or buenas
        mejor = min(cajas_ok, key=lambda o: (o['pico'], o['lineal']))
        mejor['sin_pico'] = False
        return mejor['zonas'], opciones
    buenas = validas
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
            extra = ''
            if o.get('pico') is not None:
                extra = ', pico %d min, %d cajas abiertas por partir' % (round(o['pico']), o['por_partir'])
            motivo = {'pico': ' (pico de mas de %d min)' % PICO_MAX,
                      'cajas': ' (mas de %d cajas abiertas por partir que la mejor)' % MARGEN_CAJAS}.get(
                          o.get('fuera'), '')
            partes.append('%d de lineal: acaba %s, %s%% cajas cerradas%s%s%s' % (
                o['lineal'], v12f.reloj(o['fin']), o['cajas'] if o['cajas'] is not None else '?', extra,
                o['zonas'] == elegidas and ' <- ELEGIDA' or '', o['zonas'] != elegidas and motivo or ''))
    if elegidas is None:
        return ['ZONAS DEL DIA: ninguna opcion se puede partir (%s). Se usa la configuracion.' % '; '.join(partes)]
    elegida = [o for o in opciones if o['zonas'] == elegidas][0]
    if elegida.get('sin_pico') is False:
        return ['AVISO: ninguna opcion de zonas sale sin picos (mas de %d min entre zonas); se coge la de menos pico.'
                % PICO_MAX,
                'ZONAS DEL DIA: %d de lineal (la de menos pico). %s.' % (elegida['lineal'], '; '.join(partes))]
    return ['ZONAS DEL DIA: %d de lineal (sin picos de mas de %d min ni mas cajas abiertas; la que acaba antes, con '
            'menos zonas si acaba a menos de %d min). %s.' % (elegida['lineal'], PICO_MAX, MARGEN_MIN, '; '.join(partes))]

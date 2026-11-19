# -*- coding: utf-8 -*-
# =============================================================================
# v1.5.0 (19/11/2026). Tiempos: lo previsto y lo real. Python puro, sin Odoo.
#
# A) Aviso de hora de fin: con el reparto calculado, a que hora se acaba con las personas de la configuracion y
#    cuantas personas harian falta en cada zona para acabar a la hora de fin. No cambia el reparto.
#    Trabajo de una zona = segundos de la zona con su equipo x personas del equipo (seg_z * pers): asi lo
#    reparte evaluar.repartir_personas. Personas que hacen falta = trabajo / tiempo disponible, redondeado hacia
#    arriba, al menos 1 por zona.
# B) Previsto contra real: con las lecturas de la PDA (hora exacta, uds y operario) de las OUT de cada zona, la
#    hora de la primera lectura, la del 95 % de las uds, la de la ultima y cuantas personas han leido. Se compara
#    la DURACION real (primera -> ultima lectura) con la prevista: la hora de inicio real no la sabe el reparto.
# =============================================================================
import math

PCT_COLA = 0.95


def reloj(minutos):
    minutos = int(round(minutos))
    return '%d:%02d' % (minutos // 60, minutos % 60)


def prevision(rep):
    """Lo previsto por zona del reparto (motor.modelo.Reparto), para guardarlo y compararlo despues.
    Devuelve {'inicio': min desde las 00:00, 'fin': min, 'zonas': {zona: {'min': duracion, 'pers': n}}}."""
    zonas = {}
    for zn in rep.orden_zonas:
        zonas[zn] = {'min': round(rep.seg_z.get(zn, 0.0) / 60.0, 1), 'pers': rep.pers.get(zn, 0)}
    return {'inicio': rep.ini_min, 'fin': round(rep.ini_min + rep.fin / 60.0, 1), 'zonas': zonas}


def personas_necesarias(rep, fin_min):
    """Personas por zona para acabar a fin_min (minutos desde las 00:00) empezando a rep.ini_min.
    Devuelve (total, {zona: personas}) o (None, {}) si no se puede calcular (sin equipos por zona o sin tiempo)."""
    disponible = (fin_min - rep.ini_min) * 60.0
    if not rep.pers or disponible <= 0:
        return None, {}
    por_zona = {}
    for zn in rep.orden_zonas:
        trabajo = rep.seg_z.get(zn, 0.0) * rep.pers.get(zn, 1)
        por_zona[zn] = max(1, int(math.ceil(trabajo / disponible - 1e-9)))
    return sum(por_zona.values()), por_zona


def lineas_aviso(rep, fin_min, personas):
    """Lineas 'HORA DE FIN: ...' para el informe y el correo. Vacio si no hay reparto."""
    if rep.estado != 'listo' or not rep.orden_zonas:
        return []
    fin_prev = rep.ini_min + rep.fin / 60.0
    lineas = []
    if fin_prev <= fin_min + 0.5:
        lineas.append('HORA DE FIN: con %d personas se acaba a las %s (antes de las %s).' % (
            personas, reloj(fin_prev), reloj(fin_min)))
    else:
        lineas.append('HORA DE FIN: con %d personas se acaba a las %s, %d min DESPUES de las %s.' % (
            personas, reloj(fin_prev), int(round(fin_prev - fin_min)), reloj(fin_min)))
    total, por_zona = personas_necesarias(rep, fin_min)
    if total is not None and fin_prev > fin_min + 0.5:
        detalle = ', '.join('%s %d' % (zn, por_zona[zn]) for zn in rep.orden_zonas)
        lineas.append('HORA DE FIN: para acabar a las %s harian falta %d personas (%s), %d mas.' % (
            reloj(fin_min), total, detalle, total - personas))
    return lineas


def resumen_lecturas(lecturas):
    """lecturas: [(minuto local desde las 00:00 del dia, uds, operario)] de una zona.
    Devuelve {'uds', 'inicio', 'cola' (95 % de las uds), 'fin', 'personas'} o None si no hay lecturas."""
    lecturas = sorted([x for x in lecturas if x[1] > 0], key=lambda x: x[0])
    if not lecturas:
        return None
    total = sum(x[1] for x in lecturas)
    acum = 0.0
    cola = lecturas[-1][0]
    for minuto, uds, quien in lecturas:
        acum += uds
        if acum >= total * PCT_COLA - 1e-9:
            cola = minuto
            break
    personas = set(x[2] for x in lecturas if x[2])
    return {'uds': total, 'inicio': lecturas[0][0], 'cola': cola, 'fin': lecturas[-1][0], 'personas': len(personas)}


def comparar(previsto, real_zonas, personas_dia):
    """previsto: lo de prevision() (o None). real_zonas: {zona: resumen_lecturas}. personas_dia: operarios
    distintos en todas las zonas. Devuelve (lineas de informe, {'inicio', 'fin', 'personas', 'desvio'}).
    desvio = minutos de la duracion real de la zona mas larga menos la prevista (positivo = mas lenta)."""
    lineas = ['PREVISTO CONTRA REAL (lecturas de la PDA, hora del almacen):']
    reales = [r for r in real_zonas.values() if r]
    if not reales:
        lineas.append('   Sin lecturas de la PDA en estas OUT.')
        return lineas, {}
    ini = min(r['inicio'] for r in reales)
    fin = max(r['fin'] for r in reales)
    if previsto:
        lineas.append('   Previsto: empezar a las %s y acabar a las %s (%d min). Real: primera lectura %s, ultima %s '
                      '(%d min). %d personas leyendo.' % (
                          reloj(previsto['inicio']), reloj(previsto['fin']), round(previsto['fin'] - previsto['inicio']),
                          reloj(ini), reloj(fin), round(fin - ini), personas_dia))
    else:
        lineas.append('   Sin prevision guardada (la sombra de ese dia es anterior a la 1.5.0). Real: primera lectura '
                      '%s, ultima %s (%d min). %d personas leyendo.' % (reloj(ini), reloj(fin), round(fin - ini),
                                                                         personas_dia))
    lineas.append('   Zona | previsto: min y personas | real: empieza, 95 %, acaba | min | personas | uds | diferencia')
    zonas_prev = previsto and previsto.get('zonas') or {}
    desvio = None
    largo_prev = previsto and max([z['min'] for z in zonas_prev.values()] or [0]) or 0
    largo_real = 0
    for zn in sorted(set(list(real_zonas.keys()) + list(zonas_prev.keys()))):
        r = real_zonas.get(zn)
        zp = zonas_prev.get(zn)
        prev_txt = zp and ('%4d min, %d pers.' % (round(zp['min']), zp['pers'])) or '      -        '
        if not r:
            lineas.append('   %-5s | %s | sin lecturas' % (zn, prev_txt))
            continue
        dur = r['fin'] - r['inicio']
        largo_real = max(largo_real, dur)
        dif = zp and ('%+d min' % round(dur - zp['min'])) or ''
        lineas.append('   %-5s | %s | %s, %s, %s | %4d min | %d | %d | %s' % (
            zn, prev_txt, reloj(r['inicio']), reloj(r['cola']), reloj(r['fin']), round(dur), r['personas'],
            r['uds'], dif))
    if previsto and zonas_prev:
        desvio = int(round(largo_real - largo_prev))
        lineas.append('   Zona mas larga: prevista %d min, real %d min (%+d min).' % (
            round(largo_prev), round(largo_real), desvio))
    return lineas, {'inicio': ini, 'fin': fin, 'personas': personas_dia, 'desvio': desvio}

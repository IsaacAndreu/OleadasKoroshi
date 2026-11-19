# -*- coding: utf-8 -*-
# =============================================================================
# La v12f (accion 1883, 10/11/2026) como funcion pura: datos planos -> Reparto.
# Copia LITERAL del calculo y del informe (lineas 109-965). Lo que la accion hacia con Odoo
# (buscar OUT, partir, agrupar, nota) lo hacen models/lector.py y models/escritor.py.
# Fase 2: tiene que dar EXACTAMENTE el mismo reparto (zona de cada linea) y el mismo informe que la 1883.
# No arreglar nada aqui: lo que se cambie, en la fase 4 y fuera de este fichero.
#
# v1.3.0 (14/11/2026, auditoria 13/11 fase 5): tres cambios, todos con parametro. Con modelo.COMO_1883 el resultado
# sigue siendo EXACTAMENTE el de la 1883 (tests/test_v12f_igual_1883.py):
#   - ORDEN_URGENCIA: si no cabe todo (sin UNA_RONDA), entran primero las OUT de dias anteriores (la mas antigua
#     antes) y las tiendas de 48 h; antes, siempre por numero de tienda y las de numero alto se quedaban fuera.
#     Las que entran se montan y numeran por tienda como siempre (montar_una ya las ordena por tienda).
#   - Las OUT de dias anteriores (las marca el lector con 'de_antes') salen contadas en el informe.
#   - AVISO_HORA_FIN: con UNA_RONDA no se mira la capacidad; ahora el informe avisa si se acaba despues de HORA_FIN.
# =============================================================================
import datetime

from . import modelo
from .evaluar import Calculo, clave_orden, numero_k


def minutos(hhmm):
    return int(hhmm.split(':')[0]) * 60 + int(hhmm.split(':')[1])


def reloj(mins):
    mins = int(round(mins))
    return '%d:%02d' % (mins // 60, mins % 60)


def lineal_de(complete_name):
    segmentos = (complete_name or '').split('/')
    for idx in range(len(segmentos) - 1, -1, -1):
        texto = segmentos[idx].strip()
        if ' - ' in texto:
            texto = texto.split(' - ', 1)[1]
        if len(texto) > 1 and texto[0] == 'L' and texto[1].isdigit():
            num = ''
            for ch in texto[1:]:
                if ch.isdigit():
                    num += ch
                else:
                    break
            return num and int(num) or 0
    return 0


def pct(a, b):
    return b and round(100.0 * a / b) or 0


def repartir(datos, cambios=None, contexto=None):
    """Calcula el reparto de la v12f. datos: ver motor/modelo.py. contexto: el de la accion
    (personas, hora_inicio, hora_fin, una_ronda, zonas, zonas_muelle, prueba_ids, prueba_agrupacion).
    Devuelve un modelo.Reparto (con el informe en .lineas)."""
    contexto = contexto or {}
    p = modelo.parametros(cambios, contexto)
    MODO = p['MODO']
    PERSONAS = p['PERSONAS']
    ZONAS = p['ZONAS']
    ZONA_OTRAS = p['ZONA_OTRAS']
    PREFIJO_AGRUPACION = p['PREFIJO_AGRUPACION']
    POR_ZONA = float(PERSONAS) / ZONAS
    if p['MUELLE_FIJO'] and p['MUELLE_EQUIPO_PROPIO']:
        POR_ZONA = 1.0

    calc = Calculo(p)
    R_out = modelo.Reparto()

    ahora_local = datetime.datetime.strptime(datos['ahora'], '%Y-%m-%d %H:%M:%S')
    hoy = ahora_local.strftime('%d%m')
    ini_min = p['HORA_INICIO'] == 'AHORA' and (ahora_local.hour * 60 + ahora_local.minute) or minutos(p['HORA_INICIO'])
    fin_min = minutos(p['HORA_FIN'])
    capacidad = (fin_min - ini_min) * 60.0
    calc.capacidad = capacidad
    calc.seg_lect = p['SEG_LECTURA'] / p['RENDIMIENTO'] / POR_ZONA
    calc.seg_lin = p['SEG_LINEAL'] / p['RENDIMIENTO'] / POR_ZONA
    sorter_id = datos.get('sorter_id')

    # ---------------- 1. OUT candidatas -------------------------------------------
    prueba_agr = contexto.get('prueba_agrupacion')
    if contexto.get('prueba_ids'):
        MODO = 'DIAGNOSTICO'
        prueba_agr = 'IDS'
        PREFIJO_AGRUPACION = ''
    elif prueba_agr:
        MODO = 'DIAGNOSTICO'
        PREFIJO_AGRUPACION = prueba_agr
    candidatas = datos['outs']
    validas = []
    saltadas = list(datos.get('saltadas_lector') or [])     # v1.3.0: las que el lector no ha pasado
    for p_ in candidatas:
        motivo = ''
        tipo = p_['tipo_pedido'] or ''
        if p_['company_id'] != p['COMPANY_ID'] or p_['picking_type_code'] != 'outgoing':
            motivo = 'no es una OUT de la empresa %d' % p['COMPANY_ID']
        elif tipo != p['TIPO_PEDIDO']:
            motivo = 'tipo de pedido %s' % (tipo or 'sin tipo')
        elif p_['state'] != 'assigned' and not prueba_agr:
            motivo = 'no esta Preparada (%s)' % p_['state']
        elif p_['batch_name'] and not (p_['batch_name'] or '').startswith(PREFIJO_AGRUPACION):
            motivo = 'esta en la agrupacion %s' % p_['batch_name']
        elif sorter_id and p_['location_id'] == sorter_id:
            motivo = 'sale del SORTER'
        elif not prueba_agr:
            for ml in p_['lineas']:
                if ml['qty_done'] > 0:
                    motivo = 'ya tiene unidades leidas'
                    break
                if sorter_id and ml['location_id'] == sorter_id:
                    motivo = 'tiene lineas reservadas en el SORTER'
                    break
        if motivo:
            saltadas.append('%s (%s): %s' % (p_['name'], p_['partner_name'] or '', motivo))
            continue
        validas.append(p_)

    # ---------------- 2. Prioridad y coste de cada OUT por pasillo -----------------
    seg_lect = calc.seg_lect
    seg_lin = calc.seg_lin
    prio = []
    for p_ in validas:
        calc.out_rec[p_['id']] = p_
        cp = {}
        zx = {}
        uds = 0.0
        vistos_lect = {}
        vistos_lin = {}
        calc.mls_out[p_['id']] = []
        for ml in p_['lineas']:
            qty = ml['qty']
            if prueba_agr and ml['qty_done'] > qty:
                qty = ml['qty_done']
            if qty <= 0:
                continue
            uds += qty
            calc.qty_ml[ml['id']] = qty
            calc.ml_rec[ml['id']] = ml
            calc.mls_out[p_['id']].append(ml['id'])
            lineal = lineal_de(ml['location_complete_name'])
            seg = 0.0
            clave_lect = (ml['location_id'], ml['product_id'])
            if clave_lect not in vistos_lect:
                vistos_lect[clave_lect] = 1
                seg += seg_lect
            if lineal:
                pasillo = lineal // 2
                if lineal not in vistos_lin:
                    vistos_lin[lineal] = 1
                    seg += seg_lin
                cp[pasillo] = cp.get(pasillo, 0.0) + seg
                calc.info_ml[ml['id']] = (pasillo, lineal, '')
            else:
                hueco_nombre = ml['location_name']
                hueco_completo = ml['location_complete_name']
                if (hueco_nombre or '')[:3] in ('KO_', 'TT_') and ml['parent_id']:
                    hueco_completo = ml['parent_complete_name']
                clave_h = '%s | %s' % (hueco_completo or '', ml['default_code'] or ml['product_id'])
                zx[clave_h] = zx.get(clave_h, 0.0) + seg
                calc.info_ml[ml['id']] = (-1, 0, clave_h)
            calc.seg_ml[ml['id']] = seg
        calc.coste_out[p_['id']] = cp
        calc.zx_out[p_['id']] = zx
        calc.uds_out[p_['id']] = uds
        # v1.6.0: con ORDEN_PEDIDO, por numero de pedido (S-6665...); sin el, por tienda como la 1883 (knum)
        prio.append((clave_orden(p, p_), '', 0, p_['name'], p_['id']))
    if p['ORDEN_URGENCIA'] and not p['UNA_RONDA']:
        # v1.3.0: primero las de dias anteriores (la mas antigua antes), despues las tiendas de 48 h, despues el
        # resto; dentro de cada grupo, por pedido (v1.6.0) o por tienda. Con UNA_RONDA entran todas.
        urg = []
        for x in prio:
            q = calc.out_rec[x[4]]
            antes = q.get('de_antes') and (q.get('create_date') or '')[:10] or '9999-99-99'
            k48 = numero_k(q['partner_name'] or '') in p['TIENDAS_48H']
            urg.append((antes, not k48 and 1 or 0) + x)
        urg.sort()
        prio = [x[2:] for x in urg]
    else:
        prio.sort()
    orden = []
    for x in prio:
        orden.append(x[4])

    uds_por_pedido = {}
    for p_ in validas:
        clave_p = p_['origin'] or p_['name']
        uds_por_pedido[clave_p] = uds_por_pedido.get(clave_p, 0.0) + calc.uds_out[p_['id']]
    orden_ok = []
    for pid in orden:
        q = calc.out_rec[pid]
        if uds_por_pedido[q['origin'] or q['name']] < p['MIN_UDS_PEDIDO']:
            saltadas.append('%s (%s): pedido de %d uds (menos de %d)' % (
                q['name'], q['partner_name'] or '', uds_por_pedido[q['origin'] or q['name']], p['MIN_UDS_PEDIDO']))
            continue
        orden_ok.append(pid)
    orden = orden_ok
    calc.orden = orden

    # ---------------- cuantas zonas de muelle ----------------
    if p['MUELLE_FIJO']:
        calc.ZONAS_MUELLE = p['MUELLE_EQUIPO_PROPIO'] and len(p['MUELLE_FIJO']) or 0
    if calc.ZONAS_MUELLE == 'AUTO':
        hay_zx = False
        for pid in orden:
            if calc.zx_out[pid]:
                hay_zx = True
                break
        mejor_m = 0
        if hay_zx and ZONAS > 1:
            mejor_d = 0.0
            for m in range(0, ZONAS):
                calc.ZONAS_MUELLE = m
                d = calc.evaluar(len(orden), {})[0]
                if m == 0 or d < mejor_d - 0.001:
                    mejor_d = d
                    mejor_m = m
        calc.ZONAS_MUELLE = mejor_m
    if calc.ZONAS_MUELLE >= ZONAS:
        calc.ZONAS_MUELLE = ZONAS - 1
    ZONAS_MUELLE = calc.ZONAS_MUELLE

    # ---------------- 4. Cuantas caben antes de HORA_FIN ----------------
    lo = 0
    hi = len(orden)
    if p['UNA_RONDA']:
        lo = hi
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if calc.montar(mid)['fin'] <= capacidad:
            lo = mid
        else:
            hi = mid - 1
    R = calc.montar(lo)
    entran = orden[:lo]
    no_entran = orden[lo:]
    elegidas = R['pids']
    orden_zonas = R['orden_zonas']
    hace_zx = R['hace_zx']
    zona_ml = R['zona_ml']
    grupos = R['grupos']
    qty_ml = calc.qty_ml
    info_ml = calc.info_ml
    mls_out = calc.mls_out
    uds_out = calc.uds_out
    litros_de = calc.litros_de
    cajas_de = calc.cajas_de
    cerrada = calc.cerrada
    CIERRE_MIN = p['CIERRE_MIN']
    LITROS_CAJA = p['LITROS_CAJA']

    # ---------------- 5. Plan por OUT y comparacion con la v9c ------------------------
    datos_zona = {}
    for zn in orden_zonas:
        datos_zona[zn] = {'seg': R['seg_z'][zn], 'uds': 0.0, 'cajas': 0, 'outs': {}, 'fuera': 0.0, 'lmin': 9999, 'lmax': 0}
    plan = []
    v9 = {'outs': 0, 'cerradas': 0, 'peq': 0}
    v12 = {'outs': 0, 'cerradas': 0, 'cajas': 0, 'peq': 0, 'tiendas_resto': 0}
    i = 0
    for pid in elegidas:
        p_ = calc.out_rec[pid]
        por_z = {}
        for zn in orden_zonas:
            if (pid, zn) not in grupos:
                continue
            mls_z = grupos[(pid, zn)]
            l_z = litros_de(mls_z)
            u_z = 0.0
            for x in mls_z:
                u_z += qty_ml[x]
                if zona_ml[x] != zn:
                    datos_zona[zn]['fuera'] += qty_ml[x]
                lin = info_ml[x][1]
                if lin and not zn.startswith(ZONA_OTRAS):
                    if lin < datos_zona[zn]['lmin']:
                        datos_zona[zn]['lmin'] = lin
                    if lin > datos_zona[zn]['lmax']:
                        datos_zona[zn]['lmax'] = lin
            por_z[zn] = [cajas_de(l_z), u_z, l_z, cerrada(l_z)]
            datos_zona[zn]['uds'] += u_z
            datos_zona[zn]['cajas'] += por_z[zn][0]
            datos_zona[zn]['outs'][pid] = 1
            v12['outs'] += 1
            v12['cajas'] += por_z[zn][0]
            if por_z[zn][3]:
                v12['cerradas'] += 1
            if l_z < CIERRE_MIN * LITROS_CAJA:
                v12['peq'] += 1
        if not cerrada(litros_de(mls_out[pid])):
            v12['tiendas_resto'] += 1
        trozo = {}
        for x in mls_out[pid]:
            zn = zona_ml[x]
            trozo[zn] = trozo.get(zn, 0.0) + calc.lit_ml(x)
        for zn in trozo:
            v9['outs'] += 1
            if cerrada(trozo[zn]):
                v9['cerradas'] += 1
            if trozo[zn] < CIERRE_MIN * LITROS_CAJA:
                v9['peq'] += 1
        reservado = 0.0
        for x in mls_out[pid]:
            reservado += qty_ml[x]
        demanda = p_['demanda']
        principal = ''
        mejor = -1.0
        for zn in orden_zonas:
            if zn in por_z and por_z[zn][1] > mejor:
                mejor = por_z[zn][1]
                principal = zn
        plan.append((pid, por_z, principal, demanda - reservado, i + 1))
        i += 1

    existentes = [nb for nb in (datos.get('lotes_existentes') or []) if nb.startswith('Z-%s-' % hoy)]
    prefijo = 'Z-%s-' % hoy
    if existentes:
        n_r = 2
        hay = True
        while hay:
            hay = False
            for nb in existentes:
                if nb.startswith('Z-%s-R%d-' % (hoy, n_r)):
                    hay = True
            if hay:
                n_r += 1
        prefijo = 'Z-%s-R%d-' % (hoy, n_r)

    # ---------------- Resumen ------------------------------------------------------
    POR_ZONA_TXT = POR_ZONA
    uds_entran = 0.0
    for pid in entran:
        uds_entran += uds_out[pid]
    uds_fuera = 0.0
    for pid in no_entran:
        uds_fuera += uds_out[pid]
    lineas = []
    lineas.append('KOROSHI PARTIR OUT ZONAS v12 CAJA CERRADA - %s' % MODO)
    lineas.append('Objetivo: %d personas en %d zonas (%d de lineal + %d de muelle, ~%.1f personas por zona) de %s a %s (%d min) | ritmo x%.2f (%d s/lectura, %d s/lineal por OUT)' % (
        PERSONAS, ZONAS, ZONAS - ZONAS_MUELLE, ZONAS_MUELLE, POR_ZONA_TXT, reloj(ini_min), reloj(fin_min), (fin_min - ini_min),
        p['RENDIMIENTO'], p['SEG_LECTURA'], p['SEG_LINEAL']))
    lineas.append('OUT validas: %d (%d uds) | ENTRAN: %d (%d uds) | no entran (pendientes para otra tanda): %d (%d uds) | saltadas %d' % (
        len(orden), uds_entran + uds_fuera, len(entran), uds_entran, len(no_entran), uds_fuera, len(saltadas)))
    n_antes = len([pid for pid in entran if calc.out_rec[pid].get('de_antes')])
    if n_antes or len([pid for pid in no_entran if calc.out_rec[pid].get('de_antes')]):
        # v1.3.0
        lineas.append('OUT de dias anteriores (la 1883 ya no las cogia): entran %d | no entran %d' % (
            n_antes, len([pid for pid in no_entran if calc.out_rec[pid].get('de_antes')])))
    lineas.append('Acaba previsto: %s (la zona mas larga; con la v9c seria %s) | agrupaciones %s<zona>' % (
        reloj(ini_min + R['fin'] / 60.0), reloj(ini_min + R['dur9'] / 60.0), prefijo))
    if R.get('pers'):
        lineas[-1] = 'Acaba previsto: %s (la zona mas larga) | agrupaciones %s<zona>' % (reloj(ini_min + R['fin'] / 60.0), prefijo)
        lineas[1] = lineas[1].replace(', ~%.1f personas por zona' % POR_ZONA_TXT, ', personas segun el trabajo de cada zona')
        reparto_txt = []
        for zn in orden_zonas:
            reparto_txt.append('%s %d' % (zn, R['pers'][zn]))
        lineas.append('Personas por zona (todas empiezan a la vez): %s' % ', '.join(reparto_txt))
    pasa_min = 0
    if p['AVISO_HORA_FIN'] and p['UNA_RONDA'] and elegidas and R['fin'] > capacidad:
        # v1.3.0: con todo en una ronda no se mira la capacidad; por lo menos, decirlo
        pasa_min = int(round((R['fin'] - capacidad) / 60.0))
        lineas.append('AVISO: con "Todo en una ronda" se acaba a las %s, %d min despues de la hora de fin (%s).' % (
            reloj(ini_min + R['fin'] / 60.0), pasa_min, reloj(fin_min)))
    lineas.append('')
    lineas.append('CAJA CERRADA (cajas de %d L; una OUT esta en caja cerrada si su ultima caja llega al %d%%):' % (
        LITROS_CAJA, round(CIERRE_MIN * 100)))
    lineas.append('   v9c (zonas sin mirar cajas): %d OUT | en caja cerrada %d (%d%%) | OUT pequenas (menos de una caja): %d' % (
        v9['outs'], v9['cerradas'], pct(v9['cerradas'], v9['outs']), v9['peq']))
    lineas.append('   v12 (caja cerrada):          %d OUT | en caja cerrada %d (%d%%) | OUT pequenas: %d | cajas %d, cerradas %d%%' % (
        v12['outs'], v12['cerradas'], pct(v12['cerradas'], v12['outs']), v12['peq'], v12['cajas'],
        pct(v12['cajas'] - (v12['outs'] - v12['cerradas']), v12['cajas'])))
    lineas.append('   Tiendas cuyo pedido entero ya deja la ultima caja sin llenar: %d de %d (esa caja va en una de sus OUT)' % (
        v12['tiendas_resto'], len(plan)))
    lineas.append('   %d uds se cogen fuera de su zona (lineas de la frontera movidas para cerrar cajas)' % R['fuera'])
    lineas.append('')
    for zn in orden_zonas:
        d = datos_zona[zn]
        if zn.startswith(ZONA_OTRAS):
            if not d['uds']:
                continue
            quien = hace_zx.get(zn) and ('la hace %s al acabar la suya' % hace_zx[zn]) or ('equipo fijo del muelle, acaba ~%s' % reloj(
                ini_min + d['seg'] / 60.0))
            lineas.append('Zona %s | fuera de lineal | %d uds | %d cajas | %d OUT | ~%d min (%s)' % (
                zn, d['uds'], d['cajas'], len(d['outs']), round(d['seg'] / 60.0), quien))
            if R.get('pers'):
                lineas[-1] += ' | %d personas' % R['pers'].get(zn, 0)
            continue
        tramo = d['lmax'] and ('L%d-L%d' % (d['lmin'], d['lmax'])) or 'sin lineas'
        fin_z = ini_min + (d['seg'] + R['zx_de'].get(zn, 0.0)) / 60.0
        lineas.append('Zona %s | %s | %d uds | %d cajas | %d OUT | %d uds de fuera | ~%d min | acaba ~%s' % (
            zn, tramo, d['uds'], d['cajas'], len(d['outs']), d['fuera'], round(d['seg'] / 60.0), reloj(fin_z)))
        if R.get('pers'):
            lineas[-1] += ' | %d personas' % R['pers'].get(zn, 0)
    lineas.append('')
    lineas.append('Caja | tienda | OUT | pedido | zona:cajas/uds (* = se queda la OUT original, ! = ultima caja sin llenar) | sin reserva')
    n_nuevas_plan = 0
    n_vistas = 0
    for pid, por_z, principal, sin_res, caja in plan:
        p_ = calc.out_rec[pid]
        n_vistas += 1
        trozos = ''
        for zn in orden_zonas:
            if zn in por_z:
                marca = ''
                if zn == principal:
                    marca = '*'
                else:
                    n_nuevas_plan += 1
                if not por_z[zn][3]:
                    marca += '!'
                trozos += '%s%s:%dc/%du  ' % (zn, marca, por_z[zn][0], por_z[zn][1])
        if n_vistas <= p['VER_OUT']:
            lineas.append('   %02d %s%s | %s | %s | %s| %d' % (
                caja, p_['partner_name'] or '', numero_k(p_['partner_name'] or '') in p['TIENDAS_48H'] and ' (48h)' or '',
                p_['name'], p_['origin'] or '', trozos, sin_res))
    if len(plan) > p['VER_OUT']:
        lineas.append('   ... y %d OUT mas' % (len(plan) - p['VER_OUT']))
    lineas.append('OUT nuevas que se crearian: %d' % n_nuevas_plan)
    if no_entran:
        lineas.append('')
        lineas.append('NO ENTRAN (no se tocan, quedan para otra tanda): %d OUT, %d uds' % (len(no_entran), uds_fuera))
        for pid in no_entran[:40]:
            q = calc.out_rec[pid]
            lineas.append('   %s | %s | %s | %d uds' % (q['partner_name'] or '', q['name'], q['origin'] or '', uds_out[pid]))
        if len(no_entran) > 40:
            lineas.append('   ... y %d mas' % (len(no_entran) - 40))
    if saltadas:
        lineas.append('')
        lineas.append('Saltadas (%d):' % len(saltadas))
        for s in saltadas[:40]:
            lineas.append('   %s' % s)
        if len(saltadas) > 40:
            lineas.append('   ... y %d mas' % (len(saltadas) - 40))

    # ---------------- Resultado ----------------
    R_out.modo = MODO
    R_out.prefijo = prefijo
    R_out.orden_zonas = list(orden_zonas)
    R_out.zona_fin = dict(R['zona_fin'])
    R_out.plan = plan
    R_out.pers = dict(R['pers'])
    R_out.seg_z = dict(R['seg_z'])
    R_out.fin = R['fin']
    R_out.ini_min = ini_min
    R_out.saltadas = saltadas
    R_out.no_entran = no_entran
    R_out.pasa_hora_fin = pasa_min      # v1.3.0: minutos despues de HORA_FIN (0 = acaba a tiempo)
    R_out.calc = calc
    R_out.R = R
    if not elegidas:
        lineas.append('')
        lineas.append('No entra ninguna OUT (o no hay OUT para partir).')
        R_out.estado = 'vacio'
    elif uds_entran < p['MIN_UDS_ZONAS']:
        lineas.insert(0, 'NO SE PARTE POR ZONAS: entran %d uds, menos de %d. Picking tradicional (OUT enteras). No se ha tocado nada.' % (
            uds_entran, p['MIN_UDS_ZONAS']))
        R_out.estado = 'pocas_uds'
    else:
        R_out.estado = 'listo'
        if MODO == 'DIAGNOSTICO':
            lineas.append('')
            lineas.append('DIAGNOSTICO v12: no se ha escrito nada. Siguiente paso: MODO = SIMULAR.')
    R_out.lineas = lineas
    R_out.parametros = p
    return R_out

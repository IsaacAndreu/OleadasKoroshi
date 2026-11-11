# -*- coding: utf-8 -*-
# =============================================================================
# Mover lineas de frontera entre zonas para cerrar cajas. Copia literal de la v12f (accion 1883,
# lineas 652-700). 'calc' da lit_ml, litros_de, segundos_de, cerrada y los parametros.
# =============================================================================


def cerrar_cadena(trozos, carga, obj_z, calc):
    # v12: trozos seguidos de una tienda ([zona, [ml.id]] en orden de recorrido): zona a zona cierra cajas moviendo
    # las lineas de la frontera; el resto final de menos de una caja se pega al trozo anterior
    PESO_CARGA = calc.p['PESO_CARGA']
    CIERRE_MIN = calc.p['CIERRE_MIN']
    LITROS_CAJA = calc.p['LITROS_CAJA']
    for i in range(len(trozos) - 1):
        tz = trozos[i]
        sig = trozos[i + 1]
        l_tz = calc.litros_de(tz[1])
        if calc.cerrada(l_tz):
            carga[tz[0]] += calc.segundos_de(tz[1])
            continue
        # empujar: las ultimas lineas de este trozo pasan a la zona siguiente
        queda = list(tz[1])
        empuja = []
        l_q = l_tz
        while queda and not calc.cerrada(l_q):
            x = queda.pop()
            l_q -= calc.lit_ml(x)
            empuja.insert(0, x)
        # tirar: las primeras lineas de la zona siguiente pasan a esta
        coge = list(tz[1])
        resto = list(sig[1])
        tira = []
        l_c = l_tz
        while resto and not calc.cerrada(l_c):
            x = resto.pop(0)
            l_c += calc.lit_ml(x)
            coge.append(x)
            tira.append(x)
        c_emp = calc.litros_de(empuja) * (1.0 + PESO_CARGA * (carga[sig[0]] + 1.0) / obj_z[sig[0]])
        c_tir = 1e18
        if calc.cerrada(l_c):
            c_tir = calc.litros_de(tira) * (1.0 + PESO_CARGA * (carga[tz[0]] + 1.0) / obj_z[tz[0]])
        if c_emp <= c_tir:
            tz[1] = queda
            sig[1] = empuja + sig[1]
        else:
            tz[1] = coge
            sig[1] = resto
        carga[tz[0]] += calc.segundos_de(tz[1])
    con_lineas = []
    for tz in trozos:
        if tz[1]:
            con_lineas.append(tz)
    if len(con_lineas) > 1 and calc.litros_de(con_lineas[-1][1]) < CIERRE_MIN * LITROS_CAJA:
        con_lineas[-2][1] = con_lineas[-2][1] + con_lineas[-1][1]
        con_lineas[-1][1] = []
    if con_lineas and con_lineas[-1][1]:
        carga[con_lineas[-1][0]] += calc.segundos_de(con_lineas[-1][1])

# -*- coding: utf-8 -*-
# =============================================================================
# Corte de lineales en tramos seguidos. Copia literal de la v12f (accion 1883, lineas 169-263).
# Complejidad de particion: O(k * n^2), n = pasillos con trabajo (< 70), k = zonas de lineal.
# =============================================================================


def particion(pesos, k):
    # Corta la lista de pesos (uno por pasillo, en orden) en k tramos seguidos minimizando el
    # tramo mas pesado. Devuelve (lista de pesos de cada tramo, lista de [desde, hasta) por tramo).
    n = len(pesos)
    if n == 0:
        return [], []
    if k > n:
        k = n
    pre = [0.0]
    for w in pesos:
        pre.append(pre[-1] + w)
    inf = 1e18
    dp = []
    corte = []
    for j in range(k + 1):
        dp.append([inf] * (n + 1))
        corte.append([0] * (n + 1))
    dp[0][0] = 0.0
    for j in range(1, k + 1):
        for i in range(j, n + 1):
            for t in range(j - 1, i):
                v = dp[j - 1][t]
                if pre[i] - pre[t] > v:
                    v = pre[i] - pre[t]
                if v < dp[j][i]:
                    dp[j][i] = v
                    corte[j][i] = t
    tramos = []
    i = n
    for j in range(k, 0, -1):
        t = corte[j][i]
        tramos.insert(0, [t, i])
        i = t
    tiempos = []
    for tr in tramos:
        tiempos.append(pre[tr[1]] - pre[tr[0]])
    return tiempos, tramos


def repartir_zx(tiempos, lista, capacidad):
    # v9: lo de fuera de lineal (lista de (hueco, segundos), ordenada por ubicacion) se corta en trozos seguidos.
    # Empieza la persona que antes acaba su zona y coge huecos hasta llegar a HORA_FIN; sigue la siguiente.
    # Un hueco que no cabe entero en nadie va a quien acabe antes. Devuelve (duracion, [[zona, huecos, seg]]).
    total = 0.0
    claves = []
    for c in lista:
        total += c[1]
        claves.append(c[0])
    if not tiempos:
        return total, (lista and [[-1, claves, total]] or [])
    mayor = max(tiempos)
    pares_t = []
    for z in range(len(tiempos)):
        pares_t.append((tiempos[z], z))
    pares_t.sort()
    personas = []
    for par in pares_t:
        personas.append(par[1])
    carga = {}
    orden_t = []
    idx = 0
    for z in personas:
        if idx >= len(lista):
            break
        libre = capacidad - tiempos[z]
        cl = []
        seg = 0.0
        while idx < len(lista) and seg + lista[idx][1] <= libre + 0.001:
            cl.append(lista[idx][0])
            seg += lista[idx][1]
            idx += 1
        if cl:
            carga[z] = [cl, seg]
            orden_t.append(z)
    while idx < len(lista):
        mejor = personas[0]
        fin_mejor = 1e18
        for z in personas:
            f = tiempos[z] + (z in carga and carga[z][1] or 0.0)
            if f < fin_mejor:
                fin_mejor = f
                mejor = z
        if mejor not in carga:
            carga[mejor] = [[], 0.0]
            orden_t.append(mejor)
        carga[mejor][0].append(lista[idx][0])
        carga[mejor][1] += lista[idx][1]
        idx += 1
    dur = mayor
    trozos = []
    for z in orden_t:
        if tiempos[z] + carga[z][1] > dur:
            dur = tiempos[z] + carga[z][1]
        trozos.append([z, carga[z][0], carga[z][1]])
    return dur, trozos

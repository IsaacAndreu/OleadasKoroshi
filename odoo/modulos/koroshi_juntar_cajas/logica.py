# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Juntar cajas - lógica sin Odoo (se prueba con tests/test_logica.py).
# Las reglas son las de la acción de servidor 1844 v5 («Juntar matrículas», en producción desde el 19/11/2026), más
# las del diseño bin/versiones/diseno-juntar-cajas-pda_2026-11-25.md (SHIPPED, cierre del camión, Zalando, etiqueta).
# =============================================================================
# La matrícula CJ es la de koroshi_base (comun.es_matricula / comun.esMatricula): aquí no se copia.
MAX_UDS_PEQUENA = 3          # como la 1844 y el sync a S4T: «caja pequeña» = 3 uds o menos


def error_pareja(d):
    """Motivo por el que NO se puede meter la caja pequeña en la destino, o None. d (dict):
    cj_o, cj_d             nombres de las dos CJ
    n_paquetes_o/_d        paquetes con ese nombre en Odoo (tiene que haber uno)
    uds_o, uds_d           uds leídas (qty_done) dentro de cada caja
    pedidos_o, pedidos_d   pedidos (origen de las OUT) de las líneas de cada caja (listas)
    tiendas_o, tiendas_d   ids de la tienda (partner de las OUT) de cada caja (listas)
    companias_o            ids de compañía de las OUT de la caja pequeña (lista)
    compania               la compañía buena (8)
    otra_out               la caja pequeña tiene líneas de una OUT que no está en la destino
    o_sin_validar          alguna línea de la caja pequeña no está hecha (OUT sin validar)
    shipped                el pedido está SHIPPED en S4T
    en_cierre              alguna OUT del pedido va en un cierre de camión ya enviado
    zalando                la dirección de entrega es de Zalando
    usada                  'origen' si esa CJ pequeña ya se vacía en esta misma tanda; 'destino_vaciada' si la destino
                           es una caja que se vacía en esta tanda"""
    cj_o, cj_d = d.get('cj_o'), d.get('cj_d')
    if cj_o == cj_d:
        return '%s: la caja pequeña y la destino son la misma.' % cj_o
    if d.get('usada') == 'origen':
        return '%s está dos veces.' % cj_o
    if d.get('usada') == 'destino_vaciada':
        return '%s se vacía en esta misma junta: no puede ser la destino.' % cj_d
    if d.get('n_paquetes_o') != 1:
        return '%s no es una caja cerrada.' % cj_o
    if d.get('n_paquetes_d') != 1:
        return '%s no es una caja cerrada.' % cj_d
    if not d.get('uds_o'):
        return '%s está vacía (¿ya juntada?).' % cj_o
    if not d.get('uds_d'):
        return 'La caja destino %s está vacía.' % cj_d
    ped_o = set(d.get('pedidos_o') or [])
    ped_d = set(d.get('pedidos_d') or [])
    if len(ped_o) != 1 or ped_o != ped_d:
        return '%s y %s no son del mismo pedido.' % (cj_o, cj_d)
    if set(d.get('tiendas_o') or []) != set(d.get('tiendas_d') or []):
        return '%s y %s no son de la misma tienda.' % (cj_o, cj_d)
    if set(d.get('companias_o') or []) != set([d.get('compania')]):
        return '%s no es de esta empresa.' % cj_o
    if d.get('zalando'):
        return 'Es un pedido de Zalando: no se toca.'
    if d.get('shipped'):
        return 'El pedido ya está SHIPPED en S4T: la mercancía ya ha salido.'
    if d.get('en_cierre'):
        return 'El pedido ya va en un camión cerrado: ya ha salido.'
    if d.get('otra_out') and d.get('o_sin_validar'):
        return '%s es de una OUT sin validar: valídala antes de juntar.' % cj_o
    return None


def avisos(d, partir=False):
    """Avisos que no paran la junta (se enseñan en rojo antes de «Juntar»). d: como error_pareja, más
    etiqueta (alguna OUT del pedido tiene etiqueta del transportista), transportista ('XPO', 'GLS' o '') y
    ready (v1.1.0: el pedido ya está READY en S4T). partir=True: avisos de «Revisar caja» (sin el de la caja grande)."""
    res = []
    if d.get('etiqueta'):
        res.append('El pedido ya tiene etiqueta de %s: hay que rehacerla con los bultos nuevos.'
                   % (d.get('transportista') or 'transportista'))
    if d.get('ready'):
        res.append('El pedido ya está READY en S4T con las cajas de antes: hay que volver a mandarlo (acción 1960).')
    if not partir and (d.get('uds_o') or 0) > (d.get('uds_d') or 0):
        res.append('La caja «pequeña» %s (%d uds) es más grande que la destino %s (%d uds).'
                   % (d.get('cj_o'), d.get('uds_o') or 0, d.get('cj_d'), d.get('uds_d') or 0))
    return res


# ------------------------------------------------------------------ v1.1.0: «Revisar caja» (partir una CJ)
def error_partir(d):
    """Motivo por el que NO se pueden pasar las prendas leídas de la CJ origen a la CJ nueva, o None. d (dict):
    cj_o, cj_n             CJ origen (la que tiene las prendas en Odoo) y CJ nueva (la pegada en la otra caja)
    n_paquetes_o           paquetes con el nombre de la CJ origen (tiene que haber uno)
    n_paquetes_n           paquetes con el nombre de la CJ nueva (0 = se crea; 1 = vale si está vacía o es del
                           mismo pedido y tienda)
    uds_o                  uds dentro de la CJ origen
    leidas                 uds leídas que se pasan
    pedidos_o, pedidos_n   pedidos de las líneas de cada CJ (listas; la nueva puede estar vacía)
    tiendas_o, tiendas_n   ids de la tienda de las líneas de cada CJ
    stock_n_suelto         la CJ nueva tiene stock sin líneas de pedido (es un contenedor del almacén)
    shipped, en_cierre, zalando: como en error_pareja"""
    cj_o, cj_n = d.get('cj_o'), d.get('cj_n')
    if cj_o == cj_n:
        return 'La CJ nueva %s es la misma caja.' % cj_n
    if d.get('n_paquetes_o') != 1:
        return '%s no es una caja cerrada.' % cj_o
    if not d.get('uds_o'):
        return '%s está vacía.' % cj_o
    if not d.get('leidas'):
        return 'No has leído ninguna prenda.'
    if d.get('leidas') >= d.get('uds_o'):
        return ('Has leído las %d uds de %s: no queda nada en ella. Lee solo las prendas de la caja que hay que '
                'separar.' % (d.get('uds_o'), cj_o))
    if (d.get('n_paquetes_n') or 0) > 1:
        return '%s está repetida en Odoo: avisa a la oficina.' % cj_n
    ped_o = set(d.get('pedidos_o') or [])
    if len(ped_o) != 1:
        return '%s tiene prendas de varios pedidos: avisa a la oficina.' % cj_o
    if d.get('pedidos_n') and set(d.get('pedidos_n')) != ped_o:
        return '%s ya tiene prendas de otro pedido (%s).' % (cj_n, ', '.join(sorted(d.get('pedidos_n'))))
    if d.get('tiendas_n') and set(d.get('tiendas_n')) != set(d.get('tiendas_o') or []):
        return '%s ya tiene prendas de otra tienda.' % cj_n
    if d.get('stock_n_suelto'):
        return '%s tiene stock del almacén: no es una caja de pedido.' % cj_n
    if d.get('zalando'):
        return 'Es un pedido de Zalando: no se toca.'
    if d.get('shipped'):
        return 'El pedido ya está SHIPPED en S4T: la mercancía ya ha salido.'
    if d.get('en_cierre'):
        return 'El pedido ya va en un camión cerrado: ya ha salido.'
    return None


def elegir_lineas(lineas, n):
    """Líneas ENTERAS cuyas uds suman exactamente n (v1.1.0: nunca se parte una línea, así no se toca el stock de
    los huecos ni las reservas). lineas: [(id, uds)] de un mismo artículo en la caja. Devuelve la lista de ids o
    None si no hay ninguna combinación exacta (p. ej. una sola línea de 3 uds y se han leído 2)."""
    n = int(round(n or 0))
    if n <= 0:
        return []
    orden = sorted((int(round(q)), i) for i, q in lineas if q and q > 0)
    mejor = {0: []}           # mejor[s] = ids de líneas que suman s
    for q, i in orden:
        for s in sorted(mejor, reverse=True):
            t = s + q
            if t <= n and t not in mejor:
                mejor[t] = mejor[s] + [i]
    return mejor.get(n)


def bultos_por_out(reparto, outs_con_caja, outs_hechas, actuales):
    """Número de bultos de cada OUT con las cajas reales: cada caja cuenta en una sola OUT, la que lleva más uds
    dentro (si empatan, la de id más bajo). Como recalcular_bultos de la 1844 v3-v5.
    reparto: {paquete: {out: uds}}; outs_con_caja: OUT con alguna línea en caja; outs_hechas: OUT validadas;
    actuales: {out: number_of_packages de ahora}. Devuelve [(out, antes, despues)] de las que cambian. Las OUT sin
    ninguna línea en caja y sin validar no se tocan."""
    cuenta = {}
    for paquete in reparto:
        dueno, mejor = None, -1
        for out in sorted(reparto[paquete]):
            if reparto[paquete][out] > mejor:
                dueno, mejor = out, reparto[paquete][out]
        cuenta[dueno] = cuenta.get(dueno, 0) + 1
    cambios = []
    for out in sorted(actuales):
        if out not in outs_con_caja and out not in outs_hechas:
            continue
        nuevo = cuenta.get(out, 0)
        if actuales[out] != nuevo:
            cambios.append((out, actuales[out], nuevo))
    return cambios


def cuadra(bultos_antes, bultos_despues, juntadas):
    """La junta está bien si los bultos del pedido bajan exactamente en el número de cajas juntadas (1844 v5)."""
    return bultos_despues == bultos_antes - juntadas


def transportista(texto):
    """'XPO', 'GLS' o '' según el nombre del transportista o la nota de la etiqueta."""
    t = (texto or '').upper()
    if 'XPO' in t:
        return 'XPO'
    if 'GLS' in t:
        return 'GLS'
    return ''

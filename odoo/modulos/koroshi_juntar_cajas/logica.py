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


def avisos(d):
    """Avisos que no paran la junta (se enseñan en rojo antes de «Juntar»). d: como error_pareja, más
    etiqueta (alguna OUT del pedido tiene etiqueta del transportista) y transportista ('XPO', 'GLS' o '')."""
    res = []
    if d.get('etiqueta'):
        res.append('El pedido ya tiene etiqueta de %s: hay que rehacerla con un bulto menos.'
                   % (d.get('transportista') or 'transportista'))
    if (d.get('uds_o') or 0) > (d.get('uds_d') or 0):
        res.append('La caja «pequeña» %s (%d uds) es más grande que la destino %s (%d uds).'
                   % (d.get('cj_o'), d.get('uds_o') or 0, d.get('cj_d'), d.get('uds_d') or 0))
    return res


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

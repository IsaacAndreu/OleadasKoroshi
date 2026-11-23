# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Pedidos S4T grandes - lo que no depende de Odoo (se prueba sin Odoo: pruebas/test_logica.py)
# =============================================================================

CANAL = 'root.s4t_sync'

# Claves de los candados de Postgres (pg_advisory_lock(clave, id)). El cron 192 «Alerta cola de S4T» v7 usa las
# mismas para saber si un job sigue vivo antes de reencolarlo: si se cambian aqui, se cambian alli.
CLAVE_FEED = 719401      # + id del s4t.order.feed
CLAVE_PEDIDO = 719402    # + id del sale.order

PARAM_UMBRAL = 'koroshi_s4t_pedidos.umbral_lineas'
PARAM_BLOQUE = 'koroshi_s4t_pedidos.bloque_reserva'
UMBRAL_POR_DEFECTO = 60   # lineas: desde aqui, confirmar y reservar van en jobs aparte. 0 = apagado (como antes)
BLOQUE_POR_DEFECTO = 50   # movimientos por bloque al reservar

ESPERA_COPIA = 300        # s: si otra copia del mismo job esta trabajando, se vuelve a mirar en 5 min
ESPERA_RESERVA = 60       # s: si un bloque choca 3 veces seguidas, se reintenta el job en 1 min
INTENTOS_BLOQUE = 3

ESTADOS_POR_RESERVAR = ('confirmed', 'partially_available')
ESTADOS_PEDIDO_SIN_CONFIRMAR = ('draft', 'sent')

DESC_CONFIRMAR = 'S4T Confirmar pedido %s'
DESC_RESERVAR = 'S4T Reservar OUT %s'


def leer_entero(valor, defecto, minimo):
    """Entero de un parametro de sistema; si esta vacio, mal escrito o por debajo del minimo, el defecto."""
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        return defecto
    return n if n >= minimo else defecto


def es_grande(num_lineas, umbral):
    """True si el pedido se confirma y se reserva en jobs aparte. umbral 0 = apagado."""
    return umbral > 0 and num_lineas >= umbral


def bloques(ids, tam):
    """[ids[0:tam], ids[tam:2*tam], ...]"""
    tam = max(1, int(tam))
    return [ids[i:i + tam] for i in range(0, len(ids), tam)]


# =============================================================================
# v1.1.0 (23/11/2026): reserva de las tiendas por prioridad (numero de pedido S4T, el mas bajo primero)
# =============================================================================

CLAVE_PRIORIDAD = 719403            # candado: un solo reparto a la vez
PARAM_PRIORIDAD_MODO = 'koroshi_s4t_pedidos.prioridad_modo'          # simular (por defecto) | real | apagado
PARAM_PRIORIDAD_LOTE = 'koroshi_s4t_pedidos.prioridad_prefijo_lote'  # lotes que si se aceptan (agrupacion del dia)
MODOS_PRIORIDAD = ('simular', 'real', 'apagado')
TIPO_TIENDAS = 'PED. TIENDAS'       # = koroshi_zonas/motor/modelo.py TIPO_PEDIDO
PREFIJO_LOTE_TIENDA = 'TIENDA'      # = PREFIJO_AGRUPACION de la 1883: las OUT llegan en la agrupacion del dia
SIN_PEDIDO = 10 ** 12
TOLERANCIA = 0.001


def modo_prioridad(valor):
    v = (valor or '').strip().lower()
    return v if v in MODOS_PRIORIDAD else 'simular'


def numero_pedido(origin):
    """'S-6665004409' -> 6665004409. Sin numero: SIN_PEDIDO (al final). Igual que koroshi_zonas/motor/evaluar.py:29
    y que el Monitor, para que la reserva siga el mismo orden que la ronda."""
    num = ''
    for ch in origin or '':
        if ch.isdigit():
            num += ch
        elif num:
            break
    return int(num) if num else SIN_PEDIDO


def clave_prioridad(mov):
    """Orden de reserva: numero de pedido, y a igual numero la OUT y el movimiento mas antiguos."""
    return (mov['numero'], mov['picking_id'], mov['id'])


def en_disputa(movs):
    """movs: [{'numero', 'picking_id', 'id', 'pedido' (demanda), 'reservado'}] de UN articulo.
    True si a alguno le falta reserva y otro de numero MAS ALTO tiene algo reservado: entonces el orden importa.
    Si hay para todos, o el que no tiene es el de numero mas alto, no se toca nada."""
    orden = sorted(movs, key=clave_prioridad)
    falta_antes = False
    for m in orden:
        if falta_antes and m['reservado'] > TOLERANCIA:
            return True
        if m['pedido'] - m['reservado'] > TOLERANCIA:
            falta_antes = True
    return False


def cambios(antes, despues):
    """{clave: uds} antes y despues -> [(clave, antes, despues)] solo de las que cambian."""
    res = []
    for k in sorted(set(antes) | set(despues), key=str):
        a = antes.get(k, 0.0)
        d = despues.get(k, 0.0)
        if abs(a - d) > TOLERANCIA:
            res.append((k, a, d))
    return res

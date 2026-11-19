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

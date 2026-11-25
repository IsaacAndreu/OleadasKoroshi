# Cabecera de la accion 1827 «Recuperar Pedidos Online» ANTES del 19/11/2026 (la ultima vez se uso el 29/09/2026).
# El resto del codigo (desde «if not SIMULACION and not CANTIDADES_CONFIRMADAS:») no se cambia.
# ================================================================
# RECUPERACION MANUAL KOROSHI - 2 PEDIDOS (26/09/2026)
# Accion de servidor sobre s4t.order.feed
#
# SIMULACION = True -> solo valida duplicados y SKU, no crea nada
# CANTIDADES_CONFIRMADAS -> True solo tras validar unidades con Betty
# IDs S4T negativos = PROVISIONALES (Koroshi no los devuelve por API)
# ================================================================
SIMULACION = False
CANTIDADES_CONFIRMADAS = True

PEDIDOS = [
    (
        '0000053992-02',
        '2026-09-26',
        'Paloma',
        -900022,
        [
            ('1821ML07-000003-XS', 1),
            ('1821ML13-000014-XS', 1),
            ('1821ML14-000003-XS', 1),
            ('2111MC36-000003-S', 1),
            ('2421ML08-000123-S', 1),
        ]
    ),
    (
        '0000053993-02',
        '2026-09-26',
        'Goiaz',
        -900023,
        [
            ('1922VS91-000158-XL', 1),
            ('2522VS20-000323-XL', 1),
        ]
    ),
]

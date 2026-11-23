# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Contenedores - lógica sin Odoo (se prueba con tests/test_logica.py, sin servidor).
# v1.13.0: repartir() dice cuántas uds de cada línea reservada pasan a Faltantes.
# =============================================================================


def repartir(reservas, sobra, precision=0.001):
    """Cuántas uds quitar a cada línea reservada para que, en total, salgan `sobra` uds (lo reservado que no está).

    reservas: uds reservadas de cada línea, en el orden en que se quitan (las pequeñas primero: así una OUT pasa
    entera antes que partir dos).
    Devuelve una lista con lo que se quita a cada línea (0 = no se toca). Nunca más de lo que tiene la línea, ni
    más de `sobra` en total. Con sobra >= todo lo reservado («Poner a cero») se quitan todas enteras."""
    res = []
    queda = sobra
    for r in reservas:
        if queda <= precision or r <= precision:
            res.append(0.0)
            continue
        q = round(min(r, queda), 6)
        res.append(q)
        queda = round(queda - q, 6)
    return res

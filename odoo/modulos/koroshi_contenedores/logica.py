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


# -----------------------------------------------------------------------------
# v1.14.0 (R23): «Es otro» (cambiar artículo). Errores de talla: lo que Odoo llama A en el contenedor es B.
# -----------------------------------------------------------------------------
def modelo(nombre):
    """Modelo de un artículo por su nombre: la referencia sin la talla del final. En KOROSHI cada talla es un artículo
    (y una plantilla) aparte: 2621PT01-000014-34 y 2621PT01-000014-36 son el modelo 2621PT01-000014. Si el nombre no
    tiene esa forma (menos de dos guiones), el modelo es el nombre entero."""
    n = (nombre or '').strip().upper()
    if n.startswith('['):           # display_name: «[REF] nombre»
        n = n.split(']', 1)[-1].strip()
    if n.count('-') >= 2:
        return n.rsplit('-', 1)[0]
    return n


def mismo_modelo(nombre_a, nombre_b):
    """True si los dos artículos son el mismo modelo en otra talla."""
    a, b = modelo(nombre_a), modelo(nombre_b)
    return bool(a) and a == b


def error_uds_cambio(uds, actual, maximo):
    """Texto del error si no se pueden pasar `uds` de A a B ('' = se puede). actual = uds de A en el contenedor."""
    if uds is None or uds < 1:
        return 'Pon cuántas uds son del otro artículo (1 o más).'
    if uds > actual + 0.001:
        return 'Solo hay %s uds en el contenedor: no se pueden cambiar %s.' % (_n(actual), _n(uds))
    if uds > maximo:
        return 'Más de %d uds de una vez: revisa la cantidad.' % maximo
    return ''


def reservas_a_faltantes(uds, actual, reservadas):
    """Uds reservadas de A que pasan a Faltantes al cambiar `uds` de A a B: las que no caben en lo que queda de A."""
    return max(0.0, round(reservadas - (actual - uds), 6))


def _n(x):
    x = round(x or 0, 2)
    return ('%d' % x) if x == int(x) else ('%s' % x).replace('.', ',')

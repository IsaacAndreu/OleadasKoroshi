# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Contenedores - lógica sin Odoo (se prueba con tests/test_logica.py, sin servidor).
# v1.13.0: repartir() dice cuántas uds de cada línea reservada pasan a Faltantes.
# =============================================================================
import re


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


# -----------------------------------------------------------------------------
# v1.16.0: «Retirar cajas a 0» (ronda por lineal y hueco). Diseño aprobado por Isaac el 26/11:
# bin/versiones/diseno-compactacion-odoo-retirar-vacias-juntar-cajas_2026-11-26_v2.md, parte 1.
# -----------------------------------------------------------------------------
RANGO_LINEALES = (44, 136)          # zona 0: palés de L44 a L136
_RE_RANGO = re.compile(r'^\s*L?(\d{1,4})\s*-\s*L?(\d{1,4})\s*$', re.I)
_RE_LINEAL = re.compile(r'(?:^|\s)L(\d{1,4})(?=\s|$)', re.I)
_RE_P = re.compile(r'(?:^|\s)P(\d{1,4})(?=\s|$)', re.I)
_RE_C = re.compile(r'(?:^|\s)C(\d{1,3})(?=\s|$)', re.I)


def rango_lineales(texto):
    """«44-136» (o «L44-L136») -> (44, 136). Vacío o mal escrito: el de siempre (44, 136)."""
    m = _RE_RANGO.match(texto or '')
    if not m:
        return RANGO_LINEALES
    a, b = int(m.group(1)), int(m.group(2))
    return (a, b) if a <= b else (b, a)


def lineal_de(nombre_hueco):
    """Número del lineal sacado del nombre del hueco: «07828 - L67 P16 C1» -> 67. Sin lineal L (MU-01…) -> None."""
    m = _RE_LINEAL.search(nombre_hueco or '')
    return int(m.group(1)) if m else None


def orden_hueco(nombre_hueco):
    """Clave para ordenar los huecos como se recorren: lineal, P, C (números, no texto: P2 antes que P10)."""
    n = nombre_hueco or ''
    num = [int(m.group(1)) if m else 9999 for m in (_RE_LINEAL.search(n), _RE_P.search(n), _RE_C.search(n))]
    return tuple(num) + (n,)


def clasificar(activos, negativos, descuadres, abierta):
    """Estado de una caja para la ronda.
    activos = quants con cantidad o con reserva; negativos = quants con cantidad < 0; descuadres = quants con más
    reservado que cantidad; abierta = tiene líneas de movimiento sin hacer (IN, INT u OUT que salen o entran).
    'revisar': negativo o descuadre (solo Isaac, Betty y José Luis); 'stock': tiene prendas; 'abierta': a 0 pero con
    una recepción o un traslado sin validar (no se retira); 'cero': se puede retirar."""
    if negativos or descuadres:
        return 'revisar'
    if activos:
        return 'stock'
    if abierta:
        return 'abierta'
    return 'cero'


def ids_tarjetas(texto):
    """«12, 34; 56» -> {12, 34, 56}: ids de empleado (hr.employee) de un parámetro. Lo que no es número se ignora."""
    return {int(x) for x in re.findall(r'\d+', texto or '')}


def con_prendas_pendiente(ultima_marca, ultimo_cambio):
    """Una caja marcada «Tiene prendas» sigue pendiente si después no se ha hecho nada con su stock. Ids crecientes
    del registro (koroshi.contenedor.movimiento): la marca más nueva y el último cambio (añadir, cambiar, a cero…)."""
    if not ultima_marca:
        return False
    return not ultimo_cambio or ultima_marca > ultimo_cambio


def repartir_encontrados(uds, faltantes, precision=0.001):
    """Prendas leídas de un artículo en una caja «con prendas» y faltantes pendientes de ese artículo con vuelta a la
    caja o a su hueco [(id, cantidad)], en orden. Cada faltante se da por encontrado entero si las uds que quedan lo
    cubren (un faltante no se parte: marcar_encontrado lo devuelve entero). Devuelve (ids encontrados, uds que
    sobran = ajuste +)."""
    queda = uds
    usados = []
    for fid, cant in faltantes:
        if cant <= precision:
            continue
        if cant <= queda + precision:
            usados.append(fid)
            queda = round(queda - cant, 6)
    return usados, max(0.0, queda)

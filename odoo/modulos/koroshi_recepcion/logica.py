# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recepción: cálculos sin Odoo (Python puro), para probarlos sin servidor: tests/test_logica.py.
#
#   - referencia de KOROSHI: «2711JA43-000062-S» = modelo 2711JA43, color 000062, talla S;
#   - palés: «PAL-03 A» (palé 3, cara A), nombre = código de barras;
#   - comparar lo que traen las IN (teórico, por artículo) con lo leído;
#   - repartir lo leído entre los movimientos pendientes de las IN, por orden.
# Diseño: bin/versiones/diseno-recepciones-packing-list_2026-11-23_v6.md
# =============================================================================
import re

MAX_CAJAS = 2000            # contenedores de control de una vez (un contenedor marítimo grande: ~700 cajas)
MAX_PALETS = 99             # PAL-01 … PAL-99
MAX_UDS_LECTURA = 5000      # uds de un artículo en una caja (más = error al escribir)
CARAS = ('A', 'B')

RE_PALET = re.compile(r'^PAL\s*-?\s*(\d{1,2})\s*-?\s*([AB])$', re.I)
RE_REF = re.compile(r'^([^-\s]+)-([^-\s]+)-(\S+)$')


# ----------------------------------------------------------------------------- referencias
def partes_referencia(ref):
    """«2711JA43-000062-S» -> ('2711JA43', '000062', 'S'). Si no tiene esa forma: (ref, '', '')."""
    ref = (ref or '').strip()
    m = RE_REF.match(ref)
    if not m:
        return ref, '', ''
    return m.group(1), m.group(2), m.group(3)


ORDEN_TALLAS = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL', 'XXXL', '4XL', '5XL']


def clave_talla(talla):
    """Para ordenar tallas: XS < S < M < L < XL…; los números por su valor (2, 4, 6, 12 años…); lo demás al final."""
    t = (talla or '').upper()
    if t in ORDEN_TALLAS:
        return (0, ORDEN_TALLAS.index(t), t)
    num = re.match(r'^(\d+)', t)
    if num:
        return (1, int(num.group(1)), t)
    return (2, 0, t)


# ----------------------------------------------------------------------------- palés
def nombre_palet(numero, cara):
    """3, 'a' -> «PAL-03 A»."""
    cara = (cara or '').upper()
    if cara not in CARAS:
        raise ValueError('La cara de un palé es A o B.')
    if not (1 <= int(numero) <= MAX_PALETS):
        raise ValueError('Los palés van del 1 al %d.' % MAX_PALETS)
    return 'PAL-%02d %s' % (int(numero), cara)


def nombres_palets(cuantos):
    """3 -> PAL-01 A, PAL-01 B, PAL-02 A, PAL-02 B, PAL-03 A, PAL-03 B."""
    if not (1 <= int(cuantos) <= MAX_PALETS):
        raise ValueError('Se pueden tener de 1 a %d palés.' % MAX_PALETS)
    return [nombre_palet(n, c) for n in range(1, int(cuantos) + 1) for c in CARAS]


def palet_de(codigo):
    """«PAL-03 A», «pal3a», «PAL-3-B» -> «PAL-03 A». Si no es un palé, None."""
    m = RE_PALET.match((codigo or '').strip())
    if not m:
        return None
    try:
        return nombre_palet(int(m.group(1)), m.group(2))
    except ValueError:
        return None


def numero_palet(nombre):
    """«PAL-03 A» -> (3, 'A'); None si no es un palé."""
    p = palet_de(nombre)
    return p and (int(p[4:6]), p[7]) or None


# ----------------------------------------------------------------------------- buscador
def es_final_ean(texto):
    """El operario escribe los últimos 4 dígitos del EAN (o 3 a 6): solo cifras."""
    t = (texto or '').strip()
    return t.isdigit() and 3 <= len(t) <= 6


def cantidad_valida(texto):
    """'12' -> 12. Lanza ValueError con el motivo, en castellano."""
    try:
        n = float(str(texto).replace(',', '.'))
    except (TypeError, ValueError):
        raise ValueError('La cantidad tiene que ser un número.')
    if n != int(n):
        raise ValueError('La cantidad tiene que ser un número entero de prendas.')
    n = int(n)
    if n <= 0:
        raise ValueError('La cantidad tiene que ser mayor que 0.')
    if n > MAX_UDS_LECTURA:
        raise ValueError('%d prendas en una caja son demasiadas: revisa la cantidad.' % n)
    return n


# ----------------------------------------------------------------------------- cajas del proveedor (1.1.0)
MAX_CAJA = 20               # caracteres del nº de caja escrito a mano
MAX_HUECOS = 300            # huecos de numeración que se enseñan


def normalizar_caja(texto):
    """El nº de caja escrito a rotulador: «108», « 0108 », «108a» -> «108», «108», «108A». Vacío -> ValueError.
    Las cifras sin ceros delante (así «0108» y «108» son la misma caja)."""
    t = ' '.join((texto or '').split()).upper()
    if not t:
        raise ValueError('Escribe el nº de caja (el que lleva escrito a mano).')
    if len(t) > MAX_CAJA or (t.isdigit() and len(t) >= 8):
        raise ValueError('El nº de caja «%s» parece un código de barras: escribe el nº que lleva la caja a mano.' % t)
    if t.isdigit():
        t = str(int(t))
    return t


def clave_pedido(texto):
    """Nº de pedido de la etiqueta («ORDER NUMBER 0000001936») para compararlo con el origen de las IN: sin espacios,
    en mayúsculas y, si son cifras, sin ceros delante («1936» = «0000001936»). Vacío -> ''."""
    t = ''.join((texto or '').split()).upper()
    if t.isdigit():
        t = str(int(t))
    return t


def pedido_ajeno(pedido, origenes):
    """True si se ha escrito un pedido y no es el de ninguna IN (origenes: los origin de las IN del contenedor)."""
    p = clave_pedido(pedido)
    return bool(p) and p not in {clave_pedido(o) for o in origenes if o}


def normalizar_modelo(texto):
    """1.2.0: el modelo de la etiqueta (REFERENCE): « 2711ja22 » -> «2711JA22». Si se escribe la referencia entera
    («2711JA22-000062-S»), se queda el modelo. Vacío -> ValueError."""
    t = ''.join((texto or '').split()).upper()
    if not t:
        raise ValueError('Falta el modelo (el REFERENCE de la etiqueta, p. ej. 2711JA22).')
    return modelo_de(t)


def modelo_de(ref):
    """«2711JA43-000062-S» -> «2711JA43» (el modelo, sin color ni talla); una referencia sin guiones, entera."""
    return (partes_referencia(ref)[0] or '').upper()


def in_coincide(texto, nombre, origen, contenedores, codigos):
    """1.3.0: buscador de IN. True si «texto» está en el nombre (EFFEC/IN/00396; «396» vale), el origen (pedido
    0000002172; «2172» vale), algún contenedor de la IN o es el principio de algún código de artículo (2711JA22).
    1.6.1 (Isaac): contenedores = carrier_tracking_ref, puede traer varios con «+» («MIEU4099960», «4099960» o un
    trozo valen); ya no busca por referencia del proveedor ni BL. Sin texto: todas."""
    t = ''.join((texto or '').split()).upper()
    if not t:
        return True
    num = str(int(t)) if t.isdigit() else None
    nombre = (nombre or '').upper()
    if t in nombre:
        return True
    cola = re.search(r'(\d+)$', nombre)
    if num and cola and str(int(cola.group(1))) == num:
        return True
    if num and num in clave_pedido(origen):
        return True
    if t in ''.join((origen or '').split()).upper():
        return True
    for c in contenedores or []:
        for uno in (c or '').replace(',', '+').replace(';', '+').split('+'):
            if t in ''.join(uno.split()).upper():
                return True
    return any((c or '').upper().startswith(t) for c in codigos)


def total_packing(origenes, feeds):
    """1.4.0: total de cajas y uds del packing list de S4T de los pedidos de las IN.
    origenes: los origin de las IN. feeds: [(name, cajas, uds, duplicado)] de s4t.packing.feed (puede haber varios
    con el mismo name: se cuenta uno, el primero). Devuelve {'cajas', 'uds', 'pedidos': [(name, cajas, uds, dup)],
    'sin_packing': [pedidos sin feed], 'duplicados': [names marcados duplicated o repetidos]}."""
    claves = []
    for o in origenes:
        k = clave_pedido(o)
        if k and k not in claves:
            claves.append(k)
    por_clave, repetidos = {}, set()
    for name, cajas, uds, dup in feeds:
        k = clave_pedido(name)
        if k in por_clave:
            repetidos.add(name)
            continue
        por_clave[k] = (name, int(cajas or 0), int(uds or 0), bool(dup))
    pedidos = [por_clave[k] for k in claves if k in por_clave]
    duplicados = sorted({p[0] for p in pedidos if p[3]} | {n for n in repetidos if clave_pedido(n) in claves})
    return {'cajas': sum(p[1] for p in pedidos), 'uds': sum(p[2] for p in pedidos), 'pedidos': pedidos,
            'sin_packing': [k for k in claves if k not in por_clave], 'duplicados': duplicados}


def clave_caja(caja):
    """Para ordenar nº de caja: los números por su valor, después lo demás."""
    c = caja or ''
    return (0, int(c), '') if c.isdigit() else (1, 0, c)


def resumen_cajas(lecturas, esperadas=0):
    """lecturas: [(caja, pedido, ajeno)] de las lecturas buenas. esperadas: las cajas que dijo quien recepciona.
    Devuelve {'leidas': [cajas ordenadas], 'huecos': [números que faltan entre 1 y el mayor (o las esperadas)],
    'huecos_mas': hay más huecos que MAX_HUECOS, 'ajenas': [(caja, pedido)] con un pedido que no es de este
    contenedor}."""
    cajas = sorted({c for c, _p, _a in lecturas if c}, key=clave_caja)
    sin_numero = sum(1 for c, _p, _a in lecturas if not c)     # 1.5.0: cajas contadas con «+1» (sin nº)
    numeros = {int(c) for c in cajas if c.isdigit()}
    tope = max(list(numeros) + [int(esperadas or 0)]) if (numeros or esperadas) else 0
    huecos = [n for n in range(1, tope + 1) if n not in numeros] if numeros else []
    ajenas = sorted({(c, p) for c, p, a in lecturas if a}, key=lambda x: (clave_caja(x[0]), x[1]))
    return {'leidas': cajas, 'sin_numero': sin_numero, 'total': len(cajas) + sin_numero,
            'huecos': huecos[:MAX_HUECOS], 'huecos_mas': len(huecos) > MAX_HUECOS,
            'n_huecos': len(huecos), 'ajenas': ajenas}


def rangos_texto(numeros, maximo=60):
    """[1, 2, 3, 7, 9, 10] -> «1-3, 7, 9-10» (1.6.0: cajas que faltan). Si hay más de «maximo» trozos, «…»."""
    nums = sorted(set(int(n) for n in numeros))
    trozos = []
    for n in nums:
        if trozos and n == trozos[-1][1] + 1:
            trozos[-1][1] = n
        else:
            trozos.append([n, n])
    txt = ['%d' % a if a == b else '%d-%d' % (a, b) for a, b in trozos]
    return ', '.join(txt[:maximo]) + (', …' if len(txt) > maximo else '')


def cajas_contadas(cajas_de_lecturas):
    """1.5.0: cajas que llevan contadas: las distintas con nº + una por cada «+1» (sin nº)."""
    con = {c for c in cajas_de_lecturas if c}
    return len(con) + sum(1 for c in cajas_de_lecturas if not c)


# ----------------------------------------------------------------------------- comparar
def comparar(teorico, leido):
    """teorico, leido: {producto: uds}. Devuelve {producto: (teorico, leido, diferencia, estado)}.
    estado: 'ok' (igual), 'falta' (leído < teórico), 'sobra' (leído > teórico, venía en las IN), 'no_venia' (leído sin
    estar en ninguna IN)."""
    res = {}
    for p in set(teorico) | set(leido):
        t = teorico.get(p, 0) or 0
        l = leido.get(p, 0) or 0
        if not t and not l:
            continue
        d = l - t
        if not t:
            estado = 'no_venia'
        elif d == 0:
            estado = 'ok'
        elif d < 0:
            estado = 'falta'
        else:
            estado = 'sobra'
        res[p] = (t, l, d, estado)
    return res


# ----------------------------------------------------------------------------- repartir lo leído entre las IN
def repartir(pendientes, leidos):
    """Reparte lo leído entre los movimientos pendientes de las IN.

    pendientes: [(movimiento, producto, uds_pendientes)] en el orden en que se llenan (fecha prevista de la IN).
    leidos: [(lectura, producto, destino, uds)] en orden de lectura.

    Devuelve (lineas, sin_in):
      lineas: [(movimiento, destino, uds, [lecturas])]: una línea hecha por movimiento y destino. Lo que pasa de lo
              pendiente de un artículo va al ÚLTIMO movimiento de ese artículo (la prenda está en el almacén: Odoo
              tiene que tenerla), y se ve como «sobra» al comparar.
      sin_in: [lectura]: lecturas de artículos que no están en ninguna IN pendiente. No se pasan a stock.
    """
    por_producto = {}
    for mov, prod, uds in pendientes:
        por_producto.setdefault(prod, []).append([mov, max(uds or 0, 0)])
    acumulado = {}           # (mov, destino) -> [uds, [lecturas]]
    orden = []
    sin_in = []
    for lectura, prod, destino, uds in leidos:
        movs = por_producto.get(prod)
        if not movs:
            sin_in.append(lectura)
            continue
        queda = uds
        for m in movs:
            if queda <= 0:
                break
            toma = min(queda, m[1])
            if toma > 0:
                m[1] -= toma
                queda -= toma
                _sumar(acumulado, orden, m[0], destino, toma, lectura)
        if queda > 0:        # sobra: al último movimiento del artículo
            _sumar(acumulado, orden, movs[-1][0], destino, queda, lectura)
    lineas = [(mov, dest, acumulado[(mov, dest)][0], acumulado[(mov, dest)][1]) for mov, dest in orden]
    return lineas, sin_in


def _sumar(acumulado, orden, mov, destino, uds, lectura):
    clave = (mov, destino)
    if clave not in acumulado:
        acumulado[clave] = [0, []]
        orden.append(clave)
    acumulado[clave][0] += uds
    if lectura not in acumulado[clave][1]:
        acumulado[clave][1].append(lectura)


# ----------------------------------------------------------------------------- exportar
def csv_celda(valor):
    """Una celda para un CSV con «;» (Excel en castellano): comillas si hace falta; números con coma decimal."""
    if valor is None or valor is False:
        return ''
    if isinstance(valor, float):
        valor = ('%g' % round(valor, 2)).replace('.', ',')
    s = str(valor)
    if any(c in s for c in ';"\n\r'):
        s = '"%s"' % s.replace('"', '""')
    return s


def csv_texto(filas):
    """[[celdas]] -> texto CSV con «;» y saltos \\r\\n."""
    return '\r\n'.join(';'.join(csv_celda(c) for c in fila) for fila in filas) + '\r\n'

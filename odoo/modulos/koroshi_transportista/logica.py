# -*- coding: utf-8 -*-
"""
KOROSHI Transportista - lógica sin Odoo (tests/test_logica.py).
Diseño: bin/versiones/diseno-imprimir-desde-pda_2026-11-25_v4.md.

Cuadrar: las CJ escaneadas tienen que ser EXACTAMENTE las cajas distintas de las OUT validadas sin etiqueta de la
tienda (la misma cuenta que mandan XPO, koroshi_xpo_bultos.bultos_de, y GLS, acción 1834 v5). Si sobra una, error con
el porqué; si falta una, se dice cuál. Solo con todo cuadrado se puede etiquetar (decisión de Isaac, 25/11).
"""
import re

GLS = 'gls'
XPO = 'xpo'
TRANSPORTISTAS = (GLS, XPO)
NOMBRES = {GLS: 'GLS', XPO: 'XPO'}
DIAS_PENDIENTES = 10            # OUT validadas sin etiqueta de hasta 10 días atrás (P3: OUT de días distintos juntas)

RE_TIENDA = re.compile(r',\s*(K\d+\b.*)$')     # «DIGITAL E-GLOBAL XPERIENCE, SL, K24 - VALLADOLID» -> «K24 - VALLADOLID»


def tienda_de(nombre_cliente):
    """La tienda (K## - nombre) del nombre del cliente de la OUT, o '' si no es de tienda (web, Zalando...)."""
    m = RE_TIENDA.search(nombre_cliente or '')
    return m.group(1).strip() if m else ''


def transportista_de(tipo_entrega):
    """delivery_type de Odoo -> gls / xpo / ''."""
    t = (tipo_entrega or '').lower()
    if t.startswith('gls'):
        return GLS
    if t.startswith('xpo'):
        return XPO
    return ''


RE_CIFRAS = re.compile(r'^\d{4,9}$')   # v1.1.0: las últimas cifras de la CJ, escritas a mano (etiqueta que no se lee)


def puede_dejar_fuera(fecha_validada, hoy):
    """v1.3.0: solo se puede dejar fuera de la etiqueta una OUT validada otro día (no la de hoy)."""
    return bool(fecha_validada and fecha_validada < hoy)


MAX_TANDA = 30     # v1.4.0: huecos solo dentro de una tanda corta de etiquetas


def huecos_tanda(usadas):
    """v1.4.0 (K24 25/11: la CJ665013675 se pegó en una caja y nunca se leyó en Odoo). usadas: {fecha de impresión:
    [números de secuencia de las CJ de la tienda impresas a esa hora]}. Devuelve los números que faltan entre la
    menor y la mayor de cada tanda (máximo MAX_TANDA de distancia): etiquetas impresas con estas cajas que no son
    cajas de la tienda. Quien llama mira si están vacías en Odoo."""
    res = set()
    for nums in usadas.values():
        nums = sorted(set(n for n in nums if n))
        if len(nums) < 2 or nums[-1] - nums[0] > MAX_TANDA:
            continue
        res.update(n for n in range(nums[0] + 1, nums[-1]) if n not in nums)
    return sorted(res)


GLS_MAX_BULTOS = 5        # v1.5.0 (Isaac 25/11): GLS normalmente hasta 5 bultos; las grandes, XPO
DIAS_HISTORIAL = 30
MIN_HISTORIAL = 3         # expediciones parecidas para fiarse del historial
PARTE_HABITUAL = 0.75     # «casi siempre» = 3 de cada 4


def habitual(bultos, historial):
    """v1.5.0: el transportista habitual de la tienda para una expedición de «bultos». historial: [(gls|xpo, bultos)]
    de las expediciones de la tienda de los últimos DIAS_HISTORIAL días. Primero las del mismo tamaño (hasta
    GLS_MAX_BULTOS o más); si hay pocas, todas. Devuelve (gls|xpo|'', veces, total): '' si no hay uno claro."""
    pequena = bultos <= GLS_MAX_BULTOS
    parecidas = [t for t, b in historial if t and (b <= GLS_MAX_BULTOS) == pequena]
    if len(parecidas) < MIN_HISTORIAL:
        parecidas = [t for t, b in historial if t]
    if len(parecidas) < MIN_HISTORIAL:
        return '', 0, len(parecidas)
    for t in TRANSPORTISTAS:
        veces = parecidas.count(t)
        if veces >= PARTE_HABITUAL * len(parecidas):
            return t, veces, len(parecidas)
    return '', 0, len(parecidas)


def avisos_transportista(elegido, bultos, historial):
    """v1.5.0: avisos (no prohíben) si se elige el transportista que no toca: GLS con más de GLS_MAX_BULTOS bultos, o
    el contrario del habitual de la tienda. Lista de textos."""
    res = []
    if elegido == GLS and bultos > GLS_MAX_BULTOS:
        res.append('GLS normalmente lleva hasta %d bultos y esta expedición tiene %d: las grandes suelen ir por XPO.'
                   % (GLS_MAX_BULTOS, bultos))
    t, veces, total = habitual(bultos, historial)
    if t and t != elegido:
        res.append('Esta tienda sale casi siempre por %s (%d de sus últimas %d expediciones parecidas, %d días).'
                   % (NOMBRES[t], veces, total, DIAS_HISTORIAL))
    return res


def es_sumi(origen):
    """v1.2.0: OUT de suministros de la tienda (origen «SUMINISTROS KOROSHI 24/11 K41»), no del pedido S-."""
    return (origen or '').strip().upper().startswith('SUMINISTROS')


def son_cifras(texto):
    """True si lo escrito son de 4 a 9 cifras (el final de una CJ escrito a mano)."""
    return bool(RE_CIFRAS.match((texto or '').strip()))


def elegir_por_cifras(cifras, candidatas):
    """v1.1.0: la CJ de candidatas que acaba en esas cifras. Devuelve (cj, coinciden): cj si hay una sola; si no, ''
    y la lista de las que coinciden (vacía = ninguna, varias = hay que escribir más cifras)."""
    cifras = (cifras or '').strip()
    coinciden = sorted(set(c for c in candidatas if c and c.endswith(cifras)))
    return (coinciden[0] if len(coinciden) == 1 else ''), coinciden


def cuadre(leidas, esperadas):
    """leidas: [CJ escaneadas, en orden]; esperadas: {CJ: [OUT]} de las OUT pendientes de etiqueta de la tienda.
    Devuelve {'bien': [CJ leídas que tocan], 'sobran': [CJ leídas que no tocan], 'faltan': [CJ esperadas sin leer],
    'ok': todo cuadra, 'esperadas': n, 'leidas': n}."""
    vistas = []
    for cj in leidas:
        if cj not in vistas:
            vistas.append(cj)
    bien = [cj for cj in vistas if cj in esperadas]
    sobran = [cj for cj in vistas if cj not in esperadas]
    faltan = sorted(cj for cj in esperadas if cj not in vistas)
    return {'bien': bien, 'sobran': sobran, 'faltan': faltan, 'esperadas': len(esperadas), 'leidas': len(bien),
            'ok': bool(esperadas) and not sobran and not faltan}


def motivo_sobra(d):
    """Por qué una CJ escaneada no cuenta para la expedición. d: lo que se sabe de ella en Odoo:
    existe, juntada_en, outs ([{'nombre', 'tienda', 'estado', 'tracking', 'dias', 'en_cierre'}]), tienda (la de la
    pantalla)."""
    if not d.get('existe'):
        return 'no existe en Odoo'
    if d.get('juntada_en'):
        return 'está juntada dentro de %s (Juntar cajas): ya no es un bulto' % d['juntada_en']
    outs = d.get('outs') or []
    if not outs:
        return 'está vacía: no tiene prendas en ninguna OUT'
    otras = sorted(set(o['tienda'] or 'sin tienda' for o in outs if o['tienda'] != d.get('tienda')))
    if otras:
        return 'es de otra tienda: %s' % ', '.join(otras)
    dejadas = [o['nombre'] for o in outs if o.get('fuera')]      # v1.3.0
    if dejadas:
        return 'su OUT está dejada fuera de esta etiqueta: %s (apártala)' % ', '.join(dejadas)
    sin_validar = [o['nombre'] for o in outs if o['estado'] != 'done']
    if sin_validar:
        return 'su OUT no está validada: %s' % ', '.join(sin_validar)
    con_etiqueta = ['%s (%s)' % (o['nombre'], o['tracking']) for o in outs if o.get('tracking')]
    if con_etiqueta:
        return 'ya tiene etiqueta: %s' % ', '.join(con_etiqueta)
    en_cierre = [o['nombre'] for o in outs if o.get('en_cierre')]
    if en_cierre:
        return 'va en un camión XPO ya cerrado: %s' % ', '.join(en_cierre)
    viejas = [o['nombre'] for o in outs if (o.get('dias') or 0) > DIAS_PENDIENTES]
    if viejas:
        return 'su OUT es de hace más de %d días: %s (hacerlo desde el portátil)' % (DIAS_PENDIENTES, ', '.join(viejas))
    return 'no está en ninguna OUT pendiente de etiqueta de esta tienda'


def reparto_gls(outs):
    """Acción 1834 v5 (GLS), para UNA tienda. outs: [{'id', 'bultos' (number_of_packages), 'cajas' (ids de cajas)}].
    GLS cuenta los bultos OUT por OUT: las OUT sin bultos (juntadas) o cuyas cajas ya van en otra OUT que se manda
    (cajas compartidas) no se mandan; reciben el mismo tracking. Devuelve {'enviar': [ids], 'juntadas': [ids],
    'compartidas': [ids], 'bultos_gls': n, 'cajas': n} (bultos_gls != cajas = GLS contará de más: aviso)."""
    con_bultos = [o for o in outs if (o.get('bultos') or 0) > 0]
    enviar = con_bultos if con_bultos else list(outs)
    juntadas = [o['id'] for o in outs if o not in enviar]
    vistas = set()
    compartidas = []
    for o in sorted([o for o in enviar if o.get('cajas')], key=lambda x: (-len(x['cajas']), x['id'])):
        cajas = set(o['cajas'])
        if cajas - vistas:
            vistas |= cajas
        else:
            compartidas.append(o['id'])
    quedan = [o for o in enviar if o['id'] not in compartidas]
    bultos_gls = sum(len(o['cajas']) if o.get('cajas') else 1 for o in quedan)
    reales = len(vistas) + len([o for o in quedan if not o.get('cajas')])
    return {'enviar': [o['id'] for o in quedan], 'juntadas': juntadas + compartidas, 'compartidas': compartidas,
            'bultos_gls': bultos_gls, 'cajas': reales}

# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Retener pedidos de tienda: lo que se puede probar sin Odoo (tests/test_regla.py).
#   tienda_de(nombre)                 'K48 - LA MAQUINISTA' -> 'K48'
#   inicio_noche(ahora, hora_corte)   desde cuando cuentan los pedidos de esta noche (hora local)
#   horas(texto) / hora_pendiente()   a que horas del dia se revisa y cual toca ahora
#   numero_s4t(nombre)                'S-6665004614' -> '6665004614'
#   estados_de_items(items, numeros)  estado de cada pedido en la respuesta de la API de S4T
#   grupos_seguidos(lista, horas)     pedidos de una tienda que entran a menos de 'horas' unos de otros
#   decidir(pedidos, estados, s4t_ok, ventana_horas)  que pedidos se retienen y por que
#   texto_aviso(...)                  el correo para el responsable
# Diseno: bin/versiones/diseno-retener-pedidos-tienda_2026-11-24.md
# =============================================================================
import datetime
import re

RE_TIENDA = re.compile(r'^\s*(K\d+)\b', re.I)
RE_HORA = re.compile(r'^(\d{1,2}):(\d{2})$')

# Estados de S4T que cuentan como cancelado (en mayusculas)
CANCELADOS = ('CANCELLED', 'CANCELED', 'CANCELADO', 'CANCELADA')

# Motivos (los mismos valores que el campo motivo del modelo)
DUPLICADO = 'duplicado'
CANCELADO = 'cancelado'
DUPLICADO_CANCELADO = 'duplicado_cancelado'
UNICO_VIVO = 'unico_vivo'      # de una tienda con varios pedidos, el unico vivo en S4T: no se retiene


def tienda_de(nombre):
    """Codigo de tienda (K##) del nombre de la direccion de entrega, o '' si no es una tienda."""
    m = RE_TIENDA.match(nombre or '')
    return m and m.group(1).upper() or ''


def inicio_noche(ahora, hora_corte):
    """Inicio de la noche que se revisa (datetime local, sin cambiar la zona de 'ahora').
    Lo que entra despues de hora_corte (hh, mm) cuenta para la noche siguiente: a las 04:40 la noche empezo a la
    hora_corte de ayer; a las 15:00, a la hora_corte de hoy."""
    corte = ahora.replace(hour=hora_corte[0], minute=hora_corte[1], second=0, microsecond=0)
    if (ahora.hour, ahora.minute) < hora_corte:
        corte = corte - datetime.timedelta(days=1)
    return corte


def hora(texto, defecto):
    """'14:00' -> (14, 0). Si no se entiende, el defecto."""
    m = RE_HORA.match((texto or '').strip())
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        return int(m.group(1)), int(m.group(2))
    return defecto


def horas(texto):
    """'04:40, 05:45' -> [(4, 40), (5, 45)] ordenado y sin repetidos. Lo que no se entiende se ignora."""
    salida = set()
    for trozo in re.split(r'[,;\s]+', texto or ''):
        h = hora(trozo, None)
        if h:
            salida.add(h)
    return sorted(salida)


def hora_pendiente(ahora, lista, ultima, margen_min):
    """Revision de hoy que toca hacer, o None. ultima: clave 'AAAA-MM-DD HH:MM' de la ultima hecha.
    Devuelve la clave. Si han pasado mas de margen_min minutos desde la hora, no se hace (servidor parado)."""
    pasadas = [h for h in lista if (ahora.hour, ahora.minute) >= h]
    if not pasadas:
        return None
    h = pasadas[-1]
    clave = '%s %02d:%02d' % (ahora.date().isoformat(), h[0], h[1])
    if (ultima or '') >= clave:
        return None
    if (ahora.hour * 60 + ahora.minute) - (h[0] * 60 + h[1]) > margen_min:
        return None
    return clave


def numero_s4t(nombre):
    """Numero del pedido sin el prefijo de Odoo: 'S-6665004614' -> '6665004614'."""
    return re.sub(r'^[A-Za-z]+-', '', (nombre or '').strip())


def _texto(v):
    if v is None or isinstance(v, (dict, list)):
        return ''
    return str(v).strip()


def estados_de_items(items, numeros):
    """Estado en S4T de los pedidos 'numeros' (sin prefijo), buscando en la lista de pedidos de la API.

    No se sabe aun el nombre exacto de los campos (P0 del diseno): el numero es el primer valor de texto del pedido
    que coincide con uno de los numeros buscados (con o sin el prefijo 'S-'), y el estado, el del primer campo cuyo
    nombre lleva 'status', 'state' o 'estado'. Devuelve ({numero: ESTADO}, {'numero': campo, 'estado': campo})."""
    buscados = set(numeros)
    estados = {}
    campos = {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        num = None
        for k in sorted(it):
            t = numero_s4t(_texto(it[k]))
            if t in buscados:
                num = t
                campos.setdefault('numero', k)
                break
        if not num:
            continue
        for k in sorted(it):
            kl = k.lower()
            if ('status' in kl or 'state' in kl or 'estado' in kl) and _texto(it[k]):
                estados[num] = _texto(it[k]).upper()
                campos.setdefault('estado', k)
                break
    return estados, campos


def grupos_seguidos(lista, horas):
    """Parte los pedidos de una tienda en grupos de pedidos seguidos: cada uno entra a menos de 'horas' horas del
    anterior. lista: [{'creado': datetime, ...}]. Sin 'creado' (o horas <= 0) todo es un solo grupo.
    v1.1.0: medido en Odoo el 24/11 (120 dias): los duplicados de verdad (07/10 y 24/11) entran en menos de 2 h; un
    pedido de tarde (14:15, 15:00, 17:15) y el de la noche estan a 9-11 h y son pedidos distintos."""
    if not lista:
        return []
    if not horas or horas <= 0 or any(not p.get('creado') for p in lista):
        return [list(lista)]
    orden = sorted(lista, key=lambda p: p['creado'])
    grupos = [[orden[0]]]
    for p in orden[1:]:
        if p['creado'] - grupos[-1][-1]['creado'] <= datetime.timedelta(hours=horas):
            grupos[-1].append(p)
        else:
            grupos.append([p])
    return grupos


def decidir(pedidos, estados, s4t_ok, ventana_horas=0):
    """Que pedidos de la noche se retienen.

    pedidos: [{'id', 'name', 'tienda', 'creado', ...}] (los que no tienen tienda K## no se miran).
    estados: {numero sin prefijo: ESTADO S4T}. s4t_ok: True si la API ha contestado.
    Reglas (diseno 24/11):
      - Pedido cancelado en S4T: se retiene siempre.
      - Tienda con mas de un pedido seguido (a menos de ventana_horas uno de otro; 0 = toda la noche): se retienen
        todos los del grupo, salvo que S4T haya contestado, conozca todos los del grupo y solo uno siga vivo: ese
        pasa (UNICO_VIVO) y se retienen los cancelados.
    Devuelve {id: (retener, motivo, estado_s4t)} solo de los pedidos que se apuntan (retenidos y unicos vivos)."""
    por_tienda = {}
    for p in pedidos:
        if p.get('tienda'):
            por_tienda.setdefault(p['tienda'], []).append(p)
    salida = {}
    grupos = []
    for lista in por_tienda.values():
        grupos.extend(grupos_seguidos(lista, ventana_horas))
    for lista in grupos:
        info = []
        for p in lista:
            est = estados.get(numero_s4t(p['name']), '') if s4t_ok else ''
            info.append((p, est, est in CANCELADOS))
        if len(lista) == 1:
            p, est, cancelado = info[0]
            if cancelado:
                salida[p['id']] = (True, CANCELADO, est)
            continue
        conocidos = s4t_ok and all(est for _p, est, _c in info)
        vivos = [p for p, est, c in info if not c]
        for p, est, cancelado in info:
            if conocidos and len(vivos) == 1 and not cancelado:
                salida[p['id']] = (False, UNICO_VIVO, est)
            else:
                salida[p['id']] = (True, cancelado and DUPLICADO_CANCELADO or DUPLICADO, est)
    return salida


TEXTO_MOTIVO = {
    DUPLICADO: 'RETENIDO (varios pedidos de la tienda)',
    CANCELADO: 'RETENIDO (cancelado en S4T)',
    DUPLICADO_CANCELADO: 'RETENIDO (cancelado en S4T)',
    UNICO_VIVO: 'pasa a zonas (único vivo en S4T)',
}


def texto_aviso(filas, nota_s4t, modo):
    """Correo para el responsable. filas: [{'tienda', 'pedido', 'hora', 'uds', 'estado_s4t', 'motivo', 'retener',
    'decision'}]. Agrupado por tienda, en orden de tienda y de entrada."""
    retenidos = [f for f in filas if f['retener'] and f.get('decision', 'pendiente') == 'pendiente']
    tiendas = sorted(set(f['tienda'] for f in retenidos), key=lambda t: (len(t), t))
    lineas = ['%s pedidos de tienda retenidos sin decidir (%s tiendas).' % (len(retenidos), len(tiendas))]
    if modo != 'real':
        lineas.append('MODO AVISO: el módulo solo avisa; estos pedidos SÍ entran en las zonas y en el reparto.')
    lineas.append('S4T: %s' % nota_s4t)
    lineas.append('')
    todas = sorted(set(f['tienda'] for f in filas), key=lambda t: (len(t), t))
    for t in todas:
        de_t = sorted([f for f in filas if f['tienda'] == t], key=lambda f: (f['hora'], f['pedido']))
        if not any(f['retener'] and f.get('decision', 'pendiente') == 'pendiente' for f in de_t):
            continue
        lineas.append('%s (%s pedidos esta noche)' % (t, len(de_t)))
        for f in de_t:
            texto = TEXTO_MOTIVO.get(f['motivo'], f['motivo'])
            if f['retener'] and f.get('decision', 'pendiente') != 'pendiente':
                texto = 'decidido: %s' % f['decision']
            lineas.append('   %-14s %s  %5s uds  S4T: %-10s %s' % (
                f['pedido'], f['hora'], int(f['uds'] or 0), f['estado_s4t'] or '-', texto))
    lineas.append('')
    lineas.append('Decidir en KOROSHI > Pedidos de tienda retenidos: «Preparar este» o «Ya cancelado en Odoo». '
                  'El módulo no cancela nada.')
    return '\n'.join(lineas)

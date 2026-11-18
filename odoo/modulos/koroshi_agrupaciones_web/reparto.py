# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Agrupaciones web: lo que se puede probar sin Odoo (tests/test_reparto.py).
#   cortes(texto)                   '06:00,11:00' -> [(6, 0), (11, 0)]
#   corte_pendiente(ahora, ...)     que corte de hoy toca hacer (o None)
#   repartir(outs, tope)            OUT en orden de llegada en grupos de hasta 'tope' uds (nunca se parte una OUT)
#   siguiente_numero(nombres, pre)  WEB_ddmmaa_NN: el siguiente NN libre del dia
# =============================================================================
import datetime
import re


def cortes(texto):
    """'06:00, 11:00' -> [(6, 0), (11, 0)] ordenado y sin repetidos. Lo que no se entiende se ignora."""
    salida = set()
    for trozo in re.split(r'[,;\s]+', texto or ''):
        m = re.match(r'^(\d{1,2}):(\d{2})$', trozo.strip())
        if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
            salida.add((int(m.group(1)), int(m.group(2))))
    return sorted(salida)


def clave_corte(dia, hhmm):
    """Clave con la que se apunta un corte hecho: 'AAAA-MM-DD HH:MM'."""
    return '%s %02d:%02d' % (dia.isoformat(), hhmm[0], hhmm[1])


def corte_pendiente(ahora, lista_cortes, ultimo, margen_min):
    """Corte de hoy que toca hacer, o None.

    ahora: datetime local (hora del almacen). ultimo: clave del ultimo corte hecho ('' si ninguno).
    Toca el ultimo corte de hoy que ya ha pasado y aun no se ha hecho. Devuelve (clave, (hh, mm), tarde):
    tarde = True si han pasado mas de margen_min minutos desde la hora del corte (servidor parado, modulo
    recien encendido): ese corte se apunta como hecho pero no se ejecuta, para no agrupar ni cancelar a deshora."""
    hoy = ahora.date()
    pasados = [c for c in lista_cortes if (ahora.hour, ahora.minute) >= c]
    if not pasados:
        return None
    hhmm = pasados[-1]
    clave = clave_corte(hoy, hhmm)
    if ultimo and ultimo >= clave:
        return None
    hora = datetime.datetime.combine(hoy, datetime.time(hhmm[0], hhmm[1]))
    minutos = (ahora.replace(tzinfo=None) - hora).total_seconds() / 60.0
    return clave, hhmm, minutos > margen_min


def repartir(outs, tope):
    """outs: lista de (id, uds) YA en orden de llegada. Devuelve listas de ids.

    Se van metiendo OUT hasta que la siguiente pasaria de 'tope' uds; entonces se abre otro grupo. Una OUT nunca se
    parte: si ella sola pasa del tope, va en un grupo para ella. tope <= 0 = sin tope (un solo grupo)."""
    grupos = []
    actual, uds = [], 0
    for ident, n in outs:
        if actual and tope > 0 and uds + n > tope:
            grupos.append(actual)
            actual, uds = [], 0
        actual.append(ident)
        uds += n
    if actual:
        grupos.append(actual)
    return grupos


def siguiente_numero(nombres, prefijo):
    """Mayor NN de los nombres 'prefijo + NN' (p. ej. WEB_181126_03) + 1. Ignora lo que no encaja."""
    mayor = 0
    for nombre in nombres:
        resto = (nombre or '').strip()[len(prefijo):] if (nombre or '').strip().startswith(prefijo) else ''
        if resto.isdigit():
            mayor = max(mayor, int(resto))
    return mayor + 1

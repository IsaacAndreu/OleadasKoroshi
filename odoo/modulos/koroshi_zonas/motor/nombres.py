# -*- coding: utf-8 -*-
# =============================================================================
# Nombres de agrupaciones de zonas y lo que se lee de la nota de la OUT.
# Agrupacion de zona: Z-ddmm-<zona> o Z-ddmm-R2-<zona>, con <zona> = D1, ZX, ZX2, MU1, A...
# Almacen crea a mano otras agrupaciones que empiezan por Z- para imprimir lo del transportista
# ('Z-2210-SALIO 22-10', 'Z-2710- SALE 28-10', 'Z-1011 SALE 11-'): NO son zonas. Sus OUT se cuentan en la
# zona que dice su nota ('Z-2210-D3 | CAJA 05 | ...'), si la nota aun lo lleva.
# =============================================================================
import re

RE_LOTE = re.compile(r'^(Z-\d{4}-(?:R\d+-)?)([A-Z]{1,3}\d{0,2})$')
RE_CAJAS_NOTA = re.compile(r'\|\s*CAJAS\s+(\d+)')


def partir_nombre_lote(nombre):
    """'Z-1011-R2-MU1' -> ('Z-1011-R2-', 'MU1'). None si no es una agrupacion de zona."""
    m = RE_LOTE.match((nombre or '').strip())
    return m and (m.group(1), m.group(2)) or None


def es_lote_z(nombre):
    """Cualquier agrupacion que empieza por Z- (de zona o de almacen)."""
    return (nombre or '').startswith('Z-')


def zona_de_nota(nota):
    """'Z-2210-D3 | CAJA 05 | K1 - ... | CAJAS 2' -> ('Z-2210-', 'D3'). None si la nota no lo dice."""
    primero = (nota or '').split('|')[0]
    return partir_nombre_lote(primero)


def cajas_de_nota(nota):
    """'... | CAJAS 3' -> 3. None si la nota ya no lo lleva (otro proceso la pisa con 'Envio junto: ...')."""
    m = RE_CAJAS_NOTA.search(nota or '')
    if not m:
        return None
    return int(m.group(1))

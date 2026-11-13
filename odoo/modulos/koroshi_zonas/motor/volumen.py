# -*- coding: utf-8 -*-
# =============================================================================
# Litros por prenda y cajas por OUT.
# Copia EXACTA de las formulas de la v12f (accion 1883, lineas 463-483), con sus mismos valores por
# defecto. No cambiar sin cambiar la fase 2 (el criterio es dar el mismo reparto que la 1883).
# Fase 3: los valores pasan a koroshi.zonas.config y la tabla a koroshi.kpi.peso.tipo.
# =============================================================================

LITROS_CAJA = 80.0
CIERRE_MIN = 0.8
LITROS_DEFECTO = 3.0
LITROS_TIPO = {'JA': 8.0, 'XC': 12.0, 'ZB': 14.0, 'SU': 4.0, 'TR': 3.7, 'CL': 3.0, 'PT': 2.2, 'PL': 2.1,
               'ML': 1.9, 'VS': 1.8, 'FA': 1.6, 'TP': 1.2, 'BL': 0.8, 'ZC': 0.6}

EPS = 0.001


class Medidas(object):
    """Parametros de la caja. Por defecto, los de la v12f."""

    def __init__(self, litros_caja=LITROS_CAJA, cierre_min=CIERRE_MIN, litros_tipo=None,
                 litros_defecto=LITROS_DEFECTO):
        self.litros_caja = float(litros_caja)
        self.cierre_min = float(cierre_min)
        self.litros_tipo = dict(LITROS_TIPO if litros_tipo is None else litros_tipo)
        self.litros_defecto = float(litros_defecto)

    def como_dict(self):
        return {'litros_caja': self.litros_caja, 'cierre_min': self.cierre_min,
                'litros_tipo': dict(self.litros_tipo), 'litros_defecto': self.litros_defecto}


def litros_ud(volumen_m3, referencia, medidas):
    """Litros de una prenda: el volumen del producto en Odoo (m3) y, si no tiene, la tabla por tipo
    (letras 5 y 6 de la referencia: 2421JA14-... = JA). v12f: litros_ud()."""
    v = (volumen_m3 or 0.0) * 1000.0
    if v <= 0:
        codigo = referencia or ''
        v = medidas.litros_tipo.get(codigo[4:6], medidas.litros_defecto)
    return v


def cajas_de(litros, medidas):
    """Cajas que hacen falta para estos litros: hacia arriba y minimo 1. v12f: cajas_de()."""
    n = int(litros / medidas.litros_caja)
    if n * medidas.litros_caja < litros - EPS:
        n += 1
    return max(1, n)


def cerrada(litros, medidas):
    """Una OUT se coge llenando una caja, cerrandola y abriendo otra: esta en caja cerrada si su ULTIMA
    caja llega a cierre_min (las anteriores van llenas). v12f: cerrada()."""
    if litros <= EPS:
        return True
    return litros - medidas.litros_caja * (cajas_de(litros, medidas) - 1) >= \
        medidas.cierre_min * medidas.litros_caja - EPS


def caja_llena(litros, medidas):
    """Una caja REAL (una matricula) esta llena si lo que lleva dentro llega a cierre_min de la caja."""
    return litros >= medidas.cierre_min * medidas.litros_caja - EPS

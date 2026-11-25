# -*- coding: utf-8 -*-
"""Qué es cada ubicación de Odoo, a partir de su nombre, ruta y código de barras. Funciones puras.

Formato real (muestra leída el 23/11/2026):
  nombre «00006 - L01 P19 C2», ruta «EFFEC/Stock/NAVE2/00006 - L01 P19 C2», código de barras «L01 P19 C2».
Contenedores: «KO_110626_032» / «TT_…», hijos del hueco (koroshi_contenedores).
Muelle: «MU-05»; N1-: «N1-L..» en la ruta (bin/KOROSHI_partir_OUT_zonas_…_v12e: MUELLE_FIJO).
Los nombres que no encajan no se descartan: quedan con tipo 'otra' y salen en el resumen.
"""
import re

RE_HUECO = re.compile(r'\bL(\d{1,3})\s*P(\d{1,2})\s*C(\d{1,2})\b', re.I)
RE_HUECO_SIN_NIVEL = re.compile(r'\bL(\d{1,3})\s*P(\d{1,2})\b', re.I)
PREFIJOS_CONTENEDOR = ('KO_', 'TT_')
# Solo la NAVE2 del almacén EFFEC (KOROSHI). La compañía 8 tiene más almacenes (MODAL, TARKO); TARKO también
# tiene una «NAVE2» (descarga del 23/11: 600 contenedores KO_ en TARKO/Stock/NAVE2) que no es esta nave.
RAIZ_NAVE = 'EFFEC/Stock/NAVE2'

TIPOS = ('hueco', 'contenedor', 'muelle', 'n1', 'perchas', 'otra')


def clasificar(nombre, ruta, codigo_barras):
    """Devuelve {'tipo', 'lineal', 'posicion', 'nivel', 'en_nave'}.

    - hueco: «Lnn Pnn Cn» en el código de barras o, si no, en el nombre (lineal/posición/nivel como números).
    - contenedor: nombre KO_/TT_ (su hueco es el padre; se resuelve al cargar).
    - muelle: nombre MU-… ; n1: «/N1-» en la ruta (se miran antes que el hueco: N1-L.. lleva «L.. P..»).
    - perchas: «PERCHA» en el nombre (PERCHAS_KO: 32.239 uds PERMANENTE el 23/11).
    - Además, al cargar, todo hijo de un hueco es contenedor aunque no sea KO_/TT_ (GC_, ECIGC_, MI_, números…:
      1.100 el 23/11): lo hace descarga.clasificar_en_bd.
    - otra: todo lo demás (SORTER, CAJAS, NAVE2, Stock, nombres que no encajan…).
    """
    nombre = (nombre or '').strip()
    ruta = ruta or ''
    codigo = (codigo_barras or '').strip()
    r = {'tipo': 'otra', 'lineal': None, 'posicion': None, 'nivel': None,
         'en_nave': ruta == RAIZ_NAVE or ruta.startswith(RAIZ_NAVE + '/')}
    if nombre.upper().startswith(PREFIJOS_CONTENEDOR):
        r['tipo'] = 'contenedor'
        return r
    if nombre.upper().startswith('MU-') or '/MU-' in ruta:
        r['tipo'] = 'muelle'
        return r
    if '/N1-' in ruta or nombre.upper().startswith('N1-'):
        r['tipo'] = 'n1'
        return r
    if 'PERCHA' in nombre.upper():
        r['tipo'] = 'perchas'
        return r
    m = RE_HUECO.search(codigo) or RE_HUECO.search(nombre)
    if m:
        r.update(tipo='hueco', lineal=int(m.group(1)), posicion=int(m.group(2)), nivel=int(m.group(3)))
    return r


def texto_hueco(lineal, posicion, nivel=None):
    """«L03 P05 C4» (o «L03 P05» sin nivel), como lo escribe Odoo."""
    t = 'L%02d P%02d' % (lineal, posicion)
    return t if nivel is None else '%s C%d' % (t, nivel)

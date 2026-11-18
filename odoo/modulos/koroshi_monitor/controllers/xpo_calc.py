# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Monitor: filas del Excel «PREVISIÓN XPO AMPOSTA» del cierre del camión, en Python puro (sin Odoo).
#
# v1.34.0 (18/11/2026): Erika (KOROSHI) pidió el 18/11 que el correo del cierre del camión lleve solo lo que XPO
# necesita, con el formato del Excel que ya le mandaban («Envíos Koroshi AMPOSTA dd-mm-aaaa»): fecha de salida,
# nº de expedición, nombre de tienda, bultos, volumen y peso. Es provisional, hasta que la informática de KOROSHI
# lo mande desde su API.
#   - Una fila por nº de expedición (cada expedición es un expediente en XPO).
#   - Bultos = los declarados a XPO al hacer la etiqueta (nota «XPO: declarados N bultos»); si la expedición no
#     tiene nota, los bultos de las OUT del pedido. Las mismas cuentas que el Excel de Tiendas y el resumen del
#     cierre (envios.py), para que el total del correo cuadre con el de la pantalla.
#   - Volumen y peso con el criterio de XPO por bulto: el mismo que koroshi_xpo_bultos
#     (models/delivery_carrier.py: PESO_BULTO y VOLUMEN_BULTO). El Excel de Amposta del 17/11 da lo mismo:
#     K01, 7 bultos = 0,63 m3 y 105 kg.
# Pruebas: tests/test_xpo_calc.py (sin Odoo).
# =============================================================================
import re

PESO_BULTO = 15.0      # kg por bulto (criterio de XPO; igual que koroshi_xpo_bultos)
VOLUMEN_BULTO = 0.09   # m3 por bulto (criterio de XPO; igual que koroshi_xpo_bultos)

CABECERA = ['Fecha salida', 'Nº expedición', 'Nombre tienda', 'Bultos', 'Volumen m3', 'Peso Neto']


def _orden(fila):
    numero = re.search(r'K(\d+)', fila['tienda'] or '', re.I)
    return (int(numero.group(1)) if numero else 99999, fila['tienda'] or '', fila['expedicion'] or '')


def filas_xpo(grupos, declarados):
    """grupos: los de envios._agrupar (un dict por pedido con 'tienda', 'expediciones' y 'bultos').
    declarados: {nº expedición: bultos declarados a XPO}.

    Devuelve una lista de {'tienda', 'expedicion', 'bultos', 'volumen', 'peso'}, ordenada por número de tienda."""
    filas = {}
    for g in grupos:
        tienda = g.get('tienda') or '—'
        refs = [x for x in g.get('expediciones') or [] if x in declarados]
        if refs:
            # Lo declarado va una sola vez por expedición, aunque la expedición lleve varios pedidos.
            for ref in refs:
                filas.setdefault((tienda, ref), {'tienda': tienda, 'expedicion': ref, 'bultos': declarados[ref]})
            continue
        ref = ', '.join(g.get('expediciones') or [])
        fila = filas.setdefault((tienda, ref), {'tienda': tienda, 'expedicion': ref, 'bultos': 0})
        fila['bultos'] += g.get('bultos') or 0
    resultado = sorted(filas.values(), key=_orden)
    for fila in resultado:
        fila['volumen'] = round(fila['bultos'] * VOLUMEN_BULTO, 2)
        fila['peso'] = round(fila['bultos'] * PESO_BULTO, 2)
    return resultado

# -*- coding: utf-8 -*-
# =============================================================================
# Lector: lee de Odoo y construye los datos planos que recibe el motor. Solo lee.
# =============================================================================
import re

from ..motor import volumen

COMPANY_ID = 8                  # EFFECTIVE LOGISTICS, S.L.
RE_CAJAS_NOTA = re.compile(r'\|\s*CAJAS\s+(\d+)')
# Agrupacion de zonas: Z-ddmm-<zona> o Z-ddmm-R2-<zona> (segunda tanda del dia)
RE_LOTE = re.compile(r'^(Z-\d{4}-(?:R\d+-)?)(.+)$')

CAMPOS_LINEA = ['id', 'picking_id', 'result_package_id', 'qty_done', 'product_id']


def partir_nombre_lote(nombre):
    """'Z-1011-R2-MU1' -> ('Z-1011-R2-', 'MU1'). None si no es una agrupacion de zonas."""
    m = RE_LOTE.match(nombre or '')
    return m and (m.group(1), m.group(2)) or None


def cajas_de_nota(nota):
    """'Z-1011-D1 | CAJA 01 | K1 - ... | PEDIDO S-... | CAJAS 3' -> 3. None si la nota ya no lo lleva
    (otro proceso la pisa con 'Envio junto: ...')."""
    m = RE_CAJAS_NOTA.search(nota or '')
    if not m:
        return None
    return int(m.group(1))


def lineas_para_medir(env, pickings, medidas):
    """Lineas leidas (qty_done > 0, sin cancelar) de estas OUT y de cualquier otra OUT que use sus cajas.
    Devuelve la lista de dicts que espera motor.medir.medir()."""
    Line = env['stock.move.line'].sudo()
    propias = Line.search_read([('picking_id', 'in', pickings.ids), ('state', '!=', 'cancel'),
                                ('qty_done', '>', 0)], CAMPOS_LINEA, order='id')
    cajas = list(set([x['result_package_id'][0] for x in propias if x['result_package_id']]))
    otras = []
    if cajas:
        otras = Line.search_read([('result_package_id', 'in', cajas), ('state', '!=', 'cancel'),
                                  ('qty_done', '>', 0), ('picking_id', 'not in', pickings.ids)],
                                 CAMPOS_LINEA, order='id')
    todas = propias + otras
    ids_prod = list(set([x['product_id'][0] for x in todas if x['product_id']]))
    prod = {}
    for p in env['product.product'].sudo().with_context(active_test=False).browse(ids_prod).read(
            ['volume', 'default_code']):
        prod[p['id']] = volumen.litros_ud(p['volume'], p['default_code'], medidas)
    lineas = []
    for x in todas:
        if not x['picking_id']:
            continue
        lit_ud = x['product_id'] and prod.get(x['product_id'][0], medidas.litros_defecto) or medidas.litros_defecto
        lineas.append({
            'id': x['id'],
            'out_id': x['picking_id'][0],
            'caja_id': x['result_package_id'] and x['result_package_id'][0] or None,
            'uds': x['qty_done'],
            'litros': lit_ud * x['qty_done'],
        })
    return lineas

# -*- coding: utf-8 -*-
# PRUEBA (24/11/2026, tuctuc): buscar productos por «Stock = N» (qty_available). SOLO LECTURA: no escribe nada y
# deshace al final.
#
# Hoy (odoo13/addons/stock/models/product.py:323 _search_qty_available): solo «> 0» usa los quants; cualquier otra
# busqueda (= 10, < 5, = 0...) va a _search_product_quantity (:351), que recorre los ~364.000 productos y calcula
# qty_available de cada uno (movimientos, kits de mrp...). La pantalla se queda «pensando» mas de una hora.
#
# NUEVA (propuesta): qty_available sin fechas es la suma de los quants de las ubicaciones del almacen redondeada a la
# unidad de medida (_compute_quantities_dict). Se suma en SQL por producto (mismo dominio y reglas de acceso), los que
# no tienen quants valen 0, y los KITS (mrp, bom phantom) se calculan como hasta ahora (ORM), porque su stock sale
# de los componentes. Luego se aplica el operador.
#
# Comprobaciones:
#   1) Muestra de productos al azar + todos los kits: qty_available de Odoo (ORM) == valor de la NUEVA.
#   2) Tiempo de la NUEVA completa para «= 10», «= 0», «< 0» y «> 0» (esta ultima contra la rapida de Odoo).
#   3) Estimacion del tiempo de HOY = segundos por producto de la muestra x productos.
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261124_prueba_buscar_stock_igual_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
import random
import sys
import time

from odoo.addons.stock.models.product import OPERATORS
from odoo.tools.float_utils import float_round

EMPRESA = 21          # UNITED BRANDS 2015 SL (cids=21 en la pantalla de Isaac)
MUESTRA = 3000


def log(t):
    print(t)
    sys.stdout.flush()


e = env(context=dict(env.context, allowed_company_ids=[EMPRESA], force_company=EMPRESA))
PP = e['product.product']
Q = e['stock.quant']
cr = e.cr


def nueva_mapa():
    """{product_id: qty_available} de los productos que no son kit, igual que _compute_quantities_dict."""
    dominio = PP._get_domain_locations()[0]
    q = Q._where_calc(dominio)
    Q._apply_ir_rules(q, 'read')
    f, w, p = q.get_sql()
    cr.execute('SELECT "stock_quant".product_id, sum("stock_quant".quantity) FROM %s WHERE %s '
               'GROUP BY "stock_quant".product_id' % (f, w), p)
    return dict(cr.fetchall())


def redondeos(ids):
    cr.execute("""SELECT pp.id, u.rounding FROM product_product pp
                  JOIN product_template pt ON pt.id = pp.product_tmpl_id
                  JOIN uom_uom u ON u.id = pt.uom_id WHERE pp.id = ANY(%s)""", (list(ids),))
    return dict(cr.fetchall())


def kits_de(productos):
    if 'mrp.bom' not in e:
        return PP
    # mismo criterio que mrp/models/product.py _compute_quantities_dict (bom phantom de la empresa)
    return PP.browse([pr.id for pr in e['mrp.bom']._get_product2bom(productos, bom_type='phantom')])


def buscar_nueva(operator, value, todos, kits, mapa, redondeo):
    op = OPERATORS[operator]
    ids = []
    kit_ids = set(kits.ids)
    for pid in todos:
        if pid in kit_ids:
            continue
        qty = float_round(mapa.get(pid, 0.0), precision_rounding=redondeo.get(pid, 0.01))
        if op(qty, value):
            ids.append(pid)
    for k in kits:            # kits: como hasta ahora
        if op(k.qty_available, value):
            ids.append(k.id)
    return ids


try:
    t = time.time()
    todos = PP.with_context(prefetch_fields=False).search([], order='id').ids
    log('PRUEBA productos (search([]) como hace Odoo): %s en %.1f s' % (len(todos), time.time() - t))

    t = time.time()
    kits = kits_de(PP.browse(todos))
    log('PRUEBA kits (bom phantom): %s en %.1f s' % (len(kits), time.time() - t))

    t = time.time()
    mapa = nueva_mapa()
    redondeo = redondeos(todos)
    t_mapa = time.time() - t
    log('PRUEBA NUEVA: suma de quants por producto en SQL: %s productos con quants en %.1f s' % (len(mapa), t_mapa))

    # 1) Muestra: Odoo (ORM, como hoy) contra NUEVA
    random.seed(24112026)
    kit_ids = set(kits.ids)
    muestra = random.sample([i for i in todos if i not in kit_ids], min(MUESTRA, len(todos)))
    # que la muestra tenga tambien productos con stock
    con_stock = [i for i in todos if mapa.get(i)]
    muestra = list(set(muestra + random.sample(con_stock, min(MUESTRA, len(con_stock)))))
    t = time.time()
    orm = {}
    for i in range(0, len(muestra), 500):
        lote = PP.browse(muestra[i:i + 500])
        for pr in lote:
            orm[pr.id] = pr.qty_available
        e.clear()
    t_orm = time.time() - t
    distintos = [(i, orm[i], float_round(mapa.get(i, 0.0), precision_rounding=redondeo.get(i, 0.01)))
                 for i in muestra
                 if abs(orm[i] - float_round(mapa.get(i, 0.0), precision_rounding=redondeo.get(i, 0.01))) > 1e-9]
    log('PRUEBA muestra %s productos: Odoo (ORM) %.1f s, distintos: %s' % (len(muestra), t_orm, len(distintos)))
    for d in distintos[:10]:
        log('  distinto: producto %s Odoo %s NUEVA %s' % d)
    por_producto = t_orm / max(len(muestra), 1)
    log('PRUEBA HOY (estimado): %.4f s por producto x %s = %.0f min por busqueda' % (
        por_producto, len(todos), por_producto * len(todos) / 60))

    # 2) Busquedas completas con la NUEVA
    for operator, value in (('=', 10), ('=', 0), ('<', 0), ('>', 0)):
        t = time.time()
        r = buscar_nueva(operator, value, todos, kits, nueva_mapa(), redondeo)
        log('PRUEBA NUEVA stock %s %s: %.1f s, %s productos' % (operator, value, time.time() - t, len(r)))
        if (operator, value) == ('>', 0):
            t = time.time()
            rapida = set(PP._search_qty_available_new('>', 0))
            log('  Odoo rapida (solo > 0): %.1f s, %s productos, iguales a NUEVA: %s (solo Odoo %s, solo NUEVA %s)' % (
                time.time() - t, len(rapida), rapida == set(r), len(rapida - set(r)), len(set(r) - rapida)))
finally:
    env.cr.rollback()
    log('PRUEBA deshecho (rollback): no queda nada escrito')

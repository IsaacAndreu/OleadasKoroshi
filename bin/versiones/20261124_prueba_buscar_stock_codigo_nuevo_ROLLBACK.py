# -*- coding: utf-8 -*-
# PRUEBA EN REAL del cambio de la busqueda por stock (24/11/2026, tuctuc). SOLO LECTURA: no escribe nada, deshace al
# final y devuelve las clases a como estaban.
#
# Carga el codigo NUEVO tal cual de los archivos cambiados (subidos a ~):
#   stock_product_nuevo.py  (odoo/nucleo_tuctuc/addons/stock/models/product.py)
#   mrp_product_nuevo.py    (odoo/nucleo_tuctuc/addons/mrp/models/product.py)
# y lo pone en las clases de Odoo solo dentro de este proceso (el servidor no se entera).
#
# Comprueba:
#   1) Kits: _productos_stock_aparte (nuevo) == mrp.bom._get_product2bom(todos, 'phantom') (lo que usa Odoo).
#   2) VERDAD: qty_available de TODOS los productos calculado por Odoo como hoy (uno a uno, ~19 min).
#      Lo que hoy devuelve la busqueda (_search_product_quantity) es exactamente «los que cumplen» segun esto.
#   3) Para varias busquedas, el codigo NUEVO (product.product.search([('qty_available', op, valor)])) da los MISMOS
#      productos que la verdad, y cuanto tarda. Tambien la pantalla de Productos (product.template).
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261124_prueba_buscar_stock_codigo_nuevo_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
import sys
import textwrap
import time

import odoo.addons.mrp.models.product as mod_mrp
import odoo.addons.stock.models.product as mod_stock
from odoo.addons.stock.models.product import OPERATORS

EMPRESA = 21          # UNITED BRANDS 2015 SL (cids=21 en la pantalla de Isaac)
CASOS = [('=', 10), ('=', 0), ('<', 0), ('>', 0), ('>=', 1), ('<=', 5), ('!=', 0), ('=', 1), ('>', 100), ('<', 1)]


def log(t):
    print(t)
    sys.stdout.flush()


def metodo(ruta, nombre, clase_py):
    """Saca 'def nombre' de la clase del archivo nuevo, tal cual, y lo compila con los globals del modulo real."""
    lineas = open(ruta, encoding='utf-8').read().split('\n')
    dentro = False
    trozo = []
    for i, l in enumerate(lineas):
        if l.startswith('    def %s(' % nombre):
            dentro = True
            trozo = [l]
            continue
        if dentro:
            if l.startswith('    def ') or l.startswith('    @') or l.startswith('class '):
                break
            trozo.append(l)
    assert trozo, nombre
    ns = dict(vars(sys.modules[clase_py.__module__]))
    exec(textwrap.dedent('\n'.join(trozo)), ns)
    return ns[nombre]


ST = mod_stock.Product
MR = mod_mrp.ProductProduct
NUEVOS = [
    (ST, '_search_qty_available', metodo('/home/it_nath_group/stock_product_nuevo.py', '_search_qty_available', ST)),
    (ST, '_productos_stock_aparte', metodo('/home/it_nath_group/stock_product_nuevo.py', '_productos_stock_aparte', ST)),
    (ST, '_buscar_stock_por_quants', metodo('/home/it_nath_group/stock_product_nuevo.py', '_buscar_stock_por_quants', ST)),
    (MR, '_productos_stock_aparte', metodo('/home/it_nath_group/mrp_product_nuevo.py', '_productos_stock_aparte', MR)),
]
originales = [(c, n, c.__dict__.get(n)) for c, n, f in NUEVOS]

e = env(context=dict(env.context, allowed_company_ids=[EMPRESA], force_company=EMPRESA))
PP = e['product.product']
try:
    for c, n, f in NUEVOS:
        setattr(c, n, f)

    t = time.time()
    todos = PP.with_context(prefetch_fields=False).search([], order='id').ids
    log('PRUEBA productos: %s (%.1f s)' % (len(todos), time.time() - t))

    # 1) kits
    t = time.time()
    kits_nuevo = set(PP._productos_stock_aparte().ids) & set(todos)
    t_nuevo = time.time() - t
    t = time.time()
    kits_odoo = {p.id for p in e['mrp.bom']._get_product2bom(PP.browse(todos), bom_type='phantom')}
    log('PRUEBA kits: nuevo %s en %.1f s | Odoo %s en %.1f s | iguales: %s' % (
        len(kits_nuevo), t_nuevo, len(kits_odoo), time.time() - t, kits_nuevo == kits_odoo))
    e.clear()

    # 2) verdad: qty_available de todos, como hoy
    t = time.time()
    verdad = {}
    for i in range(0, len(todos), 1000):
        for p in PP.browse(todos[i:i + 1000]):
            verdad[p.id] = p.qty_available
        e.clear()
    log('PRUEBA VERDAD (Odoo uno a uno, como hoy): %.0f s = %.1f min' % (time.time() - t, (time.time() - t) / 60))

    # 3) busquedas con el codigo nuevo
    for op, valor in CASOS:
        esperado = {pid for pid in todos if OPERATORS[op](verdad[pid], valor)}
        t = time.time()
        nuevo = set(PP.search([('qty_available', op, valor)]).ids)
        t_n = time.time() - t
        log('PRUEBA stock %s %s: NUEVO %.1f s, %s productos | iguales a hoy: %s' % (
            op, valor, t_n, len(nuevo), nuevo == esperado))
        if nuevo != esperado:
            log('  solo hoy (10): %s' % sorted(esperado - nuevo)[:10])
            log('  solo nuevo (10): %s' % sorted(nuevo - esperado)[:10])
        e.clear()
    t = time.time()
    n = e['product.template'].search_count([('qty_available', '=', 10)])
    log('PRUEBA pantalla Productos (product.template) stock = 10: %.1f s, %s plantillas' % (time.time() - t, n))
finally:
    env.cr.rollback()
    for c, n, f in originales:
        if f is None:
            if n in c.__dict__:
                delattr(c, n)
        else:
            setattr(c, n, f)
    log('PRUEBA deshecho (rollback) y clases como estaban: no queda nada escrito')

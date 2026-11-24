# -*- coding: utf-8 -*-
# PRUEBA multi_search_with_comma 11.0.1 en tuctuc (24/11/2026). odoo shell; no escribe nada (rollback al final).
# Compara la funcion _where_calc VIEJA (la cargada ahora) con la NUEVA (archivo subido a ~): mismo SQL generado y
# mismos resultados, y cuenta cuantas consultas lanza cada una en 200 busquedas.
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261124_prueba_busqueda_comas_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
from odoo.models import BaseModel

vieja = BaseModel._where_calc
ns = {}
exec(open('/home/it_nath_group/multi_search_nuevo.py').read(), ns)
nueva = ns['_where_calc']
BaseModel._where_calc = vieja   # el exec la ha puesto; se deja la vieja hasta comparar
print('PRUEBA instalado segun el registro: %s' % ('multi_search_with_comma' in env.registry._init_modules))
casos = [
    ('product.product', [('default_code', 'ilike', 'A1,B2, C3')]),
    ('product.product', [('name', 'ilike', 'camiseta')]),
    ('res.partner', [('name', 'ilike', 'prime,united')]),
    ('stock.picking', [('name', 'ilike', 'OUT,IN'), ('state', '=', 'done')]),
]
try:
    for modelo, dom in casos:
        M = env[modelo]
        res = {}
        for nombre, f in (('vieja', vieja), ('nueva', nueva)):
            BaseModel._where_calc = f
            q = M._where_calc(dom)
            sql = q.get_sql()
            ids = M.search(dom, limit=500, order='id').ids
            n0 = env.cr.sql_log_count if hasattr(env.cr, 'sql_log_count') else 0
            for _ in range(200):
                M._where_calc(dom)
            n1 = env.cr.sql_log_count if hasattr(env.cr, 'sql_log_count') else 0
            res[nombre] = (sql, ids, n1 - n0)
        print('PRUEBA %s %s: SQL igual %s, resultados igual %s (%s), consultas en 200 busquedas: vieja %s, nueva %s' % (
            modelo, dom, res['vieja'][0] == res['nueva'][0], res['vieja'][1] == res['nueva'][1],
            len(res['nueva'][1]), res['vieja'][2], res['nueva'][2]))
finally:
    BaseModel._where_calc = vieja
    env.cr.rollback()
    print('PRUEBA deshecho (rollback): no queda nada escrito')

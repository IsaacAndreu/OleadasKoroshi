# -*- coding: utf-8 -*-
# SOLO LECTURA (24/11/2026): plan (EXPLAIN, sin ejecutar) de la consulta agrupada del 347 de 2024 de PRIME
# (informe 7) tal como la monta Odoo, y de la misma partida en dos sin el OR de impuestos.
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261124_explain_mod347_SOLO-LECTURA.py 2>&1 | grep -E '^(PLAN|  )'
from odoo import api

rep0 = env['l10n.es.aeat.mod347.report'].browse(7)
e = api.Environment(env.cr, rep0.create_uid.id, dict(env.context, allowed_company_ids=[rep0.company_id.id]))
rep = rep0.with_env(e)
AML = e['account.move.line']
taxes = rep._get_taxes(e.ref('l10n_es_aeat_mod347.aeat_mod347_map_a'))
print('PLAN impuestos clave A: %s' % len(taxes))
base = [
    ('partner_id', '!=', False),
    ('date', '>=', rep.date_start),
    ('date', '<=', rep.date_end),
    ('parent_state', '=', 'posted'),
]
variantes = {
    'ACTUAL (con OR)': base + ['|', ('tax_ids', 'in', taxes.ids), ('tax_line_id', 'in', taxes.ids)],
    'PARTE 1 (tax_line_id)': base + [('tax_line_id', 'in', taxes.ids)],
    'PARTE 2 (tax_ids sin tax_line_id)': base + [('tax_ids', 'in', taxes.ids), '|',
                                                 ('tax_line_id', 'not in', taxes.ids),
                                                 ('tax_line_id', '=', False)],
}
for nombre, dom in variantes.items():
    q = AML._where_calc(dom)
    AML._apply_ir_rules(q, 'read')
    f, w, p = q.get_sql()
    sql = 'EXPLAIN SELECT "account_move_line".partner_id, sum("account_move_line".balance) FROM %s WHERE %s ' \
          'GROUP BY "account_move_line".partner_id' % (f, w)
    env.cr.execute(sql, p)
    print('PLAN ---- %s' % nombre)
    for (linea,) in env.cr.fetchall():
        print('  ' + linea[:180])
env.cr.rollback()

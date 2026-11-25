# -*- coding: utf-8 -*-
# PRUEBA EN REAL (25/11/2026, tuctuc) de la conciliacion automatica por ORIGEN de la factura. ROLLBACK: lo que hace
# dentro se deshace al final y las clases vuelven a como estaban; no queda nada escrito.
#
# Extracto 46266 (SHOPIFY, 23/11/2026, 42 lineas). La regla 330 «LIQUIDACION SHOPIFY-MOLLIE B2C» esta hoy en
# «Sugerir valores de contrapartida» y ha mandado las lineas WT# a la 43001000 sin casar las facturas.
# Dentro de la transaccion:
#   1) deshace la conciliacion de las lineas WT# del extracto (button_cancel_reconciliation);
#   2) pone la regla 330 como en la 1.a captura de contabilidad: «Casar con las facturas existentes», empresa
#      establecida, misma moneda, importe 100 %, auto-validar;
#   3) aplica las reglas como el boton de conciliar: primero con el codigo de HOY y despues (volviendo al punto 2)
#      con el NUEVO (account_reconcile_model.py con el origen), y compara.
# Comprueba que cada linea conciliada lo esta con la factura/devolucion de su pedido (el n.o WT esta en el origen o
# en la referencia), y que ninguna se concilia con otra.
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261125_prueba_conciliacion_por_origen_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
import re
import sys
import textwrap
import time

import odoo.addons.account.models.account_reconcile_model as mod_rec

EXTRACTO = 46266
REGLA = 330
NUEVO = '/home/it_nath_group/account_reconcile_model_nuevo.py'


def log(t):
    print(t)
    sys.stdout.flush()


def metodo(ruta, nombre, clase_py):
    """Saca 'def nombre' de la clase del archivo nuevo, tal cual, y lo compila con los globals del modulo real."""
    lineas = open(ruta, encoding='utf-8').read().split('\n')
    dentro = False
    trozo = []
    for l in lineas:
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


ARM = mod_rec.AccountReconcileModel
CAMBIADOS = ['_get_select_communication_flag', '_get_invoice_matching_query']
NUEVOS = [(n, metodo(NUEVO, n, ARM)) for n in CAMBIADOS]
originales = [(n, ARM.__dict__.get(n)) for n in CAMBIADOS]


def numeros(texto):
    return set(re.findall(r'\d+', texto or ''))


def revisar(e, lineas, res, etiqueta):
    conciliadas = [l for l in lineas if res.get(l.id, {}).get('status') == 'reconciled']
    propuestas = [l for l in lineas if res.get(l.id, {}).get('aml_ids') and l not in conciliadas]
    mal = []
    for l in conciliadas:
        movs = e['account.move.line'].browse(res[l.id]['aml_ids']).mapped('move_id')
        bien = all(numeros(l.name) & (numeros(m.invoice_origin) | numeros(m.ref)) for m in movs)
        if not bien:
            mal.append((l.name, l.amount, ', '.join('%s (origen %s, ref %s)' % (m.name, m.invoice_origin, m.ref)
                                                  for m in movs)))
    log('PRUEBA %s: %s lineas | conciliadas solas %s | solo propuestas %s | sin nada %s | conciliadas con OTRA '
        'factura: %s' % (etiqueta, len(lineas), len(conciliadas), len(propuestas),
                         len(lineas) - len(conciliadas) - len(propuestas), len(mal)))
    for m in mal:
        log('  MAL: %s %s -> %s' % m)
    return {l.id for l in conciliadas}


try:
    st = env['account.bank.statement'].browse(EXTRACTO)
    empresa = st.company_id
    e = env(context=dict(env.context, allowed_company_ids=[empresa.id], force_company=empresa.id))
    st = e['account.bank.statement'].browse(EXTRACTO)
    lineas = st.line_ids.filtered(lambda l: (l.name or '').startswith('WT#'))
    log('PRUEBA extracto %s (%s, %s): %s lineas, %s WT#' % (st.id, st.journal_id.name, st.date, len(st.line_ids),
                                                          len(lineas)))

    # 1) deshacer la conciliacion de las lineas WT#
    t = time.time()
    lineas.button_cancel_reconciliation()
    lineas.invalidate_cache()
    log('PRUEBA deshecha la conciliacion de %s lineas (%.1f s); con asientos aun: %s' % (
        len(lineas), time.time() - t, len(lineas.filtered(lambda l: l.journal_entry_ids))))

    # 2) regla 330 como «Casar con las facturas existentes»
    regla = e['account.reconcile.model'].browse(REGLA)
    regla.write({'rule_type': 'invoice_matching', 'match_partner': True, 'auto_reconcile': True,
                 'match_same_currency': True, 'match_total_amount': True, 'match_total_amount_param': 100})
    modelos = e['account.reconcile.model'].search([('rule_type', '!=', 'writeoff_button'),
                                                   ('company_id', '=', empresa.id)])
    log('PRUEBA reglas que se aplican: %s' % ', '.join('%s %s (%s)' % (m.id, m.name, m.rule_type) for m in modelos))
    e.cr.execute('SAVEPOINT prueba_conciliacion')

    # 3a) codigo de HOY
    t = time.time()
    res = modelos._apply_rules(lineas)
    hoy = revisar(e, lineas, res, 'HOY (%.1f s)' % (time.time() - t))
    e.cr.execute('ROLLBACK TO SAVEPOINT prueba_conciliacion')
    e.clear()

    # 3b) codigo NUEVO
    for n, f in NUEVOS:
        setattr(ARM, n, f)
    lineas = e['account.bank.statement.line'].browse(lineas.ids)
    modelos = e['account.reconcile.model'].browse(modelos.ids)
    t = time.time()
    res = modelos._apply_rules(lineas)
    nuevo = revisar(e, lineas, res, 'NUEVO (%.1f s)' % (time.time() - t))
    log('PRUEBA las que concilia HOY siguen conciliadas con el NUEVO: %s' % (hoy <= nuevo))
    for l in lineas.filtered(lambda x: x.id not in nuevo):
        r = res.get(l.id, {})
        movs = e['account.move.line'].browse(r.get('aml_ids', [])).mapped('move_id')
        log('  sin conciliar: %s %s -> propuesta: %s' % (l.name, l.amount, ', '.join(
            '%s (origen %s, %s)' % (m.name, m.invoice_origin, m.amount_total) for m in movs) or 'nada'))
finally:
    env.cr.rollback()
    for n, f in originales:
        if f is None:
            if n in ARM.__dict__:
                delattr(ARM, n)
        else:
            setattr(ARM, n, f)
    log('PRUEBA deshecho (rollback) y clases como estaban: no queda nada escrito')

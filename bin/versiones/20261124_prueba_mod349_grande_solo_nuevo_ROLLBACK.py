# -*- coding: utf-8 -*-
# PRUEBA l10n_es_aeat_mod349 1.2.1/1.2.2 en un 349 GRANDE (PRIME COLLECTIONS, marzo 2026), SOLO código nuevo
# (24/11/2026). El código viejo tarda horas con ~180.000 líneas, así que no se repite. Se ejecuta con odoo shell y
# DESHACE todo (rollback). Necesita en el mismo directorio 20261124_prueba_mod349_bloques_ROLLBACK_v2.py, del que
# toma las funciones nuevas (sacadas tal cual del módulo).
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261124_prueba_mod349_grande_solo_nuevo_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
import sys
import time

exec(open('/home/it_nath_group/20261124_prueba_mod349_bloques_ROLLBACK_v2.py').read().split('\n\nNUEVAS = [')[0])
NUEVAS = [_create_349_details, _crear_en_bloques, _tipos_cuenta_asiento, _prepare_349_record_detail,
          _prepare_349_refund_detail, _create_349_record_detail, _create_349_refund_detail,
          _create_349_invoice_records, _create_349_refund_records]
DESDE, HASTA = '2026-03-01', '2026-03-31'

Report = env['l10n.es.aeat.mod349.report']
clase = type(Report)
base = Report.search([('company_id.name', 'ilike', 'PRIME COLLECTIONS')], order='id desc', limit=1)
print('PRUEBA base %s: %s (%s a %s)' % (base.id, base.company_id.name, base.date_start, base.date_end))
sys.stdout.flush()
originales = {f.__name__: clase.__dict__.get(f.__name__) for f in NUEVAS}
bloque_original = clase.__dict__.get('BLOQUE_DETALLES')
try:
    vals = base.copy_data()[0]
    for k in list(vals):
        if k.endswith('_ids'):
            vals.pop(k)
    vals.update({'year': 2026, 'period_type': '03', 'date_start': DESDE, 'date_end': HASTA,
                 'statement_type': 'N', 'state': 'draft', 'name': 'PRUEBA349G'})
    rep = Report.create(vals)
    for f in NUEVAS:
        setattr(clase, f.__name__, f)
    clase.BLOQUE_DETALLES = 1000
    t = time.time()
    rep.calculate()
    rep.flush()
    print('PRUEBA codigo nuevo, %s a %s: %.1f s (%.1f min)' % (DESDE, HASTA, time.time() - t, (time.time() - t) / 60))
    print('PRUEBA   detalles %s, clientes %s, rectificaciones %s, total %.2f' % (
        len(rep.partner_record_detail_ids), len(rep.partner_record_ids), len(rep.partner_refund_ids),
        rep.total_partner_records_amount if 'total_partner_records_amount' in rep._fields else 0.0))
except Exception as ex:
    print('PRUEBA ERROR %r' % ex)
finally:
    env.cr.rollback()
    for nombre, f in originales.items():
        if f is None:
            if nombre in clase.__dict__:
                delattr(clase, nombre)
        else:
            setattr(clase, nombre, f)
    if bloque_original is None:
        if 'BLOQUE_DETALLES' in clase.__dict__:
            delattr(clase, 'BLOQUE_DETALLES')
    else:
        clase.BLOQUE_DETALLES = bloque_original
    print('PRUEBA deshecho (rollback): no queda nada escrito')

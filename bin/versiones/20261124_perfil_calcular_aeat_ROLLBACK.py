# -*- coding: utf-8 -*-
# PERFIL de «Calcular» de los modelos AEAT de tuctuc (24/11/2026). Se ejecuta con odoo shell y DESHACE todo.
# Para cada informe: tiempo, número de consultas SQL y las funciones donde se va el tiempo (cProfile).
# Calcula sobre el informe ya existente (no crea otro) y hace rollback después de cada uno: no queda nada escrito.
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261124_perfil_calcular_aeat_ROLLBACK.py 2>&1 | grep -E '^(PERFIL|  )'
import cProfile
import io
import pstats
import time

INFORMES = [
    ('l10n.es.aeat.mod303.report', 108),
    ('l10n.es.vat.book', 158),
    ('l10n.es.aeat.mod347.report', 7),
]


def perfil(modelo, rid):
    rec = env[modelo].browse(rid)
    print('PERFIL %s %s: compania %s, %s a %s, estado %s' % (
        modelo, rid, rec.company_id.name, rec.date_start, rec.date_end, rec.state))
    env.cr.execute('SELECT count(*) FROM account_move_line WHERE company_id = %s AND date BETWEEN %s AND %s',
                   (rec.company_id.id, rec.date_start, rec.date_end))
    print('PERFIL   apuntes del periodo: %s' % env.cr.fetchone()[0])
    antes = env.cr.sql_log_count
    prof = cProfile.Profile()
    t = time.time()
    try:
        prof.enable()
        rec.calculate()
        rec.flush()
        prof.disable()
        print('PERFIL   tiempo %.1f s, consultas %s' % (time.time() - t, env.cr.sql_log_count - antes))
        s = io.StringIO()
        pstats.Stats(prof, stream=s).sort_stats('cumulative').print_stats(r'addons|odoo/models|sql_db', 25)
        for linea in s.getvalue().splitlines():
            if linea.strip() and ('/' in linea or 'ncalls' in linea):
                print('  ' + linea.strip()[:170])
        s = io.StringIO()
        pstats.Stats(prof, stream=s).sort_stats('tottime').print_stats(12)
        print('  -- por tiempo propio --')
        for linea in s.getvalue().splitlines():
            if linea.strip() and ('/' in linea or '{' in linea or 'ncalls' in linea):
                print('  ' + linea.strip()[:170])
    except Exception as e:
        prof.disable()
        print('PERFIL   ERROR %r' % e)
    finally:
        env.cr.rollback()
        env.clear()


for modelo, rid in INFORMES:
    perfil(modelo, rid)
env.cr.rollback()
print('PERFIL deshecho (rollback): no queda nada escrito')

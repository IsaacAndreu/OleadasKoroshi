# -*- coding: utf-8 -*-
# PRUEBA l10n_es_aeat_mod347 13.0.2.1.3, SOLO código nuevo (24/11/2026). Se ejecuta con odoo shell y DESHACE todo.
# El código viejo tardaba ~7 s por cliente (8 min y sin acabar solo con enero 2024), así que no se repite:
# se calcula el 347 de 2024 entero (informe 7) con el código NUEVO y se compara con los registros que el informe ya
# tenía guardados (calculados antes con el código viejo; si los datos han cambiado desde entonces puede haber
# diferencias legítimas).
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell \
#   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 \
#   < 20261124_prueba_mod347_solo_nuevo_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
import sys
import time

from odoo import api

exec(open('/home/it_nath_group/20261124_prueba_mod347_filtro_ROLLBACK.py').read().split('\n\nNUEVAS = [')[0])
NUEVAS = [_account_move_line_domain, _asientos_excluidos_347, _clientes_validos_347, _create_partner_records,
          _create_cash_moves]


def foto(rep):
    return sorted(
        (r.partner_id.id, r.operation_key, round(r.amount, 2), round(r.cash_amount, 2))
        for r in rep.partner_record_ids
    )


for INFORME in (7, 8):
    base0 = env['l10n.es.aeat.mod347.report'].browse(INFORME)
    e = api.Environment(env.cr, base0.create_uid.id,
                        dict(env.context, allowed_company_ids=[base0.company_id.id]))
    rep = base0.with_env(e)
    clase = type(rep)
    originales = {f.__name__: clase.__dict__.get(f.__name__) for f in NUEVAS}
    try:
        antes = foto(rep)
        print('PRUEBA informe %s: %s, %s a %s, guardados %s registros (ultimo calculo %s)' % (
            rep.id, rep.company_id.name, rep.date_start, rep.date_end, len(antes), rep.calculation_date))
        sys.stdout.flush()
        for f in NUEVAS:
            setattr(clase, f.__name__, f)
        t = time.time()
        rep.calculate()
        despues = foto(rep)
        print('PRUEBA   codigo nuevo: %.1f s, %s registros' % (time.time() - t, len(despues)))
        if antes == despues:
            print('PRUEBA   IGUAL a lo guardado (cliente, clave, importe, efectivo)')
        else:
            sa, sb = set(antes), set(despues)
            print('PRUEBA   DISTINTO de lo guardado: %s solo antes, %s solo ahora' % (len(sa - sb), len(sb - sa)))
            for x in sorted(sa - sb)[:8]:
                print('    solo antes: %s' % (x,))
            for x in sorted(sb - sa)[:8]:
                print('    solo ahora: %s' % (x,))
        sys.stdout.flush()
    except Exception as ex:
        print('PRUEBA   ERROR %r' % ex)
    finally:
        env.cr.rollback()
        for nombre, f in originales.items():
            if f is None:
                if nombre in clase.__dict__:
                    delattr(clase, nombre)
            else:
                setattr(clase, nombre, f)
        env.clear()
print('PRUEBA deshecho (rollback): no queda nada escrito')

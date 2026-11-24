# -*- coding: utf-8 -*-
# PRUEBA l10n_es_aeat_mod347 13.0.2.1.3 (24/11/2026). Se ejecuta con odoo shell y DESHACE todo al acabar.
# 1) Calcula el mismo 347 (enero 2024, PRIME, como el usuario que hizo el informe 7) con el código ORIGINAL y con el
#    NUEVO (funciones de abajo, sacadas tal cual de odoo/modulos/l10n_es_aeat_mod347/models/mod347.py) y compara
#    clientes, claves, importes, asientos y cobros en efectivo.
# 2) Solo con el código NUEVO, calcula el 347 de 2024 entero (informe 7) para medir el tiempo.
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell #   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 #   < 20261124_prueba_mod347_filtro_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
import sys
import time
from odoo import _, api

INFORME_BASE = 7
DESDE, HASTA = '2024-01-01', '2024-01-31'

# ---- funciones NUEVAS (copiadas del módulo por script) ----
def _account_move_line_domain(self, taxes):
    """Return domain for searching move lines.

    :param: taxes: Taxes to look for in move lines.
    """
    # tuctuc v2.1.3: antes ("partner_id.not_in_mod347", "=", False) y ("move_id.not_in_mod347", "=", False).
    # Odoo 13 resuelve eso sacando TODOS los ids de res_partner (726.000) y de account_move (838.000) y
    # filtrando con IN (lista enorme), y lo repite por cada cliente (group["__domain"]).
    # Ahora: los asientos excluidos son pocos (48 el 24/11/2026) y se quitan con "not in"; los clientes se
    # filtran después de agrupar, solo entre los que aparecen (_clientes_validos_347). Mismo resultado.
    return [
        ("partner_id", "!=", False),
        ("move_id", "not in", self._asientos_excluidos_347()),
        ("date", ">=", self.date_start),
        ("date", "<=", self.date_end),
        "|",
        ("tax_ids", "in", taxes.ids),
        ("tax_line_id", "in", taxes.ids),
        ("parent_state", "=", "posted"),
    ]

def _asientos_excluidos_347(self):
    """Ids de los asientos marcados «No incluir en el 347» (con las reglas del usuario)."""
    return self.env["account.move"].search([("not_in_mod347", "=", True)]).ids

def _clientes_validos_347(self, partner_ids):
    """De estos clientes, los que cuentan para el 347.

    Es la misma búsqueda que hace Odoo 13 con ("partner_id.not_in_mod347", "=", False)
    (odoo/osv/expression.py, many2one: comodel.with_context(active_test=False).search(...), con las reglas
    del usuario), pero solo entre los clientes que salen en los grupos y no entre los 726.000.
    """
    return set(
        self.env["res.partner"]
        .with_context(active_test=False)
        .search([("id", "in", list(partner_ids)), ("not_in_mod347", "=", False)])
        .ids
    )

def _create_partner_records(self, key, map_ref, partner_record=None):
    partner_record_obj = self.env["l10n.es.aeat.mod347.partner_record"]
    partner_obj = self.env["res.partner"]
    map_line = self.env.ref(map_ref)
    taxes = self._get_taxes(map_line)
    domain = self._account_move_line_domain(taxes)
    if partner_record:
        domain += [("partner_id", "=", partner_record.partner_id.id)]
    groups = self.env["account.move.line"].read_group(
        domain, ["partner_id", "balance"], ["partner_id"],
    )
    validos = self._clientes_validos_347(g["partner_id"][0] for g in groups)
    filtered_groups = list(
        filter(
            lambda d: d["partner_id"][0] in validos
            and abs(d["balance"]) > self.operations_limit,
            groups,
        )
    )
    for group in filtered_groups:
        partner = partner_obj.browse(group["partner_id"][0])
        vals = {
            "report_id": self.id,
            "partner_id": partner.id,
            "representative_vat": "",
            "operation_key": key,
            "amount": (-1 if key == "B" else 1) * group["balance"],
        }
        vals.update(self._get_partner_347_identification(partner))
        move_groups = self.env["account.move.line"].read_group(
            group["__domain"], ["move_id", "balance"], ["move_id"],
        )
        vals["move_record_ids"] = [
            (
                0,
                0,
                {
                    "move_id": move_group["move_id"][0],
                    "amount": move_group["balance"],
                },
            )
            for move_group in move_groups
        ]
        if partner_record:
            vals["move_record_ids"][0:0] = [
                (2, x) for x in partner_record.move_record_ids.ids
            ]
            partner_record.write(vals)
        else:
            partner_record_obj.create(vals)

def _create_cash_moves(self):
    partner_obj = self.env["res.partner"]
    move_line_obj = self.env["account.move.line"]
    cash_journals = self.env["account.journal"].search([("type", "=", "cash")],)
    if not cash_journals:
        return
    domain = [
        ("account_id.internal_type", "=", "receivable"),
        ("journal_id", "in", cash_journals.ids),
        ("date", ">=", self.date_start),
        ("date", "<=", self.date_end),
        ("partner_id", "!=", False),
    ]
    cash_groups = move_line_obj.read_group(
        domain, ["partner_id", "balance"], ["partner_id"]
    )
    validos = self._clientes_validos_347(g["partner_id"][0] for g in cash_groups)
    cash_groups = [g for g in cash_groups if g["partner_id"][0] in validos]
    for cash_group in cash_groups:
        partner = partner_obj.browse(cash_group["partner_id"][0])
        partner_record_obj = self.env["l10n.es.aeat.mod347.partner_record"]
        amount = abs(cash_group["balance"])
        if amount > self.received_cash_limit:
            move_lines = move_line_obj.search(cash_group["__domain"])
            partner_record = partner_record_obj.search(
                [
                    ("partner_id", "=", partner.id),
                    ("operation_key", "=", "B"),
                    ("report_id", "=", self.id),
                ]
            )
            if partner_record:
                partner_record.write(
                    {
                        "cash_record_ids": [(6, 0, move_lines.ids)],
                        "cash_amount": amount,
                    }
                )
            else:
                vals = {
                    "report_id": self.id,
                    "partner_id": partner.id,
                    "representative_vat": "",
                    "operation_key": "B",
                    "amount": 0,
                    "cash_amount": amount,
                    "cash_record_ids": [(6, 0, move_lines.ids)],
                }
                vals.update(self._get_partner_347_identification(partner))
                partner_record_obj.create(vals)

NUEVAS = [_account_move_line_domain, _asientos_excluidos_347, _clientes_validos_347, _create_partner_records,
          _create_cash_moves]


def foto(rep):
    regs = []
    for r in rep.partner_record_ids:
        regs.append((
            r.partner_id.id, r.operation_key, round(r.amount, 2), round(r.cash_amount, 2),
            tuple(sorted((m.move_id.id, round(m.amount, 2)) for m in r.move_record_ids)),
            tuple(sorted(r.cash_record_ids.ids)),
        ))
    return sorted(regs)


def informe_nuevo(e, base, nombre):
    vals = base.copy_data()[0]
    for k in list(vals):
        if k.endswith('_ids'):
            vals.pop(k)
    for campo in ('year', 'period_type'):
        vals[campo] = base[campo]
    vals.update({'date_start': DESDE, 'date_end': HASTA, 'statement_type': 'N', 'state': 'draft', 'name': nombre})
    return e['l10n.es.aeat.mod347.report'].create(vals)


base0 = env['l10n.es.aeat.mod347.report'].browse(INFORME_BASE)
usuario = base0.create_uid
e = api.Environment(env.cr, usuario.id, dict(env.context, allowed_company_ids=[base0.company_id.id]))
base = base0.with_env(e)
Report = e['l10n.es.aeat.mod347.report']
clase = type(Report)
print('PRUEBA base %s: %s, usuario %s, prueba %s a %s' % (base.id, base.company_id.name, usuario.login, DESDE, HASTA))
print('PRUEBA excluidos: %s clientes, %s asientos' % (
    len(env['res.partner'].with_context(active_test=False).search([('not_in_mod347', '=', True)])),
    env['account.move'].search_count([('not_in_mod347', '=', True)])))
sys.stdout.flush()
originales = {f.__name__: clase.__dict__.get(f.__name__) for f in NUEVAS}
try:
    a = informe_nuevo(e, base, 'PRUEBA347A')
    t = time.time()
    a.calculate()
    t_viejo = time.time() - t
    foto_a = foto(a)
    print('PRUEBA original: %.1f s, %s registros' % (t_viejo, len(foto_a)))
    sys.stdout.flush()
    a.unlink()
    for f in NUEVAS:
        setattr(clase, f.__name__, f)
    b = informe_nuevo(e, base, 'PRUEBA347B')
    t = time.time()
    b.calculate()
    t_nuevo = time.time() - t
    foto_b = foto(b)
    print('PRUEBA nuevo:    %.1f s, %s registros' % (t_nuevo, len(foto_b)))
    if foto_a == foto_b:
        print('PRUEBA RESULTADO: IGUAL EN TODO (clientes, claves, importes, asientos y efectivo)')
    else:
        sa, sb = set(foto_a), set(foto_b)
        print('PRUEBA RESULTADO: DISTINTO: %s solo en original, %s solo en nuevo' % (len(sa - sb), len(sb - sa)))
        for x in list(sa - sb)[:5]:
            print('  solo original: %s' % (x[:4],))
        for x in list(sb - sa)[:5]:
            print('  solo nuevo:    %s' % (x[:4],))
    sys.stdout.flush()
    b.unlink()
    # 2) Año entero con el código nuevo
    t = time.time()
    base.calculate()
    print('PRUEBA 347 de 2024 entero con el codigo nuevo: %.1f s, %s registros' % (
        time.time() - t, len(base.partner_record_ids)))
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
    print('PRUEBA deshecho (rollback): no queda nada escrito')

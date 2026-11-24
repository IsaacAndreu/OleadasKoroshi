# -*- coding: utf-8 -*-
# PRUEBA l10n_es_aeat_mod347 13.0.2.1.3 (24/11/2026, v2: filtro de impuestos partido en dos y dos consultas por
# clave en vez de una por cliente). Se ejecuta con odoo shell y DESHACE todo al acabar.
# 1) El 347 de UNITED BRANDS 2026 (mismas fechas y usuario que el informe 8) con el código ORIGINAL y con el NUEVO
#    (funciones de abajo, sacadas tal cual de odoo/modulos/l10n_es_aeat_mod347/models/mod347.py): compara clientes,
#    claves, importes, asientos y efectivo.
# 2) Solo con el código NUEVO, el 347 de 2024 entero de PRIME (informe 7), para medir el tiempo.
#
# sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell #   -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 #   < 20261124_prueba_mod347_v2_ROLLBACK.py 2>&1 | grep -E '^(PRUEBA|  )'
import sys
import time
from odoo import _, api

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

def _dominios_347(self, taxes):
    """El dominio de _account_move_line_domain partido en dos mitades que no se solapan:
    1) apuntes de impuesto (tax_line_id en T);
    2) apuntes con impuesto (tax_ids en T) que no son de esos impuestos (tax_line_id fuera de T o vacío).
    La unión es exactamente "tax_ids en T OR tax_line_id en T"."""
    comun = [
        ("partner_id", "!=", False),
        ("move_id", "not in", self._asientos_excluidos_347()),
        ("date", ">=", self.date_start),
        ("date", "<=", self.date_end),
        ("parent_state", "=", "posted"),
    ]
    return [
        comun + [("tax_line_id", "in", taxes.ids)],
        comun
        + [
            ("tax_ids", "in", taxes.ids),
            "|",
            ("tax_line_id", "not in", taxes.ids),
            ("tax_line_id", "=", False),
        ],
    ]

def _saldos_cliente_asiento_347(self, dominios):
    """Suma de balance por cliente y asiento de varios dominios que no se solapan:
    {partner_id: {move_id: saldo}}. El saldo del cliente es la suma de sus asientos."""
    saldos = {}
    for dominio in dominios:
        for grupo in self.env["account.move.line"].read_group(
            dominio,
            ["partner_id", "move_id", "balance"],
            ["partner_id", "move_id"],
            lazy=False,
        ):
            if grupo["partner_id"] and grupo["move_id"]:
                asientos = saldos.setdefault(grupo["partner_id"][0], {})
                move_id = grupo["move_id"][0]
                asientos[move_id] = asientos.get(move_id, 0.0) + grupo["balance"]
    return saldos

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
    # tuctuc v2.1.3: el dominio de antes, con "tax_ids in T OR tax_line_id in T", hacía recorrer a
    # PostgreSQL todos los apuntes del periodo (1,68 M en el 347 de 2024 de PRIME: 14 min y sin acabar).
    # Se parte en dos mitades que no se solapan y se suman (mismo resultado).
    dominios = self._dominios_347(taxes)
    if partner_record:
        dominios = [
            d + [("partner_id", "=", partner_record.partner_id.id)] for d in dominios
        ]
    # Dos consultas en total (una por mitad), agrupadas por cliente y asiento, en vez de una por cliente.
    por_cliente = self._saldos_cliente_asiento_347(dominios)
    validos = self._clientes_validos_347(por_cliente)
    filtered_groups = []
    for partner_id, asientos in por_cliente.items():
        balance = sum(asientos.values())
        if partner_id in validos and abs(balance) > self.operations_limit:
            filtered_groups.append((partner_id, balance, asientos))
    for partner_id, balance, saldos_asiento in filtered_groups:
        partner = partner_obj.browse(partner_id)
        vals = {
            "report_id": self.id,
            "partner_id": partner.id,
            "representative_vat": "",
            "operation_key": key,
            "amount": (-1 if key == "B" else 1) * balance,
        }
        vals.update(self._get_partner_347_identification(partner))
        vals["move_record_ids"] = [
            (0, 0, {"move_id": move_id, "amount": amount})
            for move_id, amount in saldos_asiento.items()
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

NUEVAS = [_account_move_line_domain, _dominios_347, _saldos_cliente_asiento_347, _asientos_excluidos_347, _clientes_validos_347, _create_partner_records, _create_cash_moves]


def foto(rep):
    regs = []
    for r in rep.partner_record_ids:
        regs.append((
            r.partner_id.id, r.operation_key, round(r.amount, 2), round(r.cash_amount, 2),
            tuple(sorted((m.move_id.id, round(m.amount, 2)) for m in r.move_record_ids)),
            tuple(sorted(r.cash_record_ids.ids)),
        ))
    return sorted(regs)


def entorno(base0):
    return api.Environment(env.cr, base0.create_uid.id,
                           dict(env.context, allowed_company_ids=[base0.company_id.id]))


def informe_nuevo(e, base, nombre):
    vals = base.copy_data()[0]
    for k in list(vals):
        if k.endswith('_ids'):
            vals.pop(k)
    for campo in ('year', 'period_type', 'date_start', 'date_end'):
        vals[campo] = base[campo]
    vals.update({'statement_type': 'N', 'state': 'draft', 'name': nombre})
    return e['l10n.es.aeat.mod347.report'].create(vals)


Report = env['l10n.es.aeat.mod347.report']
clase = type(Report)
originales = {f.__name__: clase.__dict__.get(f.__name__) for f in NUEVAS}


def poner(nuevas):
    for f in NUEVAS:
        if nuevas:
            setattr(clase, f.__name__, f)
        elif originales[f.__name__] is None:
            if f.__name__ in clase.__dict__:
                delattr(clase, f.__name__)
        else:
            setattr(clase, f.__name__, originales[f.__name__])


try:
    base0 = Report.browse(8)
    e = entorno(base0)
    base = base0.with_env(e)
    print('PRUEBA 1) %s, %s a %s, usuario %s' % (base.company_id.name, base.date_start, base.date_end,
                                                base0.create_uid.login))
    sys.stdout.flush()
    poner(False)
    a = informe_nuevo(e, base, 'PRUEBA347A')
    t = time.time()
    a.calculate()
    t_viejo = time.time() - t
    foto_a = foto(a)
    print('PRUEBA   original: %.1f s, %s registros' % (t_viejo, len(foto_a)))
    sys.stdout.flush()
    a.unlink()
    poner(True)
    b = informe_nuevo(e, base, 'PRUEBA347B')
    t = time.time()
    b.calculate()
    t_nuevo = time.time() - t
    foto_b = foto(b)
    print('PRUEBA   nuevo:    %.1f s, %s registros' % (t_nuevo, len(foto_b)))
    if foto_a == foto_b:
        print('PRUEBA   RESULTADO: IGUAL EN TODO (clientes, claves, importes, asientos y efectivo)')
    else:
        sa, sb = set(foto_a), set(foto_b)
        print('PRUEBA   RESULTADO: DISTINTO: %s solo en original, %s solo en nuevo' % (len(sa - sb), len(sb - sa)))
        for x in sorted(sa - sb)[:5]:
            print('    solo original: %s' % (x[:4],))
        for x in sorted(sb - sa)[:5]:
            print('    solo nuevo:    %s' % (x[:4],))
    sys.stdout.flush()
    env.cr.rollback()
    env.clear()
    # 2) PRIME 2024 entero, solo nuevo
    base0 = Report.browse(7)
    e = entorno(base0)
    rep = base0.with_env(e)
    poner(True)
    t = time.time()
    rep.calculate()
    print('PRUEBA 2) %s %s a %s, codigo nuevo: %.1f s, %s registros' % (
        rep.company_id.name, rep.date_start, rep.date_end, time.time() - t, len(rep.partner_record_ids)))
except Exception as ex:
    print('PRUEBA ERROR %r' % ex)
finally:
    env.cr.rollback()
    poner(False)
    print('PRUEBA deshecho (rollback): no queda nada escrito')

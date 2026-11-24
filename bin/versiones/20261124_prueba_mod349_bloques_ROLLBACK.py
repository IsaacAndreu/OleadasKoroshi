# -*- coding: utf-8 -*-
# PRUEBA l10n_es_aeat_mod349 13.0.1.2.1 (24/11/2026). Se ejecuta con odoo shell y DESHACE todo al acabar.
# Calcula el mismo 349 con el código ORIGINAL (el instalado) y con el NUEVO (las funciones de abajo, sacadas
# tal cual de odoo/modulos/l10n_es_aeat_mod349/models/mod349.py por un script) en dos informes nuevos creados
# dentro de la transacción, y compara detalles, registros por cliente, rectificaciones y totales.
# Al final: env.cr.rollback(). No queda nada escrito en la base de datos.
#
#   sudo -u ubuntu /opt/tuctuc-erp/env/bin/python /opt/tuctuc-erp/odoo13/odoo-bin shell #       -c /opt/tuctuc-erp/tuctuc-erp.conf -d TUCTUC_PRODUCTION --no-http --max-cron-threads=0 #       < /tmp/prueba_mod349.py 2>&1 | grep -E '^(PRUEBA|  )'
#
# Por defecto usa los parámetros del informe 202 (MODA INTIMA, marzo 2026, ~3.000 líneas).
import math
import time
from odoo.fields import first
from odoo.tools import float_is_zero, float_round

INFORME_BASE = 202


def _create_349_details(self, move_lines):
    # Misma decisión que la versión original (línea a línea y en el mismo orden), pero los
    # valores se acumulan y se crean en bloque: mismos registros, mismo orden de ids.
    record_vals = []
    refund_vals = []
    tipos_por_asiento = {}
    for move_line in move_lines:
        if move_line.move_id.type in ("in_refund", "out_refund"):
            # Check for refunds if the origin invoice period is different
            # from the declaration
            origin_invoice = move_line.move_id.reversed_entry_id
            if origin_invoice:
                if (
                    origin_invoice.date < self.date_start
                    or origin_invoice.date > self.date_end
                ):
                    refund_vals.append(
                        self._prepare_349_refund_detail(move_line, tipos_por_asiento)
                    )
                    continue
        record_vals.append(
            self._prepare_349_record_detail(move_line, tipos_por_asiento)
        )
    self._crear_en_bloques("l10n.es.aeat.mod349.partner_record_detail", record_vals)
    self._crear_en_bloques("l10n.es.aeat.mod349.partner_refund_detail", refund_vals)

def _crear_en_bloques(self, modelo, lista_vals):
    modelo = self.env[modelo]
    for i in range(0, len(lista_vals), self.BLOQUE_DETALLES):
        modelo.create(lista_vals[i : i + self.BLOQUE_DETALLES])

def _tipos_cuenta_asiento(self, move, tipos_por_asiento):
    # El original lo calculaba en cada línea; una factura de 90 líneas lo repetía 90 veces.
    if move.id not in tipos_por_asiento:
        tipos_por_asiento[move.id] = move.mapped("line_ids.account_id.internal_type")
    return tipos_por_asiento[move.id]

def _prepare_349_record_detail(self, move_line, tipos_por_asiento=None):
    if tipos_por_asiento is None:
        tipos_por_asiento = {}
    types = self._tipos_cuenta_asiento(move_line.move_id, tipos_por_asiento)
    sign = 1 if "payable" in types else -1
    return {
        "report_id": self.id,
        "move_line_id": move_line.id,
        "amount_untaxed": sign * move_line.balance,
    }

def _prepare_349_refund_detail(self, move_line, tipos_por_asiento=None):
    if tipos_por_asiento is None:
        tipos_por_asiento = {}
    types = self._tipos_cuenta_asiento(move_line.move_id, tipos_por_asiento)
    sign = 1 if "receivable" in types else -1
    return {
        "report_id": self.id,
        "refund_line_id": move_line.id,
        "amount_untaxed": sign * move_line.balance,
    }

def _create_349_record_detail(self, move_line):
    return self.env["l10n.es.aeat.mod349.partner_record_detail"].create(
        self._prepare_349_record_detail(move_line)
    )

def _create_349_refund_detail(self, move_line):
    return self.env["l10n.es.aeat.mod349.partner_refund_detail"].create(
        self._prepare_349_refund_detail(move_line)
    )

def _create_349_invoice_records(self):
    """creates partner records in 349"""
    rec_obj = self.env["l10n.es.aeat.mod349.partner_record"]
    detail_obj = self.env["l10n.es.aeat.mod349.partner_record_detail"]
    data = {}
    for record_detail in self.partner_record_detail_ids:
        move_line = record_detail.move_line_id
        partner = move_line.partner_id
        op_key = move_line.l10n_es_aeat_349_operation_key
        partner_dict = data.setdefault(partner, {})
        # Lista de ids en vez de "recordset += registro" (que copia el conjunto entero en cada
        # vuelta: cuadrático con miles de líneas por cliente).
        op_key_dict = partner_dict.setdefault(op_key, {"record_details": []})
        op_key_dict["record_details"].append(record_detail.id)
    for partner in list(data.keys()):
        for op_key in list(data[partner].keys()):
            record_created = rec_obj.create(
                {
                    "report_id": self.id,
                    "partner_id": partner.id,
                    "partner_vat": partner.vat,
                    "operation_key": op_key,
                    "country_id": partner.country_id.id,
                }
            )
            # Un solo write por grupo en vez de uno por detalle: mismo resultado.
            detail_obj.browse(data[partner][op_key]["record_details"]).write(
                {"partner_record_id": record_created.id}
            )
    rounding = self.env.user.company_id.currency_id.rounding
    self.partner_record_ids.filtered(
        lambda r: float_is_zero(
            r.total_operation_amount, precision_rounding=rounding
        )
    ).unlink()
    return True

def _create_349_refund_records(self):
    """Creates restitution records in 349"""
    self.ensure_one()
    detail_obj = self.env["l10n.es.aeat.mod349.partner_record_detail"]
    obj = self.env["l10n.es.aeat.mod349.partner_refund"]
    refund_detail_obj = self.env["l10n.es.aeat.mod349.partner_refund_detail"]
    move_line_obj = self.env["account.move.line"]
    taxes = self._get_taxes()
    data = {}
    # This is for avoiding to find same lines several times
    visited_details = self.env["l10n.es.aeat.mod349.partner_record_detail"]
    visited_move_lines = self.env["account.move.line"]
    groups = {}
    for refund_detail in self.partner_refund_detail_ids:
        move_line = refund_detail.refund_line_id
        origin_invoice = move_line.move_id.reversed_entry_id
        # Lista de ids en vez de "recordset +=" (mismo orden): ver _create_349_invoice_records.
        groups.setdefault(origin_invoice, []).append(refund_detail.id)
    for origin_invoice in groups:
        refund_details = refund_detail_obj.browse(groups[origin_invoice])
        refund_detail = first(refund_details)
        move_line = refund_detail.refund_line_id
        partner = move_line.partner_id
        op_key = move_line.l10n_es_aeat_349_operation_key
        if not origin_invoice:
            # TODO: Instead continuing, generate an empty record and a msg
            continue
        # Fetch the latest presentation made for this move
        original_details = detail_obj.search(
            [
                ("move_line_id.move_id", "=", origin_invoice.id),
                ("partner_record_id.operation_key", "=", op_key),
                ("id", "not in", visited_details.ids),
            ],
            order="report_id desc",
        )
        # we add all of them to visited, as we don't want to repeat
        visited_details |= original_details
        if original_details:
            # There's at least one previous 349 declaration report
            report = original_details.mapped("report_id")[:1]
            original_details = original_details.filtered(
                lambda d: d.report_id == report
            )
            origin_amount = sum(original_details.mapped("amount_untaxed"))
            period_type = report.period_type
            year = str(report.year)
        else:
            # There's no previous 349 declaration report in Odoo
            original_amls = move_line_obj.search(
                [
                    ("tax_ids", "in", taxes.ids),
                    ("l10n_es_aeat_349_operation_key", "=", op_key),
                    ("move_id", "=", origin_invoice.id),
                ]
            )
            origin_amount = abs(
                sum((original_amls - visited_move_lines).mapped("balance"))
            )
            visited_move_lines |= original_amls
            # We have to guess the period type, as we don't have that info
            # through move lines. Inferred from:
            # * current record period scheme (monthly/quarterly/yearly)
            # * date of the move line
            if original_amls:
                original_move = original_amls[:1]
                year = str(original_move.date.year)
                month = "%02d" % (original_move.date.month)
            else:
                continue  # We can't find information to attach to
            if self.period_type == "0A":
                period_type = "0A"
            elif self.period_type in ("1T", "2T", "3T", "4T"):
                period_type = "%sT" % int(math.ceil(int(month) / 3.0))
            else:
                period_type = month
        key = (partner, op_key, period_type, year)
        key_vals = data.setdefault(
            key, {"original_amount": 0, "refund_details": refund_detail_obj}
        )
        key_vals["original_amount"] += origin_amount
        key_vals["refund_details"] += refund_details
    for key, key_vals in data.items():
        partner, op_key, period_type, year = key
        partner_refund = obj.create(
            {
                "report_id": self.id,
                "partner_id": partner.id,
                "partner_vat": partner.vat,
                "operation_key": op_key,
                "country_id": partner.country_id.id,
                "total_origin_amount": key_vals["original_amount"],
                "period_type": period_type,
                "year": year,
            }
        )
        key_vals["refund_details"].write({"refund_id": partner_refund.id})

NUEVAS = [_create_349_details, _crear_en_bloques, _tipos_cuenta_asiento, _prepare_349_record_detail, _prepare_349_refund_detail, _create_349_record_detail, _create_349_refund_detail, _create_349_invoice_records, _create_349_refund_records]


def foto(rep):
    """Todo lo que deja Calcular, en un formato comparable (sin ids propios del informe)."""
    det = [(d.move_line_id.id, round(d.amount_untaxed, 2), d.partner_record_id.partner_id.id,
            d.partner_record_id.operation_key) for d in rep.partner_record_detail_ids.sorted('id')]
    regs = sorted((r.partner_id.id, r.partner_vat or '', r.operation_key or '', r.country_id.id,
                   round(r.total_operation_amount, 2)) for r in rep.partner_record_ids)
    rdet = [(d.refund_line_id.id, round(d.amount_untaxed, 2), d.refund_id.partner_id.id)
            for d in rep.partner_refund_detail_ids.sorted('id')]
    rect = sorted((r.partner_id.id, r.operation_key or '', r.period_type or '', r.year,
                   round(r.total_origin_amount, 2), round(r.total_operation_amount, 2))
                  for r in rep.partner_refund_ids)
    tot = (rep.total_partner_records, round(rep.total_partner_records_amount, 2),
           rep.total_partner_refunds, round(rep.total_partner_refunds_amount, 2))
    return {'detalles': det, 'clientes': regs, 'detalles_rect': rdet, 'rectificaciones': rect,
            'totales': tot}


def informe_nuevo(base, nombre):
    vals = base.copy_data()[0]
    for k in list(vals):
        if k.endswith('_ids'):
            vals.pop(k)
    vals['statement_type'] = 'N'
    vals['state'] = 'draft'
    # Nombre propio: así no se gasta un número de la secuencia oficial del 349.
    vals['name'] = nombre
    return env['l10n.es.aeat.mod349.report'].create(vals)


Report = env['l10n.es.aeat.mod349.report']
clase = type(Report)
base = Report.browse(INFORME_BASE)
print('PRUEBA informe base %s: compania %s, %s a %s' % (base.id, base.company_id.name, base.date_start, base.date_end))
try:
    a = informe_nuevo(base, 'PRUEBA349A')
    t = time.time()
    a.calculate()
    t_viejo = time.time() - t
    foto_viejo = foto(a)
    # Las rectificaciones buscan detalles de OTROS informes 349: se borra A antes de calcular B
    # para que B vea lo mismo que vio A.
    a.unlink()
    originales = {f.__name__: clase.__dict__.get(f.__name__) for f in NUEVAS}
    clase.BLOQUE_DETALLES = 1000
    for f in NUEVAS:
        setattr(clase, f.__name__, f)
    try:
        b = informe_nuevo(base, 'PRUEBA349B')
        t = time.time()
        b.calculate()
        t_nuevo = time.time() - t
        foto_nuevo = foto(b)
    finally:
        for nombre, f in originales.items():
            if f is None:
                delattr(clase, nombre)
            else:
                setattr(clase, nombre, f)
    print('PRUEBA tiempo original %.1f s, nuevo %.1f s' % (t_viejo, t_nuevo))
    iguales = True
    for k in foto_viejo:
        ok = foto_viejo[k] == foto_nuevo[k]
        iguales = iguales and ok
        print('  %-16s original %7s  nuevo %7s  %s' % (
            k, len(foto_viejo[k]), len(foto_nuevo[k]), 'IGUAL' if ok else 'DISTINTO'))
    print('  totales original %s' % (foto_viejo['totales'],))
    print('  totales nuevo    %s' % (foto_nuevo['totales'],))
    print('PRUEBA RESULTADO: %s' % ('IGUAL EN TODO' if iguales else 'HAY DIFERENCIAS'))
finally:
    env.cr.rollback()
    print('PRUEBA deshecho (rollback): no queda nada escrito')

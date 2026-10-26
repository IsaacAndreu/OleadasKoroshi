# -*- coding: utf-8 -*-
from odoo import api, fields, models

PREFIJO = 'Delegación '            # etiqueta de contacto de la tienda: "Delegación BILBAO" -> BILBAO


def actualizar_delegacion(cr, partner_ids=None):
    """Pone en los albaranes la delegacion de la etiqueta de su contacto, con SQL (sin recalcular uno a uno).
    partner_ids: solo los albaranes de esos contactos; None: todos."""
    filtro = ''
    params = [PREFIJO, PREFIJO + '%']
    if partner_ids is not None:
        if not partner_ids:
            return
        filtro = ' AND p.partner_id IN %s'
        params.append(tuple(partner_ids))
    # Sin etiqueta de delegacion: vacio (por si se la han quitado)
    cr.execute("""
        UPDATE stock_picking p SET koroshi_delegacion = NULL
         WHERE p.koroshi_delegacion IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM res_partner_res_partner_category_rel r
                             JOIN res_partner_category c ON c.id = r.category_id
                            WHERE r.partner_id = p.partner_id AND c.name LIKE %s)""" + filtro,
               [PREFIJO + '%'] + params[2:])
    cr.execute("""
        UPDATE stock_picking p SET koroshi_delegacion = d.deleg
          FROM (SELECT r.partner_id, MIN(substr(c.name, length(%s) + 1)) AS deleg
                  FROM res_partner_res_partner_category_rel r
                  JOIN res_partner_category c ON c.id = r.category_id
                 WHERE c.name LIKE %s
                 GROUP BY r.partner_id) d
         WHERE p.partner_id = d.partner_id
           AND p.koroshi_delegacion IS DISTINCT FROM d.deleg""" + filtro, params)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    koroshi_delegacion = fields.Char('Delegación', index=True, readonly=True, copy=False,
                                     help='Delegación de transporte de la tienda (etiqueta "Delegación ..." del contacto)')

    def _koroshi_delegacion_de(self, partner):
        for c in partner.category_id:
            if (c.name or '').startswith(PREFIJO):
                return c.name[len(PREFIJO):]
        return False

    @api.model_create_multi
    def create(self, vals_list):
        Partner = self.env['res.partner']
        for vals in vals_list:
            if vals.get('partner_id') and 'koroshi_delegacion' not in vals:
                vals['koroshi_delegacion'] = self._koroshi_delegacion_de(Partner.browse(vals['partner_id']))
        return super().create(vals_list)

    def write(self, vals):
        if 'partner_id' in vals and 'koroshi_delegacion' not in vals:
            vals = dict(vals, koroshi_delegacion=self._koroshi_delegacion_de(
                self.env['res.partner'].browse(vals['partner_id'] or [])))
        return super().write(vals)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        res = super().write(vals)
        if 'category_id' in vals:
            # Cambio de etiquetas de la tienda: se actualizan sus albaranes
            self.env['stock.picking'].flush(['partner_id'])
            actualizar_delegacion(self.env.cr, self.ids)
            self.env['stock.picking'].invalidate_cache(['koroshi_delegacion'])
        return res

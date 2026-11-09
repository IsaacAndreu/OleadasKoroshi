# -*- coding: utf-8 -*-
# Crear muchos operarios de golpe: un nombre por linea -> empleado con codigo OP0001, OP0002...
# en "ID de credencial" y la etiqueta "Operario KOROSHI". No crea usuarios de Odoo.
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KoroshiCrearOperarios(models.TransientModel):
    _name = 'koroshi.crear.operarios'
    _description = 'KOROSHI Crear operarios'

    nombres = fields.Text('Nombres', required=True, help='Un nombre por linea')
    prefijo = fields.Char('Prefijo del codigo', required=True, default='OP')
    company_id = fields.Many2one('res.company', 'Empresa', required=True, default=lambda self: self.env.company)

    @api.model
    def _siguiente_numero(self, prefijo):
        Emp = self.env['hr.employee'].sudo().with_context(active_test=False)
        mayor = 0
        patron = re.compile(r'^%s(\d+)$' % re.escape(prefijo))
        for codigo in Emp.search([('barcode', '=like', prefijo + '%')]).mapped('barcode'):
            m = patron.match(codigo or '')
            if m and int(m.group(1)) > mayor:
                mayor = int(m.group(1))
        return mayor + 1

    def action_crear(self):
        self.ensure_one()
        nombres = [n.strip() for n in (self.nombres or '').splitlines() if n.strip()]
        if not nombres:
            raise UserError(_('Escribe al menos un nombre'))
        prefijo = (self.prefijo or 'OP').strip().upper()
        categoria = self.env.ref('koroshi_operarios.categoria_operario_koroshi')
        numero = self._siguiente_numero(prefijo)
        Emp = self.env['hr.employee'].sudo()
        creados = Emp.browse()
        for nombre in nombres:
            creados |= Emp.create({
                'name': nombre,
                'barcode': '%s%04d' % (prefijo, numero),
                'company_id': self.company_id.id,
                'category_ids': [(4, categoria.id)],
            })
            numero += 1
        return {
            'type': 'ir.actions.act_window',
            'name': _('Operarios creados (%d)') % len(creados),
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', creados.ids)],
            'target': 'current',
        }

# -*- coding: utf-8 -*-
from odoo import _, fields, models


class KoroshiS4tTraspasoRecuperar(models.TransientModel):
    _name = 'koroshi.s4t.traspaso.recuperar'
    _description = 'Recuperar traspasos S4T de un dia'

    tipo = fields.Selection([('devolucion', 'Devoluciones e-commerce'), ('correccion', 'Correcciones')],
                            string='Tipo', required=True, default='devolucion')
    fecha = fields.Date(string='Fecha del traspaso', required=True)

    def action_recuperar(self):
        self.ensure_one()
        Traspaso = self.env['koroshi.s4t.traspaso']
        nuevos = Traspaso.recuperar_por_fecha(self.tipo, fields.Date.to_string(self.fecha))
        Traspaso.search([('state', '=', 'nuevo')]).action_procesar()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Traspasos S4T'), 'sticky': False,
                       'message': _('%d traspasos nuevos guardados.') % nuevos},
        }

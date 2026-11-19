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
        creados = []
        nuevos = Traspaso.recuperar_por_fecha(self.tipo, fields.Date.to_string(self.fecha), creados)
        # v1.3: solo en modo real y solo los que se acaban de guardar (antes procesaba todos los 'nuevo')
        if Traspaso._modo() == 'real':
            Traspaso.browse(creados).action_procesar()
        # v1.1: Odoo 13 no tiene la accion display_notification: se abre la lista con el resultado en el titulo
        return {
            'type': 'ir.actions.act_window',
            'name': _('Traspasos S4T: %d nuevos guardados') % nuevos,
            'res_model': 'koroshi.s4t.traspaso',
            'view_mode': 'tree,form',
            'domain': [('tipo', '=', self.tipo)],
            'target': 'current',
        }

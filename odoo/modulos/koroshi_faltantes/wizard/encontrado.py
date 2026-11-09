# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Faltantes - asistente "Encontrado": devuelve las uds de FALTANT a la ubicacion que se elija.
# =============================================================================
from odoo import fields, models
from odoo.exceptions import UserError


class KoroshiFaltanteEncontrado(models.TransientModel):
    _name = 'koroshi.faltante.encontrado'
    _description = 'KOROSHI Faltante encontrado'

    faltante_ids = fields.Many2many('koroshi.faltante', string='Faltantes',
                                    default=lambda self: [(6, 0, self.env.context.get('active_ids', []))])
    ubicacion_id = fields.Many2one('stock.location', 'Devolver a', required=True,
                                   domain="[('usage', '=', 'internal')]",
                                   help='Ubicacion donde esta la pieza (normalmente su caja KO o el hueco)')

    def action_confirmar(self):
        self.ensure_one()
        if not self.faltante_ids:
            raise UserError('No hay faltantes seleccionados.')
        self.faltante_ids.marcar_encontrado(self.ubicacion_id)
        return {'type': 'ir.actions.act_window_close'}

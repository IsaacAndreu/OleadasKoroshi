# -*- coding: utf-8 -*-
from odoo import fields, models


class KoroshiContenedorMovimiento(models.Model):
    _name = 'koroshi.contenedor.movimiento'
    _description = 'KOROSHI: movimiento de contenedor entre ubicaciones'
    _order = 'id desc'

    accion = fields.Selection([('mover', 'Mover'), ('archivar', 'Archivar vacío')], 'Acción', default='mover',
                              required=True)
    contenedor = fields.Char('Contenedor', required=True, index=True)
    origen_id = fields.Many2one('stock.location', 'Origen (hueco)', ondelete='set null')
    destino_id = fields.Many2one('stock.location', 'Destino (hueco)', ondelete='set null')
    origen = fields.Char('Origen')
    destino = fields.Char('Destino')
    uds = fields.Float('Uds', digits=(16, 2))
    reservadas = fields.Float('Reservadas', digits=(16, 2))
    lineas = fields.Integer('Referencias')
    employee_id = fields.Many2one('hr.employee', 'Operario (tarjeta)', ondelete='set null', index=True)
    user_id = fields.Many2one('res.users', 'Usuario de Odoo', default=lambda s: s.env.uid)

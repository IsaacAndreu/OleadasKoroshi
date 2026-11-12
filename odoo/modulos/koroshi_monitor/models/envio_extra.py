# -*- coding: utf-8 -*-
"""OUT añadidas a mano al Excel de un día en Consulta de envíos.

A veces a oficina le falta en el Excel de un día un pedido u OUT (por ejemplo, una del día
anterior que se etiquetó tarde o sin adjunto). Aquí se guarda «esta OUT va también en el
Excel de este día». Se puede quitar si se añadió por error.
"""
from odoo import fields, models


class KoroshiEnvioExtra(models.Model):
    _name = 'koroshi.envio.extra'
    _description = 'OUT añadida a mano al Excel de envíos de un día'
    _order = 'dia desc, id desc'
    _rec_name = 'picking_id'

    dia = fields.Date(string='Día del Excel', required=True, index=True)
    apartado = fields.Selection([('tiendas', 'Tiendas'), ('web', 'Web')], string='Apartado',
                                required=True, default='tiendas', index=True)
    transportista = fields.Selection([('xpo', 'XPO SAS'), ('gls', 'GLS'), ('seur', 'SEUR'),
                                      ('todos', 'Todos (sin transportista)')],
                                     string='Excel de', required=True, index=True)
    picking_id = fields.Many2one('stock.picking', string='OUT', required=True, ondelete='cascade', index=True)
    pedido = fields.Char(string='Pedido')
    escrito = fields.Char(string='Texto escrito')
    company_id = fields.Many2one('res.company', string='Compañía', required=True, index=True,
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('koroshi_envio_extra_unico', 'unique(picking_id, dia, apartado, transportista)',
         'Esta OUT ya está añadida a ese día.'),
    ]

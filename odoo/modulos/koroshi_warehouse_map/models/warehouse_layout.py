# -*- coding: utf-8 -*-
from odoo import fields, models


class KoroshiLayout(models.Model):
    _name = 'koroshi.layout'
    _description = 'Plano editable de almacén KOROSHI'
    _order = 'name, id'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True, default='NAU-2')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.user.company_id, index=True,
    )
    warehouse_id = fields.Many2one('stock.warehouse', string='Almacén')
    source_version = fields.Char(string='Versión del plano', default='NAU-2 · 2026-10-29')
    map_json = fields.Text(
        string='Datos del mapa',
        help='JSON del estado editable del plano. Se mantiene separado del plano base.',
    )
    notes = fields.Text(string='Notas')
    element_ids = fields.One2many(
        'koroshi.layout.element', 'layout_id', string='Elementos del plano',
    )

    _sql_constraints = [
        (
            'koroshi_layout_code_company_uniq',
            'unique(code, company_id)',
            'Ya existe un plano con este código en la compañía.',
        ),
    ]


class KoroshiLayoutElement(models.Model):
    _name = 'koroshi.layout.element'
    _description = 'Elemento del plano KOROSHI'
    _order = 'sequence, id'

    layout_id = fields.Many2one(
        'koroshi.layout', string='Plano', required=True,
        ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Nombre', required=True)
    element_type = fields.Selection([
        ('zone', 'Zona'),
        ('lineal', 'Lineal'),
        ('aisle', 'Pasillo'),
        ('dock', 'Muelle'),
        ('note', 'Anotación'),
        ('other', 'Otro'),
    ], string='Tipo', required=True, default='zone')
    external_ref = fields.Char(string='Referencia externa')
    x = fields.Float(string='X')
    y = fields.Float(string='Y')
    width = fields.Float(string='Ancho')
    height = fields.Float(string='Alto')
    rotation = fields.Float(string='Giro')
    visible = fields.Boolean(default=True)
    payload_json = fields.Text(string='Propiedades JSON')
    company_id = fields.Many2one(
        related='layout_id.company_id', string='Compañía', store=True,
    )

# -*- coding: utf-8 -*-
from odoo import fields, models


class KoroshiPickSession(models.Model):
    _name = 'koroshi.pick.session'
    _description = 'Sesión operativa de picking KOROSHI'
    _order = 'last_scan_at desc, id desc'

    name = fields.Char(string='Referencia', required=True, default='Nueva sesión')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.user.company_id, index=True,
    )
    pda_code = fields.Char(string='PDA')
    operator_name = fields.Char(string='Persona')
    user_id = fields.Many2one('res.users', string='Usuario Odoo')
    picking_id = fields.Many2one('stock.picking', string='OUT')
    out_reference = fields.Char(string='OUT visible')
    state = fields.Selection([
        ('draft', 'Sin empezar'),
        ('picking', 'En picking'),
        ('paused', 'En pausa'),
        ('done', 'Finalizado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', required=True, index=True)
    started_at = fields.Datetime(string='Inicio')
    last_scan_at = fields.Datetime(string='Último escaneo', index=True)
    finished_at = fields.Datetime(string='Fin')
    last_location = fields.Char(string='Última ubicación')
    last_line = fields.Char(string='Último lineal')
    last_position = fields.Char(string='Última posición')
    last_level = fields.Selection([
        ('c1', 'C1'), ('c2', 'C2'), ('c3', 'C3'), ('c4', 'C4'),
    ], string='Nivel')
    progress = fields.Float(string='Progreso (%)', digits=(16, 2))
    pick_count = fields.Integer(string='Picks')
    source = fields.Selection([
        ('pda', 'PDA'),
        ('odoo', 'Odoo'),
        ('import', 'Importación'),
        ('demo', 'Demo'),
    ], string='Fuente', default='pda')
    payload_json = fields.Text(string='Datos de origen JSON')
    note = fields.Text(string='Notas')
    event_ids = fields.One2many(
        'koroshi.pick.event', 'session_id', string='Eventos',
    )


class KoroshiPickEvent(models.Model):
    _name = 'koroshi.pick.event'
    _description = 'Evento de picking KOROSHI'
    _order = 'occurred_at desc, id desc'

    session_id = fields.Many2one(
        'koroshi.pick.session', string='Sesión', required=True,
        ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        related='session_id.company_id', string='Compañía', store=True,
    )
    picking_id = fields.Many2one('stock.picking', string='OUT')
    user_id = fields.Many2one('res.users', string='Usuario Odoo')
    event_type = fields.Selection([
        ('start', 'Inicio OUT'),
        ('pick', 'Pick confirmado'),
        ('pause', 'Pausa'),
        ('resume', 'Reanudación'),
        ('finish', 'OUT finalizado'),
        ('scan', 'Escaneo'),
    ], string='Tipo', required=True, default='scan')
    occurred_at = fields.Datetime(string='Fecha y hora', required=True, index=True,
                                  default=fields.Datetime.now)
    location = fields.Char(string='Ubicación')
    line = fields.Char(string='Lineal')
    position = fields.Char(string='Posición')
    level = fields.Selection([
        ('c1', 'C1'), ('c2', 'C2'), ('c3', 'C3'), ('c4', 'C4'),
    ], string='Nivel')
    product_id = fields.Many2one('product.product', string='Producto')
    quantity = fields.Float(string='Cantidad')
    source_ref = fields.Char(string='Referencia de origen')
    payload_json = fields.Text(string='Datos JSON')

# -*- coding: utf-8 -*-
"""v1.45.0 (25/11/2026): etiquetas CJ que un jefe ha quitado de «Etiquetas CJ sin leer» con «La he tirado».

Tabla propia del Monitor (nada en tablas compartidas). Solo guarda que esa CJ no hay que buscarla: quién y cuándo.
No toca la etiqueta (zebra.label), ni la OUT, ni las cajas.
"""
from odoo import fields, models


class KoroshiMonitorCjDescartada(models.Model):
    _name = 'koroshi.monitor.cj.descartada'
    _description = 'Etiqueta CJ de zona sin leer quitada a mano (la he tirado)'
    _order = 'id desc'

    name = fields.Char(string='Matrícula CJ', required=True, index=True, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='OUT', readonly=True, ondelete='set null')
    usuario_id = fields.Many2one('res.users', string='Quitada por', readonly=True,
                                 default=lambda self: self.env.user)

    _sql_constraints = [
        ('koroshi_monitor_cj_descartada_name', 'unique(name)', 'Esa etiqueta ya está quitada.'),
    ]

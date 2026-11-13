# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades - lista de actividades que se eligen en el portátil.
# Se cambian desde Configuración (nombre, orden, color, archivar) sin tocar código.
# =============================================================================
from odoo import fields, models


class KoroshiActividad(models.Model):
    _name = 'koroshi.actividad'
    _description = 'KOROSHI Actividad (manipulaciones)'
    _order = 'sequence, id'

    name = fields.Char('Actividad', required=True, translate=False)
    sequence = fields.Integer('Orden', default=10)
    color = fields.Char('Color', default='#0b4f9c', help='Color del botón en el portátil (#rrggbb)')
    active = fields.Boolean('Activa', default=True)
    company_id = fields.Many2one('res.company', 'Empresa', default=lambda self: self.env.company)
    nota = fields.Char('Qué incluye', help='Texto pequeño debajo del nombre en el botón (opcional)')

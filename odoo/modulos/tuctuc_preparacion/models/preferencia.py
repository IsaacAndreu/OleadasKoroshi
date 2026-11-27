# -*- coding: utf-8 -*-
# v3.21: el color de la franja de la ubicación que ha elegido cada operario (menú ☰ > Color de la ubicación).
# Tabla propia: no se añade nada a hr.employee. Sin fila = el color por defecto (F, amarilla grande).
from odoo import api, fields, models

COLORES = [('a', 'A · Negra'), ('b', 'B · Blanca con borde'), ('c', 'C · Amarilla'), ('d', 'D · Azul oscuro'),
           ('e', 'E · En casillas'), ('f', 'F · Amarilla grande')]
COLOR_DEFECTO = 'f'


class Preferencia(models.Model):
    _name = 'tuctuc.preparacion.preferencia'
    _description = 'TUCTUC Preparación: preferencias del operario en la PDA'

    employee_id = fields.Many2one('hr.employee', 'Operario', required=True, index=True, ondelete='cascade')
    color = fields.Selection(COLORES, 'Color de la ubicación', required=True, default=COLOR_DEFECTO)

    _sql_constraints = [('employee_uniq', 'unique(employee_id)', 'Ya hay preferencias para ese operario.')]

    @api.model
    def color_de(self, employee):
        if not employee:
            return COLOR_DEFECTO
        p = self.sudo().search([('employee_id', '=', employee.id)], limit=1)
        return p.color if p else COLOR_DEFECTO

    @api.model
    def poner_color(self, employee, color):
        if color not in dict(COLORES):
            color = COLOR_DEFECTO
        if not employee:
            return color
        p = self.sudo().search([('employee_id', '=', employee.id)], limit=1)
        if p:
            p.color = color
        else:
            self.sudo().create({'employee_id': employee.id, 'color': color})
        return color

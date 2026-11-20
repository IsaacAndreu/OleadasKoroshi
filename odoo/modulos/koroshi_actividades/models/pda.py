# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades v1.6.0 - entrada única de la PDA: quién ve «Gestión» y qué hay dentro.
# Diseño: bin/versiones/diseno-pda-entrada-unica_2026-11-20_v2.md (Isaac 20/11: Gestión por la tarjeta).
#
# En la PDA todos entran con el mismo usuario («Almacén Nath»), así que el jefe se reconoce por su tarjeta:
#   koroshi.pda.jefe    = operarios que ven «Gestión» al pasar su tarjeta.
#   koroshi.pda.enlace  = botones de «Gestión» (Monitor, Tablero, Integración S4T...): una acción que ya existe.
# Ojo: la pantalla se abre con el usuario de la PDA. Lo que se ve dentro depende de sus permisos, no del jefe.
# Tablas propias; nada en hr.employee ni en stock.*.
# =============================================================================
from odoo import api, fields, models

from .actividad import accion_de


class KoroshiPdaJefe(models.Model):
    _name = 'koroshi.pda.jefe'
    _description = 'KOROSHI PDA: operario que ve «Gestión»'
    _order = 'employee_id'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', 'Operario', required=True, index=True, ondelete='cascade',
                                  help='Al pasar su tarjeta en el Inicio de la PDA le sale «Gestión».')
    company_id = fields.Many2one('res.company', 'Empresa', default=lambda self: self.env.company)

    _sql_constraints = [
        ('employee_unico', 'unique(employee_id)', 'Este operario ya está en la lista de jefes.'),
    ]

    @api.model
    def es_jefe(self, employee):
        return bool(employee and self.sudo().search_count([('employee_id', '=', employee.id)]))


class KoroshiPdaEnlace(models.Model):
    _name = 'koroshi.pda.enlace'
    _description = 'KOROSHI PDA: botón de «Gestión»'
    _order = 'sequence, id'

    name = fields.Char('Botón', required=True)
    sequence = fields.Integer('Orden', default=10)
    abre = fields.Char('Abre', required=True,
                       help='Id externo de la acción (p. ej. koroshi_monitor.action_koroshi_monitor) o su número. '
                            'Si no existe, el botón no sale.')
    nota = fields.Char('Qué es')
    active = fields.Boolean('Activo', default=True)

    def accion_abre(self):
        self.ensure_one()
        return accion_de(self.env, self.abre)

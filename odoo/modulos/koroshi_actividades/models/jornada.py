# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Actividades - jornada por persona y día (vista SQL, solo lectura).
# Entrada = inicio del primer tramo; salida = fin del último (vacío si sigue trabajando);
# horas trabajadas = suma de los tramos; pausa = de la entrada a la salida menos lo trabajado.
# =============================================================================
from odoo import fields, models, tools


class KoroshiActividadJornada(models.Model):
    _name = 'koroshi.actividad.jornada'
    _description = 'KOROSHI Actividades: jornada por persona y día'
    _auto = False
    _order = 'dia desc, employee_id'

    employee_id = fields.Many2one('hr.employee', 'Persona', readonly=True)
    company_id = fields.Many2one('res.company', 'Empresa', readonly=True)
    dia = fields.Date('Día', readonly=True)
    entrada = fields.Datetime('Entrada', readonly=True)
    salida = fields.Datetime('Salida', readonly=True)
    horas = fields.Float('Horas trabajadas', readonly=True, digits=(16, 2), group_operator='sum')
    horas_pausa = fields.Float('Horas en pausa', readonly=True, digits=(16, 2), group_operator='sum')
    tramos = fields.Integer('Tramos', readonly=True, group_operator='sum')
    actividades = fields.Integer('Actividades distintas', readonly=True, group_operator='max')
    abierta = fields.Boolean('Sigue trabajando', readonly=True)
    automatica = fields.Boolean('Cerrada o pausada sola', readonly=True,
                                help='Algún tramo lo cerró el sistema a la hora de la comida o del cierre: '
                                     'se le olvidó pausar o acabar.')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(r.id) AS id,
                    r.employee_id,
                    MIN(r.company_id) AS company_id,
                    r.dia,
                    MIN(r.inicio) AS entrada,
                    CASE WHEN BOOL_OR(r.estado = 'curso') THEN NULL ELSE MAX(r.fin) END AS salida,
                    SUM(r.minutos) / 60.0 AS horas,
                    CASE WHEN BOOL_OR(r.estado = 'curso') THEN 0
                         ELSE GREATEST(0, EXTRACT(EPOCH FROM (MAX(r.fin) - MIN(r.inicio))) / 3600.0
                                          - SUM(r.minutos) / 60.0) END AS horas_pausa,
                    COUNT(*) AS tramos,
                    COUNT(DISTINCT r.actividad_id) AS actividades,
                    BOOL_OR(r.estado = 'curso') AS abierta,
                    BOOL_OR(r.motivo_fin IN ('pausa_auto', 'fin_auto')) AS automatica
                FROM koroshi_actividad_registro r
                GROUP BY r.employee_id, r.dia
            )
        """ % self._table)

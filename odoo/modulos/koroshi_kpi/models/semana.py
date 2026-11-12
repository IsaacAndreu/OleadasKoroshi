# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI KPI v1.5 - Comparativa de semanas: cada dia de ESTA semana (lunes a domingo, hora de Madrid)
# contra el mismo dia de la semana ANTERIOR (lunes con lunes, martes con martes...).
#
# Vista SQL de solo lectura (no guarda nada): se calcula cada vez que se abre la lista.
#   Uds y cajas = ficha del dia completo (koroshi.kpi.dia con metodo 'mixto')
#   u/h         = uds / horas-persona de picking de esa ficha (hp_picking: lo apuntado a mano o, si no,
#                 lo estimado por las cajas). Sin horas de picking = vacio.
#   Delta %     = (u/h esta - u/h pasada) / u/h pasada x 100 (solo si los dos dias tienen u/h)
#   Faltas      = suma de 'Uds que faltan' de koroshi.kpi.falta de ese dia (todos los motivos)
# Fila 'Total (lunes a hoy)': suma de los dias de lunes al dia de hoy en las dos semanas, para comparar
# lo mismo; su u/h = uds de los dias con horas / horas-persona de picking de esos dias.
# Dias sin ficha ni faltas = celdas vacias.
# =============================================================================
from odoo import fields, models, tools

DIAS = [('1', 'Lunes'), ('2', 'Martes'), ('3', 'Miércoles'), ('4', 'Jueves'), ('5', 'Viernes'),
        ('6', 'Sábado'), ('7', 'Domingo'), ('8', 'Total (lunes a hoy)')]


class KoroshiKpiSemana(models.Model):
    _name = 'koroshi.kpi.semana'
    _description = 'KOROSHI KPI - comparativa esta semana / semana pasada'
    _auto = False
    _order = 'orden'

    orden = fields.Integer('Orden', readonly=True)
    dia = fields.Selection(DIAS, 'Día', readonly=True)
    es_total = fields.Boolean('Fila de total', readonly=True)
    fecha_esta = fields.Date('Fecha esta sem.', readonly=True)
    fecha_pasada = fields.Date('Fecha sem. pasada', readonly=True)
    hay_esta = fields.Boolean('Hay datos esta semana', readonly=True)
    hay_pasada = fields.Boolean('Hay datos semana pasada', readonly=True)
    uds_esta = fields.Float('Uds esta sem.', readonly=True, digits=(16, 0))
    uds_pasada = fields.Float('Uds sem. pasada', readonly=True, digits=(16, 0))
    hp_esta = fields.Float('H-p picking esta', readonly=True, digits=(16, 1))
    hp_pasada = fields.Float('H-p picking pasada', readonly=True, digits=(16, 1))
    uh_esta = fields.Float('u/h esta', readonly=True, digits=(16, 0),
                           help='Uds / horas-persona de picking de la ficha del día completo')
    uh_pasada = fields.Float('u/h pasada', readonly=True, digits=(16, 0),
                             help='Uds / horas-persona de picking de la ficha del día completo')
    delta_uh = fields.Float('Δ% u/h', readonly=True, digits=(16, 1),
                            help='(u/h esta - u/h pasada) / u/h pasada x 100')
    faltas_esta = fields.Float('Faltas (uds) esta', readonly=True, digits=(16, 0))
    faltas_pasada = fields.Float('Faltas (uds) pasada', readonly=True, digits=(16, 0))
    cajas_esta = fields.Integer('Cajas esta', readonly=True)
    cajas_pasada = fields.Integer('Cajas pasada', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
            WITH hoy AS (
                SELECT (now() AT TIME ZONE 'Europe/Madrid')::date AS hoy,
                       date_trunc('week', (now() AT TIME ZONE 'Europe/Madrid'))::date AS lunes
            ), dias AS (
                SELECT g AS n, (hoy.lunes + (g - 1))::date AS f_esta, (hoy.lunes + (g - 8))::date AS f_pasada,
                       (hoy.lunes + (g - 1))::date <= hoy.hoy AS hasta_hoy
                FROM hoy, generate_series(1, 7) AS g
            ), kpi AS (
                SELECT fecha, uds::float8 AS uds, cajas, hp_picking::float8 AS hp
                FROM koroshi_kpi_dia WHERE metodo = 'mixto'
            ), fal AS (
                SELECT fecha, SUM(faltan)::float8 AS faltan
                FROM koroshi_kpi_falta WHERE faltan > 0 GROUP BY fecha
            ), filas AS (
                SELECT d.n, d.f_esta, d.f_pasada, d.hasta_hoy,
                       (ke.fecha IS NOT NULL OR fe.fecha IS NOT NULL) AS hay_esta,
                       (kp.fecha IS NOT NULL OR fp.fecha IS NOT NULL) AS hay_pasada,
                       ke.uds AS uds_esta, kp.uds AS uds_pasada,
                       ke.hp AS hp_esta, kp.hp AS hp_pasada,
                       CASE WHEN ke.hp > 0 THEN ke.uds END AS uds_h_esta,
                       CASE WHEN kp.hp > 0 THEN kp.uds END AS uds_h_pasada,
                       CASE WHEN ke.fecha IS NOT NULL OR fe.fecha IS NOT NULL
                            THEN COALESCE(fe.faltan, 0) END AS faltas_esta,
                       CASE WHEN kp.fecha IS NOT NULL OR fp.fecha IS NOT NULL
                            THEN COALESCE(fp.faltan, 0) END AS faltas_pasada,
                       ke.cajas AS cajas_esta, kp.cajas AS cajas_pasada
                FROM dias d
                LEFT JOIN kpi ke ON ke.fecha = d.f_esta
                LEFT JOIN kpi kp ON kp.fecha = d.f_pasada
                LEFT JOIN fal fe ON fe.fecha = d.f_esta
                LEFT JOIN fal fp ON fp.fecha = d.f_pasada
            ), todo AS (
                SELECT n, f_esta, f_pasada, hay_esta, hay_pasada, uds_esta, uds_pasada, hp_esta, hp_pasada,
                       uds_h_esta, uds_h_pasada, faltas_esta, faltas_pasada, cajas_esta, cajas_pasada
                FROM filas
                UNION ALL
                SELECT 8, NULL::date, NULL::date, TRUE, TRUE,
                       SUM(uds_esta), SUM(uds_pasada),
                       SUM(CASE WHEN hp_esta > 0 THEN hp_esta END), SUM(CASE WHEN hp_pasada > 0 THEN hp_pasada END),
                       SUM(uds_h_esta), SUM(uds_h_pasada),
                       SUM(faltas_esta), SUM(faltas_pasada),
                       SUM(cajas_esta)::int, SUM(cajas_pasada)::int
                FROM filas WHERE hasta_hoy
            ), uh AS (
                SELECT t.*,
                       CASE WHEN hp_esta > 0 THEN uds_h_esta / hp_esta END AS uh_esta,
                       CASE WHEN hp_pasada > 0 THEN uds_h_pasada / hp_pasada END AS uh_pasada
                FROM todo t
            )
            SELECT n AS id, n AS orden, n::varchar AS dia, n = 8 AS es_total,
                   f_esta AS fecha_esta, f_pasada AS fecha_pasada, hay_esta, hay_pasada,
                   uds_esta, uds_pasada, hp_esta, hp_pasada, uh_esta, uh_pasada,
                   CASE WHEN uh_esta > 0 AND uh_pasada > 0 THEN (uh_esta - uh_pasada) / uh_pasada * 100.0 END
                       AS delta_uh,
                   faltas_esta, faltas_pasada, cajas_esta, cajas_pasada
            FROM uh
            )""" % self._table)

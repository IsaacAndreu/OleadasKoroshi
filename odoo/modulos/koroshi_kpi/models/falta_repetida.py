# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI KPI v1.5 - Faltas repetidas: articulos que dan falta (koroshi.kpi.falta con faltan > 0) en N o
# mas dias laborables SEGUIDOS. N = parametro 'koroshi_kpi.dias_falta_repetida' (por defecto 3).
#
# Dias seguidos = dias consecutivos en los que hubo faltas de cualquier articulo (asi se saltan fines de
# semana y festivos sin actividad). Una fila por articulo y racha de dias seguidos.
# Ubicacion habitual = la ubicacion interna de la empresa 8 con mas stock del articulo (stock.quant).
#
# Es una PROPUESTA para una ronda de revision: vista SQL de solo lectura, no crea INT, rondas ni movimientos.
# =============================================================================
from odoo import fields, models, tools

from .kpi import COMPANY_ID

DIAS_DEFECTO = 3


class KoroshiKpiFaltaRepetida(models.Model):
    _name = 'koroshi.kpi.falta.repetida'
    _description = 'KOROSHI faltas repetidas (dias seguidos)'
    _auto = False
    _order = 'ultimo_dia desc, dias desc, faltan desc'

    product_id = fields.Many2one('product.product', 'Artículo', readonly=True)
    referencia = fields.Char('Referencia', readonly=True)
    dias = fields.Integer('Días seguidos', readonly=True)
    primer_dia = fields.Date('Primer día', readonly=True)
    ultimo_dia = fields.Date('Último día', readonly=True)
    sigue = fields.Boolean('Sigue dando falta', readonly=True,
                           help='La racha llega hasta el último día con faltas registradas')
    faltan = fields.Float('Uds que faltan (total)', readonly=True, digits=(16, 0))
    n_outs = fields.Integer('OUT afectadas', readonly=True)
    outs = fields.Char('Nº OUT', readonly=True)
    ubicacion_id = fields.Many2one('stock.location', 'Ubicación habitual', readonly=True,
                                   help='Ubicación interna con más stock del artículo ahora mismo')
    stock_ubicacion = fields.Float('Stock en esa ubicación', readonly=True, digits=(16, 0))
    stock_interno = fields.Float('Stock interno total', readonly=True, digits=(16, 0))

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %(tabla)s AS (
            WITH param AS (
                SELECT COALESCE((SELECT CASE WHEN TRIM(value) ~ '^[0-9]+$' THEN TRIM(value)::int END
                                 FROM ir_config_parameter WHERE key = 'koroshi_kpi.dias_falta_repetida'),
                                %(defecto)s) AS n
            ), activos AS (
                SELECT fecha, ROW_NUMBER() OVER (ORDER BY fecha) AS pos
                FROM (SELECT DISTINCT fecha FROM koroshi_kpi_falta WHERE faltan > 0) f
            ), prod_dia AS (
                SELECT DISTINCT product_id, fecha FROM koroshi_kpi_falta
                WHERE faltan > 0 AND product_id IS NOT NULL
            ), grupos AS (
                SELECT pd.product_id, pd.fecha,
                       a.pos - ROW_NUMBER() OVER (PARTITION BY pd.product_id ORDER BY pd.fecha) AS grupo
                FROM prod_dia pd JOIN activos a ON a.fecha = pd.fecha
            ), rachas AS (
                SELECT product_id, grupo, COUNT(*) AS dias, MIN(fecha) AS primer_dia, MAX(fecha) AS ultimo_dia
                FROM grupos GROUP BY product_id, grupo
                HAVING COUNT(*) >= (SELECT n FROM param)
            ), totales AS (
                SELECT r.product_id, r.grupo, SUM(f.faltan) AS faltan,
                       COUNT(DISTINCT f.picking_id) AS n_outs,
                       STRING_AGG(DISTINCT f.out, ', ') AS outs,
                       MAX(f.referencia) AS referencia
                FROM rachas r
                JOIN koroshi_kpi_falta f ON f.product_id = r.product_id AND f.faltan > 0
                     AND f.fecha BETWEEN r.primer_dia AND r.ultimo_dia
                GROUP BY r.product_id, r.grupo
            ), stock AS (
                SELECT q.product_id, SUM(q.quantity) AS total
                FROM stock_quant q JOIN stock_location l ON l.id = q.location_id
                WHERE l.usage = 'internal' AND q.company_id = %(empresa)s AND q.quantity > 0
                  AND q.product_id IN (SELECT product_id FROM rachas)
                GROUP BY q.product_id
            ), mejor AS (
                SELECT DISTINCT ON (q.product_id) q.product_id, q.location_id, q.quantity
                FROM stock_quant q JOIN stock_location l ON l.id = q.location_id
                WHERE l.usage = 'internal' AND q.company_id = %(empresa)s AND q.quantity > 0
                  AND q.product_id IN (SELECT product_id FROM rachas)
                ORDER BY q.product_id, q.quantity DESC, q.location_id
            )
            SELECT ROW_NUMBER() OVER (ORDER BY r.product_id, r.primer_dia) AS id,
                   r.product_id, t.referencia, r.dias::int AS dias, r.primer_dia, r.ultimo_dia,
                   r.ultimo_dia = (SELECT MAX(fecha) FROM activos) AS sigue,
                   t.faltan::float8 AS faltan, t.n_outs::int AS n_outs, t.outs,
                   m.location_id AS ubicacion_id, m.quantity::float8 AS stock_ubicacion,
                   COALESCE(s.total, 0)::float8 AS stock_interno
            FROM rachas r
            JOIN totales t ON t.product_id = r.product_id AND t.grupo = r.grupo
            LEFT JOIN mejor m ON m.product_id = r.product_id
            LEFT JOIN stock s ON s.product_id = r.product_id
            )""" % {'tabla': self._table, 'defecto': DIAS_DEFECTO, 'empresa': COMPANY_ID})

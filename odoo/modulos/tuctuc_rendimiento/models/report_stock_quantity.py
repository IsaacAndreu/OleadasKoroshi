# -*- coding: utf-8 -*-
from odoo import models, tools

# Misma vista que koroshi_rendiment 1.0.0 (nath). Comprobado el 23/11/2026 en tuctuc: el cuerpo del CTE de
# /opt/tuctuc-erp/odoo13/addons/stock/report/report_stock_quantity.py es identico al de nath (md5 sin espacios
# 19855883ff851244cbbf85d5ba07d98c en los dos) y ningun modulo de custom_addons cambia la vista
# (stock_enterprise solo anade read_grid y action_open_moves). Unico cambio: el CTE "WITH forecast_qty AS (...)"
# pasa a ser la subconsulta "FROM (...) forecast_qty". En PostgreSQL 11 un CTE es una barrera:
# se calcula entero (todos los productos x fechas) y el filtro product_id = X se aplica al final. Con la subconsulta, PostgreSQL mete el filtro dentro de
# cada parte del UNION y usa los indices de stock_move.product_id / stock_quant.product_id.
# Se mantiene UNION (no UNION ALL) para que el resultado sea exactamente el mismo.
SELECT_PREVISION = """
SELECT
    MIN(id) as id,
    product_id,
    state,
    date,
    sum(product_qty) as product_qty,
    company_id,
    warehouse_id
FROM (
    SELECT
        m.id,
        m.product_id,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN 'out'
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN 'in'
        END AS state,
        m.date_expected::date AS date,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN -product_qty
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN whs.id
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN whd.id
        END AS warehouse_id
    FROM
        stock_move m
    LEFT JOIN stock_location ls on (ls.id=m.location_id)
    LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    LEFT JOIN product_product pp on pp.id=m.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    WHERE
        pt.type = 'product' AND
        product_qty != 0 AND
        (whs.id IS NULL or whd.id IS NULL OR whs.id != whd.id) AND
        m.state NOT IN ('cancel', 'draft', 'done')
    UNION
    SELECT
        -q.id as id,
        q.product_id,
        'forecast' as state,
        date.*::date,
        q.quantity as product_qty,
        q.company_id,
        wh.id as warehouse_id
    FROM
        GENERATE_SERIES((now() at time zone 'utc')::date - interval '3month',
        (now() at time zone 'utc')::date + interval '3 month', '1 day'::interval) date,
        stock_quant q
    LEFT JOIN stock_location l on (l.id=q.location_id)
    LEFT JOIN stock_warehouse wh ON l.parent_path like concat('%/', wh.view_location_id, '/%')
    WHERE
        l.usage = 'internal'
    UNION
    SELECT
        m.id,
        m.product_id,
        'forecast' as state,
        GENERATE_SERIES(
        CASE
            WHEN m.state = 'done' THEN (now() at time zone 'utc')::date - interval '3month'
            ELSE m.date_expected::date
        END,
        CASE
            WHEN m.state != 'done' THEN (now() at time zone 'utc')::date + interval '3 month'
            ELSE m.date::date - interval '1 day'
        END, '1 day'::interval)::date date,
        CASE
            WHEN ((whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit') AND m.state = 'done' THEN product_qty
            WHEN ((whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit') AND m.state = 'done' THEN -product_qty
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN -product_qty
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN whs.id
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN whd.id
        END AS warehouse_id
    FROM
        stock_move m
    LEFT JOIN stock_location ls on (ls.id=m.location_id)
    LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    LEFT JOIN product_product pp on pp.id=m.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    WHERE
        pt.type = 'product' AND
        product_qty != 0 AND
        (whs.id IS NULL or whd.id IS NULL OR whs.id != whd.id) AND
        m.state NOT IN ('cancel', 'draft')
) AS forecast_qty
GROUP BY product_id, state, date, company_id, warehouse_id
"""


class ReportStockQuantity(models.Model):
    _inherit = 'report.stock.quantity'

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_quantity')
        self._cr.execute(
            "CREATE or REPLACE VIEW report_stock_quantity AS (%s)" % SELECT_PREVISION)

C=/opt/nath-erp/nath-erp.conf; g(){ sudo grep -oP "^$1\s*=\s*\K\S+" $C; }; cat > /tmp/prova_previsio.sql <<'SQLEOF'
\timing on
\echo == 1. NOU: grafic Previsto (mateix filtre que el boto)
EXPLAIN (ANALYZE, BUFFERS) SELECT date, state, sum(product_qty) FROM (SELECT
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
GROUP BY product_id, state, date, company_id, warehouse_id) v WHERE product_id = 750090 AND warehouse_id IS NOT NULL AND state = 'forecast' GROUP BY 1, 2;
\echo == 2. VELL: vista actual del mateix producte a una taula temporal (uns 4 min)
CREATE TEMP TABLE vell AS SELECT * FROM report_stock_quantity WHERE product_id = 750090;
CREATE TEMP TABLE nou AS SELECT * FROM (SELECT
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
GROUP BY product_id, state, date, company_id, warehouse_id) v WHERE product_id = 750090;
\echo == 3. Diferencies (han de ser 0 i 0)
SELECT (SELECT count(*) FROM vell) n_vell, (SELECT count(*) FROM nou) n_nou,
       (SELECT count(*) FROM (SELECT * FROM vell EXCEPT SELECT * FROM nou) a) nomes_vell,
       (SELECT count(*) FROM (SELECT * FROM nou EXCEPT SELECT * FROM vell) b) nomes_nou;
SQLEOF
PGPASSWORD="$(g db_password)" psql -h "$(g db_host)" -U "$(g db_user)" -d NATH_PRODUCTION -X -f /tmp/prova_previsio.sql > /tmp/prova_previsio.txt 2>&1; tail -5 /tmp/prova_previsio.txt

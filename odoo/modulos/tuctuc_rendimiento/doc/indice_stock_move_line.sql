-- TUCTUC - índice para la trazabilidad (movimientos de un producto). NO lo crea el módulo.
-- Ejecutar a mano en TUCTUC_PRODUCTION, solo con el sí de Isaac, fuera de horas punta.
--
-- Por qué: stock_move_line (19,1 M filas, 11 GB) no tiene índice por producto. Cada pantalla de movimientos de un
-- producto (botón de la ficha, Inventario > Informes) recorre la tabla entera: 0,97 s con 7 núcleos y 3,3 GB leídos
-- de memoria por consulta (EXPLAIN ANALYZE del 23/11/2026, producto 1318281), y la pantalla hace varias.
-- Desde el 02/09/2026 la tabla se ha leído entera o casi 748.684 veces (pg_stat_user_tables.seq_scan).
-- Con el índice: unos milisegundos. Un índice no cambia ningún resultado.
--
-- CONCURRENTLY: no bloquea las escrituras (las PDA y los TPV siguen trabajando); tarda unos minutos y no puede ir
-- dentro de una transacción (psql sin BEGIN). Si se corta, queda un índice "INVALID": borrarlo con
-- DROP INDEX CONCURRENTLY tuctuc_sml_product_id_idx; y repetir.
--
-- Nombre propio a propósito: Odoo 13 BORRA el índice "stock_move_line_product_id_index" al actualizar el módulo
-- stock si el campo no tiene index=True (odoo/fields.py, update_db_index). Con otro nombre no lo toca.

\timing on
SET statement_timeout = 0;
CREATE INDEX CONCURRENTLY IF NOT EXISTS tuctuc_sml_product_id_idx ON stock_move_line (product_id);

-- Comprobar que ha quedado válido y su tamaño:
SELECT c.relname, i.indisvalid, pg_size_pretty(pg_relation_size(c.oid))
FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relname = 'tuctuc_sml_product_id_idx';

-- Comprobar que se usa (debe salir "Index Scan" o "Bitmap Index Scan" en vez de "Parallel Seq Scan"):
EXPLAIN SELECT count(1) FROM stock_move_line WHERE product_id = 1318281 AND state = 'done';

-- Volver atrás (no cambia ningún dato):
-- DROP INDEX CONCURRENTLY tuctuc_sml_product_id_idx;

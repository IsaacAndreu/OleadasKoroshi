# -*- coding: utf-8 -*-
# KOROSHI - Recibido, pendiente, salidas y stock por SKU, con el stock separado por sitio (v1.0, 23/11/2026).
# SOLO LECTURA. Para «odoo-bin shell» en el servidor. Solo hace SELECT y termina con rollback.
# A diferencia de KOROSHI_exportar_tallas_MASTER_SHELL_2026-11-20.py, no lleva lista de modelos: saca todos los
# productos de la compañía 8 con algún movimiento o stock (también las temporadas viejas).
# Uso: odoo-bin shell -c /opt/nath-erp/nath-erp.conf -d NATH_PRODUCTION --no-http < este_fichero.py
# Escribe /tmp/koroshi_stock_sku.csv:
#   sku;ean;volumen_m3;recibido;pendiente;fecha_prevista_primera;salidas;stock_total;stock_ubicacion;
#   stock_faltante;stock_devolucion;stock_sorter
import csv

COMPANY_ID = 8
SALIDA = '/tmp/koroshi_stock_sku.csv'
cr = env.cr
datos = {}

def fila(pid):
    return datos.setdefault(pid, {'rec': 0.0, 'pend': 0.0, 'eta': '', 'sal': 0.0,
                                  'ubi': 0.0, 'fal': 0.0, 'dev': 0.0, 'sor': 0.0})

# Recibido de proveedor y salidas a clientes (hechos)
cr.execute("""SELECT sm.product_id,
                     SUM(CASE WHEN lo.usage = 'supplier' THEN sm.product_qty ELSE 0 END),
                     SUM(CASE WHEN ld.usage = 'customer' THEN sm.product_qty ELSE 0 END)
              FROM stock_move sm
              JOIN stock_location lo ON lo.id = sm.location_id
              JOIN stock_location ld ON ld.id = sm.location_dest_id
              WHERE sm.state = 'done' AND sm.company_id = %s AND (lo.usage = 'supplier' OR ld.usage = 'customer')
              GROUP BY 1""", (COMPANY_ID,))
for pid, rec, sal in cr.fetchall():
    d = fila(pid); d['rec'] = rec or 0.0; d['sal'] = sal or 0.0

# Pendiente de recibir (recepciones abiertas)
cr.execute("""SELECT sm.product_id, SUM(sm.product_qty), MIN(sm.date_expected)::date
              FROM stock_move sm JOIN stock_location lo ON lo.id = sm.location_id
              WHERE sm.state NOT IN ('done', 'cancel', 'draft') AND sm.company_id = %s AND lo.usage = 'supplier'
              GROUP BY 1""", (COMPANY_ID,))
for pid, pend, eta in cr.fetchall():
    d = fila(pid); d['pend'] = pend or 0.0; d['eta'] = str(eta or '')

# Stock interno separado por sitio
cr.execute("""SELECT sq.product_id,
                     CASE WHEN sl.complete_name ILIKE '%%FALTANTE%%' THEN 'fal'
                          WHEN sl.complete_name ILIKE '%%DEVOLU%%' THEN 'dev'
                          WHEN sl.complete_name ILIKE '%%SORTER%%' THEN 'sor'
                          ELSE 'ubi' END,
                     SUM(sq.quantity)
              FROM stock_quant sq JOIN stock_location sl ON sl.id = sq.location_id
              WHERE sq.company_id = %s AND sl.usage = 'internal'
              GROUP BY 1, 2""", (COMPANY_ID,))
for pid, sitio, qty in cr.fetchall():
    fila(pid)[sitio] += qty or 0.0

ids = list(datos)
cr.execute("""SELECT pp.id, pt.name, pp.barcode, pp.volume
              FROM product_product pp JOIN product_template pt ON pt.id = pp.product_tmpl_id
              WHERE pp.id = ANY(%s)""", (ids,))
prod = {pid: (nombre, ean, vol) for pid, nombre, ean, vol in cr.fetchall()}

with open(SALIDA, 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(['sku', 'ean', 'volumen_m3', 'recibido', 'pendiente', 'fecha_prevista_primera', 'salidas',
                'stock_total', 'stock_ubicacion', 'stock_faltante', 'stock_devolucion', 'stock_sorter'])
    for pid in ids:
        nombre, ean, vol = prod.get(pid, ('', '', 0))
        d = datos[pid]
        sku = (nombre or '').split(' ')[0].strip('[]')
        w.writerow([sku, ean or '', vol or 0, d['rec'], d['pend'], d['eta'], d['sal'],
                    d['ubi'] + d['fal'] + d['dev'] + d['sor'], d['ubi'], d['fal'], d['dev'], d['sor']])
cr.rollback()
print('KOROSHI_FIN productos=%d' % len(ids))

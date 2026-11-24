# -*- coding: utf-8 -*-
# KOROSHI - SKU que se cancelan por falta y tienen stock en Odoo (v1.0, 24/11/2026). Solo lee un fichero local.
# Datos: koroshi.kpi.falta del 16/11 al 23/11 y stock.quant interno de Odoo (leídos el 24/11 por JSON-RPC, solo lectura).
# Entrada: líneas «sku|ean|días|tiendas|líneas|uds|última(mm-dd)|stock_total|ubicación|cantidad|reservada».
# Uso: python -I -X utf8 KOROSHI_skus_falta_con_stock_2026-11-24.py <entrada.txt> <salida.xlsx>
import sys
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

ENT, OUT = sys.argv[1:3]
AZ = PatternFill('solid', fgColor='DDEBF7')
B = Font(bold=True)
GRUPOS = ['Hueco (L..)', 'FALTANTE', 'SORTER', 'DEVOLUCIÓN', 'TARKO / taras']


def grupo(loc):
    if loc.startswith('E/'):
        return 'Hueco (L..)'
    if 'FALTANTE' in loc:
        return 'FALTANTE'
    if 'SORTER' in loc:
        return 'SORTER'
    if 'DEVOLUCIO' in loc:
        return 'DEVOLUCIÓN'
    if loc.startswith('T/'):
        return 'TARKO / taras'
    return loc


def nombre(loc):
    return loc.replace('E/', 'EFFEC/Stock/NAVE2/', 1).replace('T/', 'TARKO/Stock/NAVE2/', 1).replace('EF/', 'EFFEC/', 1) \
        if loc[:2] in ('E/', 'T/') or loc.startswith('EF/') else loc


def cab(ws, row, heads, widths):
    for i, h in enumerate(heads, 1):
        c = ws.cell(row, i, h); c.font = B; c.fill = AZ; c.alignment = Alignment(wrap_text=True, vertical='top')
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w


filas = [l.strip().split('|') for l in open(ENT, encoding='utf-8') if l.strip()]
sku = {}
for f in filas:
    s = sku.setdefault(f[0], {'ean': f[1], 'dias': int(f[2]), 'tiendas': int(f[3]), 'lineas': int(f[4]), 'uds': int(f[5]),
                              'ult': '2026-' + f[6], 'stock': float(f[7]), 'g': {g: 0.0 for g in GRUPOS}, 'res': 0.0})
    s['g'][grupo(f[8])] += float(f[9])
    s['res'] += float(f[10])

wb = openpyxl.Workbook()
rs = wb.active; rs.title = 'Resumen'
rs['A1'] = 'KOROSHI · SKU cancelados por falta que SÍ tienen stock en Odoo (16/11–23/11)'; rs['A1'].font = Font(bold=True, size=13)
rs['A2'] = ('Fuente: Odoo, koroshi.kpi.falta (16/11–23/11) y stock interno leído el 24/11. Solo lectura. '
            'De 386 SKU con falta, estos %d tienen stock; el resto tiene stock 0.' % len(sku))
cab(rs, 4, ['Dónde está el stock', 'SKU', 'Uds en esa ubicación', 'Líneas de falta de esos SKU'], [26, 10, 20, 26])
r = 5
for g in GRUPOS:
    ss = [v for v in sku.values() if v['g'][g] > 0]
    rs.cell(r, 1, g); rs.cell(r, 2, len(ss)); rs.cell(r, 3, sum(v['g'][g] for v in ss)); rs.cell(r, 4, sum(v['lineas'] for v in ss))
    r += 1
rs.cell(r + 1, 1, 'Un SKU puede estar en más de una ubicación: la columna SKU no suma %d.' % len(sku))

p = wb.create_sheet('Por SKU')
cab(p, 1, ['SKU', 'EAN', 'Días con falta', 'Tiendas', 'Líneas', 'Uds canceladas', 'Última falta', 'Stock total Odoo',
           'En hueco (L..)', 'FALTANTE', 'SORTER', 'DEVOLUCIÓN', 'TARKO / taras', 'Reservadas'],
    [22, 15, 9, 8, 8, 10, 11, 10, 9, 10, 8, 11, 10, 10])
r = 2
for k, v in sorted(sku.items(), key=lambda x: (-x[1]['lineas'], x[0])):
    vals = [k, v['ean'], v['dias'], v['tiendas'], v['lineas'], v['uds'], v['ult'], v['stock']] + [v['g'][g] for g in GRUPOS] + [v['res']]
    for i, x in enumerate(vals, 1):
        p.cell(r, i, x)
    r += 1
p.freeze_panes = 'B2'; p.auto_filter.ref = 'A1:N%d' % (r - 1)

d = wb.create_sheet('Ubicaciones')
cab(d, 1, ['SKU', 'Tipo', 'Ubicación', 'Cantidad', 'Reservada'], [22, 14, 50, 9, 9])
r = 2
for f in sorted(filas, key=lambda x: (grupo(x[8]), x[8], x[0])):
    for i, x in enumerate([f[0], grupo(f[8]), nombre(f[8]), float(f[9]), float(f[10])], 1):
        d.cell(r, i, x)
    r += 1
d.freeze_panes = 'A2'; d.auto_filter.ref = 'A1:E%d' % (r - 1)
wb.save(OUT)
print('SKU', len(sku), 'ubicaciones', len(filas), {g: (sum(1 for v in sku.values() if v['g'][g] > 0), sum(v['g'][g] for v in sku.values())) for g in GRUPOS})

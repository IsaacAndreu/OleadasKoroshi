# -*- coding: utf-8 -*-
# KOROSHI - Ronda de faltantes prioritarios (v1.0, 24/11/2026). Solo lee un fichero local.
# Datos: koroshi.faltante pendientes cuyo artículo tiene líneas canceladas en koroshi.kpi.falta del 16/11 al 23/11,
# leídos de Odoo el 24/11 por JSON-RPC (solo lectura).
# Entrada: «ubicación|sku|ean|uds|tipo(S/R)|día(mm-dd)|en_ronda|líneas_falta|tiendas|OUT|stock_odoo».
# Uso: python -I -X utf8 KOROSHI_ronda_faltantes_prioritarios_2026-11-24.py <entrada.txt> <salida.xlsx>
import re
import sys
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ENT, OUT = sys.argv[1:3]
AZ = PatternFill('solid', fgColor='DDEBF7'); AM = PatternFill('solid', fgColor='FFF2CC')
B = Font(bold=True); FINO = Border(*(Side(style='thin', color='BFBFBF'),) * 4)


def cab(ws, row, heads, widths):
    for i, h in enumerate(heads, 1):
        c = ws.cell(row, i, h); c.font = B; c.fill = AZ; c.alignment = Alignment(wrap_text=True, vertical='top')
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w


def partes(ubic):
    hueco, _, cont = ubic.partition('/')
    m = re.search(r'(L\d+|MU-\d+) P(\d+) C(\d+)', hueco)
    return (m.group(1) if m else '', hueco, cont)


filas = [l.rstrip('\n').split('|') for l in open(ENT, encoding='utf-8') if l.strip()]
grupos = {}
for f in filas:
    k = (f[0], f[1])
    g = grupos.setdefault(k, {'f': f, 'n': 0, 'uds': 0.0, 'ronda': 0, 'outs': [], 'dias': []})
    g['n'] += 1; g['uds'] += float(f[3]); g['ronda'] = max(g['ronda'], int(f[6])); g['outs'].append(f[9]); g['dias'].append(f[5])

wb = openpyxl.Workbook()
r0 = wb.active; r0.title = 'Ronda'
r0['A1'] = 'KOROSHI · Ronda de faltantes prioritarios (24/11/2026)'; r0['A1'].font = Font(bold=True, size=13)
r0['A2'] = ('Faltantes pendientes cuyo artículo las tiendas siguen pidiendo (líneas canceladas 16/11–23/11). '
            '%d faltantes en %d paradas. Ordenado por lineal, pasillo y nivel: un solo recorrido.' % (len(filas), len(grupos)))
r0['A3'] = 'Columnas amarillas: las rellena el operario. Resultado = Está / No está / No existe la ubicación.'
heads = ['Orden', 'Lineal', 'Hueco', 'Contenedor', 'SKU', 'EAN', 'Uds a buscar', 'Faltantes', 'Líneas canceladas 16–23/11',
         'Tiendas', 'Ya en ronda INT/67387', 'Stock Odoo hoy', 'Resultado', 'Uds encontradas', 'Nota']
cab(r0, 5, heads, [6, 7, 20, 18, 20, 15, 8, 9, 11, 8, 10, 9, 13, 10, 28])
dv = DataValidation(type='list', formula1='"Está,No está,No existe la ubicación"', allow_blank=True)
r0.add_data_validation(dv)
r = 6
for i, ((ubic, sku), g) in enumerate(grupos.items(), 1):
    f = g['f']; lin, hueco, cont = partes(ubic)
    vals = [i, lin, hueco, cont, sku, f[2], g['uds'], g['n'], int(f[7]), int(f[8]), 'Sí' if g['ronda'] else 'No', float(f[10])]
    for j, v in enumerate(vals, 1):
        r0.cell(r, j, v).border = FINO
    for j in (13, 14, 15):
        c = r0.cell(r, j); c.fill = AM; c.border = FINO
    dv.add('M%d' % r)
    r += 1
r0.freeze_panes = 'C6'; r0.auto_filter.ref = 'A5:O%d' % (r - 1)
r0.print_title_rows = '5:5'; r0.page_setup.orientation = 'landscape'; r0.page_setup.fitToWidth = 1
r0.page_setup.fitToHeight = 0; r0.sheet_properties.pageSetUpPr.fitToPage = True

d = wb.create_sheet('Detalle por faltante')
cab(d, 1, ['Hueco y contenedor', 'SKU', 'EAN', 'Uds', 'Tipo', 'Día del faltante', 'En ronda INT/67387', 'OUT'],
    [40, 20, 15, 6, 16, 10, 10, 16])
for i, f in enumerate(filas, 2):
    for j, v in enumerate([f[0], f[1], f[2], float(f[3]), 'Sin alternativa' if f[4] == 'S' else 'Reubicado',
                           '2026-' + f[5], 'Sí' if f[6] == '1' else 'No', f[9]], 1):
        d.cell(i, j, v)
d.freeze_panes = 'A2'; d.auto_filter.ref = 'A1:H%d' % (len(filas) + 1)
wb.save(OUT)
print('faltantes', len(filas), 'paradas', len(grupos), 'uds', sum(g['uds'] for g in grupos.values()),
      'lineales', len({partes(k[0])[0] for k in grupos}), 'stock<=0', sum(1 for g in grupos.values() if float(g['f'][10]) <= 0))

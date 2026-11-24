# -*- coding: utf-8 -*-
# KOROSHI - % de faltante por artículo (v1.0, 24/11/2026). Solo lee ficheros locales.
# Uso: python -I -X utf8 KOROSHI_faltante_por_articulo_2026-11-24.py <conciliacion.xlsx> <libro2_v3.xlsx> <salida.xlsx>
import sys
import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

CONC, LIB2, OUT = sys.argv[1:4]
AZ = PatternFill('solid', fgColor='DDEBF7'); GR = PatternFill('solid', fgColor='F2F2F2'); ROJO = PatternFill('solid', fgColor='FFC7CE')
B = Font(bold=True)
wb = openpyxl.Workbook()

def cab(ws, row, heads, widths):
    for i, h in enumerate(heads, 1):
        c = ws.cell(row, i, h); c.font = B; c.fill = AZ; c.alignment = Alignment(wrap_text=True, vertical='top')
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[L(i)].width = w

def marcar(ws, col, desde, hasta):
    ws.conditional_formatting.add('A%d:%s%d' % (desde, L(ws.max_column), hasta),
                                  FormulaRule(formula=['$%s%d>Resumen!$B$4' % (col, desde)], fill=ROJO))

# ---------- Resumen ----------
rs = wb.active; rs.title = 'Resumen'
rs['A1'] = 'KOROSHI · % de faltante por artículo (24/11/2026)'; rs['A1'].font = Font(bold=True, size=13)
rs['A2'] = 'Datos: dashboard de llegadas de KOROSHI (24/11) y Odoo del 23/11. En rojo, los que pasan del umbral.'
rs['A4'] = 'Umbral de faltante'; rs['B4'] = 0.10; rs['B4'].number_format = '0%'; rs['A4'].font = B

# ---------- 1. Proveedor / recepción ----------
p = wb.create_sheet('1 Proveedor por artículo')
p['A1'] = 'Faltante del proveedor o de recepción: lo llegado según el PL que ni está recibido ni pendiente en Odoo'; p['A1'].font = Font(bold=True, size=12)
p['A2'] = ('% faltante = (llegado − recibido − pendiente) ÷ llegado. Artículo = modelo-color; «(PL sin desglose por color)» = modelo entero. '
           'No incluye las referencias distintas entre PL y Odoo (ver la conciliación).')
cab(p, 4, ['Modelo', 'Color', 'PL llegado', 'Recibido Odoo', 'Pendiente Odoo', 'Faltante (uds)', '% faltante', 'Clase de la conciliación'],
    [11, 26, 11, 12, 12, 12, 11, 40])
src = openpyxl.load_workbook(CONC, read_only=True)
filas = []
for r in src['Por modelo-color'].iter_rows(min_row=6, values_only=True):
    lleg, rec, pend, cl = r[2] or 0, r[5] or 0, r[6] or 0, r[9] or ''
    if lleg <= 0 or 'distinta' in cl or 'otra referencia' in cl:
        continue
    filas.append((r[0], r[1], lleg, rec, pend, cl))
filas.sort(key=lambda x: -max(x[2] - x[3] - x[4], 0) / x[2])
r = 5
for m, c, lleg, rec, pend, cl in filas:
    for i, v in enumerate([m, c, lleg, rec, pend], 1):
        p.cell(r, i, v).number_format = '#,##0'
    p.cell(r, 6, '=MAX(C%d-D%d-E%d,0)' % (r, r, r)).number_format = '#,##0'
    p.cell(r, 7, '=IFERROR(F%d/C%d,0)' % (r, r)).number_format = '0.0%'
    p.cell(r, 8, cl)
    r += 1
UP = r - 1
p.freeze_panes = 'C5'; p.auto_filter.ref = 'A4:H%d' % UP; marcar(p, 'G', 5, UP)

# ---------- 2. Inventario por SKU ----------
lib = openpyxl.load_workbook(LIB2, read_only=True, data_only=True)
s = wb.create_sheet('2 Inventario por SKU')
s['A1'] = 'Faltante de inventario por talla: stock en Odoo por debajo de lo esperado (recibido − salidas)'; s['A1'].font = Font(bold=True, size=12)
s['A2'] = '% faltante = uds que faltan ÷ recibido. Solo SKU con falta. Stock de Odoo del 23/11 (todas las ubicaciones internas).'
cab(s, 4, ['SKU', 'Modelo', 'Color', 'Talla', 'Recibido', 'Salidas', 'Stock esperado', 'Stock Odoo', 'Faltan (uds)', '% faltante'],
    [22, 11, 9, 7, 10, 10, 11, 10, 11, 11])
t = [x for x in lib['Desviación por talla'].iter_rows(min_row=6, values_only=True) if x[0] and (x[8] or 0) < 0]
t.sort(key=lambda x: (x[8] or 0) / x[4] if x[4] else 0)
r = 5
for x in t:
    for i, v in enumerate([x[3], x[0], x[1], x[2], x[4], x[5], x[6], x[7]], 1):
        s.cell(r, i, v).number_format = '#,##0'
    s.cell(r, 9, '=G%d-H%d' % (r, r)).number_format = '#,##0'
    s.cell(r, 10, '=IFERROR(I%d/E%d,0)' % (r, r)).number_format = '0.0%'
    r += 1
US = r - 1
s.freeze_panes = 'B5'; s.auto_filter.ref = 'A4:J%d' % US; marcar(s, 'J', 5, US)

# ---------- 3. Inventario por modelo-color ----------
mc = wb.create_sheet('3 Inventario modelo-color')
mc['A1'] = 'Faltante de inventario por modelo-color (suma de las tallas con falta)'; mc['A1'].font = Font(bold=True, size=12)
mc['A2'] = '% faltante = falta ÷ recibido. La sobra va aparte: no compensa la falta.'
cab(mc, 4, ['Modelo', 'Color', 'Recibido', 'Falta (uds)', 'Sobra (uds)', '% faltante', '¿Cruce de tallas?'], [11, 9, 11, 11, 11, 11, 12])
z = [x for x in lib['Desviación modelo-color'].iter_rows(min_row=6, values_only=True) if x[0] and (x[3] or 0) < 0]
z.sort(key=lambda x: (x[3] or 0) / x[2] if x[2] else 0)
r = 5
for x in z:
    for i, v in enumerate([x[0], x[1], x[2], -(x[3] or 0), x[4] or 0], 1):
        mc.cell(r, i, v).number_format = '#,##0'
    mc.cell(r, 6, '=IFERROR(D%d/C%d,0)' % (r, r)).number_format = '0.0%'
    mc.cell(r, 7, x[9] or '')
    r += 1
UM = r - 1
mc.freeze_panes = 'C5'; mc.auto_filter.ref = 'A4:G%d' % UM; marcar(mc, 'F', 5, UM)

# ---------- Resumen (fórmulas vivas sobre el umbral) ----------
cab(rs, 6, ['Tipo de faltante', 'Artículos con falta', 'Pasan del umbral', 'Uds de los que pasan'], [44, 16, 16, 20])
H1, H2, H3 = "'1 Proveedor por artículo'!", "'2 Inventario por SKU'!", "'3 Inventario modelo-color'!"
lineas = [('1. Proveedor / recepción (modelo-color)', H1, 'F', 'G', UP),
          ('2. Inventario por SKU (talla)', H2, 'I', 'J', US),
          ('3. Inventario por modelo-color', H3, 'D', 'F', UM)]
for i, (nom, h, cu, cp, u) in enumerate(lineas, 7):
    rs.cell(i, 1, nom)
    rs.cell(i, 2, '=COUNTIF(%s%s5:%s%d,">0")' % (h, cu, cu, u))
    rs.cell(i, 3, '=COUNTIF(%s%s5:%s%d,">"&$B$4)' % (h, cp, cp, u))
    rs.cell(i, 4, '=SUMIF(%s%s5:%s%d,">"&$B$4,%s%s5:%s%d)' % (h, cp, cp, u, h, cu, cu, u)).number_format = '#,##0'
rs['A11'] = ('Faltante de servicio (no servido ÷ pedido) no se puede sacar aún: el fichero de SMS4TEX solo trae lo no servido. '
             'Haría falta el total pedido por artículo.')
wb.save(OUT)
print('proveedor', UP - 4, 'sku', US - 4, 'modelo-color', UM - 4)

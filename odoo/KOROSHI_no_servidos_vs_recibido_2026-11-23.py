# Cruza los no servidos de SMS4TEX con comprado/recibido (MASTER v13) y el stock de Odoo del 20/11.
import csv, openpyxl, sys
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L

CSV_NS, BASE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
f = lambda x: float(x or 0)
ns = list(csv.DictReader(open(CSV_NS, encoding='utf-8-sig')))
T = {r['referencia']: r for r in csv.DictReader(open(BASE + '/20261120_tallas_MASTER_odoo.csv', encoding='utf-8-sig'), delimiter=';')}
src = openpyxl.load_workbook(BASE + '/261120_KOROSHI_1_MASTER_OI_26-27_v13.xlsx', read_only=True, data_only=True)
M = {}
for r in src['MASTER por modelo'].iter_rows(min_row=8, max_row=474, values_only=True):
    M[r[3]] = (f(r[12]), f(r[20]), f(r[24]))

AZ = PatternFill('solid', fgColor='DDEBF7'); GR = PatternFill('solid', fgColor='F2F2F2'); B = Font(bold=True)
wb = openpyxl.Workbook()

def cab(ws, row, heads, widths):
    for i, h in enumerate(heads, 1):
        c = ws.cell(row, i, h); c.font = B; c.fill = AZ; c.alignment = Alignment(wrap_text=True, vertical='top')
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[L(i)].width = w

# ---------- Comprado vs recibido ----------
cr = wb.create_sheet('Comprado vs recibido')
cr['A1'] = 'KOROSHI · Comprado (packing list) vs recibido en Odoo, por modelo — OI 26/27'; cr['A1'].font = Font(bold=True, size=13)
cr['A2'] = ('Recibido y pendiente: Odoo del 20/11/2026 (libro 1 MASTER v13). Pendiente dentro de compra = lo que aún puede '
            'llegar sin pasar de lo comprado. Faltante real = comprado − recibido − pendiente dentro de compra. '
            'El packing list es por modelo: no hay comprado por talla.')
cab(cr, 5, ['Modelo', 'Familia', 'Comprado (uds)', 'Recibido (uds)', '% recibido', 'Pendiente dentro de compra',
            'Faltante real (uds)', '% faltante real', 'Sobra sobre lo comprado (uds)', '% sobra'],
    [12, 9, 13, 13, 11, 14, 13, 12, 14, 10])
r = 6
for m, (c, rec, p) in M.items():
    cr.cell(r, 1, m); cr.cell(r, 2, m[4:6]); cr.cell(r, 3, c); cr.cell(r, 4, rec)
    cr.cell(r, 5, '=IFERROR(D%d/C%d,0)' % (r, r))
    cr.cell(r, 6, '=MIN(%s,MAX(C%d-D%d,0))' % (p, r, r))
    cr.cell(r, 7, '=MAX(C%d-D%d-F%d,0)' % (r, r, r))
    cr.cell(r, 8, '=IFERROR(G%d/C%d,0)' % (r, r))
    cr.cell(r, 9, '=MAX(D%d-C%d,0)' % (r, r))
    cr.cell(r, 10, '=IFERROR(I%d/C%d,0)' % (r, r))
    r += 1
U = r - 1
cr['A4'] = 'TOTAL'
for k in 'CDFGI':
    cr['%s4' % k] = '=SUM(%s6:%s%d)' % (k, k, U)
cr['E4'] = '=IFERROR(D4/C4,0)'; cr['H4'] = '=IFERROR(G4/C4,0)'; cr['J4'] = '=IFERROR(I4/C4,0)'
for c in cr[4]:
    c.font = B; c.fill = GR
for row in cr.iter_rows(min_row=4, max_row=U):
    for c in row[2:]:
        c.number_format = '#,##0'
    for i in (4, 7, 9):
        row[i].number_format = '0.0%'
cr.freeze_panes = 'B6'; cr.auto_filter.ref = 'A5:J%d' % U

# ---------- No servidos por SKU ----------
ws = wb.create_sheet('No servidos por SKU')
ws['A1'] = 'KOROSHI · SKU no servidos a tiendas (SMS4TEX, órdenes B2B Amposta, acumulado hasta el 23/11/2026) cruzados con Odoo'
ws['A1'].font = Font(bold=True, size=13)
ws['A2'] = ('Datos de Odoo del 20/11 (solo modelos del MASTER OI 26/27). Clase: A hay stock en Odoo → revisar nosotros; '
            'B pendiente de recibir; C agotado (todo lo recibido ya salió); D nunca recibido esa talla; '
            'E fuera del MASTER (sin datos de Odoo aquí).')
heads = ['SKU', 'Referencia', 'Temporada', 'Producto', 'Color', 'Talla', 'Órdenes', 'Solicitada', 'Servida', 'Pendiente',
         'Última orden', 'Clase', 'Recibido Odoo', 'Pendiente Odoo', 'Salidas Odoo', 'Stock Odoo 20/11', '% servido']
cab(ws, 5, heads, [22, 11, 9, 28, 16, 7, 9, 10, 9, 10, 11, 34, 10, 10, 10, 10, 9])
CL = {}
r = 6
for x in sorted(ns, key=lambda x: -f(x['Pendiente'])):
    t = T.get(x['SKU'])
    if x['Referencia'] not in M:
        c = 'E fuera del MASTER (I27/V27)' if x['Temporada'] in ('I27', 'V27') else 'E fuera del MASTER (temporada vieja)'
    elif not t:
        c = 'F SKU no está en Odoo'
    elif f(t['stock']) > 0:
        c = 'A hay stock en Odoo'
    elif f(t['pendiente']) > 0:
        c = 'B pendiente de recibir'
    elif f(t['recibido']) > 0:
        c = 'C agotado'
    else:
        c = 'D nunca recibido esa talla'
    vals = [x['SKU'], x['Referencia'], x['Temporada'], x['Producto'], x['Color'], x['Talla'], f(x['Ordenes']),
            f(x['Solicitada']), f(x['Servida']), f(x['Pendiente']), x['Ultima fecha de orden'], c]
    vals += [f(t[k]) for k in ('recibido', 'pendiente', 'salidas', 'stock')] if t else [None] * 4
    for i, v in enumerate(vals, 1):
        ws.cell(r, i, v)
    ws.cell(r, 17, '=IFERROR(I%d/H%d,0)' % (r, r)).number_format = '0%'
    a = CL.setdefault(c, [0, 0, 0]); a[0] += 1; a[1] += f(x['Pendiente']); a[2] += f(x['Ordenes'])
    r += 1
UN = r - 1
ws.freeze_panes = 'B6'; ws.auto_filter.ref = 'A5:Q%d' % UN

# ---------- Resumen ----------
rs = wb['Sheet']; rs.title = 'Resumen'
rs['A1'] = 'KOROSHI · Faltantes: ¿qué falta de verdad? (23/11/2026)'; rs['A1'].font = Font(bold=True, size=13)
rs['A3'] = '1. Comprado vs recibido (OI 26/27, por modelo)'; rs['A3'].font = B
CV = "'Comprado vs recibido'!"
filas = [('Comprado (uds)', '=%sC4' % CV, '#,##0'), ('Recibido (uds)', '=%sD4' % CV, '#,##0'),
         ('% recibido', '=%sE4' % CV, '0.0%'), ('Pendiente dentro de compra', '=%sF4' % CV, '#,##0'),
         ('Faltante real del proveedor (uds)', '=%sG4' % CV, '#,##0'), ('% faltante real', '=%sH4' % CV, '0.00%'),
         ('Modelos con faltante real', '=COUNTIF(%sG6:G%d,">0")' % (CV, U), '0'),
         ('Sobra sobre lo comprado (uds)', '=%sI4' % CV, '#,##0'),
         ('Modelos con sobra', '=COUNTIF(%sI6:I%d,">0")' % (CV, U), '0')]
for i, (k, fm, nf) in enumerate(filas, 4):
    rs.cell(i, 1, k); rs.cell(i, 2, fm).number_format = nf
rs['A15'] = '2. SKU no servidos a tiendas (SMS4TEX): por qué no se sirven'; rs['A15'].font = B
cab(rs, 16, ['Clase', 'SKU', 'Uds pendientes', '% de las uds', 'Órdenes'], [46, 10, 14, 12, 10])
NS = "'No servidos por SKU'!"
rr = 17; tot = 17 + len(CL)
for k in sorted(CL):
    rs.cell(rr, 1, k)
    rs.cell(rr, 2, '=COUNTIF(%sL6:L%d,A%d)' % (NS, UN, rr))
    rs.cell(rr, 3, '=SUMIF(%sL6:L%d,A%d,%sJ6:J%d)' % (NS, UN, rr, NS, UN)).number_format = '#,##0'
    rs.cell(rr, 4, '=IFERROR(C%d/C$%d,0)' % (rr, tot)).number_format = '0.0%'
    rs.cell(rr, 5, '=SUMIF(%sL6:L%d,A%d,%sG6:G%d)' % (NS, UN, rr, NS, UN)).number_format = '#,##0'
    rr += 1
rs.cell(rr, 1, 'TOTAL').font = B
for k in 'BCE':
    rs['%s%d' % (k, rr)] = '=SUM(%s17:%s%d)' % (k, k, rr - 1); rs['%s%d' % (k, rr)].number_format = '#,##0'
rs['D%d' % rr] = '=SUM(D17:D%d)' % (rr - 1); rs['D%d' % rr].number_format = '0.0%'
rs.cell(rr + 2, 1, 'OJO: el fichero de SMS4TEX acumula órdenes desde febrero; un SKU con 175 órdenes y 0 servidas es la '
                   'reposición pidiéndolo cada día. Stock de Odoo del 20/11, no el de cada día.')
wb.save(OUT)
for k in sorted(CL):
    print(k, CL[k])
print('ok', U, UN)

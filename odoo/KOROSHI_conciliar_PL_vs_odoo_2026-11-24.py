# -*- coding: utf-8 -*-
# KOROSHI - Conciliación packing list (dashboard de llegadas de KOROSHI) vs recibido en Odoo (v1.0, 24/11/2026).
# Solo lee ficheros locales: no se conecta a Odoo.
# Uso: python -I -X utf8 KOROSHI_conciliar_PL_vs_odoo_2026-11-24.py <dashboard_koroshi.html> <stock_por_sku.csv> <salida.xlsx> <hoy AAAA-MM-DD>
import collections, csv, json, sys
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

HTML, CSV_ODOO, OUT, HOY = sys.argv[1:5]
f = lambda x: float(x or 0)

t = open(HTML, encoding='utf-8', errors='replace').read()
def obj(n):
    i = t.index('var ' + n + '=') + len('var ' + n + '=')
    return json.JSONDecoder().raw_decode(t[i:])[0]
PL, ENV, CAN = obj('PL'), obj('D'), set(obj('CANCELLED'))

def fecha(x):
    x = (x or '').strip()
    if '/' in x:
        d, m, a = x.split('/'); return '%s-%s-%s' % (a, m.zfill(2), d.zfill(2))
    return x[:10]

# Envío de cada PL (un envío puede llevar varios PL: «2094/2095/2096»)
envio = {}
for e in ENV:
    for p in str(e.get('packing') or '').split('/'):
        if p.strip():
            envio[p.strip()] = e

# Estado de cada PL y líneas (modelo, color, uds)
import re
def codigo_color(txt):
    """Código de color de 6 cifras del PL; None si la línea mezcla colores o solo trae el nombre."""
    txt = (txt or '').strip()
    cods = set(re.findall(r'(?<!\d)\d{6}(?!\d)', txt))
    if len(cods) == 1:
        return cods.pop()
    if not cods:
        m = re.match(r'^(\d{1,5})\b', txt)
        if m:
            return m.group(1).zfill(6)
    return None
lineas = {k: [(x['ref'], codigo_color(x['color']), x['pcs'] or 0, x['ctns'] or 0, x['cbm'] or 0) for x in v['models']]
          for k, v in PL.items()}
# Odoo por SKU (se lee antes para saber qué colores tiene cada modelo)
ODOO_SKU = []
for r in csv.DictReader(open(CSV_ODOO, encoding='utf-8-sig'), delimiter=';'):
    p = r['sku'].split('-')
    if len(p) >= 2:
        ODOO_SKU.append((p[0], p[1], f(r['recibido']), f(r['pendiente']), f(r['stock_total'])))
colores_odoo = collections.defaultdict(set)
for m, c, rec, pend, st in ODOO_SKU:
    if rec or pend:
        colores_odoo[m].add(c)
colores_pl = collections.defaultdict(set)
for k, ls in lineas.items():
    if k not in CAN:
        for r, c, p, _, _ in ls:
            if p:
                colores_pl[r].add(c)
# Modelos que se comparan solo por modelo: el PL mezcla colores en una línea, no trae código, o le faltan colores que
# sí hay en Odoo (muchos PL ponen un solo color para todo el modelo)
SIN_DESGLOSE = {r for ls in lineas.values() for r, c, p, _, _ in ls if c is None and p}
SIN_DESGLOSE |= {m for m in colores_pl if colores_odoo.get(m) and not colores_odoo[m] <= colores_pl[m]}
SIN_COLOR = '(PL sin desglose por color)'
lineas = {k: [(r, SIN_COLOR if r in SIN_DESGLOSE else c, p, ct, cb) for r, c, p, ct, cb in ls] for k, ls in lineas.items()}
firmas_con_envio = collections.defaultdict(set)
for k, ls in lineas.items():
    if k in envio and k not in CAN:
        for r, c, p, _, _ in ls:
            firmas_con_envio[(r, c, p)].add(k)
estado = {}
for k, ls in lineas.items():
    if k in CAN:
        estado[k] = 'Cancelado'
    elif k in envio:
        fl = fecha(envio[k].get('llegada_barbera'))
        estado[k] = 'Llegado' if fl and fl <= HOY else 'En camino'
    elif ls and all(p == 0 or firmas_con_envio.get((r, c, p)) for r, c, p, _, _ in ls):
        estado[k] = 'Duplicado (mismas uds en un PL con envío)'
    else:
        estado[k] = 'Sin envío'

# PL por modelo-color
pl = collections.defaultdict(lambda: {'Llegado': 0.0, 'En camino': 0.0, 'Sin envío': 0.0, 'pls': set()})
for k, ls in lineas.items():
    if estado[k] not in ('Llegado', 'En camino', 'Sin envío'):
        continue
    for r, c, p, _, _ in ls:
        pl[(r, c)][estado[k]] += p
        if p:
            pl[(r, c)]['pls'].add(k)

# Odoo por modelo-color
odoo = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
for m, c, rec, pend, st in ODOO_SKU:
    o = odoo[(m, SIN_COLOR if m in SIN_DESGLOSE else c)]
    o[0] += rec; o[1] += pend; o[2] += st
modelos_pl = {m for m, c in pl}

# Referencia probablemente mal escrita en el PL: el modelo del PL no tiene nada en Odoo y otro modelo con la misma
# familia y número (p. ej. 2521JA50 → 2621JA50) tiene recibido de más
tot_pl_mod = collections.Counter(); rec_mod = collections.Counter()
for (m, c), a in pl.items():
    tot_pl_mod[m] += a['Llegado'] + a['En camino'] + a['Sin envío']
for (m, c), o in odoo.items():
    rec_mod[m] += o[0] + o[1]
ALIAS, ALIAS_DE = {}, {}
for m in modelos_pl:
    falta = tot_pl_mod[m] - rec_mod[m]
    if tot_pl_mod[m] > 0 and rec_mod[m] < 0.1 * tot_pl_mod[m]:
        cands = [x for x in rec_mod if x != m and x[-4:] == m[-4:] and rec_mod[x] - tot_pl_mod[x] >= 0.5 * falta]
        if len(cands) == 1:
            ALIAS[m] = cands[0]; ALIAS_DE[cands[0]] = m

filas = []
for key in sorted(set(pl) | {k for k in odoo if k[0] in modelos_pl or k[0] in ALIAS_DE}):
    a = pl.get(key, {'Llegado': 0.0, 'En camino': 0.0, 'Sin envío': 0.0, 'pls': set()})
    rec, pend, st = odoo.get(key, [0.0, 0.0, 0.0])
    tot_pl = a['Llegado'] + a['En camino'] + a['Sin envío']
    pend_mas = max(pend - max(tot_pl - rec, 0), 0)
    filas.append([key[0], key[1], a['Llegado'], a['En camino'], a['Sin envío'], rec, pend, rec - a['Llegado'],
                  ' '.join(sorted(a['pls'])), pend_mas])

# Por modelo: para ver si los desvíos de color se compensan dentro del modelo
pm = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
for m, c, lleg, cam, sin, rec, pend, dif, _, _ in filas:
    x = pm[m]; x[0] += lleg; x[1] += rec; x[2] += max(-dif, 0); x[3] += max(dif, 0)

def clase(m, lleg, cam, sin, rec, pend, dif):
    tot_pl = lleg + cam + sin
    if m in ALIAS:
        return 'Referencia distinta: el PL dice %s y en Odoo se recibió como %s' % (m, ALIAS[m])
    if m in ALIAS_DE and dif > 0:
        return 'Recibido con otra referencia: en el PL es %s' % ALIAS_DE[m]
    if tot_pl == 0 and rec > 0:
        return 'Recibido sin PL (color que no está en el PL)'
    if tot_pl > 0 and rec == 0 and pend == 0:
        return 'En el PL y nada en Odoo'
    if dif == 0:
        return 'Cuadra'
    if pm[m][2] > 0 and pm[m][3] > 0:
        return 'Cruce de colores en el modelo'
    if dif < 0:
        return 'Llegado y sin recepcionar' if pend >= -dif else 'Recibido de menos'
    return 'Recibido de más (puede ser de un PL en camino)' if dif <= cam + sin else 'Recibido de más'

AZ = PatternFill('solid', fgColor='DDEBF7'); GR = PatternFill('solid', fgColor='F2F2F2'); B = Font(bold=True)
wb = openpyxl.Workbook()
def cab(ws, row, heads, widths):
    for i, h in enumerate(heads, 1):
        c = ws.cell(row, i, h); c.font = B; c.fill = AZ; c.alignment = Alignment(wrap_text=True, vertical='top')
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[L(i)].width = w

# ---------- Por modelo-color ----------
mc = wb.create_sheet('Por modelo-color')
mc['A1'] = 'KOROSHI · Packing list vs recibido en Odoo, por modelo-color (%s)' % HOY; mc['A1'].font = Font(bold=True, size=13)
mc['A2'] = ('PL = dashboard de llegadas de KOROSHI, sin PL cancelados ni duplicados. Llegado = su envío ya tiene fecha de llegada a Barberà. '
            'Odoo = recibido de proveedor y recepciones abiertas (pendiente) del 23/11. Diferencia = recibido − llegado. '
            'Color «(PL sin desglose por color)»: el PL de ese modelo mezcla colores en una línea o no trae código, y se compara el modelo entero.')
heads = ['Modelo', 'Color', 'PL llegado', 'PL en camino', 'PL sin envío', 'Recibido Odoo', 'Pendiente Odoo', 'Diferencia (uds)',
         '% s/ llegado', 'Clase', 'PL', 'Pendiente de más (recepción abierta que sobra)']
cab(mc, 5, heads, [11, 9, 11, 11, 11, 12, 12, 12, 10, 44, 22, 16])
cnt = collections.defaultdict(lambda: [0, 0.0, 0.0])
PEND_MAS = [0, 0.0]
r = 6
for m, c, lleg, cam, sin, rec, pend, dif, pls, pmas in sorted(filas, key=lambda x: (-abs(x[7]), x[0], x[1])):
    cl = clase(m, lleg, cam, sin, rec, pend, dif)
    for i, v in enumerate([m, c, lleg, cam, sin, rec, pend, dif], 1):
        mc.cell(r, i, v).number_format = '#,##0'
    mc.cell(r, 9, '=IFERROR(H%d/C%d,0)' % (r, r)).number_format = '0.0%'
    mc.cell(r, 10, cl); mc.cell(r, 11, pls); mc.cell(r, 12, pmas).number_format = '#,##0'
    k = cnt[cl]; k[0] += 1; k[1] += abs(dif); k[2] += lleg
    if pmas > 0:
        PEND_MAS[0] += 1; PEND_MAS[1] += pmas
    r += 1
UMC = r - 1
mc.freeze_panes = 'C6'; mc.auto_filter.ref = 'A5:L%d' % UMC

# ---------- Por modelo ----------
mo = wb.create_sheet('Por modelo')
mo['A1'] = 'KOROSHI · Packing list vs recibido en Odoo, por modelo (%s)' % HOY; mo['A1'].font = Font(bold=True, size=13)
mo['A2'] = 'Falta y sobra = suma de los colores con menos / más recibido que llegado. Si las dos son > 0, hay cruce de colores.'
cab(mo, 5, ['Modelo', 'PL llegado', 'Recibido Odoo', 'Neto (uds)', 'Colores de menos (uds)', 'Colores de más (uds)', 'Cruce de colores'],
    [11, 12, 12, 11, 13, 13, 12])
r = 6
for m, (lleg, rec, falta, sobra) in sorted(pm.items(), key=lambda x: -(x[1][2] + x[1][3])):
    for i, v in enumerate([m, lleg, rec, rec - lleg, -falta, sobra], 1):
        mo.cell(r, i, v).number_format = '#,##0'
    mo.cell(r, 7, 'Sí' if falta > 0 and sobra > 0 else '')
    r += 1
mo.freeze_panes = 'B6'; mo.auto_filter.ref = 'A5:G%d' % (r - 1)

# ---------- Por PL ----------
pp = wb.create_sheet('Por PL')
pp['A1'] = 'KOROSHI · Estado de cada packing list del dashboard (%s)' % HOY; pp['A1'].font = Font(bold=True, size=13)
cab(pp, 5, ['PL', 'Estado', 'Uds', 'Cartones', 'm³', 'Modelos', 'Proveedor', 'Contenedor', 'Llegada a Barberà'], [8, 36, 10, 10, 9, 40, 30, 14, 14])
r = 6
for k in sorted(lineas):
    e = envio.get(k, {})
    ls = lineas[k]
    vals = [k, estado[k], sum(x[2] for x in ls), sum(x[3] for x in ls), round(sum(x[4] for x in ls), 3),
            ' '.join(sorted({x[0] for x in ls})), e.get('proveedor', PL[k].get('supplier', '')), e.get('container', ''), fecha(e.get('llegada_barbera'))]
    for i, v in enumerate(vals, 1):
        pp.cell(r, i, v)
    r += 1
pp.freeze_panes = 'C6'; pp.auto_filter.ref = 'A5:I%d' % (r - 1)

# ---------- Resumen ----------
rs = wb['Sheet']; rs.title = 'Resumen'
rs['A1'] = 'KOROSHI · ¿Se recepcionó bien lo que dice el packing list? (%s)' % HOY; rs['A1'].font = Font(bold=True, size=13)
rs['A2'] = 'Datos: dashboard de llegadas de KOROSHI y Odoo del 23/11. Diferencia en valor absoluto (lo que falta y lo que sobra suman).'
cab(rs, 4, ['Clase', 'Modelo-color', 'Diferencia (uds, abs.)', 'PL llegado (uds)'], [48, 14, 20, 18])
r = 5
for k in sorted(cnt, key=lambda x: -cnt[x][1]):
    rs.cell(r, 1, k); rs.cell(r, 2, cnt[k][0]); rs.cell(r, 3, cnt[k][1]).number_format = '#,##0'; rs.cell(r, 4, cnt[k][2]).number_format = '#,##0'
    r += 1
rs.cell(r, 1, 'TOTAL').font = B
for col in 'BCD':
    rs['%s%d' % (col, r)] = '=SUM(%s5:%s%d)' % (col, col, r - 1); rs['%s%d' % (col, r)].number_format = '#,##0'
r += 2
rs.cell(r, 1, 'Recepciones abiertas en Odoo por encima de lo que falta por llegar').font = B
rs.cell(r + 1, 1, 'Modelo-color'); rs.cell(r + 1, 2, PEND_MAS[0])
rs.cell(r + 2, 1, 'Uds pendientes de más'); rs.cell(r + 2, 2, PEND_MAS[1]).number_format = '#,##0'
r += 4
ec = collections.Counter(estado.values())
rs.cell(r, 1, 'Packing lists por estado').font = B; r += 1
for k, v in ec.most_common():
    rs.cell(r, 1, k); rs.cell(r, 2, v); r += 1
wb.save(OUT)
print('estados PL', dict(ec))
for k in sorted(cnt, key=lambda x: -cnt[x][1]):
    print(k, cnt[k])
print('modelos con cruce de colores', sum(1 for v in pm.values() if v[2] > 0 and v[3] > 0))
print('sin desglose', len(SIN_DESGLOSE), 'alias', ALIAS, 'pendiente de más', PEND_MAS)
print('llegado', sum(x[2] for x in filas), 'recibido', sum(x[5] for x in filas), 'pendiente', sum(x[6] for x in filas))

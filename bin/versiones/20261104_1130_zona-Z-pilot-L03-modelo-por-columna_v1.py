# Prova pilot L03 P18-P36 (Zona Z): quin model-color va a cada columna.
# Dades: estoc NAVE2 del 02/11 (stock_nave2_20261102.txt) i litres de calc.py.
import sys, re, math, collections, os
NAVE = r'C:\Users\tuctuc\AppData\Local\Temp\claude\C--dev-OleadasKoroshi\647e5596-1777-445d-8786-affe3d0fc698\scratchpad\nave'
sys.path.insert(0, NAVE)
from calc import MC, HUECO_L
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUTF = sys.argv[1]
POS = ['P%02d' % p for p in list(range(18, 32)) + [34, 35, 36]]      # P32/P33: a Odoo existeixen pero estan buides -> reserva
COLS = ['C1', 'C2', 'C3', 'C4']
MIG = HUECO_L / 2 * 0.9          # mig forat (10,7 L) al 90 %: 9,6 L
PER_COL = 18                     # 9 forats x 2 migs
OBJ = 0.85                       # ompli fins al 85 %, la resta marge
TORDER = {t: i for i, t in enumerate(['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL', 'XXXL', '4XL', '5XL', 'UNI', 'U', 'TU'])}
def tkey(t):
    if t in TORDER: return (0, TORDER[t], t)
    m = re.match(r'(\d+)', t); return (1, int(m.group(1)) if m else 999, t)

raw = {}
for ln in open(os.path.join(NAVE, 'stock_nave2_20261102.txt'), encoding='utf-8').read().split('\n'):
    mc, se, t, ub = ln.split('|')
    raw[mc] = {x.rsplit(':', 1)[0]: int(x.rsplit(':', 1)[1]) for x in ub.split(',') if ':' in x}
R = re.compile(r'L03 P(1[89]|2\d|3[0-6]) C')

cand = []
for m in MC:
    u3 = sum(q for k, q in raw[m['mc']].items() if R.match(k))
    if not u3: continue
    need = max(1, math.ceil(m['L'] / MIG - 1e-9))
    color = m['mc'].rsplit('-', 1)[1]
    cand.append(dict(m=m, mc=m['mc'], u3=u3, need=need, color=color, fam=m['fam'] or '¿?'))
cand.sort(key=lambda x: (-(x['u3'] / x['m']['u']), -x['u3']))

CAP = len(POS) * 4 * PER_COL
sel, used = [], 0
for x in cand:
    if x['need'] > 4 * PER_COL: continue                       # mes d'una posicio sencera: no es pilot
    if used + x['need'] <= CAP * OBJ: sel.append(x); used += x['need']
selset = {x['mc'] for x in sel}

# ---- col.locacio: models grans primer (ocupen columnes senceres), despres first-fit amb regla de barreja ----
cols = [dict(pos=p, col=c, items=[], free=PER_COL) for p in POS for c in COLS]
def ok_veí(col, x):
    if not col['items']: return True
    a = col['items'][-1]
    return a['color'] != x['color'] and a['fam'] != x['fam']
grans = sorted([x for x in sel if x['need'] > PER_COL], key=lambda x: -x['need'])
petits = sorted([x for x in sel if x['need'] <= PER_COL], key=lambda x: -x['need'])
ci = 0
for x in grans:                                                # columnes seguides dins la mateixa posicio si cal
    n = math.ceil(x['need'] / PER_COL)
    while True:
        blk = cols[ci:ci + n]
        if len(blk) == n and len({b['pos'] for b in blk}) == 1 and all(not b['items'] for b in blk): break
        ci += 1
    rest = x['need']
    for b in blk:
        q = min(PER_COL, rest); b['items'].append(dict(x, q=q, part=True)); b['free'] -= q; rest -= q
    ci += n
viol = 0
for x in petits:
    tgt = next((c for c in cols if c['free'] >= x['need'] and ok_veí(c, x)), None)
    if tgt is None:
        tgt = next(c for c in cols if c['free'] >= x['need']); viol += 1
    tgt['items'].append(dict(x, q=x['need'], part=False)); tgt['free'] -= x['need']

# ---- assignacio de nivells (1 = dalt) i talles en ordre ----
rows = []
for c in cols:
    h = 0
    for it in c['items']:
        n0, h = h, h + it['q']
        it['niv'] = '%d-%d' % (n0 // 2 + 1, math.ceil(h / 2)) if math.ceil(h / 2) != n0 // 2 + 1 else str(n0 // 2 + 1)
        it['pos'], it['col'] = c['pos'], c['col']

# un registre per model: posicio, columnes, nivells
PL = collections.OrderedDict()
for c in cols:
    for it in c['items']:
        p = PL.setdefault(it['mc'], dict(it=it, pos=c['pos'], cols=[], niv=it['niv']))
        p['cols'].append(c['col'])
        if len(p['cols']) > 1: p['niv'] = '1-9'
def colstr(p): return p['cols'][0] if len(p['cols']) == 1 else '%s-%s' % (p['cols'][0], p['cols'][-1])

# ---- moviments ----
def fonts(mc):
    return sorted(((k, q) for k, q in raw[mc].items() if not R.match(k)), key=lambda kq: -kq[1])
entren = sum(x['m']['u'] - x['u3'] for x in sel)
surten = [(x, q) for x in cand if x['mc'] not in selset for k, q in raw[x['mc']].items() if R.match(k)]

# ---- Excel ----
wb = Workbook()
B = Font(bold=True); H = PatternFill('solid', fgColor='DDEBF7'); W = Alignment(wrap_text=True, vertical='top')
thin = Side(style='thin', color='999999'); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
def head(ws, r, vals):
    for i, v in enumerate(vals, 1):
        c = ws.cell(r, i, v); c.font = B; c.fill = H; c.alignment = W
def widths(ws, ws_w):
    for i, w in enumerate(ws_w, 1): ws.column_dimensions[get_column_letter(i)].width = w

ws = wb.active; ws.title = 'Resum'
L = [
    ('Prova pilot Zona Z · L03 P18-P36 · un model-color per columna (V36 vertical)', None),
    ('Dades: estoc NAVE2 de l\'Odoo del 02/11/2026 (comprovat el 04/11: L03 gairebe igual). Tornar a treure el dia del trasllat.', None),
    (None, None),
    ('Posicions de la prova', '%d (P18-P31 i P34-P36). P32 i P33 existeixen a l\'Odoo pero estan buides: reserva si fisicament hi son.' % len(POS)),
    ('Columnes', '%d (C1-C4 de cada posicio, les que ja hi ha a l\'Odoo)' % (len(POS) * 4)),
    ('Una columna', '9 forats en alt de 21,3 L (A36). Es compta en migs forats de %.1f L utils (90 %%).' % MIG),
    ('Ompliment objectiu', '%d %% (la resta es marge per entrades)' % (OBJ * 100)),
    ('Ocupacio prevista', '%d de %d migs forats (%.0f %%)' % (used, CAP, 100 * used / CAP)),
    (None, None),
    ('Model-colors que hi ha avui a L03 P18-P36', len(cand)),
    ('Unitats que hi ha avui a L03 P18-P36', sum(x['u3'] for x in cand)),
    ('Model-colors escollits per a la prova', len(sel)),
    ('   unitats d\'aquests models (totes)', sum(x['m']['u'] for x in sel)),
    ('   ja son a L03', sum(x['u3'] for x in sel)),
    ('   s\'han de portar d\'altres llocs (full «Entren»)', entren),
    ('Unitats d\'altres models que han de sortir de L03 (full «Surten»)', sum(q for _, q in surten)),
    ('Moviments totals (unitats)', entren + sum(q for _, q in surten)),
    (None, None),
    ('Criteri d\'eleccio', 'Primer els model-colors que ja tenen mes part del seu estoc a L03 (menys moviments). Model sencer: totes les talles al mateix lloc.'),
    ('Ordre dins la columna', 'Cada model-color en un tram seguit; talles de petita a gran, de dalt (nivell 1) a baix (nivell 9).'),
    ('Regla de barreja aplicada', 'Dos models seguits a la mateixa columna: mai el mateix codi de color ni la mateixa familia.'),
    ('   casos on no s\'ha pogut complir', viol),
    ('Clar / fosc i estampat / llis', 'L\'Odoo no te el nom del color (nomes el codi). Ho ha de mirar el José Luis al muntar: columna «Clar/fosc» del full «Plànol».'),
    (None, None),
    ('Com fer la prova', '1) Abans: mesurar 1 dia de picking a L03 com esta ara (temps per linia, errors). 2) Treure el que surt. '
                         '3) Portar el que entra, columna per columna, escanejant a la PDA. 4) Etiqueta a cada columna amb el model-color. '
                         '5) 2-3 dies de picking: temps per linia, errors, quantes vegades cal mirar l\'etiqueta.'),
]
for r, (a, b) in enumerate(L, 1):
    ws.cell(r, 1, a).font = B if r == 1 or b is not None else Font()
    if b is not None: ws.cell(r, 2, b).alignment = W
ws['A1'].font = Font(bold=True, size=13)
widths(ws, [52, 110])

# Plànol: una fila per posicio, una columna per C1..C4
ws = wb.create_sheet('Plànol')
head(ws, 1, ['Posició'] + ['%s (dalt → baix)' % c for c in COLS])
for i, p in enumerate(POS, 2):
    ws.cell(i, 1, 'L03 ' + p).font = B
    for j, c in enumerate(COLS, 2):
        col = next(k for k in cols if k['pos'] == p and k['col'] == c)
        txt = '\n'.join('niv %s · %s · %s · %s' % (it['niv'], it['mc'], it['fam'][:18], ' '.join(s['t'] for s in sorted(it['m']['skus'], key=lambda s: tkey(s['t']))))
                        for it in col['items'])
        cc = ws.cell(i, j, txt or '(lliure)'); cc.alignment = W; cc.border = BOX
    ws.row_dimensions[i].height = 15 * max(1, max(len(k['items']) for k in cols if k['pos'] == p))
widths(ws, [12, 48, 48, 48, 48])

# Detall per talla: el que ha de quedar a cada columna
ws = wb.create_sheet('Detall per talla')
head(ws, 1, ['Posició', 'Col', 'Nivells', 'Model-color', 'Família', 'Temporada', 'Codi color', 'Talla', 'Uds', 'Litres', 'Ja a L03 (model)', 'Clar/fosc (José Luis)', 'Estampat/llis'])
r = 2
for mc, p in PL.items():
    it = p['it']
    for sk in sorted(it['m']['skus'], key=lambda s: tkey(s['t'])):
        for v, val in enumerate(['L03 ' + p['pos'], colstr(p), p['niv'], mc, it['fam'], it['m']['temp'], it['color'], sk['t'], sk['u'], round(sk['L'], 1), it['u3'], '', ''], 1):
            ws.cell(r, v, val)
        r += 1
ws.freeze_panes = 'A2'; ws.auto_filter.ref = 'A1:M%d' % (r - 1)
widths(ws, [11, 5, 8, 20, 30, 10, 10, 7, 6, 8, 10, 14, 12])

# Entren: d'on s'ha d'anar a buscar
ws = wb.create_sheet('Entren')
head(ws, 1, ['Destí', 'Model-color', 'Família', 'Uds a portar', 'Ubicacions d\'origen (uds), de més a menys'])
r = 2
for mc, p in PL.items():
    f = fonts(mc)
    if not f: continue
    ws.cell(r, 1, 'L03 %s %s' % (p['pos'], colstr(p))); ws.cell(r, 2, mc); ws.cell(r, 3, p['it']['fam'])
    ws.cell(r, 4, sum(q for _, q in f)); ws.cell(r, 5, ', '.join('%s (%d)' % kq for kq in f)).alignment = W
    r += 1
ws.freeze_panes = 'A2'
widths(ws, [16, 20, 30, 12, 110])

# Surten: el que no es queda a L03
ws = wb.create_sheet('Surten')
head(ws, 1, ['Model-color', 'Família', 'Uds a L03', 'Ubicacions a L03', 'Destí suggerit: on té més estoc fora de L03'])
r = 2
for x in sorted([x for x in cand if x['mc'] not in selset], key=lambda x: -x['u3']):
    here = [(k, q) for k, q in raw[x['mc']].items() if R.match(k)]
    f = [kq for kq in fonts(x['mc']) if re.match(r'L\d+ P', kq[0])]
    ws.cell(r, 1, x['mc']); ws.cell(r, 2, x['fam']); ws.cell(r, 3, x['u3'])
    ws.cell(r, 4, ', '.join('%s (%d)' % kq for kq in here)); ws.cell(r, 5, '%s (%d)' % f[0] if f else 'a decidir')
    r += 1
ws.freeze_panes = 'A2'
widths(ws, [20, 30, 10, 50, 40])

wb.save(OUTF)
print('sel', len(sel), 'used', used, CAP, 'entren', entren, 'surten', sum(q for _, q in surten), 'viol', viol,
      'grans', len(grans), 'cols buides', sum(1 for c in cols if not c['items']))

# PILOT ZONA Z · L03 tram P18-P24 · un model-color per columna (04/11/2026)
# Accio de servidor sobre stock.picking (provar a la 1837). No depen dels registres seleccionats.
# Crea 3 tipus d'INT (tipus 48 EFFEC "Transferencias internas"):
#   A  BUIDAR   : el que hi ha al tram i NO es queda -> a la columna on aquell model te mes estoc fora del tram
#   B  RECOLLIR : tot l'estoc lliure dels models escollits -> CARRO PILOT L03 (fora d'EFFEC/Stock: cap OUT el reserva)
#                 un INT per bloc de lineals d'origen (per repartir-ho entre pickers)
#   C  UBICAR   : CARRO PILOT L03 -> columna final de cada talla (queda "en espera"; "Comprobar disponibilidad" quan B estigui validat)
# Unitats reservades per a OUT/INT oberts: NO es mouen (es llisten al diagnostic).
# MODO = 'DIAGNOSTICO' no escriu res i acaba amb raise Warning. MODO = 'REAL' nomes amb l'OK de l'Isaac.
MODO = 'DIAGNOSTICO'
CO = 8
TRAMO = 'L03 P18-P24'
ORIGEN = 'PILOT ' + TRAMO
STOCK_ID = 85
NAVE2_ID = 31480
PTYPE_ID = 48
CARRO_BC = 'CARRO-PILOT-L03'
BLOQUES = [(1, 12, 'B1 L01-L12'), (13, 24, 'B2 L13-L24'), (25, 36, 'B3 L25-L36'), (37, 999, 'B4 L37+'), (0, 0, 'B5 sin lineal')]
DATA = """
25100-000039-XS|L03 P18 C2
25100-000039-S|L03 P18 C2
25100-000039-M|L03 P18 C2
25100-000039-XL|L03 P18 C2
YS8044-000039-35|L03 P18 C3
YS8044-000039-36|L03 P18 C3
YS8044-000039-39|L03 P18 C3
YS8044-000039-40|L03 P18 C3
1822PT27-000003-34|L03 P18 C3
1822PT27-000003-36|L03 P18 C3
1822PT27-000003-38|L03 P18 C3
1822PT27-000003-42|L03 P18 C3
1822PT27-000003-44|L03 P18 C3
23207-000010-XL|L03 P18 C4
23207-000010-XXL|L03 P18 C4
23207-000010-3XL|L03 P18 C4
23394-000005-S|L03 P18 C4
23394-000005-XXL|L03 P18 C4
2222XC26-000003-36|L03 P19 C1
2222XC26-000003-37|L03 P19 C1
2222XC26-000003-38|L03 P19 C1
2222XC26-000003-39|L03 P19 C1
2222XC26-000003-40|L03 P19 C1
2222XC26-000003-41|L03 P19 C1
29H04-000029-UNI|L03 P19 C1
25P2-000039-XS|L03 P19 C2
25P2-000039-S|L03 P19 C2
25P2-000039-M|L03 P19 C2
25P2-000039-L|L03 P19 C2
25P2-000039-XL|L03 P19 C2
25P2-000039-XXL|L03 P19 C2
2021TR37-000005-S|L03 P19 C2
2021TR37-000005-M|L03 P19 C2
2021TR37-000005-XL|L03 P19 C2
2121SU27-000039-S|L03 P19 C3
2121SU27-000039-M|L03 P19 C3
2121SU27-000039-L|L03 P19 C3
2121SU27-000039-XL|L03 P19 C3
2121SU27-000039-XXL|L03 P19 C3
2212JA92-000301-S|L03 P19 C3
2212JA92-000301-M|L03 P19 C3
2212JA92-000301-XL|L03 P19 C3
2212JA92-000301-XXL|L03 P19 C3
25982-000043-XS|L03 P19 C4
25982-000043-S|L03 P19 C4
2321JA78-000001-S|L03 P19 C4
2321JA78-000001-L|L03 P19 C4
2321JA78-000001-XXL|L03 P19 C4
2321JA78-000001-3XL|L03 P19 C4
2322JA67-000003-XS|L03 P20 C1
2322JA67-000003-S|L03 P20 C1
2322JA67-000003-M|L03 P20 C1
2322JA67-000003-L|L03 P20 C1
2322JA67-000003-XL|L03 P20 C1
2425SU01-000039-4|L03 P20 C1
2425SU01-000039-6|L03 P20 C1
2425SU01-000039-8|L03 P20 C1
2425SU01-000039-10|L03 P20 C1
25975-000019-XS|L03 P20 C2
25975-000019-S|L03 P20 C2
25388-000005-S|L03 P20 C2
25388-000005-L|L03 P20 C2
25388-000005-XL|L03 P20 C2
2222XC10-000003-36|L03 P20 C3
2222XC10-000003-37|L03 P20 C3
2222XC10-000003-38|L03 P20 C3
2222XC10-000003-39|L03 P20 C3
2222XC10-000003-40|L03 P20 C3
2222XC10-000003-41|L03 P20 C3
2222TR14-000323-XS|L03 P20 C3
2222TR14-000323-S|L03 P20 C3
2222TR14-000323-M|L03 P20 C3
2222TR14-000323-XL|L03 P20 C3
2022JA79-000017-XS|L03 P20 C4
29159-000003-XS|L03 P20 C4
29159-000003-S|L03 P20 C4
29159-000003-M|L03 P20 C4
29159-000003-XXL|L03 P20 C4
2122JA91-000017-XS|L03 P21 C1
2122JA91-000017-S|L03 P21 C1
2122JA91-000017-M|L03 P21 C1
2122JA91-000017-L|L03 P21 C1
2122JA91-000017-XL|L03 P21 C1
2521SU13-000015-S|L03 P21 C1
2521SU13-000015-M|L03 P21 C1
2521SU13-000015-XL|L03 P21 C1
2521SU13-000015-XXL|L03 P21 C1
2422JA78-000039-M|L03 P21 C2
2422JA78-000039-L|L03 P21 C2
2422JA78-000039-XXL|L03 P21 C2
1921XC03-000005-40|L03 P21 C2
1921XC03-000005-41|L03 P21 C2
1921XC03-000005-43|L03 P21 C2
1921XC03-000005-44|L03 P21 C2
1921XC03-000005-45|L03 P21 C2
25101-000003-XS|L03 P21 C3
25101-000003-S|L03 P21 C3
25101-000003-M|L03 P21 C3
25101-000003-L|L03 P21 C3
25101-000003-XL|L03 P21 C3
25101-000003-XXL|L03 P21 C3
25378-000005-XL|L03 P21 C3
25378-000005-XXL|L03 P21 C3
25378-000005-3XL|L03 P21 C3
2012VS67-000003-XS|L03 P21 C4
2012VS67-000003-S|L03 P21 C4
2421TR72-000002-S|L03 P21 C4
2421TR72-000002-M|L03 P21 C4
2421TR72-000002-L|L03 P21 C4
2421TR72-000002-XL|L03 P21 C4
2421TR72-000002-XXL|L03 P21 C4
2022JA72-000017-XS|L03 P22 C1
2022JA72-000017-M|L03 P22 C1
2022TR25-000158-XS|L03 P22 C1
2022TR25-000158-S|L03 P22 C1
2022TR25-000158-M|L03 P22 C1
2022TR25-000158-L|L03 P22 C1
2022TR25-000158-XL|L03 P22 C1
29S9-000069-43|L03 P22 C2
29S9-000069-44|L03 P22 C2
29S9-000069-45|L03 P22 C2
2412SU05-000030-XS|L03 P22 C2
2412SU05-000030-S|L03 P22 C2
2412SU05-000030-M|L03 P22 C2
2412SU05-000030-L|L03 P22 C2
2412SU05-000030-XL|L03 P22 C2
2412SU05-000030-XXL|L03 P22 C2
26S42-000019-36|L03 P22 C3
26S42-000019-37|L03 P22 C3
26963-000015-XS|L03 P22 C3
26963-000015-S|L03 P22 C3
26963-000015-M|L03 P22 C3
1922TR45-000125-XS|L03 P22 C3
1922TR45-000125-S|L03 P22 C3
1922TR45-000125-M|L03 P22 C3
29SW02-000019-36|L03 P22 C4
29SW02-000019-38|L03 P22 C4
29SW02-000019-39|L03 P22 C4
29SW02-000019-40|L03 P22 C4
29SW02-000019-41|L03 P22 C4
2222JA67-000020-XS|L03 P22 C4
2222JA67-000020-S|L03 P22 C4
2222JA67-000020-M|L03 P22 C4
2222JA67-000020-L|L03 P22 C4
2222JA67-000020-XXL|L03 P22 C4
2121TR09-000027-S|L03 P22 C4
2121TR09-000027-M|L03 P22 C4
2212JA08-000003-XS|L03 P23 C1
2212JA08-000003-M|L03 P23 C1
2212JA08-000003-L|L03 P23 C1
2212JA08-000003-XL|L03 P23 C1
2212JA08-000003-XXL|L03 P23 C1
26384-000021-M|L03 P23 C1
26384-000021-XXL|L03 P23 C1
26384-000021-3XL|L03 P23 C1
2121TR32-000030-S|L03 P23 C1
2121TR32-000030-XXL|L03 P23 C1
1812JA97-000003-XS|L03 P23 C2
1812JA97-000003-S|L03 P23 C2
1812JA97-000003-XL|L03 P23 C2
2422TR69-000030-XS|L03 P23 C2
2422TR69-000030-S|L03 P23 C2
2422TR69-000030-M|L03 P23 C2
2422TR69-000030-L|L03 P23 C2
1911CC53-000006-S|L03 P23 C2
2322JA76-000015-XS|L03 P23 C3
2322JA76-000015-M|L03 P23 C3
2221JA05-000003-S|L03 P23 C3
2221JA05-000003-M|L03 P23 C3
1822PT11-000302-34|L03 P23 C3
1822PT11-000302-36|L03 P23 C3
1822PT11-000302-38|L03 P23 C3
1822PT11-000302-42|L03 P23 C3
1921XC02-000039-40|L03 P23 C4
1921XC02-000039-41|L03 P23 C4
1921XC02-000039-43|L03 P23 C4
1921XC02-000039-45|L03 P23 C4
24387-000128-XL|L03 P23 C4
24387-000128-XXL|L03 P23 C4
24387-000128-3XL|L03 P23 C4
2121CL55-000139-S|L03 P23 C4
2121CL55-000139-M|L03 P23 C4
2121CL55-000139-XL|L03 P23 C4
2121CL55-000139-XXL|L03 P23 C4
2121CL55-000139-3XL|L03 P23 C4
2221XC04-000019-40|L03 P24 C1
2221XC04-000019-41|L03 P24 C1
2221XC04-000019-42|L03 P24 C1
2221XC04-000019-43|L03 P24 C1
2221XC04-000019-45|L03 P24 C1
24373-000006-S|L03 P24 C1
24373-000006-M|L03 P24 C1
24373-000006-3XL|L03 P24 C1
2021CL56-000015-S|L03 P24 C1
2021CL56-000015-M|L03 P24 C1
2021CL56-000015-XXL|L03 P24 C1
2311JA03-000068-S|L03 P24 C2
26100-000139-XS|L03 P24 C2
26100-000139-S|L03 P24 C2
26100-000139-XXL|L03 P24 C2
26100-000139-3XL|L03 P24 C2
26975-000003-XS|L03 P24 C2
26975-000003-M|L03 P24 C2
2121TR03-000015-XL|L03 P24 C2
2121TR03-000015-XXL|L03 P24 C2
2421JA16-000014-S|L03 P24 C3
2421JA16-000014-M|L03 P24 C3
2421JA16-000014-L|L03 P24 C3
2421JA16-000014-XXL|L03 P24 C3
2412JA14-000003-M|L03 P24 C3
2412JA14-000003-L|L03 P24 C3
2412JA14-000003-XL|L03 P24 C3
2012TR09-000015-XS|L03 P24 C3
2012TR09-000015-S|L03 P24 C3
2012TR09-000015-L|L03 P24 C3
2012TR09-000015-XL|L03 P24 C3
2012TR09-000015-XXL|L03 P24 C3
26976-000014-XS|L03 P24 C3
26976-000014-XL|L03 P24 C3
2221JA51-000019-S|L03 P24 C4
2221JA51-000019-L|L03 P24 C4
2221JA51-000019-3XL|L03 P24 C4
1822VS21-000014-XS|L03 P24 C4
1822VS21-000014-S|L03 P24 C4
1822VS21-000014-M|L03 P24 C4
1822VS21-000014-L|L03 P24 C4
1822VS21-000014-XL|L03 P24 C4
1822VS21-000014-XXL|L03 P24 C4
25500-000015-XS|L03 P24 C4
25500-000015-S|L03 P24 C4
25500-000015-L|L03 P24 C4
1922JA91-000014-XS|L03 P24 C4
2222XC15-000003-36|L03 P18 C1
2222XC15-000003-37|L03 P18 C1
2222XC15-000003-38|L03 P18 C1
2222XC15-000003-39|L03 P18 C2
2222XC15-000003-40|L03 P18 C2
2222XC15-000003-41|L03 P18 C2
"""

Loc = env['stock.location']
Quant = env['stock.quant']
Prod = env['product.product']
Pick = env['stock.picking']
STOCK = Loc.browse(STOCK_ID)
NAVE2 = Loc.browse(NAVE2_ID)
msg = []

# ---- 0. que no s'hagi creat abans ----
prev = Pick.search([('company_id', '=', CO), ('origin', '=like', ORIGEN + '%'), ('state', '!=', 'cancel')])
if prev:
    log('PILOT %s: ja hi ha INT creats: %s' % (TRAMO, ', '.join(prev.mapped('name'))))
    raise Warning('Ja hi ha INT del pilot %s: %s' % (TRAMO, ', '.join(prev.mapped('name'))))

# ---- 1. dades: talla -> columna ----
dest_bc = {}
for ln in DATA.strip().split('\n'):
    p = ln.split('|')
    if len(p) == 2:
        dest_bc[p[0].strip()] = p[1].strip()

tbc = []
for pp in range(18, 25):
    for cc in range(1, 5):
        tbc.append('L03 P%02d C%d' % (pp, cc))
tcols = Loc.search([('barcode', 'in', tbc), ('company_id', '=', CO)])
col_by_bc = {}
for l in tcols:
    col_by_bc[l.barcode] = l
falten_cols = sorted(set(tbc) - set(col_by_bc.keys()))

prods = Prod.with_context(active_test=False).search([('name', 'in', list(dest_bc.keys())), '|', ('company_id', '=', CO), ('company_id', '=', False)])
by_name = {}
for p in prods:
    by_name.setdefault(p.name, []).append(p)
no_trobats = sorted(set(dest_bc.keys()) - set(by_name.keys()))
duplicats = sorted(filter(lambda n: len(by_name[n]) > 1, by_name.keys()))
dest_prod = {}
for n in by_name:
    if len(by_name[n]) == 1 and dest_bc[n] in col_by_bc:
        dest_prod[by_name[n][0].id] = col_by_bc[dest_bc[n]]
sel_ids = list(dest_prod.keys())

def columna(loc):
    # puja de la caixa KO_ a la columna "NNNNN - Lxx Pyy Cz"
    while loc and loc.location_id and loc.name and loc.name.startswith('KO_'):
        loc = loc.location_id
    return loc

def lineal(loc):
    n = loc.complete_name or ''
    i = n.find(' - L')
    if i < 0:
        return 0
    s = n[i + 4:i + 6]
    return int(s) if s.isdigit() else 0

# ---- 2. carro ----
carro = Loc.search([('barcode', '=', CARRO_BC), ('company_id', '=', CO)], limit=1)
wh = env['stock.warehouse'].search([('company_id', '=', CO), ('lot_stock_id', '=', STOCK_ID)], limit=1)

# ---- 3. B: estoc lliure dels models escollits ----
qb = Quant.search([('product_id', 'in', sel_ids), ('location_id', 'child_of', STOCK_ID), ('quantity', '>', 0)])
B = {}
for b in BLOQUES:
    B[b[2]] = []
ja_ok = 0
reserv_b = 0
reserv_b_txt = []
for q in qb:
    d = dest_prod[q.product_id.id]
    if q.location_id == d or (q.location_id.parent_path or '').startswith(d.parent_path or '-'):
        ja_ok += q.quantity
        continue
    lliure = q.quantity - q.reserved_quantity
    if q.reserved_quantity > 0:
        reserv_b += q.reserved_quantity
        reserv_b_txt.append('%s %s (%d)' % (q.product_id.name, columna(q.location_id).barcode or q.location_id.name, q.reserved_quantity))
    if lliure <= 0:
        continue
    li = lineal(q.location_id)
    for b in BLOQUES:
        if (li == 0 and b[0] == 0) or (li > 0 and b[0] <= li <= b[1]):
            B[b[2]].append((q.location_id, q.product_id, lliure))
            break

# ---- 4. A: el que hi ha al tram i no es queda ----
qa = Quant.search([('location_id', 'child_of', tcols.ids), ('quantity', '>', 0), ('product_id', 'not in', sel_ids)])
A = []
reserv_a = 0
sense_desti = 0
millor = {}
for q in qa:
    lliure = q.quantity - q.reserved_quantity
    reserv_a += q.reserved_quantity
    if lliure <= 0:
        continue
    pid = q.product_id.id
    if pid not in millor:
        alt = Quant.search([('product_id', '=', pid), ('location_id', 'child_of', STOCK_ID), '!', ('location_id', 'child_of', tcols.ids), ('quantity', '>', 0)])
        tot = {}
        for x in alt:
            c = columna(x.location_id)
            if c and lineal(c) > 0:
                tot[c.id] = tot.get(c.id, 0) + x.quantity
        millor[pid] = sorted(tot.keys(), key=lambda k: -tot[k])[0] if tot else False
    if not millor[pid]:
        sense_desti += lliure
    A.append((q.location_id, q.product_id, lliure, millor[pid]))

# ---- 5. C: del carro a la columna (per producte) ----
C = {}
for k in B:
    for t in B[k]:
        C[t[1].id] = C.get(t[1].id, 0) + t[2]

# ---- 6. resum ----
def uds(lst):
    s = 0
    for t in lst:
        s += t[2]
    return s
msg.append('PILOT %s · MODO %s' % (TRAMO, MODO))
msg.append('Talles a les dades: %d · productes trobats: %d · no trobats: %d · duplicats: %d · columnes que falten: %s' % (
    len(dest_bc), len(sel_ids), len(no_trobats), len(duplicats), ', '.join(falten_cols) or 'cap'))
msg.append('Carro %s: %s' % (CARRO_BC, carro.complete_name if carro else 'NO EXISTEIX (es crearia sota %s)' % (wh.view_location_id.complete_name if wh else '¿magatzem?')))
msg.append('A BUIDAR: %d linies, %d uds (sense desti: %d -> anirien al carro) · reservades al tram que NO es poden moure: %d' % (len(A), uds(A), sense_desti, reserv_a))
for b in BLOQUES:
    msg.append('%s: %d linies, %d uds' % (b[2], len(B[b[2]]), uds(B[b[2]])))
msg.append('Ja a la seva columna (no es mouen): %d uds · reservades per a altres albarans (no es mouen): %d' % (ja_ok, reserv_b))
msg.append('C UBICAR: %d productes, %d uds' % (len(C), sum(C.values())))
if no_trobats:
    msg.append('No trobats: ' + ', '.join(no_trobats[:15]))
if duplicats:
    msg.append('Duplicats: ' + ', '.join(duplicats[:15]))
if reserv_b_txt:
    msg.append('Reservades (mostra): ' + ', '.join(reserv_b_txt[:10]))

if MODO != 'REAL':
    log('\n'.join(msg))
    raise Warning('\n'.join(msg))

# ---- 7. REAL ----
if not carro:
    carro = Loc.create({'name': 'CARRO PILOT L03', 'barcode': CARRO_BC, 'usage': 'internal', 'company_id': CO, 'location_id': wh.view_location_id.id})

def moure(lst, nom, src, dst, assignar):
    # lst: (origen, producte, uds, desti)
    vals = []
    for t in lst:
        vals.append((0, 0, {'name': t[1].display_name, 'product_id': t[1].id, 'product_uom': t[1].uom_id.id, 'product_uom_qty': t[2],
                            'location_id': t[0].id, 'location_dest_id': t[3].id, 'company_id': CO}))
    if not vals:
        return False
    pk = Pick.create({'picking_type_id': PTYPE_ID, 'location_id': src.id, 'location_dest_id': dst.id, 'company_id': CO,
                      'origin': ORIGEN + ' ' + nom, 'move_ids_without_package': vals})
    pk.action_confirm()
    if assignar:
        pk.action_assign()
    return pk

creats = []
la = []
for t in A:
    la.append((t[0], t[1], t[2], Loc.browse(t[3]) if t[3] else carro))
pk = moure(la, 'A BUIDAR', STOCK, NAVE2, True)
if pk:
    creats.append(pk)
for b in BLOQUES:
    lb = []
    for t in B[b[2]]:
        lb.append((t[0], t[1], t[2], carro))
    pk = moure(lb, b[2], STOCK, carro, True)
    if pk:
        creats.append(pk)
lc = []
for pid in C:
    lc.append((carro, Prod.browse(pid), C[pid], dest_prod[pid]))
pk = moure(sorted(lc, key=lambda t: t[3].barcode or ''), 'C UBICAR', carro, NAVE2, False)
if pk:
    creats.append(pk)
res = []
for pk in creats:
    res.append('%s %s %s (%d uds, reservat %d)' % (pk.name, pk.origin, pk.state, sum(pk.move_lines.mapped('product_uom_qty')), sum(pk.move_line_ids.mapped('product_uom_qty'))))
log('PILOT %s REAL creats: %s' % (TRAMO, ' | '.join(res)))

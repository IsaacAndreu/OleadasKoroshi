# -*- coding: utf-8 -*-
# =============================================================================
# KOROSHI Recepción 1.6.0 (26/11/2026): lector del packing list en Excel que Mayte deja en cada IN
# («Detail_PL2160.xlsx»). Python puro (zipfile + xml), sin openpyxl ni xlrd: se prueba sin Odoo
# (tests/test_packing_xlsx.py).
#
# Forma de la hoja (IN/00379, 26/11):
#   fila 1 título; fila 2 «Proveedor: …»; fila 3 «Total: 1046 ctns / 20278 pcs | …»;
#   cabeceras: C/T NO. | COLOR | S | M | L | XL | XXL | 3XL | Q'TY/CTN | N.W./CTN | G.W./CTN | TTL N.W. | TTL G.W. |
#              L | W | H | CBM | CTNS | PCS | CBM/ud   (la primera «L» es talla; la segunda, el largo de la caja)
#   bloque por modelo-color: fila «2711JA12 — 000039 NAVY»; después filas de cajas («1», «2-4») con las uds por
#   talla (una caja mixta lleva varias tallas); cierran «Sub-total» y «CBM/ud»; al final «TOTAL».
#   La numeración de cajas empieza de nuevo en cada MODELO y sigue entre sus colores: caja física = (modelo, nº).
# =============================================================================
import io
import re
import zipfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NS_R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
RE_CAJAS = re.compile(r'^(\d+)\s*(?:[-–—]\s*(\d+))?$')
# «2711JA12 — 000039 NAVY»; en el de IN/00379 algunos colores vienen vacíos («2711JA12 —»)
RE_BLOQUE = re.compile(r'^([0-9A-Z]+)\s*[—–-]+\s*([0-9A-Z]*)\s*(.*)$')
RE_COL = re.compile(r'^([A-Z]+)')
MAX_CAJAS_FILA = 2000


def _col(ref):
    """«AB12» -> índice 0 de la columna (A=0)."""
    m = RE_COL.match(ref or '')
    n = 0
    for c in (m.group(1) if m else 'A'):
        n = n * 26 + (ord(c) - 64)
    return n - 1


def _texto(el):
    return ''.join(t.text or '' for t in el.iter(NS + 't'))


def filas_xlsx(datos):
    """Bytes de un .xlsx -> [[valores de la fila]] de la PRIMERA hoja (texto en línea, compartido o números)."""
    z = zipfile.ZipFile(io.BytesIO(datos))
    nombres = z.namelist()
    compartidos = []
    if 'xl/sharedStrings.xml' in nombres:
        raiz = ET.fromstring(z.read('xl/sharedStrings.xml'))
        compartidos = [_texto(si) for si in raiz.iter(NS + 'si')]
    hoja = 'xl/worksheets/sheet1.xml'
    try:      # la primera hoja del libro (por si no se llama sheet1)
        libro = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        primera = next(libro.iter(NS + 'sheet'))
        rid = primera.get(NS_R + 'id')
        for rel in rels:
            if rel.get('Id') == rid:
                destino = rel.get('Target').lstrip('/')
                hoja = destino if destino.startswith('xl/') else 'xl/' + destino
    except (KeyError, StopIteration, ET.ParseError):
        pass
    if hoja not in nombres:
        hoja = sorted(n for n in nombres if n.startswith('xl/worksheets/sheet'))[0]
    filas = []
    for row in ET.fromstring(z.read(hoja)).iter(NS + 'row'):
        valores = {}
        for i, c in enumerate(row.iter(NS + 'c')):
            tipo = c.get('t')
            idx = _col(c.get('r')) if c.get('r') else i
            if tipo == 'inlineStr':
                v = _texto(c)
            else:
                ve = c.find(NS + 'v')
                v = ve.text if ve is not None else ''
                if tipo == 's' and v != '':
                    v = compartidos[int(v)]
            valores[idx] = (v or '').strip()
        if valores:
            fila = [''] * (max(valores) + 1)
            for k, v in valores.items():
                fila[k] = v
            filas.append(fila)
        else:
            filas.append([])
    return filas


def _num(v):
    try:
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return 0.0


def _norm(t):
    return ''.join((t or '').split()).upper().replace('’', "'")


def leer_packing(filas):
    """[[celdas]] -> {'cajas': [{'modelo','color','color_nombre','caja','tallas': {talla: uds},'uds','qty_ctn',
    'largo','ancho','alto','cbm_caja','cbm_ud'}], 'total_cajas', 'total_uds', 'avisos': [..]}. Una entrada por caja
    física; un rango «2-4» son tres cajas iguales. Lanza ValueError si no encuentra la cabecera."""
    cab = None
    for i, f in enumerate(filas):
        if f and _norm(f[0]) in ('C/TNO.', 'C/TNO', 'CTNO.', 'C/T'):
            cab = i
            break
    if cab is None:
        raise ValueError('No encuentro la cabecera «C/T NO.» en el Excel del packing list.')
    h = [_norm(x) for x in filas[cab]]
    try:
        i_color = h.index('COLOR')
        i_qty = next(i for i, x in enumerate(h) if x.startswith("Q'TY") or x.startswith('QTY'))
    except (ValueError, StopIteration):
        raise ValueError('La cabecera del packing list no tiene COLOR o Q\'TY/CTN.')
    tallas = [(i, filas[cab][i].strip()) for i in range(i_color + 1, i_qty) if h[i]]

    def despues(nombre):
        for i in range(i_qty + 1, len(h)):
            if h[i] == nombre:
                return i
        return None
    i_l, i_w, i_h = despues('L'), despues('W'), despues('H')
    i_cbm, i_ctns, i_cbm_ud = despues('CBM'), despues('CTNS'), despues('CBM/UD')

    def celda(f, i):
        return f[i] if (i is not None and i < len(f)) else ''

    cajas, avisos = [], []
    modelo = color = color_nombre = None
    for f in filas[cab + 1:]:
        a = (f[0] if f else '').strip()
        if not a:
            continue
        au = a.upper()
        m = RE_CAJAS.match(a)
        if m:
            if not modelo:
                avisos.append('Cajas «%s» sin modelo encima: no se cuentan.' % a)
                continue
            desde = int(m.group(1))
            hasta = int(m.group(2) or desde)
            if hasta < desde or hasta - desde > MAX_CAJAS_FILA:
                avisos.append('Rango de cajas raro «%s» en %s: no se cuenta.' % (a, modelo))
                continue
            n = hasta - desde + 1
            por_talla = {}
            for i, t in tallas:
                u = int(round(_num(celda(f, i))))
                if u > 0:
                    por_talla[t] = u
            ctns = _num(celda(f, i_ctns)) or n
            cbm_fila = _num(celda(f, i_cbm))           # el CBM de la fila es el de todas sus cajas
            cbm_caja = (cbm_fila / ctns) if ctns else cbm_fila
            uds = sum(por_talla.values()) or int(_num(celda(f, i_qty)))
            for caja in range(desde, hasta + 1):
                cajas.append({
                    'modelo': modelo, 'color': color, 'color_nombre': color_nombre, 'caja': caja,
                    'tallas': dict(por_talla), 'uds': uds,
                    'qty_ctn': _num(celda(f, i_qty)), 'largo': _num(celda(f, i_l)), 'ancho': _num(celda(f, i_w)),
                    'alto': _num(celda(f, i_h)), 'cbm_caja': cbm_caja,
                    # en las filas de caja la columna CBM/ud viene vacía (solo en Sub-total): se calcula
                    'cbm_ud': _num(celda(f, i_cbm_ud)) or ((cbm_caja / uds) if uds else 0.0),
                })
            continue
        if au.startswith('SUB') or au.startswith('TOTAL') or au.startswith('CBM'):
            continue
        b = RE_BLOQUE.match(au)
        if b:
            modelo, color, color_nombre = b.group(1), b.group(2), (a[b.start(3):] if b.group(3) else '').strip()
    vistas = {}
    for c in cajas:
        clave = (c['modelo'], c['caja'])
        if clave in vistas:
            avisos.append('La caja %d de %s sale dos veces en el packing list.' % (c['caja'], c['modelo']))
        vistas[clave] = True
    return {'cajas': cajas, 'total_cajas': len(vistas), 'total_uds': sum(c['uds'] for c in cajas), 'avisos': avisos}


def contenido_texto(tallas):
    """{'S': 23, '3XL': 20} -> «23 S + 20 3XL»."""
    return ' + '.join('%d %s' % (u, t) for t, u in tallas.items())

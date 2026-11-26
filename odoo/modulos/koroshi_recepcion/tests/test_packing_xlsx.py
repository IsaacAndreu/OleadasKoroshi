# -*- coding: utf-8 -*-
# Pruebas del lector del Excel del packing list (1.6.0), sin Odoo:
#   python odoo/modulos/koroshi_recepcion/tests/test_packing_xlsx.py
import io
import os
import sys
import unittest
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import packing_xlsx as P  # noqa: E402

CAB = ['C/T NO.', 'COLOR', 'S', 'M', 'L', 'XL', 'XXL', '3XL', "Q'TY/CTN", 'N.W./CTN', 'G.W./CTN', 'TTL N.W.',
       'TTL G.W.', 'L', 'W', 'H', 'CBM', 'CTNS', 'PCS', 'CBM/ud']


def _letra(i):
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx(filas, compartidas=False):
    """Un .xlsx mínimo como el de Mayte (texto en línea) o con sharedStrings."""
    tabla = []
    xml_filas = []
    for n, fila in enumerate(filas, 1):
        celdas = []
        for i, v in enumerate(fila):
            if v in (None, ''):
                continue
            ref = '%s%d' % (_letra(i), n)
            if isinstance(v, (int, float)):
                celdas.append('<c r="%s"><v>%s</v></c>' % (ref, v))
            elif compartidas:
                tabla.append(v)
                celdas.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, len(tabla) - 1))
            else:
                celdas.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, escape(v)))
        xml_filas.append('<row r="%d">%s</row>' % (n, ''.join(celdas)))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    b = io.BytesIO()
    z = zipfile.ZipFile(b, 'w')
    z.writestr('xl/workbook.xml', '<workbook %s xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
                                  'relationships"><sheets><sheet name="Detail PL2160" sheetId="1" r:id="rId1"/>'
                                  '</sheets></workbook>' % ns)
    z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
               'relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="x"/></Relationships>')
    z.writestr('xl/worksheets/sheet1.xml', '<worksheet %s><sheetData>%s</sheetData></worksheet>'
               % (ns, ''.join(xml_filas)))
    if compartidas:
        z.writestr('xl/sharedStrings.xml', '<sst %s>%s</sst>' % (ns, ''.join(
            '<si><t>%s</t></si>' % escape(t) for t in tabla)))
    z.close()
    return b.getvalue()


FILAS = [
    ['Detail PL2160'], ['Proveedor: X'], ['Total: 6 ctns / 223 pcs | GW 1 | CBM 1'],
    CAB,
    ['2711JA12 — 000039 NAVY'],
    ['1', '', 0, 0, 40, 0, 0, 0, 40, 0, 0, 0, 0, 60, 40, 35, 0.084, 1, 40, 0.0021],
    ['2-4', '', 0, 40, 0, 0, 0, 0, 40, 0, 0, 0, 0, 60, 40, 35, 0.252, 3, 120, 0.0021],
    ['Sub-total'], ['CBM/ud'],
    ['2711JA12 —'],                                   # así viene en IN/00379: color vacío
    ['5', '', 23, 0, 0, 0, 0, 20, 43, 0, 0, 0, 0, 60, 40, 35, 0.086, 1, 43, ''],
    ['Sub-total'],
    ['2711JA13 – 000010 ROJO'],
    ['1', '', 0, 0, 0, 20, 0, 0, 20, 0, 0, 0, 0, 50, 40, 30, 0.06, 1, 20, 0.003],
    ['TOTAL'],
]


class TestPacking(unittest.TestCase):
    def test_leer(self):
        for compartidas in (False, True):
            r = P.leer_packing(P.filas_xlsx(xlsx(FILAS, compartidas)))
            self.assertEqual(r['total_cajas'], 6, compartidas)
            self.assertEqual(r['total_uds'], 40 + 120 + 43 + 20)
            c = {(x['modelo'], x['caja']): x for x in r['cajas']}
            self.assertEqual(c[('2711JA12', 1)]['tallas'], {'L': 40})       # la 1.ª «L» es talla
            self.assertEqual(c[('2711JA12', 1)]['largo'], 60)               # la 2.ª «L», el largo
            self.assertEqual(c[('2711JA12', 3)]['tallas'], {'M': 40})       # rango 2-4
            self.assertAlmostEqual(c[('2711JA12', 3)]['cbm_caja'], 0.084)
            self.assertEqual(c[('2711JA12', 5)]['color'], '')               # sigue la numeración del modelo
            self.assertAlmostEqual(c[('2711JA12', 5)]['cbm_ud'], 0.086 / 43)  # CBM/ud vacío: se calcula
            self.assertEqual(P.contenido_texto(c[('2711JA12', 5)]['tallas']), '23 S + 20 3XL')
            self.assertEqual(c[('2711JA13', 1)]['color_nombre'], 'ROJO')    # otro modelo empieza en 1
            self.assertEqual(r['avisos'], [])

    def test_sin_cabecera(self):
        with self.assertRaises(ValueError):
            P.leer_packing([['hola'], ['adios']])

    def test_repetida(self):
        filas = FILAS[:6] + [['1', '', 0, 0, 40, 0, 0, 0, 40]]
        r = P.leer_packing(P.filas_xlsx(xlsx(filas)))
        self.assertEqual(r['total_cajas'], 1)
        self.assertTrue(r['avisos'])


if __name__ == '__main__':
    unittest.main()

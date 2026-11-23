# -*- coding: utf-8 -*-
# Pruebas de logica.py sin Odoo:  python odoo/modulos/koroshi_recepcion/tests/test_logica.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logica as L  # noqa: E402


class TestReferencia(unittest.TestCase):
    def test_partes(self):
        self.assertEqual(L.partes_referencia('2711JA43-000062-S'), ('2711JA43', '000062', 'S'))
        self.assertEqual(L.partes_referencia('2711SU06-000015-XXL'), ('2711SU06', '000015', 'XXL'))
        self.assertEqual(L.partes_referencia('RARO'), ('RARO', '', ''))
        self.assertEqual(L.partes_referencia(None), ('', '', ''))

    def test_tallas(self):
        tallas = ['XL', '12', 'S', '3XL', 'M', '2', 'XXL', 'L', 'U']
        self.assertEqual(sorted(tallas, key=L.clave_talla), ['S', 'M', 'L', 'XL', 'XXL', '3XL', '2', '12', 'U'])


class TestPalets(unittest.TestCase):
    def test_nombres(self):
        self.assertEqual(L.nombres_palets(2), ['PAL-01 A', 'PAL-01 B', 'PAL-02 A', 'PAL-02 B'])
        self.assertEqual(len(L.nombres_palets(30)), 60)
        with self.assertRaises(ValueError):
            L.nombres_palets(0)
        with self.assertRaises(ValueError):
            L.nombres_palets(100)

    def test_leer(self):
        for codigo in ('PAL-03 A', 'pal3a', 'PAL-3-a', 'PAL 03 A', 'PAL03A'):
            self.assertEqual(L.palet_de(codigo), 'PAL-03 A', codigo)
        self.assertEqual(L.palet_de('PAL-12 B'), 'PAL-12 B')
        self.assertIsNone(L.palet_de('PAL-03 C'))
        self.assertIsNone(L.palet_de('PAL-00 A'))
        self.assertIsNone(L.palet_de('KO_231126_001'))
        self.assertEqual(L.numero_palet('PAL-07 B'), (7, 'B'))


class TestBuscador(unittest.TestCase):
    def test_final_ean(self):
        self.assertTrue(L.es_final_ean('8136'))
        self.assertTrue(L.es_final_ean(' 813 '))
        self.assertFalse(L.es_final_ean('81'))
        self.assertFalse(L.es_final_ean('2711JA'))
        self.assertFalse(L.es_final_ean('8435566898136'))

    def test_cantidad(self):
        self.assertEqual(L.cantidad_valida('12'), 12)
        self.assertEqual(L.cantidad_valida('12,0'), 12)
        for mal in ('', 'x', '0', '-3', '1,5', '6000'):
            with self.assertRaises(ValueError):
                L.cantidad_valida(mal)


class TestComparar(unittest.TestCase):
    def test_estados(self):
        r = L.comparar({'a': 10, 'b': 5, 'c': 3}, {'a': 10, 'b': 7, 'd': 2})
        self.assertEqual(r['a'], (10, 10, 0, 'ok'))
        self.assertEqual(r['b'], (5, 7, 2, 'sobra'))
        self.assertEqual(r['c'], (3, 0, -3, 'falta'))
        self.assertEqual(r['d'], (0, 2, 2, 'no_venia'))


class TestRepartir(unittest.TestCase):
    def test_justo(self):
        lineas, sin = L.repartir([('m1', 'a', 10)], [('l1', 'a', 'KO1', 6), ('l2', 'a', 'KO2', 4)])
        self.assertEqual(lineas, [('m1', 'KO1', 6, ['l1']), ('m1', 'KO2', 4, ['l2'])])
        self.assertEqual(sin, [])

    def test_dos_in_por_orden(self):
        # el artículo viene en dos IN: se llena primero la primera
        lineas, _ = L.repartir([('m1', 'a', 5), ('m2', 'a', 5)], [('l1', 'a', 'KO1', 7)])
        self.assertEqual(lineas, [('m1', 'KO1', 5, ['l1']), ('m2', 'KO1', 2, ['l1'])])

    def test_misma_caja_se_suma(self):
        lineas, _ = L.repartir([('m1', 'a', 20)], [('l1', 'a', 'KO1', 6), ('l2', 'a', 'KO1', 4)])
        self.assertEqual(lineas, [('m1', 'KO1', 10, ['l1', 'l2'])])

    def test_sobra_al_ultimo(self):
        lineas, _ = L.repartir([('m1', 'a', 5), ('m2', 'a', 5)], [('l1', 'a', 'KO1', 12)])
        self.assertEqual(lineas, [('m1', 'KO1', 5, ['l1']), ('m2', 'KO1', 7, ['l1'])])

    def test_no_venia(self):
        lineas, sin = L.repartir([('m1', 'a', 5)], [('l1', 'b', 'KO1', 3), ('l2', 'a', 'KO1', 2)])
        self.assertEqual(lineas, [('m1', 'KO1', 2, ['l2'])])
        self.assertEqual(sin, ['l1'])

    def test_pendiente_cero(self):
        # un movimiento ya lleno (0 pendiente): todo va al último como sobra
        lineas, _ = L.repartir([('m1', 'a', 0)], [('l1', 'a', 'KO1', 3)])
        self.assertEqual(lineas, [('m1', 'KO1', 3, ['l1'])])


class TestCsv(unittest.TestCase):
    def test_celdas(self):
        self.assertEqual(L.csv_texto([['a;b', 1.5, None, 'x"y']]), '"a;b";1,5;;"x""y"\r\n')


if __name__ == '__main__':
    unittest.main()

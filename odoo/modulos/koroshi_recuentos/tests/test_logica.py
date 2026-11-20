# -*- coding: utf-8 -*-
# Pruebas sin Odoo: python odoo/modulos/koroshi_recuentos/tests/test_logica.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logica  # noqa: E402


class TestLogica(unittest.TestCase):

    def test_modelo(self):
        self.assertEqual(logica.modelo_de('2621XC04'), '2621XC04')
        self.assertEqual(logica.modelo_de(' 2621xc04-000014-42 '), '2621XC04')
        self.assertEqual(logica.modelo_de(''), '')

    def test_partes(self):
        self.assertEqual(logica.partes('2622JA00-000003-L'), ('2622JA00', '000003', 'L'))
        self.assertEqual(logica.partes('2621XC04-000014-42'), ('2621XC04', '000014', '42'))
        self.assertEqual(logica.partes('2621XC04-42'), ('2621XC04', '', '42'))
        self.assertEqual(logica.partes('2621XC04'), ('2621XC04', '', ''))

    def test_tallas(self):
        tallas = ['XL', '3XL', 'S', 'M', 'XXL', 'L', 'XS']
        self.assertEqual(sorted(tallas, key=logica.clave_talla), ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'])
        self.assertEqual(sorted(['44', '38', '40', '42/44'], key=logica.clave_talla), ['38', '40', '42/44', '44'])
        self.assertEqual(sorted(['40', 'M', 'RARA'], key=logica.clave_talla), ['M', '40', 'RARA'])

    def test_recorrido(self):
        huecos = ['FALTANTE', 'MU-01 P00 C1', '21995 - L128 P15 C2', '07828 - L94 P35 C1', '07828 - L94 P03 C2',
                  '07828 - L94 P03 C1']
        self.assertEqual(sorted(huecos, key=logica.clave_recorrido), [
            '07828 - L94 P03 C1', '07828 - L94 P03 C2', '07828 - L94 P35 C1', '21995 - L128 P15 C2',
            'MU-01 P00 C1', 'FALTANTE'])

    def test_hueco_corto(self):
        self.assertEqual(logica.hueco_corto('21995 - L128 P15 C2'), 'L128 P15 C2')
        self.assertEqual(logica.hueco_corto('MU-01 P00 C1'), 'MU-01 P00 C1')


if __name__ == '__main__':
    unittest.main()

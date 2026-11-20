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

    def test_decidir(self):
        d = logica.decidir
        # cuadra a la primera (los ceros no cuentan)
        self.assertEqual(d(1, [{1: 4}], {1: 4, 2: 0}), ('cuadra', None))
        self.assertEqual(d(1, [{}], {}), ('cuadra', None))
        # no cuadra -> 2.ª; la 2.ª igual que la 1.ª -> confirmada
        self.assertEqual(d(1, [{1: 0}], {1: 11}), ('releer', 2))
        self.assertEqual(d(2, [{}, {}], {1: 11}), ('confirmada', None))
        # la 2.ª cuadra con Odoo (la 1.ª se leyó mal) -> cuadra
        self.assertEqual(d(2, [{1: 3}, {1: 4}], {1: 4}), ('cuadra', None))
        # 2.ª distinta -> 3.ª; la 3.ª igual a la 1.ª o a la 2.ª -> confirmada; distinta de todas -> jefe
        self.assertEqual(d(2, [{1: 3}, {1: 2}], {1: 4}), ('releer', 3))
        self.assertEqual(d(3, [{1: 3}, {1: 2}, {1: 3}], {1: 4}), ('confirmada', None))
        self.assertEqual(d(3, [{1: 3}, {1: 2}, {1: 2}], {1: 4}), ('confirmada', None))
        self.assertEqual(d(3, [{1: 3}, {1: 2}, {1: 1}], {1: 4}), ('para_jefe', None))
        # Odoo en negativo nunca cuadra con una lectura
        self.assertEqual(d(1, [{1: 0}], {1: -4}), ('releer', 2))

    def test_hueco_corto(self):
        self.assertEqual(logica.hueco_corto('21995 - L128 P15 C2'), 'L128 P15 C2')
        self.assertEqual(logica.hueco_corto('MU-01 P00 C1'), 'MU-01 P00 C1')


if __name__ == '__main__':
    unittest.main()

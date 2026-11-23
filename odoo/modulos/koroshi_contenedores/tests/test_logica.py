# -*- coding: utf-8 -*-
# Pruebas sin Odoo: python odoo/modulos/koroshi_contenedores/tests/test_logica.py
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import logica  # noqa: E402


class TestRepartir(unittest.TestCase):

    def test_solo_la_diferencia(self):
        # R1: línea de 5 reservada y hay 4: pasa 1, no 5
        self.assertEqual(logica.repartir([5], 1), [1])

    def test_ko_241026_115(self):
        # 2 uds reservadas que no están (de 2621PT01-000014-34): «Cambiar» a 0 de ese artículo
        self.assertEqual(logica.repartir([2], 2), [2])

    def test_pequenas_primero(self):
        # la línea de 1 pasa entera; la de 5 no se toca
        self.assertEqual(logica.repartir([1, 5], 1), [1, 0])

    def test_reparto_en_dos(self):
        self.assertEqual(logica.repartir([1, 3], 2), [1, 1])

    def test_nada_que_quitar(self):
        self.assertEqual(logica.repartir([2, 3], 0), [0, 0])

    def test_poner_a_cero_todas_enteras(self):
        self.assertEqual(logica.repartir([2, 3], 5), [2, 3])
        self.assertEqual(logica.repartir([2, 3], 99), [2, 3])

    def test_nunca_mas_de_lo_que_sobra(self):
        r = logica.repartir([0.5, 1.5, 4], 1.7)
        self.assertAlmostEqual(sum(r), 1.7)
        self.assertTrue(all(q <= c for q, c in zip(r, [0.5, 1.5, 4])))

    def test_sin_lineas(self):
        self.assertEqual(logica.repartir([], 3), [])

    def test_linea_a_cero(self):
        self.assertEqual(logica.repartir([0, 2], 1), [0, 1])


if __name__ == '__main__':
    unittest.main()

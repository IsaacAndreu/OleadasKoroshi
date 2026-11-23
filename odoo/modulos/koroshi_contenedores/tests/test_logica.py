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


class TestCambiarArticulo(unittest.TestCase):
    # v1.14.0 (R23): «Es otro»

    def test_modelo_quita_la_talla(self):
        self.assertEqual(logica.modelo('2621PT01-000014-34'), '2621PT01-000014')
        self.assertEqual(logica.modelo('[2621PT01-000014-34] 2621PT01-000014-34'), '2621PT01-000014')
        self.assertEqual(logica.modelo('2622ja00-000003-l'), '2622JA00-000003')

    def test_modelo_sin_forma_de_referencia(self):
        self.assertEqual(logica.modelo('CAMISETA'), 'CAMISETA')
        self.assertEqual(logica.modelo('A-B'), 'A-B')
        self.assertEqual(logica.modelo(''), '')

    def test_mismo_modelo(self):
        self.assertTrue(logica.mismo_modelo('2621PT01-000014-34', '2621PT01-000014-36'))
        self.assertTrue(logica.mismo_modelo('2622JA00-000003-L', '[2622JA00-000003-M] 2622JA00-000003-M'))
        self.assertFalse(logica.mismo_modelo('2621PT01-000014-34', '2621PT01-000015-34'))
        self.assertFalse(logica.mismo_modelo('', ''))

    def test_error_uds(self):
        self.assertEqual(logica.error_uds_cambio(3, 5, 500), '')
        self.assertEqual(logica.error_uds_cambio(5, 5, 500), '')
        self.assertIn('1 o más', logica.error_uds_cambio(0, 5, 500))
        self.assertIn('1 o más', logica.error_uds_cambio(None, 5, 500))
        self.assertIn('Solo hay 5', logica.error_uds_cambio(6, 5, 500))
        self.assertIn('Más de 500', logica.error_uds_cambio(501, 600, 500))

    def test_reservas_libres_no_tocan(self):
        # 5 uds, 2 reservadas: cambiar 3 deja 2 de A, que cubren las 2 reservadas
        self.assertEqual(logica.reservas_a_faltantes(3, 5, 2), 0)

    def test_reservas_que_no_caben(self):
        # 5 uds, 4 reservadas: cambiar 3 deja 2 de A: 2 reservadas pasan a Faltantes
        self.assertEqual(logica.reservas_a_faltantes(3, 5, 4), 2)
        # todas son B: todo lo reservado pasa
        self.assertEqual(logica.reservas_a_faltantes(5, 5, 4), 4)

    def test_sin_reservas(self):
        self.assertEqual(logica.reservas_a_faltantes(5, 5, 0), 0)


if __name__ == '__main__':
    unittest.main()

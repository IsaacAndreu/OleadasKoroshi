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


class TestRondaCajasCero(unittest.TestCase):
    """v1.16.0: retirar cajas a 0."""

    def test_rango(self):
        self.assertEqual(logica.rango_lineales('44-136'), (44, 136))
        self.assertEqual(logica.rango_lineales('L1 - L43'), (1, 43))
        self.assertEqual(logica.rango_lineales('136-44'), (44, 136))
        self.assertEqual(logica.rango_lineales(''), (44, 136))
        self.assertEqual(logica.rango_lineales('todo'), (44, 136))

    def test_lineal_de(self):
        self.assertEqual(logica.lineal_de('07828 - L67 P16 C1'), 67)
        self.assertEqual(logica.lineal_de('L200 P00 C1'), 200)
        self.assertIsNone(logica.lineal_de('MU-01 P00 C1'))
        self.assertIsNone(logica.lineal_de('KO_090726_030'))
        self.assertIsNone(logica.lineal_de(''))

    def test_orden_hueco(self):
        huecos = ['07828 - L67 P10 C1', '07828 - L67 P2 C2', '07828 - L67 P2 C1', '07828 - L66 P40 C1']
        self.assertEqual(sorted(huecos, key=logica.orden_hueco),
                         ['07828 - L66 P40 C1', '07828 - L67 P2 C1', '07828 - L67 P2 C2', '07828 - L67 P10 C1'])

    def test_clasificar(self):
        self.assertEqual(logica.clasificar(0, 0, 0, False), 'cero')
        self.assertEqual(logica.clasificar(0, 0, 0, True), 'abierta')
        self.assertEqual(logica.clasificar(2, 0, 0, False), 'stock')
        self.assertEqual(logica.clasificar(1, 1, 0, False), 'revisar')     # stock negativo
        self.assertEqual(logica.clasificar(1, 0, 1, True), 'revisar')      # reservado sin cantidad

    def test_ids_tarjetas(self):
        self.assertEqual(logica.ids_tarjetas('12, 34; 56'), {12, 34, 56})
        self.assertEqual(logica.ids_tarjetas(''), set())
        self.assertEqual(logica.ids_tarjetas(None), set())

    def test_con_prendas_pendiente(self):
        self.assertFalse(logica.con_prendas_pendiente(None, None))
        self.assertTrue(logica.con_prendas_pendiente(10, None))
        self.assertTrue(logica.con_prendas_pendiente(10, 5))        # marcada después del último cambio
        self.assertFalse(logica.con_prendas_pendiente(10, 12))      # ya se resolvió

    def test_repartir_encontrados(self):
        # KO_090726_045: 1 prenda y un faltante de 1 de esa caja: encontrado, sin ajuste
        self.assertEqual(logica.repartir_encontrados(1, [(7, 1)]), ([7], 0.0))
        # 3 prendas, faltantes de 1 y 1: los dos encontrados y 1 ud de ajuste +
        self.assertEqual(logica.repartir_encontrados(3, [(7, 1), (8, 1)]), ([7, 8], 1.0))
        # un faltante de 2 con 1 prenda: no se parte; ajuste + de 1
        self.assertEqual(logica.repartir_encontrados(1, [(7, 2)]), ([], 1.0))
        # el de 2 no cabe, el de 1 sí
        self.assertEqual(logica.repartir_encontrados(1, [(7, 2), (8, 1)]), ([8], 0.0))
        self.assertEqual(logica.repartir_encontrados(2, []), ([], 2.0))


if __name__ == '__main__':
    unittest.main()

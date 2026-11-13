# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor import volumen  # noqa: E402


class TestVolumen(unittest.TestCase):
    def setUp(self):
        self.m = volumen.Medidas()

    def test_valores_v12f(self):
        self.assertEqual(self.m.litros_caja, 80.0)
        self.assertEqual(self.m.cierre_min, 0.8)
        self.assertEqual(self.m.litros_tipo['JA'], 8.0)
        self.assertEqual(self.m.litros_defecto, 3.0)

    def test_litros_ud_volumen_manda(self):
        self.assertAlmostEqual(volumen.litros_ud(0.005, '2421JA14-XX', self.m), 5.0)

    def test_litros_ud_tabla_y_defecto(self):
        self.assertEqual(volumen.litros_ud(0.0, '2421JA14-XX', self.m), 8.0)
        self.assertEqual(volumen.litros_ud(None, '2421QQ14', self.m), 3.0)
        self.assertEqual(volumen.litros_ud(0.0, '', self.m), 3.0)

    def test_cajas_de(self):
        self.assertEqual(volumen.cajas_de(0.0, self.m), 1)
        self.assertEqual(volumen.cajas_de(80.0, self.m), 1)
        self.assertEqual(volumen.cajas_de(80.0005, self.m), 1)   # tolerancia de la v12f
        self.assertEqual(volumen.cajas_de(80.01, self.m), 2)
        self.assertEqual(volumen.cajas_de(240.0, self.m), 3)

    def test_cerrada(self):
        self.assertTrue(volumen.cerrada(0.0, self.m))
        self.assertTrue(volumen.cerrada(64.0, self.m))
        self.assertFalse(volumen.cerrada(63.9, self.m))
        self.assertTrue(volumen.cerrada(80.0 + 64.0, self.m))
        self.assertFalse(volumen.cerrada(80.0 + 10.0, self.m))

    def test_caja_llena(self):
        self.assertTrue(volumen.caja_llena(64.0, self.m))
        self.assertFalse(volumen.caja_llena(40.0, self.m))
        self.assertFalse(volumen.caja_llena(0.0, self.m))


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
# Tests de calculo_prevision.py sin Odoo. Desde la carpeta del modulo: python -m unittest discover -s tests
# (No hay tests/__init__.py a proposito: no son tests de Odoo.)
import importlib.util
import os
import unittest

_RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'calculo_prevision.py')
_spec = importlib.util.spec_from_file_location('calculo_prevision', _RUTA)
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

# Fichas "dia completo" reales (volumen m3, cajas) del 20/10 al 13/11/2026, leidas el 15/11
REALES = [(35.64, 438), (27.48, 342), (24.582, 375), (23.475, 309), (28.492, 332), (8.812, 133), (14.424, 179),
          (8.941, 122), (7.771, 107), (23.0, 292), (31.825, 437), (29.955, 418), (28.797, 333), (42.7, 546),
          (4.495, 59), (39.882, 477), (39.389, 492), (38.907, 481), (4.227, 84), (16.187, 208)]


class TestPrevision(unittest.TestCase):

    def test_factor_con_los_dias_reales(self):
        factor, n = cp.factor_calibrado(REALES)
        self.assertEqual(n, 20)
        self.assertGreater(factor, 1.0)
        self.assertLess(factor, 1.15)

    def test_dias_pequenos_no_calibran(self):
        factor, n = cp.factor_calibrado([(4.227, 49), (1.0, 10)] * 5)
        self.assertEqual((factor, n), (cp.FACTOR_DEFECTO, 0))

    def test_pocos_dias_factor_por_defecto(self):
        self.assertEqual(cp.factor_calibrado(REALES[:4]), (cp.FACTOR_DEFECTO, 4))
        self.assertEqual(cp.factor_calibrado([]), (cp.FACTOR_DEFECTO, 0))

    def test_sin_volumen_no_cuenta(self):
        self.assertEqual(cp.factor_calibrado([(0, 300), (None, 300)] * 5)[1], 0)

    def test_cajas_previstas(self):
        self.assertEqual(cp.cajas_previstas(0, 1.07), 0)
        self.assertEqual(cp.cajas_previstas(None, 1.07), 0)
        self.assertEqual(cp.cajas_previstas(0.084, 1.0), 1)
        # 13/11: las OUT de Z-1311 tenian 15,32 m3 y salieron 199 cajas
        self.assertEqual(cp.cajas_previstas(15.32, 1.07), 195)

    def test_acierto_con_los_dias_reales(self):
        # con el factor calibrado (1,077), de los 14 dias normales (>= 200 cajas) 13 quedan dentro de +-10 %; el
        # que no, el 22/10 (+19 %). Ninguno pasa del 20 %.
        factor = cp.factor_calibrado(REALES)[0]
        desvios = [cp.desvio(cajas, cp.cajas_previstas(vol, factor)) for vol, cajas in REALES if cajas >= 200]
        self.assertEqual(len(desvios), 14)
        self.assertLessEqual(len([d for d in desvios if abs(d) > 10]), 1, desvios)
        self.assertTrue(all(abs(d) < 20 for d in desvios), desvios)

    def test_desvio(self):
        self.assertIsNone(cp.desvio(100, 0))
        self.assertEqual(cp.desvio(110, 100), 10.0)
        self.assertEqual(cp.desvio(90, 100), -10.0)

    def test_mediana(self):
        self.assertIsNone(cp.mediana([]))
        self.assertEqual(cp.mediana([3, 1, 2]), 2)
        self.assertEqual(cp.mediana([4, 1, 2, 3]), 2.5)


if __name__ == '__main__':
    unittest.main()

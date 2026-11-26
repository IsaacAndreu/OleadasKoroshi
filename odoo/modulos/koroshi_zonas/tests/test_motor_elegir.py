# -*- coding: utf-8 -*-
# =============================================================================
# v1.9.0: motor/elegir.py. Cuantas zonas de lineal: la que acaba antes (con menos zonas si acaba casi igual).
# =============================================================================
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, AQUI)

from motor import elegir  # noqa: E402
from motor import v12f  # noqa: E402
import sintetico  # noqa: E402


class TestElegir(unittest.TestCase):

    def test_candidatos(self):
        self.assertEqual(elegir.candidatos('5, 3,4;4, x, 12'), [3, 4, 5])
        self.assertEqual(elegir.candidatos(''), [])

    def test_elige_la_que_acaba_antes(self):
        datos = sintetico.generar(21, n_pedidos=120)
        cam = {'MODO': 'REAL'}
        total, opciones = elegir.elegir(datos, cam, {}, [2, 3, 4], margen=0)
        self.assertEqual([o['lineal'] for o in opciones], [2, 3, 4])
        fin = dict((o['zonas'], o['fin']) for o in opciones)
        self.assertEqual(fin[total], min(fin.values()))
        # el reparto con las elegidas es el mismo que pidiendolas a mano
        a = v12f.repartir(datos, {'MODO': 'DIAGNOSTICO', 'ZONAS': total})
        self.assertAlmostEqual(a.ini_min + a.fin / 60.0, fin[total], places=3)
        self.assertEqual(cam, {'MODO': 'REAL'})          # no toca los cambios que recibe

    def test_menos_zonas_si_acaba_casi_igual(self):
        datos = sintetico.generar(21, n_pedidos=120)
        _total, opciones = elegir.elegir(datos, {}, {}, [2, 3, 4], margen=0)
        fines = sorted(o['fin'] for o in opciones)
        total, _ = elegir.elegir(datos, {}, {}, [2, 3, 4], margen=10000)
        self.assertEqual(total, 2 + 2)                     # con un margen enorme, siempre la de menos zonas
        self.assertTrue(fines)

    def test_lineas(self):
        datos = sintetico.generar(21, n_pedidos=120)
        total, opciones = elegir.elegir(datos, {}, {}, [3, 4])
        lineas = elegir.lineas_elegir(total, opciones)
        self.assertIn(len(lineas), (1, 2))
        self.assertTrue(lineas[-1].startswith('ZONAS DEL DIA:'))    # el correo las busca asi
        self.assertIn('<- ELEGIDA', lineas[-1])
        if len(lineas) == 2:
            self.assertTrue(lineas[0].startswith('AVISO:'))
        self.assertEqual(elegir.lineas_elegir(None, []), [])

    def test_v1100_pico_y_cajas(self):
        datos = sintetico.generar(21, n_pedidos=120)
        _t, opciones = elegir.elegir(datos, {}, {}, [2, 3, 4], margen=0)
        for o in opciones:
            self.assertIsNotNone(o['pico'])
            self.assertGreaterEqual(o['pico'], 0)
            self.assertGreaterEqual(o['por_partir'], 0)

    def test_v1100_no_elige_con_pico(self):
        viejo = elegir.PICO_MAX
        try:
            datos = sintetico.generar(21, n_pedidos=120)
            _t, opciones = elegir.elegir(datos, {}, {}, [2, 3, 4], margen=0)
            picos = sorted(o['pico'] for o in opciones)
            # con el limite justo por debajo del pico mas alto, esa opcion no se elige nunca
            elegir.PICO_MAX = (picos[-2] + picos[-1]) / 2.0
            if picos[-1] > picos[-2]:
                total, opciones = elegir.elegir(datos, {}, {}, [2, 3, 4], margen=0)
                peor = [o for o in opciones if o['pico'] == picos[-1]][0]
                self.assertNotEqual(total, peor['zonas'])
                self.assertEqual(peor['fuera'], 'pico')
            # con un limite imposible: la de menos pico y aviso
            elegir.PICO_MAX = -1
            total, opciones = elegir.elegir(datos, {}, {}, [2, 3, 4], margen=0)
            menos = min(opciones, key=lambda o: (o['pico'], o['lineal']))
            self.assertEqual(total, menos['zonas'])
            self.assertTrue(elegir.lineas_elegir(total, opciones)[0].startswith('AVISO:'))
        finally:
            elegir.PICO_MAX = viejo

    def test_pocas_uds_ninguna(self):
        datos = sintetico.generar(21, n_pedidos=3)
        total, opciones = elegir.elegir(datos, {'MIN_UDS_ZONAS': 100000}, {}, [3, 4])
        self.assertIsNone(total)
        self.assertIn('ninguna opcion', elegir.lineas_elegir(total, opciones)[0])


if __name__ == '__main__':
    unittest.main()

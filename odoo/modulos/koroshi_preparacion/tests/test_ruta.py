# -*- coding: utf-8 -*-
# v3.29: tests puros de models/ruta.py (sin base de datos). Se pueden pasar sin Odoo:
#   python odoo/modulos/koroshi_preparacion/tests/test_ruta.py
# y dentro de Odoo con --test-enable (koroshi_preparacion).
import importlib.util
import os
import random
import unittest

try:   # dentro de Odoo, con sus etiquetas; fuera, unittest a secas
    from odoo.tests.common import BaseCase as Base
except ImportError:
    Base = unittest.TestCase

_RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'ruta.py')
_spec = importlib.util.spec_from_file_location('koroshi_preparacion_ruta_test', _RUTA)
ruta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ruta)


class TestRuta(Base):

    def setUp(self):
        super(TestRuta, self).setUp()
        ruta._CACHE.clear()

    # ------------------------------------------------------------ lpc / parada
    def test_lpc_nombres_reales(self):
        self.assertEqual(ruta.lpc('EFFEC/Stock/NAVE2/28035 - L44 P17 C2/KO_110626_032'), (44, 17, 2))
        self.assertEqual(ruta.lpc('L58 P21 C1'), (58, 21, 1))
        self.assertEqual(ruta.lpc('EFFEC/Stock/NAVE2/00114 - L02 P31'), (2, 31, 0))   # sin altura: C0

    def test_lpc_no_lineal(self):
        self.assertIsNone(ruta.lpc('EFFEC/Stock/NAVE2/N1-L07 P10 C1'))   # zona N1: no se sabe dónde está
        self.assertIsNone(ruta.lpc('EFFEC/Stock/MU-15'))
        self.assertIsNone(ruta.lpc(''))
        self.assertIsNone(ruta.lpc(None))

    def test_parada(self):
        self.assertEqual(ruta.parada('28035 - L44 P17 C2'), (22, ruta._x(17)))
        # la altura no cuenta: misma parada
        self.assertEqual(ruta.parada('L44 P17 C1'), ruta.parada('L44 P17 C4'))
        # espalda con espalda (L43 y L44 dan a pasillos distintos; L44 y L45, al mismo)
        self.assertEqual(ruta.parada('L44 P05')[0], ruta.parada('L45 P05')[0])
        self.assertEqual(ruta.parada('EFFEC/Stock/MU-15'), ruta.ZONA_MU)
        self.assertIsNone(ruta.parada('EFFEC/Stock/FALTANTE'))

    def test_x_pasillos_transversales(self):
        # cada posición va más lejos de la fachada que la anterior, con los saltos de los pasillos
        xs = [ruta._x(p) for p in range(1, 37)]
        self.assertEqual(xs, sorted(xs))
        self.assertGreater(ruta._x(4) - ruta._x(3), ruta.ANCHO_P)      # pasillo después de P03
        self.assertGreater(ruta._x(18) - ruta._x(17), ruta.ANCHO_P)    # pasillo central
        self.assertGreater(ruta._x(25) - ruta._x(24), ruta.ANCHO_P)    # pasillo después de P24

    # ------------------------------------------------------------ distancia
    def test_distancia(self):
        a, b, c = (5, 10.0), (5, 20.0), (8, 15.0)
        self.assertEqual(ruta.distancia(a, b), 10.0)                 # mismo pasillo: en horizontal
        self.assertEqual(ruta.distancia(a, a), 0)
        self.assertEqual(ruta.distancia(a, c), ruta.distancia(c, a))  # simétrica
        # pasillo distinto: cruzar (2 m por pasillo) por el transversal que salga más corto
        self.assertAlmostEqual(ruta.distancia((5, 10.1), (8, 10.1)), 3 * ruta.ENTRE_PASILLOS)
        self.assertGreater(ruta.distancia(a, c), 3 * ruta.ENTRE_PASILLOS)

    # ------------------------------------------------------------ ordenar
    def test_ordenar_vacio_y_una(self):
        self.assertEqual(ruta.ordenar([]), [])
        self.assertEqual(ruta.ordenar([None, None]), [])
        self.assertEqual(ruta.ordenar([(3, 10.0), (3, 10.0)]), [(3, 10.0)])

    def test_ordenar_es_permutacion_sin_repetidas(self):
        rnd = random.Random(13)
        paradas = [(rnd.randint(0, 60), ruta._x(rnd.randint(1, 36))) for _ in range(40)] + [None]
        res = ruta.ordenar(paradas)
        self.assertEqual(sorted(res), sorted(set(p for p in paradas if p)))

    def test_ordenar_mu_al_final(self):
        res = ruta.ordenar([(2, ruta._x(3)), ruta.ZONA_MU, (20, ruta._x(30)), (10, ruta._x(12))])
        self.assertEqual(res[-1], ruta.ZONA_MU)

    def test_ordenar_no_depende_del_orden_de_entrada(self):
        # dos PDA con las mismas líneas en otro orden ven la misma ruta
        rnd = random.Random(7)
        paradas = [(rnd.randint(1, 30), ruta._x(rnd.randint(1, 36))) for _ in range(60)]
        res = ruta.ordenar(paradas)
        ruta._CACHE.clear()
        rnd.shuffle(paradas)
        self.assertEqual(ruta.ordenar(paradas), res)

    def test_ordenar_mejor_o_igual_que_por_nombre(self):
        rnd = random.Random(3)
        paradas = list(set((rnd.randint(1, 40), ruta._x(rnd.randint(1, 36))) for _ in range(50)))
        por_nombre = sorted(paradas)
        # la penalización por cambio de pasillo puede costar algún metro, nunca mucho más que el orden por nombre
        self.assertLessEqual(ruta.metros(ruta.ordenar(paradas)), ruta.metros(por_nombre) * 1.05)

    def test_ordenar_cache_no_se_estropea(self):
        paradas = [(4, ruta._x(2)), (9, ruta._x(30)), (15, ruta._x(10))]
        primera = ruta.ordenar(paradas)
        primera.reverse()   # quien llama puede tocar la lista
        self.assertEqual(ruta.ordenar(paradas), list(reversed(primera)))

    def test_metros(self):
        self.assertEqual(ruta.metros([]), 0)
        ida_vuelta = ruta.metros([(0, ruta.MUELLES[1] + 10)])
        self.assertAlmostEqual(ida_vuelta, 20.0)


if __name__ == '__main__':
    unittest.main()

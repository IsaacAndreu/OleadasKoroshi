# -*- coding: utf-8 -*-
# Pruebas sin Odoo: python odoo/modulos/koroshi_prenda_suelo/tests/test_logica.py
# Usa la ruta de verdad de koroshi_preparacion (models/ruta.py, Python puro) para las distancias.
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AQUI)), 'koroshi_preparacion', 'models'))
import logica  # noqa: E402
import ruta  # noqa: E402

L44 = ruta.parada('EFFEC/Stock/NAVE2/28035 - L44 P17 C2')
L45 = ruta.parada('EFFEC/Stock/NAVE2/28100 - L45 P17 C1')
L10 = ruta.parada('EFFEC/Stock/NAVE2/10000 - L10 P05 C1')
MU = ruta.parada('EFFEC/Stock/NAVE2/MU-01 P00 C1')


class TestLogica(unittest.TestCase):

    def test_paradas(self):
        self.assertEqual(L44[0], L45[0])          # L44 y L45: el mismo pasillo
        self.assertIsNotNone(MU)
        self.assertIsNone(ruta.parada('EFFEC/Stock/NAVE2/N1-L07 P10 C1'))

    def test_metros(self):
        self.assertEqual(logica.metros(ruta.distancia, L44, L45), 0)
        self.assertIsNone(logica.metros(ruta.distancia, L44, None))
        self.assertGreater(logica.metros(ruta.distancia, L44, L10), 10)

    def test_ordenar_personas_por_metros(self):
        personas = [
            {'nombre': 'LEJOS', 'actual': L10, 'siguiente': None, 'minutos': 1},
            {'nombre': 'CERCA', 'actual': L45, 'siguiente': None, 'minutos': 9},
            {'nombre': 'SIN SABER', 'actual': None, 'siguiente': None, 'minutos': 0},
        ]
        res = logica.ordenar_personas(personas, ruta.distancia, L44)
        self.assertEqual([p['nombre'] for p in res], ['CERCA', 'LEJOS', 'SIN SABER'])
        self.assertEqual(res[0]['metros'], 0)

    def test_ordenar_personas_va_hacia(self):
        # está lejos pero va hacia donde estoy: cuenta lo más cerca de las dos
        personas = [
            {'nombre': 'VIENE', 'actual': L10, 'siguiente': L45, 'minutos': 2},
            {'nombre': 'MEDIO', 'actual': MU, 'siguiente': None, 'minutos': 2},
        ]
        res = logica.ordenar_personas(personas, ruta.distancia, L44)
        self.assertEqual(res[0]['nombre'], 'VIENE')

    def test_ordenar_personas_sin_origen(self):
        personas = [
            {'nombre': 'ANTIGUA', 'actual': L10, 'siguiente': None, 'minutos': 12},
            {'nombre': 'RECIENTE', 'actual': L45, 'siguiente': None, 'minutos': 1},
            {'nombre': 'NUNCA', 'actual': None, 'siguiente': None, 'minutos': None},
        ]
        res = logica.ordenar_personas(personas, ruta.distancia, None)
        self.assertEqual([p['nombre'] for p in res], ['RECIENTE', 'ANTIGUA', 'NUNCA'])
        self.assertIsNone(res[0]['metros'])

    def test_ordenar_huecos(self):
        huecos = [
            {'nombre': 'L10 P05 C1', 'parada': L10, 'uds': 9},
            {'nombre': 'L45 P17 C1', 'parada': L45, 'uds': 1},
            {'nombre': 'N1-L07 P10 C1', 'parada': None, 'uds': 20},
        ]
        cerca = logica.ordenar_huecos([dict(h) for h in huecos], ruta.distancia, L44)
        self.assertEqual([h['nombre'] for h in cerca], ['L45 P17 C1', 'L10 P05 C1', 'N1-L07 P10 C1'])
        sin_origen = logica.ordenar_huecos([dict(h) for h in huecos], ruta.distancia, None)
        self.assertEqual([h['nombre'] for h in sin_origen], ['N1-L07 P10 C1', 'L10 P05 C1', 'L45 P17 C1'])

    def test_caso(self):
        self.assertEqual(logica.caso([1], [1], [1], [1]), 'A')
        self.assertEqual(logica.caso([], [1], [1], [1]), 'B')
        self.assertEqual(logica.caso([], [], [1], [1]), 'C')
        self.assertEqual(logica.caso([], [], [], [1]), 'D')
        self.assertEqual(logica.caso([], [], [], []), 'E')

    def test_textos(self):
        self.assertEqual(logica.texto_minutos(None), '')
        self.assertEqual(logica.texto_minutos(0.2), 'ahora mismo')
        self.assertEqual(logica.texto_minutos(3), 'hace 3 min')
        self.assertEqual(logica.texto_minutos(75), 'hace 1 h 15 min')
        self.assertEqual(logica.texto_metros(None), '')
        self.assertEqual(logica.texto_metros(2), 'aquí al lado')
        self.assertEqual(logica.texto_metros(14), 'a unos 14 m')


if __name__ == '__main__':
    unittest.main()

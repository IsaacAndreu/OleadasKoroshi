# -*- coding: utf-8 -*-
# Tests de reparto.py sin Odoo. Desde la carpeta del modulo: python -m unittest discover -s tests
# (No hay tests/__init__.py a proposito: no son tests de Odoo.)
import datetime
import importlib.util
import os
import unittest

_RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reparto.py')
_spec = importlib.util.spec_from_file_location('reparto', _RUTA)
reparto = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reparto)

DT = datetime.datetime


class TestReparto(unittest.TestCase):

    def test_cortes(self):
        self.assertEqual(reparto.cortes('06:00,11:00'), [(6, 0), (11, 0)])
        self.assertEqual(reparto.cortes(' 11:00 ; 6:00, 11:00, 25:00, x'), [(6, 0), (11, 0)])
        self.assertEqual(reparto.cortes(''), [])
        self.assertEqual(reparto.cortes(None), [])

    def test_corte_pendiente(self):
        c = [(6, 0), (11, 0)]
        self.assertIsNone(reparto.corte_pendiente(DT(2026, 11, 18, 5, 59), c, '', 120))
        self.assertEqual(reparto.corte_pendiente(DT(2026, 11, 18, 6, 7), c, '2026-11-17 11:00', 120),
                         ('2026-11-18 06:00', (6, 0), False))
        # ya hecho
        self.assertIsNone(reparto.corte_pendiente(DT(2026, 11, 18, 6, 22), c, '2026-11-18 06:00', 120))
        # a las 11 toca el de las 11
        self.assertEqual(reparto.corte_pendiente(DT(2026, 11, 18, 11, 1), c, '2026-11-18 06:00', 120)[0],
                         '2026-11-18 11:00')
        # servidor parado: a las 14:00 el de las 11 llega tarde (se apunta, no se hace)
        self.assertEqual(reparto.corte_pendiente(DT(2026, 11, 18, 14, 0), c, '2026-11-18 06:00', 120),
                         ('2026-11-18 11:00', (11, 0), True))
        # si se salto el de las 6, a las 11 solo se hace el de las 11
        self.assertEqual(reparto.corte_pendiente(DT(2026, 11, 18, 11, 5), c, '2026-11-17 11:00', 120)[0],
                         '2026-11-18 11:00')
        self.assertIsNone(reparto.corte_pendiente(DT(2026, 11, 18, 12, 0), [], '', 120))

    def test_repartir(self):
        self.assertEqual(reparto.repartir([], 100), [])
        self.assertEqual(reparto.repartir([(1, 40), (2, 60), (3, 1)], 100), [[1, 2], [3]])
        self.assertEqual(reparto.repartir([(1, 40), (2, 61), (3, 1)], 100), [[1], [2, 3]])
        # una OUT que sola pasa del tope va sola
        self.assertEqual(reparto.repartir([(1, 30), (2, 150), (3, 5)], 100), [[1], [2], [3]])
        self.assertEqual(reparto.repartir([(1, 150)], 100), [[1]])
        # se respeta el orden de llegada (no se rellenan huecos con OUT posteriores)
        self.assertEqual(reparto.repartir([(1, 90), (2, 20), (3, 5)], 100), [[1], [2, 3]])
        self.assertEqual(reparto.repartir([(1, 500), (2, 500)], 0), [[1, 2]])

    def test_siguiente_numero(self):
        p = 'WEB_181126_'
        self.assertEqual(reparto.siguiente_numero([], p), 1)
        self.assertEqual(reparto.siguiente_numero(['WEB_181126_01', 'WEB_181126_03', 'WEB_171126_09'], p), 4)
        self.assertEqual(reparto.siguiente_numero(['WEB_181126_01 ', 'WEB_181126_x', 'juntar 96 cajas', None], p), 2)


if __name__ == '__main__':
    unittest.main()

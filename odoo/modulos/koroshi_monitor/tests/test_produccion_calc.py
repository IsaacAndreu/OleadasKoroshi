# -*- coding: utf-8 -*-
# Pruebas sin Odoo:  python -I odoo/modulos/koroshi_monitor/tests/test_produccion_calc.py
import datetime
import os
import sys
import unittest

import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'controllers'))
import produccion_calc as calc  # noqa: E402

TZ = pytz.timezone('Europe/Madrid')
D = datetime.datetime


def utc(h, m=0, dia=17):
    """Hora local de Madrid del 17/11/2026 (UTC+1) -> UTC sin zona."""
    return TZ.localize(D(2026, 11, dia, h, m)).astimezone(pytz.utc).replace(tzinfo=None)


class TestProduccion(unittest.TestCase):

    def test_minutos_por_hora_sin_parados(self):
        inter = calc.intervalos_activos(utc(7, 30), utc(9, 10), [(utc(8, 0), utc(8, 20), 20)])
        mh = calc.minutos_por_hora(inter, TZ)
        self.assertAlmostEqual(mh[7], 30)
        self.assertAlmostEqual(mh[8], 40)
        self.assertAlmostEqual(mh[9], 10)
        self.assertAlmostEqual(sum(mh.values()), 80)    # 100 min - 20 parado

    def test_uds_por_lecturas(self):
        t = {'op': 'Ana · OP3', 'codigo': 'OP3', 'ref': 'OUT/1', 'inicio': utc(7, 30), 'fin': utc(9, 10), 'uds': 100,
             'minutos': 100, 'efectivo': 80, 'huecos': [(utc(8, 0), utc(8, 20), 20)],
             'lecturas': [(utc(7, 40), 30), (utc(8, 30), 50), (utc(9, 5), 20)]}
        r = calc.produccion([t], TZ)
        self.assertEqual(r['horas'], [7, 8, 9])
        o = r['operarios'][0]
        self.assertEqual([o['celdas'][h]['uds'] for h in ('7', '8', '9')], [30, 50, 20])
        self.assertEqual(o['celdas']['7']['uh'], 60)    # 30 uds en 30 min
        self.assertEqual(o['celdas']['8']['uh'], 75)    # 50 uds en 40 min
        self.assertEqual(o['celdas']['9']['uh'], 120)   # 20 uds en 10 min
        self.assertEqual(o['uds'], 100)
        self.assertEqual(o['uh'], 75)                   # 100 uds / 80 min efectivos
        self.assertFalse(o['estimado'])

    def test_sin_lecturas_por_minutos_y_equipo(self):
        a = {'op': 'Ana · OP3', 'codigo': 'OP3', 'inicio': utc(7, 0), 'fin': utc(9, 0), 'uds': 120, 'minutos': 120,
             'efectivo': 120, 'huecos': [], 'lecturas': []}
        b = {'op': 'Luis · OP10', 'codigo': 'OP10', 'inicio': utc(8, 0), 'fin': utc(8, 30), 'uds': 40, 'minutos': 30,
             'efectivo': 30, 'huecos': [], 'lecturas': [(utc(8, 10), 40)]}
        c = {'op': 'Zoe · OP1', 'codigo': 'OP1', 'inicio': utc(8, 0), 'fin': utc(8, 0), 'uds': 0, 'minutos': 0,
             'efectivo': 0, 'huecos': [], 'lecturas': []}
        r = calc.produccion([b, a, c], TZ)
        self.assertEqual([o['codigo'] for o in r['operarios']], ['OP1', 'OP3', 'OP10'])   # por numero de codigo
        ana = r['operarios'][1]
        self.assertEqual(ana['celdas']['7']['uds'], 60)
        self.assertEqual(ana['celdas']['8']['uds'], 60)
        self.assertTrue(ana['estimado'])
        eq = r['equipo']['celdas']['8']
        self.assertEqual(eq['uds'], 100)
        self.assertEqual(eq['min'], 90)
        self.assertEqual(eq['uh'], 67)                  # 100 uds en 90 min-persona
        self.assertEqual(r['equipo']['uds'], 160)
        self.assertEqual(r['equipo']['uh'], 64)         # 160 / 150 min

    def test_poco_tiempo_sin_uh(self):
        t = {'op': 'X', 'codigo': 'OP2', 'inicio': utc(10, 58), 'fin': utc(11, 30), 'uds': 10, 'minutos': 32,
             'efectivo': 32, 'huecos': [], 'lecturas': [(utc(10, 59), 2), (utc(11, 10), 8)]}
        o = calc.produccion([t], TZ)['operarios'][0]
        self.assertIsNone(o['celdas']['10']['uh'])      # 2 min en esa hora: no se ensena u/h
        self.assertEqual(o['celdas']['11']['uds'], 8)

    def test_cambio_de_hora(self):
        # 25/10/2026: a las 3:00 de verano vuelven a ser las 2:00 (dia de 25 h)
        ini = TZ.localize(D(2026, 10, 25, 1, 30)).astimezone(pytz.utc).replace(tzinfo=None)
        fin = ini + datetime.timedelta(hours=2)
        mh = calc.minutos_por_hora([(ini, fin)], TZ)
        self.assertAlmostEqual(sum(mh.values()), 120)


if __name__ == '__main__':
    unittest.main()

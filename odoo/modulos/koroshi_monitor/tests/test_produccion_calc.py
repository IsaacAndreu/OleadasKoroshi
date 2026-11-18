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

    def test_uh_real_y_perdido(self):
        # v1.32: Diana de 9 a 9:54 hace 42 uds en 44 min efectivos (dos pedidos con 10 min entre ellos, cerrando
        # caja): presencia 54, u/h real 47. (v1.35: con 15 min o mas entre ellos ese hueco ya no cuenta)
        a = {'op': 'Diana · OP2', 'codigo': 'OP2', 'tipo': 'tiendas', 'inicio': utc(9, 0), 'fin': utc(9, 20),
             'uds': 20, 'minutos': 20, 'efectivo': 20, 'huecos': [], 'lecturas': [(utc(9, 10), 20)]}
        b = {'op': 'Diana · OP2', 'codigo': 'OP2', 'tipo': 'web', 'inicio': utc(9, 30), 'fin': utc(9, 54),
             'uds': 22, 'minutos': 24, 'efectivo': 24, 'huecos': [], 'lecturas': [(utc(9, 50), 22)]}
        r = calc.produccion([a, b], TZ)
        c = r['operarios'][0]['celdas']['9']
        self.assertEqual((c['uds'], c['min'], c['pres'], c['perdido']), (42, 44, 54, 10))
        self.assertEqual(c['uh_real'], 47)
        self.assertEqual(c['uh'], 57)                   # mientras pica: 42 uds / 44 min
        self.assertEqual(c['color'], 'bajo')            # < 100 u/h real: rojo
        o = r['operarios'][0]
        self.assertEqual((o['presencia'], o['perdido'], o['uh_real']), (54, 10, 47))
        self.assertEqual(r['tipos'], {'tiendas': 1, 'web': 1})
        self.assertEqual(r['equipo']['max_a_la_vez'], 1)
        # solo web: la presencia es solo el tiempo dentro de sus pedidos (24 min)
        w = calc.produccion([a, b], TZ, filtrar=lambda t: t['tipo'] == 'web')
        ow = w['operarios'][0]
        self.assertEqual((ow['uds'], ow['presencia'], ow['perdido']), (22, 24, 0))
        self.assertEqual(ow['uh_real'], 55)

    def test_hueco_largo_entre_pedidos_no_cuenta(self):
        # v1.35: 30 min entre dos pedidos (desayuno, o se cerro sola por inactividad): no es presencia ni perdido
        a = {'op': 'Ana · OP3', 'codigo': 'OP3', 'inicio': utc(9, 0), 'fin': utc(9, 20), 'uds': 20, 'minutos': 20,
             'efectivo': 20, 'huecos': [], 'lecturas': [(utc(9, 10), 20)]}
        b = {'op': 'Ana · OP3', 'codigo': 'OP3', 'inicio': utc(9, 50), 'fin': utc(10, 10), 'uds': 20, 'minutos': 20,
             'efectivo': 20, 'huecos': [], 'lecturas': [(utc(10, 0), 20)]}
        o = calc.produccion([a, b], TZ)['operarios'][0]
        self.assertEqual((o['presencia'], o['perdido']), (40, 0))
        self.assertEqual((o['celdas']['9']['pres'], o['celdas']['9']['perdido']), (30, 0))
        # con 14 min entre ellos si cuenta (cerrar caja, palé)
        b2 = dict(b, inicio=utc(9, 34), fin=utc(9, 54))
        o2 = calc.produccion([a, b2], TZ)['operarios'][0]
        self.assertEqual((o2['presencia'], o2['perdido']), (54, 14))

    def test_sesion_olvidada_abierta(self):
        # v1.35 (captura del 18/11): tarea abierta desde las 13:16, ultima lectura 13:57 y ahora son las 15:52. El
        # controlador pasa fin = ahora y el «parado ahora» como hueco: de 14 a 16 ya no sale nada.
        t = {'op': 'Sheyla · OP9', 'codigo': 'OP9', 'inicio': utc(13, 16), 'fin': utc(15, 52), 'uds': 47,
             'minutos': 156, 'efectivo': 41, 'huecos': [(utc(13, 57), utc(15, 52), 115)],
             'lecturas': [(utc(13, 30), 20), (utc(13, 55), 27)]}
        o = calc.produccion([t], TZ)['operarios'][0]
        self.assertEqual((o['presencia'], o['perdido'], o['efectivo']), (41, 0, 41))
        self.assertEqual(o['celdas']['13']['pres'], 41)
        self.assertEqual(o['celdas'].get('14', {}).get('pres', 0), 0)
        self.assertEqual(o['celdas'].get('15', {}).get('pres', 0), 0)
        # un parado de 15 min o mas dentro del pedido tampoco es presencia
        t2 = dict(t, fin=utc(14, 30), huecos=[(utc(13, 30), utc(13, 50), 20)])
        o2 = calc.produccion([t2], TZ)['operarios'][0]
        self.assertEqual(o2['presencia'], 54)           # 13:16-13:30 + 13:50-14:30

    def test_color_ok(self):
        t = {'op': 'X', 'codigo': 'OP5', 'inicio': utc(8, 0), 'fin': utc(9, 0), 'uds': 120, 'minutos': 60,
             'efectivo': 60, 'huecos': [], 'lecturas': [(utc(8, 30), 120)]}
        o = calc.produccion([t], TZ)['operarios'][0]
        self.assertEqual(o['celdas']['8']['color'], 'ok')
        self.assertEqual(o['color'], 'ok')

    def test_cambio_de_hora(self):
        # 25/10/2026: a las 3:00 de verano vuelven a ser las 2:00 (dia de 25 h)
        ini = TZ.localize(D(2026, 10, 25, 1, 30)).astimezone(pytz.utc).replace(tzinfo=None)
        fin = ini + datetime.timedelta(hours=2)
        mh = calc.minutos_por_hora([(ini, fin)], TZ)
        self.assertAlmostEqual(sum(mh.values()), 120)


if __name__ == '__main__':
    unittest.main()

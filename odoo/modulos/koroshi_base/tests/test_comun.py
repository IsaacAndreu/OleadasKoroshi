# -*- coding: utf-8 -*-
# Tests de comun.py sin Odoo. Desde la carpeta del modulo: python -m unittest discover -s tests
# (No hay tests/__init__.py a proposito: no son tests de Odoo.)
import datetime
import importlib.util
import os
import unittest

_RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'comun.py')
_spec = importlib.util.spec_from_file_location('comun', _RUTA)
comun = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comun)

D = datetime.date
DT = datetime.datetime


class TestComun(unittest.TestCase):

    def test_constantes(self):
        self.assertEqual(comun.COMPANY_ID, 8)
        self.assertEqual(comun.TZ, 'Europe/Madrid')

    def test_matricula(self):
        for bueno in ('CJ123456789', 'cj123456789', ' CJ000000001 ', 'Cj999999999'):
            self.assertTrue(comun.es_matricula(bueno), bueno)
        for malo in ('', None, False, 'CJ12345678', 'CJ1234567890', 'XJ123456789', 'CJ12345678A', '123456789'):
            self.assertFalse(comun.es_matricula(malo), malo)
        # la expresion sola sigue siendo estricta (mayusculas), como estaba en los modulos
        self.assertIsNone(comun.RE_CJ.match('cj123456789'))

    def test_dia_normal(self):
        # invierno: UTC+1
        self.assertEqual(comun.rango_dia_utc(D(2026, 11, 14)), (DT(2026, 11, 13, 23), DT(2026, 11, 14, 23)))
        # verano: UTC+2
        self.assertEqual(comun.rango_dia_utc(D(2026, 7, 1)), (DT(2026, 6, 30, 22), DT(2026, 7, 1, 22)))

    def test_cambio_de_hora(self):
        # 29/03/2026: el dia dura 23 h; 25/10/2026: 25 h
        ini, fin = comun.rango_dia_utc(D(2026, 3, 29))
        self.assertEqual((ini, fin), (DT(2026, 3, 28, 23), DT(2026, 3, 29, 22)))
        ini, fin = comun.rango_dia_utc(D(2026, 10, 25))
        self.assertEqual((ini, fin), (DT(2026, 10, 24, 22), DT(2026, 10, 25, 23)))
        self.assertEqual(fin - ini, datetime.timedelta(hours=25))

    def test_rango_dias(self):
        self.assertEqual(comun.rango_dias_utc(D(2026, 11, 10), D(2026, 11, 14)),
                         (DT(2026, 11, 9, 23), DT(2026, 11, 14, 23)))
        self.assertEqual(comun.rango_dias_utc(D(2026, 11, 14), D(2026, 11, 14)), comun.rango_dia_utc(D(2026, 11, 14)))

    def test_a_local(self):
        self.assertIsNone(comun.a_local(False))
        loc = comun.a_local(DT(2026, 11, 13, 23, 30))
        self.assertEqual((loc.date(), loc.hour, loc.minute), (D(2026, 11, 14), 0, 30))
        self.assertEqual(comun.dia_local(DT(2026, 11, 13, 22, 59)), D(2026, 11, 13))
        self.assertEqual(comun.dia_local(DT(2026, 11, 13, 23, 0)), D(2026, 11, 14))

    def test_hoy(self):
        self.assertEqual(comun.hoy_local(), comun.ahora_local().date())
        self.assertEqual(comun.ahora_local().tzinfo.zone, 'Europe/Madrid')


if __name__ == '__main__':
    unittest.main()

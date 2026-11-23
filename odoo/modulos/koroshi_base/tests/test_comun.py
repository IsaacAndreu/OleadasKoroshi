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

class TestTurnos(unittest.TestCase):
    """v1.1.0: turno por hora de entrada."""

    def utc(self, h, m=0, dia=20):
        import pytz
        return comun.zona().localize(DT(2026, 11, dia, h, m)).astimezone(pytz.utc).replace(tzinfo=None)

    def test_manana(self):
        t = comun.turno_de(self.utc(6, 4))
        self.assertEqual(t['tramos'], [(self.utc(6), self.utc(14))])
        self.assertEqual((t['fin'], t['descanso'], t['continuo'], t['nombre']), (self.utc(14), 15, True, '06:00-14:00'))
        self.assertEqual(comun.turno_de(self.utc(5, 50))['nombre'], '06:00-14:00')     # llega antes de hora
        self.assertEqual(comun.turno_de(self.utc(6, 59))['nombre'], '06:00-14:00')

    def test_partido(self):
        t = comun.turno_de(self.utc(8, 3))
        self.assertEqual(t['tramos'], [(self.utc(8), self.utc(13)), (self.utc(14), self.utc(17))])
        self.assertEqual((t['fin'], t['descanso'], t['continuo']), (self.utc(17), 0, False))
        self.assertEqual(comun.turno_de(self.utc(7))['nombre'], '08:00-13:00 y 14:00-17:00')

    def test_sin_turno(self):
        self.assertIsNone(comun.turno_de(self.utc(11)))
        self.assertIsNone(comun.turno_de(self.utc(15, 30)))
        self.assertIsNone(comun.turno_de(None))

    def test_cambio_de_hora(self):
        # 29/03/2026 (verano): 06:00 local = 04:00 UTC; 20/11 (invierno): 05:00 UTC
        t = comun.turno_de(self.utc(6, 10, dia=20))
        self.assertEqual(t['tramos'][0][0], DT(2026, 11, 20, 5, 0))
        import pytz
        e = comun.zona().localize(DT(2026, 3, 30, 6, 10)).astimezone(pytz.utc).replace(tzinfo=None)
        self.assertEqual(comun.turno_de(e)['tramos'][0][0], DT(2026, 3, 30, 4, 0))

    def test_parametro(self):
        texto = '07:30 06:30-14:30 descanso=20; 12:00 09:00-14:00,15:00-19:00'
        self.assertEqual(comun.turno_de(self.utc(7, 10), texto)['nombre'], '06:30-14:30')
        self.assertEqual(comun.turno_de(self.utc(7, 10), texto)['descanso'], 20)
        self.assertEqual(comun.turno_de(self.utc(11, 0), texto)['fin'], self.utc(19))
        # mal escrito: se salta esa parte; todo mal: la regla por defecto
        self.assertEqual(len(comun.leer_turnos('07:00 06:00-14:00; xx 8-9; 11:00 10:00-09:00')), 1)
        self.assertEqual(comun.leer_turnos('basura'), comun.leer_turnos(None))
        self.assertEqual(comun.leer_turnos(''), comun.leer_turnos(None))


class TestVariantesCodigo(unittest.TestCase):
    # v1.2.0 (O5)

    def test_ean13(self):
        self.assertEqual(comun.variantes_codigo('8445962847058'), ['8445962847058'])

    def test_upc_12_con_cero_delante(self):
        self.assertEqual(comun.variantes_codigo('445962847058'), ['445962847058', '0445962847058'])

    def test_ean_con_cero_delante_sin_el(self):
        self.assertEqual(comun.variantes_codigo('0445962847058'), ['0445962847058', '445962847058'])

    def test_referencia_y_vacio(self):
        self.assertEqual(comun.variantes_codigo(' 2621PT01-000014-34 '), ['2621PT01-000014-34'])
        self.assertEqual(comun.variantes_codigo(''), [])
        self.assertEqual(comun.variantes_codigo(None), [])


if __name__ == '__main__':
    unittest.main()

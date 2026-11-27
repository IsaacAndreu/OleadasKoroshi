# -*- coding: utf-8 -*-
# Tests de comun.py sin Odoo. Desde la carpeta del módulo: python -m unittest discover -s tests
# (No hay tests/__init__.py a propósito: no son tests de Odoo.)
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

    def test_sin_compania_fija(self):
        self.assertFalse(hasattr(comun, 'COMPANY_ID'))
        self.assertEqual(comun.TZ, 'Europe/Madrid')

    def test_caja(self):
        for bueno in ('BOX0699806', 'box0699806', ' BOX0000001 '):
            self.assertTrue(comun.es_caja(bueno), bueno)
        for malo in ('', None, False, 'BOX069980', 'BOX06998061', 'CJ123456789', 'BOX069980A'):
            self.assertFalse(comun.es_caja(malo), malo)
        self.assertTrue(comun.es_caja('CJ123456789', r'^CJ\d{9}$'))

    def test_lista_y_prefijos(self):
        self.assertEqual(comun.lista(' KO_, TT_ ,,UB_ '), ['KO_', 'TT_', 'UB_'])
        self.assertEqual(comun.lista(''), [])
        self.assertEqual(comun.lista(None), [])
        self.assertEqual(comun.lista(comun.TIPOS_OLEADA), ['WEB', 'WEB B&B', 'PED. INICIAL'])
        pref = comun.lista(comun.PREFIJOS_CONTENEDOR)
        self.assertEqual(comun.empieza_por('ub_240725_612', pref), 'UB_')
        self.assertEqual(comun.empieza_por('KO_300726_755', pref), 'KO_')
        self.assertEqual(comun.empieza_por('06298 - L75 P38 C2', pref), '')
        self.assertEqual(comun.empieza_por('8447333693493', comun.lista(comun.PREFIJOS_EAN)), '8447333')

    def test_nombre_corto(self):
        self.assertEqual(comun.nombre_corto('WH-OR/Stock/N1/06298 - L75 P38 C2/KO_300726_755'),
                         'N1/06298 - L75 P38 C2/KO_300726_755')
        self.assertEqual(comun.nombre_corto('UBRAN/STOCK/N1/20640 - L147 P05 C4/UB_240725_612'),
                         'N1/20640 - L147 P05 C4/UB_240725_612')
        self.assertEqual(comun.nombre_corto('WH-OR/SORTER'), 'SORTER')
        self.assertEqual(comun.nombre_corto('SORTER'), 'SORTER')
        self.assertEqual(comun.nombre_corto(''), '')
        self.assertEqual(comun.nombre_corto(None), '')

    def test_dia_normal(self):
        self.assertEqual(comun.rango_dia_utc(D(2026, 11, 14)), (DT(2026, 11, 13, 23), DT(2026, 11, 14, 23)))
        self.assertEqual(comun.rango_dia_utc(D(2026, 7, 1)), (DT(2026, 6, 30, 22), DT(2026, 7, 1, 22)))

    def test_cambio_de_hora(self):
        ini, fin = comun.rango_dia_utc(D(2026, 3, 29))
        self.assertEqual((ini, fin), (DT(2026, 3, 28, 23), DT(2026, 3, 29, 22)))
        ini, fin = comun.rango_dia_utc(D(2026, 10, 25))
        self.assertEqual(fin - ini, datetime.timedelta(hours=25))

    def test_rango_dias(self):
        self.assertEqual(comun.rango_dias_utc(D(2026, 11, 10), D(2026, 11, 14)),
                         (DT(2026, 11, 9, 23), DT(2026, 11, 14, 23)))

    def test_a_local(self):
        self.assertIsNone(comun.a_local(False))
        self.assertEqual(comun.dia_local(DT(2026, 11, 13, 22, 59)), D(2026, 11, 13))
        self.assertEqual(comun.dia_local(DT(2026, 11, 13, 23, 0)), D(2026, 11, 14))


class TestTurnos(unittest.TestCase):

    def utc(self, h, m=0, dia=20):
        import pytz
        return comun.zona().localize(DT(2026, 11, dia, h, m)).astimezone(pytz.utc).replace(tzinfo=None)

    def test_reglas(self):
        self.assertEqual(comun.turno_de(self.utc(6, 4))['nombre'], '06:00-14:00')
        self.assertEqual(comun.turno_de(self.utc(8, 3))['nombre'], '08:00-13:00 y 14:00-17:00')
        self.assertIsNone(comun.turno_de(self.utc(11)))
        self.assertIsNone(comun.turno_de(None))
        self.assertEqual(comun.leer_turnos('basura'), comun.leer_turnos(None))
        self.assertEqual(comun.PARAM_TURNOS, 'tuctuc_base.turnos')


class TestVariantesCodigo(unittest.TestCase):

    def test_variantes(self):
        self.assertEqual(comun.variantes_codigo('8447333693493'), ['8447333693493'])
        self.assertEqual(comun.variantes_codigo('447333693493'), ['447333693493', '0447333693493'])
        self.assertEqual(comun.variantes_codigo('0447333693493'), ['0447333693493', '447333693493'])
        self.assertEqual(comun.variantes_codigo(''), [])


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
# Prueba sin Odoo:  python odoo/modulos/koroshi_ubicaciones/tests/test_nombres.py
# (no hay tests/__init__.py a propósito: Odoo no la carga como prueba del módulo)
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nombres as N  # noqa: E402


class TestNombres(unittest.TestCase):

    def test_lineal_normalizado(self):
        self.assertEqual(N.lineal_normalizado('l181'), 'L181')
        self.assertEqual(N.lineal_normalizado(' L094 '), 'L94')
        self.assertEqual(N.lineal_normalizado('mu5'), 'MU-05')
        self.assertEqual(N.lineal_normalizado('MU-05'), 'MU-05')
        self.assertEqual(N.lineal_normalizado('MU 5'), 'MU-05')
        self.assertIsNone(N.lineal_normalizado('L94 P10'))
        self.assertIsNone(N.lineal_normalizado('KO_171126'))
        self.assertIsNone(N.lineal_normalizado(''))

    def test_nombres_lineal(self):
        n = N.nombres_lineal('L181', 0, 2, 1, 4)
        self.assertEqual(len(n), 12)
        self.assertEqual(n[:5], ['L181 P00 C1', 'L181 P00 C2', 'L181 P00 C3', 'L181 P00 C4', 'L181 P01 C1'])
        self.assertEqual(n[-1], 'L181 P02 C4')
        self.assertEqual(N.nombres_lineal('mu5', 18, 18, 1, 1), ['MU-05 P18 C1'])
        for malo in [('X1', 0, 1, 1, 1), ('L1', 5, 1, 1, 1), ('L1', 0, 1, 0, 1), ('L1', 0, 1, 3, 2),
                     ('L1', 0, 999, 1, 9)]:
            with self.assertRaises(ValueError):
                N.nombres_lineal(*malo)

    def test_partes_hueco(self):
        self.assertEqual(N.partes_hueco('21048 - L142 P00 C1'), ('L142', 0, 1))
        self.assertEqual(N.partes_hueco('L181 P05 C2'), ('L181', 5, 2))
        self.assertEqual(N.partes_hueco('MU-04 P18 C4'), ('MU-04', 18, 4))
        self.assertIsNone(N.partes_hueco('KO_171126_001'))
        self.assertIsNone(N.partes_hueco('NAVE2'))
        self.assertEqual(N.clave_hueco('18260 - L180 P13 C1'), 'L180 P13 C1')

    def test_contenedores(self):
        pref = N.prefijo_dia('KO_', datetime.date(2026, 11, 17))
        self.assertEqual(pref, 'KO_171126_')
        with self.assertRaises(ValueError):
            N.prefijo_dia('XX_', datetime.date(2026, 11, 17))
        existentes = ['KO_171126_001', 'KO_171126_100', 'KO_171126_7', 'KO_171126_abc', 'KO_161126_500']
        self.assertEqual(N.siguiente_numero(existentes, pref), 101)
        self.assertEqual(N.siguiente_numero([], pref), 1)
        self.assertEqual(N.nombres_contenedores(pref, 101, 3), ['KO_171126_101', 'KO_171126_102', 'KO_171126_103'])
        self.assertEqual(N.nombres_contenedores(pref, 999, 2), ['KO_171126_999', 'KO_171126_1000'])
        with self.assertRaises(ValueError):
            N.nombres_contenedores(pref, 1, 0)

    def test_reimpresion(self):
        self.assertEqual(N.interpretar_reimpresion('L94'), {'tipo': 'lineal', 'lineal': 'L94', 'p_desde': None, 'p_hasta': None})
        self.assertEqual(N.interpretar_reimpresion('l94 p10-p20'), {'tipo': 'lineal', 'lineal': 'L94', 'p_desde': 10, 'p_hasta': 20})
        self.assertEqual(N.interpretar_reimpresion('L94 P20-10'), {'tipo': 'lineal', 'lineal': 'L94', 'p_desde': 10, 'p_hasta': 20})
        self.assertEqual(N.interpretar_reimpresion('L94 P7'), {'tipo': 'lineal', 'lineal': 'L94', 'p_desde': 7, 'p_hasta': 7})
        self.assertEqual(N.interpretar_reimpresion('mu1')['lineal'], 'MU-01')
        self.assertEqual(N.interpretar_reimpresion('KO_171126'),
                         {'tipo': 'contenedores', 'prefijo': 'KO_171126_', 'desde': None, 'hasta': None})
        self.assertEqual(N.interpretar_reimpresion('ko_171126_001-050'),
                         {'tipo': 'contenedores', 'prefijo': 'KO_171126_', 'desde': 1, 'hasta': 50})
        self.assertEqual(N.interpretar_reimpresion('KO_171126_001 - KO_171126_050')['hasta'], 50)
        self.assertEqual(N.interpretar_reimpresion('TT_250826_445')['desde'], 445)
        self.assertEqual(N.interpretar_reimpresion('18260 - L180 P13 C1'), {'tipo': 'nombre', 'nombre': '18260 - L180 P13 C1'})
        with self.assertRaises(ValueError):
            N.interpretar_reimpresion('  ')

    def test_varios(self):
        self.assertEqual(N.escapar_like('KO_171126_'), 'KO\\_171126\\_')
        self.assertEqual(N.resumen_lista(['a', 'b']), 'a, b')
        self.assertEqual(N.resumen_lista([str(i) for i in range(10)], 3), '0, 1 … 9')


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
# Pruebas sin Odoo:  python -I odoo/modulos/koroshi_monitor/tests/test_cj_calc.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'controllers'))
import cj_calc as calc  # noqa: E402


def out(estado='done', zona='D2', ident=1):
    return {'id': ident, 'estado': estado, 'tienda': 'K1 - MAQUINISTA', 'pedido': 'S-6665004772', 'zona': zona,
            'hora': '25/11 08:40'}


class TestCjSaltadas(unittest.TestCase):

    def test_caso_k1_25_11(self):
        """810 y 811 impresas para la OUT/27848; solo se leyo la 811 (23 uds)."""
        et = [('CJ665013810', 'ETQ ZONA EFFEC/OUT/27848'), ('CJ665013811', 'ETQ ZONA EFFEC/OUT/27848')]
        r = calc.saltadas(et, {'CJ665013811'}, {'EFFEC/OUT/27848': out()}, set(), {'CJ665013811': 23})
        self.assertEqual([x['cj'] for x in r], ['CJ665013810'])
        self.assertEqual(r[0]['leidas'], [('CJ665013811', 23)])
        self.assertEqual(r[0]['max_uds'], 23)

    def test_no_salen(self):
        et = [('CJ1', 'ETQ ZONA A'), ('CJ2', 'ETQ ZONA A'),      # A: sin validar
              ('CJ3', 'ETQ ZONA B'), ('CJ4', 'ETQ ZONA B'),      # B: ninguna leida
              ('CJ5', 'ETQ ZONA C'), ('CJ6', 'ETQ ZONA C'),      # C: la 6 tirada a mano
              ('CJ7', 'ETQ ZONA D'), ('CJ8', 'ETQ ZONA D'),      # D: las dos leidas
              ('CJ9', 'OTRA NOTA')]
        outs = {'A': out('assigned'), 'B': out(), 'C': out(), 'D': out()}
        r = calc.saltadas(et, {'CJ1', 'CJ5', 'CJ7', 'CJ8'}, outs, {'CJ6'}, {})
        self.assertEqual(r, [])

    def test_orden_mas_llena_primero(self):
        et = [('CJ1', 'ETQ ZONA A'), ('CJ2', 'ETQ ZONA A'), ('CJ3', 'ETQ ZONA B'), ('CJ4', 'ETQ ZONA B')]
        outs = {'A': out(ident=1), 'B': out(ident=2)}
        r = calc.saltadas(et, {'CJ1', 'CJ3'}, outs, set(), {'CJ1': 6, 'CJ3': 20})
        self.assertEqual([x['cj'] for x in r], ['CJ4', 'CJ2'])


if __name__ == '__main__':
    unittest.main()

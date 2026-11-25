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
        """810 y 811 impresas para la OUT/27848; solo se leyo la 811 (23 uds, 0,149 m3)."""
        et = [('CJ665013810', 'ETQ ZONA EFFEC/OUT/27848'), ('CJ665013811', 'ETQ ZONA EFFEC/OUT/27848')]
        r = calc.saltadas(et, {'CJ665013811'}, {'EFFEC/OUT/27848': out()}, set(), {'CJ665013811': 23},
                          {'CJ665013811': 0.149}, {'CJ665013811'})
        self.assertEqual([x['cj'] for x in r], ['CJ665013810'])
        self.assertEqual(r[0]['leidas'], [('CJ665013811', 23, 0.149, True)])
        self.assertTrue(r[0]['llena'])

    def test_no_salen(self):
        et = [('CJ1', 'ETQ ZONA A'), ('CJ2', 'ETQ ZONA A'),      # A: sin validar
              ('CJ3', 'ETQ ZONA B'), ('CJ4', 'ETQ ZONA B'),      # B: ninguna leida
              ('CJ5', 'ETQ ZONA C'), ('CJ6', 'ETQ ZONA C'),      # C: la 6 tirada a mano
              ('CJ7', 'ETQ ZONA D'), ('CJ8', 'ETQ ZONA D'),      # D: las dos leidas
              ('CJ9', 'OTRA NOTA')]
        outs = {'A': out('assigned'), 'B': out(), 'C': out(), 'D': out()}
        r = calc.saltadas(et, {'CJ1', 'CJ5', 'CJ7', 'CJ8'}, outs, {'CJ6'}, {})
        self.assertEqual(r, [])

    def test_orden_llena_primero(self):
        et = [('CJ1', 'ETQ ZONA A'), ('CJ2', 'ETQ ZONA A'), ('CJ3', 'ETQ ZONA B'), ('CJ4', 'ETQ ZONA B'),
              ('CJ5', 'ETQ ZONA C'), ('CJ6', 'ETQ ZONA C')]
        outs = {'A': out(ident=1), 'B': out(ident=2), 'C': out(ident=3)}
        vol = {'CJ1': 0.05, 'CJ3': 0.09, 'CJ5': 0.12}
        r = calc.saltadas(et, {'CJ1', 'CJ3', 'CJ5'}, outs, set(), {'CJ1': 30, 'CJ3': 5, 'CJ5': 8}, vol, {'CJ5'})
        self.assertEqual([x['cj'] for x in r], ['CJ6', 'CJ4', 'CJ2'])


class TestVolumen(unittest.TestCase):

    def test_umbrales(self):
        t = calc.umbrales('CAJA 600X400X400=0,11; caja koroshi mediana = 0.10; basura; X=abc')
        self.assertEqual(calc.umbral_de('CAJA 600X400X400', t), 0.11)
        self.assertEqual(calc.umbral_de('CAJA KOROSHI MEDIANA', t), 0.10)
        self.assertEqual(calc.umbral_de('OTRA', t), calc.UMBRAL_DEFECTO)
        self.assertEqual(calc.umbral_de('OTRA', calc.umbrales('*=0.2')), 0.2)

    def test_volumenes_con_media(self):
        vol, media = calc.volumenes([('CJ1', 1, 2), ('CJ1', 2, 1), ('CJ2', 3, 4)], {1: 0.01, 2: 0.03, 3: 0})
        self.assertAlmostEqual(media, 0.02)
        self.assertAlmostEqual(vol['CJ1'], 0.05)
        self.assertAlmostEqual(vol['CJ2'], 0.08)     # sin volumen: la media

    def test_dos_cajas_y_capacidad(self):
        vol = {'CJ1': 0.149, 'CJ2': 0.08, 'CJ3': 0.105}
        tipo = {'CJ1': 'CAJA 600X400X400', 'CJ2': 'CAJA 600X400X400', 'CJ3': 'CAJA KOROSHI MEDIANA'}
        t = calc.umbrales('CAJA KOROSHI MEDIANA=0.10')
        r = calc.dos_cajas(vol, tipo, t, {'CJ1': {'tienda': 'K1'}})
        self.assertEqual([(x['cj'], x['m3']) for x in r], [('CJ1', 0.149), ('CJ3', 0.105)])
        self.assertEqual(r[0]['tienda'], 'K1')
        c = calc.capacidad(vol, tipo)
        self.assertEqual(c[0]['tipo'], 'CAJA 600X400X400')
        self.assertEqual((c[0]['n'], c[0]['max']), (2, 0.149))


if __name__ == '__main__':
    unittest.main()

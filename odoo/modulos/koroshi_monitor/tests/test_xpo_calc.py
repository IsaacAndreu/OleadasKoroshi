# -*- coding: utf-8 -*-
# Pruebas sin Odoo:  python -I odoo/modulos/koroshi_monitor/tests/test_xpo_calc.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'controllers'))
import xpo_calc as calc  # noqa: E402


def grupo(tienda, expediciones, bultos):
    return {'tienda': tienda, 'expediciones': expediciones, 'bultos': bultos}


class TestFilasXpo(unittest.TestCase):

    def test_k01_del_17_11_como_el_excel_de_amposta(self):
        # 26076 hizo la etiqueta (7 declarados); 26077 se validó después, sin nº y con 0 bultos propios.
        filas = calc.filas_xpo([grupo('K01 - MAQUINISTA', ['121771266'], 6)], {'121771266': 7})
        self.assertEqual(filas, [{'tienda': 'K01 - MAQUINISTA', 'expedicion': '121771266', 'bultos': 7,
                                  'volumen': 0.63, 'peso': 105.0}])

    def test_expedicion_con_dos_pedidos_va_una_vez(self):
        filas = calc.filas_xpo([grupo('K62 - XANADU', ['1'], 9), grupo('K62 - XANADU', ['1'], 8)], {'1': 17})
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['bultos'], 17)
        self.assertEqual(filas[0]['volumen'], 1.53)
        self.assertEqual(filas[0]['peso'], 255.0)

    def test_sin_nota_suma_los_bultos_de_las_out(self):
        filas = calc.filas_xpo([grupo('K80-LA JONQUERA', ['5'], 20), grupo('K80-LA JONQUERA', ['5'], 13)], {})
        self.assertEqual([(f['expedicion'], f['bultos'], f['volumen'], f['peso']) for f in filas],
                         [('5', 33, 2.97, 495.0)])

    def test_dos_expediciones_misma_tienda_dos_filas(self):
        filas = calc.filas_xpo([grupo('K72 - DIAGONAL MAR', ['2'], 10), grupo('K72 - DIAGONAL MAR', ['3'], 11)],
                               {'2': 10})
        self.assertEqual([(f['expedicion'], f['bultos']) for f in filas], [('2', 10), ('3', 11)])

    def test_orden_por_numero_de_tienda(self):
        filas = calc.filas_xpo([grupo('K85 - PLATJA', ['a'], 1), grupo('k40 - PALENCIA', ['b'], 1),
                                grupo('K7 - ISLAZUL', ['c'], 1), grupo('', [], 2)], {})
        self.assertEqual([f['tienda'] for f in filas], ['K7 - ISLAZUL', 'k40 - PALENCIA', 'K85 - PLATJA', '—'])

    def test_total_igual_que_el_resumen_del_cierre(self):
        # El resumen (envios._resumen_xpo) suma por tienda: declarados una vez por ref + bultos de pedidos sin nota.
        grupos = [grupo('K1', ['1'], 6), grupo('K1', ['1'], 0), grupo('K2', ['2'], 4), grupo('K3', [], 3)]
        filas = calc.filas_xpo(grupos, {'1': 7})
        self.assertEqual(sum(f['bultos'] for f in filas), 7 + 4 + 3)


if __name__ == '__main__':
    unittest.main()

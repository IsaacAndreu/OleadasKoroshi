# -*- coding: utf-8 -*-
# Casos sinteticos de la definicion de caja cerrada real. Los de datos reales anonimizados se anaden
# cuando haya un volcado de produccion (ver consulta en el informe de la fase 1).
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor import medir  # noqa: E402


def ln(id_, out, caja, uds, litros):
    return {'id': id_, 'out_id': out, 'caja_id': caja, 'uds': uds, 'litros': litros}


class TestMedir(unittest.TestCase):
    def test_out_limpia_dos_cajas_llenas(self):
        lineas = [ln(1, 'A', 'c1', 10, 40), ln(2, 'A', 'c1', 10, 40), ln(3, 'A', 'c2', 18, 70)]
        por_out, por_caja = medir.medir(lineas, ['A'])
        r = por_out['A']
        self.assertEqual(r['cajas_reales'], 2)
        self.assertEqual(r['cajas_cerradas'], 2)
        self.assertTrue(r['cerrada'])
        self.assertEqual(r['cajas_estimadas'], 2)       # 150 L: 2 cajas, la ultima con 70 L (>= 64)
        self.assertTrue(r['cerrada_estimada'])

    def test_ultima_caja_a_medias(self):
        lineas = [ln(1, 'A', 'c1', 20, 80), ln(2, 'A', 'c2', 5, 20)]
        por_out, _ = medir.medir(lineas, ['A'])
        self.assertEqual(por_out['A']['cajas_reales'], 2)
        self.assertEqual(por_out['A']['cajas_cerradas'], 1)
        self.assertFalse(por_out['A']['cerrada'])

    def test_caja_existente_out_pequena_en_caja_de_otra(self):
        # A llena c1 (70 L); B (pequena, del mismo pedido) mete 2 uds en c1 y se valida con 0 bultos
        lineas = [ln(10, 'A', 'c1', 15, 70), ln(20, 'B', 'c1', 2, 6)]
        por_out, por_caja = medir.medir(lineas, ['A', 'B'])
        self.assertEqual(por_caja['c1']['dueno'], 'A')
        self.assertTrue(por_caja['c1']['compartida'])
        self.assertTrue(por_caja['c1']['llena'])
        self.assertFalse(por_caja['c1']['cerrada'])          # compartida: nunca cerrada
        self.assertEqual(por_out['A']['cajas_reales'], 1)
        self.assertEqual(por_out['A']['cajas_cerradas'], 0)
        self.assertEqual(por_out['A']['cajas_compartidas'], 1)
        self.assertEqual(por_out['B']['cajas_reales'], 0)    # 0 bultos
        self.assertEqual(por_out['B']['cajas_ajenas'], 1)
        self.assertEqual(por_out['B']['uds_en_ajenas'], 2)
        self.assertFalse(por_out['B']['cerrada'])
        self.assertEqual(por_out['B']['cajas_estimadas'], 1)  # el modelo le daba 1 caja

    def test_regla_dueno(self):
        # B tiene la linea de menor id pero A mete mas uds: las dos reglas dan dueno distinto
        lineas = [ln(5, 'B', 'c1', 2, 6), ln(10, 'A', 'c1', 15, 70)]
        _, c1 = medir.medir(lineas, ['A', 'B'], regla_dueno='primera_linea')
        _, c2 = medir.medir(lineas, ['A', 'B'], regla_dueno='mas_uds')
        self.assertEqual(c1['c1']['dueno'], 'B')
        self.assertEqual(c2['c1']['dueno'], 'A')
        with self.assertRaises(ValueError):
            medir.medir(lineas, ['A'], regla_dueno='otra')

    def test_caja_compartida_con_out_no_medida(self):
        # C no esta en el grupo medido pero usa la caja de A: la caja sigue siendo compartida
        lineas = [ln(1, 'A', 'c1', 20, 75), ln(2, 'C', 'c1', 1, 3)]
        por_out, por_caja = medir.medir(lineas, ['A'])
        self.assertNotIn('C', por_out)
        self.assertTrue(por_caja['c1']['compartida'])
        self.assertEqual(por_out['A']['cajas_compartidas'], 1)

    def test_uds_sin_caja(self):
        lineas = [ln(1, 'A', 'c1', 20, 75), ln(2, 'A', None, 3, 9)]
        por_out, _ = medir.medir(lineas, ['A'])
        self.assertEqual(por_out['A']['uds_sin_caja'], 3)
        self.assertFalse(por_out['A']['cerrada'])

    def test_resumen_separa_causas(self):
        lineas = [ln(1, 'A', 'c1', 20, 75), ln(2, 'A', 'c2', 20, 75),
                  ln(3, 'B', 'c3', 15, 70), ln(4, 'D', 'c3', 2, 6)]
        por_out, _ = medir.medir(lineas, ['A', 'B', 'D'])
        res = medir.resumen(por_out, previstas={'A': 2, 'B': 1, 'D': 1})
        self.assertEqual(res['outs'], 3)
        self.assertEqual(res['cajas_reales'], 3)
        self.assertEqual(res['cajas_cerradas'], 2)
        self.assertEqual(res['pct_cajas_cerradas'], 66.7)
        limpias = res['grupos']['limpias']
        comp = res['grupos']['con_compartida']
        self.assertEqual((limpias['outs'], limpias['previstas'], limpias['reales']), (1, 2, 2))
        self.assertEqual((comp['outs'], comp['previstas'], comp['reales']), (2, 2, 1))


if __name__ == '__main__':
    unittest.main()

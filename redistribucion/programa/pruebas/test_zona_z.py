# -*- coding: utf-8 -*-
"""Pruebas de la zona Z (outlet) sin Odoo: hojas de estanterías y grupos por rotación."""
import tempfile
import unittest
from pathlib import Path

from redistrib import zona_z as Z


class Estanterias(unittest.TestCase):

    def _csv(self, filas):
        ruta = Path(tempfile.mkdtemp()) / 'e.csv'
        ruta.write_text('hoja;lineal;lado;posicion;tipo;duda\n' + '\n'.join(filas) + '\n', encoding='utf-8')
        return ruta

    def test_vale_el_numero_escrito_a_mano(self):
        # hoja 2: la casilla impresa P34 lleva «36» escrito encima → es la P36 de Odoo
        t = Z.leer_estanterias(self._csv(['2;9;medianera;34;D10;número escrito a mano encima: 36',
                                          '2;9;medianera;33;B24;']))
        self.assertEqual(t[(9, 36)]['tipo'], 'D10')
        self.assertNotIn((9, 34), t)
        self.assertEqual(t[(9, 33)]['tipo'], 'B24')

    def test_renumerada_gana_a_la_impresa(self):
        t = Z.leer_estanterias(self._csv(['4;24;medianera;25;E;número escrito a mano encima: 22',
                                          '4;24;medianera;22;C;']))
        self.assertEqual(t[(24, 22)]['tipo'], 'E')

    def test_tipo_raro_es_duda(self):
        t = Z.leer_estanterias(self._csv(['2;8;medianera;32;falta;', '2;8;medianera;31;;']))
        self.assertEqual((t[(8, 32)]['tipo'], t[(8, 31)]['tipo']), ('?', '?'))
        self.assertIn('FALTA', t[(8, 32)]['duda'])


class Grupos(unittest.TestCase):

    def test_grupo_por_rotacion_y_temporada_nueva(self):
        r = Z.ReglasZ()
        self.assertEqual(Z._grupo(1.4, False, r), 'vivo')
        self.assertEqual(Z._grupo(0.3, False, r), 'lento')
        self.assertEqual(Z._grupo(0.05, False, r), 'muerto')
        self.assertEqual(Z._grupo(0.05, True, r), 'vivo')       # V26 acaba de llegar al outlet

    def test_percentil(self):
        self.assertEqual(Z._percentil([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9), 9)
        self.assertEqual(Z._percentil([], 0.9), 0)


if __name__ == '__main__':
    unittest.main()

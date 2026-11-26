# -*- coding: utf-8 -*-
"""Pruebas de redistrib/fuentes.py: la última versión de cada matriz, con ficheros vacíos inventados."""
import tempfile
import unittest
from pathlib import Path

from redistrib import fuentes


class Matrices(unittest.TestCase):

    def test_ultima_version_de_cada_matriz(self):
        d = Path(tempfile.mkdtemp())
        for n in ['261120_KOROSHI_1_MASTER_OI_26-27_v12.xlsx', '261124_KOROSHI_1_MASTER_OI_26-27_v14.xlsx',
                  '261120_KOROSHI_1_MASTER_OI_26-27_v13.xlsx', '261123_KOROSHI_2_Recepcion_y_desviaciones_v3.xlsx',
                  '261120_MASTER_OI_26-27_KOROSHI_v11.xlsx',            # nombre antiguo: no es una matriz
                  '~$261124_KOROSHI_1_MASTER_OI_26-27_v15.xlsx',        # fichero temporal de Excel abierto
                  '20261124_informe.xlsx']:
            (d / n).write_bytes(b'')
        m = fuentes.matrices(d)
        self.assertEqual([(x.numero, x.version, x.anteriores) for x in m], [(1, 14, 2), (2, 3, 0)])
        self.assertEqual(m[0].fecha, '24/11/2026')
        self.assertEqual(fuentes.matriz(2, d).nombre, 'Recepcion y desviaciones')
        self.assertIsNone(fuentes.matriz(3, d))

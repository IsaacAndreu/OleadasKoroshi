# -*- coding: utf-8 -*-
# Pruebas sin Odoo de logica.py:  python odoo/modulos/koroshi_s4t_pedidos/pruebas/test_logica.py
# (carpeta «pruebas» y no «tests»: Odoo no las carga)
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logica  # noqa: E402


class TestLogica(unittest.TestCase):

    def test_umbral(self):
        self.assertTrue(logica.es_grande(329, 60))
        self.assertTrue(logica.es_grande(60, 60))
        self.assertFalse(logica.es_grande(59, 60))
        self.assertFalse(logica.es_grande(5, 60))        # tienda pequena: como antes
        self.assertFalse(logica.es_grande(329, 0))       # 0 = apagado

    def test_leer_entero(self):
        self.assertEqual(logica.leer_entero(None, 60, 0), 60)
        self.assertEqual(logica.leer_entero('', 60, 0), 60)
        self.assertEqual(logica.leer_entero('abc', 60, 0), 60)
        self.assertEqual(logica.leer_entero(' 80 ', 60, 0), 80)
        self.assertEqual(logica.leer_entero('0', 60, 0), 0)    # apagar el umbral
        self.assertEqual(logica.leer_entero('-3', 60, 0), 60)
        self.assertEqual(logica.leer_entero('0', 50, 1), 50)   # bloque 0 no vale

    def test_bloques(self):
        ids = list(range(1, 330))
        trozos = logica.bloques(ids, 50)
        self.assertEqual(len(trozos), 7)
        self.assertEqual([len(t) for t in trozos], [50] * 6 + [29])
        self.assertEqual(sum(trozos, []), ids)               # ni falta ni sobra ninguno, en orden
        self.assertEqual(logica.bloques([], 50), [])
        self.assertEqual(logica.bloques([1, 2], 0), [[1], [2]])

    def test_claves_distintas(self):
        # El cron 192 v7 usa las mismas claves: si cambian, hay que cambiarlas alli
        self.assertEqual((logica.CLAVE_FEED, logica.CLAVE_PEDIDO), (719401, 719402))


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
# Nombres reales de agrupaciones Z- de Odoo (21/10 a 11/11/2026).
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor import nombres  # noqa: E402


class TestNombres(unittest.TestCase):
    def test_zonas(self):
        for nombre, esperado in (('Z-1111-MU1', ('Z-1111-', 'MU1')), ('Z-1011-ZX2', ('Z-1011-', 'ZX2')),
                                 ('Z-2710-R2-D8', ('Z-2710-R2-', 'D8')), ('Z-2210-ZX', ('Z-2210-', 'ZX')),
                                 ('Z-0611-A', ('Z-0611-', 'A')), ('Z-0611-MU', ('Z-0611-', 'MU'))):
            self.assertEqual(nombres.partir_nombre_lote(nombre), esperado)

    def test_agrupaciones_de_almacen_no_son_zona(self):
        for nombre in ('Z-2210-SALIO 22-10', 'Z-2210- SALE 26-10', 'Z-2710- SALE 28-10', 'Z-0611- SALE 09-11',
                       'Z-1011 SALE 11-', 'TIENDA-1011', '', None):
            self.assertIsNone(nombres.partir_nombre_lote(nombre))
        self.assertTrue(nombres.es_lote_z('Z-1011 SALE 11-'))
        self.assertFalse(nombres.es_lote_z('TIENDA-1011'))

    def test_nota(self):
        nota = 'Z-2210-D3 | CAJA 05 | K1 - TIENDA1 | PEDIDO S-1 | CAJAS 2'
        self.assertEqual(nombres.zona_de_nota(nota), ('Z-2210-', 'D3'))
        self.assertEqual(nombres.cajas_de_nota(nota), 2)
        self.assertEqual(nombres.cajas_de_nota('... | CAJAS 0'), 0)
        self.assertIsNone(nombres.zona_de_nota('Envio junto: OUT/1, OUT/2'))
        self.assertIsNone(nombres.cajas_de_nota('Envio junto: OUT/1, OUT/2'))
        self.assertIsNone(nombres.zona_de_nota(False))


if __name__ == '__main__':
    unittest.main()

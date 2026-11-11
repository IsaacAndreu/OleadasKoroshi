# -*- coding: utf-8 -*-
# Fase 3: la configuracion por defecto da EXACTAMENTE los parametros de la v12f.
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor import modelo  # noqa: E402


class TestConfig(unittest.TestCase):
    def test_por_defecto_igual_v12f(self):
        cfg = modelo.config_por_defecto()
        cambios = modelo.cambios_desde_config(cfg, modelo.POR_DEFECTO['LITROS_TIPO'], 3.0)
        self.assertEqual(modelo.parametros(cambios), modelo.parametros())

    def test_tipos_de_dato(self):
        cambios = modelo.cambios_desde_config({'litros_caja': 93, 'personas': 10, 'tiendas_48h': '7; 24 ,x, 29'})
        self.assertIsInstance(cambios['LITROS_CAJA'], float)
        self.assertEqual(cambios['PERSONAS'], 10)
        self.assertEqual(cambios['TIENDAS_48H'], [7, 24, 29])

    def test_contexto_manda_sobre_config(self):
        p = modelo.parametros(modelo.cambios_desde_config({'personas': 10}), {'personas': 8})
        self.assertEqual(p['PERSONAS'], 8)


if __name__ == '__main__':
    unittest.main()

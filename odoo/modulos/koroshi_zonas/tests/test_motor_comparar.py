# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor import comparar  # noqa: E402


class TestComparar(unittest.TestCase):
    def test_igual(self):
        r = comparar.comparar({1: 'D1', 2: 'MU1'}, {1: 'D1', 2: 'MU1'})
        self.assertTrue(comparar.es_igual(r))
        self.assertIn('IGUAL', comparar.texto(r, 'Z-1211-', ['Z-1211-']))

    def test_distinto(self):
        r = comparar.comparar({1: 'D1', 2: 'D2', 3: 'D3'}, {1: 'D1', 2: 'D3', 4: 'MU2'})
        self.assertFalse(comparar.es_igual(r))
        self.assertEqual(r['iguales'], 1)
        self.assertEqual(r['distintas'], [(2, 'D2', 'D3')])
        self.assertEqual(r['solo_modulo'], [3])
        self.assertEqual(r['solo_202'], [4])

    def test_vacio_no_es_igual(self):
        self.assertFalse(comparar.es_igual(comparar.comparar({}, {})))


if __name__ == '__main__':
    unittest.main()

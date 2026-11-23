# -*- coding: utf-8 -*-
# Pruebas sin Odoo de cache.py (v1.44.0): python odoo/modulos/koroshi_monitor/tests/test_cache.py
import importlib.util
import os
import threading
import time
import unittest

_RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache.py')
_spec = importlib.util.spec_from_file_location('cache', _RUTA)
cache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cache)


class Reloj(object):
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class TestCachePorClave(unittest.TestCase):

    def test_guarda_y_caduca(self):
        reloj = Reloj()
        c = cache.CachePorClave(20, reloj=reloj)
        n = []
        calc = lambda: n.append(1) or len(n)
        self.assertEqual(c.obtener('a', calc), 1)
        reloj.t += 10
        self.assertEqual(c.obtener('a', calc), 1)       # aun vale
        reloj.t += 15
        self.assertEqual(c.obtener('a', calc), 2)       # caducado: se calcula otra vez

    def test_segundos_propios(self):
        reloj = Reloj()
        c = cache.CachePorClave(20, reloj=reloj)
        c.obtener('p', lambda: 'x', segundos=180)
        reloj.t += 100
        self.assertEqual(c.obtener('p', lambda: 'y', segundos=180), 'x')

    def test_error_no_se_guarda(self):
        c = cache.CachePorClave(20)

        def falla():
            raise ValueError('mal')
        with self.assertRaises(ValueError):
            c.obtener('a', falla)
        self.assertEqual(c.obtener('a', lambda: 'bien'), 'bien')

    def test_borra_lo_viejo(self):
        reloj = Reloj()
        c = cache.CachePorClave(20, max_edad=600, reloj=reloj)
        c.obtener('vieja', lambda: 1)
        reloj.t += 700
        c.obtener('nueva', lambda: 2)
        self.assertEqual(c.claves(), ['nueva'])

    def test_misma_clave_un_solo_calculo(self):
        c = cache.CachePorClave(20)
        n = []

        def lento():
            n.append(1)
            time.sleep(0.2)
            return 'r'
        hilos = [threading.Thread(target=c.obtener, args=('a', lento)) for _ in range(5)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(len(n), 1)

    def test_otra_clave_no_espera(self):
        c = cache.CachePorClave(20)
        empezado = threading.Event()
        soltar = threading.Event()

        def bloqueado():
            empezado.set()
            soltar.wait(5)
            return 'a'
        h = threading.Thread(target=c.obtener, args=('a', bloqueado))
        h.start()
        empezado.wait(5)
        t0 = time.time()
        self.assertEqual(c.obtener('b', lambda: 'b'), 'b')   # no espera a que acabe 'a'
        self.assertLess(time.time() - t0, 1)
        soltar.set()
        h.join()


if __name__ == '__main__':
    unittest.main()

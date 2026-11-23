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


class TestPrioridad(unittest.TestCase):

    def mov(self, numero, pedido, reservado, pid=1, mid=1):
        return {'numero': numero, 'picking_id': pid, 'id': mid, 'pedido': pedido, 'reservado': reservado}

    def test_numero_pedido(self):
        self.assertEqual(logica.numero_pedido('S-6665004409'), 6665004409)
        self.assertEqual(logica.numero_pedido('S-6665004409-02'), 6665004409)
        self.assertEqual(logica.numero_pedido(''), logica.SIN_PEDIDO)
        self.assertEqual(logica.numero_pedido(None), logica.SIN_PEDIDO)

    def test_disputa_el_alto_tiene_y_al_bajo_le_falta(self):
        movs = [self.mov(6665004500, 3, 3, 2, 20), self.mov(6665004400, 3, 0, 1, 10)]
        self.assertTrue(logica.en_disputa(movs))

    def test_sin_disputa_si_hay_para_todos(self):
        movs = [self.mov(6665004500, 3, 3, 2, 20), self.mov(6665004400, 3, 3, 1, 10)]
        self.assertFalse(logica.en_disputa(movs))

    def test_sin_disputa_si_al_que_falta_es_el_mas_alto(self):
        # ya esta en el orden bueno: el bajo tiene todo, al alto le falta
        movs = [self.mov(6665004400, 3, 3, 1, 10), self.mov(6665004500, 3, 1, 2, 20)]
        self.assertFalse(logica.en_disputa(movs))

    def test_sin_disputa_si_nadie_tiene(self):
        movs = [self.mov(6665004400, 3, 0, 1, 10), self.mov(6665004500, 3, 0, 2, 20)]
        self.assertFalse(logica.en_disputa(movs))

    def test_disputa_parcial(self):
        # al bajo le falta 1 y el alto tiene 1: hay que pasarselo
        movs = [self.mov(6665004400, 3, 2, 1, 10), self.mov(6665004500, 3, 1, 2, 20)]
        self.assertTrue(logica.en_disputa(movs))

    def test_cambios(self):
        self.assertEqual(logica.cambios({10: 0.0, 20: 3.0}, {10: 3.0, 20: 0.0}), [(10, 0.0, 3.0), (20, 3.0, 0.0)])
        self.assertEqual(logica.cambios({10: 3.0}, {10: 3.0}), [])

    def test_modo(self):
        self.assertEqual(logica.modo_prioridad(None), 'simular')
        self.assertEqual(logica.modo_prioridad(' REAL '), 'real')
        self.assertEqual(logica.modo_prioridad('apagado'), 'apagado')
        self.assertEqual(logica.modo_prioridad('si'), 'simular')   # mal escrito: nunca real por error

    def test_claves(self):
        self.assertEqual(logica.CLAVE_PRIORIDAD, 719403)



class TestCuandoNo(unittest.TestCase):
    """v1.2.0 (R15): horario de trabajo y reparto de zonas."""

    def test_horario(self):
        self.assertTrue(logica.en_horario(6, 0, '06:00-17:00'))
        self.assertTrue(logica.en_horario(16, 59, '06:00-17:00'))
        self.assertFalse(logica.en_horario(17, 0, '06:00-17:00'))
        self.assertFalse(logica.en_horario(5, 59, '06:00-17:00'))
        self.assertFalse(logica.en_horario(10, 5, '06:00-10:00,10:15-17:00'))

    def test_horario_mal_escrito(self):
        self.assertTrue(logica.en_horario(9, 0, 'basura'))
        self.assertTrue(logica.en_horario(9, 0, ''))

    def test_zonas(self):
        import datetime
        z = datetime.datetime(2026, 11, 24, 3, 50)
        self.assertFalse(logica.parar_por_zonas(datetime.datetime(2026, 11, 24, 3, 30), z, 5))
        self.assertTrue(logica.parar_por_zonas(datetime.datetime(2026, 11, 24, 3, 46), z, 5))
        self.assertTrue(logica.parar_por_zonas(datetime.datetime(2026, 11, 24, 3, 55), z, 5))   # zonas en marcha
        self.assertFalse(logica.parar_por_zonas(datetime.datetime(2026, 11, 24, 3, 55), None, 5))

if __name__ == '__main__':
    unittest.main()

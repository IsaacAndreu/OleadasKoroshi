# -*- coding: utf-8 -*-
# Pruebas sin Odoo: python odoo/modulos/koroshi_transportista/tests/test_logica.py
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import logica  # noqa: E402


class TestTienda(unittest.TestCase):

    def test_tienda(self):
        self.assertEqual(logica.tienda_de('DIGITAL E-GLOBAL XPERIENCE, SL, K24 - VALLADOLID'), 'K24 - VALLADOLID')
        self.assertEqual(logica.tienda_de("DIGITAL E-GLOBAL XPERIENCE, SL, K86 - L'ALJUB (ELX)"), "K86 - L'ALJUB (ELX)")

    def test_web_no_es_tienda(self):
        self.assertEqual(logica.tienda_de('DIGITAL E-GLOBAL XPERIENCE, SL'), '')
        self.assertEqual(logica.tienda_de(''), '')

    def test_transportista(self):
        self.assertEqual(logica.transportista_de('gls_asm'), logica.GLS)
        self.assertEqual(logica.transportista_de('xpo_es'), logica.XPO)
        self.assertEqual(logica.transportista_de('fixed'), '')


class TestCuadre(unittest.TestCase):
    ESP = {'CJ665000001': ['OUT/1'], 'CJ665000002': ['OUT/1'], 'CJ665000003': ['OUT/2']}

    def test_cuadra(self):
        r = logica.cuadre(['CJ665000003', 'CJ665000001', 'CJ665000002'], self.ESP)
        self.assertTrue(r['ok'])
        self.assertEqual((r['leidas'], r['esperadas']), (3, 3))

    def test_falta(self):
        r = logica.cuadre(['CJ665000001', 'CJ665000002'], self.ESP)
        self.assertFalse(r['ok'])
        self.assertEqual(r['faltan'], ['CJ665000003'])

    def test_sobra(self):
        r = logica.cuadre(['CJ665000001', 'CJ665000002', 'CJ665000003', 'CJ665000009'], self.ESP)
        self.assertFalse(r['ok'])
        self.assertEqual(r['sobran'], ['CJ665000009'])

    def test_repetida_cuenta_una(self):
        r = logica.cuadre(['CJ665000001', 'CJ665000001', 'CJ665000002', 'CJ665000003'], self.ESP)
        self.assertTrue(r['ok'])

    def test_nada_esperado_no_cuadra(self):
        self.assertFalse(logica.cuadre([], {})['ok'])


class TestMotivo(unittest.TestCase):

    def out(self, **c):
        o = {'nombre': 'OUT/1', 'tienda': 'K24 - VALLADOLID', 'estado': 'done', 'tracking': '', 'dias': 0,
             'en_cierre': False}
        o.update(c)
        return o

    def m(self, **c):
        d = {'existe': True, 'juntada_en': '', 'outs': [self.out()], 'tienda': 'K24 - VALLADOLID'}
        d.update(c)
        return logica.motivo_sobra(d)

    def test_no_existe(self):
        self.assertIn('no existe', self.m(existe=False))

    def test_juntada(self):
        self.assertIn('juntada dentro de CJ665000005', self.m(juntada_en='CJ665000005'))

    def test_vacia(self):
        self.assertIn('vacía', self.m(outs=[]))

    def test_otra_tienda(self):
        self.assertIn('K9 - BILBAO', self.m(outs=[self.out(tienda='K9 - BILBAO')]))

    def test_sin_validar(self):
        self.assertIn('no está validada: OUT/1', self.m(outs=[self.out(estado='assigned')]))

    def test_ya_etiquetada(self):
        self.assertIn('ya tiene etiqueta', self.m(outs=[self.out(tracking='121771350')]))

    def test_camion_cerrado(self):
        self.assertIn('camión', self.m(outs=[self.out(en_cierre=True)]))

    def test_vieja(self):
        self.assertIn('más de 10 días', self.m(outs=[self.out(dias=12)]))


class TestRepartoGls(unittest.TestCase):

    def test_juntada_sin_bultos_no_se_manda(self):
        # K85 28/10: 3 cajas y OUT juntadas con 0 bultos -> solo se mandan las que tienen bultos
        r = logica.reparto_gls([{'id': 1, 'bultos': 3, 'cajas': [10, 11, 12]}, {'id': 2, 'bultos': 0, 'cajas': []}])
        self.assertEqual(r['enviar'], [1])
        self.assertEqual(r['juntadas'], [2])
        self.assertEqual((r['bultos_gls'], r['cajas']), (3, 3))

    def test_cajas_compartidas(self):
        # S-6665004759 K61 24/11: 2 cajas, una OUT cuyas cajas ya van en la otra -> no se manda
        r = logica.reparto_gls([{'id': 1, 'bultos': 2, 'cajas': [10, 11]}, {'id': 2, 'bultos': 1, 'cajas': [11]}])
        self.assertEqual(r['enviar'], [1])
        self.assertEqual(r['compartidas'], [2])
        self.assertEqual((r['bultos_gls'], r['cajas']), (2, 2))

    def test_cruzadas_avisa(self):
        r = logica.reparto_gls([{'id': 1, 'bultos': 2, 'cajas': [10, 11]}, {'id': 2, 'bultos': 2, 'cajas': [11, 12]}])
        self.assertEqual(sorted(r['enviar']), [1, 2])
        self.assertEqual((r['bultos_gls'], r['cajas']), (4, 3))

    def test_ninguna_con_bultos_se_mandan_todas(self):
        r = logica.reparto_gls([{'id': 1, 'bultos': 0, 'cajas': []}, {'id': 2, 'bultos': 0, 'cajas': []}])
        self.assertEqual(sorted(r['enviar']), [1, 2])


if __name__ == '__main__':
    unittest.main()

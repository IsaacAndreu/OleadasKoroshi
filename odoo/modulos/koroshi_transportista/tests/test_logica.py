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


class TestCifras(unittest.TestCase):
    """v1.1.0: escribir las últimas cifras de la CJ cuando la etiqueta no se puede leer (Isaac, 25/11)."""
    CAND = ['CJ665013925', 'CJ665013838', 'CJ665003925']

    def test_son_cifras(self):
        self.assertTrue(logica.son_cifras('3925'))
        self.assertTrue(logica.son_cifras(' 665013925 '))
        self.assertFalse(logica.son_cifras('925'))
        self.assertFalse(logica.son_cifras('CJ665013925'))
        self.assertFalse(logica.son_cifras('39a5'))

    def test_una(self):
        self.assertEqual(logica.elegir_por_cifras('3838', self.CAND), ('CJ665013838', ['CJ665013838']))

    def test_varias_piden_mas_cifras(self):
        cj, coinciden = logica.elegir_por_cifras('3925', self.CAND)
        self.assertEqual(cj, '')
        self.assertEqual(coinciden, ['CJ665003925', 'CJ665013925'])
        self.assertEqual(logica.elegir_por_cifras('13925', self.CAND)[0], 'CJ665013925')

    def test_ninguna(self):
        self.assertEqual(logica.elegir_por_cifras('9999', self.CAND), ('', []))


class TestSumiYK41(unittest.TestCase):
    """v1.2.0: SUMI en la pantalla; K41 25/11: una caja juntada en dos OUT -> GLS contaba 8 con 7 cajas."""

    def test_sumi(self):
        self.assertTrue(logica.es_sumi('SUMINISTROS KOROSHI 24/11 K41'))
        self.assertFalse(logica.es_sumi('S-6665004768'))
        self.assertFalse(logica.es_sumi(None))

    def test_k41_cajas_distintas(self):
        outs = [{'id': 27666, 'bultos': 1, 'cajas': [13979]},
                {'id': 27810, 'bultos': 2, 'cajas': [13735, 13736]},
                {'id': 27838, 'bultos': 2, 'cajas': [13799, 13800]},
                {'id': 27839, 'bultos': 2, 'cajas': [13800, 13879, 13880]}]
        r = logica.reparto_gls(outs)
        self.assertEqual(sorted(r['enviar']), [27666, 27810, 27838, 27839])
        self.assertEqual((r['bultos_gls'], r['cajas']), (8, 7))   # a GLS se le manda 7 (models/gls.py)


class TestDejarFuera(unittest.TestCase):
    """v1.3.0: K46 25/11: la OUT 27256 (CJ665013084, del 24/11) no está y bloqueaba la tienda."""

    def test_solo_otro_dia(self):
        import datetime
        hoy = datetime.date(2026, 11, 25)
        self.assertTrue(logica.puede_dejar_fuera(datetime.date(2026, 11, 24), hoy))
        self.assertFalse(logica.puede_dejar_fuera(hoy, hoy))
        self.assertFalse(logica.puede_dejar_fuera(None, hoy))

    def test_motivo(self):
        d = {'existe': True, 'tienda': 'K46 - IRUN', 'outs': [
            {'nombre': 'EFFEC/OUT/27256', 'tienda': 'K46 - IRUN', 'estado': 'done', 'tracking': '', 'dias': 1,
             'en_cierre': False, 'fuera': True}]}
        self.assertIn('dejada fuera', logica.motivo_sobra(d))


class TestHuecos(unittest.TestCase):
    """v1.4.0: K24 25/11, SUMI: 13674 y 13676 de la tanda del 24/11 10:38 -> la 13675 sin leer."""

    def test_k24(self):
        usadas = {'2026-11-24 10:38:22': [665013674, 665013676],
                  '2026-11-25 09:27:44': [665013998, 665013999, 665014000]}
        self.assertEqual(logica.huecos_tanda(usadas), [665013675])

    def test_sin_hueco_o_tanda_larga(self):
        self.assertEqual(logica.huecos_tanda({'a': [665013998, 665013999]}), [])
        self.assertEqual(logica.huecos_tanda({'a': [665010000, 665010100]}), [])
        self.assertEqual(logica.huecos_tanda({'a': [665010000]}), [])


class TestAvisoTransportista(unittest.TestCase):
    """v1.5.0 (Isaac 25/11): GLS hasta 5 bultos; avisar si se sale de lo habitual de la tienda (no prohibir)."""

    def test_gls_grande(self):
        self.assertTrue(logica.avisos_transportista('gls', 8, []))
        self.assertEqual(logica.avisos_transportista('gls', 5, []), [])
        self.assertEqual(logica.avisos_transportista('xpo', 8, []), [])

    def test_historial(self):
        h = [('xpo', 9), ('xpo', 7), ('xpo', 12), ('gls', 3)]
        self.assertEqual(logica.habitual(10, h), ('xpo', 3, 3))
        self.assertEqual(len(logica.avisos_transportista('gls', 10, h)), 2)      # grande y contra lo habitual
        self.assertEqual(logica.avisos_transportista('xpo', 10, h), [])

    def test_mezclado_no_avisa(self):
        h = [('gls', 3), ('xpo', 4), ('gls', 2), ('xpo', 5)]
        self.assertEqual(logica.habitual(3, h)[0], '')
        self.assertEqual(logica.avisos_transportista('xpo', 3, h), [])

    def test_pocas_parecidas_usa_todas(self):
        h = [('gls', 2), ('gls', 3), ('gls', 4), ('xpo', 9)]
        self.assertEqual(logica.habitual(8, h)[0], 'gls')                     # 1 grande: mira las 4
        self.assertEqual(len(logica.avisos_transportista('xpo', 3, h)), 1)


class TestDevolucion(unittest.TestCase):
    """v1.6.0: K65 26/11: EFFEC/OUT/27486 (CJ665013642, validada el 24/11) tiene EFFEC/DEV/000145 preparada: no sale."""

    def test_k65(self):
        self.assertEqual(logica.devoluciones_vivas([('EFFEC/DEV/000145', 'assigned')]), ['EFFEC/DEV/000145'])

    def test_estados(self):
        for e in ('draft', 'waiting', 'confirmed', 'assigned', 'done'):
            self.assertTrue(logica.devoluciones_vivas([('EFFEC/DEV/1', e)]), e)
        self.assertEqual(logica.devoluciones_vivas([('EFFEC/DEV/1', 'cancel')]), [])
        self.assertEqual(logica.devoluciones_vivas([]), [])
        self.assertEqual(logica.devoluciones_vivas([('EFFEC/DEV/2', 'done'), ('EFFEC/DEV/2', 'done'),
                                                    ('EFFEC/DEV/1', 'cancel')]), ['EFFEC/DEV/2'])

    def test_motivo_k65(self):
        d = {'existe': True, 'tienda': 'K65 - BARICENTRO', 'outs': [
            {'nombre': 'EFFEC/OUT/27486', 'tienda': 'K65 - BARICENTRO', 'estado': 'done', 'tracking': '', 'dias': 2,
             'en_cierre': False, 'fuera': False, 'dev': ['EFFEC/DEV/000145']}]}
        m = logica.motivo_sobra(d)
        self.assertIn('devolución', m)
        self.assertIn('EFFEC/DEV/000145', m)


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

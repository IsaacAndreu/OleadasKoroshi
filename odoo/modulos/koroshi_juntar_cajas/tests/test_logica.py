# -*- coding: utf-8 -*-
# Pruebas sin Odoo: python odoo/modulos/koroshi_juntar_cajas/tests/test_logica.py
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import logica  # noqa: E402


def pareja(**cambios):
    d = {
        'cj_o': 'CJ665013630', 'cj_d': 'CJ665013613',
        'n_paquetes_o': 1, 'n_paquetes_d': 1,
        'uds_o': 1, 'uds_d': 25,
        'pedidos_o': ['S-6665004742'], 'pedidos_d': ['S-6665004742'],
        'tiendas_o': [7], 'tiendas_d': [7],
        'companias_o': [8], 'compania': 8,
        'otra_out': True, 'o_sin_validar': False,
        'shipped': False, 'en_cierre': False, 'zalando': False, 'usada': None,
    }
    d.update(cambios)
    return d


class TestPareja(unittest.TestCase):

    def test_buena(self):
        self.assertIsNone(logica.error_pareja(pareja()))

    def test_misma_caja(self):
        self.assertIn('la misma', logica.error_pareja(pareja(cj_d='CJ665013630')))

    def test_repetida_y_destino_vaciada(self):
        self.assertIn('dos veces', logica.error_pareja(pareja(usada='origen')))
        self.assertIn('no puede ser la destino', logica.error_pareja(pareja(usada='destino_vaciada')))

    def test_no_existe(self):
        self.assertIn('no es una caja cerrada', logica.error_pareja(pareja(n_paquetes_o=0)))
        self.assertIn('no es una caja cerrada', logica.error_pareja(pareja(n_paquetes_d=2)))

    def test_vacias(self):
        self.assertIn('vacía', logica.error_pareja(pareja(uds_o=0)))
        self.assertIn('destino', logica.error_pareja(pareja(uds_d=0)))

    def test_otro_pedido_u_otra_tienda(self):
        self.assertIn('mismo pedido', logica.error_pareja(pareja(pedidos_d=['S-6665004702'])))
        self.assertIn('mismo pedido', logica.error_pareja(pareja(pedidos_o=['S-1', 'S-2'], pedidos_d=['S-1'])))
        self.assertIn('misma tienda', logica.error_pareja(pareja(tiendas_d=[9])))

    def test_otra_empresa(self):
        self.assertIn('empresa', logica.error_pareja(pareja(companias_o=[1])))

    def test_zalando_shipped_cierre(self):
        self.assertIn('Zalando', logica.error_pareja(pareja(zalando=True)))
        self.assertIn('SHIPPED', logica.error_pareja(pareja(shipped=True)))
        self.assertIn('camión cerrado', logica.error_pareja(pareja(en_cierre=True)))

    def test_out_sin_validar(self):
        self.assertIn('valídala', logica.error_pareja(pareja(otra_out=True, o_sin_validar=True)))
        # de la misma OUT sin validar sí se puede (las líneas pasan a la otra caja)
        self.assertIsNone(logica.error_pareja(pareja(otra_out=False, o_sin_validar=True)))


class TestAvisos(unittest.TestCase):

    def test_sin_avisos(self):
        self.assertEqual(logica.avisos(pareja()), [])

    def test_etiqueta(self):
        a = logica.avisos(pareja(etiqueta=True, transportista='XPO'))
        self.assertEqual(len(a), 1)
        self.assertIn('XPO', a[0])

    def test_pequena_mas_grande(self):
        a = logica.avisos(pareja(uds_o=30, uds_d=4))
        self.assertIn('más grande', a[0])


class TestReady(unittest.TestCase):

    def test_ready_avisa(self):
        a = logica.avisos(pareja(ready=True))
        self.assertTrue(any('READY' in x for x in a))


def partir(**cambios):
    d = {
        'cj_o': 'CJ665013811', 'cj_n': 'CJ665013810',
        'n_paquetes_o': 1, 'n_paquetes_n': 0, 'uds_o': 23, 'leidas': 10,
        'pedidos_o': ['S-6665004772'], 'pedidos_n': [], 'tiendas_o': [7], 'tiendas_n': [],
        'stock_n_suelto': False, 'shipped': False, 'en_cierre': False, 'zalando': False,
    }
    d.update(cambios)
    return d


class TestPartir(unittest.TestCase):

    def test_bueno_con_cj_nueva_que_no_existe(self):
        self.assertIsNone(logica.error_partir(partir()))

    def test_cj_nueva_vacia_o_del_mismo_pedido(self):
        self.assertIsNone(logica.error_partir(partir(n_paquetes_n=1)))
        self.assertIsNone(logica.error_partir(partir(n_paquetes_n=1, pedidos_n=['S-6665004772'], tiendas_n=[7])))

    def test_errores(self):
        self.assertIn('misma caja', logica.error_partir(partir(cj_n='CJ665013811')))
        self.assertIn('ninguna prenda', logica.error_partir(partir(leidas=0)))
        self.assertIn('no queda nada', logica.error_partir(partir(leidas=23)))
        self.assertIn('otro pedido', logica.error_partir(partir(n_paquetes_n=1, pedidos_n=['S-1'])))
        self.assertIn('otra tienda', logica.error_partir(partir(n_paquetes_n=1, pedidos_n=['S-6665004772'],
                                                                tiendas_n=[9])))
        self.assertIn('stock del almacén', logica.error_partir(partir(n_paquetes_n=1, stock_n_suelto=True)))
        self.assertIn('repetida', logica.error_partir(partir(n_paquetes_n=2)))
        self.assertIn('varios pedidos', logica.error_partir(partir(pedidos_o=['S-1', 'S-2'])))
        self.assertIn('Zalando', logica.error_partir(partir(zalando=True)))
        self.assertIn('SHIPPED', logica.error_partir(partir(shipped=True)))
        self.assertIn('camión cerrado', logica.error_partir(partir(en_cierre=True)))

    def test_avisos_partir_sin_caja_grande(self):
        self.assertEqual(logica.avisos(partir(), partir=True), [])
        self.assertEqual(len(logica.avisos(partir(etiqueta=True, ready=True), partir=True)), 2)


class TestElegirLineas(unittest.TestCase):

    def test_lineas_de_una_ud(self):
        self.assertEqual(sorted(logica.elegir_lineas([(1, 1), (2, 1), (3, 1)], 2)), [1, 2])

    def test_exacta_con_varias_uds(self):
        self.assertEqual(sorted(logica.elegir_lineas([(1, 3), (2, 2), (3, 1)], 4)), [1, 3])
        self.assertEqual(logica.elegir_lineas([(1, 3)], 3), [1])

    def test_no_se_parte_una_linea(self):
        self.assertIsNone(logica.elegir_lineas([(1, 3)], 2))
        self.assertIsNone(logica.elegir_lineas([(1, 1)], 2))

    def test_cero(self):
        self.assertEqual(logica.elegir_lineas([(1, 1)], 0), [])


class TestBultos(unittest.TestCase):

    def test_dueno_y_cambios(self):
        # caja 1: OUT 10 (25 uds); caja 2: OUT 11 (1 ud). Al juntar la 2 en la 1, OUT 11 pasa de 1 a 0 bultos.
        antes = {1: {10: 25}, 2: {11: 1}}
        self.assertEqual(logica.bultos_por_out(antes, {10, 11}, {10, 11}, {10: 1, 11: 1}), [])
        despues = {1: {10: 25, 11: 1}}
        self.assertEqual(logica.bultos_por_out(despues, {10, 11}, {10, 11}, {10: 1, 11: 1}), [(11, 1, 0)])

    def test_empate_out_mas_baja(self):
        self.assertEqual(logica.bultos_por_out({1: {11: 2, 10: 2}}, {10, 11}, {10, 11}, {10: 0, 11: 1}),
                         [(10, 0, 1), (11, 1, 0)])

    def test_out_sin_caja_sin_validar_no_se_toca(self):
        self.assertEqual(logica.bultos_por_out({1: {10: 5}}, {10}, {10}, {10: 1, 12: 3}), [])

    def test_cuadra(self):
        self.assertTrue(logica.cuadra(3, 2, 1))
        self.assertFalse(logica.cuadra(3, 3, 1))
        self.assertTrue(logica.cuadra(5, 3, 2))


class TestTransportista(unittest.TestCase):

    def test_nombres(self):
        self.assertEqual(logica.transportista('XPO Logistics'), 'XPO')
        self.assertEqual(logica.transportista('GLS / ASM España'), 'GLS')
        self.assertEqual(logica.transportista(''), '')


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
# Tests de regla.py sin Odoo. Desde la carpeta del modulo: python -m unittest discover -s tests
# (No hay tests/__init__.py a proposito: no son tests de Odoo.)
import datetime
import importlib.util
import os
import unittest

_RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'regla.py')
_spec = importlib.util.spec_from_file_location('regla', _RUTA)
regla = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(regla)

DT = datetime.datetime


def ped(i, num, tienda):
    return {'id': i, 'name': 'S-%s' % num, 'tienda': tienda}


class TestRegla(unittest.TestCase):

    def test_tienda(self):
        self.assertEqual(regla.tienda_de('K48 - LA MAQUINISTA'), 'K48')
        self.assertEqual(regla.tienda_de('k7 - X'), 'K7')
        self.assertEqual(regla.tienda_de('DIGITAL E-GLOBAL XPERIENCE, SL'), '')
        self.assertEqual(regla.tienda_de('KOROSHI'), '')
        self.assertEqual(regla.tienda_de(None), '')

    def test_inicio_noche(self):
        self.assertEqual(regla.inicio_noche(DT(2026, 11, 24, 4, 40), (14, 0)), DT(2026, 11, 23, 14, 0))
        self.assertEqual(regla.inicio_noche(DT(2026, 11, 24, 15, 0), (14, 0)), DT(2026, 11, 24, 14, 0))
        self.assertEqual(regla.inicio_noche(DT(2026, 11, 24, 14, 0), (14, 0)), DT(2026, 11, 24, 14, 0))

    def test_horas(self):
        self.assertEqual(regla.horas('05:45, 04:40;04:40 x 25:00'), [(4, 40), (5, 45)])
        self.assertEqual(regla.hora('nada', (14, 0)), (14, 0))
        h = [(4, 40), (5, 45)]
        self.assertIsNone(regla.hora_pendiente(DT(2026, 11, 24, 4, 39), h, '', 60))
        self.assertEqual(regla.hora_pendiente(DT(2026, 11, 24, 4, 41), h, '2026-11-23 05:45', 60), '2026-11-24 04:40')
        self.assertIsNone(regla.hora_pendiente(DT(2026, 11, 24, 4, 55), h, '2026-11-24 04:40', 60))
        self.assertEqual(regla.hora_pendiente(DT(2026, 11, 24, 5, 50), h, '2026-11-24 04:40', 60), '2026-11-24 05:45')
        self.assertIsNone(regla.hora_pendiente(DT(2026, 11, 24, 9, 0), h, '2026-11-23 05:45', 60))   # tarde

    def test_estados_de_items(self):
        items = [{'orderNumber': 'S-6665004614', 'status': 'cancelled', 'client': '00006665'},
                 {'orderNumber': 6665004712, 'status': 'PENDING'},
                 {'orderNumber': '6665009999', 'status': 'READY'},
                 'basura']
        est, campos = regla.estados_de_items(items, {'6665004614', '6665004712'})
        self.assertEqual(est, {'6665004614': 'CANCELLED', '6665004712': 'PENDING'})
        self.assertEqual(campos, {'numero': 'orderNumber', 'estado': 'status'})

    def test_un_pedido_por_tienda(self):
        p = [ped(1, '1', 'K1'), ped(2, '2', 'K2'), ped(3, '3', '')]
        self.assertEqual(regla.decidir(p, {}, False), {})
        self.assertEqual(regla.decidir(p, {'1': 'PENDING', '2': 'CANCELLED', '3': 'CANCELLED'}, True),
                         {2: (True, regla.CANCELADO, 'CANCELLED')})

    def test_24_11_con_s4t(self):
        # K48: tres tandas, las dos primeras canceladas: pasa la de las 01:58
        p = [ped(1, '6665004614', 'K48'), ped(2, '6665004663', 'K48'), ped(3, '6665004712', 'K48')]
        est = {'6665004614': 'CANCELLED', '6665004663': 'CANCELLED', '6665004712': 'PENDING'}
        r = regla.decidir(p, est, True)
        self.assertEqual(r[1], (True, regla.DUPLICADO_CANCELADO, 'CANCELLED'))
        self.assertEqual(r[2], (True, regla.DUPLICADO_CANCELADO, 'CANCELLED'))
        self.assertEqual(r[3], (False, regla.UNICO_VIVO, 'PENDING'))

    def test_24_11_sin_s4t(self):
        p = [ped(1, 'a', 'K48'), ped(2, 'b', 'K48'), ped(3, 'c', 'K48')]
        r = regla.decidir(p, {}, False)
        self.assertEqual(set(r), {1, 2, 3})
        self.assertTrue(all(v[0] and v[1] == regla.DUPLICADO for v in r.values()))

    def test_dos_vivos_o_desconocido(self):
        p = [ped(1, 'a', 'K9'), ped(2, 'b', 'K9')]
        r = regla.decidir(p, {'a': 'PENDING', 'b': 'PENDING'}, True)
        self.assertTrue(r[1][0] and r[2][0])
        # S4T no conoce uno: se retienen los dos
        r = regla.decidir(p, {'a': 'PENDING'}, True)
        self.assertTrue(r[1][0] and r[2][0])
        # todos cancelados: se retienen todos
        r = regla.decidir(p, {'a': 'CANCELLED', 'b': 'CANCELLED'}, True)
        self.assertEqual(r[1][1], regla.DUPLICADO_CANCELADO)
        self.assertTrue(r[2][0])

    def test_texto_aviso(self):
        filas = [
            {'tienda': 'K48', 'pedido': 'S-6665004614', 'hora': '01:00', 'uds': 185, 'estado_s4t': 'CANCELLED',
             'motivo': regla.DUPLICADO_CANCELADO, 'retener': True, 'decision': 'pendiente'},
            {'tienda': 'K48', 'pedido': 'S-6665004712', 'hora': '01:58', 'uds': 367, 'estado_s4t': 'PENDING',
             'motivo': regla.UNICO_VIVO, 'retener': False, 'decision': 'pendiente'},
            {'tienda': 'K10', 'pedido': 'S-1', 'hora': '01:00', 'uds': 3, 'estado_s4t': '',
             'motivo': regla.DUPLICADO, 'retener': True, 'decision': 'preparar'},
        ]
        t = regla.texto_aviso(filas, 'leídos 10', 'aviso')
        self.assertIn('1 pedidos de tienda retenidos sin decidir (1 tiendas)', t)
        self.assertIn('MODO AVISO', t)
        self.assertIn('pasa a zonas', t)
        self.assertNotIn('K10 (', t)     # tienda ya decidida: no sale
        self.assertNotIn('MODO AVISO', regla.texto_aviso(filas, '', 'real'))


if __name__ == '__main__':
    unittest.main()

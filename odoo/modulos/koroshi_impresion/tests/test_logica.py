# -*- coding: utf-8 -*-
# Pruebas sin Odoo: python odoo/modulos/koroshi_impresion/tests/test_logica.py
import datetime
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import logica  # noqa: E402

AHORA = datetime.datetime(2026, 11, 25, 10, 0, 0)


class TestConectada(unittest.TestCase):

    def test_sin_contacto(self):
        self.assertFalse(logica.conectada(None, AHORA))

    def test_reciente(self):
        self.assertTrue(logica.conectada(AHORA - datetime.timedelta(seconds=10), AHORA))

    def test_viejo(self):
        self.assertFalse(logica.conectada(AHORA - datetime.timedelta(seconds=61), AHORA))


class TestAtascado(unittest.TestCase):

    def test_aun_no(self):
        self.assertIsNone(logica.que_hacer_atascado(AHORA - datetime.timedelta(minutes=2), 1, AHORA))

    def test_vuelve_a_cola(self):
        self.assertEqual(logica.que_hacer_atascado(AHORA - datetime.timedelta(minutes=6), 1, AHORA), logica.PENDIENTE)

    def test_sin_inicio_vuelve(self):
        self.assertEqual(logica.que_hacer_atascado(None, 0, AHORA), logica.PENDIENTE)

    def test_muchos_intentos_error(self):
        self.assertEqual(logica.que_hacer_atascado(AHORA - datetime.timedelta(minutes=6), 3, AHORA), logica.ERROR)


class TestIds(unittest.TestCase):

    def test_texto(self):
        self.assertEqual(logica.ids_de_texto('12, 13,14,13'), [12, 13, 14])

    def test_vacio(self):
        self.assertEqual(logica.ids_de_texto(''), [])

    def test_malo(self):
        with self.assertRaises(ValueError):
            logica.ids_de_texto('12,abc')
        with self.assertRaises(ValueError):
            logica.ids_de_texto('0')

    def test_ida_y_vuelta(self):
        self.assertEqual(logica.ids_de_texto(logica.texto_de_ids([5, 7])), [5, 7])


class TestCopias(unittest.TestCase):

    def test_por_defecto(self):
        self.assertEqual(logica.copias_validas(None), 1)

    def test_rango(self):
        self.assertEqual(logica.copias_validas('3'), 3)
        with self.assertRaises(ValueError):
            logica.copias_validas(-1)
        with self.assertRaises(ValueError):
            logica.copias_validas(logica.MAX_COPIAS + 1)


class TestUnicos(unittest.TestCase):

    def test_mismo_pdf_en_varias_out(self):
        # 24/11: LabelXPO_121771350.pdf adjunto a 4 OUT con el mismo checksum -> se imprime una vez
        adjuntos = [{'id': 1, 'checksum': 'eb68a40e'}, {'id': 2, 'checksum': 'eb68a40e'},
                    {'id': 3, 'checksum': 'eb68a40e'}, {'id': 4, 'checksum': '3ba50714'}]
        self.assertEqual(logica.unicos_por_contenido(adjuntos), [1, 4])

    def test_sin_checksum(self):
        self.assertEqual(logica.unicos_por_contenido([{'id': 1}, {'id': 2}, {'id': 1}]), [1, 2])


class TestComprobarTrabajo(unittest.TestCase):

    def test_adjunto(self):
        self.assertIsNone(logica.comprobar_trabajo([1], None, None, None))

    def test_informe(self):
        self.assertIsNone(logica.comprobar_trabajo(None, 'koroshi.report_etiqueta_zona', 'zebra.label', [1]))

    def test_las_dos_cosas(self):
        self.assertTrue(logica.comprobar_trabajo([1], 'stock.report_picking', 'stock.picking', [1]))

    def test_nada(self):
        self.assertTrue(logica.comprobar_trabajo(None, None, None, None))

    def test_informe_sin_punto(self):
        self.assertTrue(logica.comprobar_trabajo(None, 'report_etiqueta', 'zebra.label', [1]))

    def test_informe_sin_registros(self):
        self.assertTrue(logica.comprobar_trabajo(None, 'stock.report_picking', 'stock.picking', []))


if __name__ == '__main__':
    unittest.main()
